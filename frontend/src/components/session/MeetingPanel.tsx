import { useState } from 'react';
import { api, SessionMeeting } from '../../api';

export function MeetingPanel({
  sessionId,
  actor,
  isMentor,
  meeting,
  onMeetingUpdated
}: {
  sessionId: string;
  actor: string;
  isMentor: boolean;
  meeting: SessionMeeting | null;
  onMeetingUpdated: (m: SessionMeeting | null) => void;
}) {
  const [inputUrl, setInputUrl] = useState('');
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const handleAttach = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;
    setBusy(true);
    setError('');
    try {
      const updated = await api<SessionMeeting>(
        `/sessions/${sessionId}/meeting`,
        actor,
        'PUT',
        { meeting_url: inputUrl.trim() }
      );
      onMeetingUpdated(updated);
      setInputUrl('');
      setEditing(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async () => {
    if (!confirm('Remove the Google Meet link from this session?')) return;
    setBusy(true);
    setError('');
    try {
      await api(`/sessions/${sessionId}/meeting`, actor, 'DELETE');
      onMeetingUpdated(null);
      setEditing(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="meeting-panel" style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.25rem' }}>📹</span>
          <strong style={{ fontSize: '1rem', color: '#0f172a' }}>Google Meet Video & Screen Share</strong>
          <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', background: meeting ? '#dcfce7' : '#f1f5f9', color: meeting ? '#166534' : '#64748b' }}>
            {meeting ? 'Active Link Attached' : 'Not Connected'}
          </span>
        </div>
        {meeting && isMentor && !editing && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="secondary" style={{ fontSize: '0.8rem', padding: '4px 8px' }} onClick={() => setEditing(true)}>
              Replace Link
            </button>
            <button className="secondary" style={{ fontSize: '0.8rem', padding: '4px 8px', color: '#b91c1c' }} onClick={handleRemove}>
              Remove
            </button>
          </div>
        )}
      </div>

      {meeting && !editing ? (
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '4px' }}>Meeting Room URL:</div>
            <code style={{ fontSize: '0.9rem', color: '#2563eb' }}>{meeting.meeting_url}</code>
          </div>
          <a
            href={meeting.meeting_url}
            target="_blank"
            rel="noopener noreferrer"
            className="primary"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', background: '#16a34a', color: '#ffffff', fontWeight: 600 }}
          >
            <span>Join Google Meet</span> ↗
          </a>
        </div>
      ) : isMentor ? (
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px' }}>
          <p style={{ margin: '0 0 10px 0', fontSize: '0.85rem', color: '#475569' }}>
            As the mentor, you can optionally launch Google Meet to talk or screen share:
          </p>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '12px' }}>
            <a
              href="https://meet.google.com/new"
              target="_blank"
              rel="noopener noreferrer"
              className="secondary"
              style={{ textDecoration: 'none', padding: '6px 12px', fontSize: '0.85rem', display: 'inline-block' }}
            >
              1. Open Google Meet (New Tab) ↗
            </a>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Copy the meeting link, then paste it below:</span>
          </div>

          <form onSubmit={handleAttach} style={{ display: 'flex', gap: '8px' }}>
            <input
              type="url"
              placeholder="https://meet.google.com/abc-defg-hij"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              required
              style={{ flex: 1, padding: '6px 10px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
            />
            <button type="submit" className="primary" disabled={busy}>
              {busy ? 'Attaching…' : 'Attach Link'}
            </button>
            {editing && (
              <button type="button" className="secondary" onClick={() => setEditing(false)}>
                Cancel
              </button>
            )}
          </form>
        </div>
      ) : (
        <div style={{ padding: '8px 0', color: '#64748b', fontSize: '0.85rem' }}>
          Waiting for your mentor to create and attach a Google Meet link. You can use persistent text chat and code snippet sharing below in the meantime.
        </div>
      )}

      {error && <div style={{ color: '#b91c1c', fontSize: '0.8rem', marginTop: '8px' }}>⚠️ {error}</div>}

      <div style={{ marginTop: '10px', fontSize: '0.75rem', color: '#64748b', borderTop: '1px dashed #cbd5e1', paddingTop: '8px' }}>
        ℹ️ <em>External Communication Notice:</em> Google Meet runs externally in a separate tab. Joining does not automatically resolve the doubt, and the Triage15 timer does not disconnect external calls.
      </div>
    </div>
  );
}
