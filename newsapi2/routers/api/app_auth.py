"""
POST /api/auth/signup
POST /api/auth/login

JWT-based auth endpoints for the STO frontend.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app_auth_utils import create_access_token, hash_password, verify_password
from database import get_db
from models import AppUser, Portfolio

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/auth/signup", response_model=AuthResponse)
def signup(req: AuthRequest, db: Session = Depends(get_db)):
    if len(req.password) < 6:
        raise HTTPException(
            status_code=400,
            detail={"error": "Password must be at least 6 characters."},
        )
    if db.query(AppUser).filter(AppUser.email == req.email).first():
        raise HTTPException(
            status_code=400,
            detail={"error": "Email already in use."},
        )

    user = AppUser(email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    db.flush()   # get user.id without committing yet

    # Seed a fresh portfolio for the new user
    portfolio = Portfolio(user_id=user.id, cash=100_000.0)
    db.add(portfolio)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return AuthResponse(token=token, user=UserOut(id=str(user.id), email=user.email))


@router.post("/auth/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid email or password."},
        )

    token = create_access_token(user.id, user.email)
    return AuthResponse(token=token, user=UserOut(id=str(user.id), email=user.email))
