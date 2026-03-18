from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.services.token_store import is_token_revoked

# Bearer authentication scheme
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    """
    Helper to standardize unauthorized responses.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


async def _get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Decode token and fetch user from database.
    """
    try:
        payload = decode_access_token(token)
    except (JWTError, ValueError):
        raise _unauthorized("Invalid or expired token")

    user_id: Optional[str] = payload.get("sub")
    jti: Optional[str] = payload.get("jti")

    if not user_id:
        raise _unauthorized("Invalid token payload")
    if await is_token_revoked(jti):
        raise _unauthorized("Token revoked")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise _unauthorized("User not found")

    if not user.is_active:
        raise _unauthorized("User inactive")

    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency for protected routes.

    Ensures:
    - Bearer token exists
    - Token is valid
    - User exists and is active
    """
    cached = getattr(request.state, "current_user", None)
    if cached is not None:
        return cached

    if credentials is None:
        raise _unauthorized("Missing bearer token")

    token = credentials.credentials

    user = await _get_user_from_token(token, db)
    request.state.current_user = user
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication dependency.

    Returns:
        User if token valid
        None if no token or invalid token
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        return await _get_user_from_token(token, db)
    except HTTPException:
        return None