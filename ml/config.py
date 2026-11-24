from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'ml' / 'artifacts'
REPORTS = ROOT / 'ml' / 'reports'
PROCESSED = ROOT / 'data' / 'processed'
SEED = 42
# Exact existing app skill tokens; no database vocabulary expansion.
TAG_MAPPING = {
    'python': 'python', 'python-3.x': 'python', 'pandas': 'pandas',
    'javascript': 'javascript', 'reactjs': 'react', 'react-hooks': 'react',
    'sql': 'sql', 'mysql': 'sql', 'postgresql': 'sql', 'sqlite': 'sql', 'sql-server': 'sql',
    'join': 'joins', 'sql-join': 'joins',
    'aggregate-functions': 'aggregation', 'sql-aggregation': 'aggregation',
    'async-await': 'async', 'asynchronous': 'async',
}
LABEL_DOMAINS = {'python': 'Python', 'pandas': 'Python', 'javascript': 'JavaScript',
                 'react': 'JavaScript', 'async': 'JavaScript',
                 'sql': 'SQL', 'joins': 'SQL', 'aggregation': 'SQL'}
TOKEN_PATTERN = r'(?u)(?:\b[a-zA-Z][\w]*(?:\+\+|\#)|\.net\b|\b[\w]+(?:\.[\w]+)*\b)'
ALIASES = {
    'python': ['python', 'pip', 'traceback', 'def', 'importerror', 'indentationerror'],
    'pandas': ['pandas', 'dataframe', 'pd.', 'read_csv', 'iloc', 'loc['],
    'javascript': ['javascript', 'const', 'let', 'undefined', 'npm', 'document.', 'console.log'],
    'react': ['react', 'reactjs', 'jsx', 'usestate', 'useeffect', 'react-dom'],
    'async': ['async', 'await', 'promise', 'asynchronous', 'then'],
    'sql': ['sql', 'select', 'mysql', 'postgresql', 'sqlite', 'where', 'varchar'],
    'joins': ['join', 'joins', 'inner join', 'left join', 'outer join'],
    'aggregation': ['group by', 'aggregate', 'aggregation', 'sum(', 'count(', 'having'],
}
