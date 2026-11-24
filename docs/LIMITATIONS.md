# TRIAGE15 — SYSTEM LIMITATIONS & ENGINEERING BOUNDARIES

Honest engineering requires transparent disclosure of prototype assumptions, constraints, and operational trade-offs.

## Optional ML skill suggestions (November 24, 2026)

The new classifier is trained on 2,675 real Stack Overflow questions, not campus mentoring sessions. It covers eight existing tags across Python, JavaScript and SQL; CAD, Design, Mathematics and other tags remain manual. The selected Linear SVM achieved held-out micro F1 0.8736 and macro F1 0.8396. Joins F1 is only 0.6667; aggregation F1 is 0.6869. Scores are margins, not probabilities. No calibration or campus outcome study was performed.

Sampling by tag and recent creation time, historical tagging noise, truncated descriptions, and approximate near-duplicate detection limit generalization. Feature-count/threshold abstention is not reliable general out-of-domain detection. The 30 real-question allocation scenarios use simulated students, mentors, urgency and schedules; utility does not measure learning. The separate ML benchmark records actual persisted assignments and conflicts; the legacy benchmark's illustrative conflict estimates are not used as measured evidence.

Manual confirmation is mandatory before tags reach the existing doubt API. Missing artifacts/dependencies or `ML_ENABLED=false` retain manual operation. Joblib artifacts must come from the controlled local training pipeline. See [model card](MODEL_CARD.md), [dataset card](../data/DATASET_CARD.md), and [verification](ML_VERIFICATION.md). The latest full regression run passed 94 tests; older counts below describe the pre-ML documentation snapshot.

---

## 1. Classification of Current Boundaries

### Category A: Critical Blockers
- **Status:** **None.** All P0 critical product features (virtual bounty ledger, live session workspace, 15-minute authoritative timer, automatic matching, automatic reassignment, manual session claiming) and high-value P1 improvements (iterative conflict recovery, mentor credibility profiles, doubt editing, pending outcome handling, expanded benchmarks) are fully implemented and verified by 50 automated tests.

---

### Category B: Important Architectural Limitations

#### 1. SQLite Single-Writer Concurrency
- **Implementation Reality:** SQLite only permits one concurrent writer process. We enforce `PRAGMA journal_mode = WAL;` and wrap state-modifying booking transactions in `BEGIN IMMEDIATE`.
- **Limitation:** While read operations occur concurrently without blocking, write operations are queued sequentially. Under extreme campus loads (>1,000 writes/second), SQLite write serialization would become a throughput bottleneck.
- **Why It Is Defensible For Prototype:** For a single-campus prototype and hackathon evaluation, SQLite eliminates database server overhead, guarantees zero external dependency failures, and strictly enforces relational foreign keys and partial unique indexes.

#### 2. Demonstration Identity Header vs Cryptographic Authentication
- **Implementation Reality:** Student identity is passed via `X-Demo-Student-ID` in request headers.
- **Limitation:** Any client can forge this header to act as any demo student.
- **Why It Is Defensible For Prototype:** This is intentionally designed to allow judges and evaluators to switch between seeker and mentor roles in two clicks from the UI header dropdown. It is not production authentication. In production, this would be replaced with OAuth2/OIDC (College SSO) issuing signed JWT bearer tokens.

#### 3. Single-Instance Dispatch Coordinator
- **Implementation Reality:** Automatic dispatch is coordinated using an in-process `asyncio.Lock` inside the FastAPI application process.
- **Limitation:** If deployed across multiple horizontal backend replicas behind a load balancer, each instance would execute its own dispatch coordinator, risking overlapping dispatch sweeps (though database-level `BEGIN IMMEDIATE` and unique constraints still prevent duplicate bookings).
- **Production Solution:** Distributed lock coordinator via Redis Redlock or PostgreSQL transactional locks (`pg_try_advisory_xact_lock`).

---

### Category C: Acceptable Prototype Limitations

#### 1. Five-Question MCQ Assessments
- **Implementation Reality:** Each academic domain (Python, JavaScript, SQL) features a 5-question multiple-choice bank scored server-side.
- **Limitation:** Scoring 100% on 5 syntax questions indicates basic language familiarization, not deep architectural expertise or verified pedagogical capability.
- **Design Mitigation:** The UI and matching engine explicitly label this as *"Assessment evidence (not professional qualification)"* and allocate only 25 out of 100 suitability points to test evidence.

#### 2. Fixed 15-Minute Grid Discretization
- **Implementation Reality:** All sessions are strictly quantized into 15-minute intervals (`start % 900 == 0`, `end == start + 900`).
- **Limitation:** Participants cannot schedule arbitrary session lengths (e.g., 20 or 45 minutes) within the same allocation batch without re-gridding or multi-interval bin packing.
- **Why It Is Defensible:** 15-minute micro-mentoring intervals are the core problem statement thesis of Triage15, keeping student commitments brief, focused, and low-friction.

#### 3. Polling vs WebSockets for Live Messaging
- **Implementation Reality:** Workspace chat and status updates use incremental HTTP polling (`since_id`) every 2.5–4.0 seconds.
- **Limitation:** Chat messages have a maximum 2.5-second propagation delay compared to sub-millisecond WebSocket delivery.
- **Why It Is Defensible:** HTTP polling is robust, firewall-friendly, has zero connection state leaks, requires no complex socket heartbeat management, and worked reliably across 100% of automated test runs.

---

## 2. Future Production Scaling Roadmap

| Dimension | HackDay Prototype | Production Scale (100,000 Students) |
| :--- | :--- | :--- |
| **Database** | SQLite WAL on SSD | PostgreSQL with Read Replicas & Connection Pooling (PgBouncer) |
| **Authentication** | `X-Demo-Student-ID` header | OAuth2 / SAML College SSO with JWT Bearer Tokens & RBAC |
| **Real-time** | Incremental HTTP polling (2.5s) | WebSockets with Redis Pub/Sub cluster |
| **Matching Coordination** | In-process `asyncio.Lock` | Celery / RabbitMQ background task queue with Redis distributed locks |
| **Bounty Accounting** | SQLite integer `point_ledger` | Immutable event-sourced ledger with append-only verification |
| **Assessment Engine** | 5-question MCQ bank | Adaptive item response theory (CAT) with randomized coding sandboxes |
