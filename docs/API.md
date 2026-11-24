# REST API

Base URL: `http://127.0.0.1:8000`. React uses a Vite `/api` proxy. `/docs` serves interactive Swagger UI; `openapi.json` is a generated schema snapshot. Inputs reject unknown fields. All public records are synthetic and readable without identity. Mutation routes require a valid `X-Demo-Student-ID`, except demo profile registration. No passwords or real authentication exist.

## Shared contracts

- Missing/invalid shape, unknown domains/tags, invalid enum, naive timestamps, short titles/descriptions or impossible windows: 422.
- Unknown record/student: 404. Acting on another student's resource: 403.
- Invalid transition, booking constraint or repeated operation: 409.
- SQLite availability/lock error: 503 with a safe message.
- Lists may be empty. Timestamps in responses are UTC ISO strings; null denotes an omitted optional value.
- GET routes with DB access also expire stale offers; every database-backed route executes in one transaction.

`DoubtInput`: title 3–150 chars, description 5–3000, domain in catalog, 1–10 unique skill tags belonging to that domain, urgency Urgent/Normal/Flexible, optional preferred_start and deadline as ISO timestamps **with timezone**. A complete window must span at least 15 minutes and deadline must allow a future 15-minute interval.

`SessionOutput`: id, doubt_id, mentor_id, dispatch_run_id, start/end, state, offer_expires_at, mentor_completed, resolved, notes and explanation. Session GET/action results also include requester_id and feedback. A dispatch snapshot contains the offer fields without those enriched fields.

## General and profile routes

| Method / route | Input | Output / rules |
|---|---|---|
| GET `/api/health` | None | status and local-demo mode; no DB liveness probe |
| GET `/api/domains` | None | Domain → valid tags mapping |
| GET `/api/students` | None | All profiles, skill declarations, availability |
| POST `/api/students` | `{name}` 2–80 chars | 201 new synthetic profile, initially not mentoring; no header required |
| GET `/api/students/{id}` | Student ID | Profile plus completed/resolved counts and smoothed reliability; 404 unknown |
| PUT `/api/students/{id}/profile` | `{mentoring, skills:[{domain,tag,level}]}` | Replaces declared skills; owner only; level 1–5, max 40, no duplicates; 403/422 |
| POST `/api/students/{id}/availability` | `{start,end}` timezone-qualified | 201 window; owner only; ≥15 minutes, ≤24 hours long, ending within next seven days; max 30 windows; 422 invalid |
| DELETE `/api/students/{id}/availability/{window_id}` | IDs | `{deleted:true}`; owner only; 409 if live sessions overlap the removed window |
| GET `/api/metrics` | None | Counts by doubt/session status, actual successful resolutions, feedback count/mean |

## Assessments

| Method / route | Input | Output / rules |
|---|---|---|
| GET `/api/assessments/{domain}/questions` | Python, JavaScript or SQL | Five question IDs/prompts/options/version; **never correct answers**; 404 for other banks |
| POST `/api/assessments/submit` | `{domain,answers:{question_id:zero_based_option}}` | 201 attempt ID, student, domain, score, counts, timestamp/version; identity required; exact question set and valid answer indices required (422) |
| GET `/api/students/{id}/assessments` | Student ID | Attempt history, newest timestamp first; no response/answer-key exposure; 404 unknown student |

Scoring is performed on the backend from seeded answer keys. Optional assessment results do not automatically add declared profile skills. Other domains use provisional evidence. Repeated attempts are permitted; no test-integrity or anti-cheat guarantee exists.

## Doubts

| Method / route | Input | Output / rules |
|---|---|---|
| POST `/api/doubts` | DoubtInput | 201 request, requester from header, OPEN status, normalized skills |
| GET `/api/doubts` | Optional domain, skill, urgency, status, search query | Matching list, newest first; search checks title/description (max 150 chars); all filters combine with AND |
| GET `/api/doubts/{id}` | Request ID | Request detail or 404 |
| PATCH `/api/doubts/{id}` | Complete DoubtInput | Owner only; replace editable fields/skills on OPEN/UNMATCHED request; resets status OPEN; 409 if already assigned/closed. This MVP PATCH requires the full editable object, not a sparse patch. |
| POST `/api/doubts/{id}/cancel` | No body | Owner only; cancels its live session if present and marks doubt CANCELLED; 409 if already closed |

