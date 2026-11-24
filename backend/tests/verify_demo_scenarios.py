"""
Verification script for judge demonstration scenarios.
Validates ML suggestions, mathematical feature attributions,
and legitimate Hungarian matching / manual claim eligibility.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from app.database import SessionLocal
from app import models as m, services
from ml.predictor import predictor
from sqlalchemy import select

SCENARIOS = [
    {
        'id': 'Demo 01',
        'judge': 'Vishal Dhakad (Product & Frontend)',
        'mentor_id': 'student-02',
        'domain': 'JavaScript',
        'expected_tags': ['react', 'javascript'],
        'title': 'React dashboard displays stale data',
        'desc': 'My dashboard displays stale data after an API update. How should I refresh state without repeatedly fetching in React with JavaScript?'
    },
    {
        'id': 'Demo 02',
        'judge': 'Yash Jain (Software & Database)',
        'mentor_id': 'student-01',
        'domain': 'SQL',
        'expected_tags': ['sql', 'joins'],
        'title': 'SQL query returns duplicate transaction records',
        'desc': 'A retry of my reward-settlement request can produce duplicate transactions. My SQL join query returns duplicate transaction records after joining accounts and payments tables.'
    },
    {
        'id': 'Demo 03',
        'judge': 'Harsh Jain (Backend Engineering)',
        'mentor_id': 'student-04',
        'domain': 'SQL',
        'expected_tags': ['sql', 'aggregation'],
        'title': 'SQL aggregation produces incorrect counts after join',
        'desc': 'My SQL aggregation counts duplicate rows after joining two tables. How can I correct the query to get accurate count and sum?'
    },
    {
        'id': 'Demo 04',
        'judge': 'Arushi Sthapak (Applied AI)',
        'mentor_id': 'student-08',
        'domain': 'Python',
        'expected_tags': ['python', 'pandas'],
        'title': 'Missing values in pandas dataframe before model training',
        'desc': 'My Python pandas dataframe contains missing values before classification. How can I preprocess it without leaking information from the test set?'
    },
    {
        'id': 'Demo 05',
        'judge': 'Manas Arora (Machine Learning)',
        'mentor_id': 'student-03',
        'domain': 'Python',
        'expected_tags': ['python', 'pandas'],
        'title': 'TF-IDF data leakage during model evaluation in Python',
        'desc': 'My Python text classifier gets much better validation scores when I fit TF-IDF before splitting the dataset. Is this data leakage in pandas and Python?'
    },
    {
        'id': 'Demo 06',
        'judge': 'Shriyash Beohar (Applied ML & Infrastructure)',
        'mentor_id': 'student-06',
        'domain': 'Python',
        'expected_tags': ['python'],
        'title': 'Python FastAPI endpoint blocks while performing heavy task',
        'desc': 'My Python FastAPI endpoint blocks while performing a CPU-heavy task. How can I avoid blocking the server and fix latency debugging in Python?'
    }
]

def verify_all():
    print("=" * 70)
    print("TRIAGE15 — DEMONSTRATION SCENARIOS VERIFICATION")
    print("=" * 70)

    with SessionLocal() as db:
        now = m.now()
        start_slot = ((now + 900 - 1) // 900) * 900

        all_passed = True
        for sc in SCENARIOS:
            print(f"\n--- [{sc['id']}] {sc['judge']} ---")
            mentor = db.get(m.Student, sc['mentor_id'])
            assert mentor is not None, f"Mentor {sc['mentor_id']} not found!"

            # 1. ML Prediction & Feature Attributions
            ml_res = predictor.predict(sc['title'], sc['desc'])
            suggestions = ml_res.get('suggestions', [])
            suggested_tags = [s['label'] for s in suggestions]
            print(f"  ML Predicted Tags: {suggested_tags}")
            for tag in sc['expected_tags']:
                assert tag in suggested_tags, f"Expected tag {tag} not in ML suggestions {suggested_tags}"

            for s in suggestions[:2]:
                top_pos = [f['feature'] for f in s['positive_features'][:3]]
                print(f"    Tag '{s['label']}': margin={s['decision_score']:.3f}, top positive features={top_pos}")

            # 2. Hungarian Feasibility
            doubt = m.DoubtRequest(
                id='verify-doubt-' + sc['id'].replace(' ', '-'),
                requester_id='student-12',
                title=sc['title'],
                description=sc['desc'],
                domain=sc['domain'],
                urgency='Normal',
                bounty=30,
                created_at=now
            )
            doubt.skills = [m.DoubtSkill(doubt_id=doubt.id, tag=t) for t in sc['expected_tags']]

            feasible = services.feasible(db, doubt, mentor, start_slot, now)
            print(f"  Hungarian Grid Feasibility: {feasible}")
            assert feasible, f"Mentor {mentor.id} is NOT feasible for {sc['id']}!"

            # 3. Suitability & Utility Scoring
            attempt = db.scalar(
                select(m.AssessmentAttempt).where(
                    m.AssessmentAttempt.student_id == mentor.id,
                    m.AssessmentAttempt.domain == sc['domain']
                )
            )
            completed, resolved = services.history(db, mentor.id)
            score_data = services.score(doubt, mentor, start_slot, now, attempt, completed, resolved)
            print(f"  Suitability Score: {score_data['suitability']} | Utility: {score_data['utility']}")
            print(f"  Evidence: {score_data['evidence_label']} (Score: {score_data['assessment_score']})")

            # 4. Tag overlap verification
            mentor_tags = {s.tag for s in mentor.skills if s.domain == sc['domain']}
            doubt_tags = set(sc['expected_tags'])
            overlap = mentor_tags & doubt_tags
            print(f"  Skill Overlap: {overlap} (Mentor skills: {mentor_tags})")
            assert len(overlap) > 0, f"No skill overlap between {mentor_tags} and {doubt_tags}"

        print("\n" + "=" * 70)
        print("ALL 6 DEMONSTRATION SCENARIOS VERIFIED SUCCESSFULLY!")
        print("=" * 70)

if __name__ == '__main__':
    verify_all()
