import asyncio
import random
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Depends, Header, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from . import models as m, schemas as s, services as svc
from .database import transaction
from .seed import initialize
from .config import DOMAINS, SLOT
from .algorithms import benchmark

# Centralized Dispatch Coordinator (P0.4)
class DispatchCoordinator:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.enabled = True

    async def trigger(self):
        if not self.enabled:
            return None
        async with self._lock:
            try:
                return await asyncio.to_thread(self._run_dispatch)
            except Exception:
                return None

    def _run_dispatch(self):
        with transaction() as db:
            return svc.dispatch(db, m.now())

coordinator = DispatchCoordinator()

async def expiration_loop():
    while True:
        await asyncio.sleep(10)
        try:
            await asyncio.to_thread(expire_offers)
        except OperationalError:
            pass

def expire_offers():
    with transaction() as db:
        expired = svc.expire(db, m.now())
        if expired:
            try:
                svc.dispatch(db, m.now())
            except Exception:
                pass

@asynccontextmanager
async def lifespan(app):
    initialize()
    task = asyncio.create_task(expiration_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

app = FastAPI(title='Triage15', version='1.0.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'X-Demo-Student-ID', 'X-Auto-Dispatch']
)

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={'detail': 'Database integrity conflict; refresh and retry.'})

@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'detail': 'Database temporarily unavailable; retry shortly.'})

def database():
    with transaction() as db:
        svc.expire(db, m.now())
        yield db

def identity(x_demo_student_id: str = Header(...), db=Depends(database)):
    return svc.get(db, m.Student, x_demo_student_id)

def own(student, id):
    svc.require(student.id == id, 'This action belongs to another demo student', 403)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'mode': 'local demo; synthetic profiles; authoritative server clock'}

@app.get('/api/server-time')
def server_time():
    return {'now': m.now(), 'iso': svc.iso(m.now()), 'timezone': 'Asia/Kolkata (IST)'}

@app.get('/api/domains')
def domains():
    return DOMAINS

@app.get('/api/students')
def students(db=Depends(database)):
    return [svc.serialize(x) for x in db.scalars(select(m.Student).order_by(m.Student.name))]

@app.post('/api/students', status_code=201)
def register(body: s.StudentInput, db=Depends(database)):
    student = m.Student(name=body.name, points_balance=100)
    db.add(student)
    db.flush()
    # Record initial points grant in ledger
    ledger = m.PointLedger(
        student_id=student.id,
        amount=100,
        transaction_type='INITIAL_GRANT',
        reference_id=f'grant:{student.id}',
        balance_after=100,
        notes='Initial demo points grant'
    )
    db.add(ledger)
    db.flush()
    return svc.serialize(student)

@app.get('/api/students/{id}')
def student(id: str, db=Depends(database)):
    s_obj = svc.get(db, m.Student, id)
    result = svc.serialize(s_obj)
    completed, resolved = svc.history(db, id)
    result['history'] = {
        'completed': completed,
        'resolved': resolved,
        'reliability': 15 * (resolved + 2) / (completed + 4)
    }
    return result

@app.get('/api/students/{id}/ledger')
def student_ledger(id: str, db=Depends(database)):
    svc.get(db, m.Student, id)
    entries = db.scalars(select(m.PointLedger).where(m.PointLedger.student_id == id).order_by(m.PointLedger.created_at.desc())).all()
    return [svc.serialize(x) for x in entries]

