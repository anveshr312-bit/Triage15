import { SessionResolution, time } from '../../api';

export function ResolutionSummary({
  resolution
}: {
  resolution: SessionResolution;
}) {
  const isResolved = resolution.requester_status === 'CONFIRMED_RESOLVED';
  const statusColor = isResolved ? '#16a34a' : resolution.requester_status === 'CONFIRMED_UNRESOLVED' ? '#dc2626' : '#2563eb';
  const statusLabel = isResolved
    ? '✓ Confirmed Resolved by Requester'
    : resolution.requester_status === 'CONFIRMED_UNRESOLVED'
    ? '✕ Confirmed Unresolved'
    : '⏳ Pending Confirmation';

  return (
    <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '14px', marginTop: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>Structured Solution Record</strong>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: '4px', background: `${statusColor}15`, color: statusColor, border: `1px solid ${statusColor}40` }}>
          {statusLabel}
        </span>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>Root Cause:</span>
        <p style={{ margin: '2px 0 0 0', fontSize: '0.85rem', color: '#1e293b', whiteSpace: 'pre-wrap' }}>
          {resolution.root_cause}
        </p>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>Solution Explanation:</span>
        <p style={{ margin: '2px 0 0 0', fontSize: '0.85rem', color: '#1e293b', whiteSpace: 'pre-wrap' }}>
          {resolution.solution_explanation}
        </p>
      </div>

      {resolution.follow_up_steps && (
        <div style={{ marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>Follow-up:</span>
          <p style={{ margin: '2px 0 0 0', fontSize: '0.85rem', color: '#334155', whiteSpace: 'pre-wrap' }}>
            {resolution.follow_up_steps}
          </p>
        </div>
      )}

      {resolution.reference_urls && resolution.reference_urls.length > 0 && (
        <div>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>References:</span>
          <ul style={{ margin: '2px 0 0 0', paddingLeft: '18px', fontSize: '0.8rem' }}>
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

      {resolution.confirmed_at && (
        <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#64748b' }}>
          Outcome confirmed on {time(resolution.confirmed_at)}
        </div>
      )}
    </div>
  );
}
