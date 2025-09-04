import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from datetime import datetime

# Import our updated schemas
from . import crud, schemas
from .database import engine, get_db
from .prompts import get_step1_reasoning_prompt, get_step2_formatting_prompt
from celery_worker_code.core.settings import AVAILABLE_TOOLS

# This import works because of the sys.path modification in celery_app.py,
# but it's really meant for the worker. To avoid confusion/IDE errors here,
# we need to define the Task model for the API to use.
# Since we are NOT using a shared directory, we MUST duplicate the model.
# This is a key trade-off of this architecture.
from . import sql_models
from .sql_models import Task as APITaskModel

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(sql_models.Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up and creating database tables...")
    await create_db_and_tables()
    yield
    print("Shutting down...")


app = FastAPI(
    title="AI Task Parser Service (Gemini - 2-Step)",
    description="Parses tasks using a two-step process and saves them to the database.",
    version="1.2.0",
    lifespan=lifespan
)

# --- Gemini Configuration (no changes) ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    raise RuntimeError("GOOGLE_API_KEY environment variable not set.")



@app.get("/")
def read_root():
    return {"status": "AI Task Parser (Gemini - 2-Step) is running"}

# ... (imports and other code remain the same) ...




# ... (lifespan for creating DB tables remains the same) ...
# NOTE: The lifespan function will use `sql_models.Base.metadata.create_all` from its own
# sql_models.py file, which is correct.

# ... (app = FastAPI(...), Gemini config, etc. remain the same) ...

@app.post("/parse-task", response_model=schemas.Task)
async def parse_and_create_task(
    request: schemas.TaskRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        # --- STEP 1 & 2: Get structured components from LLM (logic is the same) ---
        # ... (This part of the code runs the two-step prompt chain as before)
        reasoning_model = genai.GenerativeModel("gemini-2.0-flash")
        prompt1 = get_step1_reasoning_prompt(request.prompt, request.timezone, AVAILABLE_TOOLS)
        response1 = await reasoning_model.generate_content_async(prompt1)
        analysis_text = response1.text

        json_generation_config = genai.GenerationConfig(response_mime_type="application/json", temperature=0.0)
        formatting_model = genai.GenerativeModel("gemini-1.5-flash", generation_config=json_generation_config)
        prompt2 = get_step2_formatting_prompt(analysis_text)
        response2 = await formatting_model.generate_content_async(prompt2)
        llm_output_json = json.loads(response2.text)
        
        # Inject the timezone programmatically
        llm_output_json['timezone'] = request.timezone
        
        # --- VALIDATE the LLM's raw component output using our new schemas ---
        llm_task_def = schemas.TaskDefinition(**llm_output_json)

        # --- CODE-BASED FORMATTING (The New, Robust Logic) ---
        # Start building the dictionary that will be saved to the database.
        final_task_data = llm_task_def.model_dump(exclude={"schedule_details"})
        final_task_data["schedule_details"] = llm_task_def.schedule_details.model_dump()

        if llm_task_def.schedule_details.type == 'datetime':
            # The LLM gave us components, now we build the final string
            dt_components = llm_task_def.schedule_details.value
            dt_object = datetime(
                year=dt_components.year, month=dt_components.month, day=dt_components.day,
                hour=dt_components.hour, minute=dt_components.minute, second=dt_components.second
            )
            # Overwrite the 'value' field with the final, correctly formatted dictionary
            final_task_data['schedule_details']['value'] = { "iso_datetime": dt_object.isoformat() }
            
        # --- SAVE the final, correctly formatted data to the DB ---
        # `final_task_data` is now a dict that perfectly matches our DB schema.
        db_task_model = APITaskModel(**final_task_data)
        db.add(db_task_model)
        await db.commit()
        await db.refresh(db_task_model)
        
        # Return the DB model, which Pydantic will serialize using the `Task` schema
        return db_task_model

    except ValidationError as e:
        raise HTTPException(status_code=500, detail=f"LLM output failed validation: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    

@app.get("/tasks", response_model=list[schemas.Task])
async def read_tasks(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all tasks from the database.
    """
    tasks = await crud.get_tasks(db, skip=skip, limit=limit)
    return tasks