# P1.4: Mentor Credibility Profile
@app.get('/api/mentors/{id}/profile')
def mentor_profile(id: str, db=Depends(database)):
    s_obj = svc.get(db, m.Student, id)
    completed, resolved = svc.history(db, id)
    feedbacks = db.scalars(
        select(m.SessionFeedback)
        .join(m.Session, m.SessionFeedback.session_id == m.Session.id)
        .where(m.Session.mentor_id == id)
    ).all()
    ratings = [f.rating for f in feedbacks]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    
    bounties_earned = db.scalar(
        select(func.coalesce(func.sum(m.PointLedger.amount), 0))
        .where(m.PointLedger.student_id == id, m.PointLedger.transaction_type == 'BOUNTY_AWARDED')
    ) or 0

    attempts = db.scalars(
        select(m.AssessmentAttempt)
        .where(m.AssessmentAttempt.student_id == id)
        .order_by(m.AssessmentAttempt.created_at.desc())
    ).all()

    resolution_rate = round(100.0 * resolved / completed, 1) if completed > 0 else None

    return {
        'id': s_obj.id,
        'name': s_obj.name,
        'mentoring': s_obj.mentoring,
        'points_balance': s_obj.points_balance,
        'skills': [svc.serialize(sk) for sk in s_obj.skills],
        'availability': [svc.serialize(av) for av in s_obj.availability],
        'assessments': [svc.serialize(at) for at in attempts],
        'completed_sessions': completed,
        'resolved_sessions': resolved,
        'resolution_rate': resolution_rate,
        'resolution_history_label': f"{resolution_rate}% ({resolved}/{completed} sessions)" if completed > 0 else "No resolution history yet",
        'feedback_count': len(ratings),
        'average_rating': avg_rating,
        'bounties_earned': bounties_earned,
        'smoothed_reliability_heuristic': round(15 * (resolved + 2) / (completed + 4), 2)
    }

@app.put('/api/students/{id}/profile')
def profile(id: str, body: s.ProfileInput, actor=Depends(identity), db=Depends(database)):
    own(actor, id)
    actor.mentoring = body.mentoring
    actor.skills.clear()
    db.flush()
    actor.skills = [m.StudentSkill(**skill.model_dump()) for skill in body.skills]
    db.flush()
    return svc.serialize(actor)

@app.post('/api/students/{id}/availability', status_code=201)
def availability(id: str, body: s.WindowInput, actor=Depends(identity), db=Depends(database)):
    own(actor, id)
    svc.require(body.end.timestamp() > m.now(), 'Availability is in the past', 422)
    svc.require(body.end.timestamp() <= m.now() + 7 * 86400, 'Availability must be within seven days', 422)
    svc.require(len(actor.availability) < 30, 'Maximum 30 availability windows', 422)
    window = m.AvailabilityWindow(student_id=id, start=int(body.start.timestamp()), end=int(body.end.timestamp()))
    db.add(window)
    db.flush()
    return svc.serialize(window)

@app.delete('/api/students/{id}/availability/{window_id}')
def remove_availability(id: str, window_id: str, actor=Depends(identity), db=Depends(database)):
    own(actor, id)
    window = svc.get(db, m.AvailabilityWindow, window_id)
    own(actor, window.student_id)
    svc.require(
        not db.scalar(select(m.Session.id).where(
            m.Session.mentor_id == id,
            m.Session.state.in_(svc.LIVE),
            m.Session.start < window.end,
            m.Session.end > window.start
        )),
        'Cancel reserved sessions before removing this window'
    )
    db.delete(window)
    return {'deleted': True}

# P1.3 Assessment Improvements: Server-side validation, stable option ordering, attempt cooldown
@app.get('/api/assessments/{domain}/questions')
def questions(domain: str, db=Depends(database)):
    items = list(db.scalars(select(m.AssessmentQuestion).where(m.AssessmentQuestion.domain == domain).order_by(m.AssessmentQuestion.id)))
    svc.require(bool(items), 'No assessment bank for this domain; skills remain provisional', 404)
    # Server-side option masking: never expose correct answer index.
    result = []
    for q in items:
        serialized = svc.serialize(q)
        serialized.pop('correct', None)
        result.append(serialized)
    return result

