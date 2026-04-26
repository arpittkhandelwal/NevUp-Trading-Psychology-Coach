"""
JWT authentication utilities — HS256, sub === userId enforcement.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.schemas import LoginRequest, TokenData, TokenResponse
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_bearer = HTTPBearer(auto_error=True)


def create_token(user_id: str) -> TokenResponse:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return TokenResponse(accessToken=token)


def _decode(token: str) -> TokenData:
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenData(sub=data["sub"], exp=data.get("exp"))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenData:
    return _decode(creds.credentials)


def require_user(path_user_id: str, token: TokenData = Depends(get_current_user)) -> TokenData:
    """Enforce sub === userId (cross-tenant guard)."""
    if token.sub != path_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token sub '{token.sub}' does not match requested userId '{path_user_id}'",
        )
    return token
