from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2
from jose import jwt, JWTError
from schemas import user
from dao.user_dao import get_user_by_id
from services.user_service import UserService
from database.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
SECRET_KEY = "TOP_SECRET"  # use env variable in production
ALGORITHM = "HS256"



def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")
        role = payload.get("role")

        if not user_id or not role:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_service = UserService()
        user = user_service.get_user_by_id_endpoint(db, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"]
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
