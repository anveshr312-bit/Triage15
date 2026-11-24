import os
import tempfile
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parents[1] / '.test-data'
TEST_ROOT.mkdir(exist_ok=True)
TEST_DIR = tempfile.TemporaryDirectory(prefix='triage15-tests-', dir=TEST_ROOT, ignore_cleanup_errors=True)
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(TEST_DIR.name) / 'test.db').replace('\\','/')

import pytest
from fastapi.testclient import TestClient
from app.database import engine, Base, transaction
from app.main import app
from app import models as m
from app.seed import seed

@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    with transaction() as db:
        # Delete in dependency order while retaining the schema and partial indexes.
        db.query(m.DoubtRequest).update({m.DoubtRequest.assigned_session_id:None})
        for table in [m.AssessmentResponse,m.SessionFeedback,m.Session,m.DoubtSkill,m.DoubtRequest,
                      m.AssessmentAttempt,m.AssessmentQuestion,m.StudentSkill,m.AvailabilityWindow,
                      m.Student,m.DispatchRun,m.BenchmarkRun]:
            db.query(table).delete()
        seed(db)
    with TestClient(app) as c:
        yield c

def headers(id='student-08'):
    return {'X-Demo-Student-ID':id}

@pytest.fixture
def clean(client):
    with transaction() as db:
        db.query(m.DoubtRequest).update({m.DoubtRequest.assigned_session_id:None})
        for table in [m.SessionFeedback,m.Session,m.DoubtSkill,m.DoubtRequest]:
            db.query(table).delete()
    return client

@pytest.fixture
def offered(clean):
    response=clean.post('/api/doubts',headers=headers(),json={
        'title':'Python loop help','description':'Why does my loop skip values?',
        'domain':'Python','skills':['python'],'urgency':'Urgent'})
    assert response.status_code==201,response.text
    doubt=response.json()
    run=clean.post('/api/dispatch/run',headers=headers()).json()
    session=run['result']['assignments'][0]
    return clean,doubt,session
