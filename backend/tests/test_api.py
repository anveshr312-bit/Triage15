from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app import models as m
from app.database import transaction
from app.services import feasible
from conftest import headers

PAYLOAD={'title':'Need Python help','description':'My loop gives an unexpected result','domain':'Python','skills':['python'],'urgency':'Normal'}

def stamp(n):
    return datetime.fromtimestamp(n,timezone.utc).isoformat()

def test_full_workflow(offered):
    client,doubt,session=offered
    before=client.get('/api/metrics').json()
    mentor=headers(session['mentor_id'])
    for action in ['accept','start','complete']:
        response=client.post(f"/api/sessions/{session['id']}/{action}",headers=mentor)
        assert response.status_code==200,response.text
    response=client.post(f"/api/sessions/{session['id']}/resolve",headers=headers(),json={'resolved':True,'rating':5,'notes':'Understood the loop'})
    assert response.status_code==200,response.text
    assert response.json()['feedback']['rating']==5
    assert client.get('/api/doubts/'+doubt['id']).json()['status']=='RESOLVED'
    after=client.get('/api/metrics').json()
    assert after['resolved_sessions']==before['resolved_sessions']+1
    assert after['feedback_count']==before['feedback_count']+1
    assert client.post(f"/api/sessions/{session['id']}/resolve",headers=headers(),json={'resolved':True,'rating':5}).status_code==409
    assert client.get('/api/metrics').json()==after

def test_accept_permissions_duplicate_invalid_transition(offered):
    client,doubt,session=offered
    url='/api/sessions/'+session['id']
    assert client.post(url+'/accept',headers=headers()).status_code==403
    assert client.post(url+'/start',headers=headers(session['mentor_id'])).status_code==409
    assert client.post(url+'/accept',headers=headers(session['mentor_id'])).status_code==200
    assert client.post(url+'/accept',headers=headers(session['mentor_id'])).status_code==409
    assert client.post(url+'/resolve',headers=headers(),json={'resolved':True,'rating':5}).status_code==409

def test_decline_reassignment(offered):
    client,doubt,session=offered
    assert client.post('/api/sessions/'+session['id']+'/decline',headers=headers(session['mentor_id'])).status_code==200
    assert client.get('/api/doubts/'+doubt['id']).json()['status']=='OPEN'
    next_run=client.post('/api/dispatch/run',headers=headers()).json()
    reassigned=next_run['result']['assignments'][0]
    assert reassigned['mentor_id']!=session['mentor_id']

def test_expiration_and_reaccept(offered):
    client,doubt,session=offered
    with transaction() as db:
        db.get(m.Session,session['id']).offer_expires_at=m.now()-1
    assert client.get('/api/sessions/'+session['id']).json()['state']=='EXPIRED'
    assert client.post('/api/sessions/'+session['id']+'/accept',headers=headers(session['mentor_id'])).status_code==409
    assert client.get('/api/doubts/'+doubt['id']).json()['assigned_session_id'] is None

def test_booking_unique_constraints(offered):
    client,doubt,session=offered
    with pytest.raises(IntegrityError):
        with transaction() as db:
            existing=db.get(m.Session,session['id'])
            db.add(m.Session(doubt_id=doubt['id'],mentor_id=existing.mentor_id,start=existing.start,end=existing.end,offer_expires_at=existing.offer_expires_at))
            db.flush()
    with pytest.raises(IntegrityError):
        with transaction() as db:
            existing=db.get(m.Session,session['id'])
            db.add(m.Session(doubt_id=doubt['id'],mentor_id='student-02',start=existing.start,end=existing.end,offer_expires_at=existing.offer_expires_at))
            db.flush()
    # Different doubt, same mentor slot also rejected independently.
    other=client.post('/api/doubts',headers=headers('student-09'),json=PAYLOAD).json()
    with pytest.raises(IntegrityError):
        with transaction() as db:
            existing=db.get(m.Session,session['id'])
            db.add(m.Session(doubt_id=other['id'],mentor_id=existing.mentor_id,start=existing.start,end=existing.end,offer_expires_at=existing.offer_expires_at))
            db.flush()

