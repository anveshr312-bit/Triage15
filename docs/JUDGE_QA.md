# Technical judge Q&A

Answers describe this implementation, not a production roadmap disguised as completed work.

## 1. Why FastAPI?

It provides typed request validation, structured HTTP errors and generated OpenAPI with a small Python codebase. Matching, tests and backend share Python. Routes use SQLAlchemy transactions rather than putting business decisions in React. It is not inherently a scaling solution.

**Skeptical follow-up:** Are your routes asynchronous? Database routes are synchronous and run in FastAPI's worker pool; the expiration task delegates synchronous database work to a thread.

## 2. Why SQLite?

The MVP must run locally with no database server. SQLite provides persistent transactions, foreign keys and partial indexes. `BEGIN IMMEDIATE` serializes booking validation and insertion. It limits concurrency and is not presented as a campus-scale deployment database.

**Follow-up:** Can it handle many writers? One writer at a time; a 15-second busy timeout and safe 503 response handle contention, but long batches will still bottleneck.

## 3. Why not MongoDB?

Requests, sessions, participants, assessments and feedback have explicit relational links and uniqueness rules. SQLite expresses them directly with foreign keys and indexes, without introducing a server. MongoDB could be used with careful modeling and transactions, but would add no necessary local-MVP advantage here.

**Follow-up:** Do JSON columns undermine that choice? JSON holds question option arrays and calculation/report snapshots; operational relationships remain normalized.

## 4. Why not an LLM?

The decision is a constrained resource-allocation problem. Deterministic scores and exact matrix optimization make reasons reproducible and testable, require no API keys and introduce no generated skill claims. The system does not need natural-language generation to allocate a slot.

**Follow-up:** Does it understand the description? No. Eligibility uses explicit domain and tags; description is for peers to read.

## 5. Why is this better than filtering?

Filtering answers which pairs are eligible. It cannot choose a joint assignment when the best mentor is also the only good option for another request. Hungarian matching maximizes the sum of eligible utilities over the candidate graph; the 9/8/8/1 example demonstrates the distinction.

**Follow-up:** Better for every individual? No. A student may receive their second-best mentor because the overall allocation improves.

## 6. Why Hungarian matching?

Each request needs one resource and each mentor-grid-slot serves one request, forming a weighted bipartite problem. The rectangular Hungarian implementation handles dummy unmatched resources and returns an optimal matrix allocation. It is pure Python and independently tested against exhaustive enumeration.

**Follow-up:** Is the final schedule always globally optimal? No. Additional shared-person conflicts across new assignments are rejected afterward; that safe subset may be suboptimal under the richer constraint set.

## 7. What is bipartite matching?

Two disjoint node sets represent requests and mentor-slot resources. An eligible pair is an edge with utility. Matching chooses edges without repeating a node. A mentor may appear in multiple resource nodes at distinct non-overlapping slots.

**Follow-up:** Why not one node per mentor? That would incorrectly limit them to one session across the whole scheduling horizon.

## 8. What is the time complexity?

With n requests and m real resources, the rectangular Hungarian solver takes O(n²(m+n)) after adding n dummy columns. Matrix memory is O(n(m+n)). Greedy sorts E edges in O(E log E). SQL-based eligibility and evidence queries add overhead that solver timing excludes.

**Follow-up:** Where will it become slow first? Per-edge database work and holding the serialized transaction, which should be replaced with preloaded indexed evidence for larger batches.

## 9. How do you prevent double booking?

All slots last exactly 900 seconds and align to the same grid, enforced by CHECK constraints. Partial unique indexes prohibit duplicate live mentor/start pairs and duplicate live doubt assignments. A serialized transaction rechecks availability and participant conflicts before each insert.

**Follow-up:** Would the index work for arbitrary durations? No; a general overlap exclusion constraint or normalized participant reservations would be needed.

## 10. What happens during concurrent requests?

SQLite `BEGIN IMMEDIATE` takes a write reservation before reads, so a second dispatch sees the first one's committed reservations after waiting. Automated tests submit two dispatches from separate threads and verify unique doubt/resource bookings. Lock failures return 503; integrity failures return 409.

**Follow-up:** Is this a stress test? No. It proves a focused two-caller race, not production throughput or high-load stability.

## 11. How do you handle mentor cancellation?

A participant may cancel a live session. The session remains as CANCELLED history, its reservation is released, and the doubt reopens. That mentor-request pair is excluded from subsequent dispatch, as are declines and unsuccessful finalized outcomes. The next dispatch seeks other eligible mentors.

**Follow-up:** Is redispatch automatic? No. It is explicitly triggered by the local Run dispatch control.

## 12. What if no mentor is available?

Unavailable pairs never enter the candidate matrix. Dummy resources permit the solver to leave a request unmatched. The report distinguishes no eligible slot from waiting due to allocated capacity or a final participant conflict. The Mathematics seed example intentionally has no available mentor.

**Follow-up:** Do you call that success? The dispatch computation can finish successfully, but the request stays UNMATCHED and no session is invented.

## 13. How is mentor skill measured?

