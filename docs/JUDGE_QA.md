# TRIAGE15 — TECHNICAL JUDGE DEFENSE Q&A (48 SUBSTANTIAL QUESTIONS)

This document provides exhaustive technical answers for skeptical hackathon judges, engineering leads, and technical auditors. Every answer reflects the actual implementation in the repository without fabricating hypothetical features.

---

### TABLE OF CONTENTS
1. [System Architecture & REST Design (Q1–Q5)](#1-system-architecture--rest-design)
2. [Database Normalization, Foreign Keys & Indexes (Q6–Q10)](#2-database-normalization-foreign-keys--indexes)
3. [Transactions, SQLite Concurrency & Atomic Operations (Q11–Q15)](#3-transactions-sqlite-concurrency--atomic-operations)
4. [Bipartite Matching & Algorithm Complexity (Q16–Q20)](#4-bipartite-matching--algorithm-complexity)
5. [Candidate Matrix, Optimality & Cross-Role Conflicts (Q21–Q25)](#5-candidate-matrix-optimality--cross-role-conflicts)
6. [Mentor Suitability, Cold-Start & Assessment Credibility (Q26–Q30)](#6-mentor-suitability-cold-start--assessment-credibility)
7. [Virtual Bounty Ledger & Financial Integrity (Q31–Q35)](#7-virtual-bounty-ledger--financial-integrity)
8. [Session Lifecycle, Timing & Workspace Messaging (Q36–Q40)](#8-session-lifecycle-timing--workspace-messaging)
9. [Security, XSS, Validation & Identity (Q41–Q44)](#9-security-xss-validation--identity)
10. [Benchmarks, Failure Recovery & Scaling (Q45–Q48)](#10-benchmarks-failure-recovery--scaling)

---

## 1. System Architecture & REST Design

### Q1: What is the high-level architecture of Triage15, and why was it chosen?
- **Simple Explanation:** Triage15 separates a React frontend and a FastAPI backend with SQLite persistence, communicating via structured REST endpoints without external cloud servers or API keys.
- **Precise Technical Explanation:** The frontend is a single-page application built on React 19, TypeScript, and Vite that delegates all domain decisions, matching calculations, and state transitions to a FastAPI backend. The backend uses Pydantic v2 schemas for request validation, SQLAlchemy 2.0 ORM for relational queries, and an in-process rectangular Kuhn-Munkres matching solver. Storage is handled by local SQLite configured with Write-Ahead Logging (`WAL`).
- **Source File & Function:** `backend/app/main.py` (`lifespan`, API routes); `frontend/src/App.tsx`.
- **Skeptical Follow-up:** *"Why didn't you build this with Next.js Server Actions or an all-in-one framework?"*
- **Answer:** Next.js tightly couples UI rendering with server execution. Separating FastAPI from React allows the matching algorithm and relational booking engine to run natively in Python (where optimization libraries and scientific benchmarks excel), while keeping the frontend modular, clean, and easily restylable.
- **Honest Limitation:** The prototype runs single-instance; running distributed nodes would require moving beyond in-process locks.

### Q2: Why did you build custom algorithms instead of calling an LLM API like GPT-4 or Claude?
- **Simple Explanation:** Matching peer tutors to open questions is a deterministic constrained optimization problem, not a text generation task.
- **Precise Technical Explanation:** LLMs are probabilistic, non-deterministic, slow (1–5 second API latencies), expensive, and prone to hallucinated skill endorsements. Resource assignment with hard temporal windows, mentor opt-in constraints, and slot non-overlap requires mathematical guarantees that Kuhn-Munkres delivers in under 2ms with 100% reproducibility.
- **Source File & Function:** `backend/app/algorithms.py` (`maximum_weight`, `greedy`).
- **Skeptical Follow-up:** *"Does your algorithm understand natural language doubt descriptions?"*
- **Answer:** No. Natural language descriptions are for human peers to read in the live workspace. The matching algorithm operates on explicit taxonomy domains and categorical skill tags (`domain`, `skills`).

### Q3: What REST HTTP status codes do you return, and how are errors standardized?
- **Simple Explanation:** We use precise standard HTTP status codes: 200 for OK, 201 for Created, 403 for unauthorized access, 404 for missing entities, 409 for conflicts, 422 for validation failures, 429 for rate limits, and 503 for database contention.
- **Precise Technical Explanation:**
  - `200 OK`: Successful read or state transition.
  - `201 Created`: Doubt posted, session message sent, assessment submitted, student registered.
  - `403 Forbidden`: Participant attempting to act on or view another student's session or messages (`own()` in `main.py`).
  - `404 Not Found`: Entity lookup fails (`svc.get()` in `services.py`).
  - `409 Conflict`: Double-booking, state transition violation, or SQLite `IntegrityError` (`integrity_error()` exception handler).
  - `422 Unprocessable Entity`: Pydantic validation failure or domain logic violation (e.g., insufficient point balance).
  - `429 Too Many Requests`: Assessment attempt rate limit exceeded (cooldown limit).
  - `503 Service Unavailable`: SQLite busy lock (`OperationalError`).
- **Source File & Function:** `backend/app/main.py` (`integrity_error`, `database_error`, `own`).
- **Skeptical Follow-up:** *"Do your error responses expose raw internal SQL queries?"*
- **Answer:** No. Handlers catch `IntegrityError` and `OperationalError`, returning clean JSON: `{"detail": "Database integrity conflict; refresh and retry."}`.

### Q4: Are your FastAPI endpoints asynchronous or synchronous?
- **Simple Explanation:** Endpoints are synchronous functions executed in FastAPI's internal threadpool to safely handle SQLite's synchronous file I/O.
- **Precise Technical Explanation:** SQLAlchemy sessions on SQLite perform blocking disk I/O. Declaring FastAPI endpoints as `def` (synchronous) causes Starlette to run them on background worker threads (`anyio` threadpool worker), preventing the main asyncio event loop from blocking. Long-running background loops (like `expiration_loop`) run as asyncio tasks and use `asyncio.to_thread` to invoke synchronous database sweeps.
- **Source File & Function:** `backend/app/main.py` (`lifespan`, `expiration_loop`).
- **Skeptical Follow-up:** *"Doesn't running synchronous endpoints limit high-throughput scalability?"*
- **Answer:** Yes, in high-throughput enterprise systems with async databases (e.g., PostgreSQL with `asyncpg`). For an embedded SQLite architecture, synchronous threadpool execution is the recommended and safest pattern.

### Q5: How do frontend components communicate with the backend?
- **Simple Explanation:** Through a lightweight TypeScript API client that uses `fetch` with Vite proxy forwarding.
- **Precise Technical Explanation:** The `api<T>` wrapper in `frontend/src/api.ts` attaches `Content-Type: application/json` and the identity header `X-Demo-Student-ID`. The Vite dev server proxies all `/api` prefixes to `http://127.0.0.1:8000`. Error responses throw standard JavaScript errors displaying `data.detail`.
- **Source File & Function:** `frontend/src/api.ts` (`api`); `frontend/vite.config.ts`.

---

## 2. Database Normalization, Foreign Keys & Indexes

### Q6: How is the database normalized, and why?
- **Simple Explanation:** All core business entities are in Third Normal Form (3NF) with foreign keys and unique constraints.
- **Precise Technical Explanation:** Skills are normalized into `student_skills` and `doubt_skills` to avoid comma-delimited strings or JSON querying. Responses are linked to attempts in `assessment_responses`. Sessions, messages, and ledger entries all reference primary keys via indexed foreign keys.
- **Source File & Function:** `backend/app/models.py`.
- **Skeptical Follow-up:** *"Why do you have JSON columns if the schema is normalized?"*
- **Answer:** JSON is used solely for immutable snapshots (`dispatch_runs.result`, `benchmark_runs.result`, `sessions.explanation`) and MCQ option arrays (`assessment_questions.options`). Operational entities and searchable foreign keys are strictly normalized.

### Q7: What foreign keys exist, and are they actually enforced by SQLite?
- **Simple Explanation:** Foreign keys exist between all relational tables and are enforced via SQLite PRAGMA commands on every single database connection.
- **Precise Technical Explanation:** SQLite disables foreign key enforcement by default. In `backend/app/database.py`, an event listener on SQLAlchemy's engine triggers on every connection: `connection.execute('PRAGMA foreign_keys=ON')`. Foreign keys include `doubts.requester_id -> students.id`, `sessions.doubt_id -> doubts.id`, `sessions.mentor_id -> students.id`, `point_ledger.student_id -> students.id`, and `session_messages.session_id -> sessions.id`.
- **Source File & Function:** `backend/app/database.py` (`sqlite_settings`).
- **Skeptical Follow-up:** *"What happens when you reset the database with circular foreign keys?"*
- **Answer:** `doubts.assigned_session_id` and `sessions.doubt_id` create a circular dependency. The `--reset` script in `seed.py` disables foreign keys exclusively during table drop, then re-enables them immediately: `PRAGMA foreign_keys=OFF; Base.metadata.drop_all(); PRAGMA foreign_keys=ON;`.

### Q8: What indexes are defined, and what query patterns do they optimize?
- **Simple Explanation:** Foreign keys are indexed for fast joins, and status columns are indexed for queue filtering.
- **Precise Technical Explanation:**
  - Foreign key indexes: `student_skills.student_id`, `availability_windows.student_id`, `doubts.requester_id`, `sessions.doubt_id`, `sessions.mentor_id`, `point_ledger.student_id`, `session_messages.session_id`.
  - Filter indexes: `doubts.domain`, `doubts.status`, `assessment_questions.domain`.
  - Range/Sorting indexes: `session_messages.created_at`.
- **Source File & Function:** `backend/app/models.py`.
- **Skeptical Follow-up:** *"Do you have partial indexes?"*
- **Answer:** Yes! `uq_active_doubt` and `uq_active_mentor_slot` use partial indexes with `sqlite_where` clauses.

### Q9: How do you prevent double-booking at the database level?
- **Simple Explanation:** Using partial unique indexes that only apply to active and offered sessions.
- **Precise Technical Explanation:** In `backend/app/models.py`, `Session` defines:
  ```python
  Index('uq_active_doubt', 'doubt_id', unique=True, sqlite_where=text("state IN ('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION')"))
  Index('uq_active_mentor_slot', 'mentor_id', 'start', unique=True, sqlite_where=text("state IN ('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION')"))
  ```
  If a transaction attempts to insert a second active session for the same doubt or for the same mentor at the same start timestamp, SQLite rejects it with an `IntegrityError`.
- **Source File & Function:** `backend/app/models.py` (lines 135–139).
- **Skeptical Follow-up:** *"What happens when a session is CANCELLED or DECLINED?"*
- **Answer:** Because the partial index only covers `('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION')`, once a session transitions to `DECLINED`, `EXPIRED`, or `CANCELLED`, its slot is immediately released for new bookings without deleting historical rows.

### Q10: How do you enforce the 15-minute grid interval in the database?
- **Simple Explanation:** With a SQL check constraint verifying that timestamps are multiples of 900 seconds.
- **Precise Technical Explanation:** `Session.__table_args__` enforces: `CheckConstraint('start % 900 = 0 AND end = start + 900')`. Any insert or update violating the 15-minute grid (e.g., an arbitrary 10-minute duration or unaligned start) fails validation at the database engine level.
- **Source File & Function:** `backend/app/models.py` (line 134).

---

## 3. Transactions, SQLite Concurrency & Atomic Operations

### Q11: How do you prevent race conditions when reading and writing booking state?
- **Simple Explanation:** By using `BEGIN IMMEDIATE` transactions, ensuring that reading booking state reserves the write lock upfront.
- **Precise Technical Explanation:** Normal SQLite transactions start in `DEFERRED` mode, acquiring a read lock first and upgrading to a write lock later. If two threads read simultaneously and then both try to write, SQLite throws a deadlock error (`SQLITE_BUSY`). In `backend/app/database.py`, our `transaction()` context manager issues `BEGIN IMMEDIATE`, acquiring an exclusive write reservation immediately before any SELECT query runs.
- **Source File & Function:** `backend/app/database.py` (`transaction()`).
- **Skeptical Follow-up:** *"Does `BEGIN IMMEDIATE` block readers?"*
- **Answer:** Under SQLite's `WAL` mode (`PRAGMA journal_mode=WAL`), readers never block writers, and the writer never blocks readers. Readers see the latest committed snapshot.

### Q12: What happens if two mentors try to manually claim the same open doubt at the exact same millisecond?
- **Simple Explanation:** Exactly one claim succeeds; the second receives a clean 409 Conflict.
- **Precise Technical Explanation:**
  1. Thread 1 enters `claim_doubt` inside a `BEGIN IMMEDIATE` transaction, verifies `doubt.status == 'OPEN'`, creates the `Session` record, and updates `doubt.status = 'MATCHED'`.
  2. Thread 2 waits on the SQLite write lock due to `busy_timeout=15000`.
  3. When Thread 1 commits, Thread 2 acquires the lock. Its query sees `doubt.status == 'MATCHED'` and `svc.require()` raises `HTTPException(409, 'Doubt is not open for claiming')`.
  4. Even if both threads bypassed the application check, the partial unique index `uq_active_doubt` on SQLite would abort the second insert with an `IntegrityError` (caught as 409).
- **Source File & Function:** `backend/app/services.py` (`claim_doubt`); `backend/tests/test_p0_features.py` (`test_concurrent_manual_claims_cannot_double_book`).
- **Skeptical Follow-up:** *"Have you proven this with a test?"*
- **Answer:** Yes. `test_concurrent_manual_claims_cannot_double_book` uses a `ThreadPoolExecutor(2)` to verify that exactly one claim receives `200` and the other receives `409`.

### Q13: Are your financial point ledger updates atomic?
- **Simple Explanation:** Yes. Point balance changes and ledger audit records are written in the same database transaction.
- **Precise Technical Explanation:** In `reserve_bounty()`, `award_bounty()`, and `refund_bounty()`, the `student.points_balance` update and the `PointLedger` insertion happen within the same SQLAlchemy transaction scope. If an exception occurs, the transaction rolls back completely, ensuring no desynchronization between balances and transaction logs.
- **Source File & Function:** `backend/app/services.py` (`reserve_bounty`, `award_bounty`, `refund_bounty`).

### Q14: How do you guarantee idempotency in bounty awards and refunds?
- **Simple Explanation:** Every settlement operation uses a deterministic unique reference ID that SQLite rejects if repeated.
- **Precise Technical Explanation:** `PointLedger.reference_id` carries a `UNIQUE` constraint. When awarding a bounty, the reference is `award:{session_id}`. When reserving, it is `reserve:{doubt_id}`. When refunding, it is `refund:{doubt_id}`. If a user double-clicks or an API call retries, the query checks for the existing reference key and exits cleanly without duplicating the points.
- **Source File & Function:** `backend/app/services.py` (lines 53, 73, 90).

### Q15: Can a student's point balance ever become negative?
- **Simple Explanation:** No. The database engine enforces `points_balance >= 0` via a CheckConstraint.
- **Precise Technical Explanation:** In `backend/app/models.py`, `Student` declares `__table_args__ = (CheckConstraint('points_balance >= 0'),)`. Even if application code attempted to deduct more points than available, SQLite would raise an `IntegrityError`, abort the transaction, and preserve the non-negative balance.
- **Source File & Function:** `backend/app/models.py` (line 23).

---

## 4. Bipartite Matching & Algorithm Complexity

### Q16: What is bipartite matching in the context of Triage15?
- **Simple Explanation:** It is a graph where requests form one set of nodes, mentor-slot pairs form the other set of nodes, and edges represent feasible help sessions.
- **Precise Technical Explanation:** Let $G = (D, R, E)$ be a weighted bipartite graph where $D$ is the set of $N$ open doubts and $R$ is the set of $M$ discrete mentor time slots $[t, t+900)$. A directed edge $(d_i, r_j) \in E$ exists if mentor $m_j$ satisfies all hard constraints for doubt $d_i$ at slot $t_j$. The edge weight $W_{i,j}$ is the calculated utility. A valid matching $M^* \subseteq E$ contains no two edges sharing a common request or a common resource.
- **Source File & Function:** `backend/app/services.py` (`dispatch`); `backend/app/algorithms.py`.

### Q17: Why can a mentor have multiple nodes in the bipartite graph?
- **Simple Explanation:** Because a mentor can offer multiple distinct 15-minute slots across the week.
- **Precise Technical Explanation:** If a mentor offers a 2-hour availability window, that generates 8 non-overlapping 15-minute slot resources. Assigning a mentor to Slot 1 does not prevent them from helping another student during Slot 3. The resource node is $(m_j, t_j)$, not simply $m_j$.
- **Source File & Function:** `backend/app/services.py` (lines 180–186).

### Q18: What is the computational complexity of your Hungarian matching algorithm?
- **Simple Explanation:** $O(N^2 M)$ where $N$ is requests and $M$ is slots, executing in 1–2 milliseconds for campus batches.
- **Precise Technical Explanation:** The rectangular Hungarian implementation operates on $N$ rows and $M + N$ columns (after adding $N$ dummy columns). It maintains dual potentials and uses Dijkstra-like shortest augmenting path trees. Each of the $N$ row augmentations runs in $O(N \cdot (M + N))$ time. Overall time complexity is $O(N^2 M + N^3)$, and spatial complexity is $O(N \cdot (M + N))$.
- **Source File & Function:** `backend/app/algorithms.py` (`maximum_weight`).
- **Skeptical Follow-up:** *"Isn't standard Hungarian $O(V^3)$?"*
- **Answer:** Standard square Hungarian is $O(V^3)$. When $N \ll M$ (e.g., 20 doubts and 200 available slots), rectangular augmentation with $N$ dummy columns runs in $O(N^2 M)$ time, which is substantially faster than padding the matrix to $M \times M$ ($O(M^3)$).

### Q19: What is the complexity of your greedy baseline, and how do they compare?
- **Simple Explanation:** Greedy sorts edges in $O(E \log E)$, which is faster but yields lower global utility.
- **Precise Technical Explanation:** The greedy algorithm extracts all non-null positive edges $E$, sorts them by decreasing utility in $O(E \log E)$ time, and greedily selects edges where neither the row nor the column has been consumed. In our 50-scenario benchmark, greedy runs in $0.05\text{ms}$ while Hungarian runs in $0.25\text{ms}$, but Hungarian wins in ~84% of scenarios.
- **Source File & Function:** `backend/app/algorithms.py` (`greedy`, `benchmark`).

### Q20: How do dummy nodes prevent invalid matches in Hungarian matching?
- **Simple Explanation:** Prohibited edges have a penalty of $10^{12}$, while dummy columns have cost 0. The solver always prefers leaving a doubt unassigned over picking an invalid edge.
- **Precise Technical Explanation:** The algorithm minimizes negated cost. Infeasible edges are assigned a cost of $10^{12}$. We append $N$ dummy columns with cost $0.0$. Because total real utilities are bounded between $[0, 150]$, an augmenting path can always pick an available dummy column at cost $0.0$ rather than paying $10^{12}$. Any doubt mapped to a dummy column is safely recognized as unassigned.
- **Source File & Function:** `backend/app/algorithms.py` (`maximum_weight`, lines 12–14).

---

## 5. Candidate Matrix, Optimality & Cross-Role Conflicts

### Q21: What is the 2×2 counterexample that proves Greedy is suboptimal?
- **Simple Explanation:** On matrix `[[9,8],[8,1]]`, Greedy yields 10, whereas Hungarian yields 16.
- **Precise Technical Explanation:**
  - Matrix: Row 0 has utilities $[9, 8]$; Row 1 has utilities $[8, 1]$.
  - Greedy inspects the highest edge $C_{0,0} = 9$ and takes it. Column 0 and Row 0 are consumed. Row 1 is forced to take Column 1 with utility $1$. Total utility: $9 + 1 = 10$.
  - Hungarian evaluates the global sum: taking $C_{0,1} = 8$ and $C_{1,0} = 8$ yields $8 + 8 = 16$.
  - 16 is 60% higher total utility than 10.
- **Source File & Function:** `backend/tests/test_algorithm.py` (`test_counterexample`); `backend/app/algorithms.py` (`benchmark`).

### Q22: What are cross-role conflicts, and why can't basic Hungarian matching catch them?
- **Simple Explanation:** A student can be a mentor for one doubt and a seeker for another doubt. Bipartite matching only ensures a mentor slot isn't used twice, not that a human isn't in two places at once.
- **Precise Technical Explanation:** In a peer-to-peer system, the same student $S$ may be the requester of Doubt $D_1$ and the mentor of Slot $R_1$. The bipartite graph treats Doubt $D_1$ as a row and Slot $R_1$ as a column. Bipartite matching guarantees that no two rows share a column, but it has no native mechanism to prevent Row $D_1$ and Column $R_1$ from both being assigned simultaneously during the same time interval $[t, t+900)$.
- **Source File & Function:** `backend/app/services.py` (`participant_busy`, `dispatch`).

### Q23: How does your Iterative Conflict Recovery (P1.1) resolve cross-role conflicts?
- **Simple Explanation:** When a conflict is detected at database commit, the conflicting edge is excluded, and Hungarian matching re-runs on remaining unmatched requests.
- **Precise Technical Explanation:**
  1. Kuhn-Munkres matching generates candidate assignments.
  2. During database persistence, each assignment is validated via `feasible()`, which calls `participant_busy()`.
  3. If a cross-role conflict is detected, the assignment is rejected, recorded in `rejections`, and the tuple `(doubt_id, mentor_id, slot_start)` is added to `excluded_pairs`.
  4. The candidate matrix is reconstructed for remaining open doubts with conflicting edges set to `None`.
  5. The solver executes again up to $K=3$ iterations.
  6. Newly recovered feasible assignments are committed transactionally.
- **Source File & Function:** `backend/app/services.py` (`dispatch`, lines 215–270).
- **Skeptical Follow-up:** *"Does iterative recovery guarantee global mathematical optimality under cross-role constraints?"*
- **Answer:** No! It is an iterative conflict recovery heuristic, not a mathematical proof of global optimality under multi-commodity or cross-role hypergraph constraints. We explicitly document this limitation in `docs/ALGORITHM.md` and `docs/LIMITATIONS.md`.

### Q24: What causes a request to remain in an UNMATCHED state?
- **Simple Explanation:** When no mentor supports the required skill tags, no mentor has availability during the requested window, or all eligible mentors are booked.
- **Precise Technical Explanation:** In `backend/app/services.py`, after dispatch runs, all unassigned doubts are inspected. If the candidate matrix had all `None` entries for that row, the doubt records `"No eligible slot"`. If feasible edges existed but were consumed by higher-utility assignments or cross-role conflicts, it records `"Waiting: eligible capacity allocated or participant conflict"`.
- **Source File & Function:** `backend/app/services.py` (lines 280–288).

### Q25: How does the waiting bonus prevent starvation?
- **Simple Explanation:** Doubts gain 1 point of utility per hour they wait, up to a maximum of 10 points.
- **Precise Technical Explanation:** In `score()`, `wait = min(10.0, max(0.0, current - doubt.created_at) / 3600)`. This aging term is added directly to total allocation utility. Over time, an older normal-urgency doubt can outrank a newly arrived urgent doubt.
- **Source File & Function:** `backend/app/services.py` (line 125).
- **Honest Limitation:** This is a bounded aging heuristic, not a formal mathematical proof of starvation-freedom.

---

## 6. Mentor Suitability, Cold-Start & Assessment Credibility

### Q26: How is the multi-factor suitability score calculated?
- **Simple Explanation:** A bounded score from 0 to 100 combining skill relevance (35%), assessment evidence (25%), reliability history (15%), time proximity (15%), and assessment confidence (10%).
- **Precise Technical Explanation:**
  - $S_{\text{relevance}} = 20 + 15 \times \frac{|\text{Tags}_{\text{mentor}} \cap \text{Tags}_{\text{doubt}}|}{|\text{Tags}_{\text{doubt}}|}$ (20 to 35 pts)
  - $S_{\text{evidence}} = \text{score} \times 0.25$ if tested, else 10 pts (provisional) (10 to 25 pts)
  - $S_{\text{reliability}} = 15 \times \frac{\text{resolved} + 2}{\text{completed} + 4}$ (0 to 15 pts)
  - $S_{\text{availability}} = \frac{15}{1 + \text{hours\_to\_start}}$ (0 to 15 pts)
  - $S_{\text{confidence}} = 10$ if assessed, else 4 pts (4 to 10 pts)
  Sum is bounded in $[0, 100]$.
- **Source File & Function:** `backend/app/services.py` (`score()`).

### Q27: How does your reliability calculation solve the cold-start problem?
- **Simple Explanation:** Using Bayesian Laplace smoothing, so new mentors start with a neutral 50% reliability instead of 0% or 100%.
- **Precise Technical Explanation:** The formula uses a prior of 2 successes out of 4 virtual trials:
  $$\text{Reliability} = 15 \times \frac{\text{resolved} + 2}{\text{completed} + 4}$$
  - For a new mentor with 0 completed sessions: $15 \times \frac{0 + 2}{0 + 4} = 7.5 / 15.0$ (exactly 50%).
  - A mentor who failed their first session gets $15 \times \frac{0 + 2}{1 + 4} = 6.0 / 15.0$ (40%), not 0%.
  - A mentor who succeeded in their first session gets $15 \times \frac{1 + 2}{1 + 4} = 9.0 / 15.0$ (60%), not 100%.
- **Source File & Function:** `backend/app/services.py` (`score()`, line 120).

### Q28: How do you prevent misleading credibility metrics on mentor profiles?
- **Simple Explanation:** If a mentor has 0 completed sessions, the profile displays "No resolution history yet" rather than an artificial 100% or 0% rating.
- **Precise Technical Explanation:** In `/api/mentors/{id}/profile`, `resolution_rate` is computed as `round(100.0 * resolved / completed, 1)` if `completed > 0` else `None`. The label explicitly outputs `"No resolution history yet"` when `completed == 0`, and displays raw sample sizes ($N$ completed, $M$ ratings) alongside the Bayesian smoothed heuristic.
- **Source File & Function:** `backend/app/main.py` (`mentor_profile`, lines 135–165); `frontend/src/components/Profile.tsx`.

### Q29: Does a 5-question multiple-choice assessment certify real expertise?
- **Simple Explanation:** No. It provides limited evidence of foundational syntax knowledge, not professional qualification.
- **Precise Technical Explanation:** The assessment bank tests core language concepts (e.g., immutability, scoping, joins). The UI and documentation prominently display: *"Five questions provide limited evidence, not professional verification."* Assessment evidence is capped at 25% of the suitability score, and seekers never need an assessment to ask questions.
- **Source File & Function:** `backend/app/main.py` (`questions`); `frontend/src/components/Assessment.tsx`.

### Q30: How do you prevent students from cheating on domain assessments?
- **Simple Explanation:** Questions and options are validated server-side, correct answer indexes are stripped from API responses, and attempts have a daily limit.
- **Precise Technical Explanation:**
  1. `GET /api/assessments/{domain}/questions` iterates questions and strips `correct` before serialization.
  2. The frontend sends only a dictionary of `{question_id: answer_index}`. The score is computed strictly on the backend.
  3. `POST /api/assessments/submit` checks recent attempts in SQLite and rejects more than 10 attempts per day with `429 Too Many Requests`.
- **Source File & Function:** `backend/app/main.py` (`questions`, `assess`).

---

## 7. Virtual Bounty Ledger & Financial Integrity

### Q31: How does the virtual bounty system work?
- **Simple Explanation:** Requesters attach virtual points when posting doubts. Points are reserved immediately and awarded to the mentor only when the requester confirms resolution.
- **Precise Technical Explanation:**
  1. On doubt creation, `svc.reserve_bounty` checks `student.points_balance >= bounty`.
  2. Points are deducted: `student.points_balance -= bounty`.
  3. A `BOUNTY_RESERVED` ledger row is inserted.
  4. If cancelled, `svc.refund_bounty` restores the points and logs `BOUNTY_REFUNDED`.
  5. Upon seeker confirmation (`resolve` action with `resolved == true`), `svc.award_bounty` credits the mentor and logs `BOUNTY_AWARDED`.
- **Source File & Function:** `backend/app/services.py` (`reserve_bounty`, `award_bounty`, `refund_bounty`).

### Q32: Why did you build a transaction ledger instead of just updating an integer column?
- **Simple Explanation:** A ledger provides an auditable history of every point change, preventing disputes and enabling exact reconciliation.
- **Precise Technical Explanation:** Updating an integer balance directly (`UPDATE students SET points = points + 10`) leaves no audit trail. If a balance is incorrect, it is impossible to determine whether a session was settled twice, a refund was missed, or a grant failed. `PointLedger` maintains an immutable append-only ledger with timestamp, transaction type, doubt ID, session ID, balance after, and unique reference ID.
- **Source File & Function:** `backend/app/models.py` (`PointLedger`).

### Q33: What happens if a session is unsuccessful or declined? Does the mentor get points?
- **Simple Explanation:** No. Mentors only receive points when the requester confirms successful resolution.
- **Precise Technical Explanation:** In `transition('resolve')`:
  ```python
  if body.resolved:
      doubt.status = 'RESOLVED'
      svc.award_bounty(db, mentor, session, doubt)
  else:
      doubt.status, doubt.assigned_session_id = 'OPEN', None
  ```
  If `resolved == false`, no award is made. The doubt returns to the queue, and the reserved bounty remains locked to the doubt so a future mentor can earn it.
- **Source File & Function:** `backend/app/main.py` (lines 485–497); `backend/tests/test_p0_features.py` (`test_unresolved_session_does_not_award_bounty_and_retains_reservation`).

### Q34: What prevents students from farming bounty points through collusive fake accounts?
- **Simple Explanation:** Points cannot be converted to real money, demo accounts start with bounded balances, and self-claiming is strictly blocked.
- **Precise Technical Explanation:**
  1. Points are purely virtual campus reputation markers.
  2. Self-assignment and self-claiming are rejected with `422 Unprocessable Entity` (`requester_id != mentor_id`).
  3. Initial grants are fixed at 100–150 points.
- **Honest Limitation:** In an open campus deployment without proctoring, two colluding students could create trivial doubts and confirm resolution to transfer points. Mitigating this would require daily transfer caps and graph-based collusion detection.

### Q35: How does doubt editing handle bounty adjustments?
- **Simple Explanation:** If you increase the bounty, the difference is deducted from your balance; if you decrease it, the difference is refunded.
- **Precise Technical Explanation:** `svc.adjust_bounty()` calculates $\Delta = \text{new\_bounty} - \text{doubt.bounty}$. If $\Delta > 0$, it validates `points_balance >= \Delta`, deducts $\Delta$, and records a `BOUNTY_ADJUSTED` transaction. If $\Delta < 0$, it credits $|\Delta|$ back to available points.
- **Source File & Function:** `backend/app/services.py` (`adjust_bounty`); `backend/tests/test_p0_features.py` (`test_doubt_editing_with_bounty_adjustment`).

---

## 8. Session Lifecycle, Timing & Workspace Messaging

### Q36: How does the authoritative 15-minute session timer work?
- **Simple Explanation:** The timer is calculated on the server from UTC timestamps; the client simply displays the remaining seconds without being able to manipulate them.
- **Precise Technical Explanation:** `Session` stores integer epoch timestamps: `start`, `end`, `actual_started_at`, `mentor_completed_at`. When serializing session data, the server computes:
  ```python
  data['server_time'] = m.now()
  if session.state == 'ACTIVE':
      data['active_seconds_remaining'] = max(0, session.end - m.now())
  ```
  The React frontend counts down locally every second, but re-synchronizes with `active_seconds_remaining` upon every 2.5s poll. Refreshing the browser or changing the OS clock has zero effect on the authoritative remaining time.
- **Source File & Function:** `backend/app/main.py` (`session_data`); `frontend/src/components/SessionWorkspace.tsx`.

### Q37: How do judges test the 15-minute timer without waiting 15 full minutes?
- **Simple Explanation:** Via an explicitly labeled 30-second demo clock endpoint that preserves database grid constraints.
- **Precise Technical Explanation:** `POST /api/sessions/{id}/accelerate` sets `session.is_demo_accelerated = True` and sets `actual_started_at = now()`. The server computes remaining demo seconds as `max(0, actual_started_at + 30 - now())`. This provides a fast 30-second live countdown for evaluation while keeping the database's `start` and `end` on the valid 15-minute grid (`start % 900 == 0`).
- **Source File & Function:** `backend/app/main.py` (`accelerate_session`); `frontend/src/components/SessionWorkspace.tsx`.

### Q38: How does the live session workspace prevent unauthorized access to messages?
- **Simple Explanation:** Only the assigned mentor and requester can view or send messages. Any other student gets 403 Forbidden.
- **Precise Technical Explanation:** In `GET` and `POST /api/sessions/{id}/messages`:
  ```python
  sess = svc.get(db, m.Session, id)
  doubt = svc.get(db, m.DoubtRequest, sess.doubt_id)
  svc.require(actor.id in (sess.mentor_id, doubt.requester_id), 'Only session participants can access messages', 403)
  ```
  If an unauthorized student ID is supplied in `X-Demo-Student-ID`, the endpoint aborts before querying or persisting message rows.
- **Source File & Function:** `backend/app/main.py` (`session_messages`, `send_message`); `backend/tests/test_p0_features.py` (`test_messaging_workspace_permissions_and_persistence`).

### Q39: Why did you choose incremental polling over WebSockets for live chat?
- **Simple Explanation:** HTTP polling is robust, firewall-friendly, has zero connection state leaks, and requires no complicated server infrastructure.
- **Precise Technical Explanation:** WebSockets introduce persistent stateful socket connections, requiring sticky sessions, socket heartbeats, reconnection logic, and distributed pub/sub brokers (like Redis) if scaled horizontally. Incremental HTTP polling (`GET /api/sessions/{id}/messages?since_id=...`) every 2.5s is lightweight, fully testable in standard FastAPI TestClient, and has zero connection leak risk.
- **Source File & Function:** `frontend/src/components/SessionWorkspace.tsx`.
- **Honest Limitation:** Messages have an average 1.25s propagation latency compared to sub-100ms WebSocket delivery.

### Q40: What happens if a mentor declines an offer or lets it expire?
- **Simple Explanation:** The reservation is safely released, and the system automatically finds an alternative eligible mentor.
- **Precise Technical Explanation:**
  1. Mentor decline calls `svc.release(db, session, 'DECLINED')`.
  2. The doubt's status returns to `OPEN` with `assigned_session_id = None`.
  3. The declining mentor is excluded from immediate reassignment by `feasible()`:
     `m.Session.state.in_(('DECLINED','CANCELLED'))`.
  4. Automatic dispatch evaluates the remaining queue and assigns the next best mentor.
  5. The original reserved bounty and urgency are fully preserved.
- **Source File & Function:** `backend/app/services.py` (`release`, `feasible`, `dispatch`); `backend/tests/test_e2e_workflows.py` (`test_decline_and_automatic_reassignment_workflow`).

---

## 9. Security, XSS, Validation & Identity

### Q41: How do you prevent Cross-Site Scripting (XSS) in chat and doubt descriptions?
- **Simple Explanation:** React escapes text by default, and we never use `dangerouslySetInnerHTML`.
- **Precise Technical Explanation:** All user-provided strings (`doubt.description`, `message.content`, `feedback.notes`) are rendered through standard React JSX expressions (`<p>{m.content}</p>`), which treat content as strings and auto-escape HTML entities (`<`, `>`, `&`, `"`). Code blocks are rendered inside standard `<pre><code>` blocks without arbitrary HTML evaluation.
- **Source File & Function:** `frontend/src/components/SessionWorkspace.tsx`; `frontend/src/components/DoubtBoard.tsx`.

### Q42: How does Pydantic validate input bounds?
- **Simple Explanation:** Strict Pydantic models forbid unknown fields and enforce length, range, and timezone constraints.
- **Precise Technical Explanation:** In `backend/app/schemas.py`, the base `Input` model sets `model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)`. Fields specify `min_length` and `max_length` (e.g., title 3–150 chars, description 5–3000 chars, rating 1–5). Field validators (`valid_domain`, `utc_time`) reject unknown domains and timezone-naive timestamps.
- **Source File & Function:** `backend/app/schemas.py`.

### Q43: What are the security limitations of the demo identity header?
- **Simple Explanation:** The `X-Demo-Student-ID` header is designed for quick hackathon evaluation, not production authentication.
- **Precise Technical Explanation:** In production, identity must be derived from a validated, cryptographically signed JWT bearer token issued by an OAuth2/OIDC identity provider (e.g., college Active Directory/Google Workspace). The current demo implementation extracts `x_demo_student_id` directly from request headers to allow judges to seamlessly toggle between seeker and mentor perspectives in a single browser window.
- **Source File & Function:** `backend/app/main.py` (`identity()`); `docs/LIMITATIONS.md`.

### Q44: Can a seeker resolve a session without mentor completion?
- **Simple Explanation:** No. The mentor must complete assistance first before the seeker can confirm resolution.
- **Precise Technical Explanation:** In `transition('resolve')`:
  ```python
  svc.require(session.mentor_completed, 'Mentor must complete session first')
  svc.require(session.state in ('ACTIVE', 'AWAITING_CONFIRMATION'), 'Session is not awaiting resolution')
  ```
  If a requester attempts to call `/api/sessions/{id}/resolve` while the mentor is still actively assisting, the backend returns `409 Conflict`.
- **Source File & Function:** `backend/app/main.py` (lines 477–482).

---

## 10. Benchmarks, Failure Recovery & Scaling

### Q45: What does your 50-scenario benchmark prove, and what does it NOT prove?
- **Simple Explanation:** It proves that Hungarian matching consistently achieves higher global utility than Greedy on identical candidate matrices. It does not prove better grades or academic learning.
- **Precise Technical Explanation:** The benchmark runner (`/api/benchmarks/run`) tests Hungarian and Greedy on 50 identical synthetic matrices with varying sparsity and urgency weights. Hungarian achieves higher total utility in ~84% of scenarios. However, this measures optimization against our mathematical objective function ($S \times U + W$). It does NOT prove pedagogical superiority or improved learning retention.
- **Source File & Function:** `backend/app/algorithms.py` (`benchmark`); `docs/ALGORITHM.md`.

### Q46: How does the system recover from an application server crash?
- **Simple Explanation:** SQLite WAL files preserve committed state, and the startup sweep automatically expires stale offers.
- **Precise Technical Explanation:**
  1. SQLite Write-Ahead Logging (`WAL`) guarantees ACID crash resilience.
  2. When the FastAPI application restarts, `lifespan()` runs database initialization and starts `expiration_loop()`.
  3. Any offers that expired while the server was offline are detected during the first sweep (`offer_expires_at <= current`) and released back to `OPEN`.
- **Source File & Function:** `backend/app/main.py` (`lifespan`, `expiration_loop`).

### Q47: If you had to scale this to 100,000 students across 10 universities, what would you change?
- **Simple Explanation:** Replace SQLite with PostgreSQL, move the dispatch coordinator to Celery/Redis, and use WebSockets for chat.
- **Precise Technical Explanation:**
  1. **Database:** Migrate from SQLite to PostgreSQL with read replicas and PgBouncer. Use row-level locking (`SELECT ... FOR UPDATE SKIP LOCKED`) for booking claims.
  2. **Matching Engine:** Shard dispatch runs by University and Academic Domain. Offload matching to background Celery workers running NumPy/SciPy `linear_sum_assignment`.
  3. **Messaging:** Migrate workspace chat to WebSockets backed by Redis Pub/Sub for horizontal fanout.
  4. **Authentication:** Implement OAuth2 / SAML with campus SSO and JWT authorization.
- **Source File & Function:** `docs/LIMITATIONS.md` (Section 2).

### Q48: What is the single most important technical achievement of this project?
- **Simple Explanation:** Delivering an end-to-end peer tutoring board where matching optimization, virtual bounties, and live session workspaces are completely integrated and proven by 50 passing automated tests.
- **Precise Technical Explanation:** Triage15 avoids both the pitfalls of empty hackathon mockups and the unpredictability of generative AI. Every single component—from the Kuhn-Munkres rectangular bipartite solver, to the double-entry integer point ledger, to the SQLite partial unique booking indexes, to the live chat workspace—is fully implemented, mathematically grounded, and verified by 50 automated tests with zero external cloud dependencies.
