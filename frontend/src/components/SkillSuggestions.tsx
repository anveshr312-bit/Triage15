import { useRef, useState } from 'react';
import { api } from '../api';

type Feature = { feature: string; contribution: number; tfidf_value: number; weight: number };
type Suggestion = {
  label: string; domain: string; decision_score: number; model_probability_estimate: number | null;
  intercept: number; positive_features: Feature[]; negative_features: Feature[]; omitted_contribution: number;
  score_scale: string; explanation_method: string;
};
type Prediction = { available: boolean; abstained: boolean; suggestions: Suggestion[]; reason: string };

export function SkillSuggestions({ title, description, domain, tags, onAccept, onRemove }: {
  title: string; description: string; domain: string; tags: string[];
  onAccept: (label: string, domain: string) => void;
  onRemove: (label: string) => void;
}) {
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [requestedText, setRequestedText] = useState('');
  const requestId = useRef(0);
  const currentText = JSON.stringify([title, description]);
  const fresh = currentText === requestedText;

  const suggest = async () => {
    const id = ++requestId.current;
    setBusy(true); setError(''); setResult(null); setRequestedText(currentText);
    try {
      const response = await api<Prediction>('/ml/predict-tags', '', 'POST', { title, description });
      if (id === requestId.current) setResult(response);
    } catch {
      setError('Skill suggestions are unavailable. Select your tags manually and continue.');
    } finally { if (id === requestId.current) setBusy(false); }
  };

  return <section aria-label="Optional skill suggestions">
    <button type="button" onClick={suggest} disabled={busy || title.trim().length < 3 || description.trim().length < 5}>
      {busy ? 'Suggesting…' : 'Suggest Skills'}
    </button>
    <p className="subtext">Suggestions are optional. Only the tags you select below are submitted for matching.</p>
    {error && <p role="status">{error}</p>}
    {result && !fresh && <p role="status">Text changed. Select Suggest Skills again for updated suggestions.</p>}
    {result && fresh && (!result.available || result.abstained) && <p role="status">
      {result.available ? 'No tags recommended for this text.' : 'The model is unavailable.'} Please select tags manually.
    </p>}
    {result && fresh && result.suggestions.map(s => <article key={s.label}>
      <strong>{s.label}</strong> <span>({s.domain})</span>
      <p>{s.model_probability_estimate !== null
        ? `Uncalibrated probability estimate: ${s.model_probability_estimate.toFixed(3)}`
        : `SVM decision margin: ${s.decision_score.toFixed(3)}`}</p>
      <p>Supporting: {s.positive_features.map(f => f.feature).join(', ') || 'None'}.<br />
        Opposing: {s.negative_features.map(f => f.feature).join(', ') || 'None'}.</p>
      <details><summary>Why this suggestion? Numerical contributions</summary>
        <p>{s.explanation_method}. {s.score_scale} Learned associations are not proof of expertise.</p>
        <div style={{ overflowX: 'auto' }}><table><thead><tr><th>Feature</th><th>TF-IDF</th><th>Weight</th><th>Contribution</th></tr></thead>
          <tbody>{[...s.positive_features, ...s.negative_features].map(f => <tr key={f.feature}>
            <td>{f.feature}</td><td>{f.tfidf_value.toFixed(6)}</td><td>{f.weight.toFixed(6)}</td><td>{f.contribution.toFixed(6)}</td>
          </tr>)}</tbody></table></div>
        <p>Intercept {s.intercept.toFixed(6)} + displayed contributions + omitted contribution {s.omitted_contribution.toFixed(6)} = decision score {s.decision_score.toFixed(6)}.</p>
      </details>
      <button type="button" disabled={domain === s.domain && tags.includes(s.label)} onClick={() => onAccept(s.label, s.domain)}>
        {domain === s.domain ? (tags.includes(s.label) ? 'Accepted — uncheck below to remove' : `Accept ${s.label}`) : `Use ${s.label} in ${s.domain} (replaces current tags)`}
      </button>
      <button type="button" onClick={() => {
        if (domain === s.domain && tags.includes(s.label)) onRemove(s.label);
        setResult(r => r && ({ ...r, suggestions: r.suggestions.filter(x => x.label !== s.label) }));
      }}>{domain === s.domain && tags.includes(s.label) ? `Remove ${s.label}` : 'Ignore suggestion'}</button>
    </article>)}
  </section>;
}
