from flask import Blueprint, jsonify, request
from config import Config
from services.sentiment_service import get_sentiment_overview, get_sentiment_for_symbol

sentiment_bp = Blueprint("sentiment", __name__)


@sentiment_bp.route("/overview", methods=["GET"])
def overview():
    """Aggregate sentiment across tracked symbols/sources."""
    data = get_sentiment_overview()
    return jsonify(data)


@sentiment_bp.route("/symbol/<symbol>", methods=["GET"])
def by_symbol(symbol):
    """Sentiment for a specific ticker (e.g. AAPL, GME)."""
    symbol = symbol.upper()
    data = get_sentiment_for_symbol(symbol)
    return jsonify(data)


@sentiment_bp.route("/trends", methods=["GET"])
def trends():
    """Time-series sentiment for charts (preliminary: mock)."""
    symbol = request.args.get("symbol", "AAPL")
    days = int(request.args.get("days", 7))
    data = get_sentiment_for_symbol(symbol.upper())
    # Stub trend data for charts
    trend = [
        {"date": f"Day {i}", "score": data.get("score", 0) + (i - 3) * 0.05}
        for i in range(days)
    ]
    return jsonify({"symbol": symbol, "trend": trend})
