from datetime import datetime, timezone
import difflib
from time import perf_counter
from fastapi import HTTPException
from sqlalchemy import select, and_, or_
from . import models as m
from . import config as cfg
from .algorithms import maximum_weight, greedy, summarize
from .config import SLOT, OFFER_TTL_SECONDS, URGENCY

LIVE = ('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION')

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
    data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for key in ('start','end','created_at','preferred_start','deadline','offer_expires_at',
                'accepted_at','actual_started_at','mentor_completed_at','outcome_deadline','completed_at',
                'attached_at','updated_at','submitted_at','confirmed_at'):
        if key in data:
            data[key] = iso(data[key])
    if isinstance(obj, m.DoubtRequest):
        data['skills'] = [s.tag for s in obj.skills]
    if isinstance(obj, m.Student):
        data['skills'] = [serialize(s) for s in obj.skills]
        data['availability'] = [serialize(a) for a in obj.availability]
    return data

def compute_snippet_diff(original_text: str, proposed_text: str) -> dict:
    orig_lines = original_text.splitlines()
    prop_lines = proposed_text.splitlines()
    matcher = difflib.SequenceMatcher(None, orig_lines, prop_lines)
    
    diff_lines = []
    added_count = 0
    removed_count = 0
    unchanged_count = 0
    
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'equal':
            for line in orig_lines[a0:a1]:
                diff_lines.append({'type': 'unchanged', 'text': line})
                unchanged_count += 1
        elif opcode == 'insert':
            for line in prop_lines[b0:b1]:
                diff_lines.append({'type': 'added', 'text': line})
                added_count += 1
        elif opcode == 'delete':
            for line in orig_lines[a0:a1]:
                diff_lines.append({'type': 'removed', 'text': line})
                removed_count += 1
        elif opcode == 'replace':
            for line in orig_lines[a0:a1]:
                diff_lines.append({'type': 'removed', 'text': line})
                removed_count += 1
            for line in prop_lines[b0:b1]:
                diff_lines.append({'type': 'added', 'text': line})
                added_count += 1
                
    return {
        'lines': diff_lines,
        'added_count': added_count,
        'removed_count': removed_count,
        'unchanged_count': unchanged_count,
    }


# --- BOUNTY & REWARD LEDGER SERVICES ---

def reserve_bounty(db, student, doubt_id, amount):
    if not amount or amount <= 0:
        return
    require(student.points_balance >= amount, 'Insufficient point balance to reserve bounty', 422)
    student.points_balance -= amount
    ref = f'reserve:{doubt_id}'
    # Ensure idempotency
    existing = db.scalar(select(m.PointLedger.id).where(m.PointLedger.reference_id == ref))
    if existing:
        return
    ledger = m.PointLedger(
        student_id=student.id,
        amount=-amount,
        transaction_type='BOUNTY_RESERVED',
        doubt_id=doubt_id,
        reference_id=ref,
        balance_after=student.points_balance,
        notes=f'Reserved {amount} points for doubt bounty'
    )
    db.add(ledger)
    db.flush()

def award_bounty(db, mentor, session, doubt):
    """Award platform base reward (10 pts) and transfer any optional requester-funded bounty."""
    base_amount = getattr(cfg, 'RESOLUTION_BASE_REWARD', 10)
    base_ref = f'base_reward:{session.id}'
    existing_base = db.scalar(select(m.PointLedger.id).where(m.PointLedger.reference_id == base_ref))
    if not existing_base:
        mentor.points_balance += base_amount
        ledger_base = m.PointLedger(
            student_id=mentor.id,
            amount=base_amount,
            transaction_type='BASE_REWARD',
            doubt_id=doubt.id,
            session_id=session.id,
            reference_id=base_ref,
            balance_after=mentor.points_balance,
            notes=f'Base platform reward of {base_amount} points for confirmed resolution'
        )
        db.add(ledger_base)
        db.flush()

    if doubt.bounty and doubt.bounty > 0:
        ref = f'award:{session.id}'
        existing = db.scalar(select(m.PointLedger.id).where(m.PointLedger.reference_id == ref))
        if not existing:
            mentor.points_balance += doubt.bounty
            ledger = m.PointLedger(
                student_id=mentor.id,
                amount=doubt.bounty,
                transaction_type='BOUNTY_AWARDED',
                doubt_id=doubt.id,
                session_id=session.id,
                reference_id=ref,
                balance_after=mentor.points_balance,
                notes=f'Awarded {doubt.bounty} points for resolving doubt'
            )
            db.add(ledger)
            db.flush()

