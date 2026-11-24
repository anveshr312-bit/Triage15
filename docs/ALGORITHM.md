# Deterministic allocation

Filtering alone establishes eligibility but cannot choose a good joint allocation when requests compete for the same resource. On `[[9,8],[8,1]]`, edge-sorted greedy selects 9+1=10 while maximum-weight matching selects 8+8=16. Both are implemented and tested; no LLM, trained model or prediction service is involved.

## Hard constraints

A mentor must opt in, differ from the requester, declare the exact request domain and overlap at least one requested skill tag. The proposed full 900-second interval must fit an actual availability window, start in the future/on the current instant, satisfy preferred start and deadline, and avoid live OFFERED/ACCEPTED/ACTIVE bookings for either participant. Previously declined/cancelled or unsuccessfully finalized mentor-request pairs are excluded. Other domains remain eligible with self-declared provisional skills, but cross-domain semantic matching is not implemented.

Availability windows round inward to integer multiples of 900 UTC epoch seconds; duplicate/overlapping windows produce a deduplicated slot set. The equal-duration common grid means distinct mentor-slot resources never partially overlap. Intervals are half-open: `[start,end)`, so adjacent slots do not conflict. Candidate generation covers the next seven days. Dispatch rejects batches exceeding 200 requests or 2,000 resources with 422.

## Score out of 100

| Component | Calculation |
|---|---|
| Domain and skills (35) | 20 for exact domain + 15 × fraction of requested tags supported |
| Assessment (25) | Latest relevant percentage × .25; absent assessment uses 10 provisional points |
| Reliability (15) | 15 × (finalized successful sessions + 2) / (all finalized sessions + 4) |
| Availability (15) | 15 / (1 + hours from dispatch to start) |
| Confidence (10) | 10 with a relevant assessment; 4 with provisional declaration |

All components are bounded; the unrounded sum is at most 100. The reported score is rounded to six decimal places. Self-declared level, assessment percentage, completion counts and feedback remain distinct evidence; self-declared level and feedback stars are not extra hidden score multipliers. A latest assessment is selected by timestamp then ID. Assessments submitted in the same second have deterministic UUID ordering, not strict subsecond chronology.

`utility = suitability × urgency_multiplier + min(10, max(0, waiting_hours))`

Multipliers live in `config.py`: Urgent 1.25, Normal 1.00, Flexible .85. Utility may exceed 100; suitability does not. Waiting contributes one point per hour, capped at ten. This is a modest aging heuristic, **not a starvation-freedom guarantee**. Users can self-label urgency; no abuse enforcement exists.

## Solver

Rows are waiting doubts and columns are mentor-slot pairs. Ineligible cells are `None`, not zero-score eligible candidates. The pure-Python rectangular Hungarian algorithm minimizes negated utility, using row/column potentials and augmenting paths. It adds one zero-valued dummy column per request. Invalid costs are 1e12, far beyond bounded real utilities; dummy capacity is always sufficient, so no invalid edge must be selected. Positive real assignments are returned in stable row order. Requests and resources are sorted to make repeated runs on the same state deterministic.

```text
begin immediate transaction
expire offers
requests = waiting requests in stable order
resources = unique mentor/grid slots inside declared windows
for each request and resource:
    if all eligibility constraints hold:
        calculate score components and urgency-weighted utility
    else:
        mark edge unavailable
optimized = Hungarian(matrix + unmatched dummies)
baseline = greedy(matrix)
for optimized pair in stable order:
    if final participant, availability and booking checks pass:
        insert OFFERED reservation and update request
    else:
        record rejection
mark remaining requests UNMATCHED with a reason
persist run explanation and commit
```

The baseline sorts **all** eligible edges by descending utility and accepts an edge if its row and column are both unused. It gets exactly the same matrix as Hungarian and is not deliberately weakened.

## Complexity and exact optimality boundary

For n requests and m real resources, Hungarian takes O(n²(m+n)) time and O(n(m+n)) matrix memory. Greedy costs O(E log E), E ≤ nm. Matrix construction checks nm potential edges. The straightforward SQL queries and history lookups per edge add substantial database work; solver runtime in reports excludes matrix construction and persistence.

Hungarian is optimal **for the weighted bipartite matrix**. One student can be a requester in several doubts and can also be a mentor. Those shared-person conflicts across otherwise distinct resources are extra constraints beyond bipartite matching. Existing bookings are filtered before solving; new conflicts between selected pairs are rejected at final validation. The final persisted subset is safe but is not guaranteed maximum utility under those extra constraints. The implementation does not silently advertise that subset as a constrained global optimum, and dispatch reports rejection counts. A subsequent dispatch can try remaining capacity. Supporting an exact joint-person optimum requires an integer/constraint solver or a restricted batch model.

## Evaluation

Pytest checks the counterexample, empty/all-invalid/rectangular cases, deterministic ties, and 60 small random cases against exhaustive enumeration. The benchmark endpoint generates 50 matrices using seed 15015: 2–22 requests, 1–25 resources, roughly 35% forbidden edges, suitability from 35–100, random urgency, and bounded waiting bonuses. Per scenario it records count, utility, average suitability, urgent assignment rate (null if no urgent requests), unassigned count, invalid count and solver milliseconds.

The fixture generator represents already-filtered graph edges. It does not synthesize a campus population or validate real scheduling constraints; integration tests separately do that. Actual results are saved in `benchmark-results.json`. Runtime changes across machines; graph quality results repeat. Maximizing utility does not necessarily maximize assignment count, urgent assignment count, or fairness. These are separate reported metrics, not claims of guaranteed improvement.

The score is a configurable heuristic ranking. It is neither a statistically validated probability of solving a problem nor certification of expertise. Five multiple-choice questions provide limited evidence only.
