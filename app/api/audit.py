"""
Audit router — Post-Inference Integrity Verification.
"""
from __future__ import annotations

import re
from fastapi import APIRouter
from app.memory.database import global_session_exists
from app.models.schemas import AuditRequest, AuditResponse

router = APIRouter(prefix="/audit", tags=["Security & Compliance"])

# UUID v4 pattern
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

@router.post(
    "", 
    response_model=AuditResponse, 
    summary="Audit Coach for Integrity & Hallucination",
    description=(
        "Performs a deep-scan of the AI coaching message to extract all referenced UUIDs. "
        "Each ID is cross-referenced against the global memory store to detect potential 'hallucinations' or fabricated evidence."
    )
)
async def audit_coaching(body: AuditRequest) -> AuditResponse:
    # Extract potential session/trade IDs
    raw_ids = _UUID_RE.findall(body.coachingMessage)
    unique_ids = list(dict.fromkeys(raw_ids)) 

    validated = []
    hallucinated = []
    
    for sid in unique_ids:
        exists = await global_session_exists(sid)
        if exists:
            validated.append(sid)
        else:
            hallucinated.append(sid)

    is_hallucination = len(hallucinated) > 0
    status_msg = "All referenced IDs validated." if not is_hallucination else f"Detected {len(hallucinated)} hallucinated IDs."

    return AuditResponse(
        isHallucination=is_hallucination,
        hallucinatedIds=hallucinated,
        validatedIds=validated,
        auditLog=f"Audit complete: {status_msg}"
    )
