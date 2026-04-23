from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, generate_api_key
from schemas import AdminUserCreate, UserResponse, UserTierUpdate
from datetime import datetime
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from middleware.admin_auth import verify_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

@router.get("/", response_class=HTMLResponse)
async def admin_panel(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    """Render the admin panel HTML page."""
    await verify_admin(credentials)
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/users", response_model=list[UserResponse])
async def get_users(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get all users."""
    await verify_admin(credentials)
    users = db.query(User).all()
    # Backfill legacy users that were created without an API key
    dirty = False
    for u in users:
        if u.api_key is None:
            u.api_key = generate_api_key()
            dirty = True
        if u.tier is None:
            u.tier = "free"
            dirty = True
    if dirty:
        db.commit()
    return users

@router.post("/users", response_model=UserResponse)
async def create_new_user(
    user: AdminUserCreate,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new user with API key."""
    await verify_admin(credentials)
    # Check if username or email already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create new user
    new_user = User(
        username=user.username,
        email=user.email,
        api_key=generate_api_key(),
        tier=user.tier,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.patch("/users/{user_id}/tier", response_model=UserResponse)
async def update_user_tier(
    user_id: int,
    payload: UserTierUpdate,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Update a user's tier."""
    await verify_admin(credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.tier = payload.tier
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete a user."""
    await verify_admin(credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.post("/logout")
async def logout():
    """Handle logout request."""
    # Return 401 to force browser to clear credentials
    raise HTTPException(
        status_code=401,
        detail="Logged out successfully",
        headers={"WWW-Authenticate": "Basic"}
    ) 