from flask import request
from services.auth_service import decode_token


def get_current_user_id():
    """Extract user id from Authorization: Bearer <token>. Returns None if missing/invalid."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    return decode_token(token)
