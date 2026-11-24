"""
Administrative provisioning script for Triage15 demonstration accounts.
Creates confirmed synthetic accounts in Supabase Auth via Admin API and
binds them to specialized SQLite student profiles for the HackDay judging panel.
Credentials and judge profile mappings are saved locally to .private/DEMO_ACCOUNTS.md.
"""

import os
import re
import sys
import string
import secrets
import requests
from pathlib import Path

# Ensure backend modules are on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app import config as cfg
from app import models as m
from app.database import transaction, SessionLocal
from sqlalchemy import select, delete

SLOT = cfg.SLOT

DEMO_PROFILES = [
    {
        'email': 'requester@example.com',
        'judge_name': 'Presenter (Jane Doe)',
        'affiliation': 'HackDay Presenter',
        'display_name': 'Demo Student / Requester',
        'student_id': 'student-12',
        'mentoring': False,
        'points_balance': 300,
        'domain': 'Python',
        'skills': [],
        'assessment_score': None,
        'demo_doubt': 'N/A (Doubt Requester / Presenter)',
        'purpose': 'Post doubts, demonstrate ML skill suggestions, observe Hungarian matching, confirm resolutions'
    },
    {
        'email': 'guest.product@example.com',
        'judge_name': 'Vishal Dhakad',
        'affiliation': 'Virtual Revolt Software',
        'display_name': 'Demo 01 — Product & Frontend Mentor',
        'student_id': 'student-02',
        'mentoring': True,
        'points_balance': 150,
        'domain': 'JavaScript',
        'skills': [
            ('JavaScript', 'javascript', 4),
            ('JavaScript', 'react', 4),
            ('JavaScript', 'debugging', 4)
        ],
        'assessment_score': 80,
        'demo_doubt': 'React dashboard displays stale data',
        'purpose': 'Demonstrate React/JavaScript mentoring, Google Meet link, code diffing, and resolution'
    },
    {
        'email': 'guest.software@example.com',
        'judge_name': 'Yash Jain',
        'affiliation': 'Barclays',
        'display_name': 'Demo 02 — Software & Database Mentor',
        'student_id': 'student-01',
        'mentoring': True,
        'points_balance': 150,
        'domain': 'SQL',
        'skills': [
            ('SQL', 'sql', 5),
            ('SQL', 'joins', 5),
            ('SQL', 'schema', 4)
        ],
        'assessment_score': 85,
        'demo_doubt': 'SQL query returns duplicate transaction records',
        'purpose': 'Demonstrate SQL joins triage, transaction duplicate resolution, and peer mentoring'
    },
    {
        'email': 'guest.backend@example.com',
        'judge_name': 'Harsh Jain',
        'affiliation': 'Osiyatech',
        'display_name': 'Demo 03 — Backend Engineering Mentor',
        'student_id': 'student-04',
        'mentoring': True,
        'points_balance': 150,
        'domain': 'SQL',
        'skills': [
            ('SQL', 'sql', 5),
            ('SQL', 'aggregation', 5),
            ('SQL', 'joins', 4)
        ],
        'assessment_score': 90,
        'demo_doubt': 'SQL aggregation produces incorrect counts after join',
        'purpose': 'Demonstrate SQL aggregation debugging, code snippet exchange, and resolution confirmation'
    },
    {
        'email': 'guest.ai@example.com',
        'judge_name': 'Arushi Sthapak',
        'affiliation': 'Vinfotech',
        'display_name': 'Demo 04 — Applied AI Mentor',
        'student_id': 'student-08',
        'mentoring': True,
        'points_balance': 150,
        'domain': 'Python',
        'skills': [
            ('Python', 'python', 4),
            ('Python', 'pandas', 4),
            ('Python', 'debugging', 4)
        ],
        'assessment_score': 85,
        'demo_doubt': 'Missing values in pandas dataframe before model training',
        'purpose': 'Demonstrate data preprocessing triage, ML tag feature attribution, and data leakage fix'
    },
    {
        'email': 'guest.ml@example.com',
        'judge_name': 'Manas Arora',
        'affiliation': 'AdvisoryAI',
        'display_name': 'Demo 05 — Machine Learning Mentor',
        'student_id': 'student-03',
        'mentoring': True,
        'points_balance': 150,
        'domain': 'Python',
        'skills': [
            ('Python', 'python', 4),
            ('Python', 'pandas', 4),
            ('Python', 'loops', 4)
        ],
        'assessment_score': 85,
        'demo_doubt': 'TF-IDF data leakage during model evaluation in Python',
        'purpose': 'Demonstrate ML evaluation best practices, train/validation split fix, and solution history'
    },
    {
        'email': 'guest.infra@example.com',
        'judge_name': 'Shriyash Beohar',
        'affiliation': 'Percivio',
        'display_name': 'Demo 06 — Applied ML & Infrastructure Mentor',
        'student_id': 'student-06',
        'mentoring': True,
        'points_balance': 150,
        'domain': 'Python',
        'skills': [
            ('Python', 'python', 5),
            ('Python', 'debugging', 4),
            ('Python', 'loops', 4)
        ],
        'assessment_score': 90,
        'demo_doubt': 'Python FastAPI endpoint blocks while performing heavy task',
        'purpose': 'Demonstrate async infrastructure mentoring, thread pool offloading, and bounty award'
    }
]

