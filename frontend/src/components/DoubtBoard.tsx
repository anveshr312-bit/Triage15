import { useEffect, useState } from 'react';
import { api, Domains, Student, Doubt, time, fromIST } from '../api';
import { Run } from '../App';

export function DoubtBoard({
  actor,
  domains,
  students,
  revision,
  run
}: {
  actor: string;
  domains: Domains;
  students: Student[];
  revision: number;
  run: Run;
}) {
  const [items, setItems] = useState<Doubt[]>([]);
  const [domain, setDomain] = useState('Python');
  const [tags, setTags] = useState<string[]>(['python']);
  const [bounty, setBounty] = useState<number>(0);
  const [filters, setFilters] = useState({
    domain: '',
    skill: '',
    urgency: '',
    status: '',
    search: '',
    sortBy: 'newest'
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [editingDoubt, setEditingDoubt] = useState<Doubt | null>(null);

  const currentStudent = students.find((s) => s.id === actor);
  const pointsAvailable = currentStudent?.points_balance ?? 0;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.domain) params.set('domain', filters.domain);
    if (filters.skill) params.set('skill', filters.skill);
    if (filters.urgency) params.set('urgency', filters.urgency);
    if (filters.status) params.set('status', filters.status);
    if (filters.search) params.set('search', filters.search);

    api<Doubt[]>('/doubts?' + params.toString(), actor)
      .then((d) => {
        if (alive) {
          let sorted = [...d];
          if (filters.sortBy === 'bounty') {
            sorted.sort((a, b) => (b.bounty || 0) - (a.bounty || 0));
          } else if (filters.sortBy === 'urgency') {
            const rank: Record<string, number> = { Urgent: 3, Normal: 2, Flexible: 1 };
            sorted.sort((a, b) => (rank[b.urgency] || 0) - (rank[a.urgency] || 0));
          }
          setItems(sorted);
          setError('');
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [actor, revision, filters]);

  const handlePostDoubt = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = e.currentTarget;
    const data = new FormData(f);
    void run(async () => {
      await api(
        '/doubts',
        actor,
        'POST',
        {
          title: String(data.get('title')),
          description: String(data.get('description')),
          domain,
          skills: tags,
          urgency: String(data.get('urgency')),
          bounty: Number(data.get('bounty') || 0),
          preferred_start: fromIST(String(data.get('start'))),
          deadline: fromIST(String(data.get('deadline')))
        },
        { 'X-Auto-Dispatch': 'true' }
      );
      f.reset();
      setBounty(0);
    }, 'Doubt posted and submitted to automatic matching');
  };

  const handleEditDoubt = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingDoubt) return;
    const f = e.currentTarget;
    const data = new FormData(f);
    void run(async () => {
      await api(
        `/doubts/${editingDoubt.id}`,
        actor,
        'PATCH',
        {
          title: String(data.get('title')),
          description: String(data.get('description')),
          domain: editingDoubt.domain,
          skills: editingDoubt.skills,
          urgency: String(data.get('urgency')),
          bounty: Number(data.get('bounty') || 0),
          preferred_start: fromIST(String(data.get('start'))),
          deadline: fromIST(String(data.get('deadline')))
        },
        { 'X-Auto-Dispatch': 'true' }
      );
      setEditingDoubt(null);
    }, 'Doubt updated successfully');
  };

  const handleClaim = (doubtId: string) => {
    void run(async () => {
      await api(`/doubts/${doubtId}/claim`, actor, 'POST');
    }, 'Doubt claimed successfully! Session is now accepted.');
  };

  return (
    <div className="columns">
      {/* Ask for help form */}
      <section className="doubt-form-section">
        <h2>Ask for Peer Help</h2>
        <p className="subtext">
          Available balance: <strong>★ {pointsAvailable} points</strong>
        </p>
        <form onSubmit={handlePostDoubt}>
          <label>
            Title
            <input name="title" required minLength={3} maxLength={150} placeholder="What do you need help with?" />
          </label>
          <label>
            Description
            <textarea
              name="description"
              required
              minLength={5}
              maxLength={3000}
              placeholder="Explain what you tried and where you are stuck..."
              rows={4}
            />
          </label>
          <label>
            Domain
            <select
              value={domain}
              onChange={(e) => {
                setDomain(e.target.value);
                setTags([domains[e.target.value]?.[0] || '']);
              }}
            >
              {Object.keys(domains).map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>

          <div className="tags-label">Relevant skill tags:</div>
          <div className="tags">
            {domains[domain]?.map((tag) => (
              <label key={tag} className="check">
                <input
                  type="checkbox"
                  checked={tags.includes(tag)}
                  onChange={(e) =>
                    setTags(e.target.checked ? [...tags, tag] : tags.filter((t) => t !== tag))
                  }
                />
                {tag}
              </label>
            ))}
          </div>

          <label>
            Urgency
            <select name="urgency" defaultValue="Normal">
              <option>Normal</option>
              <option>Urgent</option>
              <option>Flexible</option>
            </select>
          </label>

          <label>
            Optional virtual reputation bounty (points)
            <input
              name="bounty"
              type="number"
              min={0}
              max={pointsAvailable}
              value={bounty}
              onChange={(e) => setBounty(Number(e.target.value))}
            />
            <small>Points are reserved upon posting and awarded only upon confirmed resolution.</small>
          </label>

          <label>
            Earliest start (optional, IST)
            <input name="start" type="datetime-local" />
          </label>
          <label>
            Deadline / window end (optional, IST)
            <input name="deadline" type="datetime-local" />
          </label>
          <button className="primary" disabled={!tags.length} type="submit">
            Post Doubt
          </button>
        </form>
      </section>

      {/* Doubt board list & filters */}
      <section className="doubt-board-section">
        <h2>Doubt & Bounty Board</h2>
        <div className="filters">
          <label>
            Search
            <input
              value={filters.search}
              placeholder="Search doubts..."
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </label>
          <label>
            Domain
            <select value={filters.domain} onChange={(e) => setFilters({ ...filters, domain: e.target.value })}>
              <option value="">All Domains</option>
              {Object.keys(domains).map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <label>
            Urgency
            <select value={filters.urgency} onChange={(e) => setFilters({ ...filters, urgency: e.target.value })}>
              <option value="">All Urgencies</option>
              <option>Urgent</option>
              <option>Normal</option>
              <option>Flexible</option>
            </select>
          </label>
          <label>
            Status
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All Statuses</option>
              <option>OPEN</option>
              <option>MATCHED</option>
              <option>IN_SESSION</option>
              <option>AWAITING_CONFIRMATION</option>
              <option>RESOLVED</option>
              <option>UNMATCHED</option>
              <option>CANCELLED</option>
            </select>
          </label>
          <label>
            Sort by
            <select value={filters.sortBy} onChange={(e) => setFilters({ ...filters, sortBy: e.target.value })}>
              <option value="newest">Newest First</option>
              <option value="bounty">Highest Bounty First</option>
              <option value="urgency">Most Urgent First</option>
            </select>
          </label>
        </div>

        {error && <p role="alert" className="error">{error}</p>}
        {loading && <p>Loading doubts…</p>}
        {!loading && !items.length && <p>No doubts match these filters.</p>}

        <div className="doubt-cards">
          {items.map((d) => {
            const isOwner = d.requester_id === actor;
            const canClaim =
              !isOwner &&
              (d.status === 'OPEN' || d.status === 'UNMATCHED') &&
              currentStudent?.mentoring;

            return (
              <article key={d.id} className="doubt-card">
                <div className="doubt-header">
                  <span className={`badge status-${d.status.toLowerCase()}`}>
                    {d.status === 'UNMATCHED' ? 'Waiting / Unmatched' : d.status}
                  </span>
                  {d.bounty > 0 && <span className="badge bounty">★ {d.bounty} pts bounty</span>}
                  <span className={`badge urgency-${d.urgency.toLowerCase()}`}>{d.urgency}</span>
                </div>

                <h3>{d.title}</h3>
                <p className="doubt-desc">{d.description}</p>
                <p className="doubt-tags">
                  <strong>{d.domain}:</strong> {d.skills.join(', ')}
                </p>
                <div className="doubt-footer">
                  <small>
                    Posted by {students.find((s) => s.id === d.requester_id)?.name || d.requester_id} · {time(d.created_at)}
                  </small>
                  {d.deadline && <small> · Deadline: {time(d.deadline)}</small>}
                </div>

                <div className="card-actions">
                  {canClaim && (
                    <button className="primary claim-btn" onClick={() => handleClaim(d.id)}>
                      Claim this Doubt
                    </button>
                  )}

                  {isOwner && (d.status === 'OPEN' || d.status === 'UNMATCHED') && (
                    <>
                      <button onClick={() => setEditingDoubt(d)}>Edit Doubt</button>
                      <button
                        className="danger"
                        onClick={() =>
                          run(() => api(`/doubts/${d.id}/cancel`, actor, 'POST'), 'Request cancelled and points refunded')
                        }
                      >
                        Cancel Request
                      </button>
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>

        {/* Edit Doubt Modal / Inline form */}
        {editingDoubt && (
          <div className="modal-overlay">
            <div className="modal-card">
              <h3>Edit Doubt: {editingDoubt.title}</h3>
              <form onSubmit={handleEditDoubt}>
                <label>
                  Title
                  <input name="title" defaultValue={editingDoubt.title} required minLength={3} maxLength={150} />
                </label>
                <label>
                  Description
                  <textarea name="description" defaultValue={editingDoubt.description} required minLength={5} rows={3} />
                </label>
                <label>
                  Urgency
                  <select name="urgency" defaultValue={editingDoubt.urgency}>
                    <option>Normal</option>
                    <option>Urgent</option>
                    <option>Flexible</option>
                  </select>
                </label>
                <label>
                  Bounty (Points)
                  <input
                    name="bounty"
                    type="number"
                    min={0}
                    max={pointsAvailable + (editingDoubt.bounty || 0)}
                    defaultValue={editingDoubt.bounty || 0}
                  />
                </label>
                <div className="modal-actions">
                  <button type="submit" className="primary">Save Changes</button>
                  <button type="button" onClick={() => setEditingDoubt(null)}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
