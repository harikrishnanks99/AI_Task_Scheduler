from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Literal, Dict, Any, Union
from datetime import datetime

# --- Input Schemas (no changes) ---
class TaskRequest(BaseModel):
    prompt: str
    timezone: str


# --- Shared Schemas for Task Structure ---
class CronValue(BaseModel):
    minute: str
    hour: str
    day_of_week: str
    day_of_month: str
    month_of_year: str


class LLMDateTimeValue(BaseModel):
    year: int
    month: int
    day: int
    hour: int = 0
    minute: int = 0
    second: int = 0


class IntervalValue(BaseModel):
    every: int
    period: Literal["seconds", "minutes", "hours", "days"]


ScheduleValue = Union[CronValue, LLMDateTimeValue, IntervalValue]


class ScheduleDetails(BaseModel):
    type: Literal["cron", "datetime", "interval"]
    value: ScheduleValue


# --- Pydantic Model for Validating the LLM's raw output ---
class TaskDefinition(BaseModel):
    task_name: str
    tool_to_use: str
    parameters: Dict[str, Any]
    schedule_details: ScheduleDetails
    timezone: str  # Inject this after validation


# --- Pydantic Model for Reading a Task from the DB ---
class Task(BaseModel):
    id: int
    task_name: str
    tool_to_use: str
    parameters: Dict[str, Any]
    schedule_details: Dict[str, Any]  # DB stores final JSON
    timezone: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
