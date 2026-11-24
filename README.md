# Triage15

A local peer-help dispatch MVP: React + TypeScript + Vite, FastAPI + SQLAlchemy + SQLite, pure-Python Hungarian matching, and a shared-matrix greedy baseline. No API keys or cloud services.

## Quick start (Windows PowerShell)

Requires Python 3.11+ and Node 22.12+ (tested with Python 3.14.5 and Node 22.23.2). Run from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
cd frontend
npm ci
cd ..
```

Terminal 1:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Interactive API reference: http://127.0.0.1:8000/docs. Keep both terminals running. On Unix use `.venv/bin/python` in place of the Windows interpreter path. The Vite proxy connects `/api` to port 8000.

The first backend startup creates `backend/triage15.db` and seeds 12 synthetic students, seven opted-in mentors (one intentionally unavailable), six domains, 15 MCQs, 18 waiting sample doubts plus three historical requests, and completed/resolved feedback records. Availability is relative to seed time. Restarting does not overwrite existing data.

## Reset, tests, build, benchmark

Stop the backend before resetting. This explicitly deletes all local demo data:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.seed --reset
..\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run build
```

The tests use separate temporary databases under `backend/.test-data`; they never reset the demo. In restricted Windows agent environments, Python's event-loop socket setup may need execution outside the sandbox. A normal local terminal does not require an application code workaround.

Run the actual 50-scenario comparison from the Benchmark tab or:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/benchmarks/run -Headers @{'X-Demo-Student-ID'='student-08'}
```

Measured results and per-scenario runtimes are in `docs/benchmark-results.json`. The fixed seed produced 28 higher-utility results and 22 ties. This is a synthetic matrix benchmark, not measured student outcomes.

## Try the workflow

1. Select Rohan; post a Python question. No assessment is required.
2. Run dispatch. Inspect assignments and explicit unmatched reasons.
3. Open My sessions. Inspect the chosen mentor, slot, and score breakdown.
4. Select that mentor, accept, start, and mark their side complete.
5. Select Rohan, confirm resolution and rate the session. Metrics update from stored records.
6. Try declining another offer, then dispatch again. Mathematics requests demonstrate unavailable mentors.
7. Use Profile & availability to change skills, opt into mentoring, or add available windows. Assessments remain optional evidence.

All inputs and displays use IST; the API uses timezone-qualified ISO timestamps and the database stores UTC epoch seconds. Offers last at most five minutes and expire no later than slot start. The demo permits early session start to support a short presentation.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database and ER diagram](docs/DATABASE.md)
- [Algorithm and mathematical limits](docs/ALGORITHM.md)
- [API contract](docs/API.md), plus generated [OpenAPI](docs/openapi.json)
- [25 technical judge questions](docs/JUDGE_QA.md)
- [90-second demonstration](docs/DEMO_SCRIPT.md)
- [Executed test report](docs/TEST_REPORT.md)
- [Limitations](docs/LIMITATIONS.md)

Learn the 9/8/8/1 matching example first, then grid-based uniqueness and transactions, then the session lifecycle and scoring components. These are the central defensible engineering choices.

## Configuration

`DATABASE_URL` and `OFFER_TTL_SECONDS` are environment variables read at process startup; `.env.example` lists them but there is no automatic dotenv loader. Urgency weights and the domain catalog live in `backend/app/config.py`. Dependencies actually used are frozen in `backend/requirements-lock.txt` and `frontend/package-lock.json`.

This is demo identity selection, not authentication. Do not expose the API publicly. Matching optimizes the candidate matrix, then final validation can reject cross-role/requester conflicts; the remaining bookings are safe but not guaranteed globally optimal under those extra constraints. See limitations for the complete scope.
