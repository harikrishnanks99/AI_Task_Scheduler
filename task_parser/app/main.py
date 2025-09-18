import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from google.protobuf.struct_pb2 import Value
from datetime import datetime
import pytz
from fastapi.middleware.cors import CORSMiddleware

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

# --- Robust Converter for Google's ProtoBuf Objects ---
def to_dict(data):
    """
    Recursively converts Google's special MapComposite and RepeatedComposite
    objects into standard Python dictionaries and lists.
    """
    if hasattr(data, "items"):
        return {key: to_dict(value) for key, value in data.items()}
    elif isinstance(data, Value):
        return data.string_value or data.number_value or data.bool_value or None
    elif hasattr(data, "__iter__") and not isinstance(data, str):
        return [to_dict(item) for item in data]
    else:
        return data

# --- Intelligent Schedule Formatter with Defensive Logic (THE FIX) ---
def format_schedule_from_llm(raw_schedule: dict, timezone_str: str) -> dict:
    """
    Takes the raw, flat dictionary from the LLM and intelligently converts it
    into the structured {'type': '...', 'value': '...'} format. This version
    handles non-integer values from the LLM gracefully.
    """
    try:
        user_tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        user_tz = pytz.utc
    
    now_in_user_tz = datetime.now(user_tz)

    # --- NEW, SAFER LOGIC ORDER ---

    # Priority 1: INTERVAL ("every N period") - This is the most distinct.
    if 'every' in raw_schedule and 'period' in raw_schedule:
        print("Formatter: Classified as INTERVAL.")
        return { "type": "interval", "every": int(raw_schedule['every']), "period": raw_schedule['period'] }

    # Priority 2: A time for TODAY ("at 5pm", "at 11:44")
    # We check this before the general datetime block to handle cases like 'day': 'today'.
    elif 'hour' in raw_schedule and 'minute' in raw_schedule and not ('year' in raw_schedule or 'month' in raw_schedule):
        hour_val = raw_schedule.get('hour', 0)
        minute_val = raw_schedule.get('minute', 0)
        if str(hour_val).isdigit() and str(minute_val).isdigit():
            dt_object = now_in_user_tz.replace(
                hour=int(hour_val), minute=int(minute_val),
                second=0, microsecond=0
            )
            print(f"Formatter: Classified as 'today at time' DATETIME: {dt_object.isoformat()}")
            return {"type": "datetime", "value": dt_object.strftime('%Y-%m-%dT%H:%M:%S')}

    # Priority 3: Explicit DATETIME (year, month, or day is present)
    elif 'year' in raw_schedule or 'month' in raw_schedule or 'day' in raw_schedule:
        # Gracefully handle non-integer values by trying to convert them
        try:
            dt_object = datetime(
                year=int(raw_schedule.get('year', now_in_user_tz.year)),
                month=int(raw_schedule.get('month', now_in_user_tz.month)),
                day=int(raw_schedule.get('day', now_in_user_tz.day)),
                hour=int(raw_schedule.get('hour', 0)),
                minute=int(raw_schedule.get('minute', 0))
            )
            print(f"Formatter: Classified as explicit DATETIME: {dt_object.isoformat()}")
            return {"type": "datetime", "value": dt_object.strftime('%Y-%m-%dT%H:%M:%S')}
        except (ValueError, TypeError):
            # If conversion fails (e.g., day='today'), fall through to the safe 'now' default
            print(f"Formatter: Failed to parse explicit date parts, falling back. Parts were: {raw_schedule}")
            pass

    # Priority 4: A recurring CRON schedule
    elif 'day_of_week' in raw_schedule or 'day_of_month' in raw_schedule:
        print("Formatter: Classified as CRON.")
        day_of_week = raw_schedule.get('day_of_week', '*')
        valid_dow = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', '*']
        if not str(day_of_week).isdigit() and str(day_of_week).lower() not in valid_dow:
            day_of_week = '*'
        
        cron_parts = {
            'minute': raw_schedule.get('minute', '0'), 'hour': raw_schedule.get('hour', '*'),
            'day_of_month': raw_schedule.get('day_of_month', '*'), 'month_of_year': raw_schedule.get('month', '*'),
            'day_of_week': day_of_week
        }
        if not str(cron_parts['minute']).isdigit(): cron_parts['minute'] = '*'
        if not str(cron_parts['hour']).isdigit(): cron_parts['hour'] = '*'
        
        cron_str = "{minute} {hour} {day_of_month} {month_of_year} {day_of_week}".format(**cron_parts)
        print(f"  -> Generated CRON string: '{cron_str.strip()}'")
        return {"type": "cron", "value": cron_str.strip()}

    # --- SAFE FALLBACK ---
    else:
        print("Formatter: Ambiguous schedule. Defaulting to a one-time 'run now' DATETIME task.")
        dt_object = now_in_user_tz
        return {"type": "datetime", "value": dt_object.strftime('%Y-%m-%dT%H:%M:%S')}


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
    version="2.2.0",
    lifespan=lifespan
)

# --- Configure CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Gemini Client Configuration ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    gemini_model = genai.GenerativeModel(
        "gemini-1.5-flash",
        system_instruction="You are a helpful assistant that helps users schedule tasks...",
        tools=[schemas.ScheduleTaskTool]
    )
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
            raise HTTPException(status_code=400, detail="Could not understand the request into a schedulable task.")

        function_call_args = response_part.function_call.args
        args_dict = to_dict(function_call_args)
        
        raw_schedule = args_dict.pop('schedule', {})
        formatted_schedule = format_schedule_from_llm(raw_schedule, sanitized_timezone)
        args_dict['schedule'] = formatted_schedule
        
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