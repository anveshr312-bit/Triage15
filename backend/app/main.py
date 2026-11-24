import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError
from . import models as m, schemas as s, services as svc
from .database import transaction
from .seed import initialize
from .config import DOMAINS
from .algorithms import benchmark

async def expiration_loop():
    while True:
        await asyncio.sleep(10)
        try:
            await asyncio.to_thread(expire_offers)
        except OperationalError:
            # Retry on next sweep; every booking operation also expires offers.
            pass

def expire_offers():
    with transaction() as db:
        svc.expire(db,m.now())

@asynccontextmanager
async def lifespan(app):
    initialize()
    task = asyncio.create_task(expiration_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

app = FastAPI(title='Triage15',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],
                   allow_methods=['GET','POST','PATCH','PUT','DELETE'],allow_headers=['Content-Type','X-Demo-Student-ID'])

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409,content={'detail':'Database integrity conflict; refresh and retry.'})

@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(status_code=503,content={'detail':'Database temporarily unavailable; retry shortly.'})

def database():
    with transaction() as db:
        svc.expire(db,m.now())
        yield db

def identity(x_demo_student_id: str = Header(...), db=Depends(database)):
    return svc.get(db,m.Student,x_demo_student_id)

def own(student, id):
    svc.require(student.id == id,'This action belongs to another demo student',403)

@app.get('/api/health')
def health():
    return {'status':'ok','mode':'local demo; no production authentication'}

@app.get('/api/domains')
def domains():
    return DOMAINS

@app.get('/api/students')
def students(db=Depends(database)):
    return [svc.serialize(x) for x in db.scalars(select(m.Student).order_by(m.Student.name))]

@app.post('/api/students',status_code=201)
def register(body:s.StudentInput,db=Depends(database)):
    student = m.Student(name=body.name)
    db.add(student)
    db.flush()
    return svc.serialize(student)

@app.get('/api/students/{id}')
def student(id:str,db=Depends(database)):
    result=svc.serialize(svc.get(db,m.Student,id))
    completed,resolved=svc.history(db,id)
    result['history']={'completed':completed,'resolved':resolved,'reliability':15*(resolved+2)/(completed+4)}
    return result

@app.put('/api/students/{id}/profile')
def profile(id:str,body:s.ProfileInput,actor=Depends(identity),db=Depends(database)):
    own(actor,id)
    actor.mentoring=body.mentoring
    actor.skills.clear()
    db.flush()
    actor.skills=[m.StudentSkill(**skill.model_dump()) for skill in body.skills]
    db.flush()
    return svc.serialize(actor)

@app.post('/api/students/{id}/availability',status_code=201)
def availability(id:str,body:s.WindowInput,actor=Depends(identity),db=Depends(database)):
    own(actor,id)
    svc.require(body.end.timestamp()>m.now(),'Availability is in the past',422)
    svc.require(body.end.timestamp()<=m.now()+7*86400,'Availability must be within seven days',422)
    svc.require(len(actor.availability)<30,'Maximum 30 availability windows',422)
    window=m.AvailabilityWindow(student_id=id,start=int(body.start.timestamp()),end=int(body.end.timestamp()))
    db.add(window)
    db.flush()
    return svc.serialize(window)

@app.delete('/api/students/{id}/availability/{window_id}')
def remove_availability(id:str,window_id:str,actor=Depends(identity),db=Depends(database)):
    own(actor,id)
    window=svc.get(db,m.AvailabilityWindow,window_id)
    own(actor,window.student_id)
    svc.require(not db.scalar(select(m.Session.id).where(m.Session.mentor_id==id,m.Session.state.in_(svc.LIVE),
                m.Session.start<window.end,m.Session.end>window.start)),'Cancel reserved sessions before removing this window')
    db.delete(window)
    return {'deleted':True}

@app.get('/api/assessments/{domain}/questions')
def questions(domain:str,db=Depends(database)):
    items=list(db.scalars(select(m.AssessmentQuestion).where(m.AssessmentQuestion.domain==domain).order_by(m.AssessmentQuestion.id)))
    svc.require(bool(items),'No assessment bank for this domain; skills remain provisional',404)
    return [{k:v for k,v in svc.serialize(q).items() if k!='correct'} for q in items]

