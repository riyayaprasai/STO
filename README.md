# STO — Social Trend Observant

A friendly, AI-powered platform that observes social trends: it evaluates and quantifies sentiment in real time from social media (Reddit, Twitter) and news, and offers a risk-free practice trading environment for everyday investors.

## Features

- **Sentiment Analysis Dashboard** — Real-time market sentiment from social media using NLP
- **Simulated Trading** — Virtual portfolios to test strategies with no financial risk
- **Chatbot Interface** — Natural language queries for insights
- **Visualization** — Trends, portfolio performance, and sentiment charts

## Tech Stack

| Layer   | Stack                    |
|--------|--------------------------|
| Frontend | Next.js, Tailwind CSS   |
| Backend  | FastAPI, SQLite (local) |
| APIs     | Reddit (PRAW), Twitter, NewsAPI |
| ML       | Hugging Face (e.g. FinBERT) |

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+

### Running the Application

Use the provided `start.sh` script to run both backend and frontend:

```bash
bash start.sh
```

This will:
- Install backend dependencies and start the FastAPI server on `http://localhost:8000`
- Install frontend dependencies and start the Next.js dev server on `http://localhost:3000`

### Manual Setup (Alternative)

#### Backend

The backend uses **SQLite** — a local, file-based SQL database. No database server needed; data is stored in `newsapi2/instance/stoopid.db`.

```bash
cd newsapi2
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API runs at `http://localhost:8000` (API docs: `/docs`).

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:3000`.

### Environment

- **Backend** (`backend/.env`): `DATABASE_PATH` (optional; default `backend/instance/stoopid.db`), `SECRET_KEY`, `REDDIT_*`, `TWITTER_*`, `NEWSAPI_KEY` (optional for live models).
- **Frontend** (`frontend/.env.local`): `NEXT_PUBLIC_API_URL=http://localhost:5000`.

Without API keys, the app uses mock data for development.

## Project Structure

```
stoopid/
├── backend/          # Flask API, sentiment, simulation, DB
├── frontend/         # Next.js app (dashboard, trading, chatbot)
└── README.md
```

**STO** stands for **Social Trend Observant** — we help you see what people are saying about the market so you can stay informed.

## License

Academic project — Senior Seminar (CSCI-411-01).
