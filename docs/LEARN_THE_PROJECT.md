# TRIAGE15 — STUDY & DEFENSE GUIDE: LEARN THE PROJECT

**Audience:** Participant / Technical Presenter preparing for judge evaluation  
**Recommended Study Time:** 30–45 minutes  
**Goal:** Understand how the actual codebase works so you can answer skeptical judge questions with confidence, pointing to exact source files rather than reciting generic definitions.

---

## 30–45 MINUTE PRIORITIZED STUDY PLAN

| Time Window | Focus Area | What to Read | Key Takeaway |
| :--- | :--- | :--- | :--- |
| **00:00 – 07:00** | Level 1 & 2: Story & User Journey | Levels 1 & 2 below | Understand the 15-minute concept and the exact 6-step demo flow. |
| **07:00 – 17:00** | Level 5: The Matching Algorithm | Level 5 below + `backend/app/algorithms.py` | Memorize the 2×2 counterexample `[[9,8],[8,1]]` and why Hungarian beats Greedy. |
| **17:00 – 27:00** | Level 6: Database & Concurrency | Level 6 below + `backend/app/models.py` | Learn how `BEGIN IMMEDIATE` and partial unique indexes stop double-booking. |
| **27:00 – 35:00** | Level 7: Bounty Ledger & Lifecycle | Level 7 below + `backend/app/services.py` | Understand integer point reservations, idempotency keys, and outcome confirmation. |
| **35:00 – 45:00** | Top 5 Code Files & Limitations | Top 5 Files summary + `docs/LIMITATIONS.md` | Know the 5 critical files and how to defend trade-offs honestly. |

---

## LEVEL 1: PRODUCT OVERVIEW IN SIMPLE LANGUAGE

### What is Triage15?
Imagine you are a college student stuck on a Python recursion bug at 11 PM. You don't need a 2-hour formal tutor; you need 15 minutes with a peer who understands recursion.
- Existing options fail: Asking on a forum takes hours. Hiring a tutor is expensive. Asking an AI chatbot often gives plausible-looking code that doesn't actually work in your specific project.
- **Triage15 is a peer-to-peer micro-skill and doubt bounty board:**
  1. A student posts a focused question and attaches a virtual reputation bounty (e.g. 40 points).
  2. The system checks all waiting questions and all available mentors across campus at once, running a mathematical matching algorithm to find the globally best matches.
  3. The mentor and student enter a 15-minute live workspace with code chat and an authoritative countdown timer.
  4. When the session finishes, the student confirms resolution, and the bounty points transfer to the mentor's reputation balance.

---

## LEVEL 2: THE COMPLETE USER JOURNEY

Follow this chronological narrative:
1. **Registration / Selection:** Student logs in. Synthetic demo students receive an initial grant of 150 virtual reputation points (`PointLedger`).
2. **Mentoring Opt-In:** An experienced student (e.g., Asha) marks herself as a mentor for `Python`, declares her skill tags (`loops`, `debugging`), sets availability for the afternoon, and takes a 5-question domain quiz to provide evidence of knowledge.
3. **Posting a Doubt:** Another student (e.g., Rohan) has a recursion bug. He selects `Python`, chooses urgency (`Urgent`), attaches a `40-point` bounty, and clicks **Post Doubt**. The 40 points are immediately reserved from his balance (new balance: 110 pts).
4. **Optimal Dispatch:** The background dispatch coordinator checks all open doubts. Asha is selected as Rohan's optimal mentor based on skill match, assessment score, reliability, and time proximity.
5. **Session Offer:** Asha receives an offer notification with an explanation of why she was chosen. She clicks **Accept**.
6. **Live Workspace:** Both enter the session room. They chat and paste code. The authoritative 15-minute countdown timer ticks down on the server.
7. **Resolution & Settlement:** Asha marks assistance complete. Rohan confirms: *"Yes, resolved!"* and gives 5 stars. The 40-point bounty transfers to Asha. If it wasn't resolved, the points remain locked, and the doubt returns to the queue for a new mentor.

