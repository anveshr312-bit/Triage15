import { useState } from 'react';
import { api } from '../api';
import { Run } from '../App';

export function Benchmark({ actor, run }: { actor: string; run: Run }) {
  const [result, setResult] = useState<any>();

  return (
    <>
      <div className="section-head">
        <div>
          <h1>Algorithm Benchmark Suite</h1>
          <p>
            Rigorous comparison of rectangular maximum-weight Hungarian matching vs greedy allocation across 50 identical synthetic candidate matrices (seed 15015).
          </p>
        </div>
        <button
          className="primary"
          onClick={() =>
            run(async () => setResult((await api('/benchmarks/run', actor, 'POST')).result), 'Benchmark finished')
          }
        >
          Run Benchmark Suite
        </button>
      </div>

      {result && (
        <>
          <section className="benchmark-summary-card">
            <h2>
              {result.optimized_wins} Hungarian Utility Wins · {result.equal} Ties
            </h2>
            <p>
              In {result.greedy_faster_scenarios} of {result.scenario_count} scenarios, greedy executed faster due to lower polynomial complexity, but at the expense of global total utility.
            </p>

            <div className="metrics-grid">
              <div className="metric-box">
                <span className="metric-val">{result.average_runtime_ms?.optimized?.toFixed(3)} ms</span>
                <span className="metric-label">Hungarian Avg Runtime</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{result.average_runtime_ms?.greedy?.toFixed(3)} ms</span>
                <span className="metric-label">Greedy Avg Runtime</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{result.illustration.optimized_utility} vs {result.illustration.greedy_utility}</span>
                <span className="metric-label">2×2 Counterexample Utility</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{result.integrated_dispatch_metrics?.average_recovery_iterations}</span>
                <span className="metric-label">Avg Conflict Recovery Iterations</span>
              </div>
            </div>

            <p className="disclaimer-note">
              <strong>Honest Limitation & Academic Disclaimer:</strong> {result.academic_disclaimer}
            </p>
          </section>

          <div className="table-wrap">
            <table>
              <caption>Per-Scenario Measurements (Hungarian / Greedy)</caption>
              <thead>
                <tr>
                  {[
                    'Scenario',
                    'Requests × Slots',
                    'Assignments',
                    'Utility',
                    'Avg Suitability',
                    'Urgent Rate',
                    'Unassigned',
                    'Runtime (ms)'
                  ].map((t) => (
                    <th key={t}>{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.scenarios.map((r: any) => (
                  <tr key={r.scenario}>
                    <td>#{r.scenario + 1}</td>
                    <td>{r.request_count} × {r.resource_count}</td>
                    <td>{r.optimized.assignment_count} / {r.greedy.assignment_count}</td>
                    <td><strong>{r.optimized.total_utility.toFixed(2)}</strong> / {r.greedy.total_utility.toFixed(2)}</td>
                    <td>{r.optimized.average_suitability.toFixed(1)} / {r.greedy.average_suitability.toFixed(1)}</td>
                    <td>
                      {r.optimized.urgent_assignment_rate !== null ? `${(r.optimized.urgent_assignment_rate * 100).toFixed(0)}%` : '—'} /{' '}
                      {r.greedy.urgent_assignment_rate !== null ? `${(r.greedy.urgent_assignment_rate * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td>{r.optimized.unassigned_requests} / {r.greedy.unassigned_requests}</td>
                    <td>{r.optimized.runtime_ms.toFixed(2)} / {r.greedy.runtime_ms.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