## Dispatch

| Method / route | Input | Output / rules |
|---|---|---|
| POST `/api/dispatch/run` | No body; any valid demo identity | Run ID, timestamp, assignments with score breakdown, same-matrix optimized/greedy comparison, candidate/resource counts, unassigned reasons, final-validation rejections; 422 batch too large, 409 integrity conflict, 503 DB unavailable |
| GET `/api/dispatch/runs/{id}` | Run ID | Stored immutable report with initial assignment snapshots; 404 unknown |
| GET `/api/dispatch/runs/{id}/assignments` | Run ID | Current persisted sessions from that run; 404 unknown |

Comparison reports describe solver output before final participant validation. `assignments` lists only successfully reserved offers. A response with zero assignments is not a successful match claim.

## Sessions

| Method / route | Input | Authorized actor / transition |
|---|---|---|
| GET `/api/sessions` | None | All demo sessions, newest slot first, including outcomes/feedback |
| GET `/api/sessions/{id}` | ID | Detail or 404 |
| POST `/api/sessions/{id}/accept` | No body | Assigned mentor; OFFERED → ACCEPTED; must not have expired |
| POST `/api/sessions/{id}/decline` | No body | Assigned mentor; OFFERED → DECLINED; doubt reopens |
| POST `/api/sessions/{id}/start` | No body | Assigned mentor; ACCEPTED → ACTIVE; doubt IN_SESSION; early demo start allowed |
| POST `/api/sessions/{id}/complete` | No body | Assigned mentor; ACTIVE, sets mentor_completed once |
| POST `/api/sessions/{id}/resolve` | `{resolved:boolean,rating:1..5,notes?:string}` | Requester; ACTIVE and mentor complete required; finalizes session and stores unique feedback; notes max 2000 chars; unresolved result reopens doubt |
| POST `/api/sessions/{id}/cancel` | No body | Either participant; OFFERED/ACCEPTED/ACTIVE → CANCELLED; doubt reopens |

Action routes share one implementation with an explicit allowlist and per-action transition checks. An unknown action returns 404. Every successful action returns enriched SessionOutput. Repeated acceptance/completion/resolution returns 409. Expiration is performed by the 10-second sweep and by database routes; expired offers cannot be accepted even before the next sweep. Declined/cancelled/unsuccessfully finalized mentor-request pairs are excluded from reassignment.

## Benchmark

| Method / route | Input | Output / rules |
|---|---|---|
| POST `/api/benchmarks/run` | No body; valid demo identity | Actual fixed-seed 50-scenario run, stored with ID and timestamp; both algorithm metrics per scenario and 9/8/8/1 illustration |
| GET `/api/benchmarks/{id}` | Run ID | Persisted result or 404 |

## Examples

```http
POST /api/doubts
Content-Type: application/json
X-Demo-Student-ID: student-08

{"title":"Python loop skips values","description":"I need help understanding my loop counter.","domain":"Python","skills":["python","loops"],"urgency":"Urgent"}
```

Response shape (IDs/time are illustrative):

```json
{"id":"generated-id","requester_id":"student-08","title":"Python loop skips values","description":"I need help understanding my loop counter.","domain":"Python","urgency":"Urgent","skills":["python","loops"],"status":"OPEN","assigned_session_id":null,"preferred_start":null,"deadline":null,"created_at":"2026-11-24T00:00:00+00:00"}
```

```powershell
$h = @{'X-Demo-Student-ID'='student-08'}
$run = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/dispatch/run -Headers $h
$offer = $run.result.assignments[0]
$mentor = @{'X-Demo-Student-ID'=$offer.mentor_id}
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/sessions/$($offer.id)/accept" -Headers $mentor
```

A duplicate call returns HTTP 409, `{"detail":"accept requires OFFERED; current state is ACCEPTED"}`. A caller who is not that mentor receives 403 instead. Demo users can impersonate another identity by changing the header: these checks demonstrate ownership logic, not authentication.
