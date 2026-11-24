"""
Tests for bounty economy policy and voluntary manual claiming.
"""

import pytest
from app import models as m, config as cfg
from app.database import SessionLocal
from sqlalchemy import select

def test_new_student_starts_with_zero_points(client):
    res = client.post('/api/students', json={'name': 'Fresh Student'})
    assert res.status_code == 201
    data = res.json()
    assert data['points_balance'] == 0

    with SessionLocal() as db:
        student = db.get(m.Student, data['id'])
        assert student.points_balance == 0
        grants = db.scalars(select(m.PointLedger).where(m.PointLedger.student_id == student.id, m.PointLedger.transaction_type == 'INITIAL_GRANT')).all()
        assert len(grants) == 0

def test_zero_bounty_doubt_creation_succeeds_with_zero_balance(client):
    # Register student with 0 points
    s_res = client.post('/api/students', json={'name': 'Broke Student'})
    s_id = s_res.json()['id']

    # Post zero bounty doubt
    d_res = client.post('/api/doubts', headers={'X-Demo-Student-ID': s_id}, json={
        'title': 'Need help with loops in Python',
        'description': 'How do while loops terminate?',
        'domain': 'Python',
        'skills': ['loops', 'python'],
        'urgency': 'Normal',
        'bounty': 0
    })
    assert d_res.status_code in (200, 201)
    doubt_data = d_res.json()
    assert doubt_data['bounty'] == 0
    assert doubt_data['status'] == 'OPEN'

def test_positive_bounty_with_zero_balance_fails(client):
    s_res = client.post('/api/students', json={'name': 'Penniless Requester'})
    s_id = s_res.json()['id']

    d_res = client.post('/api/doubts', headers={'X-Demo-Student-ID': s_id}, json={
        'title': 'Need urgent help',
        'description': 'Cannot pay bounty with 0 points',
        'domain': 'Python',
        'skills': ['python'],
        'urgency': 'Urgent',
        'bounty': 20
    })
    assert d_res.status_code == 422
    assert 'Insufficient' in d_res.json()['detail']

def test_zero_bounty_resolution_awards_platform_base_reward(client):
    # Setup mentor with 0 points and requester with 0 points
    m_res = client.post('/api/students', json={'name': 'Helpful Mentor'})
    mentor_id = m_res.json()['id']

    with SessionLocal() as db:
        mentor = db.get(m.Student, mentor_id)
        mentor.mentoring = True
        mentor.skills.append(m.StudentSkill(student_id=mentor_id, domain='Python', tag='python', level=4))
        mentor.availability.append(m.AvailabilityWindow(student_id=mentor_id, start=m.now(), end=m.now() + 86400))
        db.commit()

    r_res = client.post('/api/students', json={'name': 'Grateful Requester'})
    req_id = r_res.json()['id']

    # Create 0-bounty doubt
    d_res = client.post('/api/doubts', headers={'X-Demo-Student-ID': req_id}, json={
        'title': 'Zero bounty Python doubt',
        'description': 'Simple syntax question',
        'domain': 'Python',
        'skills': ['python'],
        'urgency': 'Normal',
        'bounty': 0
    })
    doubt_id = d_res.json()['id']

    # Mentor claims doubt
    c_res = client.post(f'/api/doubts/{doubt_id}/claim', headers={'X-Demo-Student-ID': mentor_id})
    assert c_res.status_code == 200
    session_id = c_res.json()['id']

    # Start and complete session
    client.post(f'/api/sessions/{session_id}/start', headers={'X-Demo-Student-ID': mentor_id})
    client.post(f'/api/sessions/{session_id}/complete', headers={'X-Demo-Student-ID': mentor_id})

    # Requester resolves
    res_call = client.post(f'/api/sessions/{session_id}/resolve', headers={'X-Demo-Student-ID': req_id}, json={
        'resolved': True,
        'rating': 5,
        'notes': 'Great help!'
    })
    assert res_call.status_code == 200

    # Mentor earned exactly 10 base points!
    with SessionLocal() as db:
        mentor_updated = db.get(m.Student, mentor_id)
        assert mentor_updated.points_balance == 10

        # Verify ledger entry
        base_ledger = db.scalar(select(m.PointLedger).where(
            m.PointLedger.student_id == mentor_id,
            m.PointLedger.transaction_type == 'BASE_REWARD'
        ))
        assert base_ledger is not None
        assert base_ledger.amount == 10

    # Repeated resolve attempt does not double reward
    res_call2 = client.post(f'/api/sessions/{session_id}/resolve', headers={'X-Demo-Student-ID': req_id}, json={
        'resolved': True,
        'rating': 5,
        'notes': 'Duplicate attempt'
    })
    assert res_call2.status_code in (400, 409)
    with SessionLocal() as db:
        assert db.get(m.Student, mentor_id).points_balance == 10

def test_manual_claiming_ineligible_reasons(client):
    # Requester
    r_res = client.post('/api/students', json={'name': 'Doubt Poster'})
    req_id = r_res.json()['id']

    d_res = client.post('/api/doubts', headers={'X-Demo-Student-ID': req_id}, json={
        'title': 'SQL Join Question',
        'description': 'How does inner join work?',
        'domain': 'SQL',
        'skills': ['joins', 'sql'],
        'urgency': 'Normal',
        'bounty': 0
    })
    doubt_id = d_res.json()['id']

    # 1. Requester cannot claim own doubt
    own_res = client.post(f'/api/doubts/{doubt_id}/claim', headers={'X-Demo-Student-ID': req_id})
    assert own_res.status_code in (422, 409)

    # 2. Mentor not opted into mentoring
    m1_res = client.post('/api/students', json={'name': 'Non Mentor'})
    m1_id = m1_res.json()['id']
    m1_call = client.post(f'/api/doubts/{doubt_id}/claim', headers={'X-Demo-Student-ID': m1_id})
    assert m1_call.status_code == 422
    assert 'not opted into mentoring' in m1_call.json()['detail']

    # 3. Mentor with wrong skill domain
    m2_res = client.post('/api/students', json={'name': 'Python Only Mentor'})
    m2_id = m2_res.json()['id']
    with SessionLocal() as db:
        m2 = db.get(m.Student, m2_id)
        m2.mentoring = True
        m2.skills.append(m.StudentSkill(student_id=m2_id, domain='Python', tag='python', level=5))
        m2.availability.append(m.AvailabilityWindow(student_id=m2_id, start=m.now(), end=m.now() + 86400))
        db.commit()

    m2_call = client.post(f'/api/doubts/{doubt_id}/claim', headers={'X-Demo-Student-ID': m2_id})
    assert m2_call.status_code == 422
    assert 'matching skills' in m2_call.json()['detail']
