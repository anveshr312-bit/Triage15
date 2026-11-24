# TRIAGE15 — DETERMINISTIC MATCHING ALGORITHM & BENCHMARKS

## 1. Problem Formulation

Peer-to-peer micro-skill assistance requires matching a set of $N$ open technical doubt requests:
$$D = \{d_1, d_2, \dots, d_N\}$$
to a set of $M$ discrete 15-minute mentor capacity slots:
$$R = \{r_1, r_2, \dots, r_M\}$$
where each resource $r_j = (m_j, t_j)$ represents mentor $m_j$ available during the 15-minute grid interval $[t_j, t_j + 900)$.

A naive greedy algorithm (matching requests sequentially or sorting edges by weight) frequently produces suboptimal global outcomes. Consider two requests and two slots with candidate utility matrix:
$$C = \begin{pmatrix} 9 & 8 \\ 8 & 1 \end{pmatrix}$$
- **Greedy selection:** Picks the highest edge $C_{0,0} = 9$. This consumes Slot 0, forcing Request 1 to take Slot 1 with utility $C_{1,1} = 1$. Total utility: $9 + 1 = 10$.
- **Maximum-Weight Hungarian Matching:** Selects $C_{0,1} = 8$ and $C_{1,0} = 8$. Total utility: $8 + 8 = 16$.
- **Relative Difference:** A 60% total utility improvement on this candidate graph.

Triage15 implements rectangular maximum-weight bipartite matching using the Kuhn-Munkres algorithm and compares it directly against a shared-matrix greedy baseline. **No LLM, trained model, or black-box heuristic is used in the allocation engine.**

---

## 2. Hard Eligibility Constraints

Before calculating suitability, every edge $(d_i, r_j)$ must satisfy all hard constraints:
1. **Opt-in Status:** Mentor $m_j$ must have active mentoring enabled (`mentoring == True`).
2. **Non-Self-Assignment:** Requester $d_i.\text{requester\_id} \ne m_j.\text{id}$.
3. **Domain Match:** Mentor must declare the exact domain of the doubt ($d_i.\text{domain}$).
4. **Skill Intersection:** $\{s \in d_i.\text{skills}\} \cap \{s \in m_j.\text{skills} \mid s.\text{domain} = d_i.\text{domain}\} \ne \emptyset$.
5. **Temporal Validity:** Slot start $t_j \ge \text{current\_time}$ and $t_j \pmod{900} = 0$.
6. **Window Satisfaction:** $t_j \ge d_i.\text{preferred\_start}$ (if specified) and $t_j + 900 \le d_i.\text{deadline}$ (if specified).
7. **Availability Coverage:** $t_j$ and $t_j + 900$ must fall completely within one of $m_j$'s declared availability windows.
8. **Participant Live Conflict:** Neither mentor $m_j$ nor requester $d_i.\text{requester}$ may have an overlapping `OFFERED`, `ACCEPTED`, `ACTIVE`, or `AWAITING_CONFIRMATION` session during $[t_j, t_j + 900)$.
9. **Exclusion of Previous Infeasible Mentors:** A mentor who previously declined, cancelled, or failed to resolve doubt $d_i$ is excluded from immediate reassignment.

If any constraint fails, the edge is prohibited and set to `None`.

---

## 3. Suitability & Utility Scoring

For every feasible edge $(d_i, r_j)$, the multi-factor suitability score (bounded in $[0, 100]$) is computed as:

$$\text{Suitability}(d_i, r_j) = S_{\text{relevance}} + S_{\text{evidence}} + S_{\text{reliability}} + S_{\text{availability}} + S_{\text{confidence}}$$

### Score Breakdown
| Component | Points | Formulation |
| :--- | :--- | :--- |
| **Domain & Skill Relevance** | 20–35 | $20 + 15 \times \frac{|\text{Tags}_{\text{mentor}} \cap \text{Tags}_{\text{doubt}}|}{|\text{Tags}_{\text{doubt}}|}$ |
| **Assessment Evidence** | 10–25 | $\text{score} \times 0.25$ (if tested); default 10 (provisional declaration) |
| **Historical Reliability** | 0–15 | $15 \times \frac{\text{resolved} + 2}{\text{completed} + 4}$ (Bayesian smoothed) |
| **Temporal Proximity** | 0–15 | $\frac{15}{1 + \max(0, t_j - \text{current}) / 3600}$ |
| **Confidence Bonus** | 4–10 | 10 with verified assessment; 4 with self-declaration |

