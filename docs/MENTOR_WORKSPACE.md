# Triage15 — Mentoring Workspace Architecture & Workflow Guide

## Overview

The **Mentoring Workspace** transforms Triage15 from a purely algorithmic mentor-allocation system into a full peer-to-peer problem-solving environment. Once a mentor accepts an assigned session, both the mentor and requester collaborate within an integrated workspace providing:

1. **Manual Google Meet Integration**: External voice, video, and screen sharing via validated HTTPS meeting links.
2. **Persistent Code Snippet Exchange**: Structured exchange of original code, error logs, and proposed solutions.
3. **Before-and-After Code Comparison**: Deterministic textual line diff (`difflib`) highlighting additions and deletions.
4. **Structured Resolution Records**: Technical explanations of root cause, solution rationale, and follow-up steps.
5. **Persistent Solution History**: Private searchable archive allowing students to revisit resolved and attempted solutions.
6. **Integrity-Preserving Bounty Settlement**: Resolution confirmation directly triggers exactly-once reputation point transfers.

---

## 1. Complete Mentoring Workflow

```
[ Doubt Request ] (Bounty Reserved)
       │
       ▼
[ Hungarian Match / Claim ] ──► Session OFFERED ──► Mentor Accepts ──► Session ACCEPTED
                                                                          │
       ┌──────────────────────────────────────────────────────────────────┴─────────────┐
       ▼                                                                                ▼
[ External Google Meet ]                                                    [ Persistent Workspace ]
 - Mentor generates meet.google.com link                                      - Live chat & countdown timer
 - Validated & attached via API                                              - Original code snippet posted
 - Both peers join external call in tab                                       - Mentor posts proposed solution
       │                                                                                │
       └───────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
                              [ Before-and-After Diff ]
                               - Line-by-line inspection
                               - Additions & deletions
                                           │
                                           ▼
                             [ Structured Resolution ]
                               - Mentor documents root cause & fix
                               - Mentor submits resolution
                               - Session enters AWAITING_CONFIRMATION
                                           │
                                           ▼
                            [ Requester Outcome Review ]
                               - Requester reviews solution & diff
                               - Submits rating (1–5) & feedback
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
            [ Confirm Resolved ]                        [ Confirm Unresolved ]
             - Session: RESOLVED                         - Doubt returns to OPEN
             - Bounty: Awarded to Mentor                 - Bounty remains reserved
             - Stored in Solution History                - Reassignment triggered
```

---

## 2. Technical Capabilities

### 2.1 Google Meet Attachment & URL Validation
- **Architecture**: External communication channel. Triage15 does not embed Google Meet in an iframe or provision accounts through OAuth during hackathon scope.
- **Server-Side Validation**:
  - Enforces `https` scheme.
  - Enforces exact hostname: `meet.google.com` (rejects lookalike domains, subdomains, or credentials).
  - Validates meeting code regex `^[a-z]{3}-[a-z]{4}-[a-z]{3}$`.
  - Rejects embedded credentials, script URIs, and query redirects.
- **Permissions**: Only the assigned mentor can attach, replace, or remove the meeting link. Both participants can retrieve it.

### 2.2 Persistent Code Snippet Exchange
- **Entity**: `SessionCodeSnippet` stored in SQLite with foreign-key linkage to `sessions.id` and `students.id`.
- **Classification**:
  - `ORIGINAL`: Requester's broken code or context.
  - `PROPOSED_FIX`: Mentor's suggested correction (linked via `parent_snippet_id`).
  - `EXAMPLE`: Demonstration pattern or library reference.
  - `ERROR_LOG`: Console trace, traceback, or compiler output.
  - `OTHER`: Notes, SQL queries, or configuration.
- **Security**: Treated as untrusted text. Stored with a 64KB size limit. Code is never evaluated or executed on the server or in the browser.

### 2.3 Textual Line Diff (`difflib`)
- Deterministic diff computation powered by Python standard library `difflib.SequenceMatcher`.
- Classifies each line as `added`, `removed`, or `unchanged`.
- Computes `added_count` and `removed_count`.
- Side-by-side / line-by-line colored visualization in the frontend with copy actions.

