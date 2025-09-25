# app/auth.py
from fastapi import Request, Depends
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)

def is_admin(user: User | None) -> bool:
    return bool(user and user.role == "Admin")
