"""Real question text/tags; simulated campus users; isolated in-memory SQLite only."""
import json
import os
import random
import sys
from collections import Counter
from time import perf_counter
from unittest.mock import patch
from .config import ROOT, PROCESSED, REPORTS, LABEL_DOMAINS, SEED
from .preprocess import clean_html


def run_benchmark(scenarios=30):
    # No connection to the demonstration database is opened by this experiment.
    sys.path.insert(0, str(ROOT / 'backend'))
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app import models as m, services as svc
    from app.database import Base
    from app.algorithms import maximum_weight, greedy, summarize
    rng = random.Random(SEED)
    questions = []
    for name in ('train', 'validation', 'test'):
        questions.extend(json.loads((PROCESSED / f'{name}.json').read_text(encoding='utf-8')))
    questions = [q for q in questions if q['labels']]
    now = 1795482000  # fixed timestamp, aligned below; never use live clock
    now = (now // 900) * 900
    results = []
    for scenario in range(scenarios):
        n, mentors = rng.randint(5, 20), rng.randint(3, 14)
        selected = rng.sample(questions, n)
        people = [{'id': f'p-{i}', 'name': f'Simulated {i}', 'mentoring': i < mentors,
                   'labels': rng.sample(sorted(LABEL_DOMAINS), rng.randint(1, 5)),
                   'available': rng.random() < .8, 'offset': rng.choice([900, 1800, 2700])}
                  for i in range(mentors + n)]
        doubts = []
        for i, q in enumerate(selected):
            counts = Counter(LABEL_DOMAINS[label] for label in q['labels'])
            domain = max(sorted(counts), key=counts.get)
            doubts.append({'id': f'q-{i}', 'source_id': q['id'], 'source_url': q['url'],
                           'requester': f'p-{rng.randrange(mentors)}' if rng.random() < .25 else f'p-{mentors+i}',
                           'title': clean_html(q['title']), 'description': clean_html(q['body']), 'domain': domain,
                           'tags': [label for label in q['labels'] if LABEL_DOMAINS[label] == domain],
                           'urgency': rng.choice(['Urgent', 'Normal', 'Flexible']),
                           'created_at': now - rng.randrange(0, 18000), 'deadline': now + rng.choice([1800, 2700, 4500])})
        entry = {'scenario': scenario, 'request_count': n, 'mentor_count': mentors,
                 'source_question_ids': [q['source_id'] for q in doubts]}
        for name, solver in [('hungarian', maximum_weight), ('greedy', greedy)]:
            engine = create_engine('sqlite://')
            Base.metadata.create_all(engine)
            with Session(engine) as db:
                for p in people:
                    student = m.Student(id=p['id'], name=p['name'], mentoring=p['mentoring'], points_balance=100)
                    student.skills = [m.StudentSkill(domain=LABEL_DOMAINS[label], tag=label, level=3) for label in p['labels']]
                    if p['available'] and p['mentoring']:
                        student.availability = [m.AvailabilityWindow(start=now+p['offset'], end=now+p['offset']+1800)]
                    db.add(student)
                db.flush()
                for d in doubts:
                    doubt = m.DoubtRequest(id=d['id'], requester_id=d['requester'], title=d['title'], description=d['description'],
                        domain=d['domain'], urgency=d['urgency'], bounty=0, created_at=d['created_at'],
                        preferred_start=now+900, deadline=d['deadline'], status='OPEN')
                    doubt.skills = [m.DoubtSkill(tag=tag) for tag in d['tags']]
                    db.add(doubt)
                db.commit()
                captured = []
                def capture(matrix):
                    if not captured:
                        captured.append([list(row) for row in matrix])
                    return solver(matrix)
                tick = perf_counter()
                with patch.object(svc, 'maximum_weight', capture):
                    run = svc.dispatch(db, now)
                if name == 'greedy' and captured:
                    assert captured[0] == matrix, 'Integrated solvers must start from identical candidate matrices'
                db.commit()
                elapsed = (perf_counter() - tick) * 1000
                sessions = list(db.scalars(select(m.Session)))
                actual_doubts = {d.id: d for d in db.scalars(select(m.DoubtRequest))}
                urgent = sum(d['urgency'] == 'Urgent' for d in doubts)
                invalid, conflicts = 0, 0
                for s in sessions:
                    doubt = actual_doubts[s.doubt_id]
                    mentor = db.get(m.Student, s.mentor_id)
                    invalid += int(not mentor.mentoring or mentor.id == doubt.requester_id
                        or not set(x.tag for x in doubt.skills).intersection(x.tag for x in mentor.skills if x.domain == doubt.domain)
                        or s.start < doubt.preferred_start or s.end > doubt.deadline
                        or not any(w.start <= s.start and s.end <= w.end for w in mentor.availability))
                for i, a in enumerate(sessions):
                    participants = {a.mentor_id, actual_doubts[a.doubt_id].requester_id}
                    for b in sessions[i+1:]:
                        conflicts += int(a.start < b.end and b.start < a.end and bool(participants & {b.mentor_id, actual_doubts[b.doubt_id].requester_id}))
                entry[name] = {'total_utility': sum(s.explanation['utility'] for s in sessions),
                    'assignments': len(sessions), 'unassigned': n-len(sessions), 'invalid_assignments': invalid,
                    'cross_role_booking_conflicts': conflicts, 'persisted_assignments': len(sessions),
                    'urgent_assignment_rate': sum(actual_doubts[s.doubt_id].urgency == 'Urgent' for s in sessions) / urgent if urgent else None,
                    'dispatch_runtime_ms': elapsed, 'final_validation_rejections': len(run.result['final_validation_rejections'])}
                if name == 'hungarian' and captured:
                    matrix = captured[0]
                    ordered = sorted(doubts, key=lambda d: (d['created_at'], d['id']))
                    entry['shared_matrix'] = {}
                    for algorithm_name, algorithm in [('hungarian', maximum_weight), ('greedy', greedy)]:
                        tick = perf_counter(); pairs = algorithm(matrix); elapsed_solver = perf_counter()-tick
                        entry['shared_matrix'][algorithm_name] = summarize(matrix, pairs, matrix, [d['urgency'] for d in ordered], elapsed_solver)
                        # summarize's suitability field here is utility; omit the misleading duplicate.
                        entry['shared_matrix'][algorithm_name].pop('average_suitability')
            engine.dispose()
        results.append(entry)
        print(f'Allocation scenario {scenario+1}/{scenarios}', flush=True)
    summary = {'scenarios': scenarios, 'seed': SEED, 'fields': 'Real question text/tags; all profiles, skills, scheduling, and urgency simulated.',
               'interpretation': 'Utility measures the existing heuristic objective, not academic learning outcomes.'}
    for name in ('hungarian', 'greedy'):
        summary[name] = {key: sum(r[name][key] for r in results) for key in
                         ('total_utility', 'assignments', 'unassigned', 'persisted_assignments', 'invalid_assignments', 'cross_role_booking_conflicts', 'final_validation_rejections')}
        summary[name]['mean_dispatch_runtime_ms'] = sum(r[name]['dispatch_runtime_ms'] for r in results)/scenarios
        rates = [r[name]['urgent_assignment_rate'] for r in results if r[name]['urgent_assignment_rate'] is not None]
        summary[name]['mean_scenario_urgent_assignment_rate'] = sum(rates)/len(rates) if rates else None
        summary[name]['shared_matrix_total_utility'] = sum(r.get('shared_matrix', {}).get(name, {}).get('total_utility', 0) for r in results)
        summary[name]['mean_solver_runtime_ms'] = sum(r.get('shared_matrix', {}).get(name, {}).get('runtime_ms', 0) for r in results)/scenarios
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'allocation_benchmark.json').write_text(json.dumps({'summary': summary, 'scenarios': results}, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    run_benchmark()
