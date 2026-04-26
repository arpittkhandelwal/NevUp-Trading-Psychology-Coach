"""
Pluggable LLM client — Upgraded with High-Precision Coaching Prompt.
Enforces evidence grounding and actionable psychological protocols.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, List

from app.models.schemas import BehavioralSignal, SessionRecord
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# High-Precision Prompt Builder
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    return (
        "You are NevUp Platinum, an elite trading performance architect. "
        "Your mission is to provide surgical, evidence-based psychological coaching. "
        "STRICT CONSTRAINTS:\n"
        "1. ONLY reference session IDs and trade IDs provided in the context.\n"
        "2. EVERY observation must be grounded in a specific tradeId or sessionId.\n"
        "3. Focus on the MOST severe pathology detected (the first one in the list).\n"
        "4. Be direct, authoritative, yet empathetic. Avoid fluff.\n"
        "5. Structure: [Diagnosis] -> [Historical Comparison] -> [Protocol]."
    )


def _build_user_prompt(
    user_id: str,
    session_id: str,
    signals: List[BehavioralSignal],
    memory_sessions: List[SessionRecord],
) -> str:
    # Build Memory Context
    mem_lines = []
    for s in memory_sessions:
        sigs = [sig.signal for sig in s.signals] if s.signals else (s.tags or ["none"])
        mem_lines.append(f"  * Session {s.sessionId} | PnL: {s.totalPnl:.2f} | Pathologies: {', '.join(sigs)}")
    memory_block = "\n".join(mem_lines) if mem_lines else "  (No historical baseline available)"

    # Build Signal Context
    sig_lines = []
    for sig in signals:
        ev_ids = [e.tradeId for e in sig.evidence if e.tradeId != "N/A"]
        sig_lines.append(f"  * {sig.signal.upper()} (Confidence: {sig.confidence:.2f})\n    - Reasoning: {sig.reasoning}\n    - Trades: {', '.join(ev_ids) or 'Multiple'}")
    signal_block = "\n".join(sig_lines) if sig_lines else "  * No specific pathologies detected."

    return f"""
TRADER ID: {user_id}
ACTIVE SESSION: {session_id}

== DETECTED PATHOLOGIES (CURRENT) ==
{signal_block}

== HISTORICAL BASELINE ==
{memory_block}

INSTRUCTIONS:
1. Address the trader by their ID.
2. Diagnose the root psychological issue in the current session (cite specific tradeIds).
3. Connect this to the Historical Baseline (cite specific past sessionIds if patterns repeat).
4. Provide a 'Next Session Protocol': 2 specific, actionable rules to prevent recurrence.
5. Keep the total response under 250 words.
""".strip()


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

async def _stream_openai(system: str, user: str) -> AsyncGenerator[str, None]:
    import openai 
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    stream = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        stream=True,
        max_tokens=500,
        temperature=0.3, # Lower temperature for precision
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta: yield delta


async def _stream_groq(system: str, user: str) -> AsyncGenerator[str, None]:
    import httpx
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": True, "max_tokens": 500, "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]": break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content", "")
                        if delta: yield delta
                    except: pass


async def _stream_ollama(system: str, user: str) -> AsyncGenerator[str, None]:
    import httpx
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120, base_url=settings.OLLAMA_BASE_URL) as client:
        async with client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    try:
                        obj = json.loads(line)
                        delta = obj.get("message", {}).get("content", "")
                        if delta: yield delta
                    except: pass


async def _stream_fallback(system: str, user: str) -> AsyncGenerator[str, None]:
    msg = "LLM provider not configured. Deterministic behavioral analysis is complete and available in the response metadata."
    for word in msg.split():
        yield word + " "
        await asyncio.sleep(0.02)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def stream_coaching(
    user_id: str,
    session_id: str,
    signals: List[BehavioralSignal],
    memory_sessions: List[SessionRecord],
) -> AsyncGenerator[str, None]:
    system = _build_system_prompt()
    user_msg = _build_user_prompt(user_id, session_id, signals, memory_sessions)

    provider = settings.LLM_PROVIDER.lower()
    try:
        if provider == "openai" and settings.OPENAI_API_KEY:
            gen = _stream_openai(system, user_msg)
        elif provider == "groq" and settings.GROQ_API_KEY:
            gen = _stream_groq(system, user_msg)
        elif provider == "ollama":
            gen = _stream_ollama(system, user_msg)
        else:
            gen = _stream_fallback(system, user_msg)

        async for token in gen:
            yield token
    except Exception as exc:
        logger.error("LLM streaming error: %s", exc)
        yield f"\n[Coaching Stream Interrupted: {exc}]"
