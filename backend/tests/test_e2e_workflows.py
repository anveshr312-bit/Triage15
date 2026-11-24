"""Complete End-to-End Workflow Verification Suite (P2.2).
Tests the exact sequences performed by students and mentors in the frontend interface.
"""
from concurrent.futures import ThreadPoolExecutor
import pytest
from conftest import headers

def test_complete_peer_help_workflow_with_bounty_and_messaging(clean):
    # 1. Profile selection & initial balance check
    seeker_id = 'student-08'
    seeker_headers = headers(seeker_id)
    seeker = clean.get(f'/api/students/{seeker_id}').json()
    assert seeker['points_balance'] == 150

    # 2. Seeker creates technical doubt with 40-point virtual bounty
    doubt_res = clean.post(
        '/api/doubts',
        headers=seeker_headers,
        json={
            'title': 'Python: Recursion base case debugging',
            'description': 'My binary search tree DFS is causing RecursionError. Need a 15-minute pairing session.',
            'domain': 'Python',
            'skills': ['python', 'debugging'],
            'urgency': 'Urgent',
            'bounty': 40
        }
    )
    assert doubt_res.status_code == 201
    doubt = doubt_res.json()
    assert doubt['bounty'] == 40
    assert doubt['status'] == 'OPEN'

    # Verify bounty reservation
    seeker_after_post = clean.get(f'/api/students/{seeker_id}').json()
    assert seeker_after_post['points_balance'] == 110

    # 3. Matching engine allocates optimal mentor
    run_res = clean.post('/api/dispatch/run', headers=seeker_headers)
    assert run_res.status_code == 200
    dispatch_data = run_res.json()['result']
    assert len(dispatch_data['assignments']) > 0
    assigned_session = next(s for s in dispatch_data['assignments'] if s['doubt_id'] == doubt['id'])
    
    mentor_id = assigned_session['mentor_id']
    mentor_headers = headers(mentor_id)
    assert mentor_id in ('student-01', 'student-02')

    # Verify doubt status updated to MATCHED
    doubt_matched = clean.get(f"/api/doubts/{doubt['id']}").json()
    assert doubt_matched['status'] == 'MATCHED'
    assert doubt_matched['assigned_session_id'] == assigned_session['id']

    # 4. Mentor receives offer, inspects explanation, and accepts
    session_view = clean.get(f"/api/sessions/{assigned_session['id']}", headers=mentor_headers).json()
    assert session_view['state'] == 'OFFERED'
    assert session_view['bounty'] == 40
    assert session_view['explanation']['suitability'] > 0

    accept_res = clean.post(f"/api/sessions/{assigned_session['id']}/accept", headers=mentor_headers)
    assert accept_res.status_code == 200
    assert accept_res.json()['state'] == 'ACCEPTED'

    # 5. Live workspace bidirectional messaging
    # Seeker sends problem description & code
    msg1 = clean.post(
        f"/api/sessions/{assigned_session['id']}/messages",
        headers=seeker_headers,
        json={'content': 'Hi mentor! Here is my recursive function:\n```python\ndef dfs(node):\n    dfs(node.left)\n```'}
    )
    assert msg1.status_code == 201
    assert msg1.json()['sender_id'] == seeker_id

    # Mentor replies with debugging insight
    msg2 = clean.post(
        f"/api/sessions/{assigned_session['id']}/messages",
        headers=mentor_headers,
        json={'content': 'You forgot `if not node: return`. Let us start the session to test it!'}
    )
    assert msg2.status_code == 201
    assert msg2.json()['sender_id'] == mentor_id

    # 6. Mentor starts the 15-minute session
    start_res = clean.post(f"/api/sessions/{assigned_session['id']}/start", headers=mentor_headers)
    assert start_res.status_code == 200
    active_session = start_res.json()
    assert active_session['state'] == 'ACTIVE'
    assert active_session['actual_started_at'] is not None

    # Verify authoritative countdown timer fields present
    assert active_session['active_seconds_remaining'] is not None
    assert active_session['active_seconds_remaining'] > 0

    # 7. Demonstrate accelerated demo timer clock (judge evaluation feature)
    accel_res = clean.post(f"/api/sessions/{assigned_session['id']}/accelerate", headers=mentor_headers)
    assert accel_res.status_code == 200
    assert accel_res.json()['is_demo_accelerated'] is True

    # 8. Mentor completes assistance
    complete_res = clean.post(f"/api/sessions/{assigned_session['id']}/complete", headers=mentor_headers)
    assert complete_res.status_code == 200
    completed_session = complete_res.json()
    assert completed_session['state'] == 'AWAITING_CONFIRMATION'
    assert completed_session['mentor_completed'] is True

    # 9. Seeker confirms resolution, rates mentor 5/5, and settles bounty
    mentor_balance_before = clean.get(f'/api/students/{mentor_id}').json()['points_balance']

    resolve_res = clean.post(
        f"/api/sessions/{assigned_session['id']}/resolve",
        headers=seeker_headers,
        json={'resolved': True, 'rating': 5, 'notes': 'Base case fixed! Tree traversal works perfectly.'}
    )
    assert resolve_res.status_code == 200
    final_session = resolve_res.json()
    assert final_session['state'] == 'RESOLVED'
    assert final_session['resolved'] is True

    # 10. Verify bounty award to mentor
    mentor_balance_after = clean.get(f'/api/students/{mentor_id}').json()['points_balance']
    assert mentor_balance_after == mentor_balance_before + 40

    # Seeker points balance remains 110 (already deducted upon reservation)
    assert clean.get(f'/api/students/{seeker_id}').json()['points_balance'] == 110

    # Verify metrics updated
    metrics = clean.get('/api/metrics').json()
    assert metrics['resolved_sessions'] >= 1
    assert metrics['total_bounties_awarded'] >= 40