@app.post('/api/assessments/submit', status_code=201)
def assess(body: s.AssessmentInput, actor=Depends(identity), db=Depends(database)):
    # Daily attempt cooldown check
    one_day_ago = m.now() - 86400
    recent_attempts = db.scalar(
        select(func.count()).select_from(m.AssessmentAttempt).where(
            m.AssessmentAttempt.student_id == actor.id,
            m.AssessmentAttempt.domain == body.domain,
            m.AssessmentAttempt.created_at >= one_day_ago
        )
    ) or 0
    svc.require(recent_attempts < 10, 'Daily assessment attempt limit reached for this domain. Please retry tomorrow.', 429)

    items = list(db.scalars(select(m.AssessmentQuestion).where(m.AssessmentQuestion.domain == body.domain)))
    svc.require(bool(items) and set(body.answers) == {q.id for q in items}, 'Answer every question in this domain exactly once', 422)
    svc.require(all(0 <= body.answers[q.id] < len(q.options) for q in items), 'Invalid answer option', 422)
    correct = sum(body.answers[q.id] == q.correct for q in items)
    attempt = m.AssessmentAttempt(
        student_id=actor.id,
        domain=body.domain,
        score=round(100 * correct / len(items)),
        question_count=len(items),
        correct_count=correct,
        version=1
    )
    db.add(attempt)
    db.flush()
    for q in items:
        db.add(m.AssessmentResponse(attempt_id=attempt.id, question_id=q.id, answer=body.answers[q.id]))
    return svc.serialize(attempt)

@app.get('/api/students/{id}/assessments')
def assessments(id: str, db=Depends(database)):
    svc.get(db, m.Student, id)
    return [svc.serialize(x) for x in db.scalars(select(m.AssessmentAttempt).where(m.AssessmentAttempt.student_id == id).order_by(m.AssessmentAttempt.created_at.desc()))]

def doubt_values(body):
    data = body.model_dump(exclude={'skills'})
    for field in ('preferred_start', 'deadline'):
        data[field] = int(data[field].timestamp()) if data[field] else None
    svc.require(data['deadline'] is None or data['deadline'] >= m.now() + 900, 'Deadline must allow a future 15-minute session', 422)
    return data

@app.post('/api/doubts', status_code=201)
def create_doubt(body: s.DoubtInput, x_auto_dispatch: str | None = Header(None), actor=Depends(identity), db=Depends(database)):
    bounty = body.bounty or 0
    svc.require(actor.points_balance >= bounty, f'Insufficient points balance (available: {actor.points_balance}, requested: {bounty})', 422)
    
    doubt = m.DoubtRequest(requester_id=actor.id, **doubt_values(body))
    doubt.skills = [m.DoubtSkill(tag=tag) for tag in body.skills]
    db.add(doubt)
    db.flush()

    if bounty > 0:
        svc.reserve_bounty(db, actor, doubt.id, bounty)

    if x_auto_dispatch == 'true':
        try:
            svc.dispatch(db, m.now())
        except Exception:
            pass

    return svc.serialize(doubt)

@app.get('/api/doubts')
def doubts(domain: str | None = None, skill: str | None = None, urgency: str | None = None, status: str | None = None,
           search: str | None = Query(None, max_length=150), db=Depends(database)):
    query = select(m.DoubtRequest)
    for column, value in [(m.DoubtRequest.domain, domain), (m.DoubtRequest.urgency, urgency), (m.DoubtRequest.status, status)]:
        if value:
            query = query.where(column == value)
    if skill:
        query = query.where(m.DoubtRequest.skills.any(m.DoubtSkill.tag == skill))
    if search:
        query = query.where(m.DoubtRequest.title.icontains(search, autoescape=True) | m.DoubtRequest.description.icontains(search, autoescape=True))
    return [svc.serialize(d) for d in db.scalars(query.order_by(m.DoubtRequest.created_at.desc()))]

@app.get('/api/doubts/{id}')
def doubt(id: str, db=Depends(database)):
    return svc.serialize(svc.get(db, m.DoubtRequest, id))

