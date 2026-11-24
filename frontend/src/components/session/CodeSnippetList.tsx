import { useState } from 'react';
import { SessionCodeSnippet } from '../../api';
import { CodeSnippetCard } from './CodeSnippetCard';
import { CodeSnippetEditor } from './CodeSnippetEditor';

export function CodeSnippetList({
  sessionId,
  actor,
  snippets,
  onSnippetAdded,
  onOpenDiff
}: {
  sessionId: string;
  actor: string;
  snippets: SessionCodeSnippet[];
  onSnippetAdded: (snip: SessionCodeSnippet) => void;
  onOpenDiff: (origId: string, propId: string) => void;
}) {
  const [showEditor, setShowEditor] = useState(false);
  const [filterType, setFilterType] = useState<string>('ALL');

  const filtered = snippets.filter((s) => {
    if (filterType === 'ALL') return true;
    return s.snippet_type === filterType;
  });

  return (
    <div className="code-snippet-list" style={{ marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>💻</span>
          <strong style={{ fontSize: '1rem', color: '#0f172a' }}>Code Snippets ({snippets.length})</strong>
          <div style={{ display: 'flex', gap: '4px', marginLeft: '12px' }}>
            {['ALL', 'ORIGINAL', 'PROPOSED_FIX', 'EXAMPLE'].map((t) => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                style={{
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  background: filterType === t ? '#0f172a' : '#ffffff',
                  color: filterType === t ? '#ffffff' : '#475569',
                  cursor: 'pointer'
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {!showEditor && (
          <button
            className="primary"
            style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            onClick={() => setShowEditor(true)}
          >
            + Share Code Snippet
          </button>
        )}
      </div>

      {showEditor && (
        <CodeSnippetEditor
          sessionId={sessionId}
          actor={actor}
          existingSnippets={snippets}
          onSnippetCreated={(snip) => {
            onSnippetAdded(snip);
            setShowEditor(false);
          }}
          onCancel={() => setShowEditor(false)}
        />
      )}

      {filtered.length === 0 ? (
        <div style={{ background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '8px', padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
          No code snippets in this session yet. Requesters can paste problematic code, and mentors can share proposed solutions or code examples.
        </div>
      ) : (
        <div>
          {filtered.map((snippet) => (
            <CodeSnippetCard
              key={snippet.id}
              snippet={snippet}
              onCompareWith={
                snippets.length > 1
                  ? (selected) => {
                      // If selected is a proposed fix with a parent, auto-compare with parent
                      if (selected.parent_snippet_id) {
                        onOpenDiff(selected.parent_snippet_id, selected.id);
                      } else {
                        // Otherwise find first other snippet
                        const other = snippets.find((s) => s.id !== selected.id);
                        if (other) {
                          onOpenDiff(other.id, selected.id);
                        }
                      }
                    }
                  : undefined
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
