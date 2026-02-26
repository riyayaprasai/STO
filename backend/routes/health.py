from flask import Blueprint, jsonify
from config import Config

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "mock_data": Config.USE_MOCK_DATA,
        }
    )
