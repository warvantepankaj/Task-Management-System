from fastapi import FastAPI
from pydantic import BaseModel, EmailStr

# Request models
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "employee"  # Default role is employee, can be overridden by admin

class LoginRequest(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    