# P1.5: Doubt Editing with safe bounty adjustment
@app.patch('/api/doubts/{id}')
def edit_doubt(id: str, body: s.DoubtInput, x_auto_dispatch: str | None = Header(None), actor=Depends(identity), db=Depends(database)):
    doubt = svc.get(db, m.DoubtRequest, id)
    own(actor, doubt.requester_id)
    svc.require(doubt.status in ('OPEN', 'UNMATCHED'), 'Only waiting requests can be edited')
    
    # Safe bounty adjustment
    new_bounty = body.bounty or 0
    if new_bounty != doubt.bounty:
        svc.adjust_bounty(db, actor, doubt, new_bounty)

    for key, value in doubt_values(body).items():
        if key != 'bounty':
            setattr(doubt, key, value)
    doubt.skills.clear()
    db.flush()
    doubt.skills = [m.DoubtSkill(tag=tag) for tag in body.skills]
    doubt.status = 'OPEN'
    db.flush()

    if x_auto_dispatch == 'true':
        try:
            svc.dispatch(db, m.now())
        except Exception:
            pass

    return svc.serialize(doubt)

@app.post('/api/doubts/{id}/cancel')
def cancel_doubt(id: str, actor=Depends(identity), db=Depends(database)):
    doubt = svc.get(db, m.DoubtRequest, id)
    own(actor, doubt.requester_id)
    svc.require(doubt.status not in ('RESOLVED', 'CANCELLED'), 'Request already closed')
    if doubt.assigned_session_id:
        session = svc.get(db, m.Session, doubt.assigned_session_id)
        if session.state in svc.LIVE:
            session.state = 'CANCELLED'
            session.completed_at = m.now()
    doubt.status, doubt.assigned_session_id = 'CANCELLED', None
    # Refund reserved bounty
    svc.refund_bounty(db, doubt, reason='requester_cancelled')
    db.flush()
    return svc.serialize(doubt)

# P0.6: Manual Session Claiming
@app.post('/api/doubts/{id}/claim')
def claim_doubt_endpoint(id: str, body: s.ClaimInput | None = None, actor=Depends(identity), db=Depends(database)):
    slot_start = int(body.slot_start.timestamp()) if (body and body.slot_start) else None
    session = svc.claim_doubt(db, id, actor.id, m.now(), slot_start)
    return session_data(db, session)

@app.post('/api/dispatch/run')
def run_dispatch(actor=Depends(identity), db=Depends(database)):
    return svc.serialize(svc.dispatch(db, m.now()))

@app.get('/api/dispatch/runs/{id}')
def dispatch_run(id: str, db=Depends(database)):
    return svc.serialize(svc.get(db, m.DispatchRun, id))

@app.get('/api/dispatch/runs/{id}/assignments')
def assignments(id: str, db=Depends(database)):
    svc.get(db, m.DispatchRun, id)
    return [svc.serialize(x) for x in db.scalars(select(m.Session).where(m.Session.dispatch_run_id == id))]

# P1.6: Complete Session Details
def session_data(db, session):
    data = svc.serialize(session)
    doubt = svc.get(db, m.DoubtRequest, session.doubt_id)
    requester = svc.get(db, m.Student, doubt.requester_id)
    mentor = svc.get(db, m.Student, session.mentor_id)

    data['requester_id'] = requester.id
    data['requester_name'] = requester.name
    data['mentor_name'] = mentor.name
    data['doubt_title'] = doubt.title
    data['doubt_description'] = doubt.description
    data['doubt_domain'] = doubt.domain
    data['doubt_skills'] = [s.tag for s in doubt.skills]
    data['doubt_urgency'] = doubt.urgency
    data['bounty'] = doubt.bounty
    data['server_time'] = m.now()
    if session.is_demo_accelerated and session.actual_started_at:
        data['active_seconds_remaining'] = max(0, session.actual_started_at + 30 - m.now())
    elif session.state == 'ACTIVE':
        data['active_seconds_remaining'] = max(0, session.end - m.now())
    else:
        data['active_seconds_remaining'] = 900

    feedback = db.scalar(select(m.SessionFeedback).where(m.SessionFeedback.session_id == session.id))
    data['feedback'] = svc.serialize(feedback) if feedback else None
    return data

@app.get('/api/sessions')
def sessions(db=Depends(database)):
    return [session_data(db, x) for x in db.scalars(select(m.Session).order_by(m.Session.start.desc()))]

@app.get('/api/sessions/{id}')
def session(id: str, db=Depends(database)):
    return session_data(db, svc.get(db, m.Session, id))

