from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import User
from . import Conflict, Unauthorized


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user: User) -> str:
    s = get_settings()
    payload = {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def user_from_token(db: Session, token: str) -> User:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise Unauthorized("Сессия истекла, войдите заново") from None
    user = db.get(User, user_id)
    if user is None:
        raise Unauthorized("Сессия истекла, войдите заново")
    return user


def register(db: Session, email: str, password: str) -> User:
    if db.scalar(select(User).where(User.email == email)):
        raise Conflict("Пользователь с таким email уже зарегистрирован")
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise Unauthorized("Неверный email или пароль")
    return user
