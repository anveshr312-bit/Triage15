import time
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
import jwt
from starlette.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app import auth
from app import config as cfg
from app import models as m
from app.database import transaction

# Generate persistent EC keypair for deterministic offline test suite
TEST_PRIV = ec.generate_private_key(ec.SECP256R1())
TEST_PUB = TEST_PRIV.public_key()
TEST_ISS = "https://triage15-test.supabase.co/auth/v1"
TEST_AUD = "authenticated"

def create_test_token(
    sub: str = "test-uuid-001",
    role: str = "authenticated",
    aud: str = TEST_AUD,
    iss: str = TEST_ISS,
    expires_in: int = 3600,
    alg: str = "ES256",
    key = TEST_PRIV,
    headers: dict = None,
    email: str = "test@example.com",
    name: str = "Test User"
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + expires_in,
        "role": role,
        "email": email,
        "user_metadata": {"name": name}
    }
    jwt_headers = {"alg": alg, "kid": "test-key-1"}
    if headers:
        jwt_headers.update(headers)
    return jwt.encode(payload, key, algorithm=alg, headers=jwt_headers)

@pytest.fixture(autouse=True)
def setup_test_auth_verifier(monkeypatch):
    """Point global verifier to test key and issuer to isolate from live network."""
    test_verifier = auth.SupabaseJWTVerifier(
        supabase_url="https://triage15-test.supabase.co",
        algorithm="ES256",
        audience="authenticated",
        mock_key=TEST_PUB
    )
    monkeypatch.setattr(auth, "verifier", test_verifier)
    yield

def test_missing_access_token_rejected_in_production(client, monkeypatch):
    monkeypatch.setattr(cfg, "is_demo_auth_allowed", lambda: False)
    res = client.get("/api/me")
    assert res.status_code == 401
    assert "missing" in res.json()["detail"].lower()

def test_invalid_token_format_rejected(client):
    res = client.get("/api/me", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
    assert res.status_code == 401
    assert "malformed" in res.json()["detail"].lower() or "failed" in res.json()["detail"].lower()

def test_expired_token_rejected(client):
    expired_token = create_test_token(expires_in=-300)
    res = client.get("/api/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()

def test_tampered_jwt_signature_rejected(client):
    valid_token = create_test_token()
    # Flip characters in the signature segment
    parts = valid_token.split(".")
    tampered_sig = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"
    
    res = client.get("/api/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401
    assert "signature" in res.json()["detail"].lower() or "failed" in res.json()["detail"].lower()

def test_invalid_issuer_rejected(client):
    wrong_iss_token = create_test_token(iss="https://malicious-issuer.com/auth/v1")
    res = client.get("/api/me", headers={"Authorization": f"Bearer {wrong_iss_token}"})
    assert res.status_code == 401
    assert "issuer" in res.json()["detail"].lower()

def test_invalid_audience_rejected(client):
    wrong_aud_token = create_test_token(aud="untrusted-audience")
    res = client.get("/api/me", headers={"Authorization": f"Bearer {wrong_aud_token}"})
    assert res.status_code == 401
    assert "audience" in res.json()["detail"].lower()

def test_unsupported_signing_algorithm_rejected(client):
    # Try signing with HMAC HS256 instead of required ES256
    hs_token = jwt.encode(
        {"sub": "uuid-1", "aud": TEST_AUD, "iss": TEST_ISS, "exp": int(time.time()) + 300},
        "secret-key-attempt",
        algorithm="HS256"
    )
    res = client.get("/api/me", headers={"Authorization": f"Bearer {hs_token}"})
    assert res.status_code == 401
    assert "algorithm" in res.json()["detail"].lower()

def test_unknown_signing_key_rejected(client):
    other_priv = ec.generate_private_key(ec.SECP256R1())
    other_token = create_test_token(key=other_priv)
    res = client.get("/api/me", headers={"Authorization": f"Bearer {other_token}"})
    assert res.status_code == 401
    assert "signature" in res.json()["detail"].lower() or "failed" in res.json()["detail"].lower()

def test_valid_authenticated_identity_and_mapping(client):
    sub_uuid = "030b9159-test-uuid"
    # Seed mapping to student-01
    with transaction() as db:
        db.query(m.AuthIdentityMapping).filter(m.AuthIdentityMapping.supabase_user_id == sub_uuid).delete()
        mapping = m.AuthIdentityMapping(
            id="map-test-01",
            supabase_user_id=sub_uuid,
            student_id="student-01",
            created_at=m.now()
        )
        db.add(mapping)
        db.commit()

    token = create_test_token(sub=sub_uuid, name="Alice Johnson")
    res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "student-01"
    assert "Asha" in data["name"] or "student-01" in data["id"]

def test_new_user_registration_safe_provisioning(client):
    new_sub = f"new-user-{int(time.time())}"
    token = create_test_token(sub=new_sub, email="brandnew@example.com", name="Brand New Student")
    
    res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Brand New Student"
    assert data["points_balance"] == 0  # Newly registered students start with 0 points
    assert data["mentoring"] is False  # Does not receive fabricated mentor credentials

    # Verify identity mapping exists in SQLite
    with transaction() as db:
        mapping = db.scalar(select(m.AuthIdentityMapping).where(m.AuthIdentityMapping.supabase_user_id == new_sub))
        assert mapping is not None
        assert mapping.student_id == data["id"]

def test_unauthorized_identity_switching_prevented(client, monkeypatch):
    monkeypatch.setattr(cfg, "is_demo_auth_allowed", lambda: False)
    # Attacker tries to pass X-Demo-Student-ID without valid Bearer token
    res = client.get("/api/me", headers={"X-Demo-Student-ID": "student-01"})
    assert res.status_code == 401

    # Attacker tries to pass X-Demo-Student-ID of another user alongside their own token
    own_token = create_test_token(sub="own-uuid-99", name="Honest User")
    res = client.get("/api/me", headers={
        "Authorization": f"Bearer {own_token}",
        "X-Demo-Student-ID": "student-01"
    })
    assert res.status_code == 200
    data = res.json()
    # Identity is derived strictly from verified JWT, ignoring X-Demo-Student-ID
    assert data["id"] != "student-01"
    assert data["name"] == "Honest User"

def test_unauthorized_access_to_private_session_blocked(client):
    with transaction() as db:
        sess = db.scalar(select(m.Session))
        session_id = sess.id
    # Setup test token for non-participant
    non_participant_token = create_test_token(sub="intruder-uuid", name="Intruder")
    
    # Try accessing meeting link for session where user is neither mentor nor requester
    res = client.get(
        f"/api/sessions/{session_id}/meeting",
        headers={"Authorization": f"Bearer {non_participant_token}"}
    )
    assert res.status_code == 403
    assert "participants" in res.json()["detail"].lower()

def test_unauthorized_access_to_code_snippets_blocked(client):
    with transaction() as db:
        sess = db.scalar(select(m.Session))
        session_id = sess.id
    non_participant_token = create_test_token(sub="intruder-uuid", name="Intruder")
    res = client.get(
        f"/api/sessions/{session_id}/snippets",
        headers={"Authorization": f"Bearer {non_participant_token}"}
    )
    assert res.status_code == 403
    assert "participants" in res.json()["detail"].lower()

def test_unauthorized_access_to_solution_history_blocked(client):
    intruder_token = create_test_token(sub="intruder-uuid", name="Intruder")
    # Try accessing student-01's private history
    res = client.get(
        "/api/students/student-01/solution-history",
        headers={"Authorization": f"Bearer {intruder_token}"}
    )
    assert res.status_code == 403
    assert "belongs to another" in res.json()["detail"].lower()
