# STO — Free Deployment Guide

> Deploy the full STO application for **$0/month** using Render (backend) + Vercel (frontend) + Groq (AI).

---

## Deployment Architecture

```
┌─────────────────────────┐     ┌─────────────────────────┐
│    Vercel (Free)        │     │    Render (Free)         │
│    Frontend (Next.js)   │────▶│    Backend (FastAPI)     │
│    Always-on CDN        │     │    Spins down after 15m  │
│    vercel.app domain    │     │    onrender.com domain   │
└─────────────────────────┘     └──────────┬──────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │ Groq (Free) │
                                    │ LLM API     │
                                    │ llama-3.1   │
                                    └─────────────┘
```

---

## Prerequisites

1. **GitHub account** — Push your STO code to a GitHub repo
2. **Vercel account** — Sign up free at [vercel.com](https://vercel.com)
3. **Render account** — Sign up free at [render.com](https://render.com)
4. **Groq account** — Sign up free at [console.groq.com](https://console.groq.com) (for AI tab)

---

## Step 1: Push to GitHub

```bash
cd /Users/pratyushkhanal/Downloads/STO-repo
git init
git add .
git commit -m "Initial commit: STO platform"
git remote add origin https://github.com/YOUR_USERNAME/STO-repo.git
git push -u origin main
```

---

## Step 2: Deploy Backend on Render

### Option A: One-Click via Blueprint

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` and set up the service

### Option B: Manual Setup

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click **"New"** → **"Web Service"**
3. Connect your GitHub repo
4. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `sto-backend` |
| **Root Directory** | `newsapi2` |
| **Runtime** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

5. Add **Environment Variables**:

| Key | Value |
|-----|-------|
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | (choose a strong password) |
| `JWT_SECRET` | (generate: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `GROQ_API_KEY` | (from [console.groq.com/keys](https://console.groq.com/keys)) |
| `PYTHON_VERSION` | `3.11.0` |

6. Click **"Create Web Service"**

7. Wait for the build to complete (~3–5 minutes)

8. Note your backend URL: `https://sto-backend.onrender.com`

### ⚠️ Free Tier Limitations
- **Cold starts:** Service spins down after 15 min of inactivity. First request after idle takes ~30 seconds.
- **SQLite persistence:** The filesystem is **ephemeral** — database resets on each deploy. Articles will be re-fetched on startup.
- **750 hours/month:** More than enough for a single service running 24/7.

---

## Step 3: Get Groq API Key (Free)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in
3. Go to **API Keys** → **Create API Key**
4. Copy the key
5. Add it as `GROQ_API_KEY` in your Render environment variables

**Groq free tier limits:**
- 14,400 requests/day
- 30 requests/minute
- Models: llama-3.1-8b-instant (fast), llama-3.1-70b-versatile (better quality)

---

## Step 4: Deploy Frontend on Vercel

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click **"Add New…"** → **"Project"**
3. **Import** your GitHub repo
4. Configure:

| Setting | Value |
|---------|-------|
| **Framework Preset** | Next.js (auto-detected) |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `.next` (default) |

5. Add **Environment Variable**:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://sto-backend.onrender.com` |

   ⚠️ Replace `sto-backend` with your actual Render service name!

6. Click **"Deploy"**

7. Wait for build (~1–2 minutes)

8. Your app is live at: `https://your-project.vercel.app`

---

## Step 5: Verify Deployment

### Backend Health Check
```bash
curl https://sto-backend.onrender.com/api/health
# Expected: {"status":"ok","mock_data":false,"recent_articles":...}
```

### Frontend
Visit `https://your-project.vercel.app` — you should see the STO dashboard.

### Test the Full Flow
1. Sign up for an account
2. Search a ticker (AAPL)
3. Check sentiment, news, SEC filings
4. Try the AI Analyst tab (uses Groq)
5. Practice trading

---

## What Changed for Deployment

### Files Created
| File | Purpose |
|------|---------|
| `newsapi2/Procfile` | Tells Render how to start the backend |
| `render.yaml` | Render blueprint for one-click deploy |

### Files Modified
| File | Change |
|------|--------|
| `newsapi2/services/llm_analyst.py` | Added Groq API support (auto-detects via `GROQ_API_KEY` env var) |
| `frontend/lib/api.ts` | Fixed default API URL from port 5000 → 8000 |

### How the LLM Provider Works
```
if GROQ_API_KEY is set:
    → Use Groq cloud API (llama-3.1-8b-instant)
    → OpenAI-compatible SSE streaming
else:
    → Use local Ollama (llama3.2:3b)
    → Same as before (localhost:11434)
```

No other code changes needed. The system auto-detects the environment.

---

## Environment Variable Summary

### Render (Backend)
| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_USERNAME` | Yes | Admin panel login |
| `ADMIN_PASSWORD` | Yes | Admin panel password |
| `JWT_SECRET` | Yes | JWT signing key (generate a random 32-char string) |
| `GROQ_API_KEY` | Recommended | Enables AI Analyst tab in production |
| `PYTHON_VERSION` | Recommended | Set to `3.11.0` for compatibility |

### Vercel (Frontend)
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | **Yes** | Full URL to your Render backend (e.g., `https://sto-backend.onrender.com`) |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Frontend shows "Loading..." forever | Backend URL wrong or backend is cold | Check `NEXT_PUBLIC_API_URL` env var. Wait 30s for cold start. |
| CORS errors in browser console | Backend not configured for Vercel domain | The backend already allows `*` origins — this should work. If not, check Render logs. |
| AI tab shows "Error" | `GROQ_API_KEY` not set or invalid | Add/update the key in Render env vars and redeploy. |
| "mock_data: true" on health check | Backend just started, articles loading | Wait 2-3 minutes for initial RSS fetch, or hit `POST /api/refresh`. |
| Database resets after each deploy | Render free tier has ephemeral filesystem | This is expected. Articles re-fetch on startup. User accounts reset on deploy. |
| Build fails on Render | Missing Python version or dependency | Set `PYTHON_VERSION=3.11.0`. Check `requirements.txt` for compatibility. |

---

## Upgrading Later

| Upgrade | Cost | Benefit |
|---------|------|---------|
| Render Starter ($7/mo) | $7/mo | No cold starts, persistent disk |
| Render PostgreSQL ($0) | Free | 256MB managed PostgreSQL — data survives redeploys |
| Vercel Pro ($20/mo) | $20/mo | Higher limits, team features |
| Groq paid tier | Usage-based | Higher rate limits, more models |
| Custom domain | ~$12/yr | Your own `.com` domain on Vercel |
