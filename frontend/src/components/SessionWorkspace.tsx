import { useEffect, useState, useRef } from 'react';
import { api, Session, SessionMessage, Student, time, formatClock } from '../api';
import { Run } from '../App';

export function SessionWorkspace({
  session,
  actor,
  students,
  run,
  onBack
}: {
  session: Session;
  actor: string;
  students: Student[];
  run: Run;
  onBack: () => void;
}) {
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [newMsg, setNewMsg] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [currentSession, setCurrentSession] = useState<Session>(session);
  const [secondsLeft, setSecondsLeft] = useState<number>(session.active_seconds_remaining ?? 900);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const isMentor = actor === currentSession.mentor_id;
  const isRequester = actor === currentSession.requester_id;
  const isParticipant = isMentor || isRequester;

  // Authoritative countdown timer (ticks every second based on session timestamps)
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) return 0;
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll for messages and session updates every 2.5s
  useEffect(() => {
    let alive = true;
    const fetchSessionAndMessages = async () => {
      try {
        const [updatedSess, msgList] = await Promise.all([
          api<Session>(`/sessions/${session.id}`, actor),
          api<SessionMessage[]>(`/sessions/${session.id}/messages`, actor)
        ]);
        if (alive) {
          setCurrentSession(updatedSess);
          if (updatedSess.active_seconds_remaining !== undefined) {
            setSecondsLeft(updatedSess.active_seconds_remaining);
          }
          setMessages(msgList);
          setError('');
        }
      } catch (err: any) {
        if (alive) setError(err.message);
      }
    };

    void fetchSessionAndMessages();
    const interval = setInterval(fetchSessionAndMessages, 2500);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [session.id, actor]);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsg.trim() || sending) return;
    setSending(true);
    try {
      const posted = await api<SessionMessage>(`/sessions/${session.id}/messages`, actor, 'POST', {
        content: newMsg.trim()
      });
      setMessages((prev) => [...prev, posted]);
      setNewMsg('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const handleAction = (actionName: string, body?: any, successMsg = 'Session updated') => {
    void run(async () => {
      const updated = await api<Session>(`/sessions/${session.id}/${actionName}`, actor, 'POST', body);
      setCurrentSession(updated);
    }, successMsg);
  };

  const handleAccelerate = () => {
    void run(async () => {
      const updated = await api<Session>(`/sessions/${session.id}/accelerate`, actor, 'POST');
      setCurrentSession(updated);
      setSecondsLeft(30);
    }, 'Session timer accelerated to 30-second judge demo clock');
  };

  return (
    <div className="session-workspace">
      <div className="workspace-header">
        <button onClick={onBack} className="secondary">← Back to sessions</button>
        <div className="workspace-title-bar">
          <h2>
            {currentSession.doubt_title || `Session ${currentSession.id.slice(0, 8)}`}
            {currentSession.bounty ? <span className="badge bounty">★ {currentSession.bounty} pts bounty</span> : null}
            <span className="badge">{currentSession.state}</span>
          </h2>
          <p className="participants">
            <strong>Mentor:</strong> {currentSession.mentor_name || currentSession.mentor_id} ·{' '}
            <strong>Requester:</strong> {currentSession.requester_name || currentSession.requester_id}
          </p>
        </div>
      </div>

      {error && <p role="alert" className="error">{error}</p>}

      {/* Authoritative 15-Minute Countdown Timer Widget */}
      <section className="timer-card">
        <div className="timer-display">
          <span className="timer-digits">{formatClock(secondsLeft)}</span>
          <div className="timer-info">
            <strong>
              {currentSession.is_demo_accelerated
                ? 'Accelerated Demo Mode (30-second window)'
                : '15-Minute Scheduled Session Window'}
            </strong>
            <p>
              Scheduled: {time(currentSession.start)} – {time(currentSession.end)}
              {currentSession.state === 'ACTIVE' && secondsLeft === 0 && ' · Window ended; ready for outcome confirmation'}
            </p>
          </div>
          {currentSession.state === 'ACTIVE' && !currentSession.is_demo_accelerated && (
            <button onClick={handleAccelerate} className="demo-btn" title="Accelerate timer for quick hackathon evaluation">
              ⚡ Demo Clock (30s)
            </button>
          )}
        </div>
      </section>

      <div className="workspace-grid">
        {/* Left column: Doubt context & participant controls */}
        <div className="workspace-left">
          <section className="doubt-details-card">
            <h3>Doubt Context</h3>
            <p className="doubt-desc">{currentSession.doubt_description || 'No description provided.'}</p>
            <div className="doubt-meta">
              <span><strong>Domain:</strong> {currentSession.doubt_domain || '—'}</span>
              <span><strong>Urgency:</strong> {currentSession.doubt_urgency || 'Normal'}</span>
              <span><strong>Skills:</strong> {currentSession.doubt_skills?.join(', ') || '—'}</span>
            </div>
          </section>

          {/* Allocation explanation */}
          {currentSession.explanation?.suitability !== undefined && (
            <section className="explanation-card">
              <h4>Matching Explanation (Score {currentSession.explanation.suitability.toFixed(1)}/100)</h4>
              <p>{currentSession.explanation.reason}</p>
              <small>{currentSession.explanation.evidence_label}</small>
            </section>
          )}

          {/* Action buttons */}
          <section className="session-actions-card">
            <h3>Session Lifecycle Controls</h3>
            <div className="action-buttons">
              {isMentor && currentSession.state === 'OFFERED' && (
                <>
                  <button className="primary" onClick={() => handleAction('accept', undefined, 'Offer accepted')}>
                    Accept Offer
                  </button>
                  <button onClick={() => handleAction('decline', undefined, 'Offer declined')}>
                    Decline Offer
                  </button>
                </>
              )}

              {isMentor && currentSession.state === 'ACCEPTED' && (
                <button className="primary" onClick={() => handleAction('start', undefined, 'Session started')}>
                  ▶ Start 15-Minute Session
                </button>
              )}

              {isMentor && currentSession.state === 'ACTIVE' && !currentSession.mentor_completed && (
                <button onClick={() => handleAction('complete', undefined, 'Mentor finished assistance')}>
                  ✓ Mark Assistance Complete
                </button>
              )}

              {['OFFERED', 'ACCEPTED', 'ACTIVE'].includes(currentSession.state) && (
                <button className="danger" onClick={() => handleAction('cancel', undefined, 'Session cancelled')}>
                  Cancel Session
                </button>
              )}
            </div>

            {/* Requester confirmation form */}
            {isRequester && (currentSession.state === 'AWAITING_CONFIRMATION' || (currentSession.state === 'ACTIVE' && currentSession.mentor_completed)) && (
              <form
                className="outcome-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  const data = new FormData(e.currentTarget);
                  handleAction(
                    'resolve',
                    {
                      resolved: data.get('resolved') === 'yes',
                      rating: Number(data.get('rating')),
                      notes: String(data.get('notes') || '')
                    },
                    'Outcome and rating confirmed'
                  );
                }}
              >
                <h4>Confirm Session Resolution</h4>
                <p>Mentor has concluded. Confirm if your doubt was resolved to settle the virtual bounty.</p>
                <label>
                  Was your doubt resolved?
                  <select name="resolved">
                    <option value="yes">Yes, resolved (award bounty)</option>
                    <option value="no">No, return to queue</option>
                  </select>
                </label>
                <label>
                  Mentor rating (1–5)
                  <input type="number" name="rating" min="1" max="5" defaultValue="5" required />
                </label>
                <label>
                  Feedback notes
                  <textarea name="notes" placeholder="What worked well in this 15-minute session?" maxLength={2000} />
                </label>
                <button className="primary" type="submit">Submit Final Outcome</button>
              </form>
            )}

            {currentSession.feedback && (
              <div className="feedback-summary">
                <h4>Settled Feedback</h4>
                <p>
                  <strong>Outcome:</strong> {currentSession.resolved ? '✓ Resolved' : '✗ Unresolved'} ·{' '}
                  <strong>Rating:</strong> {currentSession.feedback.rating}/5
                </p>
                {currentSession.feedback.notes && <p>"{currentSession.feedback.notes}"</p>}
              </div>
            )}
          </section>
        </div>

        {/* Right column: Live Chat Workspace */}
        <div className="workspace-right">
          <section className="chat-card">
            <h3>Live Workspace Messages</h3>
            <p className="chat-subtitle">Direct peer communication. Supports code blocks.</p>

            <div className="chat-history">
              {messages.length === 0 ? (
                <p className="empty-chat">No messages yet. Greet your peer to get started!</p>
              ) : (
                messages.map((m) => {
                  const isMe = m.sender_id === actor;
                  const senderName = students.find((s) => s.id === m.sender_id)?.name || m.sender_id;
                  return (
                    <div key={m.id} className={`chat-message ${isMe ? 'message-mine' : 'message-peer'}`}>
                      <div className="message-header">
                        <strong>{senderName} {isMe ? '(You)' : ''}</strong>
                        <small>{time(m.created_at)}</small>
                      </div>
                      <div className="message-content">
                        {m.content.includes('```') ? (
                          <pre><code>{m.content}</code></pre>
                        ) : (
                          <p>{m.content}</p>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={chatBottomRef} />
            </div>

            {isParticipant && currentSession.state !== 'RESOLVED' && currentSession.state !== 'CANCELLED' && currentSession.state !== 'EXPIRED' ? (
              <form onSubmit={handleSendMessage} className="chat-input-form">
                <textarea
                  value={newMsg}
                  onChange={(e) => setNewMsg(e.target.value)}
                  placeholder="Type a message or paste code... (Ctrl+Enter to send)"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                      void handleSendMessage(e);
                    }
                  }}
                  rows={3}
                  required
                />
                <button type="submit" disabled={sending || !newMsg.trim()} className="primary">
                  {sending ? 'Sending…' : 'Send'}
                </button>
              </form>
            ) : (
              <p className="chat-closed-notice">Session closed. Conversation is preserved as read-only.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
