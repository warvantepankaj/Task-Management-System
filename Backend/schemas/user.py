from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal, Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["admin", "user"]


class UserResponse(BaseModel):
    # Cleaned up: the stray task-related fields that used to live here
    # (status / complete_by) were leftovers from an earlier copy-paste and
    # never matched any DB column on `users`.
    id: int
    username: str
    email: EmailStr
    role: Literal["admin", "user"]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Literal["admin", "user"]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
