# TRIAGE15 — AUTHENTICATION ARCHITECTURE & SPECIFICATION

## Supabase Asymmetric ES256 Authentication & SQLite Identity Mapping

**Project:** Triage15  
**Branch:** `integration/final-mvp`  
**Authentication Provider:** Supabase Auth (GoTrue)  
**Cryptographic Algorithm:** ES256 (ECDSA using P-256 and SHA-256)  
**Application Database:** SQLite with WAL Mode & Foreign Key Enforcement  

---

## 1. System Overview & Division of Responsibilities

Triage15 decouples user authentication from application business logic:
- **Supabase Auth** manages identity registration, password hashing (bcrypt/argon2), email verification, token generation, cryptographic signing, session lifecycle, and automatic token refresh.
- **FastAPI Backend** acts as a cryptographically independent relying party. It verifies signed ES256 JWTs using public keys fetched and cached from Supabase's JSON Web Key Set (JWKS) endpoint. It does **not** make administrative API requests to Supabase on every incoming HTTP call.
- **SQLite Database** stores all application entities (students, point ledgers, doubts, mentor skills, availability windows, sessions, code snippets, diffs, resolution records) and maintains the immutable `auth_identity_mappings` table.

```
┌─────────────────────────────────┐
│ React / TypeScript / Vite Client│
└────────────────┬────────────────┘
                 │ 1. Email / Password Login (signInWithPassword)
                 ▼
┌─────────────────────────────────┐
│        Supabase Auth (Cloud)    │
│  - Verifies credentials         │
│  - Signs JWT using ES256        │
└────────────────┬────────────────┘
                 │ 2. Signed Access Token (JWT)
                 ▼
┌─────────────────────────────────┐
│ React Centralized API Client    │
│ (Attaches Authorization: Bearer)│
└────────────────┬────────────────┘
                 │ 3. API Request + Bearer Token
                 ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI Application (`app.auth.SupabaseJWTVerifier`)    │
│  - Inspects unverified header: alg == 'ES256', kid     │
│  - Retrieves cached public key from Supabase JWKS      │
│  - Cryptographically verifies ES256 ECDSA signature    │
│  - Validates iss, aud == 'authenticated', exp claims   │
│  - Extracts 'sub' claim (Supabase user UUID)           │
└────────────────┬───────────────────────────────────────┘
                 │ 4. Verified UUID
                 ▼
┌────────────────────────────────────────────────────────┐
│ SQLite Database (`auth_identity_mappings`)             │
│  - Maps Supabase UUID -> `student_id` (e.g. student-08)│
│  - If new user: provisions clean student profile       │
│  - Enforces session participant authorization          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Cryptographic Verification Details

### 2.1. Why ES256 Asymmetric Cryptography?
In legacy systems using HS256, both the token issuer and token verifiers must share the identical symmetric secret. If a backend verifier is compromised, the secret key can be used to forge tokens for any user.
Under **ES256 (ECDSA P-256)**:
- Supabase holds the **private key** and signs the JWT.
- FastAPI only requires the **public key** from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.
- The backend can cryptographically prove token authenticity without ever holding signing privileges or storing the private key.

### 2.2. Verification Protocol in `app.auth`
Every protected route passes through `identity = Depends(get_current_student)`:
1. **Header Inspection:** Expects `Authorization: Bearer <token>`.
2. **Algorithm Enforcement:** The unverified header must specify `"alg": "ES256"`. Any attempt to pass `"HS256"`, `"RS256"`, or `"none"` is rejected with HTTP 401.
3. **Public Key Selection:** Key identifier (`kid`) locates the appropriate public key in `PyJWKClient`. Keys are cached in-memory with a 1-hour TTL and automatic key rotation support.
4. **Signature Verification:** Mathematical verification against the elliptic curve P-256 public key.
5. **Claims Validation:**
   - `exp`: Token must not be expired.
   - `iss`: Must equal `{SUPABASE_URL}/auth/v1`.
   - `aud`: Must equal `"authenticated"`.
   - `sub`: Must be a non-empty user UUID.
   - `role`: If present, must equal `"authenticated"`.

---

## 3. Student Identity Mapping & Safe Onboarding

### 3.1. Schema: `auth_identity_mappings`
```sql
CREATE TABLE auth_identity_mappings (
    id VARCHAR PRIMARY KEY,
    supabase_user_id VARCHAR NOT NULL UNIQUE,
    student_id VARCHAR NOT NULL UNIQUE REFERENCES students(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX ix_auth_identity_mappings_supabase_user_id ON auth_identity_mappings (supabase_user_id);
CREATE UNIQUE INDEX ix_auth_identity_mappings_student_id ON auth_identity_mappings (student_id);
```

### 3.2. Mapping Invariants
1. **No Client Assignment:** The frontend can never specify its own mapping or bind its token to an arbitrary student ID.
2. **Seeded Student Protection:** The 12 pre-seeded demonstration students (`student-01` through `student-12`) are mapped exclusively through the trusted provisioning script.
3. **Safe New Student Registration:** When a new user registers and signs in for the first time:
   - System transactionally creates a new `Student` record (`student-usr-<uuid_prefix>`).
   - Grants standard starter balance (100 virtual bounty points).
   - `mentoring = False`: New students **never** receive automatic mentor privileges or synthetic assessment scores.
   - Binds the mapping in `auth_identity_mappings`.

---

## 4. Insecure Identity Switching Removal

In the development prototype, the `X-Demo-Student-ID` header permitted unrestricted identity switching across any student ID.

### Production Hardening
- In production (`ENVIRONMENT=production` or `ALLOW_DEMO_AUTH=false`), `X-Demo-Student-ID` is **strictly ignored and forbidden**.
- Missing Bearer tokens fail closed immediately with HTTP 401.
- Attempting to pass `X-Demo-Student-ID` alongside a valid Bearer token is safely neutralized: identity is derived exclusively from the cryptographic `sub` claim and the database mapping.
- Local automated regression testing can explicitly enable test fixtures via isolated test environment settings (`ALLOW_DEMO_AUTH=true`), preserving regression speed without weakening deployed security.

---

## 5. Demonstration Accounts

To support seamless hackathon judging without requiring real email inboxes, 7 synthetic accounts were administratively provisioned in Supabase Auth via `scripts/provision_demo_accounts.py`:

| Role | Email Identifier | Bound Student Profile | Domain & Skills |
| :--- | :--- | :--- | :--- |
| **Demo Requester** | `requester@example.com` | `student-12` (Jane Doe) | General programming, Python/SQL |
| **Product & Frontend Mentor** | `guest.product@example.com` | `student-02` (Bob Smith) | JavaScript, React |
| **Software Engineering Mentor**| `guest.software@example.com` | `student-01` (Alice Johnson) | JavaScript, SQL, Python |
| **Backend & Database Mentor** | `guest.backend@example.com` | `student-04` (Diana Prince) | SQL, joins, aggregation |
| **Applied AI Mentor** | `guest.ai@example.com` | `student-08` (Henry Ford) | Python, pandas |
| **Machine Learning Mentor** | `guest.ml@example.com` | `student-03` (Charlie Brown) | Python, pandas, ML |
| **Infrastructure Mentor** | `guest.infra@example.com` | `student-06` (Fiona Gallagher) | Python, async |

*Passkeys and credentials are stored strictly in `.private/DEMO_ACCOUNTS.md`, which is excluded from Git and Docker.*

---

## 6. Railway Cloud Deployment Configuration

When deploying on Railway:
1. **Public Build Variables (Stage 1 Node Builder):**
   - `VITE_SUPABASE_URL=https://<ref>.supabase.co`
   - `VITE_SUPABASE_PUBLISHABLE_KEY=<publishable_key>`
2. **Runtime Environment Variables (Stage 2 Python Container):**
   - `SUPABASE_URL=https://<ref>.supabase.co`
   - `SUPABASE_PUBLISHABLE_KEY=<publishable_key>`
   - `SUPABASE_JWT_ALGORITHM=ES256`
   - `SUPABASE_JWT_AUDIENCE=authenticated`
   - `DATABASE_URL=sqlite:////data/triage15.db`
   - `ENVIRONMENT=production`
   - `ALLOW_DATABASE_RESET=false`

---

## 7. Known Security Limitations & Future Roadmap

1. **Token Revocation Lag:** JWTs are verified statelessly using public keys. If a user signs out on the frontend, their existing access token remains technically valid until its standard 1-hour expiration time unless an active token revocation blocklist is queried.
2. **Single-Worker Scalability:** The in-process Hungarian matching loop and session expiration timer operate within a single Uvicorn process. Horizontal scaling across multiple containers would require an external task queue (such as Redis or Celery).
