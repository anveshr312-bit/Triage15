import os
import sys

def load_dotenv():
    """Load variables from .env file into os.environ if not already present."""
    for candidate in [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')),
        os.path.abspath('.env')
    ]:
        if os.path.isfile(candidate):
            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k, v = k.strip(), v.strip()
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

load_dotenv()

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

# Supabase Authentication Settings
SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY', '')
SUPABASE_JWT_ALGORITHM = os.getenv('SUPABASE_JWT_ALGORITHM', 'ES256')
SUPABASE_JWT_AUDIENCE = os.getenv('SUPABASE_JWT_AUDIENCE', 'authenticated')

def is_demo_auth_allowed() -> bool:
    """Production fails closed. Demo header is permitted only in explicit test environments."""
    if os.getenv('ENVIRONMENT', '').lower() == 'production':
        return False
    if os.getenv('ALLOW_DEMO_AUTH', '').lower() in ('false', '0', 'no'):
        return False
    return (
        os.getenv('ALLOW_DEMO_AUTH', '').lower() in ('1', 'true', 'yes')
        or os.getenv('ENVIRONMENT', '').lower() == 'test'
        or 'pytest' in sys.modules
    )

ALLOW_DEMO_AUTH = is_demo_auth_allowed()

def ensure_database_directory(url: str):
    """Ensure the target directory for a SQLite database exists and is writable."""
    if url.startswith('sqlite:///'):
        db_path = url[len('sqlite:///'):]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