def refund_bounty(db, doubt, reason='cancelled'):
    if not doubt.bounty or doubt.bounty <= 0:
        return
    ref = f'refund:{doubt.id}'
    existing = db.scalar(select(m.PointLedger.id).where(m.PointLedger.reference_id == ref))
    if existing:
        return  # Prevent duplicate refund
    requester = get(db, m.Student, doubt.requester_id)
    requester.points_balance += doubt.bounty
    ledger = m.PointLedger(
        student_id=requester.id,
        amount=doubt.bounty,
        transaction_type='BOUNTY_REFUNDED',
        doubt_id=doubt.id,
        reference_id=ref,
        balance_after=requester.points_balance,
        notes=f'Refunded {doubt.bounty} points ({reason})'
    )
    db.add(ledger)
    db.flush()

def adjust_bounty(db, student, doubt, new_bounty):
    delta = new_bounty - doubt.bounty
    if delta == 0:
        return
    if delta > 0:
        require(student.points_balance >= delta, 'Insufficient points to increase bounty', 422)
        student.points_balance -= delta
    else:
        student.points_balance += abs(delta)
    doubt.bounty = new_bounty
    ref = f'adjust:{doubt.id}:{m.now()}'
    ledger = m.PointLedger(
        student_id=student.id,
        amount=-delta,
        transaction_type='BOUNTY_ADJUSTED',
        doubt_id=doubt.id,
        reference_id=ref,
        balance_after=student.points_balance,
        notes=f'Adjusted bounty for doubt to {new_bounty}'
    )
    db.add(ledger)
    db.flush()

# --- LIFECYCLE & DISPATCH SERVICES ---

def release(db, session, state):
    session.state = state
    session.completed_at = m.now()
    doubt = get(db, m.DoubtRequest, session.doubt_id)
    doubt.status, doubt.assigned_session_id = 'OPEN', None

def expire(db, current):
    expired_any = False
    for session in db.scalars(select(m.Session).where(m.Session.state == 'OFFERED', m.Session.offer_expires_at <= current)):
        release(db, session, 'EXPIRED')
        expired_any = True
    # Also check sessions in AWAITING_CONFIRMATION whose outcome_deadline has passed
    for session in db.scalars(select(m.Session).where(m.Session.state == 'AWAITING_CONFIRMATION', m.Session.outcome_deadline.is_not(None), m.Session.outcome_deadline <= current)):
        session.state = 'EXPIRED'
        session.completed_at = current
        doubt = get(db, m.DoubtRequest, session.doubt_id)
        doubt.status, doubt.assigned_session_id = 'CANCELLED', None
        refund_bounty(db, doubt, reason='confirmation_deadline_expired')
        expired_any = True
    db.flush()
    return expired_any

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
    # Bounties add slight priority boost (capped at 5 utility points) without overriding suitability
    bounty_bonus = min(5.0, (doubt.bounty or 0) * 0.05)
    return {'suitability':round(suitability,6), 'skill_relevance':relevance,
            'assessment_evidence':evidence, 'assessment_score':assessment.score if assessment else None,
            'evidence_label':'Assessment evidence (not qualification)' if assessment else 'Provisional self-declaration',
            'reliability':reliability, 'completed_sessions':completed, 'resolved_sessions':resolved,
            'availability':availability, 'confidence':confidence, 'urgency_multiplier':URGENCY[doubt.urgency],
            'waiting_bonus':wait, 'bounty_bonus':bounty_bonus,
            'utility':round(suitability * URGENCY[doubt.urgency] + wait + bounty_bonus, 6),
            'reason':'Eligible domain and skill overlap; available grid slot satisfies the time window. '
                     'Chosen by maximum total allocation utility across this dispatch batch. '
                     'This ranking score is not a probability of resolution.'}

