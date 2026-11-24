import { useEffect, useState } from 'react';
import { api } from '../api';

export function ModelEvaluation() {
  const [info, setInfo] = useState<any>();
  const [reports, setReports] = useState<any>();
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    Promise.all([api('/ml/model-info', ''), api('/ml/metrics', '')])
      .then(([i, r]) => { if (alive) { setInfo(i); setReports(r); } })
      .catch(() => { if (alive) setError('ML reports unavailable. Manual skill selection remains available.'); });
    return () => { alive = false; };
  }, []);
  if (error) return <p role="status">{error}</p>;
  if (!info || !reports) return <p>Loading saved ML evaluation…</p>;
  if (!info.available) return <p>Optional ML model: {info.loading_status}. Select skills manually.</p>;
  const m = info.metadata;
  return <section>
    <h2>Skill suggestion evaluation</h2>
    <p>Real data: {m.dataset.source.source}. {m.dataset.downloaded_questions} downloaded, {m.dataset.usable_questions} usable questions.
      Train / validation / test: {m.dataset.split_sizes.train} / {m.dataset.split_sizes.validation} / {m.dataset.split_sizes.test}.</p>
    <p>Selected: <strong>{m.selected_model}</strong>. {m.selection_reason}</p>
    <h3>Validation comparison</h3>
    <div style={{ overflowX: 'auto' }}><table><thead><tr><th>Model</th><th>Micro F1</th><th>Macro F1</th><th>Precision</th><th>Recall</th><th>Train seconds</th><th>Median scoring ms</th><th>Bytes</th></tr></thead>
      <tbody>{Object.entries(reports.validation).map(([name, v]: [string, any]) => <tr key={name}>
        <td>{name}</td>{['micro_f1', 'macro_f1', 'micro_precision', 'micro_recall', 'training_seconds', 'median_inference_ms'].map(k => <td key={k}>{v[k].toFixed(3)}</td>)}<td>{v.model_size_bytes}</td>
      </tr>)}</tbody></table></div>
    <p>Comparison latency includes TF-IDF transform and classifier scoring, excluding explanations and HTTP.
      {reports.predictor_latency && <> Complete warm predictor, including explanations: median {reports.predictor_latency.median_ms.toFixed(1)} ms, p95 {reports.predictor_latency.p95_ms.toFixed(1)} ms ({reports.predictor_latency.calls} illustrative calls; excludes HTTP).</>}</p>
    <h3>Selected model: held-out test</h3>
    <p>Micro F1 {reports.test.micro_f1.toFixed(3)} · Macro F1 {reports.test.macro_f1.toFixed(3)} · Coverage {reports.test.coverage.toFixed(3)} · Precision@3 {reports.test.precision_at_3.toFixed(3)}.</p>
    <details><summary>All test metrics and definitions</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify({ metrics: reports.test, definitions: reports.metric_definitions }, null, 2)}</pre></details>
    <h3>Learned feature associations</h3>
    {Object.entries(reports.feature_importance).map(([label, v]: [string, any]) => <details key={label}>
      <summary>{label} — {v.training_examples} training positives</summary>
      <p>Positive: {v.positive.map((f: any) => `${f.feature} (${f.weight.toFixed(3)})`).join(', ')}</p>
      <p>Negative: {v.negative.map((f: any) => `${f.feature} (${f.weight.toFixed(3)})`).join(', ')}</p>
    </details>)}
    <h3>Real-question allocation benchmark</h3>
    <p>Question text and tags are real. Profiles, availability, urgency, and deadlines are simulated. Utility is not a learning outcome.</p>
    <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(reports.allocation_benchmark?.summary ?? 'Not measured yet', null, 2)}</pre>
    <p>Known limitations: {m.limitations.join(' ')}</p>
  </section>;
}
