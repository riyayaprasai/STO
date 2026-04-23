"""
JWT-based authentication utilities for the STO frontend API.

These are separate from the existing API-key auth used by /v1/* routes.
Frontend users sign up / log in via email+password and receive a JWT token
that they pass as  Authorization: Bearer <token>  on protected endpoints.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import AppUser

# ── Config ────────────────────────────────────────────────────────────────────

SECRET_KEY: str = os.getenv(
    "JWT_SECRET", "sto-jwt-secret-key-change-in-production-2024"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# ── Crypto ────────────────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_http_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── Token ─────────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str, db: Session) -> Optional[AppUser]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        return db.query(AppUser).filter(AppUser.id == user_id).first()
    except (JWTError, KeyError, ValueError, Exception):
        return None


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def get_optional_app_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_http_bearer),
    db: Session = Depends(get_db),
) -> Optional[AppUser]:
    """Return the AppUser if a valid Bearer token is present, else None."""
    if not credentials:
        return None
    return _decode_token(credentials.credentials, db)


def get_required_app_user(
    user: Optional[AppUser] = Depends(get_optional_app_user),
) -> AppUser:
    """Like get_optional_app_user but raises 401 when no valid token."""
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required. Please log in."},
        )
    return user
