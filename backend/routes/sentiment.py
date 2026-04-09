from flask import Blueprint, jsonify, request
from db import get_db
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
    try:
        with get_db() as conn:
            # Hourly deduplication: skip insert if a row for this symbol
            # was recorded less than 1 hour ago.
            recent = conn.execute(
                """
                SELECT id FROM sentiment_history
                WHERE symbol = ?
                  AND recorded_at > datetime('now', '-1 hour')
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()

            if not recent:
                conn.execute(
                    """
                    INSERT INTO sentiment_history (symbol, score, label, mentions)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        float(data.get("score", 0.5)),
                        data.get("label", "neutral"),
                        int(data.get("mentions", 0)),
                    ),
                )
    except Exception as e:
        # Never block the sentiment endpoint if DB persistence fails.
        print(f"DB INSERT ERROR: {e}")
        pass
    return jsonify(data)


@sentiment_bp.route("/trends", methods=["GET"])
def trends():
    """Time-series sentiment for charts (preliminary: mock)."""
    symbol = request.args.get("symbol", "AAPL").upper()
    days = int(request.args.get("days", 7))
    data = get_sentiment_for_symbol(symbol.upper())
    # Stub trend data for charts
    stub_trend = [
        {"date": f"Day {i}", "score": data.get("score", 0) + (i - 3) * 0.05}
        for i in range(days)
    ]
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT recorded_at, score
                FROM sentiment_history
                WHERE symbol = ?
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                (symbol, days),
            ).fetchall()

        # Keep chart stable during early development.
        if len(rows) >= 2:
            # Reverse so trend is chronological (oldest first) for charts.
            trend = [{"date": row["recorded_at"], "score": row["score"]} for row in reversed(rows)]
        else:
            trend = stub_trend
    except Exception:
        trend = stub_trend

    return jsonify({"symbol": symbol, "trend": trend})
