from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import create_user
from schemas import UserCreate, UserResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and get their API key."""
    try:
        new_user = create_user(db, user.username, user.email)
        return new_user
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        ) 