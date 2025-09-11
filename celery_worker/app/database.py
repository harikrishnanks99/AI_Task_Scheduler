import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a synchronous DB driver for Celery
SYNC_DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "")

engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()