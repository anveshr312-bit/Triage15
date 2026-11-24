import { useState, useEffect } from 'react';
import { api, SessionCodeSnippet, SessionResolution } from '../../api';

export function ResolutionEditor({
  sessionId,
  actor,
  snippets,
  onResolutionSubmitted
}: {
  sessionId: string;
  actor: string;
  snippets: SessionCodeSnippet[];
  onResolutionSubmitted: () => void;
}) {
  const [rootCause, setRootCause] = useState('');
  const [solutionExplanation, setSolutionExplanation] = useState('');
  const [followUpSteps, setFollowUpSteps] = useState('');
  const [originalSnippetId, setOriginalSnippetId] = useState('');
  const [correctedSnippetId, setCorrectedSnippetId] = useState('');
  const [refUrls, setRefUrls] = useState<string[]>(['']);
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState('');

  // Load existing draft if any
  useEffect(() => {
    let alive = true;
    const loadDraft = async () => {
      try {
        const existing = await api<SessionResolution>(`/sessions/${sessionId}/resolution`, actor);
        if (alive && existing) {
          setRootCause(existing.root_cause || '');
          setSolutionExplanation(existing.solution_explanation || '');
          setFollowUpSteps(existing.follow_up_steps || '');
          setOriginalSnippetId(existing.original_snippet_id || '');
          setCorrectedSnippetId(existing.corrected_snippet_id || '');
          if (existing.reference_urls && existing.reference_urls.length > 0) {
            setRefUrls(existing.reference_urls);
          }
        }
      } catch {
        // No draft yet, ignore 404
      }
    };
    void loadDraft();
    return () => {
      alive = false;
    };
  }, [sessionId, actor]);

  const handleSaveDraft = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!rootCause.trim() || !solutionExplanation.trim()) {
      setError('Root cause and solution explanation are required to save resolution.');
      return;
    }
    setBusy(true);
    setError('');
    setStatusMessage('');
    try {
      const cleanedUrls = refUrls.map((u) => u.trim()).filter((u) => u.length > 0);
      await api<SessionResolution>(
        `/sessions/${sessionId}/resolution`,
        actor,
        'PUT',
        {
          root_cause: rootCause.trim(),
          solution_explanation: solutionExplanation.trim(),
          follow_up_steps: followUpSteps.trim() || null,
          original_snippet_id: originalSnippetId || null,
          corrected_snippet_id: correctedSnippetId || null,
          reference_urls: cleanedUrls
        }
      );
      setStatusMessage('Resolution draft saved.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleSubmitResolution = async () => {
    if (!rootCause.trim() || !solutionExplanation.trim()) {
      setError('Please provide both Root Cause and Solution Explanation before submitting.');
      return;
    }
    setBusy(true);
    setError('');
    setStatusMessage('');
    try {
      const cleanedUrls = refUrls.map((u) => u.trim()).filter((u) => u.length > 0);
      // 1. Save latest draft
      await api(
        `/sessions/${sessionId}/resolution`,
        actor,
        'PUT',
        {
          root_cause: rootCause.trim(),
          solution_explanation: solutionExplanation.trim(),
          follow_up_steps: followUpSteps.trim() || null,
          original_snippet_id: originalSnippetId || null,
          corrected_snippet_id: correctedSnippetId || null,
          reference_urls: cleanedUrls
        }
      );
      // 2. Submit resolution
      await api(`/sessions/${sessionId}/resolution/submit`, actor, 'POST');
      setStatusMessage('Resolution submitted! The session is now awaiting requester confirmation.');
      onResolutionSubmitted();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '16px', marginTop: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <span style={{ fontSize: '1.2rem' }}>📝</span>
        <strong style={{ fontSize: '1rem', color: '#0f172a' }}>Structured Solution Record (Mentor)</strong>
      </div>
      <p style={{ margin: '0 0 12px 0', fontSize: '0.85rem', color: '#475569' }}>
        Document the learning outcome and core fix. For coding, mathematics, or design doubts, this explanation is preserved in the student's personal solution history.
      </p>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
          1. Root Cause / Problem Explanation *
        </label>
        <textarea
          rows={3}
          placeholder="Explain why the error or issue occurred (e.g., in-place list modification during iteration advances index)..."
          value={rootCause}
          onChange={(e) => setRootCause(e.target.value)}
          required
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
        />
      </div>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
          2. Solution Explanation & Technical Rationale *
        </label>
        <textarea
          rows={3}
          placeholder="Explain the solution applied and how it resolves the root cause..."
          value={solutionExplanation}
          onChange={(e) => setSolutionExplanation(e.target.value)}
          required
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
        />
      </div>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>
          3. Follow-up Steps or Best Practices (Optional)
        </label>
        <textarea
          rows={2}
          placeholder="Additional tips, alternative libraries, or practice recommendations..."
          value={followUpSteps}
          onChange={(e) => setFollowUpSteps(e.target.value)}
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
        />
      </div>

      {snippets.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>
              Link Original Snippet (Optional)
            </label>
            <select
              value={originalSnippetId}
              onChange={(e) => setOriginalSnippetId(e.target.value)}
              style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
            >
              <option value="">None</option>
              {snippets.map((s) => (
                <option key={s.id} value={s.id}>{s.title} ({s.language})</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>
              Link Corrected Snippet (Optional)
            </label>
            <select
              value={correctedSnippetId}
              onChange={(e) => setCorrectedSnippetId(e.target.value)}
              style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
            >
              <option value="">None</option>
              {snippets.map((s) => (
                <option key={s.id} value={s.id}>{s.title} ({s.language})</option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>
          Reference URLs (Documentation or Tutorial links)
        </label>
        {refUrls.map((url, i) => (
          <div key={i} style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}>
            <input
              type="url"
              placeholder="https://docs.python.org/3/..."
              value={url}
              onChange={(e) => {
                const next = [...refUrls];
                next[i] = e.target.value;
                setRefUrls(next);
              }}
              style={{ flex: 1, padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
            />
            {refUrls.length > 1 && (
              <button
                type="button"
                className="secondary"
                style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                onClick={() => setRefUrls(refUrls.filter((_, idx) => idx !== i))}
              >
                ✕
              </button>
            )}
          </div>
        ))}
        {refUrls.length < 5 && (
          <button
            type="button"
            className="secondary"
            style={{ fontSize: '0.75rem', padding: '3px 8px' }}
            onClick={() => setRefUrls([...refUrls, ''])}
          >
            + Add URL
          </button>
        )}
      </div>

      {error && <div style={{ color: '#b91c1c', fontSize: '0.8rem', marginBottom: '10px' }}>⚠️ {error}</div>}
      {statusMessage && <div style={{ color: '#166534', fontSize: '0.8rem', marginBottom: '10px' }}>✓ {statusMessage}</div>}

      <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
        <button type="button" className="secondary" onClick={handleSaveDraft} disabled={busy}>
          {busy ? 'Saving…' : 'Save Draft'}
        </button>
        <button
          type="button"
          className="primary"
          onClick={handleSubmitResolution}
          disabled={busy}
          style={{ background: '#2563eb' }}
        >
          {busy ? 'Submitting…' : 'Submit Resolution to Requester'}
        </button>
      </div>
    </div>
  );
}