### 2.4 Structured Resolution Records
- Entity: `SessionResolution` associated 1:1 with `Session`.
- Fields:
  - `root_cause`: Deep explanation of the bug or conceptual misunderstanding.
  - `solution_explanation`: Step-by-step resolution rationale.
  - `follow_up_steps`: Optional advice or library recommendations.
  - `original_snippet_id` & `corrected_snippet_id`: Direct foreign-key links to snippets.
  - `reference_urls`: Validated documentation links.
  - `requester_status`: `PENDING` ➔ `CONFIRMED_RESOLVED` | `CONFIRMED_UNRESOLVED`.

### 2.5 Personal Solution History
- Private query endpoint: `GET /api/students/{id}/solution-history`.
- Returns all mentoring engagements (both as mentor and requester) with associated resolutions, snippets, star ratings, and feedback.
- Accessible via the "Solution history" tab in the frontend.

---

## 3. Database Schema

```sql
CREATE TABLE session_meetings (
    session_id VARCHAR PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    meeting_url VARCHAR NOT NULL,
    attached_by_id VARCHAR NOT NULL REFERENCES students(id),
    attached_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE session_code_snippets (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    author_id VARCHAR NOT NULL REFERENCES students(id),
    title VARCHAR NOT NULL,
    filename VARCHAR,
    language VARCHAR NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    snippet_type VARCHAR NOT NULL DEFAULT 'ORIGINAL',
    parent_snippet_id VARCHAR REFERENCES session_code_snippets(id),
    created_at INTEGER NOT NULL,
    CONSTRAINT chk_snippet_content CHECK (length(content) > 0 AND length(content) <= 65536),
    CONSTRAINT chk_snippet_type CHECK (snippet_type IN ('ORIGINAL', 'PROPOSED_FIX', 'EXAMPLE', 'ERROR_LOG', 'OTHER'))
);

CREATE TABLE session_resolutions (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    doubt_id VARCHAR NOT NULL REFERENCES doubts(id),
    mentor_id VARCHAR NOT NULL REFERENCES students(id),
    requester_id VARCHAR NOT NULL REFERENCES students(id),
    root_cause TEXT NOT NULL,
    solution_explanation TEXT NOT NULL,
    follow_up_steps TEXT,
    original_snippet_id VARCHAR REFERENCES session_code_snippets(id),
    corrected_snippet_id VARCHAR REFERENCES session_code_snippets(id),
    reference_urls JSON,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    submitted_at INTEGER,
    confirmed_at INTEGER,
    requester_status VARCHAR NOT NULL DEFAULT 'PENDING',
    CONSTRAINT chk_requester_status CHECK (requester_status IN ('PENDING', 'CONFIRMED_RESOLVED', 'CONFIRMED_UNRESOLVED'))
);
```

---

## 4. API Endpoints

| Method | Path | Description | Access Control |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/sessions/{id}/meeting` | Get attached Google Meet URL | Session participants |
| `PUT` | `/api/sessions/{id}/meeting` | Attach / replace meeting URL | Assigned mentor only |
| `DELETE` | `/api/sessions/{id}/meeting` | Remove meeting link | Assigned mentor only |
| `GET` | `/api/sessions/{id}/snippets` | List session snippets | Session participants |
| `POST` | `/api/sessions/{id}/snippets` | Share new code snippet | Session participants |
| `GET` | `/api/sessions/{id}/snippets/{snip_id}` | Retrieve specific snippet | Session participants |
| `GET` | `/api/sessions/{id}/snippets-diff` | Compute diff between two snippets | Session participants |
| `GET` | `/api/sessions/{id}/resolution` | Get resolution record | Session participants |
| `PUT` | `/api/sessions/{id}/resolution` | Draft / update resolution record | Assigned mentor only |
| `POST` | `/api/sessions/{id}/resolution/submit` | Finalize & submit resolution | Assigned mentor only |
| `GET` | `/api/students/{id}/solution-history` | List personal solution records | Student owner only |

---

## 5. Known Limitations & Edge Cases

1. **External Call Disconnect**: The 15-minute Triage15 session timer tracks platform availability and settlement deadlines. It cannot force-disconnect an external Google Meet tab.
2. **Untrusted Code Execution**: Triage15 does not execute or sandbox submitted code snippets; code comparison is purely textual.
3. **URL Validation Scope**: Server validation verifies that the link format is syntactically a legitimate `meet.google.com` room, but does not query Google servers to check room occupancy or expiration.
4. **Demo Identity Switching**: The `X-Demo-Student-ID` header is designed for rapid hackathon testing and evaluation; it is not cryptographic multi-tenant authentication.
