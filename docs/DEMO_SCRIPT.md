# 90-second demonstration

## Prepare before presenting

Start backend/frontend with README commands. Reset/reseed shortly before the demo so availability is fresh. Keep My sessions ready, and have a terminal open in `backend`. Select Rohan (student-08). Seeded mentors include Asha with Python assessment evidence, Kabir with provisional Python evidence, and Isha with Mathematics skills but no availability. Do not claim the five-question assessment verifies expertise.

| Time | Action and narration |
|---|---|
| 0–12s | Select Rohan, enter “Python loop skips values” and a short description, select Python/python, post. “A student can ask without taking an assessment.” |
| 12–22s | Switch to Asha's Profile & availability, show her declared tags and available windows, then switch to Kabir to show another eligible Python peer. “Availability and evidence are separate inputs.” |
| 22–35s | Return to Rohan, click Doubt board → Run dispatch. Show the offer count and unmatched reasons. “All waiting requests compete for mentor-slot resources; unavailable Mathematics stays unmatched.” |
| 35–48s | My sessions → expand the Python allocation explanation. Read score components and chosen time. “This is a ranking heuristic, not a probability. The solver maximizes total candidate utility.” |
| 48–58s | Benchmark → Run real benchmark. Show the 9/8/8/1 example: greedy 10, global 16; show actual wins/ties. “Both algorithms receive identical candidate edges.” |
| 58–68s | In the prepared terminal run the focused conflict test below. “Attempting to insert the same live slot or a second live session for the same doubt is rejected by SQLite constraints.” |
| 68–84s | Select the assigned mentor shown in Rohan's session, accept → start → mark my side complete. Switch back to Rohan and confirm resolved with feedback. Early start is explicitly allowed for this demo. |
| 84–90s | Point to the changed resolution/feedback metrics. “These counts come from actual records. Repeating resolution is rejected, so history cannot increment twice.” |

Prepared command for the booking-conflict demonstration:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_api.py::test_booking_unique_constraints -q
```

This test creates real records in an isolated test database and attempts three invalid inserts: same live mentor-slot/request, second mentor for the same live doubt, and another doubt in the same live mentor slot. Each raises an actual integrity error. Explain that this is the database conflict demonstration, not a clickable “simulate conflict” UI.

If the newly created question loses capacity to older or urgent requests, use one of Rohan's actual allocated sessions and explain the waiting result honestly. The seed deliberately creates competition. Offers expire within five minutes or by slot start; run dispatch again if necessary.

## Alternate paths

- UI unavailable: use `http://127.0.0.1:8000/docs` and the examples in API.md, or run `test_full_workflow` to show the complete real API chain with feedback/metrics assertions.
- No fresh available slots: stop the backend, run `python -m app.seed --reset` using the project interpreter, restart and reload. This destroys demo changes; do it before the timed presentation.
- Offer expires mid-demo: show EXPIRED, redispatch, then use the new offer. Never claim an expired offer was accepted.
- Benchmark slow/error: open the saved `benchmark-results.json` and identify it as the previously executed run. Do not present saved output as a new computation.
- A test fails on a different machine: show the error and refer to the saved executed report; do not say that the current test passed.

## Explain the engineering limit if asked

The Hungarian solver is optimal for its bipartite matrix. Final booking validation can reject new shared-requester/cross-role conflicts, leaving a safe but not necessarily globally optimal subset. Reported matrix utility and actual reserved-offer count are intentionally distinct.
