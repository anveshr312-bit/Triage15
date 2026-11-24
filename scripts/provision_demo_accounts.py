"""
Administrative provisioning script for Triage15 demonstration accounts.
Creates confirmed synthetic accounts in Supabase Auth via Admin API and
binds them to existing SQLite student profiles.
Credentials are saved locally to .private/DEMO_ACCOUNTS.md.
"""

import os
import sys
import string
import secrets
import requests
from pathlib import Path

# Ensure backend modules are on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app import config as cfg
from app import models as m
from app.database import transaction
from sqlalchemy import select, delete

DEMO_PROFILES = [
    {
        'email': 'requester@example.com',
        'name': 'Jane Doe',
        'student_id': 'student-12',
        'role_desc': 'Demo Student / Requester',
        'skills': 'General programming doubts, Python/SQL',
        'purpose': 'Post doubts, view Hungarian matching, confirm resolutions'
    },
    {
        'email': 'guest.product@example.com',
        'name': 'Bob Smith',
        'student_id': 'student-02',
        'role_desc': 'Product & Frontend Mentor',
        'skills': 'JavaScript, React, UI debugging',
        'purpose': 'Demonstrate React/JavaScript mentoring and code snippet diffing'
    },
    {
        'email': 'guest.software@example.com',
        'name': 'Alice Johnson',
        'student_id': 'student-01',
        'role_desc': 'Software Engineering Mentor',
        'skills': 'JavaScript, SQL, Python',
        'purpose': 'Demonstrate multi-domain peer mentoring and code resolution'
    },
    {
        'email': 'guest.backend@example.com',
        'name': 'Diana Prince',
        'student_id': 'student-04',
        'role_desc': 'Backend & Database Mentor',
        'skills': 'SQL, joins, aggregation, schema design',
        'purpose': 'Demonstrate complex SQL doubt triage and resolution'
    },
    {
        'email': 'guest.ai@example.com',
        'name': 'Henry Ford',
        'student_id': 'student-08',
        'role_desc': 'Applied AI Mentor',
        'skills': 'Python, pandas, data processing',
        'purpose': 'Demonstrate AI/Data doubt matching with ML tag attribution'
    },
    {
        'email': 'guest.ml@example.com',
        'name': 'Charlie Brown',
        'student_id': 'student-03',
        'role_desc': 'Machine Learning Mentor',
        'skills': 'Python, pandas, feature engineering',
        'purpose': 'Demonstrate machine learning skill matching'
    },
    {
        'email': 'guest.infra@example.com',
        'name': 'Fiona Gallagher',
        'student_id': 'student-06',
        'role_desc': 'Applied ML & Infrastructure Mentor',
        'skills': 'Python, async, concurrent pipelines',
        'purpose': 'Demonstrate async and infrastructure mentoring'
    }
]

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

    # Fetch existing users to support idempotent execution
    admin_users_url = f"{supabase_url}/auth/v1/admin/users"
    res = requests.get(admin_users_url, headers=headers, params={'per_page': 100}, timeout=10)
    if res.status_code != 200:
        print(f"ERROR: Failed to connect to Supabase Admin API (HTTP {res.status_code}): {res.text}")
        sys.exit(1)

    existing_users = {u['email'].lower(): u['id'] for u in res.json().get('users', [])}

    private_dir = Path('.private')
    private_dir.mkdir(exist_ok=True)
    try:
        os.chmod(private_dir, 0o700)
    except Exception:
        pass

    results = []

    print(f"Provisioning {len(DEMO_PROFILES)} synthetic demonstration accounts...")

    for profile in DEMO_PROFILES:
        email = profile['email'].lower()
        name = profile['name']
        student_id = profile['student_id']
        password = generate_strong_password()

        if email in existing_users:
            user_id = existing_users[email]
            # Update password for idempotent recovery
            update_url = f"{supabase_url}/auth/v1/admin/users/{user_id}"
            u_res = requests.put(update_url, headers=headers, json={'password': password}, timeout=10)
            if u_res.status_code != 200:
                print(f"Warning: Could not update password for existing user {email}: {u_res.text}")
            print(f"  [EXISTS] {email} -> Supabase UUID {user_id[:8]}... -> SQLite {student_id}")
        else:
            # Create user with email_confirm: True
            payload = {
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {'name': name}
            }
            c_res = requests.post(admin_users_url, headers=headers, json=payload, timeout=10)
            if c_res.status_code not in (200, 201):
                print(f"ERROR: Failed to create user {email} (HTTP {c_res.status_code}): {c_res.text}")
                continue
            user_id = c_res.json()['id']
            print(f"  [CREATED] {email} -> Supabase UUID {user_id[:8]}... -> SQLite {student_id}")

        # Update SQLite mapping transactionally
        with transaction() as db:
            # Ensure no stale mapping for this student_id
            db.execute(delete(m.AuthIdentityMapping).where(m.AuthIdentityMapping.student_id == student_id))
            db.execute(delete(m.AuthIdentityMapping).where(m.AuthIdentityMapping.supabase_user_id == user_id))
            mapping = m.AuthIdentityMapping(
                id=m.uid(),
                supabase_user_id=user_id,
                student_id=student_id,
                created_at=m.now()
            )
            db.add(mapping)
            db.flush()

        results.append({
            **profile,
            'password': password,
            'supabase_uuid': user_id
        })

    # Write .private/DEMO_ACCOUNTS.md
    report_lines = [
        "# TRIAGE15 — SYNTHETIC DEMONSTRATION ACCOUNTS",
        "",
        "> **CONFIDENTIAL & PRIVATE — DO NOT COMMIT OR EXPOSE**",
        "> This document is stored in `.private/DEMO_ACCOUNTS.md` and excluded from Git and Docker.",
        "> Generated automatically by `scripts/provision_demo_accounts.py`.",
        "",
        "## Guest Demonstration Account Inventory",
        "",
        "| Profile Role | Email Identifier | Password | Student ID | Domain / Skills | Demonstration Purpose |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for r in results:
        report_lines.append(
            f"| **{r['role_desc']}** | `{r['email']}` | `{r['password']}` | `{r['student_id']}` ({r['name']}) | {r['skills']} | {r['purpose']} |"
        )

    report_lines.extend([
        "",
        "---",
        "",
        "## Usage Instructions for Presenters & Judges",
        "",
        "1. Open the Triage15 web application in your browser (e.g. `http://localhost:5173` or deployed URL).",
        "2. If unauthenticated, the application presents the Supabase authentication form.",
        "3. Enter the selected guest email and password from the table above.",
        "4. Click **Sign In**.",
        "5. The application verifies your credentials with Supabase, extracts the signed ES256 JWT, sends it to FastAPI, and loads your dedicated student profile and permissions.",
        "6. To test peer interaction:",
        "   - Open an incognito or secondary browser window.",
        "   - Sign in as `requester@example.com` to post a doubt with a bounty.",
        "   - Sign in as `guest.product@example.com` or `guest.ai@example.com` to receive the matching offer, accept, and mentor.",
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
