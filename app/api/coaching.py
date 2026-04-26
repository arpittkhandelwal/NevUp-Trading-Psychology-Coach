"""
Coaching router — Real-Time Evidence-Grounded AI Coaching.
"""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.engine.behavioral import analyze_session
from app.engine.llm_client import stream_coaching
from app.memory.service import retrieve_context, store_session
from app.models.schemas import (
    BehavioralSignal, CoachingRequest, SessionPayload, TokenData, RiskProfile
)
from app.utils.auth import get_current_user, require_user

router = APIRouter(prefix="/coach", tags=["AI Coaching"])


async def _sse_generator(
    user_id: str,
    session_id: str,
    signals: List[BehavioralSignal],
    risk: RiskProfile,
    memory_sessions,
):
    """Yield SSE-formatted token stream with high-fidelity metadata."""
    # First event: metadata (signals + confidence + risk)
    meta = {
        "event": "metadata",
        "signals": [s.model_dump() for s in signals],
        "risk": risk.model_dump(),
        "referencedSessions": [s.sessionId for s in memory_sessions],
    }
    yield f"data: {json.dumps(meta)}\n\n"

    # Stream LLM tokens
    full_text = []
    async for token in stream_coaching(user_id, session_id, signals, memory_sessions):
        full_text.append(token)
        payload = json.dumps({"event": "token", "data": token})
        yield f"data: {payload}\n\n"

    # Final event
    done = json.dumps({"event": "done", "fullMessage": "".join(full_text)})
    yield f"data: {done}\n\n"


@router.post(
    "/{userId}/sessions/{sessionId}/stream",
    summary="Initiate AI Coaching Stream",
    response_class=StreamingResponse,
    description=(
        "Streams a live, evidence-grounded coaching message via SSE.\n\n"
        "**SSE Event Flow:**\n"
        "1. `metadata`: Real-time behavioral signals, confidence scores, and risk profile.\n"
        "2. `token`: Incremental AI coaching tokens cited with historical session IDs.\n"
        "3. `done`: Final completion event with the full accumulated message."
    )
)
async def coach_stream(
    userId: str,
    sessionId: str,
    body: CoachingRequest,
    token: TokenData = Depends(get_current_user),
):
    require_user(userId, token)

    if not body.trades:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="trades list must not be empty")

    # 1. Detect behavioral signals & Risk Profile (Deterministic)
    signals, risk = analyze_session(sessionId, body.trades)

    # 2. Retrieve memory context (Grounded)
    top_signal = signals[0].signal if signals else None
    memory_sessions = await retrieve_context(userId, relevant_to=top_signal)

    # 3. Auto-save session to memory with Rich Metadata
    pnls = [t.pnl for t in body.trades]
    wins = [t for t in body.trades if t.outcome == "win"]
    payload = SessionPayload(
        userId=userId,
        date=str(body.trades[0].entryAt.date()) if hasattr(body.trades[0].entryAt, "date") else "",
        trades=body.trades,
        tradeCount=len(body.trades),
        winRate=len(wins) / len(body.trades) if body.trades else 0.0,
        totalPnl=sum(pnls),
    )
    
    await store_session(
        session_id=sessionId,
        user_id=userId,
        payload=payload,
        summary=f"Coaching Entry: Risk={risk.level} | Primary={top_signal or 'none'}",
        metrics={"totalPnl": sum(pnls), "winRate": payload.winRate, "riskScore": risk.score},
        tags=[s.signal for s in signals if s.confidence > 0],
        signals=signals,
        risk_profile=risk,
    )

    if not body.streamTokens:
        # Non-streaming: Return rich JSON response
        tokens = []
        async for chunk in stream_coaching(userId, sessionId, signals, memory_sessions):
            tokens.append(chunk)
        return {
            "userId": userId,
            "sessionId": sessionId,
            "message": "".join(tokens),
            "signals": [s.model_dump() for s in signals],
            "risk": risk.model_dump(),
            "referencedSessions": [s.sessionId for s in memory_sessions],
        }

    return StreamingResponse(
        _sse_generator(userId, sessionId, signals, risk, memory_sessions),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
