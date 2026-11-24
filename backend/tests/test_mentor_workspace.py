import pytest
from starlette.testclient import TestClient
from app.main import app
from app.database import transaction
from app import models as m

client = TestClient(app)

def make_accepted_session(db, requester_id='student-08', mentor_id='student-01'):
    # Clean active sessions/doubts for these students if needed
    start = ((m.now() + 900 - 1) // 900) * 900 + 900
    doubt = m.DoubtRequest(
        title='Help with Python list comprehensions',
        description='Need assistance refactoring loop into list comprehension',
        domain='Python',
        urgency='Normal',
        bounty=40,
        requester_id=requester_id,
        created_at=m.now()
    )
    db.add(doubt)
    db.flush()
    db.add(m.DoubtSkill(doubt_id=doubt.id, tag='python'))
    
    # Reserve bounty
    req = db.get(m.Student, requester_id)
    req.points_balance -= 40
    db.add(m.PointLedger(
        student_id=req.id,
        amount=-40,
        transaction_type='BOUNTY_RESERVED',
        doubt_id=doubt.id,
        reference_id=f'reserve:{doubt.id}',
        balance_after=req.points_balance,
        notes='Reserved 40 points for doubt'
    ))

    session = m.Session(
        doubt_id=doubt.id,
        mentor_id=mentor_id,
        start=start,
        end=start + 900,
        state='ACCEPTED',
        offer_expires_at=start - 100,
        accepted_at=m.now(),
        actual_started_at=m.now()
    )
    db.add(session)
    db.flush()
    doubt.status = 'IN_SESSION'
    doubt.assigned_session_id = session.id
    db.flush()
    return session.id, doubt.id, requester_id, mentor_id

# ==========================================
# 1. Google Meet Integration Tests
# ==========================================

def test_google_meet_attachment_and_validation(clean):
    with transaction() as db:
        sess_id, doubt_id, req_id, mentor_id = make_accepted_session(db)

    # 1. Assigned mentor attaches valid meeting URL
    res = client.put(
        f'/api/sessions/{sess_id}/meeting',
        headers={'X-Demo-Student-ID': mentor_id},
        json={'meeting_url': 'https://meet.google.com/abc-defg-hij'}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data['meeting_url'] == 'https://meet.google.com/abc-defg-hij'
    assert data['attached_by_id'] == mentor_id

    # 2. Requester can retrieve the meeting URL
    res_req = client.get(
        f'/api/sessions/{sess_id}/meeting',
        headers={'X-Demo-Student-ID': req_id}
    )
    assert res_req.status_code == 200
    assert res_req.json()['meeting_url'] == 'https://meet.google.com/abc-defg-hij'

    # 3. Unrelated student gets 403 Forbidden
    res_unauth = client.get(
        f'/api/sessions/{sess_id}/meeting',
        headers={'X-Demo-Student-ID': 'student-03'}
    )
    assert res_unauth.status_code == 403

    # 4. Requester cannot replace or delete meeting link (only mentor can)
    res_fail_replace = client.put(
        f'/api/sessions/{sess_id}/meeting',
        headers={'X-Demo-Student-ID': req_id},
        json={'meeting_url': 'https://meet.google.com/xyz-uvwx-rst'}
    )
    assert res_fail_replace.status_code == 403

    res_fail_del = client.delete(
        f'/api/sessions/{sess_id}/meeting',
        headers={'X-Demo-Student-ID': req_id}
    )
    assert res_fail_del.status_code == 403

    # 5. Invalid and lookalike URLs rejected
    invalid_urls = [
        'http://meet.google.com/abc-defg-hij',             # non-https
        'https://google.com/meet/abc-defg-hij',            # wrong path/domain
        'https://meet.google.com.evil.com/abc-defg-hij',   # lookalike domain
        'https://user:pass@meet.google.com/abc-defg-hij',  # credentials
        'javascript:alert(1)',                             # script
        'https://meet.google.com/invalid_pattern',         # invalid code pattern
        'https://meet.google.com/abc-defg-hij?redirect=evil.com', # extra query
    ]
    for bad_url in invalid_urls:
        bad_res = client.put(
            f'/api/sessions/{sess_id}/meeting',
            headers={'X-Demo-Student-ID': mentor_id},
            json={'meeting_url': bad_url}
        )
        assert bad_res.status_code == 422, f'Expected 422 for bad URL: {bad_url}'

    # 6. Mentor can delete meeting URL
    res_del = client.delete(
        f'/api/sessions/{sess_id}/meeting',
        headers={'X-Demo-Student-ID': mentor_id}
    )
    assert res_del.status_code == 200
    assert res_del.json()['detail'] == 'Meeting link removed'

    # Retrieval now gives 404
    assert client.get(f'/api/sessions/{sess_id}/meeting', headers={'X-Demo-Student-ID': mentor_id}).status_code == 404


# ==========================================
# 2. Code Snippet Exchange Tests
# ==========================================

def test_code_snippet_exchange_and_permissions(clean):
    with transaction() as db:
        sess_id, doubt_id, req_id, mentor_id = make_accepted_session(db)

    # 1. Requester posts original code
    orig_code = 'def filter_evens(nums):\n    res = []\n    for n in nums:\n        if n % 2 == 0:\n            res.append(n)\n    return res'
    res_orig = client.post(
        f'/api/sessions/{sess_id}/snippets',
        headers={'X-Demo-Student-ID': req_id},
        json={
            'title': 'Original loop',
            'filename': 'evens.py',
            'language': 'python',
            'content': orig_code,
            'snippet_type': 'ORIGINAL'
        }
    )
    print('DEBUG SNIPPET RESPONSE:', res_orig.status_code, res_orig.text)
    assert res_orig.status_code == 201
    orig_data = res_orig.json()
    assert orig_data['title'] == 'Original loop'
    orig_id = orig_data['id']

    # 2. Mentor posts proposed fix linked to original
    fix_code = 'def filter_evens(nums):\n    return [n for n in nums if n % 2 == 0]'
    res_fix = client.post(
        f'/api/sessions/{sess_id}/snippets',
        headers={'X-Demo-Student-ID': mentor_id},
        json={
            'title': 'Comprehension fix',
            'filename': 'evens.py',
            'language': 'python',
            'content': fix_code,
            'snippet_type': 'PROPOSED_FIX',
            'parent_snippet_id': orig_id
        }
    )
    assert res_fix.status_code == 201
    fix_data = res_fix.json()
    assert fix_data['parent_snippet_id'] == orig_id
    fix_id = fix_data['id']

    # 3. Both participants can list snippets
    list_req = client.get(f'/api/sessions/{sess_id}/snippets', headers={'X-Demo-Student-ID': req_id})
    assert list_req.status_code == 200
    assert len(list_req.json()) == 2

    # 4. Unrelated student gets 403 Forbidden
    list_unauth = client.get(f'/api/sessions/{sess_id}/snippets', headers={'X-Demo-Student-ID': 'student-03'})
    assert list_unauth.status_code == 403

    # 5. Cross-session parent snippet rejection
    with transaction() as db:
        sess2_id, _, _, _ = make_accepted_session(db, requester_id='student-09', mentor_id='student-02')

    res_cross = client.post(
        f'/api/sessions/{sess2_id}/snippets',
        headers={'X-Demo-Student-ID': 'student-02'},
        json={
            'title': 'Invalid cross reference',
            'content': 'x = 1',
            'snippet_type': 'PROPOSED_FIX',
            'parent_snippet_id': orig_id  # belongs to sess_id, not sess2_id!
        }
    )
    assert res_cross.status_code == 400
    assert 'same session' in res_cross.text

    # 6. HTML and scripts remain inert text
    script_content = '<script>alert("xss")</script>'
    res_xss = client.post(
        f'/api/sessions/{sess_id}/snippets',
        headers={'X-Demo-Student-ID': req_id},
        json={
            'title': 'Script snippet',
            'language': 'html',
            'content': script_content,
            'snippet_type': 'EXAMPLE'
        }
    )
    assert res_xss.status_code == 201
    assert res_xss.json()['content'] == script_content  # strictly preserved as string


# ==========================================
# 3. Before-and-After Code Comparison Tests
# ==========================================

def test_code_comparison_diff(clean):
    with transaction() as db:
        sess_id, doubt_id, req_id, mentor_id = make_accepted_session(db)

    s1_res = client.post(
        f'/api/sessions/{sess_id}/snippets',
        headers={'X-Demo-Student-ID': req_id},
        json={
            'title': 'Version 1',
            'content': 'line 1\nline 2\nline 3',
            'snippet_type': 'ORIGINAL'
        }
    )
    s2_res = client.post(
        f'/api/sessions/{sess_id}/snippets',
        headers={'X-Demo-Student-ID': mentor_id},
        json={
            'title': 'Version 2',
            'content': 'line 1\nline 2 modified\nline 3\nline 4 added',
            'snippet_type': 'PROPOSED_FIX'
        }
    )
    s1_id = s1_res.json()['id']
    s2_id = s2_res.json()['id']

    # Compute diff
    diff_res = client.get(
        f'/api/sessions/{sess_id}/snippets-diff?original_id={s1_id}&proposed_id={s2_id}',
        headers={'X-Demo-Student-ID': req_id}
    )
    assert diff_res.status_code == 200
    diff = diff_res.json()
    assert diff['added_count'] >= 1
    assert diff['removed_count'] >= 1
    assert any(line['type'] == 'added' for line in diff['lines'])
    assert any(line['type'] == 'removed' for line in diff['lines'])

    # Identical snippet comparison produces 0 added, 0 removed
    same_res = client.get(
        f'/api/sessions/{sess_id}/snippets-diff?original_id={s1_id}&proposed_id={s1_id}',
        headers={'X-Demo-Student-ID': req_id}
    )
    assert same_res.status_code == 200
    assert same_res.json()['added_count'] == 0
    assert same_res.json()['removed_count'] == 0


# ==========================================
# 4. Structured Resolution Records Tests
# ==========================================

def test_structured_resolution_and_bounty_settlement(clean):
    with transaction() as db:
        sess_id, doubt_id, req_id, mentor_id = make_accepted_session(db)
        sess = db.get(m.Session, sess_id)
        sess.state = 'ACTIVE'

    # 1. Mentor drafts resolution record
    res_draft = client.put(
        f'/api/sessions/{sess_id}/resolution',
        headers={'X-Demo-Student-ID': mentor_id},
        json={
            'root_cause': 'Using a standard for loop to filter items is verbose and less pythonic.',
            'solution_explanation': 'Refactored to list comprehension with condition filter.',
            'follow_up_steps': 'Practice with dictionary comprehensions next.',
            'reference_urls': ['https://docs.python.org/3/tutorial/datastructures.html']
        }
    )
    assert res_draft.status_code == 200
    data = res_draft.json()
    assert data['root_cause'].startswith('Using a standard')

    # 2. Requester cannot modify the resolution draft (403)
    res_unauth_mod = client.put(
        f'/api/sessions/{sess_id}/resolution',
        headers={'X-Demo-Student-ID': req_id},
        json={
            'root_cause': 'Hacked',
            'solution_explanation': 'Hacked'
        }
    )
    assert res_unauth_mod.status_code == 403

    # 3. Mentor submits resolution -> session moves to AWAITING_CONFIRMATION
    res_submit = client.post(
        f'/api/sessions/{sess_id}/resolution/submit',
        headers={'X-Demo-Student-ID': mentor_id}
    )
    assert res_submit.status_code == 200

    sess_check = client.get(f'/api/sessions/{sess_id}', headers={'X-Demo-Student-ID': req_id}).json()
    assert sess_check['state'] == 'AWAITING_CONFIRMATION'
    assert sess_check['mentor_completed'] is True

    # 4. Requester confirms resolution with resolved=True -> bounty awarded
    mentor_before = client.get(f'/api/students/{mentor_id}').json()['points_balance']
    res_confirm = client.post(
        f'/api/sessions/{sess_id}/resolve',
        headers={'X-Demo-Student-ID': req_id},
        json={'resolved': True, 'rating': 5, 'notes': 'Brilliant mentor!'}
    )
    assert res_confirm.status_code == 200
    mentor_after = client.get(f'/api/students/{mentor_id}').json()['points_balance']
    assert mentor_after == mentor_before + 40  # 40 bounty awarded!

    # Verify resolution record status updated to CONFIRMED_RESOLVED
    final_res = client.get(f'/api/sessions/{sess_id}/resolution', headers={'X-Demo-Student-ID': req_id}).json()
    assert final_res['requester_status'] == 'CONFIRMED_RESOLVED'
    assert final_res['confirmed_at'] is not None


# ==========================================
# 5. Persistent Solution History Tests
# ==========================================

def test_solution_history_access_control(clean):
    with transaction() as db:
        sess_id, doubt_id, req_id, mentor_id = make_accepted_session(db)
        sess = db.get(m.Session, sess_id)
        sess.state = 'ACTIVE'

    # Put a resolution
    client.put(
        f'/api/sessions/{sess_id}/resolution',
        headers={'X-Demo-Student-ID': mentor_id},
        json={
            'root_cause': 'Sample root cause',
            'solution_explanation': 'Sample solution explanation'
        }
    )
    client.post(f'/api/sessions/{sess_id}/resolution/submit', headers={'X-Demo-Student-ID': mentor_id})
    client.post(
        f'/api/sessions/{sess_id}/resolve',
        headers={'X-Demo-Student-ID': req_id},
        json={'resolved': True, 'rating': 5, 'notes': 'Great!'}
    )

    # 1. Requester can view their solution history
    req_history = client.get(
        f'/api/students/{req_id}/solution-history',
        headers={'X-Demo-Student-ID': req_id}
    )
    assert req_history.status_code == 200
    hist = req_history.json()
    assert len(hist) >= 1
    record = next((r for r in hist if r['session_id'] == sess_id), None)
    assert record is not None
    assert record['role'] == 'requester'
    assert record['resolved'] is True
    assert record['resolution']['root_cause'] == 'Sample root cause'

    # 2. Mentor can view their solution history
    mentor_history = client.get(
        f'/api/students/{mentor_id}/solution-history',
        headers={'X-Demo-Student-ID': mentor_id}
    )
    assert mentor_history.status_code == 200
    m_hist = mentor_history.json()
    m_record = next((r for r in m_hist if r['session_id'] == sess_id), None)
    assert m_record is not None
    assert m_record['role'] == 'mentor'

    # 3. Third-party student gets 403 Forbidden attempting to view another's history
    unauth = client.get(
        f'/api/students/{req_id}/solution-history',
        headers={'X-Demo-Student-ID': 'student-03'}
    )
    assert unauth.status_code == 403
