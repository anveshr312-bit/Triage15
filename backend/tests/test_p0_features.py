from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app import models as m
from app.database import transaction
from conftest import headers

PAYLOAD = {
    'title': 'Need Python help with recursion',
    'description': 'Base case is not being hit in tree traversal',
    'domain': 'Python',
    'skills': ['python'],
    'urgency': 'Normal',
    'bounty': 40
}

def test_bounty_reservation_and_insufficient_balance(clean):
    student = clean.get('/api/students/student-08').json()
    assert student['points_balance'] == 150

    # Successful reservation of 40 points
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD)
    assert res.status_code == 201
    doubt = res.json()
    assert doubt['bounty'] == 40
    
    updated_student = clean.get('/api/students/student-08').json()
    assert updated_student['points_balance'] == 110

    # Ledger check
    ledger = clean.get('/api/students/student-08/ledger').json()
    assert any(entry['transaction_type'] == 'BOUNTY_RESERVED' and entry['amount'] == -40 for entry in ledger)

    # Attempt to reserve more points than available (available 110, requesting 200)
    over_payload = PAYLOAD | {'bounty': 200}
    res_fail = clean.post('/api/doubts', headers=headers('student-08'), json=over_payload)
    assert res_fail.status_code == 422
    assert 'Insufficient' in res_fail.json()['detail']

def test_bounty_awarded_on_resolution_and_no_duplicate(clean):
    # Seeker creates doubt with 50 bounty
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD | {'bounty': 50})
    assert res.status_code == 201, res.text
    doubt = res.json()
    
    # Run dispatch to match
    run = clean.post('/api/dispatch/run', headers=headers()).json()
    assert len(run['result']['assignments']) > 0
    session = run['result']['assignments'][0]
    mentor_id = session['mentor_id']

    mentor_before = clean.get(f'/api/students/{mentor_id}').json()
    mentor_points_before = mentor_before['points_balance']

    # Transition to active and complete
    m_headers = headers(mentor_id)
    clean.post(f"/api/sessions/{session['id']}/accept", headers=m_headers)
    clean.post(f"/api/sessions/{session['id']}/start", headers=m_headers)
    clean.post(f"/api/sessions/{session['id']}/complete", headers=m_headers)

    # Requester resolves
    res_resolve = clean.post(
        f"/api/sessions/{session['id']}/resolve",
        headers=headers('student-08'),
        json={'resolved': True, 'rating': 5, 'notes': 'Great explanation!'}
    )
    assert res_resolve.status_code == 200

    mentor_after = clean.get(f'/api/students/{mentor_id}').json()
    assert mentor_after['points_balance'] == mentor_points_before + 60  # 50 bounty + 10 base platform reward

    # Verify ledger entry
    mentor_ledger = clean.get(f'/api/students/{mentor_id}/ledger').json()
    award_entry = next(e for e in mentor_ledger if e['transaction_type'] == 'BOUNTY_AWARDED')
    assert award_entry['amount'] == 50
    assert award_entry['session_id'] == session['id']

    # Repeated resolution attempt fails with 409 and does not award points twice
    res_repeat = clean.post(
        f"/api/sessions/{session['id']}/resolve",
        headers=headers('student-08'),
        json={'resolved': True, 'rating': 5, 'notes': 'Duplicate'}
    )
    assert res_repeat.status_code == 409
    assert clean.get(f'/api/students/{mentor_id}').json()['points_balance'] == mentor_points_before + 60

def test_cancellation_refunds_bounty(clean):
    # Seeker creates doubt with 30 bounty
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD | {'bounty': 30})
    assert res.status_code == 201
    doubt = res.json()
    assert clean.get('/api/students/student-08').json()['points_balance'] == 120

    # Cancel doubt
    clean.post(f"/api/doubts/{doubt['id']}/cancel", headers=headers('student-08'))
    assert clean.get('/api/students/student-08').json()['points_balance'] == 150

    ledger = clean.get('/api/students/student-08/ledger').json()
    refund_entry = next(e for e in ledger if e['transaction_type'] == 'BOUNTY_REFUNDED')
    assert refund_entry['amount'] == 30

    # Cancelling again is rejected
    assert clean.post(f"/api/doubts/{doubt['id']}/cancel", headers=headers('student-08')).status_code == 409
    assert clean.get('/api/students/student-08').json()['points_balance'] == 150

