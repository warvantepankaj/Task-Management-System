from dao.user_dao import create_user, get_user_by_email
from utils.security import hash_password, verify_password
from core.jwt import create_access_token

def register_user(conn, username, email, password, role):
    existing_user = get_user_by_email(conn, email)
    if existing_user:
        return None, "Email already registered"
    
    hashed = hash_password(password)
    user = create_user(conn, username, email, hashed, role)
    return user, None

def login_user(conn, email, password):
    user = get_user_by_email(conn, email)
    if not user or not verify_password(password, user["password_hash"]):  # Assuming password_hash is index 3
        return None, "Invalid credentials"
    
    token = create_access_token({"user_id": user["id"], "email": user["email"]})
    return token, None
