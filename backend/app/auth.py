import os
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt

from . import config as cfg
from . import models as m
from . import services as svc

class SupabaseJWTVerifier:
    def __init__(
        self,
        supabase_url: str = cfg.SUPABASE_URL,
        algorithm: str = cfg.SUPABASE_JWT_ALGORITHM,
        audience: str = cfg.SUPABASE_JWT_AUDIENCE,
        mock_key = None
    ):
        self.supabase_url = supabase_url.rstrip('/') if supabase_url else ''
        self.algorithm = algorithm or 'ES256'
        self.audience = audience or 'authenticated'
        self.issuer = f"{self.supabase_url}/auth/v1" if self.supabase_url else ''
        self.jwks_url = f"{self.supabase_url}/auth/v1/.well-known/jwks.json" if self.supabase_url else ''
        self.mock_key = mock_key
        self._jwk_client = None

    def get_jwk_client(self) -> jwt.PyJWKClient:
        if self._jwk_client is None:
            if not self.jwks_url:
                raise HTTPException(
                    status_code=500,
                    detail="Server authentication configuration incomplete: SUPABASE_URL not configured"
                )
            self._jwk_client = jwt.PyJWKClient(
                self.jwks_url,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True,
                lifespan=3600
            )
        return self._jwk_client

    def verify_token(self, token: str) -> dict:
        try:
            # 1. Inspect unverified header for algorithm and key identifier
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get('alg')
            if alg != self.algorithm:
                raise HTTPException(
                    status_code=401,
                    detail=f"Unsupported signing algorithm: {alg}. Expected {self.algorithm}"
                )

            # 2. Obtain public signing key
            if self.mock_key is not None:
                key = self.mock_key
            else:
                client = self.get_jwk_client()
                try:
                    signing_key = client.get_signing_key_from_jwt(token)
                    key = signing_key.key
                except Exception as e:
                    raise HTTPException(
                        status_code=401,
                        detail=f"Unable to find signing key in Supabase JWKS: {str(e)}"
                    )

            # 3. Cryptographically verify signature, claims, issuer, audience and expiration
            decode_kwargs = {
                'algorithms': [self.algorithm],
                'options': {
                    'require': ['exp', 'sub', 'aud'],
                    'verify_aud': True,
                    'verify_exp': True,
                }
            }
            if self.audience:
                decode_kwargs['audience'] = self.audience
            if self.issuer:
                decode_kwargs['issuer'] = self.issuer
                decode_kwargs['options']['verify_iss'] = True

            payload = jwt.decode(token, key, **decode_kwargs)

            # 4. Verify authenticated role claim if present
            role = payload.get('role')
            if role and role != 'authenticated':
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: Token role is not 'authenticated'"
                )

            return payload

        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Authentication token has expired")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail="Invalid token audience")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=401, detail="Invalid token issuer")
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=401, detail="Invalid cryptographic token signature")
        except jwt.InvalidAlgorithmError as e:
            raise HTTPException(status_code=401, detail=f"Invalid algorithm: {str(e)}")
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="Malformed or unparseable JWT token")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"JWT verification failed: {str(e)}")

# Global verifier instance
verifier = SupabaseJWTVerifier()

def get_or_create_student_mapping(db: Session, sub: str, payload: dict) -> m.Student:
    """Safely map a Supabase user UUID to an existing or newly provisioned SQLite student."""
    mapping = db.scalar(
        select(m.AuthIdentityMapping).where(m.AuthIdentityMapping.supabase_user_id == sub)
    )
    if mapping:
        return svc.get(db, m.Student, mapping.student_id)

    # First-login for a regular registered Supabase user
    meta = payload.get('user_metadata') or {}
    email = payload.get('email', '')
    name = meta.get('name') or meta.get('full_name') or (email.split('@')[0].capitalize() if email else 'Student')
    
    clean_sub = sub.replace('-', '')[:8]
    student_id = f"student-usr-{clean_sub}"
    
    # Check if student ID collision exists
    existing = db.scalar(select(m.Student).where(m.Student.id == student_id))
    if existing:
        student_id = f"student-usr-{clean_sub}-{m.uid()[:4]}"

    student = m.Student(
        id=student_id,
        name=name,
        points_balance=100,  # Standard starter virtual bounty balance
        mentoring=False      # Regular new signups start as non-mentors without fabricated skills
    )
    db.add(student)
    db.flush()

    new_mapping = m.AuthIdentityMapping(
        supabase_user_id=sub,
        student_id=student_id,
        created_at=m.now()
    )
    db.add(new_mapping)
    db.flush()
    return student
