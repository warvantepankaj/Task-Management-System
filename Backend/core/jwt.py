from datetime import datetime, timedelta
from jose import jwt, JWTError

SECRET_KEY = "TOP_SECRET" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    """
    Create a JWT token
    :param data: dictionary with payload, e.g., {"user_id": 1, "role": "USER"}
    :param expires_delta: expiration time in minutes
    :return: JWT token as string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decode_token(token: str):
    """
    Decode a JWT token
    :param token: JWT string
    :return: payload dict if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
