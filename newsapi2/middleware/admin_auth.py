from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

security = HTTPBasic()

def get_admin_credentials():
    """Get admin credentials from environment variables."""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_password:
        raise ValueError("ADMIN_PASSWORD environment variable is not set")
    
    return admin_username, admin_password

async def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials."""
    admin_username, admin_password = get_admin_credentials()
    
    is_username_correct = secrets.compare_digest(
        credentials.username.encode("utf8"), 
        admin_username.encode("utf8")
    )
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf8"), 
        admin_password.encode("utf8")
    )
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

def admin_required(func):
    """Decorator to require admin authentication for routes."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        
        if not request:
            raise HTTPException(status_code=500, detail="Request object not found")
        
        credentials = await security(request)
        await verify_admin(credentials)
        return await func(*args, **kwargs)
    
    return wrapper 