# Executed verification report

Executed on 24 November 2026 (Asia/Kolkata), Windows, Python 3.14.5, Node 22.23.2, npm 10.9.8. Installed package versions are recorded in `backend/requirements-lock.txt` and `frontend/package-lock.json` (including FastAPI 0.165.0, SQLAlchemy 2.1.9, Pydantic 2.14.4, Pytest 9.2.0, Vite 7.3.8).

## Automated backend checks

Final command: `python -m pytest -q --junitxml=../docs/test-results.xml` from backend using the project interpreter.

**36 passed, 0 failed, 0 errors, 1 dependency deprecation warning; 4.10 seconds.** Machine-readable JUnit results: `test-results.xml`.

Coverage exercised:

- Hungarian versus a 60-case exhaustive small-instance oracle; deterministic ties, empty/rectangular/invalid matrices, dummy unmatched handling, 9/8/8/1 example and 50 fixed-seed comparisons.
- Exact/partial relevance, assessment contribution, provisional evidence, smoothed reliability, urgency multiplier, bounded waiting bonus and preference for earlier slots.
- Complete API workflow: create request → actual dispatch → assigned mentor accepts → starts → marks complete → requester resolves → feedback persists → metrics increment exactly once.
- Wrong identity, invalid transitions, duplicate accept/complete/resolve, decline and alternative-mentor reassignment, expiration and rejected expired acceptance, cancellation including ACTIVE, unsuccessful outcome/reopening and mentor exclusion.
- Database rejection of duplicate live doubt, duplicate live mentor/start and off-grid sessions; requester overlap checks; overlapping reserved-window removal; two concurrent dispatch calls.
- Invalid IDs, missing/unknown fields, empty/invalid/duplicate skills, invalid domain/urgency, naive timestamps and reversed time windows; exact deadline/availability boundaries; self-mentoring exclusion; unavailable Mathematics mentor.
- Profile registration/update, availability add/remove, all three assessment banks and server scoring, answer-key omission, query filters, dispatch report/assignment retrieval, session retrieval, benchmark persistence and metrics.

This is meaningful unit/integration coverage, not a line-coverage percentage claim. Not every possible payload permutation or concurrency schedule was tested.

## Frontend and running application

- `npm run build`: **passed** TypeScript compilation and Vite production build. 35 modules; generated JS approximately 240.25 kB / 74.91 kB gzip, CSS 3.38 kB / 1.27 kB gzip.
- Backend initialization and seed command: **passed**.
- Reset/reseed command run twice on a separate smoke-test database: **passed**; verified 12 students, 21 total doubt records (18 examples plus 3 historical) and 15 assessment questions after the second reset.
- Uvicorn startup: **passed**, application startup complete on loopback port 8000.
- Vite startup: **passed**, loopback port 5173.
- Browser manual verification via the actual React controls: posted “Browser workflow: Python loop” as Rohan, ran global dispatch, found Asha's assignment, switched identity, accepted, started, marked mentor complete, switched back to Rohan, confirmed resolved and saved notes/rating. Visible metrics changed from 2 to 3 resolved sessions and from 3 to 4 feedback records. The browser displayed RESOLVED and the saved feedback text.
- Browser session explanations and real returned offer states were inspected. No automated browser regression suite or exhaustive mobile/accessibility test was run.

## Actual algorithm benchmark

Source: saved `benchmark-results.json`, seed **15015**, **50** scenarios, same candidate matrices for both algorithms. Individual results include assignment count, utility, average suitability, urgent assignment rate, unassigned count, invalid count and runtime.

| Aggregate | Hungarian | Greedy |
|---|---:|---:|
| Assigned requests | 404 | 403 |
| Total allocation utility | 41842.8799 | 41110.3382 |
| Unassigned requests | 190 | 191 |
| Invalid chosen edges | 0 | 0 |
| Total solver runtime across 50 cases | 20.754 ms | 2.074 ms |

Hungarian had strictly higher utility in **28** scenarios and equal utility in **22**. The illustrative 2×2 case computed 16 versus 10. These timings are one measured local run and are not service latency guarantees; they exclude eligibility SQL and persistence. The benchmark does not claim real-world resolution improvements or global optimality after extra participant-conflict rejections.

## Initial failures and resolutions

- Python environment setup initially failed due to Windows sandbox temporary/cache permissions; creating the environment without ensurepip and installing with uv into the project resolved it. Dependency downloads required network-enabled execution.
- The first full test run had 12 algorithm passes and 22 setup errors because the sandbox's temporary directory could not host SQLite. Tests now use isolated temporary databases within `backend/.test-data`.
- Subsequent API setup stalled in Python's Windows asyncio socket-pair initialization because sandbox loopback was blocked. The diagnostic thread dump located the stall before API execution. Running tests outside that sandbox resolved it without changing application async logic.
- The first build reached bundling but sandbox permissions blocked creating `dist/assets`. The standard `npm run build` passed outside the sandbox.
- The first browser connection to the sandboxed frontend timed out. Starting local servers outside the sandbox allowed successful browser verification.
- One remaining dependency warning: Starlette deprecates its httpx-based TestClient in favor of httpx2. Current pinned httpx tests pass; this warning is not hidden.

## Remaining verification gaps / known limitations

No production load test, browser automation suite, penetration test, external deployment, PostgreSQL run or real student study. SQLite locking and the extra participant-conflict optimality limitation are documented in LIMITATIONS.md. The production build was compiled, while the manual browser workflow used Vite development serving. Database reset semantics and the local demo identity model remain intentionally prototype-only.
