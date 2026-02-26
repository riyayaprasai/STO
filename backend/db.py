"""
SQLite database for STO. Local file-based SQL — no server required.
Database file: instance/stoopid.db (or DATABASE_PATH from config).
"""
import os
import sqlite3
from contextlib import contextmanager
# Default: local file next to the backend (or set DATABASE_PATH in .env)
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "instance", "stoopid.db"))


def _ensure_dir():
    d = os.path.dirname(DATABASE_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


@contextmanager
def get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Call once at app startup."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                user_id TEXT PRIMARY KEY,
                cash REAL NOT NULL DEFAULT 100000,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                PRIMARY KEY (user_id, symbol),
                FOREIGN KEY (user_id) REFERENCES portfolios(user_id) ON DELETE CASCADE
            )
        """)


# --- Auth helpers ---

def create_user_row(user_id, email, password_hash, created_at):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, created_at),
        )


def get_user_by_email_row(email):
    email = (email or "").strip().lower()
    with get_conn() as conn:
        row = conn.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        return None
    return {"user_id": row["id"], "email": row["email"]}


def get_password_hash_row(email):
    email = (email or "").strip().lower()
    with get_conn() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    return row["password_hash"] if row else None


# --- Portfolio helpers ---

def get_portfolio_row(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT user_id, cash FROM portfolios WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_positions_rows(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, quantity, avg_price FROM positions WHERE user_id = ? AND quantity > 0",
            (user_id,),
        ).fetchall()
    return [{"symbol": r["symbol"], "quantity": r["quantity"], "avg_price": r["avg_price"]} for r in rows]


def create_portfolio_row(user_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolios (user_id, cash, updated_at) VALUES (?, 100000.0, datetime('now'))",
            (user_id,),
        )


def update_portfolio_cash(user_id, cash):
    with get_conn() as conn:
        conn.execute(
            "UPDATE portfolios SET cash = ?, updated_at = datetime('now') WHERE user_id = ?",
            (cash, user_id),
        )


def get_position_row(user_id, symbol):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity, avg_price FROM positions WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        ).fetchone()
    return dict(row) if row else None


def set_position(user_id, symbol, quantity, avg_price):
    with get_conn() as conn:
        if quantity <= 0:
            conn.execute("DELETE FROM positions WHERE user_id = ? AND symbol = ?", (user_id, symbol))
        else:
            conn.execute(
                """
                INSERT INTO positions (user_id, symbol, quantity, avg_price)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, symbol) DO UPDATE SET quantity = excluded.quantity, avg_price = excluded.avg_price
                """,
                (user_id, symbol, quantity, avg_price),
            )
</think>
Fixing portfolio updates: SQLite's INSERT ... ON CONFLICT doesn't correctly update avg_price when adding to a position. Implementing proper position update/insert and delete helpers:
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
StrReplace