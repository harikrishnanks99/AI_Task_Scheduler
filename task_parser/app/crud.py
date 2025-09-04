# task_parser/app/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from . import sql_models, schemas
from sqlalchemy.future import select

async def create_task(db: AsyncSession, task: schemas.TaskDefinition) -> sql_models.Task:
    """
    Creates a new task record in the database.
    """
    # Use .model_dump() which is the Pydantic v2 equivalent of .dict()
    db_task = sql_models.Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_tasks(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[sql_models.Task]:
    """
    Retrieves all task records from the database with pagination.
    """
    result = await db.execute(
        select(sql_models.Task).offset(skip).limit(limit)
    )
    return result.scalars().all()