def test_decline_and_automatic_reassignment_workflow(clean):
    # Seeker posts doubt
    seeker_headers = headers('student-08')
    doubt = clean.post(
        '/api/doubts',
        headers=seeker_headers,
        json={'title': 'Python pandas groupby help', 'description': 'Aggregating columns', 'domain': 'Python', 'skills': ['python'], 'urgency': 'Normal', 'bounty': 25}
    ).json()

    # Initial dispatch matches student-01 or student-02
    run1 = clean.post('/api/dispatch/run', headers=seeker_headers).json()
    s1 = run1['result']['assignments'][0]
    first_mentor = s1['mentor_id']

    # First mentor declines offer
    decline_res = clean.post(f"/api/sessions/{s1['id']}/decline", headers=headers(first_mentor))
    assert decline_res.status_code == 200

    # Doubt returns to OPEN queue
    doubt_after_decline = clean.get(f"/api/doubts/{doubt['id']}").json()
    assert doubt_after_decline['status'] == 'OPEN'
    assert doubt_after_decline['assigned_session_id'] is None

    # Next dispatch run reassigns to an eligible alternative (e.g. student-02 if student-01 declined)
    run2 = clean.post('/api/dispatch/run', headers=seeker_headers).json()
    assert len(run2['result']['assignments']) > 0
    s2 = run2['result']['assignments'][0]
    assert s2['mentor_id'] != first_mentor
    assert s2['doubt_id'] == doubt['id']

    # Reserved bounty (25 pts) was preserved without loss or duplication
    assert clean.get('/api/students/student-08').json()['points_balance'] == 125

def test_manual_claiming_and_duplicate_prevention_workflow(clean):
    # Student-08 posts doubt
    doubt = clean.post(
        '/api/doubts',
        headers=headers('student-08'),
        json={'title': 'SQL joins question', 'description': 'Left outer join vs inner join', 'domain': 'SQL', 'skills': ['joins'], 'urgency': 'Normal', 'bounty': 15}
    ).json()

    # Student-04 is SQL mentor with availability
    claim_res = clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers('student-04'))
    assert claim_res.status_code == 200
    session = claim_res.json()
    assert session['state'] == 'ACCEPTED'
    assert session['mentor_id'] == 'student-04'

    # Another mentor attempting to claim the same doubt gets 409 Conflict
    conflict_res = clean.post(f"/api/doubts/{doubt['id']}/claim", headers=headers('student-01'))
    assert conflict_res.status_code == 409

def test_honest_unmatched_state_workflow(clean):
    # Mathematics mentor student-07 is seeded with no availability
    doubt = clean.post(
        '/api/doubts',
        headers=headers('student-08'),
        json={'title': 'Calculus derivatives doubt', 'description': 'Chain rule question', 'domain': 'Mathematics', 'skills': ['calculus'], 'urgency': 'Urgent', 'bounty': 20}
    ).json()

    run = clean.post('/api/dispatch/run', headers=headers('student-08')).json()
    unassigned = run['result']['unassigned']
    assert any(item['id'] == doubt['id'] and 'No eligible slot' in item['reason'] for item in unassigned)

    # Status remains UNMATCHED honestly
    doubt_unmatched = clean.get(f"/api/doubts/{doubt['id']}").json()
    assert doubt_unmatched['status'] == 'UNMATCHED'
