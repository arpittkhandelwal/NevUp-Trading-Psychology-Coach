"""
Memory service — Upgraded to handle Rich Signals and Risk Profiles.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.memory.database import (
    get_session, get_sessions_by_tag, get_sessions_for_user,
    upsert_session, upsert_trade,
)
from app.models.schemas import SessionPayload, SessionRecord, TradeEvent, BehavioralSignal, RiskProfile

logger = logging.getLogger(__name__)

_SIGNAL_TAGS = {
    "revenge_trading", "overtrading", "fomo_entries", "plan_non_adherence",
    "premature_exit", "loss_running", "session_tilt",
    "time_of_day_bias", "position_sizing_inconsistency",
}


def _row_to_record(row: Dict[str, Any]) -> SessionRecord:
    trades = []
    for t in row.get("trades", []):
        try:
            trades.append(TradeEvent(
                tradeId=t.get("trade_id", t.get("tradeId", "")),
                userId=t.get("user_id", t.get("userId", "")),
                sessionId=t.get("session_id", t.get("sessionId", "")),
                asset=t.get("asset", ""),
                assetClass=t.get("asset_class", t.get("assetClass", "equity")),
                direction=t.get("direction", "long"),
                entryPrice=float(t.get("entry_price", t.get("entryPrice", 0))),
                exitPrice=float(t.get("exit_price", t.get("exitPrice", 0))),
                quantity=float(t.get("quantity", 0)),
                entryAt=t.get("entry_at", t.get("entryAt", datetime.utcnow().isoformat())),
                exitAt=t.get("exit_at", t.get("exitAt", datetime.utcnow().isoformat())),
                status=t.get("status", "closed"),
                outcome=t.get("outcome", "loss"),
                pnl=float(t.get("pnl", 0)),
                planAdherence=int(t.get("plan_adherence", t.get("planAdherence", 3))),
                emotionalState=t.get("emotional_state", t.get("emotionalState", "neutral")),
                entryRationale=t.get("entry_rationale", t.get("entryRationale")),
                revengeFlag=bool(t.get("revenge_flag", t.get("revengeFlag", False))),
            ))
        except Exception as exc:
            logger.warning("Skipping malformed trade: %s", exc)

    return SessionRecord(
        sessionId=row.get("session_id", row.get("sessionId", "")),
        userId=row.get("user_id", row.get("userId", "")),
        date=row.get("date", ""),
        notes=row.get("notes", ""),
        tradeCount=row.get("trade_count", row.get("tradeCount")),
        winRate=row.get("win_rate", row.get("winRate")),
        totalPnl=row.get("total_pnl", row.get("totalPnl")),
        summary=row.get("summary"),
        metrics=row.get("metrics"),
        tags=row.get("tags"),
        signals=[BehavioralSignal(**s) for s in row.get("signals", [])] if row.get("signals") else [],
        risk_profile=RiskProfile(**row["risk_profile"]) if row.get("risk_profile") else None,
        trades=trades,
        createdAt=row.get("created_at"),
        updatedAt=row.get("updated_at"),
    )


async def store_session(
    session_id: str, user_id: str, payload: SessionPayload,
    summary: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    signals: Optional[List[BehavioralSignal]] = None,
    risk_profile: Optional[RiskProfile] = None,
) -> SessionRecord:
    await upsert_session(
        session_id=session_id, user_id=user_id, date=payload.date,
        notes=payload.notes or "", trade_count=payload.tradeCount or len(payload.trades),
        win_rate=payload.winRate, total_pnl=payload.totalPnl,
        summary=summary, metrics=metrics, tags=tags,
        signals=[s.model_dump() for s in signals] if signals else None,
        risk_profile=risk_profile.model_dump() if risk_profile else None,
    )
    for trade in payload.trades:
        td = trade.model_dump()
        td["userId"] = user_id
        td["sessionId"] = session_id
        td["entryAt"] = trade.entryAt.isoformat() if hasattr(trade.entryAt, "isoformat") else trade.entryAt
        td["exitAt"] = trade.exitAt.isoformat() if hasattr(trade.exitAt, "isoformat") else trade.exitAt
        await upsert_trade(td)
    row = await get_session(session_id, user_id)
    return _row_to_record(row)


async def retrieve_session(session_id: str, user_id: str) -> Optional[SessionRecord]:
    row = await get_session(session_id, user_id)
    return _row_to_record(row) if row else None


async def retrieve_context(user_id: str, relevant_to: Optional[str] = None) -> List[SessionRecord]:
    if relevant_to and relevant_to in _SIGNAL_TAGS:
        rows = await get_sessions_by_tag(user_id, relevant_to)
        if rows:
            rows.sort(key=lambda r: r.get("date", ""), reverse=True)
            return [_row_to_record(r) for r in rows[:5]]
    rows = await get_sessions_for_user(user_id)
    rows.sort(key=lambda r: (r.get("total_pnl") or 0.0))
    return [_row_to_record(r) for r in rows[:5]]