### Allocation Utility
To convert multi-factor suitability into dispatch utility:
$$\text{Utility}(d_i, r_j) = \text{round}\left(\text{Suitability} \times U_{\text{urgency}} + W_{\text{wait}} + B_{\text{bounty}}, 6\right)$$

Where:
- **Urgency Multiplier ($U_{\text{urgency}}$):** `Urgent` = 1.25, `Normal` = 1.00, `Flexible` = 0.85.
- **Waiting Bonus ($W_{\text{wait}}$):** $\min\left(10, \frac{\text{current} - d_i.\text{created\_at}}{3600}\right)$ (bounded aging heuristic).
- **Bounty Bonus ($B_{\text{bounty}}$):** $\min\left(5.0, d_i.\text{bounty} \times 0.05\right)$ (gives slight tie-breaking priority to reputation bounties without overriding skill suitability).

---

## 4. Rectangular Hungarian Algorithm

Because the bipartite graph has $N$ requests and $M$ slots (where typically $M \ne N$), the algorithm transforms the rectangular matrix into a square matrix of size $N \times (M + N)$ by adding $N$ zero-valued dummy columns.

### Mathematical Formulation
1. **Negated Cost Matrix:** We minimize negated utility:
   $$\text{cost}_{i,j} = \begin{cases} -C_{i,j} & \text{if } C_{i,j} \text{ is feasible} \\ 10^{12} & \text{if infeasible (prohibited edge)} \\ 0.0 & \text{for dummy columns } j > M \end{cases}$$
2. **Dual Potentials:** Maintain potentials $u_i$ and $v_j$ such that $\text{cost}_{i,j} - u_i - v_j \ge 0$.
3. **Augmenting Paths:** For each row $i = 1, \dots, N$, find an augmenting path of minimal reduced cost using Dijkstra-like shortest path augmentation with lazy potential adjustments.
4. **Result Extraction:** For columns $j \le M$, if the assigned row $i$ has positive utility ($C_{i,j} > 0$), record $(i, j)$ as an assigned match. Dummy assignments correspond to unassigned requests.

**Complexity:** $O(N \cdot (M + N) \cdot \min(N, M + N)) = O(N^2 M + N^3)$, executing in under 2ms for campus batches of 50 requests and 100 slots.

---

## 5. Iterative Conflict Recovery (P1.1)

While the Hungarian algorithm finds the globally optimal assignment for bipartite matching, downstream scheduling constraints across roles (e.g., a student participating as both mentor and help-seeker) can cause a solver-selected match to fail at database commit time.

Rather than aborting the dispatch or leaving valid alternative matches unassigned, Triage15 executes **Bounded Iterative Conflict Recovery**:
```text
Algorithm: Iterative Conflict Recovery
Input: Open doubts D, Available slots R, Max iterations K = 3
1. iteration = 0, excluded = {}
2. while iteration < K:
3.     active_doubts = [d in D if d.status == 'OPEN']
4.     Build candidate matrix on active_doubts and R excluding edges in 'excluded'
5.     chosen = Hungarian(candidate matrix)
6.     rejections = []
7.     for (d, r) in chosen:
8.         if feasible_in_database(d, r):
9.             persist_session(d, r)
10.            d.status = 'MATCHED'
11.        else:
12.            rejections.append((d, r))
13.            excluded.add((d, r))
14.    iteration += 1
15.    if len(rejections) == 0:
16.        break
17. Mark remaining unassigned doubts with specific honest reasons
```

---

## 6. Benchmark Suite & Evaluation

The benchmark runner (`/api/benchmarks/run`) tests Hungarian and Greedy on 50 identical synthetic candidate matrices generated from seed `15015`:
- **Candidate matrices:** Random sizes $N \in [2, 22]$, $M \in [1, 25]$, scores $\in [35, 100]$, density ~65%.
- **Measured Outcomes:**
  - Hungarian wins: ~84% of scenarios.
  - Ties (identical utility): ~16% of scenarios (primarily sparse or unconstrained matrices).
  - Runtime comparison: Greedy is faster ($0.05\text{ms}$ vs $0.25\text{ms}$), as expected from its $O(E \log E)$ edge-sorting complexity.
  - Conflict recovery: Resolves ~75% of cross-role booking conflicts within 2 iterations.

### Academic Disclaimer
> [!IMPORTANT]
> Total utility improvements measure optimization quality against our synthetic objective heuristic. They do not constitute scientific proof of improved learning retention, academic performance, or mentor pedagogical efficacy.
