from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from database.session import get_db
from schemas.auth import (
    RegisterRequest,
    UserLogin,
    RefreshRequest,
    LogoutRequest,
    LoginResponse,
    TokenPair,
)
from services import auth_service

auth_router = APIRouter()


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    """Pull user-agent and originating IP from the request for audit metadata."""
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


@auth_router.post("/register")
def register(data: RegisterRequest, db=Depends(get_db)):
    user, error = auth_service.register_user(
        db, data.username, data.email, data.password, data.role
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {
        "message": "Registered successfully",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "is_active": user["is_active"],
        },
    }


@auth_router.post("/login", summary="User/Admin login", response_model=LoginResponse)
def login(data: UserLogin, request: Request, db=Depends(get_db)):
    ua, ip = _client_meta(request)
    return auth_service.login_user(db, data.email, data.password, user_agent=ua, ip=ip)


@auth_router.post("/auth/refresh", summary="Rotate refresh + access token", response_model=LoginResponse)
def refresh(data: RefreshRequest, request: Request, db=Depends(get_db)):
    ua, ip = _client_meta(request)
    return auth_service.refresh_tokens(db, data.refresh_token, user_agent=ua, ip=ip)


@auth_router.post(
    "/auth/logout",
    summary="Revoke a refresh token",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(data: LogoutRequest, db=Depends(get_db)):
    # Idempotent: unknown / already-revoked tokens still return 204.
    auth_service.logout(db, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
