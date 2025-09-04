from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Dict, List, Any, Union
from datetime import datetime

# --- Input Model (from user) ---
class TaskRequest(BaseModel):
    prompt: str
    timezone: str

# ==============================================================================
# STEP 1: DEFINE THE "TOOLS" FOR THE LLM'S FUNCTION CALLING FEATURE
# These Pydantic models define the structure of the function we want Gemini to call.
# ==============================================================================

# --- Tool Parameter Models ---
# It's good practice to define the parameters for each real tool.
# This helps the LLM generate the correct arguments.

class SendEmailParams(BaseModel):
    recipient: str = Field(description="The email address of the recipient.")
    subject: str = Field(description="The subject line of the email.")
    body: str = Field(description="The content of the email. Can include the placeholder '{PREVIOUS_STEP_RESULT}'.")

class ScrapeWebParams(BaseModel):
    url: str = Field(description="The fully qualified URL to scrape (e.g., 'https://news.ycombinator.com').")
    selector: str = Field(description="A CSS selector to extract specific elements from the page (e.g., '.titleline > a').")

class CallApiParams(BaseModel):
    endpoint: str = Field(description="The API endpoint URL to call.")
    payload: Dict[str, Any] = Field(description="The JSON payload to send with the API request.")

# --- Workflow Step Model ---
class WorkflowStep(BaseModel):
    """A single step in a workflow to be executed."""
    tool_name: Literal["send_email", "scrape_web", "call_api"] = Field(description="The name of the tool to execute for this step.")
    parameters: Dict[str, Any] = Field(description="A dictionary of arguments for the chosen tool (e.g., {'recipient': '...', 'subject': '...'}).")

# --- Schedule Models ---
# These define the different ways a task can be scheduled.

class CronSchedule(BaseModel):
    type: Literal["cron"] = "cron"
    value: str = Field(description="A standard cron expression string, e.g., '0 9 * * 1' for every Monday at 9 AM.")

class DateTimeSchedule(BaseModel):
    type: Literal["datetime"] = "datetime"
    value: str = Field(description="A specific future date and time in ISO 8601 format, e.g., '2024-12-25T09:00:00'.")

class IntervalSchedule(BaseModel):
    type: Literal["interval"] = "interval"
    every: int = Field(description="The number of periods to wait.")
    period: Literal["seconds", "minutes", "hours", "days"] = Field(description="The unit of time for the interval.")




class ScheduleTaskTool(BaseModel):
    """
    Schedules a single task or a chain of tasks to be executed according to a specified schedule.
    This is the primary tool the AI should call in response to a user's request.
    """
    task_name: str = Field(description="A short, descriptive name for the user's overall goal, e.g., 'Scrape and Email HN Headlines'.")
    workflow: list[WorkflowStep] = Field(description="A list of one or more steps to execute in sequence. The output of a step is passed to the next.")
    schedule: Dict[str, Any] = Field(description="A dictionary defining the schedule. Must contain a 'type' ('cron', 'datetime', or 'interval') and other relevant keys based on the type.")
    timezone: str = Field(description="The user's IANA timezone, e.g., 'Asia/Kolkata', 'America/New_York'.")



# ==============================================================================
# Pydantic Model for Reading a Task from the DB (for the /tasks endpoint)
# We will need to update our DB schema to match the new structure later.
# ==============================================================================
class Task(BaseModel):
    id: int
    task_name: str
    workflow: List[Dict[str, Any]]  # The DB will store the workflow as a JSON object
    schedule_details: Dict[str, Any] # The DB will store the schedule as a JSON object
    timezone: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)