@app.post('/api/assessments/submit',status_code=201)
def assess(body:s.AssessmentInput,actor=Depends(identity),db=Depends(database)):
    items=list(db.scalars(select(m.AssessmentQuestion).where(m.AssessmentQuestion.domain==body.domain)))
    svc.require(bool(items) and set(body.answers)=={q.id for q in items},'Answer every question in this domain exactly once',422)
    svc.require(all(0<=body.answers[q.id]<len(q.options) for q in items),'Invalid answer option',422)
    correct=sum(body.answers[q.id]==q.correct for q in items)
    attempt=m.AssessmentAttempt(student_id=actor.id,domain=body.domain,score=round(100*correct/len(items)),
                                question_count=len(items),correct_count=correct,version=1)
    db.add(attempt)
    db.flush()
    for q in items:
        db.add(m.AssessmentResponse(attempt_id=attempt.id,question_id=q.id,answer=body.answers[q.id]))
    return svc.serialize(attempt)

@app.get('/api/students/{id}/assessments')
def assessments(id:str,db=Depends(database)):
    svc.get(db,m.Student,id)
    return [svc.serialize(x) for x in db.scalars(select(m.AssessmentAttempt).where(m.AssessmentAttempt.student_id==id).order_by(m.AssessmentAttempt.created_at.desc()))]

def doubt_values(body):
    data=body.model_dump(exclude={'skills'})
    for field in ('preferred_start','deadline'):
        data[field]=int(data[field].timestamp()) if data[field] else None
    svc.require(data['deadline'] is None or data['deadline']>=m.now()+900,'Deadline must allow a future 15-minute session',422)
    return data

@app.post('/api/doubts',status_code=201)
def create_doubt(body:s.DoubtInput,actor=Depends(identity),db=Depends(database)):
    doubt=m.DoubtRequest(requester_id=actor.id,**doubt_values(body))
    doubt.skills=[m.DoubtSkill(tag=tag) for tag in body.skills]
    db.add(doubt)
    db.flush()
    return svc.serialize(doubt)

@app.get('/api/doubts')
def doubts(domain:str|None=None,skill:str|None=None,urgency:str|None=None,status:str|None=None,
           search:str|None=Query(None,max_length=150),db=Depends(database)):
    query=select(m.DoubtRequest)
    for column,value in [(m.DoubtRequest.domain,domain),(m.DoubtRequest.urgency,urgency),(m.DoubtRequest.status,status)]:
        if value:
            query=query.where(column==value)
    if skill:
        query=query.where(m.DoubtRequest.skills.any(m.DoubtSkill.tag==skill))
    if search:
        query=query.where(m.DoubtRequest.title.icontains(search,autoescape=True)|m.DoubtRequest.description.icontains(search,autoescape=True))
    return [svc.serialize(d) for d in db.scalars(query.order_by(m.DoubtRequest.created_at.desc()))]

@app.get('/api/doubts/{id}')
def doubt(id:str,db=Depends(database)):
    return svc.serialize(svc.get(db,m.DoubtRequest,id))

@app.patch('/api/doubts/{id}')
def edit_doubt(id:str,body:s.DoubtInput,actor=Depends(identity),db=Depends(database)):
    doubt=svc.get(db,m.DoubtRequest,id)
    own(actor,doubt.requester_id)
    svc.require(doubt.status in ('OPEN','UNMATCHED'),'Only waiting requests can be edited')
    for key,value in doubt_values(body).items():
        setattr(doubt,key,value)
    doubt.skills.clear()
    db.flush()
    doubt.skills=[m.DoubtSkill(tag=tag) for tag in body.skills]
    doubt.status='OPEN'
    db.flush()
    return svc.serialize(doubt)

@app.post('/api/doubts/{id}/cancel')
def cancel_doubt(id:str,actor=Depends(identity),db=Depends(database)):
    doubt=svc.get(db,m.DoubtRequest,id)
    own(actor,doubt.requester_id)
    svc.require(doubt.status not in ('RESOLVED','CANCELLED'),'Request already closed')
    if doubt.assigned_session_id:
        session=svc.get(db,m.Session,doubt.assigned_session_id)
        if session.state in svc.LIVE:
            session.state='CANCELLED'
    doubt.status,doubt.assigned_session_id='CANCELLED',None
    return svc.serialize(doubt)

@app.post('/api/dispatch/run')
def run_dispatch(actor=Depends(identity),db=Depends(database)):
    return svc.serialize(svc.dispatch(db,m.now()))

