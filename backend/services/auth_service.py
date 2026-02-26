import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from config import Config
from db import (
    create_user_row,
    get_user_by_email_row,
    get_password_hash_row,
)


def _hash_password(password):
    return generate_password_hash(password, method="scrypt:32768:8:1")


def _verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def create_user(email, password):
    email = (email or "").strip().lower()
    if not email or not password or len(password) < 6:
        return None, "Email and password required; password at least 6 characters"
    if get_user_by_email_row(email):
        return None, "Email already registered"
    user_id = str(uuid.uuid4())
    password_hash = _hash_password(password)
    create_user_row(user_id, email, password_hash, datetime.utcnow().isoformat())
    return {"user_id": user_id, "email": email}, None


def get_user_by_email(email):
    row = get_user_by_email_row(email)
    if not row:
        return None
    return {"user_id": row["user_id"], "email": row["email"]}


def get_password_hash_for_user(email):
    return get_password_hash_row(email)


def verify_user(email, password):
    user = get_user_by_email(email)
    if not user:
        return None, "Email not found"
    pwd_hash = get_password_hash_for_user(email)
    if not pwd_hash or not _verify_password(pwd_hash, password):
        return None, "Invalid password"
    return user, None


def encode_token(user_id):
    token = jwt.encode(
        {"sub": user_id},
        Config.SECRET_KEY,
        algorithm="HS256",
    )
    return token if isinstance(token, str) else token.decode("utf-8")


def decode_token(token):
    if not token:
        return None
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None
