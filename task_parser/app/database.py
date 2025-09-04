# task_parser/app/database.py

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL)

# async_sessionmaker is the new, preferred way for session creation in SQLAlchemy 2.0
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncSession:
    """Dependency to get an async database session."""
    async with async_session_maker() as session:
        yield session