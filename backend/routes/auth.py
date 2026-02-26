from flask import Blueprint, jsonify, request
from services.auth_service import (
    create_user,
    verify_user,
    encode_token,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new user."""
    body = request.get_json() or {}
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    user, err = create_user(email, password)
    if err:
        return jsonify({"error": err}), 400
    token = encode_token(user["user_id"])
    return jsonify({
        "token": token,
        "user": {"id": user["user_id"], "email": user["email"]},
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Log in; returns token and user."""
    body = request.get_json() or {}
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    user, err = verify_user(email, password)
    if err:
        return jsonify({"error": err}), 401
    token = encode_token(user["user_id"])
    return jsonify({
        "token": token,
        "user": {"id": user["user_id"], "email": user["email"]},
    })
