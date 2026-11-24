import { useEffect, useState } from 'react';
import { api, Session, Student, time } from '../api';
import { Run } from '../App';
import { SessionWorkspace } from './SessionWorkspace';

export function Sessions({
  actor,
  students,
  revision,
  run
}: {
  actor: string;
  students: Student[];
  revision: number;
  run: Run;
}) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const load = () =>
      api<Session[]>('/sessions', actor)
        .then((d) => {
          if (live) {
            setSessions(d.filter((s) => s.mentor_id === actor || s.requester_id === actor));
            setError('');
          }
        })
        .catch((e) => {
          if (live) setError(e.message);
        })
        .finally(() => {
          if (live) setLoading(false);
        });

    void load();
    const timer = setInterval(load, 4000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [actor, revision]);

  const selectedSession = sessions.find((s) => s.id === activeSessionId);

  if (selectedSession) {
    return (
      <SessionWorkspace
        session={selectedSession}
        actor={actor}
        students={students}
        run={run}
        onBack={() => setActiveSessionId(null)}
      />
    );
  }

  const action = (id: string, name: string) =>
    run(() => api(`/sessions/${id}/${name}`, actor, 'POST'), 'Session updated');

  return (
    <>
      <div className="section-head">
        <div>
          <h1>My Sessions</h1>
          <p>Assigned peer help sessions. Click "Open Workspace" for live chat and timer controls.</p>
        </div>
      </div>

      {error && <p role="alert" className="error">{error}</p>}
      {loading && <p>Loading sessions…</p>}
      {!loading && !sessions.length && (
        <p>No sessions yet. Post a doubt or add mentoring availability to receive matches.</p>
      )}

      <div className="cards">
        {sessions.map((s) => {
          const isMentor = s.mentor_id === actor;
          const peerName = isMentor
            ? s.requester_name || students.find((p) => p.id === s.requester_id)?.name || s.requester_id
            : s.mentor_name || students.find((p) => p.id === s.mentor_id)?.name || s.mentor_id;

          return (
            <section key={s.id} className="session-card">
              <div className="session-card-header">
                <span className="badge">{s.state}</span>
                {s.bounty ? <span className="badge bounty">★ {s.bounty} pts</span> : null}
              </div>

              <h2>
                {s.doubt_title || `Session ${s.id.slice(0, 8)}`}
              </h2>
              <p className="session-role">
                <strong>{isMentor ? 'Mentoring' : 'Assisted by'}:</strong> {peerName}
              </p>
              <p className="session-time">
                {time(s.start)} – {time(s.end)}
              </p>

              {s.state === 'OFFERED' && (
                <p className="alert-notice">Offer expires: {time(s.offer_expires_at)}</p>
              )}

              {s.explanation?.suitability !== undefined && (
                <details>
                  <summary>Allocation score: {s.explanation.suitability.toFixed(1)}/100</summary>
                  <p>{s.explanation.reason}</p>
                </details>
              )}

              <div className="actions">
                <button className="primary" onClick={() => setActiveSessionId(s.id)}>
                  Open Live Workspace →
                </button>

                {isMentor && s.state === 'OFFERED' && (
                  <>
                    <button onClick={() => action(s.id, 'accept')}>Accept</button>
                    <button onClick={() => action(s.id, 'decline')}>Decline</button>
                  </>
                )}

                {isMentor && s.state === 'ACCEPTED' && (
                  <button onClick={() => action(s.id, 'start')}>Start Session</button>
                )}

                {['OFFERED', 'ACCEPTED', 'ACTIVE'].includes(s.state) && (
                  <button className="danger" onClick={() => action(s.id, 'cancel')}>Cancel</button>
                )}
              </div>

              {s.feedback && (
                <p className="feedback-line">
                  Outcome: {s.resolved ? '✓ Resolved' : '✗ Unresolved'} · Feedback: {s.feedback.rating}/5
                </p>
              )}
            </section>
          );
        })}
      </div>
    </>
  );
}
