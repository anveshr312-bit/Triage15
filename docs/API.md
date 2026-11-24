# TRIAGE15 — REST API CONTRACTS & SPECIFICATION

All endpoints use JSON payloads and return UTC ISO strings for timestamps (`YYYY-MM-DDTHH:MM:SS+00:00`). The client formats them in Asia/Kolkata (`en-IN`).

Authentication uses the `X-Demo-Student-ID` header. This is a local demo convention, not production authentication.

---

## 1. System & Time Endpoints

### `GET /api/health`
System operational status and environment mode.
- **Response `200 OK`:**
```json
{
  "status": "ok",
  "mode": "local demo; synthetic profiles; authoritative server clock"
}
```

### `GET /api/server-time`
Authoritative server clock for countdown timer synchronization without client clock skew.
- **Response `200 OK`:**
```json
{
  "now": 1795500000,
  "iso": "2026-11-24T05:30:00+00:00",
  "timezone": "Asia/Kolkata (IST)"
}
```

### `GET /api/domains`
Allowed academic domains and valid skill tags.
- **Response `200 OK`:**
```json
{
  "Python": ["python", "loops", "pandas", "debugging"],
  "JavaScript": ["javascript", "react", "async", "debugging"],
  "SQL": ["sql", "joins", "aggregation", "schema"],
  "CAD": ["cad", "sketching", "constraints"],
  "Design": ["design", "typography", "layout"],
  "Mathematics": ["algebra", "calculus", "probability"]
}
```

---

## 2. Students, Profiles & Reputation Ledger

### `GET /api/students`
List all demo students with declared skills, availability, and reputation point balances.

### `POST /api/students`
Register a synthetic demo student. Automatically creates an `INITIAL_GRANT` transaction for 100 points.
- **Body:** `{"name": "Priya Sharma (demo)"}`
- **Response `201 Created`:** Serialized Student object.

### `GET /api/students/{id}`
Get individual student details, availability windows, and historical reliability heuristic.

### `GET /api/students/{id}/ledger`
Retrieve the complete immutable double-entry transaction history of reputation points for this student.
- **Response `200 OK`:**
```json
[
  {
    "id": "ledger-uuid",
    "student_id": "student-08",
    "amount": -40,
    "transaction_type": "BOUNTY_RESERVED",
    "doubt_id": "doubt-uuid",
    "session_id": null,
    "reference_id": "reserve:doubt-uuid",
    "balance_after": 110,
    "created_at": "2026-11-24T05:32:00+00:00",
    "notes": "Reserved 40 points for doubt bounty"
  }
]
```

### `GET /api/mentors/{id}/profile`
Mentor Credibility Profile (P1.4) providing transparent outcome statistics.
- **Response `200 OK`:**
```json
{
  "id": "student-01",
  "name": "Asha (demo)",
  "mentoring": true,
  "points_balance": 175,
  "completed_sessions": 3,
  "resolved_sessions": 2,
  "resolution_rate": 66.7,
  "resolution_history_label": "66.7% (2/3 sessions)",
  "feedback_count": 3,
  "average_rating": 3.67,
  "bounties_earned": 50,
  "smoothed_reliability_heuristic": 8.57
}
```

---

## 3. Doubt Requests & Bounties

### `GET /api/doubts`
Query doubts with filtering and searching.
- **Query Params:** `domain`, `skill`, `urgency`, `status`, `search` (max 150 chars).

### `POST /api/doubts`
Create a technical doubt request with an optional reputation bounty.
- **Headers:** `X-Demo-Student-ID: <id>`, optional `X-Auto-Dispatch: true`.
- **Body:**
```json
{
  "title": "Python: recursion base case",
  "description": "Infinite recursion in DFS tree traversal",
  "domain": "Python",
  "skills": ["python", "debugging"],
  "urgency": "Urgent",
  "bounty": 40,
  "preferred_start": "2026-11-24T06:00:00+00:00",
  "deadline": "2026-11-24T09:00:00+00:00"
}
```
- **Response `201 Created`:** Serialized Doubt with reserved bounty.
- **Errors:** `422 Unprocessable Entity` if bounty exceeds available points balance or skills invalid.

