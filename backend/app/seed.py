"""Synthetic, relative-time demo data with realistic academic domains and scenario datasets.
Reset: python -m app.seed --reset
"""
import argparse
from sqlalchemy import select
from .database import Base, engine, transaction
from . import models as m
from .config import DOMAINS, SLOT, ALLOW_DATABASE_RESET

BANKS = {
 'Python': [
  ('Which value is immutable?', ['list', 'dict', 'tuple', 'set'], 2),
  ('What is len([1, 2, 3])?', ['2', '3', '4', '0'], 1),
  ('Which keyword handles exceptions?', ['catch', 'try', 'error', 'handle'], 1),
  ('What does range(3) produce?', ['0,1,2', '1,2,3', '0,1,2,3', '3'], 0),
  ('Which checks equality?', ['=', '==', ':=', '=>'], 1)
 ],
 'JavaScript': [
  ('Which declares a block-scoped variable?', ['var', 'let', 'define', 'global'], 1),
  ('What does === compare?', ['Value only', 'Type only', 'Value and type', 'Object contents recursively'], 2),
  ('What does an async function return?', ['Promise', 'Thread', 'Always undefined', 'Iterator'], 0),
  ('Which transforms each array element?', ['filter', 'map', 'find', 'some'], 1),
  ('Which value is falsy?', ['[]', '{}', '0', '"false"'], 2)
 ],
 'SQL': [
  ('Which clause filters rows before grouping?', ['HAVING', 'WHERE', 'ORDER BY', 'LIMIT'], 1),
  ('Which JOIN retains every left row?', ['INNER JOIN', 'LEFT JOIN', 'CROSS JOIN', 'RIGHT JOIN'], 1),
  ('Which counts all rows?', ['COUNT(*)', 'SUM(*)', 'TOTAL(*)', 'ROWS()'], 0),
  ('Which clause filters groups?', ['WHERE', 'HAVING', 'FROM', 'SELECT'], 1),
  ('Which constraint ensures unique row identity?', ['DEFAULT', 'PRIMARY KEY', 'CHECK only', 'NULL'], 1)
 ]
}

