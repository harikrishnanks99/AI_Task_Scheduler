# task_parser/app/main.py

import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from google.protobuf.struct_pb2 import Value
import json

# --- Local Imports ---
from . import crud, schemas, sql_models
from .database import engine, get_db

# --- Timezone Sanitization Map ---
TIMEZONE_ABBREVIATION_MAP = {
    "IST": "Asia/Kolkata", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
    "MST": "America/Denver", "MDT": "America/Denver", "CST": "America/Chicago",
    "CDT": "America/Chicago", "EST": "America/New_York", "EDT": "America/New_York",
    "GMT": "Etc/GMT", "UTC": "UTC",
}


def format_schedule_from_llm(raw_schedule: dict) -> dict:
    """
    Takes the raw, flat dictionary from the LLM and converts it into the
    structured {'type': '...', 'value': '...'} format our system expects.
    """
    # Infer DATETIME if year, month, or day are present
    if 'year' in raw_schedule or 'month' in raw_schedule or 'day' in raw_schedule:
        now = datetime.now()
        # Use provided values, but default to current year/month/day if missing
        dt_object = datetime(
            year=raw_schedule.get('year', now.year),
            month=raw_schedule.get('month', now.month),
            day=raw_schedule.get('day', now.day),
            hour=int(raw_schedule.get('hour', 0)),
            minute=int(raw_schedule.get('minute', 0))
        )
        return {"type": "datetime", "value": dt_object.isoformat()}

    # Infer INTERVAL if 'every' and 'period' are present
    elif 'every' in raw_schedule and 'period' in raw_schedule:
        return {
            "type": "interval",
            "every": int(raw_schedule['every']),
            "period": raw_schedule['period']
        }

    # Infer CRON for everything else (e.g., just hour/minute)
    else:
        # Default to "every day" if not specified otherwise
        cron_str = "{minute} {hour} * * *".format(
            minute=int(raw_schedule.get('minute', 0)) if str(raw_schedule.get('minute')).isdigit() else '*',
            hour=int(raw_schedule.get('hour', 0)) if str(raw_schedule.get('hour')).isdigit() else '*'
        )
        return {"type": "cron", "value": cron_str}


def to_dict(data):
    """
    Recursively converts Google's MapComposite and RepeatedComposite
    objects into standard Python dictionaries and lists.
    """
    if hasattr(data, "items"):  # This checks if it's dict-like (e.g., MapComposite)
        return {key: to_dict(value) for key, value in data.items()}
    elif isinstance(data, Value): # Handles simple protobuf Value objects
        return data.string_value or data.number_value or data.bool_value or None
    elif hasattr(data, "__iter__") and not isinstance(data, str): # This checks if it's list-like
        return [to_dict(item) for item in data]
    else:
        return data



# --- Database Setup & Lifespan Event Handler ---
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(sql_models.Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up and creating database tables for workflow schema...")
    await create_db_and_tables()
    yield
    print("Shutting down...")

# --- FastAPI Application Initialization ---
app = FastAPI(
    title="AI Task Parser Service (Function Calling)",
    description="Parses tasks using Gemini's native Function Calling and saves them as workflows.",
    version="2.1.0", # Version bump for modern architecture
    lifespan=lifespan
)

# --- Gemini Client Configuration for Function Calling ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

 
    gemini_model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction="You are a helpful assistant that helps users schedule tasks by using the provided `ScheduleTaskTool` tool. You can handle single or multi-step tasks (workflows).",
        tools=[schemas.ScheduleTaskTool] # Pass the Pydantic class directly
    )
    # --- END ---

except KeyError:
    raise RuntimeError("GOOGLE_API_KEY environment variable not set.")
except Exception as e:
    print(f"!!! FATAL ERROR during Gemini model initialization: {e} !!!")
    raise

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "AI Task Parser (Function Calling) is running"}

@app.post("/parse-task", response_model=schemas.Task)
async def parse_and_create_task(
    request: schemas.TaskRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        sanitized_timezone = TIMEZONE_ABBREVIATION_MAP.get(request.timezone.upper(), request.timezone)
        user_prompt = f"{request.prompt} (The user's local timezone is {sanitized_timezone})"
        
        response = await gemini_model.generate_content_async(user_prompt)
        
        response_part = response.candidates[0].content.parts[0]
        if not response_part.function_call:
            raise HTTPException(status_code=400, detail="Could not understand the request into a schedulable task. Please be more specific about the task and schedule.")

        function_call_args = response_part.function_call.args

        args_dict = to_dict(function_call_args)

        # 1. Pop the raw schedule dict out of the main arguments
        raw_schedule = args_dict.pop('schedule', {})
        
        # 2. Format it into the structured format our system needs
        formatted_schedule = format_schedule_from_llm(raw_schedule)
        
        # 3. Add the formatted schedule back into the main data object
        args_dict['schedule'] = formatted_schedule

        # args_dict = json.loads(json.dumps(function_call_args))
        
        validated_task_data = schemas.ScheduleTaskTool(**args_dict)
        
        db_task_model = await crud.create_task(db=db, task_data=validated_task_data)
        
        print(f"Successfully created workflow task #{db_task_model.id} ('{db_task_model.task_name}')")
        return db_task_model

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"The LLM's output could not be validated. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in /parse-task: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while parsing the task.")

@app.get("/tasks", response_model=list[schemas.Task])
async def read_tasks(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tasks = await crud.get_tasks(db, skip=skip, limit=limit)
    return tasks