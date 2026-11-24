import { useEffect, useState, useRef } from 'react';
import { api, Session, SessionMessage, Student, SessionMeeting, SessionCodeSnippet, SessionResolution, time, formatClock } from '../api';
import { Run } from '../App';
import { MeetingPanel } from './session/MeetingPanel';
import { CodeSnippetList } from './session/CodeSnippetList';
import { CodeComparison } from './session/CodeComparison';
import { ResolutionEditor } from './session/ResolutionEditor';
import { ResolutionReview } from './session/ResolutionReview';
import { ResolutionSummary } from './session/ResolutionSummary';

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
  
  // Mentoring Workspace states
  const [meeting, setMeeting] = useState<SessionMeeting | null>(null);
  const [snippets, setSnippets] = useState<SessionCodeSnippet[]>([]);
  const [resolution, setResolution] = useState<SessionResolution | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'code' | 'diff' | 'resolution'>('chat');
  const [diffPair, setDiffPair] = useState<{ origId?: string; propId?: string } | null>(null);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  const isMentor = actor === currentSession.mentor_id;
  const isRequester = actor === currentSession.requester_id;
  const isParticipant = isMentor || isRequester;

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll for messages, meeting, snippets, and session updates every 2.5s
  useEffect(() => {
    let alive = true;
    const fetchSessionWorkspace = async () => {
      try {
        const [updatedSess, msgList, snipList] = await Promise.all([
          api<Session>(`/sessions/${session.id}`, actor),
          api<SessionMessage[]>(`/sessions/${session.id}/messages`, actor),
          api<SessionCodeSnippet[]>(`/sessions/${session.id}/snippets`, actor)
        ]);

        if (alive) {
          setCurrentSession(updatedSess);
          if (updatedSess.active_seconds_remaining !== undefined) {
            setSecondsLeft(updatedSess.active_seconds_remaining);
          }
          setMessages(msgList);
          setSnippets(snipList);
          setError('');
        }

        // Fetch meeting separately to handle 404 cleanly
        try {
          const mData = await api<SessionMeeting>(`/sessions/${session.id}/meeting`, actor);
          if (alive) setMeeting(mData);
        } catch {
          if (alive) setMeeting(null);
        }

        // Fetch resolution if in outcome stage
        try {
          const rData = await api<SessionResolution>(`/sessions/${session.id}/resolution`, actor);
          if (alive) setResolution(rData);
        } catch {
          if (alive) setResolution(null);
        }
      } catch (err: any) {
        if (alive) setError(err.message);
      }
    };

    void fetchSessionWorkspace();
    const interval = setInterval(fetchSessionWorkspace, 2500);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [session.id, actor]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (activeTab === 'chat') {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, activeTab]);

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

  const handleOpenDiff = (origId: string, propId: string) => {
    setDiffPair({ origId, propId });
    setActiveTab('diff');
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
      <section className="timer-card" style={{ marginBottom: '16px' }}>
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

      {/* Google Meet Panel */}
      <MeetingPanel
        sessionId={currentSession.id}
        actor={actor}
        isMentor={isMentor}
        meeting={meeting}
        onMeetingUpdated={(m) => setMeeting(m)}
      />

      {/* Workspace Navigation Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '2px solid #e2e8f0', marginBottom: '16px' }}>
        <button
          style={{
            padding: '8px 16px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'chat' ? 600 : 400,
            borderBottom: activeTab === 'chat' ? '3px solid #2563eb' : '3px solid transparent',
            color: activeTab === 'chat' ? '#2563eb' : '#64748b'
          }}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat Messages ({messages.length})
        </button>
        <button
          style={{
            padding: '8px 16px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'code' ? 600 : 400,
            borderBottom: activeTab === 'code' ? '3px solid #2563eb' : '3px solid transparent',
            color: activeTab === 'code' ? '#2563eb' : '#64748b'
          }}
          onClick={() => setActiveTab('code')}
        >
          💻 Code Snippets ({snippets.length})
        </button>
        <button
          style={{
            padding: '8px 16px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'diff' ? 600 : 400,
            borderBottom: activeTab === 'diff' ? '3px solid #2563eb' : '3px solid transparent',
            color: activeTab === 'diff' ? '#2563eb' : '#64748b'
          }}
          onClick={() => setActiveTab('diff')}
        >
          🔍 Before & After Diff
        </button>
        <button
          style={{
            padding: '8px 16px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'resolution' ? 600 : 400,
            borderBottom: activeTab === 'resolution' ? '3px solid #2563eb' : '3px solid transparent',
            color: activeTab === 'resolution' ? '#2563eb' : '#64748b'
          }}
          onClick={() => setActiveTab('resolution')}
        >
          📝 Solution & Outcome {resolution?.requester_status === 'CONFIRMED_RESOLVED' ? '✓' : ''}
        </button>
      </div>

      <div className="workspace-grid">
        {/* Left column: Context & Controls */}
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

          {currentSession.explanation?.suitability !== undefined && (
            <section className="explanation-card">
              <h4>Matching Explanation (Score {currentSession.explanation.suitability.toFixed(1)}/100)</h4>
              <p>{currentSession.explanation.reason}</p>
              <small>{currentSession.explanation.evidence_label}</small>
            </section>
          )}

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
                <button onClick={() => setActiveTab('resolution')} style={{ background: '#2563eb', color: '#fff' }}>
                  📝 Prepare & Submit Resolution
                </button>
              )}

              {['OFFERED', 'ACCEPTED', 'ACTIVE'].includes(currentSession.state) && (
                <button className="danger" onClick={() => handleAction('cancel', undefined, 'Session cancelled')}>
                  Cancel Session
                </button>
              )}
            </div>

            {/* Requester confirmation form (if awaiting confirmation) */}
            {isRequester && (currentSession.state === 'AWAITING_CONFIRMATION' || (currentSession.state === 'ACTIVE' && currentSession.mentor_completed)) && (
              <ResolutionReview
                sessionId={currentSession.id}
                actor={actor}
                bountyAmount={currentSession.bounty || 0}
                onResolved={() => {
                  void run(async () => {
                    const updated = await api<Session>(`/sessions/${session.id}`, actor);
                    setCurrentSession(updated);
                  }, 'Outcome settled');
                }}
              />
            )}

            {resolution && currentSession.state === 'RESOLVED' && (
              <ResolutionSummary resolution={resolution} />
            )}

            {currentSession.feedback && !resolution && (
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

        {/* Right column: Active Tool / Tab Content */}
        <div className="workspace-right">
          {activeTab === 'chat' && (
            <section className="chat-card">
              <h3>Live Workspace Messages</h3>
              <p className="chat-subtitle">Direct peer communication. Paste questions, thoughts or short logs.</p>

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
                    placeholder="Type a message... (Ctrl+Enter to send)"
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
          )}

          {activeTab === 'code' && (
            <CodeSnippetList
              sessionId={currentSession.id}
              actor={actor}
              snippets={snippets}
              onSnippetAdded={(snip) => setSnippets((prev) => [...prev, snip])}
              onOpenDiff={handleOpenDiff}
            />
          )}

          {activeTab === 'diff' && (
            snippets.length >= 2 ? (
              <CodeComparison
                sessionId={currentSession.id}
                actor={actor}
                snippets={snippets}
                initialOriginalId={diffPair?.origId}
                initialProposedId={diffPair?.propId}
                onClose={() => setActiveTab('code')}
              />
            ) : (
              <div style={{ background: '#f8fafc', padding: '24px', borderRadius: '8px', border: '1px dashed #cbd5e1', textAlign: 'center', color: '#64748b' }}>
                At least two code snippets are needed to compute a diff. Post an original snippet and a proposed fix in the Code Snippets tab.
              </div>
            )
          )}

          {activeTab === 'resolution' && (
            <div>
              {isMentor && (currentSession.state === 'ACTIVE' || currentSession.state === 'AWAITING_CONFIRMATION') ? (
                <ResolutionEditor
                  sessionId={currentSession.id}
                  actor={actor}
                  snippets={snippets}
                  onResolutionSubmitted={() => {
                    void run(async () => {
                      const updated = await api<Session>(`/sessions/${session.id}`, actor);
                      setCurrentSession(updated);
                    }, 'Resolution submitted');
                  }}
                />
              ) : isRequester && (currentSession.state === 'AWAITING_CONFIRMATION' || currentSession.mentor_completed) ? (
                <ResolutionReview
                  sessionId={currentSession.id}
                  actor={actor}
                  bountyAmount={currentSession.bounty || 0}
                  onResolved={() => {
                    void run(async () => {
                      const updated = await api<Session>(`/sessions/${session.id}`, actor);
                      setCurrentSession(updated);
                    }, 'Outcome resolved');
                  }}
                />
              ) : resolution ? (
                <ResolutionSummary resolution={resolution} />
              ) : (
                <div style={{ background: '#f8fafc', padding: '24px', borderRadius: '8px', border: '1px dashed #cbd5e1', textAlign: 'center', color: '#64748b' }}>
                  No resolution record submitted yet. The mentor will prepare and submit the technical resolution when ready.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