def seed(db):
    if db.scalar(select(m.Student.id).limit(1)):
        return
    for domain, bank in BANKS.items():
        for i, (prompt, options, correct) in enumerate(bank):
            db.add(m.AssessmentQuestion(id=f'{domain}-{i}', domain=domain, prompt=prompt, options=options, correct=correct, version=1))
    
    # 12 diverse demo students (7 mentors, 5 seekers)
    names = ['Asha', 'Kabir', 'Meera', 'Arjun', 'Nila', 'Dev', 'Isha', 'Rohan', 'Tara', 'Vikram', 'Zoya', 'Om']
    mentor_domains = ['Python', 'Python', 'JavaScript', 'SQL', 'CAD', 'Design', 'Mathematics']
    start = ((m.now() + SLOT - 1) // SLOT) * SLOT
    
    for i, name in enumerate(names):
        student = m.Student(id=f'student-{i+1:02}', name=f'{name} (demo)', mentoring=i < 7, points_balance=150)
        db.add(student)
        db.flush()
        
        # Initial point ledger grant
        db.add(m.PointLedger(
            student_id=student.id,
            amount=150,
            transaction_type='INITIAL_GRANT',
            reference_id=f'grant:{student.id}',
            balance_after=150,
            notes='Demo account initial point allocation'
        ))

        if i < 7:
            domain = mentor_domains[i]
            for tag in DOMAINS[domain]:
                db.add(m.StudentSkill(student_id=student.id, domain=domain, tag=tag, level=2 + i % 4))
            # student-07 (Mathematics) is intentionally unavailable to test honest unmatched state
            if i != 6:
                db.add(m.AvailabilityWindow(student_id=student.id, start=start + (i % 3) * SLOT, end=start + (i % 3 + 6) * SLOT))
            if domain in BANKS and i != 1:
                attempt = m.AssessmentAttempt(student_id=student.id, domain=domain, score=80, question_count=5, correct_count=4, version=1)
                db.add(attempt)
                db.flush()
                for q, (prompt, options, correct) in enumerate(BANKS[domain]):
                    db.add(m.AssessmentResponse(attempt_id=attempt.id, question_id=f'{domain}-{q}', answer=correct if q < 4 else (correct + 1) % 4))

    db.flush()
    domains = list(DOMAINS)
    
    # Seed 18 sample doubts across domains, urgency, and bounties
    for i in range(18):
        domain = domains[i % 6]
        bounty_val = (i % 4) * 20  # 0, 20, 40, 60 points
        doubt = m.DoubtRequest(
            id=f'doubt-{i+1:02}',
            requester_id=f'student-{8+i%5:02}',
            title=f'{domain}: {DOMAINS[domain][i%len(DOMAINS[domain])]} question {i+1}',
            description='I tried a small example but need help understanding the result. Can we work through it together?',
            domain=domain,
            urgency=['Urgent', 'Normal', 'Flexible'][i % 3],
            bounty=bounty_val,
            created_at=m.now() - i * 600
        )
        db.add(doubt)
        db.flush()
        db.add(m.DoubtSkill(doubt_id=doubt.id, tag=DOMAINS[domain][0]))
        if bounty_val > 0:
            requester = db.get(m.Student, doubt.requester_id)
            requester.points_balance -= bounty_val
            db.add(m.PointLedger(
                student_id=requester.id,
                amount=-bounty_val,
                transaction_type='BOUNTY_RESERVED',
                doubt_id=doubt.id,
                reference_id=f'reserve:{doubt.id}',
                balance_after=requester.points_balance,
                notes=f'Reserved {bounty_val} points for doubt bounty'
            ))

    # Cross-role conflict scenario seed: student-02 (Python mentor) also seeks JavaScript help
    cross_doubt = m.DoubtRequest(
        id='cross-role-doubt',
        requester_id='student-02',
        title='JavaScript: async Promise chain issue',
        description='Need help chaining async functions in Node.js without unhandled rejections.',
        domain='JavaScript',
        urgency='Urgent',
        bounty=30,
        created_at=m.now() - 300
    )
    db.add(cross_doubt)
    db.flush()
    db.add(m.DoubtSkill(doubt_id=cross_doubt.id, tag='async'))
    s02 = db.get(m.Student, 'student-02')
    s02.points_balance -= 30
    db.add(m.PointLedger(
        student_id='student-02',
        amount=-30,
        transaction_type='BOUNTY_RESERVED',
        doubt_id=cross_doubt.id,
        reference_id=f'reserve:{cross_doubt.id}',
        balance_after=s02.points_balance,
        notes='Reserved 30 points for JavaScript cross-role doubt'
    ))

    # Persisted historical records with genuine ratings
    for i in range(3):
        doubt = m.DoubtRequest(
            id=f'history-{i}',
            requester_id='student-12',
            title='Previous Python help',
            description='Synthetic historical session',
            domain='Python',
            urgency='Normal',
            bounty=25,
            status='RESOLVED' if i < 2 else 'OPEN'
        )
        db.add(doubt)
        db.flush()
        db.add(m.DoubtSkill(doubt_id=doubt.id, tag='python'))
        session = m.Session(
            doubt_id=doubt.id,
            mentor_id='student-01',
            start=start - (8 + i) * SLOT,
            end=start - (7 + i) * SLOT,
            state='RESOLVED',
            offer_expires_at=start - 10 * SLOT,
            mentor_completed=True,
            resolved=i < 2,
            notes='Synthetic demonstration history',
            explanation={'evidence_label': 'Seeded historical record'}
        )
        db.add(session)
        db.flush()
        if i < 2:
            doubt.assigned_session_id = session.id
            db.add(m.PointLedger(
                student_id='student-01',
                amount=25,
                transaction_type='BOUNTY_AWARDED',
                doubt_id=doubt.id,
                session_id=session.id,
                reference_id=f'award:{session.id}',
                balance_after=175,
                notes='Awarded 25 points for resolved doubt'
            ))
        db.add(m.SessionFeedback(session_id=session.id, student_id='student-12', rating=4 if i < 2 else 2, notes='Seeded demo feedback'))
        
        # Seed sample messages in historical sessions
        db.add(m.SessionMessage(session_id=session.id, sender_id='student-12', content='Hi Asha! Could you check my loop structure?'))
        db.add(m.SessionMessage(session_id=session.id, sender_id='student-01', content='Sure, you are modifying the list in-place while iterating.'))

        # Seed sample meeting, snippets and resolution for history-0
        if i == 0:
            db.add(m.SessionMeeting(
                session_id=session.id,
                meeting_url='https://meet.google.com/abc-defg-hij',
                attached_by_id='student-01',
                attached_at=start - 8 * SLOT,
                updated_at=start - 8 * SLOT
            ))
            snip_orig = m.SessionCodeSnippet(
                id=f'snip-orig-{i}',
                session_id=session.id,
                author_id='student-12',
                title='Mutating list during iteration',
                filename='filter_items.py',
                language='python',
                content='def remove_evens(nums):\n    for n in nums:\n        if n % 2 == 0:\n            nums.remove(n)\n    return nums',
                snippet_type='ORIGINAL',
                created_at=start - 8 * SLOT
            )
            db.add(snip_orig)
            db.flush()
            snip_fix = m.SessionCodeSnippet(
                id=f'snip-fix-{i}',
                session_id=session.id,
                author_id='student-01',
                title='List comprehension fix',
                filename='filter_items.py',
                language='python',
                content='def remove_evens(nums):\n    # Do not mutate list in-place while iterating\n    return [n for n in nums if n % 2 != 0]',
                snippet_type='PROPOSED_FIX',
                parent_snippet_id=snip_orig.id,
                created_at=start - 7 * SLOT
            )
            db.add(snip_fix)
            db.flush()
            db.add(m.SessionResolution(
                session_id=session.id,
                doubt_id=doubt.id,
                mentor_id='student-01',
                requester_id='student-12',
                root_cause='Modifying a Python list with .remove() during active for-loop iteration skips elements because the internal iteration index advances while the list shrinks.',
                solution_explanation='Replaced the mutating for-loop with a clean list comprehension [n for n in nums if n % 2 != 0], creating a filtered copy without index skipping.',
                follow_up_steps='For large collections where memory is constrained, consider using itertools.filterfalse or generator expressions.',
                original_snippet_id=snip_orig.id,
                corrected_snippet_id=snip_fix.id,
                reference_urls=['https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions'],
                created_at=start - 7 * SLOT,
                updated_at=start - 7 * SLOT,
                submitted_at=start - 7 * SLOT,
                confirmed_at=start - 7 * SLOT,
                requester_status='CONFIRMED_RESOLVED'
            ))


def initialize():
    Base.metadata.create_all(engine)
    with transaction() as db:
        seed(db)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()
    if args.reset:
        if not ALLOW_DATABASE_RESET:
            raise RuntimeError(
                'Database reset is disabled (ALLOW_DATABASE_RESET=false). '
                'Set ALLOW_DATABASE_RESET=true if this destructive operation is intentional.'
            )
        with engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
            Base.metadata.drop_all(connection)
            connection.commit()
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    initialize()
    print('Synthetic demo database initialized.')
