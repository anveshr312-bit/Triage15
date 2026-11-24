# ML implementation verification — November 24, 2026

## Recovery and unchanged components

Before source changes: clean Git tree at `d048de3`; `git archive` saved `.tmp/ml-checkpoint/source-before-ml.zip`, commit recorded in `commit.txt`, and SQLite's backup API saved `.tmp/ml-checkpoint/triage15.db`. These local recovery files are ignored. No Git push or commit was performed.

Production algorithm, matching weights, service implementation, database models and schemas were not modified. The browser uses `.tmp/ml-browser.db`; all benchmarks use in-memory databases and tests use isolated temporary databases. The live demonstration database was not used for test writes.

## Executed checks

| Check | Result |
|---|---|
| Original suite before ML changes | 56 passed, 1 warning, 16.15 s |
| Final full backend suite including ML | 94 passed, 0 failed, 57 warnings, 17.29 s |
| New ML coverage | 38 tests, including parametrized cases |
| Frontend TypeScript checking | Passed through `tsc -b` in production build |
| Frontend production bundle | Passed; Vite transformed 38 modules |
| Real allocation scenarios | 30; both solvers have zero invalid assignments and zero cross-role conflicts |
| Enabled startup | Local Uvicorn server completed startup and served prediction/UI |
| Disabled startup | TestClient lifespan completed; health=ok, ML unavailable, domains remain accessible |
| Missing-artifact startup | TestClient lifespan completed; health=ok, ML unavailable, domains remain accessible |
| Missing/incompatible dependency and corrupt artifact | Safe unavailable behavior covered by unit tests |

Command: `.venv/Scripts/python.exe -m pytest backend -q -o faulthandler_timeout=30 --junitxml=docs/ml-test-results.xml`.
Frontend command: `npm --prefix frontend run build` (includes type checking).
The first sandboxed baseline stalled; rerunning outside the sandbox against the same isolated test configuration completed. All reported passes come from completed runs.
Warnings are the existing Starlette/httpx TestClient deprecation and joblib's NumPy 2.5 array-shape deprecation. They are not failed tests; exact runtime versions are pinned.

New checks cover HTML/technical tokens, mapping, unsupported tags, duplicates, split disjointness, all three attribution formulas, score reconstruction, multi-label/deterministic inference, abstention, artifact corruption/missing dependencies, strict API input validation, read-only inference, manual unsupported domains, accepted/rejected/added tags through the existing API, startup fallback, and measured benchmark consistency.
The original suite exercises matching, bounty reserve/award/refund, sessions, chat permissions, scheduling, concurrent claims, and deployment routes.

## Browser verification

Actual browser on `http://127.0.0.1:8001`, backed by an isolated test SQLite database:

1. Entered a Python/pandas title and description and clicked Suggest Skills.
2. Saw Python and pandas suggestions with SVM margin labels and supporting/opposing words.
3. Accepted pandas, unchecked Python, manually added debugging, and ignored the Python suggestion.
4. Expanded numerical contributions: TF-IDF, weights, signed products, intercept, and omitted contribution rendered correctly.
5. Posted via the existing form. The persisted board entry showed exactly `pandas, debugging`, and status `MATCHED`.
6. Opened ML evaluation and verified real dataset counts, validation comparison, final test metrics, feature associations and benchmark results.
7. Browser console returned no errors during this workflow.

The final frontend build was also reloaded: direct Remove pandas cleared the checkbox, accepting React explicitly switched to JavaScript, and the evaluation table stayed within a horizontally scrollable container. Dependency consistency passed `uv pip check` (39 installed packages).

After adding the saved full-predictor latency field, the focused ML suite passed again (38 passed, 0 failed, 9.72 s), and the final TypeScript/Vite build passed. Warm full-predictor latency measured over 100 illustrative calls was median 71.84 ms and p95 91.71 ms, excluding HTTP. This is distinct from the validation transform-and-score latency of 5.84 ms for SVM.

The browser demonstrated a complete suggestion-to-confirmed-doubt-to-matching path. Bounty, chat and full session completion were covered by automated regression tests, not repeated in the browser.

## Not executed / remaining limitations

Docker is not installed on this host, so no Docker image build or Railway deployment was executed. Runtime package metadata confirms Python 3.12 support; the Dockerfile includes the local artifact and retains SQLite persistence and one worker. No production/cloud rollout or Git push was attempted.
No statistical significance study, calibration fitting, campus pilot, domain-drift monitoring, or academic outcome evaluation was performed. Latency is a local CPU measurement, not a production SLA. See model/dataset cards for weak labels and provenance limitations.
