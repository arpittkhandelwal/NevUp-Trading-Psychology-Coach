"""
Memory router — Advanced Behavioral Persistence and Explainability Layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.engine.behavioral import analyze_session
from app.memory.service import retrieve_context, retrieve_session, store_session
from app.models.schemas import (
    MemoryContext, SessionPayload, SessionRecord, TokenData, ExplanationReport
)
from app.utils.auth import get_current_user, require_user

router = APIRouter(prefix="/memory", tags=["Memory & Explainability"])


@router.put(
    "/{userId}/sessions/{sessionId}",
    response_model=SessionRecord,
    summary="Ingest Trading Session",
    description="Stores a complete trading session, triggers the Behavioral Engine, and calculates the unified Risk Profile."
)
async def put_session(
    userId: str,
    sessionId: str,
    body: SessionPayload,
    token: TokenData = Depends(get_current_user),
) -> SessionRecord:
    require_user(userId, token)

    # Run behavioral analysis to derive Rich Signals and Risk Profile
    signals, risk = analyze_session(sessionId, body.trades)
    
    # Legacy tags for backward compatibility
    tags = [s.signal for s in signals if s.confidence > 0]

    # Build metrics summary
    pnls = [t.pnl for t in body.trades]
    wins = [t for t in body.trades if t.outcome == "win"]
    metrics = {
        "totalPnl": sum(pnls),
        "winRate": len(wins) / len(body.trades) if body.trades else 0.0,
        "tradeCount": len(body.trades),
        "riskScore": risk.score,
        "riskLevel": risk.level,
    }
    
    summary = (
        f"Session {sessionId} — Risk: {risk.level.upper()} ({risk.score}/100). "
        f"Detected: {', '.join(tags) or 'none'}"
    )

    # Enrich payload
    body.tradeCount = len(body.trades)
    body.totalPnl = sum(pnls)
    body.winRate = metrics["winRate"]

    return await store_session(
        session_id=sessionId,
        user_id=userId,
        payload=body,
        summary=summary,
        metrics=metrics,
        tags=tags,
        signals=signals,
        risk_profile=risk,
    )


@router.get(
    "/{userId}/sessions/{sessionId}",
    response_model=SessionRecord,
    summary="Retrieve Session Deep-Dive",
    description="Fetches a full historical record of a session including all trade events and detected pathologies."
)
async def get_session_endpoint(
    userId: str,
    sessionId: str,
    token: TokenData = Depends(get_current_user),
) -> SessionRecord:
    require_user(userId, token)
    record = await retrieve_session(sessionId, userId)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Session {sessionId} not found for user {userId}")
    return record


@router.get(
    "/{userId}/sessions/{sessionId}/explain",
    response_model=ExplanationReport,
    summary="Explain Behavioral Pathologies (XAI)",
    description="Provides deterministic explainability (XAI) with trade-level evidence, reasoning, and psychological risk quantification."
)
async def explain_session(
    userId: str,
    sessionId: str,
    token: TokenData = Depends(get_current_user),
) -> ExplanationReport:
    require_user(userId, token)
    record = await retrieve_session(sessionId, userId)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if not record.signals:
        return ExplanationReport(
            prediction="none",
            confidence=1.0,
            severity=0.0,
            evidence=[],
            reasoning="No pathologies detected. Trader followed predefined plan and risk parameters.",
            risk=record.risk_profile or analyze_session(sessionId, record.trades)[1]
        )

    primary = record.signals[0]
    return ExplanationReport(
        prediction=primary.signal,
        confidence=primary.confidence,
        severity=primary.severity,
        evidence=primary.evidence,
        reasoning=primary.reasoning,
        risk=record.risk_profile or analyze_session(sessionId, record.trades)[1]
    )


@router.get(
    "/{userId}/context",
    response_model=MemoryContext,
    summary="Retrieve Historically Relevant Sessions",
    description="Fetches the top historically relevant sessions based on a behavioral signal to provide grounding for the AI coach."
)
async def get_context(
    userId: str,
    relevantTo: Optional[str] = Query(None, description="Behavioral signal name (e.g. overtrading)"),
    token: TokenData = Depends(get_current_user),
) -> MemoryContext:
    require_user(userId, token)
    sessions = await retrieve_context(userId, relevant_to=relevantTo)
    return MemoryContext(
        userId=userId,
        relevantSessions=sessions,
        signal=relevantTo,
        retrievedAt=datetime.utcnow(),
    )
