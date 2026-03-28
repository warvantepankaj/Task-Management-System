from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from database.session import get_db
from services.auth_service import register_user, login_user
from services.user_service import UserService
from fastapi import Request
from schemas.auth import RegisterRequest, LoginRequest, UserLogin
from utils.security import verify_password
from core.jwt import create_access_token

auth_router = APIRouter()

# Routes
@auth_router.post("/register")
def register(data: RegisterRequest, db=Depends(get_db)):
    user, error = register_user(db, data.username, data.email, data.password, data.role)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],   # <-- critical
            "is_active": user["is_active"]
        }
    }

@auth_router.post("/login", summary="User/Admin login")
def login_user(data: UserLogin, db=Depends(get_db)):
    user = UserService().get_user_by_email_endpoint(db, data.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_payload = {
        "user_id": user["id"],
        "role": user["role"]
    }

    access_token = create_access_token(token_payload)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "username":user["username"]
        }
    }


