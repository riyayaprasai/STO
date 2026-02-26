from flask import Blueprint, jsonify, request
from auth_middleware import get_current_user_id
from services.trading_service import (
    get_or_create_portfolio,
    get_portfolio_positions,
    place_order,
    get_market_prices,
)

trading_bp = Blueprint("trading", __name__)


def _require_user():
    user_id = get_current_user_id()
    if not user_id:
        return None, jsonify({"error": "Login required"}), 401
    return user_id, None, None


@trading_bp.route("/portfolio", methods=["GET"])
def portfolio():
    """Get or create virtual portfolio for the current user."""
    out = _require_user()
    if out[0] is None:
        return out[1], out[2]
    user_id = out[0]
    data = get_or_create_portfolio(user_id)
    return jsonify(data)


@trading_bp.route("/portfolio/positions", methods=["GET"])
def positions():
    """List positions in the current user's portfolio."""
    out = _require_user()
    if out[0] is None:
        return out[1], out[2]
    user_id = out[0]
    data = get_portfolio_positions(user_id)
    return jsonify(data)


@trading_bp.route("/portfolio/order", methods=["POST"])
def order():
    """Place a simulated buy/sell order for the current user."""
    out = _require_user()
    if out[0] is None:
        return out[1], out[2]
    user_id = out[0]
    body = request.get_json() or {}
    symbol = (body.get("symbol") or "").upper()
    side = (body.get("side") or "buy").lower()
    quantity = int(body.get("quantity", 0))
    if not symbol or side not in ("buy", "sell") or quantity <= 0:
        return jsonify({"error": "Invalid symbol, side, or quantity"}), 400
    data = place_order(user_id, symbol=symbol, side=side, quantity=quantity)
    return jsonify(data)


@trading_bp.route("/prices", methods=["GET"])
def prices():
    """Current mock prices for symbols (for simulation). Public."""
    symbols = request.args.get("symbols", "AAPL,GOOGL,MSFT,GME,AMC")
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    data = get_market_prices(sym_list)
    return jsonify(data)
