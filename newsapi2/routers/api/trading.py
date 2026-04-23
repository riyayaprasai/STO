"""
GET  /api/trading/portfolio              – user's portfolio (cash + positions + total value)
GET  /api/trading/portfolio/positions   – list of positions
POST /api/trading/portfolio/order       – place a buy or sell order
GET  /api/trading/prices                – simulated current prices

Prices are deterministic-random: they vary ±4 % from a base price and rotate
once per hour, so they look live without needing an external API.
"""
import random
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app_auth_utils import get_required_app_user
from database import get_db
from models import AppUser, Portfolio, Position

router = APIRouter()

# ── Simulated prices ──────────────────────────────────────────────────────────

_BASE_PRICES: dict[str, float] = {
    "AAPL":  175.50,
    "GOOGL": 170.25,
    "MSFT":  380.00,
    "GME":    15.75,
    "AMC":     4.85,
    "NVDA":  450.00,
    "TSLA":  245.00,
    "META":  480.00,
    "AMZN":  185.00,
    "NFLX":  620.00,
}


def _get_price(symbol: str) -> float:
    """Return a deterministic-random price that changes once per hour."""
    base = _BASE_PRICES.get(symbol.upper(), 100.0)
    # Seed rotates per (UTC date-hour, symbol) so price shifts each hour
    seed = int(datetime.utcnow().strftime("%Y%m%d%H")) + abs(hash(symbol.upper())) % 100_000
    rng = random.Random(seed)
    variation = rng.uniform(-0.04, 0.04)
    return round(base * (1 + variation), 2)


# ── Portfolio helpers ─────────────────────────────────────────────────────────

def _get_or_create_portfolio(user_id: int, db: Session) -> Portfolio:
    port = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not port:
        port = Portfolio(user_id=user_id, cash=100_000.0)
        db.add(port)
        db.commit()
        db.refresh(port)
    return port


def _build_portfolio_response(user: AppUser, port: Portfolio, db: Session) -> dict:
    positions: List[Position] = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.quantity > 0)
        .all()
    )
    positions_value = sum(
        p.quantity * _get_price(p.symbol) for p in positions
    )
    return {
        "user_id": str(user.id),
        "cash": round(port.cash, 2),
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_price": round(p.avg_price, 2),
            }
            for p in positions
        ],
        "total_value": round(port.cash + positions_value, 2),
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    symbol: str
    side: str   # "buy" | "sell"
    quantity: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/trading/portfolio")
def get_portfolio(
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_required_app_user),
):
    port = _get_or_create_portfolio(user.id, db)
    return _build_portfolio_response(user, port, db)


@router.get("/trading/portfolio/positions")
def get_positions(
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_required_app_user),
):
    positions: List[Position] = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.quantity > 0)
        .all()
    )
    return {
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_price": round(p.avg_price, 2),
            }
            for p in positions
        ]
    }


@router.post("/trading/portfolio/order")
def place_order(
    req: OrderRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_required_app_user),
):
    sym = req.symbol.upper().strip()
    side = req.side.lower()

    if side not in ("buy", "sell"):
        raise HTTPException(
            status_code=400,
            detail={"error": "side must be 'buy' or 'sell'"},
        )
    if req.quantity < 1:
        raise HTTPException(
            status_code=400,
            detail={"error": "quantity must be at least 1"},
        )

    price = _get_price(sym)
    cost = price * req.quantity

    port = _get_or_create_portfolio(user.id, db)
    position = db.query(Position).filter(
        Position.user_id == user.id, Position.symbol == sym
    ).first()

    if side == "buy":
        if port.cash < cost:
            return {
                "success": False,
                "error": f"Insufficient cash. Need ${cost:,.2f} but you only have ${port.cash:,.2f}.",
            }
        # Deduct cash and update / create position
        port.cash -= cost
        if position:
            # Update average price
            total_qty = position.quantity + req.quantity
            position.avg_price = (
                (position.avg_price * position.quantity + price * req.quantity)
                / total_qty
            )
            position.quantity = total_qty
        else:
            position = Position(
                user_id=user.id,
                symbol=sym,
                quantity=req.quantity,
                avg_price=price,
            )
            db.add(position)

    else:  # sell
        if not position or position.quantity < req.quantity:
            owned = position.quantity if position else 0
            return {
                "success": False,
                "error": f"You only own {owned} shares of {sym}.",
            }
        position.quantity -= req.quantity
        port.cash += cost

    db.commit()
    db.refresh(port)

    return {
        "success": True,
        "portfolio": _build_portfolio_response(user, port, db),
    }


@router.get("/trading/prices")
def get_prices(
    symbols: str = Query(..., description="Comma-separated ticker symbols, e.g. AAPL,MSFT"),
):
    tickers = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return {sym: _get_price(sym) for sym in tickers}
