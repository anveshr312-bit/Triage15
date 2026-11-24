import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./triage15.db')
OFFER_TTL_SECONDS = int(os.getenv('OFFER_TTL_SECONDS', '300'))
URGENCY = {'Urgent': 1.25, 'Normal': 1.0, 'Flexible': 0.85}
SLOT = 900
DOMAINS = {
    'Python': ['python', 'loops', 'pandas', 'debugging'],
    'JavaScript': ['javascript', 'react', 'async', 'debugging'],
    'SQL': ['sql', 'joins', 'aggregation', 'schema'],
    'CAD': ['cad', 'sketching', 'constraints'],
    'Design': ['design', 'typography', 'layout'],
    'Mathematics': ['algebra', 'calculus', 'probability'],
}

# Environment and deployment settings
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
ALLOW_DATABASE_RESET = os.getenv(
    'ALLOW_DATABASE_RESET',
    'false' if ENVIRONMENT.lower() == 'production' else 'true'
).lower() in ('1', 'true', 'yes')

CORS_ORIGINS_RAW = os.getenv(
    'CORS_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000'
)
ALLOWED_ORIGINS = [orig.strip() for orig in CORS_ORIGINS_RAW.split(',') if orig.strip()]

FRONTEND_DIST_DIR = os.getenv(
    'FRONTEND_DIST_DIR',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/dist'))
)

def ensure_database_directory(url: str):
    """Ensure the target directory for a SQLite database exists and is writable."""
    if url.startswith('sqlite:///'):
        db_path = url[len('sqlite:///'):]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

