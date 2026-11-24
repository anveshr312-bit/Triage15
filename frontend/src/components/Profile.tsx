import { useEffect, useState } from 'react';
import { api, Domains, Student, PointTransaction, MentorProfile, time, fromIST } from '../api';
import { Run } from '../App';

export function Profile({
  student,
  domains,
  run
}: {
  student: Student;
  domains: Domains;
  run: Run;
}) {
  const [mentoring, setMentoring] = useState(student.mentoring);
  const [skills, setSkills] = useState(student.skills);
  const [domain, setDomain] = useState('Python');
  const [level, setLevel] = useState(3);
  const [ledger, setLedger] = useState<PointTransaction[]>([]);
  const [credibility, setCredibility] = useState<MentorProfile | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'credibility' | 'ledger'>('profile');

  useEffect(() => {
    let alive = true;
    api<PointTransaction[]>(`/students/${student.id}/ledger`, student.id)
      .then((entries) => {
        if (alive) setLedger(entries);
      })
      .catch(() => {});

    api<MentorProfile>(`/mentors/${student.id}/profile`, student.id)
      .then((prof) => {
        if (alive) setCredibility(prof);
      })
      .catch(() => {});

    return () => {
      alive = false;
    };
  }, [student.id]);

  return (
    <>
      <div className="section-head">
        <div>
          <h1>Profile, Availability & Reputation</h1>
          <p>
            Current Balance: <strong>★ {student.points_balance} points</strong> · Self-declared levels are kept distinct from assessment evidence.
          </p>
        </div>
      </div>

      <nav className="sub-nav">
        <button aria-pressed={activeSubTab === 'profile'} onClick={() => setActiveSubTab('profile')}>
          Profile & Availability
        </button>
        <button aria-pressed={activeSubTab === 'credibility'} onClick={() => setActiveSubTab('credibility')}>
          Mentor Credibility
        </button>
        <button aria-pressed={activeSubTab === 'ledger'} onClick={() => setActiveSubTab('ledger')}>
          Points Ledger & Bounties ({ledger.length})
        </button>
      </nav>

      {activeSubTab === 'profile' && (
        <>
          <div className="columns">
            <section>
              <h2>{student.name}</h2>
              <label className="check">
                <input
                  type="checkbox"
                  checked={mentoring}
                  onChange={(e) => setMentoring(e.target.checked)}
                />{' '}
                Opt into mentoring peers
              </label>

              <label>
                Domain
                <select value={domain} onChange={(e) => setDomain(e.target.value)}>
                  {Object.keys(domains).map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </label>

              <label>
                Self-declared level (1–5)
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={level}
                  onChange={(e) => setLevel(+e.target.value)}
                />
              </label>

              <div className="tags-label">Skills in {domain}:</div>
              <div className="tags">
                {domains[domain]?.map((tag) => (
                  <label className="check" key={tag}>
                    <input
                      type="checkbox"
                      checked={skills.some((s) => s.domain === domain && s.tag === tag)}
                      onChange={(e) =>
                        setSkills(
                          e.target.checked
                            ? [...skills, { domain, tag, level }]
                            : skills.filter((s) => !(s.domain === domain && s.tag === tag))
                        )
                      }
                    />
                    {tag}
                  </label>
                ))}
              </div>

              <div className="skills-list">
                <h4>Declared Skills</h4>
                {skills.length === 0 && <p className="subtext">No skills declared yet.</p>}
                <ul>
                  {skills.map((s) => (
                    <li key={s.domain + s.tag}>
                      <strong>{s.domain}</strong> / {s.tag}: level {s.level} (provisional self-declaration)
                    </li>
                  ))}
                </ul>
              </div>

              <button
                className="primary"
                onClick={() => {
                  const sanitizedSkills = skills.map((s) => ({
                    domain: s.domain,
                    tag: s.tag,
                    level: s.level
                  }));
                  run(
                    () => api('/students/' + student.id + '/profile', student.id, 'PUT', { mentoring, skills: sanitizedSkills }),
                    'Profile and skills updated'
                  );
                }}
              >
                Save Profile
              </button>
            </section>

            <section>
              <h2>Mentoring Availability</h2>
              <p className="subtext">
                Slots are rounded inward to the 15-minute grid. Add availability windows within the next 7 days.
              </p>

              <div className="availability-list">
                {student.availability.length === 0 && <p>No availability windows set.</p>}
                {student.availability.map((w) => (
                  <div key={w.id} className="avail-row">
                    <span>
                      {time(w.start)} – {time(w.end)}
                    </span>
                    <button
                      className="danger small"
                      onClick={() =>
                        run(
                          () => api(`/students/${student.id}/availability/${w.id}`, student.id, 'DELETE'),
                          'Availability window removed'
                        )
                      }
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = e.currentTarget;
                  const data = new FormData(f);
                  void run(async () => {
                    await api('/students/' + student.id + '/availability', student.id, 'POST', {
                      start: fromIST(String(data.get('start'))),
                      end: fromIST(String(data.get('end')))
                    });
                    f.reset();
                  }, 'Availability window added');
                }}
              >
                <h3>Add Availability Window</h3>
                <label>
                  Start (IST)
                  <input required name="start" type="datetime-local" />
                </label>
                <label>
                  End (IST)
                  <input required name="end" type="datetime-local" />
                </label>
                <button type="submit">Add Window</button>
              </form>
            </section>
          </div>

          <section className="demo-register-card">
            <h2>Register New Demo Profile</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = e.currentTarget;
                void run(async () => {
                  await api('/students', student.id, 'POST', {
                    name: String(new FormData(f).get('name'))
                  });
                  f.reset();
                }, 'Profile created with initial 100 points grant; select it in the identity menu');
              }}
            >
              <label>
                Display name
                <input required minLength={2} maxLength={80} name="name" placeholder="e.g. Priya Sharma (demo)" />
              </label>
              <button type="submit">Create Profile</button>
            </form>
          </section>
        </>
      )}

      {activeSubTab === 'credibility' && credibility && (
        <section className="credibility-section">
          <h2>Mentor Credibility Card: {credibility.name}</h2>
          <p className="subtext">
            Transparent metrics based strictly on confirmed session outcomes. A small assessment is evidence, not certification.
          </p>

          <div className="metrics-grid">
            <div className="metric-box">
              <span className="metric-val">{credibility.resolution_history_label}</span>
              <span className="metric-label">Confirmed Resolution Rate</span>
            </div>
            <div className="metric-box">
              <span className="metric-val">{credibility.completed_sessions}</span>
              <span className="metric-label">Completed Sessions</span>
            </div>
            <div className="metric-box">
              <span className="metric-val">
                {credibility.average_rating ? `${credibility.average_rating}/5` : '—'}
              </span>
              <span className="metric-label">Avg Feedback ({credibility.feedback_count} ratings)</span>
            </div>
            <div className="metric-box">
              <span className="metric-val">★ {credibility.bounties_earned} pts</span>
              <span className="metric-label">Bounties Earned</span>
            </div>
          </div>

          <div className="credibility-details">
            <h3>Domain Assessment Evidence</h3>
            {credibility.assessments.length === 0 ? (
              <p>No assessment attempts recorded. Skills remain provisional self-declarations.</p>
            ) : (
              <ul>
                {credibility.assessments.map((a) => (
                  <li key={a.id}>
                    <strong>{a.domain}:</strong> {a.score}% score ({a.correct_count}/{a.question_count} correct) · Version {a.version} · Taken {time(a.created_at)}
                  </li>
                ))}
              </ul>
            )}

            <h3>Reliability Calculation</h3>
            <p className="subtext">
              Smoothed Bayesian heuristic: <code>15 × (resolved + 2) / (completed + 4) = {credibility.smoothed_reliability_heuristic.toFixed(2)} / 15.0</code>.
              Prior smoothing prevents zero-session mentors from having an artificial 0% or 100% rating.
            </p>
          </div>
        </section>
      )}

      {activeSubTab === 'ledger' && (
        <section className="ledger-section">
          <h2>Point Ledger & Reputation Transactions</h2>
          <p className="subtext">
            Auditable double-entry record of initial allocations, reservations, awards, refunds, and adjustments.
          </p>

          <table className="ledger-table">
            <thead>
              <tr>
                <th>Time (IST)</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Balance After</th>
                <th>Reference ID</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {ledger.length === 0 ? (
                <tr>
                  <td colSpan={6}>No ledger entries recorded yet.</td>
                </tr>
              ) : (
                ledger.map((tx) => (
                  <tr key={tx.id}>
                    <td>{time(tx.created_at)}</td>
                    <td>
                      <span className={`badge tx-${tx.transaction_type.toLowerCase()}`}>
                        {tx.transaction_type}
                      </span>
                    </td>
                    <td className={tx.amount >= 0 ? 'credit' : 'debit'}>
                      {tx.amount > 0 ? `+${tx.amount}` : tx.amount} pts
                    </td>
                    <td>★ {tx.balance_after} pts</td>
                    <td><code>{tx.reference_id}</code></td>
                    <td>{tx.notes || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}