---

## LEVEL 3: FRONTEND-BACKEND COMMUNICATION

### Architecture Separation
- **Frontend:** React 19 + TypeScript (`frontend/src/`).
- **Backend:** FastAPI + Python (`backend/app/`).
- **Communication Protocol:** JSON REST over HTTP. All endpoints start with `/api`.
- **Identity Header:** Every request sends `X-Demo-Student-ID: <student_id>` so the backend knows who the actor is.
- **Time Representation:**
  - Backend stores raw integer UTC seconds: `int(time.time())`.
  - Backend returns ISO 8601 UTC strings: `2026-11-24T05:30:00+00:00`.
  - Frontend renders in Indian Standard Time (`Asia/Kolkata`): `time()` helper in `api.ts`.
- **Real-Time Polling Hook:** Instead of complex WebSockets, the frontend polls `/api/sessions` and `/api/sessions/{id}/messages` every 2.5–4.0 seconds. It uses cursor queries (`?since_id=...`) to only download new messages.

---

## LEVEL 4: DATABASE STRUCTURE & RELATIONS

Look at `backend/app/models.py`. There are 12 relational tables:
1. `students`: Participant records. Has `points_balance` with SQL constraint `points_balance >= 0`.
2. `student_skills`: Mentor declared skills with level 1–5. Unique constraint on `(student_id, domain, tag)`.
3. `availability_windows`: When mentors are free. SQL constraint `end > start`.
4. `doubts`: Help requests. Has `domain`, `urgency`, `bounty`, `status` (`OPEN`, `MATCHED`, `IN_SESSION`, etc.).
5. `doubt_skills`: Specific skills required by a doubt.
6. `sessions`: 15-minute bookings. Has `start`, `end`, `state`, `mentor_id`, `doubt_id`.
7. `session_messages`: Live workspace chat history.
8. `point_ledger`: Double-entry accounting ledger tracking all point adjustments.
9. `session_feedback`: 1–5 star ratings and reviews given by requesters.
10. `assessment_questions`: Multiple-choice question banks per domain.
11. `assessment_attempts`: Test attempts with scores and timestamps.
12. `dispatch_runs` / `benchmark_runs`: Persisted JSON snapshots of algorithm executions.

---

## LEVEL 5: THE MATCHING ALGORITHM (THE MOST IMPORTANT JUDGE TOPIC)

Judges will test you on this. Study this carefully!

### Why not Greedy?
A greedy algorithm looks at the highest individual match and takes it immediately. But greedy can steal a mentor from someone who has no other options!

### The 2×2 Worked Counterexample:
Imagine two doubts ($D_1, D_2$) and two mentors ($M_1, M_2$):
$$\begin{pmatrix} & M_1 & M_2 \\ D_1 & 9 & 8 \\ D_2 & 8 & 1 \end{pmatrix}$$
- **Greedy Approach:** Looks for the highest number in the whole grid: $D_1 \to M_1$ with utility **9**. Now $D_1$ and $M_1$ are taken. $D_2$ is forced to take $M_2$ with utility **1**. Total utility = $9 + 1 = \mathbf{10}$.
- **Hungarian Approach:** Considers both pairs together: $D_1 \to M_2$ (utility 8) and $D_2 \to M_1$ (utility 8). Total utility = $8 + 8 = \mathbf{16}$.
- **Result:** Hungarian yields **16 vs 10** — a **60% improvement in total campus utility**!

### How Does the Hungarian Algorithm Work in Code? (`backend/app/algorithms.py`)
1. **Rectangular Padding:** If there are 10 doubts and 50 slots, we add 10 "dummy" slots with cost 0.
2. **Minimizing Cost:** We turn high utility into low cost by negating it (`cost = -utility`). Prohibited edges get cost $10^{12}$.
3. **Dual Potentials & Augmenting Paths:** We maintain row potentials $u$ and column potentials $v$. The algorithm iteratively finds augmenting paths to reach the lowest possible total cost.
4. **Extraction:** Any doubt assigned to a real slot is matched; any doubt assigned to a dummy slot is left unassigned.

