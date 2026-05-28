from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ---------- Request models ----------

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


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ---------- Response models ----------

class UserBrief(BaseModel):
    id: int
    email: EmailStr
    role: str
    username: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(TokenPair):
    user: UserBrief