def test_unresolved_session_does_not_award_bounty_and_retains_reservation(clean):
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD | {'bounty': 35})
    assert res.status_code == 201
    doubt = res.json()

    run = clean.post('/api/dispatch/run', headers=headers()).json()
    assert len(run['result']['assignments']) > 0
    session = run['result']['assignments'][0]
    mentor_id = session['mentor_id']
    mentor_points_before = clean.get(f'/api/students/{mentor_id}').json()['points_balance']

    m_headers = headers(mentor_id)
    clean.post(f"/api/sessions/{session['id']}/accept", headers=m_headers)
    clean.post(f"/api/sessions/{session['id']}/start", headers=m_headers)
    clean.post(f"/api/sessions/{session['id']}/complete", headers=m_headers)

    # Resolved = False
    clean.post(
        f"/api/sessions/{session['id']}/resolve",
        headers=headers('student-08'),
        json={'resolved': False, 'rating': 2, 'notes': 'Did not solve'}
    )

    # Mentor gets 0 points
    assert clean.get(f'/api/students/{mentor_id}').json()['points_balance'] == mentor_points_before
    # Seeker points balance remains 115 because bounty remains reserved for the open doubt
    assert clean.get('/api/students/student-08').json()['points_balance'] == 115
    assert clean.get(f"/api/doubts/{doubt['id']}").json()['status'] == 'OPEN'

def test_messaging_workspace_permissions_and_persistence(clean):
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD)
    assert res.status_code == 201
    run = clean.post('/api/dispatch/run', headers=headers()).json()
    assert len(run['result']['assignments']) > 0
    session = run['result']['assignments'][0]
    mentor_id = session['mentor_id']

    # Accept session
    clean.post(f"/api/sessions/{session['id']}/accept", headers=headers(mentor_id))

    # Requester sends message
    msg1 = clean.post(
        f"/api/sessions/{session['id']}/messages",
        headers=headers('student-08'),
        json={'content': 'Hello mentor, here is my code snippet:\n```python\ndef solve(): pass\n```'}
    )
    assert msg1.status_code == 201
    assert msg1.json()['content'].startswith('Hello mentor')

    # Mentor replies
    msg2 = clean.post(
        f"/api/sessions/{session['id']}/messages",
        headers=headers(mentor_id),
        json={'content': 'I see the bug. Let us start the session!'}
    )
    assert msg2.status_code == 201

    # Unrelated student cannot access messages
    unrelated = clean.get(f"/api/sessions/{session['id']}/messages", headers=headers('student-11'))
    assert unrelated.status_code == 403

    # Unrelated student cannot post message
    unrelated_post = clean.post(
        f"/api/sessions/{session['id']}/messages",
        headers=headers('student-11'),
        json={'content': 'Intruder message'}
    )
    assert unrelated_post.status_code == 403

    # Both participants can retrieve conversation history
    history = clean.get(f"/api/sessions/{session['id']}/messages", headers=headers('student-08')).json()
    assert len(history) == 2
    assert history[0]['sender_id'] == 'student-08'
    assert history[1]['sender_id'] == mentor_id

    # Incremental polling with since_id
    since = clean.get(f"/api/sessions/{session['id']}/messages?since_id={history[0]['id']}", headers=headers(mentor_id)).json()
    assert len(since) == 1
    assert since[0]['id'] == history[1]['id']

    # Reject empty or excessively long message
    assert clean.post(f"/api/sessions/{session['id']}/messages", headers=headers(mentor_id), json={'content': ''}).status_code == 422
    assert clean.post(f"/api/sessions/{session['id']}/messages", headers=headers(mentor_id), json={'content': 'x' * 4001}).status_code == 422

def test_manual_claiming_workflow(clean):
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD)
    assert res.status_code == 201
    doubt = res.json()

    # Ineligible student (student-10 is not mentoring) cannot claim
    assert clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers('student-10')).status_code == 422

    # Self-claim rejected
    assert clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers('student-08')).status_code == 422

    # Eligible mentor (student-01 mentors Python and has availability) claims
    claim_res = clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers('student-01'))
    assert claim_res.status_code == 200
    session = claim_res.json()
    assert session['state'] == 'ACCEPTED'
    assert session['mentor_id'] == 'student-01'
    assert clean.get(f"/api/doubts/{doubt['id']}").json()['status'] == 'MATCHED'

    # Second claim on already matched doubt rejected
    assert clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers('student-02')).status_code == 409

