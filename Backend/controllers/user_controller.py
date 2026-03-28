from fastapi import APIRouter, Depends, HTTPException, Query
from services.user_service import UserService
from database.session import get_db
from utils.security import hash_password, get_current_user
from schemas.user import UserResponse, UserCreate as UserCreateSchema

user_router = APIRouter(prefix="/user", tags=["User"])

@user_router.get("/", summary="Fetch all users")
def fetch_all_users(
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        users = UserService().fetch_all_users(db)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/id/{id}", summary="Get user by ID")
def get_user_by_id(
    id: int,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        user = UserService().get_user_by_id_endpoint(db, id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user by ID: {str(e)}")


@user_router.get("/email/{email}", summary="Get user by email")
def get_user_by_email(
    email: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        user = UserService().get_user_by_email_endpoint(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user by email: {str(e)}")


@user_router.post("/create_user", summary="Create new user")
def new_user(
    user: UserCreateSchema,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        hashed_password = hash_password(user.password)
        created_user = UserService().create_user_endpoint(
            db, user.username, user.email, hashed_password, user.role
        )
        return created_user
    except Exception as e:
        if "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


@user_router.get("/paginated", summary="Fetch users with pagination")
def fetch_all_users_paginated(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of users per page"),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        users, total = UserService.fetch_all_users_paginated(db, page, page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
            "users": users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")
