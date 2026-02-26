from db import (
    get_portfolio_row,
    get_positions_rows,
    create_portfolio_row,
    update_portfolio_cash,
    get_position_row,
    set_position,
)

# Mock prices for simulation (no real money)
MOCK_PRICES = {
    "AAPL": 178.50,
    "GOOGL": 142.20,
    "MSFT": 415.80,
    "GME": 22.40,
    "AMC": 4.85,
}


def _default_price(symbol):
    return MOCK_PRICES.get(symbol.upper(), 100.0)


def get_market_prices(symbols):
    return {s: _default_price(s) for s in symbols}


def get_or_create_portfolio(user_id):
    row = get_portfolio_row(user_id)
    if not row:
        create_portfolio_row(user_id)
        return {
            "user_id": user_id,
            "cash": 100000.0,
            "positions": [],
            "total_value": 100000.0,
        }
    cash = float(row["cash"])
    positions = get_positions_rows(user_id)
    total_value = cash + sum(
        p["quantity"] * _default_price(p["symbol"]) for p in positions
    )
    return {
        "user_id": user_id,
        "cash": round(cash, 2),
        "positions": positions,
        "total_value": round(total_value, 2),
    }


def get_portfolio_positions(user_id):
    data = get_or_create_portfolio(user_id)
    return {"positions": data.get("positions", [])}


def place_order(user_id, symbol, side, quantity):
    get_or_create_portfolio(user_id)
    row = get_portfolio_row(user_id)
    cash = float(row["cash"])
    price = _default_price(symbol)

    if side == "buy":
        cost = price * quantity
        if cost > cash:
            return {"success": False, "error": "Insufficient cash"}
        current = get_position_row(user_id, symbol)
        if current:
            old_q, old_avg = current["quantity"], current["avg_price"]
            new_q = old_q + quantity
            new_avg = (old_q * old_avg + quantity * price) / new_q
            set_position(user_id, symbol, new_q, new_avg)
        else:
            set_position(user_id, symbol, quantity, price)
        update_portfolio_cash(user_id, cash - cost)
    else:
        current = get_position_row(user_id, symbol)
        if not current:
            return {"success": False, "error": "No position for symbol"}
        q = current["quantity"]
        if quantity > q:
            return {"success": False, "error": "Insufficient shares"}
        update_portfolio_cash(user_id, cash + price * quantity)
        new_q = q - quantity
        set_position(user_id, symbol, new_q, current["avg_price"] if new_q > 0 else 0)

    return {
        "success": True,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "portfolio": get_or_create_portfolio(user_id),
    }