---

## LEVEL 6: TRANSACTIONS, CONCURRENCY & BOOKING INTEGRITY

Judges often ask: *"What happens if two people click at the same time?"*

Here is your exact technical answer:

### 1. `BEGIN IMMEDIATE` Serialization (`backend/app/database.py`)
In SQLite, normal transactions only lock the database when writing. If two threads read simultaneously, they both think a mentor is free and both write, causing a race condition.
- We solved this: Every booking transaction calls `db.connection().exec_driver_sql('BEGIN IMMEDIATE')`. This locks the write reservation **before reading any booking data**. Only one transaction can validate and book at a time.

### 2. Partial Unique Indexes (`backend/app/models.py`)
Even if Python code had a bug, the database schema itself makes double-booking impossible:
```sql
CREATE UNIQUE INDEX uq_active_mentor_slot 
ON sessions (mentor_id, start) 
WHERE state IN ('OFFERED', 'ACCEPTED', 'ACTIVE', 'AWAITING_CONFIRMATION');
```
If two requests try to book the same mentor at the same start time, SQLite aborts the second one with an `IntegrityError` (`409 Conflict`).

---

## LEVEL 7: BOUNTY LEDGER & SESSION LIFECYCLE

### Why is it a "Ledger" and not just a points column?
If you only have `points_balance = 100`, you cannot prove how a student earned their points or audit whether a bug double-paid them.
- `point_ledger` records an immutable row for every event:
  - `INITIAL_GRANT` (+150 pts)
  - `BOUNTY_RESERVED` (-40 pts)
  - `BOUNTY_AWARDED` (+40 pts)
  - `BOUNTY_REFUNDED` (+40 pts)
- Every transaction has a unique `reference_id` (e.g. `award:session-123`). SQLite's `UNIQUE` constraint guarantees points cannot be awarded or refunded twice.

### The Authoritative 15-Minute Timer
- Session windows are strictly 15 minutes (`start` to `end`).
- The client timer counts down using `active_seconds_remaining` computed on the backend.
- **Judge Demo Feature:** In the workspace, click **⚡ Demo Clock (30s)**. It accelerates the active countdown to 30 seconds for quick hackathon evaluation without violating the database's 15-minute grid rules!

---

## LEVEL 8: BENCHMARKS & HONEST TECHNICAL LIMITATIONS

Judges love honesty. If you admit limitations proactively, you gain immense credibility:

1. **Academic Disclaimer:** Our benchmark shows Hungarian wins utility in ~84% of scenarios. But total utility is an objective function we defined. It is an algorithmic optimization measurement, **not proof that students get better exam grades**.
2. **SQLite Write Concurrency:** SQLite only allows one writer at a time. It is perfect for a single-campus prototype (zero external servers to crash), but scaling to 100,000 students would require PostgreSQL with row-level locking (`SELECT FOR UPDATE`).
3. **Assessment Limitation:** A 5-question multiple choice quiz tests syntax awareness, not true teaching ability. We explicitly label it as *"provisional evidence, not professional qualification"*.

---

## TOP 5 CODE FILES YOU MUST KNOW

1. **`backend/app/algorithms.py`**: Contains `maximum_weight()` (rectangular Kuhn-Munkres) and `greedy()`.
2. **`backend/app/services.py`**: Contains `dispatch()`, `feasible()`, `score()`, and the bounty accounting functions (`reserve_bounty`, `award_bounty`, `refund_bounty`).
3. **`backend/app/models.py`**: Contains the SQLAlchemy database models, foreign keys, `CheckConstraint`, and partial unique indexes.
4. **`backend/app/main.py`**: Contains the REST API endpoints, role permission checks (`own()`), and session lifecycle transitions.
5. **`frontend/src/components/SessionWorkspace.tsx`**: The live workspace UI with chat messaging and countdown timer.
