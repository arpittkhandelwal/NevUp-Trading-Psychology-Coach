"""
Auth router — Generate Security Bearer Tokens.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import TokenRequest, TokenResponse
from app.utils.auth import create_token

router = APIRouter(prefix="/auth", tags=["Security"])

# Demo shared secret
_DEMO_SECRET = "nevup2026"

@router.post(
    "/token", 
    response_model=TokenResponse, 
    summary="Generate Security Bearer Token",
    description="Authenticates the trader and returns a scoped JWT access token for session management."
)
async def login(body: TokenRequest) -> TokenResponse:
    if body.secret != _DEMO_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")
    return create_token(body.userId)
