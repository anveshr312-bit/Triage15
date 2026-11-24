"""Synthetic, relative-time demo data. Reset: python -m app.seed --reset."""
import argparse
from sqlalchemy import select
from .database import Base, engine, transaction
from . import models as m
from .config import DOMAINS, SLOT

BANKS = {
 'Python':[
  ('Which value is immutable?', ['list','dict','tuple','set'],2),
  ('What is len([1, 2, 3])?', ['2','3','4','0'],1),
  ('Which keyword handles exceptions?', ['catch','try','error','handle'],1),
  ('What does range(3) produce?', ['0,1,2','1,2,3','0,1,2,3','3'],0),
  ('Which checks equality?', ['=','==',':=','=>'],1)],
 'JavaScript':[
  ('Which declares a block-scoped variable?', ['var','let','define','global'],1),
  ('What does === compare?', ['Value only','Type only','Value and type','Object contents recursively'],2),
  ('What does an async function return?', ['Promise','Thread','Always undefined','Iterator'],0),
  ('Which transforms each array element?', ['filter','map','find','some'],1),
  ('Which value is falsy?', ['[]','{}','0','"false"'],2)],
 'SQL':[
  ('Which clause filters rows before grouping?', ['HAVING','WHERE','ORDER BY','LIMIT'],1),
  ('Which JOIN retains every left row?', ['INNER JOIN','LEFT JOIN','CROSS JOIN','RIGHT JOIN'],1),
  ('Which counts all rows?', ['COUNT(*)','SUM(*)','TOTAL(*)','ROWS()'],0),
  ('Which clause filters groups?', ['WHERE','HAVING','FROM','SELECT'],1),
  ('Which constraint ensures unique row identity?', ['DEFAULT','PRIMARY KEY','CHECK only','NULL'],1)]}

def seed(db):
    if db.scalar(select(m.Student.id).limit(1)):
        return
    for domain,bank in BANKS.items():
        for i,(prompt,options,correct) in enumerate(bank):
            db.add(m.AssessmentQuestion(id=f'{domain}-{i}',domain=domain,prompt=prompt,options=options,correct=correct,version=1))
    names = ['Asha','Kabir','Meera','Arjun','Nila','Dev','Isha','Rohan','Tara','Vikram','Zoya','Om']
    mentor_domains = ['Python','Python','JavaScript','SQL','CAD','Design','Mathematics']
    start = ((m.now()+SLOT-1)//SLOT)*SLOT
    for i,name in enumerate(names):
        student = m.Student(id=f'student-{i+1:02}',name=f'{name} (demo)',mentoring=i<7)
        db.add(student)
        db.flush()
        if i < 7:
            domain = mentor_domains[i]
            for tag in DOMAINS[domain]:
                db.add(m.StudentSkill(student_id=student.id,domain=domain,tag=tag,level=2+i%4))
            # Mathematics mentor is intentionally unavailable.
            if i != 6:
                db.add(m.AvailabilityWindow(student_id=student.id,start=start+(i%3)*SLOT,end=start+(i%3+6)*SLOT))
            if domain in BANKS and i != 1:
                attempt = m.AssessmentAttempt(student_id=student.id,domain=domain,score=80,question_count=5,correct_count=4,version=1)
                db.add(attempt)
                db.flush()
                for q,(prompt,options,correct) in enumerate(BANKS[domain]):
                    db.add(m.AssessmentResponse(attempt_id=attempt.id,question_id=f'{domain}-{q}',answer=correct if q<4 else (correct+1)%4))
    db.flush()
    domains = list(DOMAINS)
    for i in range(18):
        domain = domains[i%6]
        doubt = m.DoubtRequest(id=f'doubt-{i+1:02}',requester_id=f'student-{8+i%5:02}',
                              title=f'{domain}: {DOMAINS[domain][i%len(DOMAINS[domain])]} question {i+1}',
                              description='I tried a small example but need help understanding the result. Can we work through it?',
                              domain=domain,urgency=['Urgent','Normal','Flexible'][i%3],created_at=m.now()-i*600)
        db.add(doubt)
        db.flush()
        db.add(m.DoubtSkill(doubt_id=doubt.id,tag=DOMAINS[domain][0]))
    # Actual persisted historical records; no fabricated rating counters.
    for i in range(3):
        doubt = m.DoubtRequest(id=f'history-{i}',requester_id='student-12',title='Previous Python help',
                              description='Synthetic historical session',domain='Python',urgency='Normal',status='RESOLVED' if i<2 else 'OPEN')
        db.add(doubt)
        db.flush()
        db.add(m.DoubtSkill(doubt_id=doubt.id,tag='python'))
        session = m.Session(doubt_id=doubt.id,mentor_id='student-01',start=start-(8+i)*SLOT,end=start-(7+i)*SLOT,
                            state='RESOLVED',offer_expires_at=start-10*SLOT,mentor_completed=True,resolved=i<2,
                            notes='Synthetic demonstration history',explanation={'evidence_label':'Seeded historical record'})
        db.add(session)
        db.flush()
        if i<2:
            doubt.assigned_session_id=session.id
        db.add(m.SessionFeedback(session_id=session.id,student_id='student-12',rating=4 if i<2 else 2,notes='Seeded demo feedback'))

def initialize():
    Base.metadata.create_all(engine)
    with transaction() as db:
        seed(db)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset',action='store_true')
    args = parser.parse_args()
    if args.reset:
        # Explicit reset command is intentionally destructive to this local demo database.
        with engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
            Base.metadata.drop_all(connection)
            connection.commit()
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    initialize()
    print('Synthetic demo database initialized.')