def load_existing_passwords() -> dict:
    passwords = {}
    path = Path('.private/DEMO_ACCOUNTS.md')
    if path.exists():
        try:
            content = path.read_text(encoding='utf-8')
            # Extract email and password from markdown table
            for match in re.finditer(r'`([^`]+@[^`]+)`\s*\|\s*`([^`]+)`', content):
                passwords[match.group(1).lower()] = match.group(2)
        except Exception:
            pass
    return passwords

def generate_strong_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)):
            return pwd

def provision():
    supabase_url = cfg.SUPABASE_URL.rstrip('/')
    secret_key = cfg.SUPABASE_SECRET_KEY

    if not supabase_url or not secret_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SECRET_KEY not configured in .env.")
        sys.exit(1)

    headers = {
        'apikey': secret_key,
        'Authorization': f'Bearer {secret_key}',
        'Content-Type': 'application/json'
    }

    # Fetch existing users from Supabase Admin API
    admin_users_url = f"{supabase_url}/auth/v1/admin/users"
    res = requests.get(admin_users_url, headers=headers, params={'per_page': 100}, timeout=10)
    if res.status_code != 200:
        print(f"ERROR: Failed to connect to Supabase Admin API (HTTP {res.status_code}): {res.text}")
        sys.exit(1)

    existing_users = {u['email'].lower(): u['id'] for u in res.json().get('users', [])}
    saved_passwords = load_existing_passwords()

    private_dir = Path('.private')
    private_dir.mkdir(exist_ok=True)
    try:
        os.chmod(private_dir, 0o700)
    except Exception:
        pass

    results = []

    print(f"Provisioning {len(DEMO_PROFILES)} specialized demonstration accounts...")

    now_ts = m.now()
    window_start = ((now_ts - 3600) // SLOT) * SLOT
    window_end = window_start + 7 * 86400  # 7 days rolling availability

    for profile in DEMO_PROFILES:
        email = profile['email'].lower()
        display_name = profile['display_name']
        student_id = profile['student_id']
        password = saved_passwords.get(email) or generate_strong_password()

        if email in existing_users:
            user_id = existing_users[email]
            try:
                update_url = f"{supabase_url}/auth/v1/admin/users/{user_id}"
                u_res = requests.put(
                    update_url,
                    headers=headers,
                    json={'user_metadata': {'name': display_name}},
                    timeout=20
                )
                if u_res.status_code != 200:
                    print(f"  Warning: Metadata update for {email}: {u_res.text}")
            except Exception as e:
                print(f"  Note: Supabase API update skipped for existing user {email} ({type(e).__name__})")
            print(f"  [SUPABASE-EXISTS] {email} -> UUID {user_id[:8]}... -> SQLite {student_id}")
        else:
            payload = {
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {'name': display_name}
            }
            try:
                c_res = requests.post(admin_users_url, headers=headers, json=payload, timeout=20)
                if c_res.status_code not in (200, 201):
                    print(f"ERROR: Failed to create user {email} (HTTP {c_res.status_code}): {c_res.text}")
                    continue
                user_id = c_res.json()['id']
                print(f"  [SUPABASE-CREATED] {email} -> UUID {user_id[:8]}... -> SQLite {student_id}")
            except Exception as e:
                print(f"ERROR: Failed to connect to Supabase to create {email}: {e}")
                continue

        # Update SQLite student record, skills, availability, and assessment transactionally
        with transaction() as db:
            # 1. Update Student record
            student = db.get(m.Student, student_id)
            if not student:
                student = m.Student(
                    id=student_id,
                    name=display_name,
                    mentoring=profile['mentoring'],
                    points_balance=profile['points_balance']
                )
                db.add(student)
            else:
                student.name = display_name
                student.mentoring = profile['mentoring']
                student.points_balance = profile['points_balance']
            db.flush()

            # 2. Update AuthIdentityMapping
            db.execute(delete(m.AuthIdentityMapping).where(m.AuthIdentityMapping.student_id == student_id))
            db.execute(delete(m.AuthIdentityMapping).where(m.AuthIdentityMapping.supabase_user_id == user_id))
            mapping = m.AuthIdentityMapping(
                id=m.uid(),
                supabase_user_id=user_id,
                student_id=student_id,
                created_at=now_ts
            )
            db.add(mapping)

            # 3. Update Student Skills
            db.execute(delete(m.StudentSkill).where(m.StudentSkill.student_id == student_id))
            for domain, tag, level in profile['skills']:
                db.add(m.StudentSkill(
                    id=m.uid(),
                    student_id=student_id,
                    domain=domain,
                    tag=tag,
                    level=level
                ))

            # 4. Update Availability Windows (7-day window for mentors)
            db.execute(delete(m.AvailabilityWindow).where(m.AvailabilityWindow.student_id == student_id))
            if profile['mentoring']:
                db.add(m.AvailabilityWindow(
                    id=m.uid(),
                    student_id=student_id,
                    start=window_start,
                    end=window_end
                ))

            # 5. Assessment attempt (evidence for mentor scoring)
            if profile['mentoring'] and profile['assessment_score'] is not None:
                domain = profile['domain']
                existing_attempt = db.scalar(
                    select(m.AssessmentAttempt).where(
                        m.AssessmentAttempt.student_id == student_id,
                        m.AssessmentAttempt.domain == domain
                    )
                )
                if not existing_attempt:
                    attempt = m.AssessmentAttempt(
                        id=m.uid(),
                        student_id=student_id,
                        domain=domain,
                        score=profile['assessment_score'],
                        question_count=5,
                        correct_count=int(5 * (profile['assessment_score'] / 100)),
                        created_at=now_ts - 86400,
                        version=1
                    )
                    db.add(attempt)
                    db.flush()
                    # Add responses to existing questions if present
                    questions = list(db.scalars(
                        select(m.AssessmentQuestion).where(m.AssessmentQuestion.domain == domain)
                    ))
                    for q_idx, q in enumerate(questions[:5]):
                        ans = q.correct if q_idx < attempt.correct_count else (q.correct + 1) % len(q.options)
                        db.add(m.AssessmentResponse(
                            id=m.uid(),
                            attempt_id=attempt.id,
                            question_id=q.id,
                            answer=ans
                        ))
                else:
                    existing_attempt.score = profile['assessment_score']

            # 6. Point Ledger record
            ref = f'demo_grant:{student_id}'
            existing_ledger = db.scalar(
                select(m.PointLedger.id).where(m.PointLedger.reference_id == ref)
            )
            if not existing_ledger:
                db.add(m.PointLedger(
                    student_id=student_id,
                    amount=profile['points_balance'],
                    transaction_type='INITIAL_GRANT',
                    reference_id=ref,
                    balance_after=profile['points_balance'],
                    notes=f'Initial demonstration grant for {display_name}'
                ))

            db.flush()

        results.append({
            **profile,
            'password': password,
            'supabase_uuid': user_id
        })

    # Write .private/DEMO_ACCOUNTS.md
    report_lines = [
        "# TRIAGE15 — JUDGE DEMONSTRATION ACCOUNTS & CREDENTIALS",
        "",
        "> **CONFIDENTIAL & RESTRICTED — DO NOT COMMIT OR EXPOSE**",
        "> This document is stored in `.private/DEMO_ACCOUNTS.md` and excluded from Git and Docker.",
        "> Generated automatically by `scripts/provision_demo_accounts.py` for HackDay 2026 judging panel.",
        "",
        "## 1. Judge-Specific Guest Account Directory",
        "",
        "| Judge / Affiliation | Profile Role & Name | Login Email | Login Password | Student ID | Domain / Skills | Recommended Demo Doubt |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for r in results:
        skills_str = ", ".join(f"`{tag}` (L{lvl})" for _, tag, lvl in r['skills']) if r['skills'] else "None (Requester)"
        report_lines.append(
            f"| **{r['judge_name']}**<br>*{r['affiliation']}* | **{r['display_name']}** | `{r['email']}` | `{r['password']}` | `{r['student_id']}` | **{r['domain']}**<br>{skills_str} | {r['demo_doubt']} |"
        )

    report_lines.extend([
        "",
        "---",
        "",
        "## 2. Multi-Device Demonstration Workflow for Presenter",
        "",
        "### Scenario Overview",
        "1. **Presenter Machine (Laptop / Projector)**:",
        "   - Sign in as `requester@example.com` (`student-12`).",
        "   - Select one of the 6 recommended doubts below.",
        "   - Enter title & description in the **Create Doubt** form.",
        "   - Observe real-time ML skill suggestions from the One-vs-Rest Linear SVM with mathematical feature attributions.",
        "   - Confirm the suggested tags and post the doubt with a virtual bounty (e.g. 20-40 points).",
        "",
        "2. **Judge Device (Mobile Phone / Incognito Tab)**:",
        "   - Have the judge sign in to Triage15 with their assigned guest credentials above.",
        "   - Their dashboard immediately loads with their specialized student profile.",
        "   - In the **Peer Mentoring** / **Open Doubts** tab, they discover the incoming doubt matching their domain and skills.",
        "   - The judge accepts the match offer (or claims the open doubt).",
        "",
        "3. **Interactive Mentoring Workspace**:",
        "   - Both devices transition into the live mentoring session.",
        "   - Presenter and judge can paste code into the synchronized **Code Snippets** tab.",
        "   - Review the built-in deterministic before-and-after **Code Diff**.",
        "   - Generate and launch a **Google Meet** video conference directly from the workspace.",
        "   - The judge files a structured **Session Resolution** (root cause, explanation, corrected code).",
        "   - The presenter confirms resolution, unlocking an atomic, exactly-once virtual bounty settlement recorded on the immutable ledger.",
        "",
        "---",
        "",
        "## 3. Recommended Demonstration Doubts",
        "",
        "### Demo 01 — Product & Frontend Mentor (Vishal Dhakad)",
        "- **Email**: `guest.product@example.com` | **Domain**: `JavaScript` | **Tags**: `react`, `javascript`",
        "- **Title**: `React dashboard displays stale data`",
        "- **Description**: `My dashboard displays stale data after an API update. How should I refresh state without repeatedly fetching in React with JavaScript?`",
        "- **Expected ML Attribution**: Positive weights on `react`, `in react`, `dashboard`, `javascript`, `api`.",
        "",
        "### Demo 02 — Software & Database Mentor (Yash Jain)",
        "- **Email**: `guest.software@example.com` | **Domain**: `SQL` | **Tags**: `sql`, `joins`",
        "- **Title**: `SQL query returns duplicate transaction records`",
        "- **Description**: `A retry of my reward-settlement request can produce duplicate transactions. My SQL join query returns duplicate transaction records after joining accounts and payments tables.`",
        "- **Expected ML Attribution**: Positive weights on `sql`, `query`, `transaction`, `join`, `tables`.",
        "",
        "### Demo 03 — Backend Engineering Mentor (Harsh Jain)",
        "- **Email**: `guest.backend@example.com` | **Domain**: `SQL` | **Tags**: `sql`, `aggregation`",
        "- **Title**: `SQL aggregation produces incorrect counts after join`",
        "- **Description**: `My SQL aggregation counts duplicate rows after joining two tables. How can I correct the query to get accurate count and sum?`",
        "- **Expected ML Attribution**: Positive weights on `sql`, `query`, `sum`, `count`, `counts`.",
        "",
        "### Demo 04 — Applied AI Mentor (Arushi Sthapak)",
        "- **Email**: `guest.ai@example.com` | **Domain**: `Python` | **Tags**: `python`, `pandas`",
        "- **Title**: `Missing values in pandas dataframe before model training`",
        "- **Description**: `My Python pandas dataframe contains missing values before classification. How can I preprocess it without leaking information from the test set?`",
        "- **Expected ML Attribution**: Positive weights on `pandas`, `dataframe`, `python`.",
        "",
        "### Demo 05 — Machine Learning Mentor (Manas Arora)",
        "- **Email**: `guest.ml@example.com` | **Domain**: `Python` | **Tags**: `python`, `pandas`",
        "- **Title**: `TF-IDF data leakage during model evaluation in Python`",
        "- **Description**: `My Python text classifier gets much better validation scores when I fit TF-IDF before splitting the dataset. Is this data leakage in pandas and Python?`",
        "- **Expected ML Attribution**: Positive weights on `python`, `pandas`, `in python`, `data`.",
        "",
        "### Demo 06 — Applied ML & Infrastructure Mentor (Shriyash Beohar)",
        "- **Email**: `guest.infra@example.com` | **Domain**: `Python` | **Tags**: `python`",
        "- **Title**: `Python FastAPI endpoint blocks while performing heavy task`",
        "- **Description**: `My Python FastAPI endpoint blocks while performing a CPU-heavy task. How can I avoid blocking the server and fix latency debugging in Python?`",
        "- **Expected ML Attribution**: Positive weights on `python`, `fastapi`, `in python`.",
        ""
    ])

    report_path = private_dir / 'DEMO_ACCOUNTS.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')
    try:
        os.chmod(report_path, 0o600)
    except Exception:
        pass

    print(f"\nSUCCESS: {len(results)} demonstration accounts provisioned.")
    print(f"Credentials written securely to {report_path.resolve()}.")
    print("Zero passwords or secrets were printed to terminal logs.")

if __name__ == '__main__':
    provision()
