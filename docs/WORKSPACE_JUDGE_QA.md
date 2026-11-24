# Triage15 — Mentoring Workspace Judge Defense Q&A

This document provides exact, engineering-grounded answers to architectural, security, and algorithmic questions regarding the Triage15 Mentoring Workspace.

---

### 1. Why not simply use Google Meet alone?
Google Meet handles video and audio streaming, but cannot manage peer doubt queues, algorithmic mentor matching (Hungarian optimization), skill assessments, 15-minute slot commitments, persistent code snippet exchange, textual diff tracking, or reputation bounty settlement. Triage15 provides the coordination, matching, and learning outcome layer; Google Meet is merely an optional communication vehicle.

### 2. Why did you not build native video calling (e.g. WebRTC)?
Building a native WebRTC video/audio calling stack with STUN/TURN/SFU infrastructure within a hackathon timebox introduces significant network, firewall, and latency failure modes without adding core academic value. Reusing battle-tested Google Meet via manual attachment lets students use reliable screen sharing and audio while keeping Triage15 focused on algorithmic dispatch and structured resolution tracking.

### 3. Is the Google Meet video embedded inside Triage15?
No. Google Meet does not allow embedding full interactive meeting interfaces in external `<iframe>` elements due to `X-Frame-Options: SAMEORIGIN` and strict CSP headers. Attempting to iframe it results in broken interfaces. Triage15 provides safe external launch buttons (`target="_blank" rel="noopener noreferrer"`).

### 4. Does Triage15 generate actual meeting rooms automatically?
No. Generating meeting rooms programmatically requires Google Workspace Domain-wide Delegation, Google Calendar REST API OAuth provisioning, and Google Cloud credentials. For this hackathon, we implemented a resilient manual attachment workflow: the mentor clicks to open Google Meet in a tab, generates a link, and pastes it into Triage15.

### 5. How do you validate meeting links?
Server-side validation in `app.schemas.MeetingInput` parses the URL using Python's `urllib.parse` and regex:
1. Scheme must be strictly `https`.
2. Netloc must be exactly `meet.google.com` (case-insensitive).
3. Rejects user credentials, query strings, and redirects (e.g., `?redirect=...`).
4. Path must match the standard 3-4-3 Google Meet meeting code regex `^[a-z]{3}-[a-z]{4}-[a-z]{3}$`.
Lookalike domains, IP addresses, and script injection URLs are rejected with HTTP 422.

### 6. Can another student access a private meeting link?
No. Endpoints `GET /api/sessions/{id}/meeting`, `PUT`, and `DELETE` enforce participant authorization at the FastAPI dependency layer. If the requesting student (`X-Demo-Student-ID`) is neither the assigned mentor nor the requester, the server returns HTTP 403 Forbidden. Meeting links are never exposed in public doubt or session feeds.

### 7. How is code stored?
Code is stored as structured records in the SQLite `session_code_snippets` table with fields for `session_id`, `author_id`, `title`, `filename`, `language`, `snippet_type` (`ORIGINAL`, `PROPOSED_FIX`, `EXAMPLE`, `ERROR_LOG`), `parent_snippet_id`, and `content` (up to 64KB).

### 8. Is submitted code executed?
No. Submitted code is treated strictly as untrusted text. Triage15 does not run a remote code execution sandbox or containerized compiler.

### 9. How do you prevent malicious HTML or JavaScript execution?
React automatically escapes all string interpolation in JSX, rendering raw HTML and scripts inert. Code is presented in `<pre><code>` blocks without using `dangerouslySetInnerHTML`. Even if a user submits `<script>alert('xss')</script>`, the browser renders it purely as text characters.

### 10. How does the code comparison algorithm work?
The backend uses Python's standard library `difflib.SequenceMatcher` (`svc.compute_snippet_diff`). It splits the original and proposed snippets into line arrays and computes matching opcodes (`equal`, `insert`, `delete`, `replace`). It returns a structured JSON payload containing categorized lines (`added`, `removed`, `unchanged`) and counts.

### 11. Does the diff verify that the code is correct?
No. The textual diff only visualizes what lines changed between the two text blobs. It does not execute tests or verify syntax. Both the frontend and documentation include explicit disclosures explaining this limitation.

### 12. What happens if the mentor's proposed solution is wrong?
The requester retains sole authority over outcome confirmation. When reviewing the mentor's solution, the requester can click **"Problem Not Resolved (Keep in Queue)"**. This marks the session as unconfirmed, prevents any bounty points from being awarded to the mentor, and returns the doubt to `OPEN` status for automatic reassignment.

### 13. Who confirms that a doubt was resolved?
Exclusively the student who posted the doubt (the requester). The mentor can only mark their assistance as complete and draft a structured resolution. The resolution transition requires the requester's explicit confirmation (`POST /api/sessions/{id}/resolve`).

### 14. How do you prevent duplicate bounty settlement?
The ledger service (`svc.award_bounty`) enforces idempotent settlement:
1. It executes within a serialized SQLite transaction (`BEGIN IMMEDIATE`).
2. It generates a unique reference ID `award:{session.id}`.
3. It checks for existing entries with that reference ID before creating a `BOUNTY_AWARDED` transaction.
4. Calling `/resolve` a second time is rejected because the session has already transitioned out of `AWAITING_CONFIRMATION`.

### 15. What happens if the requester never confirms?
When the mentor submits a resolution, the session enters `AWAITING_CONFIRMATION` with an `outcome_deadline` set to 24 hours (`now() + 86400`). If the deadline expires without requester confirmation, the background expiration loop handles expiry without releasing unearned bounty points.

### 16. Can students access previous solutions?
Yes. The `GET /api/students/{id}/solution-history` endpoint returns a private historical ledger of all sessions the student participated in (as either mentor or requester), including root causes, solution explanations, shared code snippets, ratings, and feedback.

### 17. How do you protect private code and conversation history?
All snippet, chat, and resolution endpoints enforce student authorization against the session's `mentor_id` and the doubt's `requester_id`. Attempts by third-party students to access or compare snippets return HTTP 403 Forbidden. Solution history is restricted to `student.id == actor.id`.

### 18. Does the mentoring workspace work without Google Meet?
Yes, 100%. Google Meet is an optional enhancement. If participants do not use video, they can solve the entire doubt using real-time text messaging, the code snippet exchange, and the diff viewer.

### 19. What happens when the 15-minute timer ends but the Meet call continues?
The Triage15 timer tracks the scheduled allocation window. When the timer reaches 00:00, Triage15 flags that the scheduled slot has ended and prompts participants to submit the resolution. Because Google Meet runs externally, the video call does not abruptly drop, allowing peers to say goodbye and wrap up naturally.

### 20. How would you improve this communication architecture in production?
In a post-hackathon production deployment:
1. Implement Google Workspace OAuth 2.0 with the Google Calendar API to provision meeting URLs programmatically on demand.
2. Integrate WebAssembly-based client-side syntax highlighting (Prism.js / Shiki).
3. Add a sandboxed container runner (e.g. gVisor / Firecracker) for optional safe code execution and unit testing.
4. Replace the demo identity switcher header with JWT-based session tokens and SSO.
