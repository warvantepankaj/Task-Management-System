from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["admin", "user"]

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Literal["admin", "user"]
    created_at: datetime
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED"]
    complete_by: datetime | None
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str

    class Config:
        orm_mode = True