Profiles store self-declared domain/tag levels. Optional MCQs store attempts, scores, counts, version and responses separately. Finalized session outcomes drive smoothed reliability. Feedback stars are shown separately and are not hidden scoring inputs.

**Follow-up:** Does level 5 beat level 1 automatically? No; declared level is displayed, while declared tag overlap determines the relevance component.

## 14. Can five MCQs verify expertise?

No. The interface says assessment evidence, not professional verification. Scores provide a limited signal for the domain, not proof of mentoring ability, depth, honesty or teaching skill.

**Follow-up:** Can users memorize answers? Yes. Attempts are repeatable and the bank is static; anti-cheat is outside this demo.

## 15. How do you handle cold-start mentors?

No assessment uses a limited 10/25 prior and 4/10 confidence. Reliability begins at 15×2/4=7.5, not a perfect rating. A relevant self-declared skill and real available slot are enough to be considered.

**Follow-up:** Are experienced mentors guaranteed priority? No. Availability, relevance, urgency and the overall assignment can favor a provisional mentor.

## 16. How do you avoid rating manipulation?

Only the requester's selected identity may submit feedback after mentor completion, and session feedback is unique. Those rules prevent duplicate ratings for one session. They do not prevent fake identities or collusion: demo headers are not authentication. Stars do not directly drive allocation.

**Follow-up:** Could someone switch identity and submit? Yes; the selector intentionally demonstrates roles, not identity proof.

## 17. How do you prevent unfair allocation?

Waiting adds one utility point per hour capped at ten, and urgency is explicit. Deterministic ordering makes ties reproducible. These are modest heuristics; no fairness or starvation guarantee is claimed. Assignment counts and urgent rates are reported separately from utility.

**Follow-up:** Can flexible requests still wait indefinitely? Yes, under sustained competition. A fairness policy needs a stronger objective and evaluation.

## 18. How does urgency affect assignment?

After eligibility, suitability is multiplied by 1.25 for urgent, 1.00 normal, .85 flexible, then the waiting bonus is added. Urgency belongs to the request and does not change mentor skill evidence.

**Follow-up:** Can urgent utility exceed 100? Yes. Only suitability is out of 100; allocation utility is a separate quantity.

## 19. What if an urgent doubt has no eligible mentor?

It stays unmatched. A multiplier never creates an edge that fails skills, availability, deadline or booking constraints. There is no fallback to an incompatible or nonexistent mentor.

**Follow-up:** Is there an escalation channel? The local board exposes the unmatched state; there is no external notification or human dispatch service.

## 20. How do you evaluate quality?

The algorithm has a known counterexample, exhaustive small-instance oracle checks, deterministic edge cases and 50 reproducible synthetic scenarios. API tests check real scheduling and booking invariants. The executed report includes actual counts and per-scenario outputs, not estimates of student success.

**Follow-up:** Do benchmarks prove students learn more? No. That needs a real study with consent, outcome definitions and representative users.

## 21. How do you compare against greedy?

Both algorithms receive exactly the same matrix. Greedy sorts all eligible edges by utility and takes unused pairs. The fixed run produced 28 higher-utility Hungarian outcomes and 22 ties. The optimized algorithm is slower but improves aggregate synthetic utility; no claim of universal per-metric improvement is made.

**Follow-up:** Are the numbers hardcoded? The endpoint generates and computes them every time; the JSON file is a saved actual run.

## 22. What if the database goes down?

A failed transaction rolls back; OperationalError is handled as a safe 503 and the UI shows an error. There is no high availability, replicated failover or offline queue. `/health` reports process health, not a database readiness probe.

**Follow-up:** Can the user retry safely? State checks and uniqueness reject duplicate lifecycle operations; creation is not protected by client idempotency keys, so users should check before resubmitting after an ambiguous network failure.

## 23. How would you scale to 10,000 students?

First measure workload. Move to PostgreSQL with migrations, row/resource locking and temporal constraints; preload evidence to avoid per-edge queries; partition dispatch by compatible scope/time; use a durable job queue and admission limits; implement pagination, identity, monitoring and load tests. These are future changes, not implemented features.

**Follow-up:** Can you just change DATABASE_URL? No. The current pragmas and BEGIN IMMEDIATE are SQLite-specific.

## 24. What are the security limitations?

Identity headers are spoofable, all demo records are readable, no rate limiting exists and static assessment banks are not secret from source readers. Inputs are validated, ORM queries parameterized, ownership enforced relative to the selected identity, answer keys omitted from question APIs and CORS restricted locally. This remains a loopback-only prototype.

**Follow-up:** Does CORS protect the API? No. It restricts browser origins; it does not authenticate non-browser clients.

## 25. What would you build with another 24 hours?

Prioritize exact handling of shared-person allocation constraints or a clearly restricted batch policy; preload eligibility evidence; add authenticated campus identities and private record access; add browser regression tests and stronger expiry/timing enforcement. Then evaluate fairness and notification needs with users.

**Follow-up:** Why not add AI first? The immediate risks are identity, constraint modeling and reliability, not missing text generation.
