import os
import shutil
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config import (
    ALLOWED_ORIGINS,
    ALLOW_DATABASE_RESET,
    FRONTEND_DIST_DIR,
    ensure_database_directory,
)
from app.seed import seed, initialize

client = TestClient(app)

def test_health_check_endpoint():
    res = client.get('/api/health')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'ok'
    assert 'demonstration prototype' in data['mode']
    assert 'X-Demo-Student-ID' in data['auth_notice']
    assert data['database'] == 'connected'

def test_cors_configuration():
    assert len(ALLOWED_ORIGINS) >= 1
    # Check that origins are specific and not wildcard '*'
    assert '*' not in ALLOWED_ORIGINS

def test_ensure_database_directory(tmp_path):
    target_dir = tmp_path / "deep" / "nested" / "dir"
    db_file = target_dir / "test.db"
    db_url = f"sqlite:///{db_file}"
    
    assert not target_dir.exists()
    ensure_database_directory(db_url)
    assert target_dir.exists()
    assert target_dir.is_dir()

def test_unhandled_api_routes_return_404_not_spa_html():
    res = client.get('/api/non-existent-endpoint')
    assert res.status_code == 404
    data = res.json()
    assert 'detail' in data
    # Ensure it did NOT return HTML
    assert 'text/html' not in res.headers.get('content-type', '')

def test_spa_serving_when_frontend_dist_present():
    if not os.path.isdir(FRONTEND_DIST_DIR):
        pytest.skip("frontend/dist not yet built; skipping SPA dist check")
    
    # Root route should return index.html
    root_res = client.get('/')
    assert root_res.status_code == 200
    assert 'text/html' in root_res.headers.get('content-type', '')
    assert '<!doctype html>' in root_res.text.lower() or '<html' in root_res.text.lower()
    
    # Unknown client-side route should return index.html for SPA routing
    spa_res = client.get('/app/doubts/explore')
    assert spa_res.status_code == 200
    assert 'text/html' in spa_res.headers.get('content-type', '')

def test_database_reset_protection():
    import subprocess
    import sys

    # Running app.seed with --reset when ALLOW_DATABASE_RESET=false must fail
    env = os.environ.copy()
    env['ALLOW_DATABASE_RESET'] = 'false'
    env['PYTHONPATH'] = 'backend'

    proc = subprocess.run(
        [sys.executable, '-m', 'app.seed', '--reset'],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True
    )
    assert proc.returncode != 0
    assert "Database reset is disabled" in proc.stderr
