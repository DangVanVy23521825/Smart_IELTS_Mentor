from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _build_common_payload(*, subject: str, token_type: str, expires_at: datetime, jti: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "sub": subject,
        "typ": token_type,
        "jti": jti,
    }


def create_access_token(*, subject: str, jti: str | None = None) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    token_jti = jti or str(uuid4())
    payload = _build_common_payload(subject=subject, token_type="access", expires_at=exp, jti=token_jti)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), token_jti


def create_refresh_token(*, subject: str, jti: str | None = None) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.refresh_token_expire_days)
    token_jti = jti or str(uuid4())
    payload = _build_common_payload(subject=subject, token_type="refresh", expires_at=exp, jti=token_jti)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), token_jti


def _decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


def decode_access_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("typ") != "access":
        raise ValueError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("typ") != "refresh":
        raise ValueError("Invalid token type")
    return payload