# P0.2: Session Messaging Workspace Endpoints
@app.get('/api/sessions/{id}/messages')
def session_messages(id: str, since_id: str | None = None, since_time: int | None = None,
                     actor=Depends(identity), db=Depends(database)):
    sess = svc.get(db, m.Session, id)
    doubt = svc.get(db, m.DoubtRequest, sess.doubt_id)
    svc.require(actor.id in (sess.mentor_id, doubt.requester_id), 'Only session participants can access messages', 403)
    
    query = select(m.SessionMessage).where(m.SessionMessage.session_id == id)
    if since_time:
        query = query.where(m.SessionMessage.created_at > since_time)
    messages = db.scalars(query.order_by(m.SessionMessage.created_at.asc())).all()
    if since_id:
        idx = next((i for i, msg in enumerate(messages) if msg.id == since_id), -1)
        if idx != -1:
            messages = messages[idx + 1:]
    return [svc.serialize(msg) for msg in messages]

@app.post('/api/sessions/{id}/messages', status_code=201)
def send_message(id: str, body: s.MessageInput, actor=Depends(identity), db=Depends(database)):
    sess = svc.get(db, m.Session, id)
    doubt = svc.get(db, m.DoubtRequest, sess.doubt_id)
    svc.require(actor.id in (sess.mentor_id, doubt.requester_id), 'Only session participants can post messages', 403)
    svc.require(sess.state in ('OFFERED', 'ACCEPTED', 'ACTIVE', 'AWAITING_CONFIRMATION'), 'Cannot send messages to a closed session', 409)
    
    msg = m.SessionMessage(
        session_id=id,
        sender_id=actor.id,
        content=body.content
    )
    db.add(msg)
    db.flush()
    return svc.serialize(msg)

# P0.3: Accelerated Demo Mode Trigger
@app.post('/api/sessions/{id}/accelerate')
def accelerate_session(id: str, actor=Depends(identity), db=Depends(database)):
    sess = svc.get(db, m.Session, id)
    doubt = svc.get(db, m.DoubtRequest, sess.doubt_id)
    svc.require(actor.id in (sess.mentor_id, doubt.requester_id), 'Only session participants can toggle demo mode', 403)
    svc.require(sess.state in ('ACCEPTED', 'ACTIVE'), 'Can only accelerate active or accepted sessions', 409)
    
    sess.is_demo_accelerated = True
    if sess.state == 'ACCEPTED':
        sess.state = 'ACTIVE'
        doubt.status = 'IN_SESSION'
    if not sess.actual_started_at:
        sess.actual_started_at = m.now()
    db.flush()
    return session_data(db, sess)