### `PATCH /api/doubts/{id}`
Edit an open or unmatched doubt. Re-evaluates bounty delta safely transactionally.
- **Body:** Same schema as `POST /api/doubts`.
- **Response `200 OK`:** Updated Doubt.

### `POST /api/doubts/{id}/cancel`
Cancels the request. If an unawarded bounty was reserved, immediately creates a `BOUNTY_REFUNDED` transaction and restores points to requester.
- **Response `200 OK`:** Doubt with status `CANCELLED`.

### `POST /api/doubts/{id}/claim` (P0.6 Manual Claiming)
Enables an eligible mentor to directly claim an open doubt without waiting for dispatch.
- **Headers:** `X-Demo-Student-ID: <mentor_id>`.
- **Body:** Optional `{"slot_start": "2026-11-24T06:00:00+00:00"}`.
- **Response `200 OK`:** Created Session in `ACCEPTED` state.
- **Errors:**
  - `409 Conflict`: If doubt is already claimed/matched or mentor is double-booked.
  - `422 Unprocessable Entity`: If mentor lacks matching skills, is not mentoring, or attempts self-claim.

---

## 4. Sessions & Live Workspace

### `GET /api/sessions`
List sessions. Returns full context: requester/mentor names, doubt title, bounty, scheduled times, and server time.

### `GET /api/sessions/{id}`
Detailed session status and timer metadata.

### `GET /api/sessions/{id}/messages`
Retrieve message thread for the live workspace.
- **Query Params:** Optional `since_id` or `since_time`.
- **Headers:** `X-Demo-Student-ID: <participant_id>`.
- **Errors:** `403 Forbidden` if caller is not the assigned mentor or requester.

### `POST /api/sessions/{id}/messages`
Post a message or code snippet to the live session room.
- **Body:** `{"content": "def fix(): return True"}` (1–4000 chars).
- **Response `201 Created`:** Persisted `SessionMessage`.

### `POST /api/sessions/{id}/accelerate` (P0.3 Demo Clock)
Switches session to 30-second accelerated evaluation clock for judge demonstration.
- **Response `200 OK`:** Updated Session with `is_demo_accelerated: true`.

### `POST /api/sessions/{id}/{action}`
State lifecycle transitions:
- `accept` (Mentor): Moves `OFFERED` -> `ACCEPTED`.
- `decline` (Mentor): Releases reservation, marks `DECLINED`, returns doubt to `OPEN` for reassignment.
- `start` (Mentor): Validates start window, moves `ACCEPTED` -> `ACTIVE`.
- `complete` (Mentor): Flags assistance concluded, moves to `AWAITING_CONFIRMATION`.
- `resolve` (Requester): Final outcome confirmation.
  - Body: `{"resolved": true, "rating": 5, "notes": "Resolved quickly"}`.
  - Awards bounty to mentor if `resolved == true`.
- `cancel` (Either participant): Closes live session. Refunds bounty if cancelled by seeker.

---

## 5. Assessments, Dispatch & Benchmarks

### `GET /api/assessments/{domain}/questions`
Get 5 domain questions. Question order and option ordering are stable; correct answer is never exposed.

### `POST /api/assessments/submit`
Submit answers. Scored strictly on the backend. Enforces daily attempt cooldown (max 10 attempts/day).

### `POST /api/dispatch/run`
Execute manual dispatch across all `OPEN` and `UNMATCHED` doubts using rectangular Hungarian matching with iterative conflict recovery.
- **Response `200 OK`:** Dispatch run summary with comparisons, rejections, and assignments.

### `POST /api/benchmarks/run`
Run reproducible 50-scenario benchmark comparing Hungarian matching vs Greedy allocation.
