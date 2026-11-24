import { useEffect, useState } from 'react';
import { api, SessionCodeSnippet, SnippetDiff } from '../../api';

export function CodeComparison({
  sessionId,
  actor,
  snippets,
  initialOriginalId,
  initialProposedId,
  onClose
}: {
  sessionId: string;
  actor: string;
  snippets: SessionCodeSnippet[];
  initialOriginalId?: string;
  initialProposedId?: string;
  onClose: () => void;
}) {
  const [origId, setOrigId] = useState(initialOriginalId || snippets[0]?.id || '');
  const [propId, setPropId] = useState(
    initialProposedId ||
    snippets.find((s) => s.id !== (initialOriginalId || snippets[0]?.id))?.id ||
    snippets[0]?.id ||
    ''
  );
  const [diff, setDiff] = useState<SnippetDiff | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!origId || !propId) return;
    let alive = true;
    const fetchDiff = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await api<SnippetDiff>(
          `/sessions/${sessionId}/snippets-diff?original_id=${origId}&proposed_id=${propId}`,
          actor
        );
        if (alive) setDiff(data);
      } catch (err: any) {
        if (alive) setError(err.message);
      } finally {
        if (alive) setLoading(false);
      }
    };
    void fetchDiff();
    return () => {
      alive = false;
    };
  }, [sessionId, actor, origId, propId]);

  return (
    <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>🔍</span>
          <strong style={{ fontSize: '1rem', color: '#0f172a' }}>Before-and-After Code Comparison</strong>
          {diff && (
            <div style={{ display: 'flex', gap: '6px', marginLeft: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: '4px', background: '#dcfce7', color: '#166534' }}>
                +{diff.added_count} lines added
              </span>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: '4px', background: '#fee2e2', color: '#991b1b' }}>
                -{diff.removed_count} lines removed
              </span>
            </div>
          )}
        </div>
        <button className="secondary" style={{ fontSize: '0.8rem', padding: '4px 8px' }} onClick={onClose}>
          ✕ Close Diff
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Original Snippet (Base):</label>
          <select
            value={origId}
            onChange={(e) => setOrigId(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          >
            {snippets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title} ({s.snippet_type})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Proposed Fix (Comparison):</label>
          <select
            value={propId}
            onChange={(e) => setPropId(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          >
            {snippets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title} ({s.snippet_type})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#64748b' }}>Computing difference…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#b91c1c' }}>⚠️ {error}</p>}

      {diff && !loading && (
        <div style={{ background: '#0f172a', borderRadius: '6px', overflow: 'hidden', border: '1px solid #334155' }}>
          <div style={{ maxHeight: '350px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.82rem', lineHeight: '1.4' }}>
            {diff.lines.map((line, idx) => {
              const bg = line.type === 'added' ? '#064e3b' : line.type === 'removed' ? '#7f1d1d' : 'transparent';
              const textCol = line.type === 'added' ? '#a7f3d0' : line.type === 'removed' ? '#fecaca' : '#cbd5e1';
              const prefix = line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  ';
              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    background: bg,
                    color: textCol,
                    padding: '1px 8px',
                    borderLeft: line.type === 'added' ? '3px solid #10b981' : line.type === 'removed' ? '3px solid #ef4444' : '3px solid transparent'
                  }}
                >
                  <span style={{ width: '32px', color: '#475569', userSelect: 'none' }}>{idx + 1}</span>
                  <span style={{ width: '16px', userSelect: 'none', fontWeight: 'bold' }}>{prefix}</span>
                  <pre style={{ margin: 0, whiteSpace: 'pre', overflowX: 'auto', flex: 1 }}>{line.text}</pre>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div style={{ marginTop: '10px', fontSize: '0.75rem', color: '#64748b' }}>
        ℹ️ <em>Diff Disclaimer:</em> Textual comparison highlighting added and deleted lines. Triage15 does not compile or execute code to guarantee correctness.
      </div>
    </div>
  );
}
