# TRIAGE15 — JUDGE DEMONSTRATION SCRIPT & SCENARIO GUIDE

**Estimated Duration:** 90–120 seconds  
**Objective:** Present a bulletproof, deterministic demonstration of optimization, transactional integrity, live peer messaging, authoritative timers, and reputation bounties.

---

## 1. Quick Startup & Reset Commands

Before presenting to the judges, reset the demonstration database to a known clean state:
```bash
# 1. Reset synthetic demo database
set PYTHONPATH=backend
.venv\Scripts\python.exe -m app.seed --reset

# 2. Start FastAPI backend (Terminal 1)
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Start React frontend (Terminal 2)
cd frontend
npm run dev
# Open browser at http://localhost:5173
```

---

## 2. Core 90-Second Walkthrough (Scenario A)

### Step 1: Identity Selection & Points Inspection (0:00–0:15)
- Open `http://localhost:5173`.
- In the top-right header, select demo identity: **`Asha (demo)`** (Student-01, Mentor, Python).
- Point out her point balance (`★ 175 pts`) and navigate to **Profile & Availability** -> **Mentor Credibility**.
- **Judge Speaking Point:** *"Notice how Asha's credibility card transparently reports 2 confirmed resolutions out of 3 completed sessions (66.7%), with a separate Bayesian smoothed reliability rating. We never fabricate a 100% expertise rating for new mentors."*

### Step 2: Seeker Doubt Creation with Reputation Bounty (0:15–0:35)
- Switch identity to **`Rohan (demo)`** (Student-08, Seeker, Balance `150 pts`).
- Under **Ask for Peer Help**:
  - Title: `Python: Recursion base case issue`
  - Description: `Binary search tree DFS is causing infinite recursion.`
  - Domain: `Python` (Tags: `python`, `debugging`)
  - Urgency: `Urgent`
  - Bounty: `40 points`
  - Click **Post Doubt**.
- Point out that Rohan's balance immediately updates to `110 pts` (40 points reserved in the ledger).
- Show the doubt card on the board with badges: `Urgent`, `★ 40 pts bounty`, `OPEN`.

### Step 3: Optimization & Automatic Dispatch (0:35–0:50)
- In the Doubt Board header, click **Run Dispatch (Manual)** (or observe continuous automatic matching).
- Expand **Dispatch Results & Allocation Analysis**:
  - Show the candidate matrix utility comparison: **Hungarian total utility vs Greedy utility**.
  - Show that Asha (`student-01`) was selected as the optimal mentor.
  - Expand **Why this allocation?** to inspect suitability breakdown: 35 skill relevance + 20 assessment evidence + 10 reliability + proximity + urgency multiplier.

### Step 4: Mentor Offer Acceptance & Live Workspace (0:50–1:15)
- Switch identity back to **`Asha (demo)`** (`student-01`).
- Navigate to **My sessions**.
- Show the pending offer card with offer expiration countdown and bounty attached.
- Click **Open Live Workspace →**.
- Point out:
  - Authoritative 15-minute countdown timer (`15:00`).
  - Full doubt description and required skills.
  - Chat room: Type a message as Asha:
    ```text
    Hi Rohan! You forgot `if not node: return`. Let's test it!
    ```
  - Click **Send**. Message appears immediately with UTC timestamp.

### Step 5: Authoritative Demo Clock & Outcome Confirmation (1:15–1:40)
- Click **⚡ Demo Clock (30s)**:
  - **Judge Speaking Point:** *"In production, sessions run for an authoritative 15-minute window. For our hackathon evaluation, this demo clock accelerates the timer to 30 seconds without modifying the database's 15-minute slot grid constraints."*
  - Watch the timer tick down in real-time.
  - Click **✓ Mark Assistance Complete**. Session transitions to `AWAITING_CONFIRMATION`.
- Switch identity back to **`Rohan (demo)`** (`student-08`) and refresh/view the workspace.
- The **Confirm Session Resolution** form is now visible for Rohan:
  - Was your doubt resolved? Select **Yes, resolved (award bounty)**.
  - Rating: `5` stars.
  - Notes: `Understood the base case thoroughly!`
  - Click **Submit Final Outcome**.

### Step 6: Bounty Award & Ledger Audit (1:40–1:55)
- Switch identity to **`Asha (demo)`** (`student-01`).
- Her balance has increased from `175 pts` to `215 pts` (★ +40 pts awarded).
- Navigate to **Profile & Availability** -> **Points Ledger & Bounties**.
- Show the auditable transaction:
  - Type: `BOUNTY_AWARDED`
  - Amount: `+40 pts`
  - Reference ID: `award:<session-id>`
- Show that repeated settlement attempts are strictly rejected by the unique database constraint.

---

## 3. Technical Deep-Dive Demonstrations

### Technical Demo 1: Rectangular Hungarian vs Greedy (Scenario B)
- Navigate to the **Benchmark** tab.
- Click **Run Benchmark Suite**.
- Show the results across 50 reproducible synthetic matrices (seed 15015):
  - Hungarian wins ~84% of scenarios.
  - In the 2×2 illustrative counterexample `[[9,8],[8,1]]`, Greedy picks $9+1=10$, while Hungarian picks $8+8=16$ (a 60% total utility improvement).
  - Point out the honest disclaimer: Greedy is computationally faster ($O(E \log E)$ vs $O(N^2 M)$), and total utility improvements measure algorithm quality against our objective function, not academic mastery.

### Technical Demo 2: Automatic Reassignment (Scenario C)
- Post a doubt as **`Rohan (demo)`**.
- When offered to **`Asha (demo)`**, click **Decline Offer**.
- Observe that the doubt immediately returns to `OPEN` status, and upon the next matching cycle, the engine reassigns the doubt to **`Kabir (demo)`** (`student-02`), completely excluding Asha from immediate reassignment. The 40-point reserved bounty is preserved without duplication or loss.

### Technical Demo 3: Concurrent Claim Protection (Scenario D)
- Open an `OPEN` doubt on the board.
- As an eligible mentor, click **Claim this Doubt**.
- The claim succeeds instantly (`200 OK`) and moves the session to `ACCEPTED`.
- Attempting to claim the same doubt simultaneously from another mentor tab is immediately rejected with a `409 Conflict` via SQLite's `uq_active_doubt` partial unique index.

### Technical Demo 4: Honest Unmatched State (Scenario E)
- Filter by domain **`Mathematics`**.
- The seeded Mathematics mentor (`Isha`, `student-07`) is intentionally configured without availability windows.
- Run dispatch: Mathematics doubts remain honest and visible as **`Waiting / Unmatched`** with explanation `"No eligible slot"`. The system never fabricates or forces an invalid match.
