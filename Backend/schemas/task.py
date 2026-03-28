from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    assigned_to: int = Field(..., gt=0)
    due_date: date
    status: TaskStatus = TaskStatus.PENDING

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[date]

class TaskStatusUpdate(BaseModel):
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED"]

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED"]
    due_date: Optional[date]
    assigned_to: int
    assigned_by: int
    created_at: datetime
    class Config:
        from_attributes = True

class TaskUpdateAdmin(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status :Optional[Literal["PENDING", "IN_PROGRESS", "COMPLETED"]] = None
    due_date: Optional[date] = None
    assigned_to: Optional[int] = None