def participant_busy(db, person, start, end):
    return db.scalar(select(m.Session.id).join(m.DoubtRequest, m.Session.doubt_id == m.DoubtRequest.id).where(
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
    if participant_busy(db, mentor.id, start, start+SLOT) or participant_busy(db, doubt.requester_id, start, start+SLOT):
        return False
    # Avoid offering the same unresolved problem back to a mentor who declined, cancelled, or failed it
    if db.scalar(select(m.Session.id).where(m.Session.doubt_id == doubt.id, m.Session.mentor_id == mentor.id,
                    m.Session.state.in_(('DECLINED','CANCELLED')) |
                    ((m.Session.state == 'RESOLVED') & m.Session.resolved.is_(False)))):
        return False
    return True

# --- MANUAL CLAIMING ---

def claim_doubt(db, doubt_id, mentor_id, current, slot_start=None):
    doubt = get(db, m.DoubtRequest, doubt_id)
    mentor = get(db, m.Student, mentor_id)
    require(doubt.status in ('OPEN','UNMATCHED'), 'Doubt is not open for claiming', 409)
    require(mentor.mentoring, 'Student has not opted into mentoring', 422)
    require(mentor.id != doubt.requester_id, 'Cannot claim your own doubt', 422)
    
    mentor_tags = {s.tag for s in mentor.skills if s.domain == doubt.domain}
    doubt_tags = {s.tag for s in doubt.skills}
    require(bool(mentor_tags & doubt_tags), 'Mentor does not have matching skills for this doubt', 422)
    
    feasible_slot = None
    if slot_start is not None:
        if feasible(db, doubt, mentor, slot_start, current):
            feasible_slot = slot_start
    else:
        slots = set()
        for window in mentor.availability:
            first = ((max(window.start, current) + SLOT - 1) // SLOT) * SLOT
            slots.update(range(first, min(window.end, current + 7 * 86400) - SLOT + 1, SLOT))
        for s in sorted(slots):
            if feasible(db, doubt, mentor, s, current):
                feasible_slot = s
                break
                
    require(feasible_slot is not None, 'Mentor has no feasible availability window for this doubt', 409)
    
    session = m.Session(
        doubt_id=doubt.id,
        mentor_id=mentor.id,
        start=feasible_slot,
        end=feasible_slot + SLOT,
        state='ACCEPTED',
        accepted_at=current,
        offer_expires_at=feasible_slot,
        explanation={
            'reason': 'Manually claimed by eligible mentor.',
            'suitability': 100.0,
            'evidence_label': 'Direct claim by mentor',
            'utility': 100.0
        }
    )
    db.add(session)
    db.flush()
    doubt.status = 'MATCHED'
    doubt.assigned_session_id = session.id
    db.flush()
    return session

# --- DISPATCH WITH ITERATIVE CONFLICT RECOVERY (P1.1) ---

def dispatch(db, current, max_recovery_iterations=3):
    expire(db, current)
    doubts = list(db.scalars(select(m.DoubtRequest).where(m.DoubtRequest.status.in_(('OPEN','UNMATCHED')))
                            .order_by(m.DoubtRequest.created_at, m.DoubtRequest.id)))
    mentors = list(db.scalars(select(m.Student).where(m.Student.mentoring.is_(True)).order_by(m.Student.id)))
    resources = []
    for mentor in mentors:
        slots = set()
        for window in mentor.availability:
            first = ((max(window.start,current)+SLOT-1)//SLOT)*SLOT
            slots.update(range(first,min(window.end,current+7*86400)-SLOT+1,SLOT))
        resources.extend((mentor,start) for start in sorted(slots))
    require(len(doubts) <= 200 and len(resources) <= 2000, 'Dispatch batch exceeds MVP limit (200 requests / 2000 slots)', 422)
    
    run = m.DispatchRun(result={})
    db.add(run)
    db.flush()

    assignments = []
    all_rejections = []
    excluded_pairs = set()  # (doubt_id, mentor_id, slot_start)
    comparisons = {}
    recovery_iterations = 0
    recovered_count = 0

    while recovery_iterations < max_recovery_iterations:
        active_doubts = [d for d in doubts if d.status in ('OPEN','UNMATCHED')]
        if not active_doubts or not resources:
            break

        matrix, scores, details = [], [], {}
        for i, doubt in enumerate(active_doubts):
            row, raw = [], []
            for j, (mentor, start) in enumerate(resources):
                if (doubt.id, mentor.id, start) not in excluded_pairs and feasible(db, doubt, mentor, start, current):
                    attempt = db.scalar(select(m.AssessmentAttempt).where(m.AssessmentAttempt.student_id == mentor.id,
                        m.AssessmentAttempt.domain == doubt.domain).order_by(m.AssessmentAttempt.created_at.desc(), m.AssessmentAttempt.id.desc()))
                    completed, resolved = history(db, mentor.id)
                    breakdown = score(doubt, mentor, start, current, attempt, completed, resolved)
                    details[i, j] = breakdown
                    row.append(breakdown['utility'])
                    raw.append(breakdown['suitability'])
                else:
                    row.append(None)
                    raw.append(None)
            matrix.append(row)
            scores.append(raw)

        if recovery_iterations == 0:
            for name, algorithm in [('optimized', maximum_weight), ('greedy', greedy)]:
                tick = perf_counter()
                pairs = algorithm(matrix)
                elapsed = perf_counter() - tick
                comparisons[name] = summarize(matrix, pairs, scores, [d.urgency for d in active_doubts], elapsed)
            chosen = maximum_weight(matrix)
        else:
            chosen = maximum_weight(matrix)

        if not chosen:
            break

        new_assignments_this_iter = 0
        iteration_rejections = []

        for i, j in chosen:
            doubt = active_doubts[i]
            mentor, start = resources[j]
            # Final validation check before DB insert
            if not feasible(db, doubt, mentor, start, current):
                reason = 'Participant conflict at final validation'
                iteration_rejections.append({'doubt_id': doubt.id, 'mentor_id': mentor.id, 'start': start, 'reason': reason})
                excluded_pairs.add((doubt.id, mentor.id, start))
                continue

            session = m.Session(
                doubt_id=doubt.id,
                mentor_id=mentor.id,
                dispatch_run_id=run.id,
                start=start,
                end=start+SLOT,
                offer_expires_at=min(current+OFFER_TTL_SECONDS, start),
                explanation=details[i, j]
            )
            db.add(session)
            db.flush()
            doubt.status, doubt.assigned_session_id = 'MATCHED', session.id
            db.flush()
            assignments.append(serialize(session))
            new_assignments_this_iter += 1

        all_rejections.extend(iteration_rejections)
        recovery_iterations += 1

        if recovery_iterations > 1:
            recovered_count += new_assignments_this_iter

        # If no rejections occurred, the assignment set was completely clean
        if not iteration_rejections:
            break

    for doubt in doubts:
        if doubt.status != 'MATCHED':
            doubt.status = 'UNMATCHED'

    run.result = {
        'assignments': assignments,
        'comparison': comparisons,
        'final_validation_rejections': all_rejections,
        'recovery_iterations': recovery_iterations,
        'recovered_assignments': recovered_count,
        'unassigned': [{'id': d.id, 'reason': 'No eligible slot' if not any((d.id, m_cand.id, s_cand) not in excluded_pairs and feasible(db, d, m_cand, s_cand, current) for (m_cand, s_cand) in resources)
                       else 'Waiting: eligible capacity allocated or participant conflict'}
                       for d in doubts if d.status == 'UNMATCHED'],
        'candidate_edges': len(details) if 'details' in locals() else 0,
        'resource_count': len(resources)
    }
    return run
