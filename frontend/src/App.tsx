import { useCallback, useEffect, useState } from 'react';
import { api, Student, Domains, setTokenProvider } from './api';
import { supabase } from './supabase';
import { Auth } from './components/Auth';
import { Profile } from './components/Profile';
import { DoubtBoard } from './components/DoubtBoard';
import { Sessions } from './components/Sessions';
import { Assessment } from './components/Assessment';
import { Benchmark } from './components/Benchmark';
import { ModelEvaluation } from './components/ModelEvaluation';
import { SolutionHistory } from './components/SolutionHistory';

export default function App() {
  const [session, setSession] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [students, setStudents] = useState<Student[]>([]);
  const [domains, setDomains] = useState<Domains>({});
  const [actor, setActor] = useState('');
  const [tab, setTab] = useState('Doubt board');
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [metrics, setMetrics] = useState<any>();
  const [dispatch, setDispatch] = useState<any>();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const refresh = useCallback(() => setRevision((x) => x + 1), []);

  // Initialize and track Supabase authentication state
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setTokenProvider(() => session?.access_token || null);
      setAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      setSession(currentSession);
      setTokenProvider(() => currentSession?.access_token || null);
      setAuthLoading(false);
      if (currentSession) {
        setRevision((x) => x + 1);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // Synchronize authenticated student profile from /api/me
  useEffect(() => {
    if (!session) return;
    let alive = true;
    const loadCurrentUser = async () => {
      try {
        const me = await api<Student>('/me');
        if (alive && me) {
          setActor(me.id);
        }
      } catch (e: any) {
        if (alive) setError(e.message);
      }
    };
    void loadCurrentUser();
    return () => {
      alive = false;
    };
  }, [session, revision]);

  // Initial load and periodic polling (every 4s) for live updates (P1.2)
  useEffect(() => {
    if (!session || !actor) return;
    let alive = true;
    const loadState = async () => {
      try {
        const [s, d, m] = await Promise.all([
          api<Student[]>('/students', actor),
          api<Domains>('/domains', actor),
          api<any>('/metrics', actor)
        ]);
        if (alive) {
          setStudents(s);
          setDomains(d);
          setMetrics(m);
        }
      } catch (e: any) {
        if (alive) setError(e.message);
      }
    };

    void loadState();
    const interval = setInterval(loadState, 4000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [session, actor, revision]);

  const run = async (task: () => Promise<unknown>, message = 'Saved') => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await task();
      setNotice(message);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const student = students.find((s) => s.id === actor);

  if (authLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <strong>TRIAGE<span>15</span></strong>
        <p style={{ color: 'var(--text-muted, #666)', marginTop: '8px' }}>Verifying Supabase authentication…</p>
      </div>
    );
  }

  if (!session) {
    return (
      <>
        <header>
          <div className="branding">
            <strong>TRIAGE<span>15</span></strong>
            <p>Peer-to-Peer Micro-Skill & Doubt Bounty Board · 15-Minute Sessions</p>
          </div>
        </header>
        <main>
          <p className="banner">
            Supabase ES256 Asymmetric Authentication Active · Verified SQLite Student Identity
          </p>
          <Auth onAuthSuccess={() => refresh()} />
        </main>
        <footer>
          Deterministic Kuhn-Munkres Rectangular Matching · Exact Integer Point Ledger · Authoritative 15-Minute Timer · Triage15
        </footer>
      </>
    );
  }

  return (
    <>
      <header>
        <div className="branding">
          <strong>TRIAGE<span>15</span></strong>
          <p>Peer-to-Peer Micro-Skill & Doubt Bounty Board · 15-Minute Sessions</p>
        </div>
        <div className="identity-control">
          {student && (
            <div className="student-badge">
              <span>{student.name}</span>
              <span className="badge bounty">★ {student.points_balance} pts</span>
            </div>
          )}
          <div className="user-auth-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="user-email-tag" style={{ fontSize: '0.8rem', color: '#cee0eb' }}>
              {session.user.email}
            </span>
            <button
              type="button"
              className="secondary"
              style={{ padding: '6px 12px', fontSize: '0.85rem', minHeight: '38px' }}
              onClick={async () => {
                await supabase.auth.signOut();
                setSession(null);
                setActor('');
                setTokenProvider(() => null);
              }}
            >
              Sign Out
            </button>
            <button
              type="button"
              className="mobile-nav-toggle"
              aria-label="Toggle navigation menu"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? '✕ Close' : '☰ Menu'}
            </button>
          </div>
        </div>
      </header>

      <main>
        <p className="banner">
          Supabase ES256 Authenticated · Authoritative Server Timestamps (IST) · Deterministic Hungarian Matching Engine
        </p>

        {metrics && (
          <div className="metrics">
            <div>
              <b>{(metrics.doubts.OPEN || 0) + (metrics.doubts.UNMATCHED || 0)}</b> waiting requests
            </div>
            <div>
              <b>{metrics.sessions.OFFERED || 0}</b> active mentor offers
            </div>
            <div>
              <b>{metrics.resolved_sessions || 0}</b> resolved sessions
            </div>
            <div>
              <b>{metrics.average_rating ? metrics.average_rating.toFixed(1) : '—'}</b> avg feedback ({metrics.feedback_count || 0})
            </div>
            <div>
              <b>★ {metrics.total_bounties_awarded || 0}</b> bounties awarded
            </div>
          </div>
        )}

        <nav className={`main-nav ${mobileMenuOpen ? 'mobile-open' : ''}`}>
          {['Doubt board', 'My sessions', 'Profile & availability', 'Assessments', 'Benchmark', 'ML evaluation', 'Solution history'].map((t) => (
            <button
              aria-pressed={tab === t}
              key={t}
              onClick={() => {
                setTab(t);
                setMobileMenuOpen(false);
              }}
            >
              {t === 'My sessions' && (metrics?.sessions?.OFFERED || 0) > 0 ? `🔔 ${t} (${metrics.sessions.OFFERED})` : t}
            </button>
          ))}
        </nav>

        {error && <p role="alert" className="error">{error}</p>}
        {notice && <p role="status" className="success">{notice}</p>}
        {busy && <p role="status" className="busy-indicator">Working…</p>}

        {!student ? (
          <p>Loading profiles…</p>
        ) : (
          <fieldset disabled={busy} className="workspace">
            {tab === 'Doubt board' && (
              <>
                <div className="section-head">
                  <div>
                    <h1>Find the Right Peer.</h1>
                    <p>Post a technical doubt with an optional bounty. Automatic matching runs continuously, or trigger manual dispatch below.</p>
                  </div>
                  <button
                    className="primary"
                    onClick={() =>
                      run(async () => setDispatch(await api('/dispatch/run', actor, 'POST')), 'Manual dispatch completed')
                    }
                  >
                    Run Dispatch (Manual)
                  </button>
                </div>

                {dispatch && (
                  <section className="dispatch-summary">
                    <h2>Dispatch Results & Allocation Analysis</h2>
                    <p>
                      <strong>{dispatch.result.assignments.length}</strong> offers generated ·{' '}
                      <strong>{dispatch.result.unassigned.length}</strong> waiting ·{' '}
                      <strong>{dispatch.result.final_validation_rejections?.length || 0}</strong> validation rejections ·{' '}
                      <strong>{dispatch.result.recovery_iterations || 1}</strong> recovery iterations
                    </p>
                    {dispatch.result.comparison && (
                      <p>
                        Candidate matrix utility: Hungarian{' '}
                        <strong>{dispatch.result.comparison.optimized?.total_utility?.toFixed(2)}</strong> vs Greedy{' '}
                        <strong>{dispatch.result.comparison.greedy?.total_utility?.toFixed(2)}</strong>
                      </p>
                    )}
                    {dispatch.result.unassigned?.length > 0 && (
                      <details>
                        <summary>Unassigned explanations ({dispatch.result.unassigned.length})</summary>
                        {dispatch.result.unassigned.map((x: any) => (
                          <p key={x.id}>
                            <code>{x.id}</code>: {x.reason}
                          </p>
                        ))}
                      </details>
                    )}
                  </section>
                )}

                <DoubtBoard
                  actor={actor}
                  domains={domains}
                  students={students}
                  revision={revision}
                  run={run}
                  onNavigateToSessions={() => setTab('My sessions')}
                />
              </>
            )}

            {tab === 'My sessions' && (
              <Sessions actor={actor} students={students} revision={revision} run={run} />
            )}

            {tab === 'Profile & availability' && (
              <Profile key={actor + revision} student={student} domains={domains} run={run} />
            )}

            {tab === 'Assessments' && (
              <Assessment key={actor} actor={actor} run={run} />
            )}

            {tab === 'Benchmark' && (
              <Benchmark actor={actor} run={run} />
            )}
            {tab === 'ML evaluation' && <ModelEvaluation />}

            {tab === 'Solution history' && (
              <SolutionHistory actor={actor} studentName={student.name} />
            )}
          </fieldset>
        )}
      </main>

      <footer>
        Deterministic Kuhn-Munkres Rectangular Matching · Exact Integer Point Ledger · Authoritative 15-Minute Timer · Triage15
      </footer>
    </>
  );
}

export type Run = (task: () => Promise<unknown>, message?: string) => Promise<void>;
