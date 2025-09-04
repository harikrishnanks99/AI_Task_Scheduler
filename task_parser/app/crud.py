from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import sql_models, schemas

async def create_task(db: AsyncSession, task_data: schemas.ScheduleTaskTool) -> sql_models.Task:
    """
    Creates a new task record in the database from the structured data
    provided by the Function Calling LLM.
    """
    # Convert the Pydantic models for the workflow and schedule into plain dictionaries
    # so they can be stored in the JSON columns of our database.
    workflow_dict = [step.model_dump() for step in task_data.workflow]
    schedule_dict = task_data.schedule

    # Create the SQLAlchemy Task instance, mapping the fields correctly.
    db_task = sql_models.Task(
        task_name=task_data.task_name,
        workflow=workflow_dict,
        schedule_details=schedule_dict,
        timezone=task_data.timezone
    )
    
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_tasks(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[sql_models.Task]:
    """
    Retrieves all task records from the database with pagination.
    This function remains unchanged and will work correctly with the new schema.
    """
    result = await db.execute(
        select(sql_models.Task).offset(skip).limit(limit)
    )
    return result.scalars().all()