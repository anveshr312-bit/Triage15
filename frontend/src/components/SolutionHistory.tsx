import { useEffect, useState } from 'react';
import { api, SolutionHistoryItem, time } from '../api';
import { CodeSnippetCard } from './session/CodeSnippetCard';
import { ResolutionSummary } from './session/ResolutionSummary';

export function SolutionHistory({
  actor,
  studentName
}: {
  actor: string;
  studentName: string;
}) {
  const [history, setHistory] = useState<SolutionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [domainFilter, setDomainFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSessionId, setExpandedSessionId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetchHistory = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await api<SolutionHistoryItem[]>(`/students/${actor}/solution-history`, actor);
        if (alive) setHistory(data);
      } catch (err: any) {
        if (alive) setError(err.message);
      } finally {
        if (alive) setLoading(false);
      }
    };
    void fetchHistory();
    return () => {
      alive = false;
    };
  }, [actor]);

  const domains = Array.from(new Set(history.map((h) => h.domain)));

  const filtered = history.filter((item) => {
    if (domainFilter !== 'ALL' && item.domain !== domainFilter) return false;
    if (statusFilter === 'RESOLVED' && !item.resolved) return false;
    if (statusFilter === 'UNRESOLVED' && item.resolved !== false) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = item.doubt_title.toLowerCase().includes(q);
      const matchSkills = item.skills.some((s) => s.toLowerCase().includes(q));
      const matchPartner = item.other_student_name.toLowerCase().includes(q);
      if (!matchTitle && !matchSkills && !matchPartner) return false;
    }
    return true;
  });

  return (
    <div className="solution-history" style={{ marginTop: '16px' }}>
      <div className="section-head" style={{ marginBottom: '16px' }}>
        <div>
          <h1>Personal Solution History</h1>
          <p>
            Private archive of your completed and attempted mentoring sessions as <strong>{studentName}</strong>. Revisit root causes, explanations, code snippets, and outcomes.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '16px', alignItems: 'center' }}>
        <input
          type="search"
          placeholder="Search by title, skill, or peer name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', minWidth: '240px', fontSize: '0.85rem' }}
        />

        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
        >
          <option value="ALL">All Domains</option>
          {domains.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
        >
          <option value="ALL">All Outcomes</option>
          <option value="RESOLVED">Resolved Only</option>
          <option value="UNRESOLVED">Unresolved / Attempted</option>
        </select>
      </div>

      {loading && <p style={{ color: '#64748b' }}>Loading solution records…</p>}
      {error && <p style={{ color: '#b91c1c' }}>⚠️ {error}</p>}

      {!loading && filtered.length === 0 && (
        <div style={{ background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '8px', padding: '32px', textAlign: 'center', color: '#64748b' }}>
          No solution records found matching your filters. Complete a session to see persistent problem-solving history here.
        </div>
      )}

      <div>
        {filtered.map((item) => {
          const isExpanded = expandedSessionId === item.session_id;
          return (
            <div
              key={item.session_id}
              style={{
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '14px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: item.role === 'mentor' ? '#e0e7ff' : '#fef3c7',
                        color: item.role === 'mentor' ? '#3730a3' : '#92400e'
                      }}
                    >
                      {item.role === 'mentor' ? 'Mentored by You' : 'Requested by You'}
                    </span>
                    <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', background: '#f1f5f9', color: '#475569' }}>
                      {item.domain}
                    </span>
                    {item.bounty > 0 && (
                      <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', background: '#dcfce7', color: '#166534', fontWeight: 600 }}>
                        ★ {item.bounty} pts
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: item.resolved ? '#dcfce7' : item.resolved === false ? '#fee2e2' : '#f1f5f9',
                        color: item.resolved ? '#166534' : item.resolved === false ? '#991b1b' : '#64748b'
                      }}
                    >
                      {item.resolved ? '✓ Resolved' : item.resolved === false ? '✕ Unresolved' : item.session_state}
                    </span>
                  </div>
                  <h3 style={{ margin: '4px 0', fontSize: '1.05rem', color: '#0f172a' }}>
                    {item.doubt_title}
                  </h3>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{time(item.date)}</div>
                  {item.rating && (
                    <div style={{ fontSize: '0.85rem', color: '#eab308', marginTop: '2px' }}>
                      {'★'.repeat(item.rating)}{'☆'.repeat(5 - item.rating)}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '10px' }}>
                Peer: <strong>{item.other_student_name}</strong> · Skills:{' '}
                {item.skills.map((s) => (
                  <code key={s} style={{ background: '#f1f5f9', padding: '1px 6px', borderRadius: '3px', marginRight: '4px' }}>
                    #{s}
                  </code>
                ))}
              </div>

              {item.resolution ? (
                <ResolutionSummary resolution={item.resolution} />
              ) : (
                <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px', fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>
                  No structured resolution record submitted for this session.
                </div>
              )}

              {item.snippets.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <button
                    className="secondary"
                    style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                    onClick={() => setExpandedSessionId(isExpanded ? null : item.session_id)}
                  >
                    {isExpanded ? 'Hide Code Snippets' : `View Code Snippets (${item.snippets.length})`}
                  </button>

                  {isExpanded && (
                    <div style={{ marginTop: '10px' }}>
                      {item.snippets.map((snip) => (
                        <CodeSnippetCard key={snip.id} snippet={snip} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
