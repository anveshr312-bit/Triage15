import { useState, useEffect } from 'react';
import { api, SessionResolution } from '../../api';

export function ResolutionReview({
  sessionId,
  actor,
  bountyAmount,
  onResolved
}: {
  sessionId: string;
  actor: string;
  bountyAmount: number;
  onResolved: () => void;
}) {
  const [resolution, setResolution] = useState<SessionResolution | null>(null);
  const [rating, setRating] = useState(5);
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    const fetchResolution = async () => {
      try {
        const data = await api<SessionResolution>(`/sessions/${sessionId}/resolution`, actor);
        if (alive) setResolution(data);
      } catch {
        // May not have structured record, will show fallback
      }
    };
    void fetchResolution();
    return () => {
      alive = false;
    };
  }, [sessionId, actor]);

  const handleResolve = async (isResolved: boolean) => {
    setBusy(true);
    setError('');
    try {
      await api(`/sessions/${sessionId}/resolve`, actor, 'POST', {
        resolved: isResolved,
        rating,
        notes: notes.trim() || (isResolved ? 'Confirmed resolved.' : 'Issue unresolved.')
      });
      onResolved();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '8px', padding: '16px', marginTop: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <span style={{ fontSize: '1.2rem' }}>🎓</span>
        <strong style={{ fontSize: '1rem', color: '#065f46' }}>Review Mentor's Solution & Confirm Outcome</strong>
        {bountyAmount > 0 && (
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: '4px', background: '#fef3c7', color: '#92400e' }}>
            ★ {bountyAmount} pts bounty reserved
          </span>
        )}
      </div>

      {resolution ? (
        <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '14px', marginBottom: '14px' }}>
          <div style={{ marginBottom: '10px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '2px' }}>
              Root Cause Identified:
            </span>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#1e293b', whiteSpace: 'pre-wrap' }}>
              {resolution.root_cause}
            </p>
          </div>

          <div style={{ marginBottom: '10px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '2px' }}>
              Proposed Solution & Explanation:
            </span>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#1e293b', whiteSpace: 'pre-wrap' }}>
              {resolution.solution_explanation}
            </p>
          </div>

          {resolution.follow_up_steps && (
            <div style={{ marginBottom: '10px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '2px' }}>
                Follow-up Recommendations:
              </span>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#334155', whiteSpace: 'pre-wrap' }}>
                {resolution.follow_up_steps}
              </p>
            </div>
          )}

          {resolution.reference_urls && resolution.reference_urls.length > 0 && (
            <div>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '2px' }}>
                References & Links:
              </span>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem' }}>
                {resolution.reference_urls.map((url, i) => (
                  <li key={i}>
                    <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>
                      {url} ↗
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <p style={{ fontSize: '0.85rem', color: '#065f46', marginBottom: '12px' }}>
          Your mentor has completed their assistance. Please verify if your doubt was resolved and rate your peer.
        </p>
      )}

      <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '12px', marginBottom: '14px' }}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>Mentor Rating:</label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRating(star)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.2rem',
                  cursor: 'pointer',
                  color: star <= rating ? '#eab308' : '#cbd5e1'
                }}
              >
                ★
              </button>
            ))}
          </div>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>({rating} / 5)</span>
        </div>

        <input
          type="text"
          placeholder="Optional feedback notes for the mentor..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={200}
          style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
        />
      </div>

      {error && <div style={{ color: '#b91c1c', fontSize: '0.8rem', marginBottom: '10px' }}>⚠️ {error}</div>}

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        <button
          type="button"
          className="primary"
          onClick={() => handleResolve(true)}
          disabled={busy}
          style={{ background: '#16a34a', fontWeight: 600 }}
        >
          {busy ? 'Processing…' : '✓ Confirm Problem Resolved (Release Bounty)'}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => handleResolve(false)}
          disabled={busy}
          style={{ color: '#b91c1c' }}
        >
          {busy ? 'Processing…' : '✕ Problem Not Resolved (Keep in Queue)'}
        </button>
      </div>

      <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#047857' }}>
        ℹ️ Confirming resolution releases the reserved bounty to the mentor. If confirmed unresolved, the bounty remains reserved for automatic reassignment.
      </div>
    </div>
  );
}
