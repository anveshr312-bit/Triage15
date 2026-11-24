import { useCallback, useEffect, useState } from 'react';
import { api, Student, Domains } from './api';
import { Profile } from './components/Profile';
import { DoubtBoard } from './components/DoubtBoard';
import { Sessions } from './components/Sessions';
import { Assessment } from './components/Assessment';
import { Benchmark } from './components/Benchmark';
import { ModelEvaluation } from './components/ModelEvaluation';
import { SolutionHistory } from './components/SolutionHistory';

export default function App() {
  const [students, setStudents] = useState<Student[]>([]);
  const [domains, setDomains] = useState<Domains>({});
  const [actor, setActor] = useState('student-08');
  const [tab, setTab] = useState('Doubt board');
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [metrics, setMetrics] = useState<any>();
  const [dispatch, setDispatch] = useState<any>();

  const refresh = useCallback(() => setRevision((x) => x + 1), []);

  // Initial load and periodic polling (every 4s) for live updates (P1.2)
  useEffect(() => {
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
  }, [actor, revision]);

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
          <label>
            Demo identity
            <select
              value={actor}
              onChange={(e) => {
                setActor(e.target.value);
                setNotice('');
                setError('');
              }}
            >
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.points_balance} pts) {s.mentoring ? '· Mentor' : ''}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <main>
        <p className="banner">
          HackDay Demonstration · Authoritative Server Timestamps (IST) · Deterministic Hungarian Matching Engine · Identity selection is not production auth.
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

        <nav>
          {['Doubt board', 'My sessions', 'Profile & availability', 'Assessments', 'Benchmark', 'ML evaluation', 'Solution history'].map((t) => (
            <button aria-pressed={tab === t} key={t} onClick={() => setTab(t)}>
              {t}
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

                <DoubtBoard actor={actor} domains={domains} students={students} revision={revision} run={run} />
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
