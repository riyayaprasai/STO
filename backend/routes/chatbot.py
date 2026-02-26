from flask import Blueprint, jsonify, request
from services.chatbot_service import chat

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/message", methods=["POST"])
def message():
    """Send a message to the STOOPID chatbot (preliminary: rule-based)."""
    body = request.get_json() or {}
    user_message = (body.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "message is required"}), 400
    reply = chat(user_message)
    return jsonify({"reply": reply})