def test_concurrent_dispatch(clean):
    for id in ['student-08','student-09']:
        assert clean.post('/api/doubts',headers=headers(id),json=PAYLOAD).status_code==201
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda _:clean.post('/api/dispatch/run',headers=headers()),range(2)))
    assert all(r.status_code==200 for r in responses)
    sessions=[s for s in clean.get('/api/sessions').json() if s['state']=='OFFERED']
    assert len(sessions)==2
    assert len({s['doubt_id'] for s in sessions})==2
    assert len({(s['mentor_id'],s['start']) for s in sessions})==2

@pytest.mark.parametrize('change',[{'title':''},{'description':''},{'domain':'unknown'},{'skills':['rust']},
 {'skills':[]},{'skills':['python','python']},{'urgency':'Critical'},
 {'preferred_start':'2026-01-01T10:00:00'},
 {'preferred_start':'2030-01-01T12:00:00Z','deadline':'2030-01-01T11:00:00Z'}])
def test_invalid_doubts(client,change):
    assert client.post('/api/doubts',headers=headers(),json=PAYLOAD|change).status_code==422

def test_invalid_student_missing_fields(client):
    assert client.post('/api/doubts',headers=headers('nonexistent'),json=PAYLOAD).status_code==404
    assert client.post('/api/doubts',headers=headers(),json={}).status_code==422
    assert client.post('/api/doubts',json=PAYLOAD).status_code==422

def test_assessment_scores_no_answers(client):
    for domain in ['Python','JavaScript','SQL']:
        questions=client.get('/api/assessments/'+domain+'/questions').json()
        assert len(questions)==5
        assert all('correct' not in q for q in questions)
        with transaction() as db:
            answers={q.id:q.correct for q in db.scalars(select(m.AssessmentQuestion).where(m.AssessmentQuestion.domain==domain))}
        result=client.post('/api/assessments/submit',headers=headers(),json={'domain':domain,'answers':answers})
        assert result.status_code==201,result.text
        assert result.json()['score']==100
        assert result.json()['correct_count']==5
    assert len(client.get('/api/students/student-08/assessments').json())==3
    assert client.post('/api/assessments/submit',headers=headers(),json={'domain':'Python','answers':{}}).status_code==422
    assert client.get('/api/assessments/CAD/questions').status_code==404

def test_profile_availability_and_filters(client):
    assert client.get('/api/health').status_code==200
    assert len(client.get('/api/domains').json())==6
    assert len(client.get('/api/students').json())==12
    assert client.get('/api/students/student-01').json()['history']['completed']==3
    new=client.post('/api/students',json={'name':'Demo tester'}).json()
    h=headers(new['id'])
    profile={'mentoring':True,'skills':[{'domain':'Python','tag':'python','level':3}]}
    assert client.put('/api/students/'+new['id']+'/profile',headers=headers(),json=profile).status_code==403
    assert client.put('/api/students/'+new['id']+'/profile',headers=h,json=profile).status_code==200
    assert client.put('/api/students/'+new['id']+'/profile',headers=h,json=profile).status_code==200
    window={'start':stamp(m.now()+1800),'end':stamp(m.now()+3600)}
    result=client.post('/api/students/'+new['id']+'/availability',headers=h,json=window)
    assert result.status_code==201
    assert client.delete('/api/students/'+new['id']+'/availability/'+result.json()['id'],headers=h).status_code==200
    assert client.post('/api/students/'+new['id']+'/availability',headers=h,json={'start':window['end'],'end':window['start']}).status_code==422
    items=client.get('/api/doubts?domain=Python&skill=python&urgency=Urgent&status=OPEN&search=question').json()
    assert len(items)>0
    assert all(d['domain']=='Python' and 'python' in d['skills'] and d['urgency']=='Urgent' for d in items)

