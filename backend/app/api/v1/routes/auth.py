from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.rate_limit import login_rate_limiter
from app.services.token_store import is_token_revoked, revoke_token_jti

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse(id=user.id, email=user.email, role=user.role.value)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{payload.email.lower()}"
    decision = await login_rate_limiter.evaluate(rate_key)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, please try again later",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is None or not user.is_active:
        await login_rate_limiter.register_failure(rate_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        await login_rate_limiter.register_failure(rate_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await login_rate_limiter.clear(rate_key)
    access_token, _ = create_access_token(subject=user.id)
    refresh_token, _ = create_refresh_token(subject=user.id)
    return TokenResponse(  # type: ignore[reportUnknownReturnType]
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        token_data = decode_refresh_token(payload.refresh_token)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    subject = token_data.get("sub")
    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if not subject or not jti or not exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")

    if await is_token_revoked(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    user = (await db.execute(select(User).where(User.id == subject))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = max(1, int(exp) - now_ts)
    await revoke_token_jti(jti, ttl_seconds=ttl)

    access_token, _ = create_access_token(subject=subject)
    refresh_token, _ = create_refresh_token(subject=subject)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        token_data = decode_refresh_token(payload.refresh_token)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if token_data.get("sub") != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token does not belong to user")

    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if jti and exp:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        ttl = max(1, int(exp) - now_ts)
        await revoke_token_jti(jti, ttl_seconds=ttl)

    return {"status": "ok"}