# Session Lifecycle Transitions (P0.3, P0.5, P1.7)
@app.post('/api/sessions/{id}/{action}')
def transition(id: str, action: str, body: s.ResolutionInput | None = None,
               x_auto_dispatch: str | None = Header(None), actor=Depends(identity), db=Depends(database)):
    session = svc.get(db, m.Session, id)
    doubt = svc.get(db, m.DoubtRequest, session.doubt_id)
    
    if action in ('accept', 'decline', 'start', 'complete'):
        own(actor, session.mentor_id)
        if action == 'accept':
            svc.require(session.state == 'OFFERED', f'accept requires OFFERED; current state is {session.state}')
            svc.require(session.offer_expires_at > m.now(), 'Offer expired')
            session.state = 'ACCEPTED'
            session.accepted_at = m.now()
        elif action == 'decline':
            svc.require(session.state == 'OFFERED', f'decline requires OFFERED; current state is {session.state}')
            svc.release(db, session, 'DECLINED')
            session.notes = 'Declined by mentor; returned to queue'
            # P0.5 Reassignment trigger if requested
            if x_auto_dispatch == 'true':
                try:
                    svc.dispatch(db, m.now())
                except Exception:
                    pass
        elif action == 'start':
            svc.require(session.state == 'ACCEPTED', f'start requires ACCEPTED; current state is {session.state}')
            # Validate start window (cannot start more than 15 min past end)
            svc.require(m.now() <= session.end + 900, 'Session scheduled window has expired; cannot start', 409)
            session.state, doubt.status = 'ACTIVE', 'IN_SESSION'
            session.actual_started_at = m.now()
        else:  # complete
            svc.require(session.state in ('ACTIVE', 'AWAITING_CONFIRMATION'), f'complete requires ACTIVE; current state is {session.state}')
            svc.require(not session.mentor_completed, 'Mentor already marked complete')
            session.mentor_completed = True
            session.mentor_completed_at = m.now()
            session.state = 'AWAITING_CONFIRMATION'
            session.outcome_deadline = m.now() + 86400  # 24 hour confirmation window
            doubt.status = 'AWAITING_CONFIRMATION'
    elif action == 'resolve':
        own(actor, doubt.requester_id)
        svc.require(session.mentor_completed, 'Mentor must complete session first')
        svc.require(session.state in ('ACTIVE', 'AWAITING_CONFIRMATION'), 'Session is not awaiting resolution')
        svc.require(body is not None, 'Resolution, rating and notes are required', 422)
        
        session.state, session.resolved, session.notes = 'RESOLVED', body.resolved, body.notes
        session.completed_at = m.now()
        db.add(m.SessionFeedback(session_id=session.id, student_id=actor.id, rating=body.rating, notes=body.notes))
        
        if body.resolved:
            doubt.status = 'RESOLVED'
            mentor = svc.get(db, m.Student, session.mentor_id)
            svc.award_bounty(db, mentor, session, doubt)
        else:
            doubt.status, doubt.assigned_session_id = 'OPEN', None
            # Reserved bounty remains intact on the doubt for reassignment!
            if x_auto_dispatch == 'true':
                try:
                    svc.dispatch(db, m.now())
                except Exception:
                    pass
    elif action == 'cancel':
        svc.require(actor.id in (session.mentor_id, doubt.requester_id), 'Only participants can cancel', 403)
        svc.require(session.state in svc.LIVE, 'Session already closed')
        is_mentor = actor.id == session.mentor_id
        svc.release(db, session, 'CANCELLED')
        if not is_mentor:
            # Requester cancelled doubt session
            doubt.status = 'CANCELLED'
            svc.refund_bounty(db, doubt, reason='requester_cancelled_session')
        else:
            # Mentor cancelled: doubt returns to queue
            doubt.status, doubt.assigned_session_id = 'OPEN', None
            if x_auto_dispatch == 'true':
                try:
                    svc.dispatch(db, m.now())
                except Exception:
                    pass
    else:
        raise HTTPException(404, 'Unknown session action')

    db.flush()
    return session_data(db, session)

@app.get('/api/metrics')
def metrics(db=Depends(database)):
    doubt_counts = dict(db.execute(select(m.DoubtRequest.status, func.count()).group_by(m.DoubtRequest.status)).all())
    session_counts = dict(db.execute(select(m.Session.state, func.count()).group_by(m.Session.state)).all())
    total_bounties = db.scalar(
        select(func.coalesce(func.sum(m.PointLedger.amount), 0))
        .where(m.PointLedger.transaction_type == 'BOUNTY_AWARDED')
    ) or 0
    return {
        'doubts': doubt_counts,
        'sessions': session_counts,
        'resolved_sessions': db.scalar(select(func.count()).select_from(m.Session).where(m.Session.resolved.is_(True))),
        'feedback_count': db.scalar(select(func.count()).select_from(m.SessionFeedback)),
        'average_rating': db.scalar(select(func.avg(m.SessionFeedback.rating))),
        'total_bounties_awarded': total_bounties
    }

@app.post('/api/benchmarks/run')
def run_benchmark(actor=Depends(identity), db=Depends(database)):
    run = m.BenchmarkRun(result=benchmark())
    db.add(run)
    db.flush()
    return svc.serialize(run)

@app.get('/api/benchmarks/{id}')
def benchmark_result(id: str, db=Depends(database)):
    return svc.serialize(svc.get(db, m.BenchmarkRun, id))
