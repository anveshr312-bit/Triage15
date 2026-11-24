# Implemented scope and honest limits

Implemented: local persistent relational storage; demo profiles, skill declarations, availability; optional three-domain MCQs; doubts and filters; explainable score; Hungarian and greedy matching; actual 50-case benchmark; reserved expiring offers; ownership checks; accept/decline/start/mentor-complete/seeker-outcome/cancel; feedback and record-derived metrics; React UI; tests and documentation.

## Prototype limits

- Only synthetic data. There are no verified campus identities, production authentication, passwords, real communication channels or email/push notifications. Anyone with API access can select any identity. Bind to loopback only.
- Five MCQs are limited assessment evidence. The provisional prior is a heuristic, not proof. Repeated attempts are allowed and answer keys can be read by a developer with source/database access. No anti-cheat, rate limiting, assessment cooldown or identity-based rating-abuse protection exists.
- Matching optimizes a fixed bipartite matrix. Extra shared-requester/cross-role conflicts can remove selected pairs in final validation, so actual persisted bookings need not be a constrained global optimum. Reported solver utility and count precede those rejections; offer counts reflect actual bookings.
- Dispatch is manual. Declines/expiry/negative outcomes release the request; press Run dispatch again for reassignment. A declined, cancelled or unsuccessful mentor is excluded for that request, even after editing it. There is no exclusion-reset endpoint.
- Exact catalog domain/tag matching only; no semantic skill inference. Required tags use partial overlap eligibility. Declared level is displayed separately and does not increase the score. Latest assessment uses second-resolution timestamps plus deterministic ID tie breaking.
- The bounded age bonus cannot guarantee fairness or prevent starvation. Urgency is self-reported. The platform does not guarantee that a problem can be solved or that a mentor will attend.
- No ML model and no validated probability of expertise or resolution. Feedback affects displayed metrics, not scoring; actual resolution outcomes drive the reliability heuristic.
- SQLite serializes writers; this MVP serializes DB reads too. Per-edge evidence/availability SQL queries are deliberately simple and inefficient for large batches. Seven-day candidate horizon; max 200 requests, 2,000 slots, 30 availability windows per profile. No pagination, production migrations, queue, tracing or load-test claim.
- Availability slots are fixed at 15 minutes on a UTC grid. There is no arbitrary-duration support or requester availability calendar beyond per-request time bounds. The demo allows early start/completion without a wall-clock gate, while reservations continue to use scheduled intervals. Timing enforcement would be needed for real operation.
- Accepted/active sessions do not auto-close at scheduled end. Mentor completion requires seeker outcome before entering finalized reliability history. Pending outcomes need manual follow-up. Session state RESOLVED means finalized, with `resolved=false` explicitly recording an unsuccessful outcome.
- The UI provides all core flows; request editing is API-only (full editable object). The UI shows session request IDs rather than a dedicated request-detail route. Window removal is conservatively blocked if any live reservation overlaps, even if another overlapping window would cover it.
- Read APIs expose all synthetic profiles and sessions. This is appropriate only for the demo, not real student data. CORS is restricted but is not authentication.
- Benchmarks use reproducible synthetic eligibility matrices, not real students or deployment traffic. Solver runtime excludes candidate generation/SQL. There is no guaranteed improvement in assignment count or urgent assignment rate.
- The seed creates tables only if needed and does not renew old availability on every startup. Run explicit reset to refresh a stale demo; it destroys local demo changes. No schema migration system is included.

## Next work, not claimed as implemented

Production identity and per-record privacy; PostgreSQL migrations/row locks/exclusion constraints; an exact optimizer for shared-person conflicts; batched evidence loading; background dispatch jobs; notifications; assessment version management; fair urgency policy; accessible automated browser regression coverage; real-user evaluation and feedback abuse controls. No hosting/deployment or external integrations were attempted because the requested MVP runs locally.
