from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, func
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String, index=True)
    workflow = Column(JSON)  # Stores the list of steps for the task
    schedule_details = Column(JSON)
    timezone = Column(String)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())