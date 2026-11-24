import { useState } from 'react';
import { SessionCodeSnippet, time } from '../../api';

export function CodeSnippetCard({
  snippet,
  onCompareWith
}: {
  snippet: SessionCodeSnippet;
  onCompareWith?: (snip: SessionCodeSnippet) => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard.writeText(snippet.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const typeColor = {
    ORIGINAL: '#ea580c',
    PROPOSED_FIX: '#16a34a',
    EXAMPLE: '#2563eb',
    ERROR_LOG: '#dc2626',
    OTHER: '#64748b'
  }[snippet.snippet_type] || '#64748b';

  const typeLabel = {
    ORIGINAL: 'Original Code',
    PROPOSED_FIX: 'Proposed Solution',
    EXAMPLE: 'Example',
    ERROR_LOG: 'Error Log',
    OTHER: 'Snippet'
  }[snippet.snippet_type] || snippet.snippet_type;

  const lines = snippet.content.split('\n');

  return (
    <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '8px', overflow: 'hidden', marginBottom: '12px' }}>
      <div style={{ background: '#f8fafc', padding: '10px 14px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: '4px', background: `${typeColor}15`, color: typeColor, border: `1px solid ${typeColor}40` }}>
            {typeLabel}
          </span>
          <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>{snippet.title}</strong>
          {snippet.filename && (
            <code style={{ fontSize: '0.8rem', color: '#64748b' }}>({snippet.filename})</code>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            {snippet.author_name ? `${snippet.author_name} · ` : ''}{time(snippet.created_at)}
          </span>
          <button
            onClick={handleCopy}
            className="secondary"
            style={{ fontSize: '0.75rem', padding: '3px 8px' }}
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
          {onCompareWith && (
            <button
              onClick={() => onCompareWith(snippet)}
              className="secondary"
              style={{ fontSize: '0.75rem', padding: '3px 8px', color: '#2563eb' }}
            >
              Compare
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', background: '#0f172a', color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.82rem', maxHeight: '280px', overflowY: 'auto' }}>
        <div style={{ padding: '10px 8px', background: '#090d16', color: '#475569', textAlign: 'right', userSelect: 'none', borderRight: '1px solid #1e293b' }}>
          {lines.map((_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>
        <pre style={{ margin: 0, padding: '10px 12px', flex: 1, whiteSpace: 'pre', overflowX: 'auto', lineHeight: '1.4' }}>
          {snippet.content}
        </pre>
      </div>
    </div>
  );
}