def test_time_constraints_and_no_suitable_mentor(clean):
    with transaction() as db:
        mentor=db.get(m.Student,'student-01')
        start=mentor.availability[0].start
        d=m.DoubtRequest(id='time-doubt',requester_id='student-08',domain='Python',title='Times',description='Check times',urgency='Normal',
                         preferred_start=start,deadline=start+900,skills=[m.DoubtSkill(tag='python')])
        db.add(d)
        db.flush()
        assert feasible(db,d,mentor,start,m.now())
        assert not feasible(db,d,mentor,start+900,m.now())
        assert not feasible(db,d,mentor,start-900,m.now())
        assert not feasible(db,d,mentor,start+1,m.now())
        assert not feasible(db,d,db.get(m.Student,'student-03'),start,m.now())
        assert not feasible(db,d,mentor,start+86400,m.now())
        d.requester_id=mentor.id
        assert not feasible(db,d,mentor,start,m.now())
        d.requester_id='student-08'
    request=clean.post('/api/doubts',headers=headers(),json=PAYLOAD|{'domain':'Mathematics','skills':['algebra']}).json()
    run=clean.post('/api/dispatch/run',headers=headers()).json()
    assert any(x['id']==request['id'] and x['reason']=='No eligible slot' for x in run['result']['unassigned'])
    assert clean.get('/api/doubts/'+request['id']).json()['status']=='UNMATCHED'
    assert clean.get('/api/dispatch/runs/'+run['id']).status_code==200
    assert clean.get('/api/dispatch/runs/'+run['id']+'/assignments').status_code==200

def test_unresolved_feedback_and_cancellation(offered):
    client,doubt,session=offered
    for action in ['accept','start','complete']:
        assert client.post('/api/sessions/'+session['id']+'/'+action,headers=headers(session['mentor_id'])).status_code==200
    assert client.post('/api/sessions/'+session['id']+'/complete',headers=headers(session['mentor_id'])).status_code==409
    assert client.post('/api/sessions/'+session['id']+'/resolve',headers=headers(),json={'resolved':False,'rating':2}).status_code==200
    assert client.get('/api/doubts/'+doubt['id']).json()['status']=='OPEN'
    with transaction() as db:
        original=db.get(m.Session,session['id'])
        assert not feasible(db,db.get(m.DoubtRequest,doubt['id']),db.get(m.Student,session['mentor_id']),original.start,m.now())
    assert client.patch('/api/doubts/'+doubt['id'],headers=headers(),json=PAYLOAD|{'title':'Revised request'}).status_code==200
    assert client.post('/api/doubts/'+doubt['id']+'/cancel',headers=headers('student-09')).status_code==403
    assert client.post('/api/doubts/'+doubt['id']+'/cancel',headers=headers()).status_code==200

def test_cancel_session_releases_slot(offered):
    client,doubt,session=offered
    assert client.post('/api/sessions/'+session['id']+'/cancel',headers=headers('student-09')).status_code==403
    assert client.post('/api/sessions/'+session['id']+'/accept',headers=headers(session['mentor_id'])).status_code==200
    assert client.post('/api/sessions/'+session['id']+'/cancel',headers=headers(session['mentor_id'])).status_code==200
    assert client.get('/api/doubts/'+doubt['id']).json()['assigned_session_id'] is None

def test_benchmark_endpoints(client):
    response=client.post('/api/benchmarks/run',headers=headers())
    assert response.status_code==200
    data=response.json()
    assert data['result']['scenario_count']==50
    assert client.get('/api/benchmarks/'+data['id']).json()==data

def test_requester_conflict_and_unaligned_constraint(offered):
    client,doubt,session=offered
    with transaction() as db:
        original=db.get(m.Session,session['id'])
        other=m.DoubtRequest(id='shared-seeker',requester_id=doubt['requester_id'],title='Another question',
                            description='Same requester needs Python',domain='Python',urgency='Normal',skills=[m.DoubtSkill(tag='python')])
        db.add(other)
        db.flush()
        alternative='student-02' if session['mentor_id']=='student-01' else 'student-01'
        assert not feasible(db,other,db.get(m.Student,alternative),original.start,m.now())
    with pytest.raises(IntegrityError):
        with transaction() as db:
            original=db.get(m.Session,session['id'])
            db.add(m.Session(doubt_id='shared-seeker',mentor_id=alternative,start=original.start+1,
                             end=original.end+1,offer_expires_at=original.offer_expires_at))
            db.flush()

def test_active_cancel_and_reserved_availability(offered):
    client,doubt,session=offered
    mentor=headers(session['mentor_id'])
    student=client.get('/api/students/'+session['mentor_id']).json()
    window=student['availability'][0]
    assert client.delete(f"/api/students/{session['mentor_id']}/availability/{window['id']}",headers=mentor).status_code==409
    for action in ['accept','start','cancel']:
        assert client.post('/api/sessions/'+session['id']+'/'+action,headers=mentor).status_code==200
    assert client.get('/api/doubts/'+doubt['id']).json()['status']=='OPEN'