@app.get('/api/dispatch/runs/{id}')
def dispatch_run(id:str,db=Depends(database)):
    return svc.serialize(svc.get(db,m.DispatchRun,id))

@app.get('/api/dispatch/runs/{id}/assignments')
def assignments(id:str,db=Depends(database)):
    svc.get(db,m.DispatchRun,id)
    return [svc.serialize(x) for x in db.scalars(select(m.Session).where(m.Session.dispatch_run_id==id))]

def session_data(db,session):
    data=svc.serialize(session)
    data['requester_id']=svc.get(db,m.DoubtRequest,session.doubt_id).requester_id
    feedback=db.scalar(select(m.SessionFeedback).where(m.SessionFeedback.session_id==session.id))
    data['feedback']=svc.serialize(feedback) if feedback else None
    return data

@app.get('/api/sessions')
def sessions(db=Depends(database)):
    return [session_data(db,x) for x in db.scalars(select(m.Session).order_by(m.Session.start.desc()))]

@app.get('/api/sessions/{id}')
def session(id:str,db=Depends(database)):
    return session_data(db,svc.get(db,m.Session,id))

@app.post('/api/sessions/{id}/{action}')
def transition(id:str,action:str,body:s.ResolutionInput|None=None,actor=Depends(identity),db=Depends(database)):
    session=svc.get(db,m.Session,id)
    doubt=svc.get(db,m.DoubtRequest,session.doubt_id)
    if action in ('accept','decline','start','complete'):
        own(actor,session.mentor_id)
        expected={'accept':'OFFERED','decline':'OFFERED','start':'ACCEPTED','complete':'ACTIVE'}[action]
        svc.require(session.state==expected,f'{action} requires {expected}; current state is {session.state}')
        if action=='accept':
            svc.require(session.offer_expires_at>m.now(),'Offer expired')
            session.state='ACCEPTED'
        elif action=='decline':
            svc.release(db,session,'DECLINED')
        elif action=='start':
            # Local demo permits early start, preserving the reserved scheduling interval.
            session.state,doubt.status='ACTIVE','IN_SESSION'
        else:
            svc.require(not session.mentor_completed,'Mentor already marked complete')
            session.mentor_completed=True
    elif action=='resolve':
        own(actor,doubt.requester_id)
        svc.require(session.state=='ACTIVE' and session.mentor_completed,'Mentor must complete an active session first')
        svc.require(body is not None,'Resolution, rating and notes are required',422)
        session.state,session.resolved,session.notes='RESOLVED',body.resolved,body.notes
        db.add(m.SessionFeedback(session_id=session.id,student_id=actor.id,rating=body.rating,notes=body.notes))
        if body.resolved:
            doubt.status='RESOLVED'
        else:
            doubt.status,doubt.assigned_session_id='OPEN',None
    elif action=='cancel':
        svc.require(actor.id in (session.mentor_id,doubt.requester_id),'Only participants can cancel',403)
        svc.require(session.state in svc.LIVE,'Session already closed')
        svc.release(db,session,'CANCELLED')
    else:
        raise HTTPException(404,'Unknown session action')
    db.flush()
    return session_data(db,session)

@app.get('/api/metrics')
def metrics(db=Depends(database)):
    doubt_counts=dict(db.execute(select(m.DoubtRequest.status,func.count()).group_by(m.DoubtRequest.status)).all())
    session_counts=dict(db.execute(select(m.Session.state,func.count()).group_by(m.Session.state)).all())
    return {'doubts':doubt_counts,'sessions':session_counts,
            'resolved_sessions':db.scalar(select(func.count()).select_from(m.Session).where(m.Session.resolved.is_(True))),
            'feedback_count':db.scalar(select(func.count()).select_from(m.SessionFeedback)),
            'average_rating':db.scalar(select(func.avg(m.SessionFeedback.rating)))}

@app.post('/api/benchmarks/run')
def run_benchmark(actor=Depends(identity),db=Depends(database)):
    run=m.BenchmarkRun(result=benchmark())
    db.add(run)
    db.flush()
    return svc.serialize(run)

@app.get('/api/benchmarks/{id}')
def benchmark_result(id:str,db=Depends(database)):
    return svc.serialize(svc.get(db,m.BenchmarkRun,id))
