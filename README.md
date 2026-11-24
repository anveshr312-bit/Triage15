# TRIAGE15

### Peer-to-Peer Micro-Skill and Doubt Bounty Board (15-Minute Sessions)

**Explainable ML is ready:** Use **Suggest Skills** in the doubt form, review actual feature contributions, and accept/remove/add tags before posting. Open **ML evaluation** for measured results. A local TF-IDF + Linear SVM model uses eight existing tags; final held-out micro F1 is **0.8736** on 404 questions. The Hungarian engine remains independent and unchanged. Set `ML_ENABLED=false` for manual-only operation.

[ML architecture and reproduction](docs/ML_ARCHITECTURE.md) · [Model card](docs/MODEL_CARD.md) · [Dataset and attribution](data/DATASET_CARD.md) · [Judge Q&A](docs/ML_JUDGE_QA.md) · [15-minute guide](docs/ML_15_MINUTE_GUIDE.md) · [Verification](docs/ML_VERIFICATION.md)

**Event:** MLH HackDay  
**Stack:** React 19 + TypeScript + Vite | FastAPI + SQLAlchemy 2.0 + SQLite (WAL) | Rectangular Kuhn-Munkres Hungarian Matching  
**Test Suite:** 94 automated tests passing (56 original + 38 ML checks) | Offline inference; network only for optional dataset acquisition

---

## 1. What is Triage15?

Triage15 solves campus academic bottlenecks by matching students needing quick technical assistance with qualified peer mentors in structured 15-minute intervals. 

Instead of sequential first-come first-served queueing or unreliable chat bots, Triage15 utilizes:
1. **Deterministic Bipartite Optimization:** Maximizes global campus utility using the rectangular Kuhn-Munkres algorithm, outperforming greedy heuristics on competing requests.
2. **Virtual Reputation Bounty Board:** Students attach virtual points to doubts. Points are reserved on submission, audited in an integer double-entry ledger, and awarded to the mentor only upon confirmed resolution.
3. **Live 15-Minute Session Workspace:** Secure peer chat, code snippet exchange, and an authoritative countdown timer.
4. **Resilient Scheduling & Reassignment:** Partial unique database indexes prevent double-booking. If a mentor declines or an offer expires, the system automatically finds an alternative.
5. **Transparent Mentor Credibility:** Profiles display actual resolution rates, completed sessions, and assessment evidence, without misleading 100% expertise claims.

---

## 2. Quickstart Instructions (Windows PowerShell)

### Prerequisites
- Python 3.12+ (tested with Python 3.14.5; Docker uses 3.12)
- Node.js 18+ (tested with Node 22.x)

### Setup & Installation
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install backend dependencies
.\.venv\Scripts\pip install -r backend\requirements.txt

# 3. Install frontend dependencies
cd frontend
npm install
cd ..
```

### Initialize Database & Demo Data
```powershell
$env:PYTHONPATH=".;backend"
.\.venv\Scripts\python.exe -m app.seed --reset
```
*Initializes 12 synthetic students, 7 mentors, academic skill domain banks, availability windows, sample doubts with bounties, and historical feedback records.*

### Run the Application

**Terminal 1 (Backend API):**
```powershell
$env:PYTHONPATH=".;backend"
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend Client):**
```powershell
cd frontend
npm run dev
```

- Open the web application at: **`http://localhost:5173`**
- Interactive Swagger API docs: **`http://127.0.0.1:8000/docs`**

---

## 3. Running Verification & Benchmarks

### Execute Full Automated Test Suite (94 Tests)
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest -v backend\tests
```
*Runs 94 tests across algorithm verification, API contracts, bounty/messaging/timer/claiming, end-to-end workflows, ML attribution and fallback. See docs/ML_VERIFICATION.md for the executed results.*

### Verify Frontend Production Build
```powershell
cd frontend
npm run build
```
*Compiles TypeScript and bundles via Vite with zero diagnostic errors.*

### Execute Algorithm Benchmark Suite
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/benchmarks/run -Headers @{'X-Demo-Student-ID'='student-08'}
```
*Evaluates Hungarian maximum-weight matching against the greedy baseline across 50 reproducible synthetic matrices (seed 15015).*

---

## 4. Key Product Capabilities

| Capability | Technical Mechanism | Primary Files |
| :--- | :--- | :--- |
| **Bounty Accounting** | Integer double-entry ledger (`PointLedger`), `points_balance >= 0` check constraint, unique settlement keys | `models.py`, `services.py` |
| **Live Workspace** | Role-authorized messaging room, safe pre/code rendering, 2.5s cursor polling | `models.py`, `main.py`, `SessionWorkspace.tsx` |
| **15-Min Session Timer** | Authoritative server timestamps (`start`, `end`, `actual_started_at`), client zero-drift sync, 30s judge demo clock | `models.py`, `main.py`, `SessionWorkspace.tsx` |
| **Automatic Matching** | Continuous centralized coordinator (`DispatchCoordinator`), multi-factor suitability scoring | `services.py`, `main.py` |
| **Iterative Conflict Recovery** | Bounded multi-pass Hungarian re-matching to resolve cross-role scheduling conflicts | `services.py`, `algorithms.py` |
| **Automatic Reassignment** | State release on decline/expiry, exclusion of previous mentors, automatic queue re-dispatch | `services.py`, `main.py` |
| **Manual Session Claiming** | Direct claim (`POST /api/doubts/{id}/claim`) with SQLite `BEGIN IMMEDIATE` double-booking protection | `services.py`, `main.py`, `DoubtBoard.tsx` |
| **Mentor Credibility** | Transparent resolution rate, feedback stars, assessment evidence, Bayesian smoothed reliability | `main.py`, `Profile.tsx` |

---

## 5. Documentation Directory

Detailed technical documents are available in `docs/`:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Full system architecture, coordinator design, and Mermaid workflows.
- [`docs/DATABASE.md`](docs/DATABASE.md): Relational schema, foreign keys, partial unique indexes, and ER diagram.
- [`docs/ALGORITHM.md`](docs/ALGORITHM.md): Mathematical formulations, Kuhn-Munkres matching, suitability scoring, and benchmarks.
- [`docs/API.md`](docs/API.md): Comprehensive REST API contract reference with status codes and schemas.
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md): Step-by-step 90-second judge demonstration walkthrough and test scenarios.
- [`docs/ML_VERIFICATION.md`](docs/ML_VERIFICATION.md): Current automated and browser verification (94 passing tests); older results remain in `docs/TEST_REPORT.md`.
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md): Transparent engineering boundaries and production scaling roadmap.
- [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md): 45+ comprehensive technical defense questions and answers.
- [`docs/LEARN_THE_PROJECT.md`](docs/LEARN_THE_PROJECT.md): 8-level comprehensive study guide for technical evaluation.
- [`docs/COMPLETION_TRACKER.md`](docs/COMPLETION_TRACKER.md): Live implementation and verification checklist.
