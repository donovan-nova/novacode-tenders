# NovaCode Tender Intelligence — Deployment Guide

## What you have
- **Backend**: Python FastAPI — polls SA OCDS API + scrapes Africa portals, scores with Claude AI
- **Frontend**: React dashboard — filters, detail panel, alerts management
- **Deploy target**: Render.com (both services, free tier)

---

## Step 1 — Push to GitHub

Open PowerShell in the `novacode-tenders` folder:

```powershell
cd path\to\novacode-tenders

git init
git add .
git commit -m "Initial commit: NovaCode Tender Intelligence"

# Create repo on GitHub (go to github.com → New repository → name: novacode-tenders)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/novacode-tenders.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Deploy Backend to Render

1. Go to **render.com** → **New** → **Web Service**
2. Connect your GitHub repo → select `novacode-tenders`
3. Set:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
4. Add Environment Variables:
   - `ANTHROPIC_API_KEY` = your Anthropic API key (from console.anthropic.com)
5. Click **Create Web Service**
6. Copy the URL it gives you e.g. `https://novacode-tenders-api.onrender.com`

---

## Step 3 — Deploy Frontend to Render

1. Go to **render.com** → **New** → **Static Site**
2. Connect same GitHub repo
3. Set:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `build`
4. Add Environment Variables:
   - `REACT_APP_API_URL` = your backend URL from Step 2
5. Click **Create Static Site**

---

## Step 4 — Verify

- Visit your frontend URL — you should see the dashboard
- On first load, the backend auto-syncs all sources
- Check `https://your-api.onrender.com/docs` for the Swagger API docs
- Check `https://your-api.onrender.com/health` for status

---

## Anthropic API Key

Get yours at: https://console.anthropic.com/api-keys

Without it, the app still works using rule-based scoring (keyword matching).
With it, Claude scores each tender against NovaCode's full capability profile.

---

## Local development

```powershell
# Backend
cd backend
pip install -r requirements.txt
copy .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm start
# Opens at http://localhost:3000
```

---

## Data sources

| Source | Type | Coverage | Update frequency |
|--------|------|----------|-----------------|
| SA National Treasury (OCDS API) | Official API | National + Provincial | Daily |
| PPRA Kenya | HTML scraper | Kenya national | Every 6 hours |
| Zambia ZPPA | HTML scraper | Zambia national | Every 6 hours |
| Nigeria BPP | HTML scraper | Nigeria national | Every 6 hours |
| Ghana PPA | HTML scraper | Ghana national | Every 6 hours |

Eskom, Transnet, and additional country scrapers are ready to add in `fetchers.py`.

---

## Phase 2 — Tender document assistant (coming next)

The backend already has a `/api/tenders/{id}/rescore` endpoint.
Phase 2 will add:
- `POST /api/tenders/{id}/analyse` — upload PDF, Claude extracts requirements
- `POST /api/tenders/{id}/draft` — generate compliance checklist + response outline
- NovaCode boilerplate library (company profile, director CVs, capability statements)
