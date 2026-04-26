"""
Dataset loader — seeds the DB from nevup_seed_dataset.json on first run.
Read-only; the dataset file is never modified.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from app.memory.database import get_all_session_ids, upsert_session, upsert_trade
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def seed_database() -> int:
    """
    Load nevup_seed_dataset.json and insert every session + trade that does
    not already exist in the DB.  Returns number of sessions seeded.
    """
    path = settings.DATASET_PATH
    if not os.path.exists(path):
        logger.warning("Dataset not found at %s — skipping seed", path)
        return 0

    with open(path, "r", encoding="utf-8") as fh:
        dataset: Dict[str, Any] = json.load(fh)

    existing = set(await get_all_session_ids())
    seeded = 0

    # Build per-user pathology map from groundTruthLabels
    pathology_map: Dict[str, list] = {
        entry["userId"]: entry.get("pathologies", [])
        for entry in dataset.get("groundTruthLabels", [])
    }

    for trader in dataset.get("traders", []):
        user_id: str = trader["userId"]
        trader_pathologies: list = trader.get("groundTruthPathologies", pathology_map.get(user_id, []))

        for session in trader.get("sessions", []):
            session_id: str = session["sessionId"]
            if session_id in existing:
                continue

            # Compute tags = pathologies that are evidenced in this session
            session_tags = _infer_session_tags(session, trader_pathologies)

            await upsert_session(
                session_id=session_id,
                user_id=user_id,
                date=session.get("date", ""),
                notes=session.get("notes", ""),
                trade_count=session.get("tradeCount"),
                win_rate=session.get("winRate"),
                total_pnl=session.get("totalPnl"),
                summary=trader.get("description", ""),
                metrics={
                    "avgPlanAdherence": trader.get("stats", {}).get("avgPlanAdherence"),
                    "totalPnl": session.get("totalPnl"),
                    "winRate": session.get("winRate"),
                },
                tags=session_tags,
            )

            for trade in session.get("trades", []):
                trade_record = {
                    "tradeId": trade["tradeId"],
                    "userId": user_id,
                    "sessionId": session_id,
                    "asset": trade.get("asset", ""),
                    "assetClass": trade.get("assetClass", "equity"),
                    "direction": trade.get("direction", "long"),
                    "entryPrice": trade.get("entryPrice", 0.0),
                    "exitPrice": trade.get("exitPrice", 0.0),
                    "quantity": trade.get("quantity", 0.0),
                    "entryAt": trade.get("entryAt", ""),
                    "exitAt": trade.get("exitAt", ""),
                    "status": trade.get("status", "closed"),
                    "outcome": trade.get("outcome", "loss"),
                    "pnl": trade.get("pnl", 0.0),
                    "planAdherence": trade.get("planAdherence", 3),
                    "emotionalState": trade.get("emotionalState", "neutral"),
                    "entryRationale": trade.get("entryRationale"),
                    "revengeFlag": trade.get("revengeFlag", False),
                }
                await upsert_trade(trade_record)

            seeded += 1
            existing.add(session_id)

    logger.info("Seeded %d sessions from dataset", seeded)
    return seeded


def _infer_session_tags(session: Dict[str, Any], trader_pathologies: list) -> list:
    """
    Map dataset-level pathologies to session tags.
    Also look at trade-level revengeFlag for fine-grained tagging.
    """
    tags = list(trader_pathologies)  # start with trader-level pathologies

    trades = session.get("trades", [])
    has_revenge = any(t.get("revengeFlag") for t in trades)
    if has_revenge and "revenge_trading" not in tags:
        tags.append("revenge_trading")

    # High trade count in session → overtrading hint
    if session.get("tradeCount", 0) >= 10 and "overtrading" not in tags:
        tags.append("overtrading")

    return tags
