# Triage15 — Railway Cloud Deployment Guide

This document outlines the exact procedure for deploying **Triage15** to [Railway](https://railway.app) using the root-level multi-stage Dockerfile and persistent volume storage for SQLite.

---

## 1. Architecture & Deployment Overview

Triage15 is deployed as a single-container service containing:
1. **React 19 + TypeScript + Vite frontend**: Compiled to static assets in Stage 1 of the Dockerfile and served by FastAPI at the root (`/`) with SPA client-side routing fallback.
2. **FastAPI backend**: Operates all `/api` endpoints, Swagger/OpenAPI documentation (`/docs`, `/openapi.json`), WebSocket/SSE/polling channels, and background workers.
3. **SQLite database with WAL mode**: Stored on a Railway persistent volume mounted at `/data/triage15.db`.
4. **Single-Worker / Single-Replica Execution**: The in-process `DispatchCoordinator` and `expiration_loop` require a single worker process (`--workers 1`) and a single deployment replica (`1 instance`).

---

## 2. Prerequisites

- A [Railway](https://railway.app) account.
- Access to the GitHub repository: `https://github.com/anveshr312-bit/Triage15.git` (or your fork).
- Railway CLI (optional, but convenient).

---

## 3. Step-by-Step Railway Deployment Instructions

### Step 3.1: Create a New Project on Railway
1. Log into your [Railway Dashboard](https://railway.app/dashboard).
2. Click **"+ New Project"**.
3. Select **"Deploy from GitHub repo"**.
4. Select `anveshr312-bit/Triage15` (or your cloned repository).

### Step 3.2: Configure the Service Build Settings
Railway automatically detects the root-level `Dockerfile`.
1. In your project canvas, click on the newly created service.
2. Navigate to the **"Settings"** tab.
3. Verify:
   - **Build**: Uses `Dockerfile` (located at repository root `/`).
   - **Root Directory**: `/` (leave empty or `/`).
   - **Restart Policy**: `On failure` (Max retries: 10).

### Step 3.3: Attach a Persistent Volume (`/data`)
SQLite requires persistent disk storage across restarts and redeployments.
1. In the service settings, navigate to the **"Volumes"** section (or click **"+ New"** > **"Volume"**).
2. Click **"Add Volume"**.
3. Set the **Mount Path** to:
   ```text
   /data
   ```
4. Click **"Save"** or **"Attach"**.
> **Important**: All SQLite database files (`triage15.db`, `triage15.db-wal`, `triage15.db-shm`) reside inside `/data`. Without this volume, data will reset on every redeployment.

### Step 3.4: Configure Environment Variables
Navigate to the **"Variables"** tab and add the following configuration:

| Variable | Recommended Production Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:////data/triage15.db` | Path to persistent SQLite database on the volume. |
| `ENVIRONMENT` | `production` | Sets application mode to production. |
| `ALLOW_DATABASE_RESET` | `false` | Blocks destructive database resets via CLI/seed. |
| `CORS_ORIGINS` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | Allowed origin for CORS (or comma-separated URLs). |
| `PORT` | `8000` | (Injected automatically by Railway runtime). |
| `OFFER_TTL_SECONDS` | `300` | Mentor assignment acceptance TTL (5 minutes). |

> **Note on CORS**: Because the compiled React frontend is served by FastAPI from the **same origin**, CORS restrictions do not block browser requests from the UI. Setting `CORS_ORIGINS` restricts external API consumers.

### Step 3.5: Configure Health Check
1. Under **"Settings"** > **"Healthcheck"**:
2. Set **Healthcheck Path** to:
   ```text
   /api/health
   ```
3. Set **Healthcheck Timeout**: `15` seconds.
4. Expected Response: Status `200 OK` with JSON payload:
   ```json
   {
     "status": "ok",
     "mode": "demonstration prototype; synthetic profiles; authoritative server clock",
     "auth_notice": "X-Demo-Student-ID is a prototype identity switcher for demonstration, not secure authentication",
     "database": "connected"
   }
   ```

### Step 3.6: Generate Domain & Deploy
1. Navigate to the **"Networking"** section in **Settings**.
2. Click **"Generate Domain"** to get a public URL (e.g., `https://triage15-production.up.railway.app`).
3. If not automatically deployed, click **"Deploy"**.

---

## 4. Concurrency & Replicas Constraint

> [!WARNING]
> **Do not scale beyond 1 replica.**
> Triage15 uses an in-process, asynchronous dispatch coordinator (`asyncio.Lock()`) and background task (`expiration_loop`) for real-time 15-minute slot allocation, offer expiration, and automatic reassignment.
> Multiple replicas or multiple Uvicorn worker processes would operate independently without a distributed lock manager (e.g. Redis), leading to double-assignment conflicts and race conditions.
> Keep:
> - **Replicas**: `1`
> - **Uvicorn Workers**: `1` (enforced in `Dockerfile` start command)

---

## 5. Security & Prototype Notice

1. **Synthetic Demo Data**: The application is pre-seeded with 12 diverse demo student profiles, 6 academic domains, assessments, and sample doubts.
2. **Identity Switcher**: The `X-Demo-Student-ID` header is a rapid demo switching mechanism designed for hackathon evaluation and demonstration. It is **not** a secure user authentication system.
3. **Data Protection**: Destructive operations like `python -m app.seed --reset` are strictly rejected when `ALLOW_DATABASE_RESET=false`.
4. **Authoritative Clock**: The backend clock (`/api/server-time`) enforces IST scheduling.

---

## 6. Local Development & Fallback Verification

If testing locally without Docker:

### Backend:
```bash
# From workspace root
# 1. Activate Python virtual environment
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux/macOS

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend:
```bash
# In another terminal
cd frontend
npm install
npm run dev
# Vite runs at http://localhost:5173 and proxies /api to http://127.0.0.1:8000
```

### Run Tests:
```bash
# Set PYTHONPATH to backend
pytest backend/tests -v
```

---

## 7. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| Database resets on every redeployment | Persistent volume not mounted to `/data` | Ensure Railway volume is attached and mount path is set to `/data`. |
| 404 on API requests | URL prefix mismatch | All backend routes are prefixed with `/api`. Frontend uses relative `/api/...`. |
| Healthcheck fails during startup | Seed or table creation takes longer than timeout | Increase Healthcheck timeout to 30s. Verify SQLite permissions on `/data`. |
| Cross-origin errors | CORS origins misconfigured | Verify `CORS_ORIGINS` matches the exact deployed domain (including `https://`). |
