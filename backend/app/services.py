from datetime import datetime, timezone
from time import perf_counter
from fastapi import HTTPException
from sqlalchemy import select
from . import models as m
from .algorithms import maximum_weight, greedy, summarize
from .config import SLOT, OFFER_TTL_SECONDS, URGENCY

LIVE = ('OFFERED','ACCEPTED','ACTIVE')

def get(db, model, id):
    value = db.get(model, id)
    if value is None:
        raise HTTPException(404, f'{model.__name__} not found')
    return value

def require(condition, message, code=409):
    if not condition:
        raise HTTPException(code, message)

def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None

def serialize(obj):
    data = {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
    for key in ('start','end','created_at','preferred_start','deadline','offer_expires_at'):
        if key in data:
            data[key] = iso(data[key])
    if isinstance(obj,m.DoubtRequest):
        data['skills'] = [s.tag for s in obj.skills]
    if isinstance(obj,m.Student):
        data['skills'] = [serialize(s) for s in obj.skills]
        data['availability'] = [serialize(a) for a in obj.availability]
    return data

def release(db, session, state):
    session.state = state
    doubt = get(db,m.DoubtRequest,session.doubt_id)
    doubt.status, doubt.assigned_session_id = 'OPEN', None

def expire(db, current):
    for session in db.scalars(select(m.Session).where(m.Session.state == 'OFFERED', m.Session.offer_expires_at <= current)):
        release(db,session,'EXPIRED')
    db.flush()

def history(db, student_id):
    sessions = list(db.scalars(select(m.Session).where(m.Session.mentor_id == student_id, m.Session.state == 'RESOLVED')))
    return len(sessions), sum(s.resolved is True for s in sessions)

def score(doubt, mentor, start, current, assessment, completed, resolved):
    tags = {s.tag for s in mentor.skills if s.domain == doubt.domain}
    required = {s.tag for s in doubt.skills}
    relevance = 20 + 15 * len(tags & required)/len(required)
    evidence = assessment.score * .25 if assessment else 10
    reliability = 15 * (resolved+2)/(completed+4)
    availability = 15 / (1+max(0,start-current)/3600)
    confidence = 10 if assessment else 4
    suitability = relevance + evidence + reliability + availability + confidence
    wait = min(10, max(0,current-doubt.created_at)/3600)
    return {'suitability':round(suitability,6), 'skill_relevance':relevance,
            'assessment_evidence':evidence, 'assessment_score':assessment.score if assessment else None,
            'evidence_label':'Assessment evidence (not qualification)' if assessment else 'Provisional self-declaration',
            'reliability':reliability, 'completed_sessions':completed, 'resolved_sessions':resolved,
            'availability':availability, 'confidence':confidence, 'urgency_multiplier':URGENCY[doubt.urgency],
            'waiting_bonus':wait, 'utility':round(suitability * URGENCY[doubt.urgency]+wait,6),
            'reason':'Eligible domain and skill overlap; available grid slot satisfies the time window. '
                     'Chosen by maximum total allocation utility across this dispatch batch. '
                     'This ranking score is not a probability of resolution.'}

def participant_busy(db, person, start, end):
    return db.scalar(select(m.Session.id).join(m.DoubtRequest,m.Session.doubt_id == m.DoubtRequest.id).where(
        m.Session.state.in_(LIVE), m.Session.start < end, m.Session.end > start,
        (m.Session.mentor_id == person) | (m.DoubtRequest.requester_id == person))) is not None

def feasible(db, doubt, mentor, start, current):
    if not mentor.mentoring or doubt.requester_id == mentor.id or start < current or start % SLOT:
        return False
    if not {s.tag for s in doubt.skills} & {s.tag for s in mentor.skills if s.domain == doubt.domain}:
        return False
    if doubt.preferred_start and start < doubt.preferred_start:
        return False
    if doubt.deadline and start+SLOT > doubt.deadline:
        return False
    if not any(w.start <= start and start+SLOT <= w.end for w in mentor.availability):
        return False
    if participant_busy(db,mentor.id,start,start+SLOT) or participant_busy(db,doubt.requester_id,start,start+SLOT):
        return False
    # Avoid offering the same unresolved problem back to a mentor who could not help.
    if db.scalar(select(m.Session.id).where(m.Session.doubt_id == doubt.id, m.Session.mentor_id == mentor.id,
                    m.Session.state.in_(('DECLINED','CANCELLED')) |
                    ((m.Session.state == 'RESOLVED') & m.Session.resolved.is_(False)))):
        return False
    return True

def dispatch(db, current):
    expire(db,current)
    doubts = list(db.scalars(select(m.DoubtRequest).where(m.DoubtRequest.status.in_(('OPEN','UNMATCHED')))
                            .order_by(m.DoubtRequest.created_at,m.DoubtRequest.id)))
    mentors = list(db.scalars(select(m.Student).where(m.Student.mentoring.is_(True)).order_by(m.Student.id)))
    resources = []
    # Deliberate local-MVP horizon bounds memory and matching latency.
    for mentor in mentors:
        slots = set()
        for window in mentor.availability:
            first = ((max(window.start,current)+SLOT-1)//SLOT)*SLOT
            slots.update(range(first,min(window.end,current+7*86400)-SLOT+1,SLOT))
        resources.extend((mentor,start) for start in sorted(slots))
    require(len(doubts) <= 200 and len(resources) <= 2000, 'Dispatch batch exceeds MVP limit (200 requests / 2000 slots)', 422)
    matrix, scores, details = [], [], {}
    for i,doubt in enumerate(doubts):
        row, raw = [], []
        for j,(mentor,start) in enumerate(resources):
            if feasible(db,doubt,mentor,start,current):
                attempt = db.scalar(select(m.AssessmentAttempt).where(m.AssessmentAttempt.student_id == mentor.id,
                    m.AssessmentAttempt.domain == doubt.domain).order_by(m.AssessmentAttempt.created_at.desc(),m.AssessmentAttempt.id.desc()))
                completed,resolved = history(db,mentor.id)
                breakdown = score(doubt,mentor,start,current,attempt,completed,resolved)
                details[i,j] = breakdown
                row.append(breakdown['utility'])
                raw.append(breakdown['suitability'])
            else:
                row.append(None)
                raw.append(None)
        matrix.append(row)
        scores.append(raw)
    comparisons, chosen = {}, []
    for name, algorithm in [('optimized',maximum_weight),('greedy',greedy)]:
        tick = perf_counter()
        pairs = algorithm(matrix)
        elapsed = perf_counter()-tick
        comparisons[name] = summarize(matrix,pairs,scores,[d.urgency for d in doubts],elapsed)
        if name == 'optimized':
            chosen = pairs
    run = m.DispatchRun(result={})
    db.add(run)
    db.flush()
    assignments, rejected = [], []
    for i,j in chosen:
        doubt, (mentor,start) = doubts[i],resources[j]
        # Recheck after each insert: protects students participating in both roles.
        if not feasible(db,doubt,mentor,start,current):
            rejected.append({'doubt_id':doubt.id,'reason':'Participant conflict at final validation'})
            continue
        session = m.Session(doubt_id=doubt.id,mentor_id=mentor.id,dispatch_run_id=run.id,start=start,end=start+SLOT,
                            offer_expires_at=min(current+OFFER_TTL_SECONDS,start),explanation=details[i,j])
        db.add(session)
        db.flush()
        doubt.status, doubt.assigned_session_id = 'MATCHED',session.id
        db.flush()
        assignments.append(serialize(session))
    for doubt in doubts:
        if doubt.status != 'MATCHED':
            doubt.status = 'UNMATCHED'
    run.result = {'assignments':assignments,'comparison':comparisons,'final_validation_rejections':rejected,
                  'unassigned':[{'id':d.id,'reason':'No eligible slot' if not any(v is not None for v in matrix[i])
                                else 'Waiting: eligible capacity allocated or participant conflict'}
                                for i,d in enumerate(doubts) if d.status == 'UNMATCHED'],
                  'candidate_edges':len(details),'resource_count':len(resources)}
    return run