def test_concurrent_manual_claims_cannot_double_book(clean):
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD)
    assert res.status_code == 201
    doubt = res.json()

    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(
            lambda mentor_id: clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers(mentor_id)),
            ['student-01', 'student-02']
        ))

    statuses = [r.status_code for r in responses]
    assert 200 in statuses
    assert 409 in statuses
    assert statuses.count(200) == 1

def test_accelerated_demo_timer_endpoint(clean):
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD)
    assert res.status_code == 201
    run = clean.post('/api/dispatch/run', headers=headers()).json()
    assert len(run['result']['assignments']) > 0
    session = run['result']['assignments'][0]
    m_headers = headers(session['mentor_id'])

    clean.post(f"/api/sessions/{session['id']}/accept", headers=m_headers)

    # Accelerate session
    accel = clean.post(f"/api/sessions/{session['id']}/accelerate", headers=m_headers)
    assert accel.status_code == 200
    data = accel.json()
    assert data['is_demo_accelerated'] is True
    assert data['state'] == 'ACTIVE'
    assert 'active_seconds_remaining' in data

def test_mentor_credibility_profile(client):
    profile = client.get('/api/mentors/student-01/profile').json()
    assert profile['id'] == 'student-01'
    assert profile['mentoring'] is True
    assert profile['completed_sessions'] == 3
    assert profile['resolved_sessions'] == 2
    assert profile['resolution_rate'] == 66.7
    assert '66.7%' in profile['resolution_history_label']
    assert profile['feedback_count'] > 0
    assert profile['average_rating'] is not None

    # Student with no history
    client.post('/api/students', json={'name': 'Novice Mentor'})
    new_id = client.get('/api/students').json()[-1]['id']
    client.put(f'/api/students/{new_id}/profile', headers=headers(new_id), json={'mentoring': True, 'skills': []})
    novice = client.get(f'/api/mentors/{new_id}/profile').json()
    assert novice['completed_sessions'] == 0
    assert novice['resolution_rate'] is None
    assert novice['resolution_history_label'] == 'No resolution history yet'

def test_doubt_editing_with_bounty_adjustment(clean):
    res = clean.post('/api/doubts', headers=headers('student-08'), json=PAYLOAD | {'bounty': 20})
    assert res.status_code == 201
    doubt = res.json()
    assert clean.get('/api/students/student-08').json()['points_balance'] == 130

    # Edit title and increase bounty to 50 (extra 30 deducted)
    edit_payload = PAYLOAD | {'title': 'Updated Title For Python Help', 'bounty': 50}
    edit_res = clean.patch(f"/api/doubts/{doubt['id']}", headers=headers('student-08'), json=edit_payload)
    assert edit_res.status_code == 200
    assert edit_res.json()['title'] == 'Updated Title For Python Help'
    assert edit_res.json()['bounty'] == 50
    assert clean.get('/api/students/student-08').json()['points_balance'] == 100

    # Unrelated student cannot edit
    assert clean.patch(f"/api/doubts/{doubt['id']}", headers=headers('student-09'), json=edit_payload).status_code == 403

def test_profile_update_strict_schema_validation(clean):
    """Test that profile update rejects extra fields like id or student_id, and succeeds with clean skill objects."""
    # Attempting to send GET serialized skills with extra fields 'id' or 'student_id' fails with 422 extra_forbidden
    forbidden_payload = {
        'mentoring': True,
        'skills': [
            {'id': 'dummy-id', 'student_id': 'student-03', 'domain': 'Python', 'tag': 'python', 'level': 4}
        ]
    }
    res_forbidden = clean.put('/api/students/student-03/profile', headers=headers('student-03'), json=forbidden_payload)
    assert res_forbidden.status_code == 422
    err_detail = res_forbidden.json()['detail']
    assert any('extra_forbidden' in str(e) for e in err_detail)

    # Clean payload with only domain, tag, level succeeds and updates skills
    clean_payload = {
        'mentoring': True,
        'skills': [
            {'domain': 'Python', 'tag': 'python', 'level': 4},
            {'domain': 'Python', 'tag': 'pandas', 'level': 4},
            {'domain': 'Python', 'tag': 'loops', 'level': 4}
        ]
    }
    res_clean = clean.put('/api/students/student-03/profile', headers=headers('student-03'), json=clean_payload)
    assert res_clean.status_code == 200
    s_obj = clean.get('/api/students/student-03').json()
    assert s_obj['mentoring'] is True
    skill_tags = [sk['tag'] for sk in s_obj['skills']]
    assert 'python' in skill_tags and 'pandas' in skill_tags and 'loops' in skill_tags
