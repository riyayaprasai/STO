#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  STO – start both backend and frontend
#  Usage:  bash start.sh
# ─────────────────────────────────────────────────────────────
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STO – Social Trend Observant"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Backend ────────────────────────────────────────────────────
echo "▶ Installing backend dependencies…"
cd "$ROOT/newsapi2"
pip install -r requirements.txt --quiet

echo ""
echo "▶ Starting backend on http://localhost:8000 …"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────────────────────
echo ""
echo "▶ Installing frontend dependencies…"
cd "$ROOT/frontend"
npm install --silent

echo ""
echo "▶ Starting frontend on http://localhost:3000 …"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Backend  → http://localhost:8000   (API docs: /docs)"
echo "  Frontend → http://localhost:3000"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for both processes; kill both on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
