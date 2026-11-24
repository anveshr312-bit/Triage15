import { useState } from 'react';
import { api, SessionCodeSnippet } from '../../api';

const LANGUAGES = [
  'python',
  'javascript',
  'typescript',
  'sql',
  'html',
  'css',
  'json',
  'text',
  'java',
  'c',
  'cpp',
  'bash'
];

export function CodeSnippetEditor({
  sessionId,
  actor,
  existingSnippets,
  onSnippetCreated,
  onCancel
}: {
  sessionId: string;
  actor: string;
  existingSnippets: SessionCodeSnippet[];
  onSnippetCreated: (snip: SessionCodeSnippet) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState('');
  const [filename, setFilename] = useState('');
  const [language, setLanguage] = useState('python');
  const [snippetType, setSnippetType] = useState<'ORIGINAL' | 'PROPOSED_FIX' | 'EXAMPLE' | 'ERROR_LOG' | 'OTHER'>('ORIGINAL');
  const [parentSnippetId, setParentSnippetId] = useState('');
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    setBusy(true);
    setError('');
    try {
      const created = await api<SessionCodeSnippet>(
        `/sessions/${sessionId}/snippets`,
        actor,
        'POST',
        {
          title: title.trim(),
          filename: filename.trim() || null,
          language,
          snippet_type: snippetType,
          parent_snippet_id: parentSnippetId || null,
          content
        }
      );
      onSnippetCreated(created);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: '#0f172a' }}>Share Code Snippet</h3>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px', marginBottom: '10px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Snippet Title *</label>
          <input
            type="text"
            placeholder="e.g. Broken list filter loop"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            maxLength={120}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Filename (Optional)</label>
          <input
            type="text"
            placeholder="e.g. main.py"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            maxLength={120}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '10px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Language</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{lang.toUpperCase()}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Snippet Type</label>
          <select
            value={snippetType}
            onChange={(e) => setSnippetType(e.target.value as any)}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          >
            <option value="ORIGINAL">Original Code</option>
            <option value="PROPOSED_FIX">Proposed Fix / Solution</option>
            <option value="EXAMPLE">Example / Reference</option>
            <option value="ERROR_LOG">Error Log / Stack Trace</option>
            <option value="OTHER">Other</option>
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>Linked Snippet (Optional)</label>
          <select
            value={parentSnippetId}
            onChange={(e) => setParentSnippetId(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
          >
            <option value="">None (Independent)</option>
            {existingSnippets.map((s) => (
              <option key={s.id} value={s.id}>
                Fix for: {s.title} ({s.language})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <label style={{ fontSize: '0.8rem', color: '#475569' }}>Code / Snippet Content *</label>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{content.length} / 65536 chars</span>
        </div>
        <textarea
          rows={8}
          placeholder="// Paste code here..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
          maxLength={65536}
          style={{
            width: '100%',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #cbd5e1',
            background: '#ffffff',
            lineHeight: 1.4
          }}
        />
      </div>

      <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '12px' }}>
        🔒 <em>Security Warning:</em> Code is stored as plain text and is never executed on our servers. Do not paste sensitive API keys or private secrets.
      </div>

      {error && <div style={{ color: '#b91c1c', fontSize: '0.8rem', marginBottom: '10px' }}>⚠️ {error}</div>}

      <div style={{ display: 'flex', gap: '8px' }}>
        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Posting…' : 'Share Snippet'}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
