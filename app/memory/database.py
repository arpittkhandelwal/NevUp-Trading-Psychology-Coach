"""
SQLite database layer — Upgraded for NevUp Hackathon 2026.
Added global session existence check for the Anti-Hallucination Audit tool.
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiosqlite

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT    PRIMARY KEY,
    user_id      TEXT    NOT NULL,
    date         TEXT    NOT NULL,
    notes        TEXT    DEFAULT '',
    trade_count  INTEGER,
    win_rate     REAL,
    total_pnl    REAL,
    summary      TEXT,
    metrics      TEXT,   -- JSON blob
    tags         TEXT,   -- JSON array (legacy/compatibility)
    signals      TEXT,   -- JSON blob (Rich BehavioralSignal list)
    risk_profile TEXT,   -- JSON blob (RiskProfile object)
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id          TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    session_id        TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    asset             TEXT NOT NULL,
    asset_class       TEXT NOT NULL,
    direction         TEXT NOT NULL,
    entry_price       REAL NOT NULL,
    exit_price        REAL NOT NULL,
    quantity          REAL NOT NULL,
    entry_at          TEXT NOT NULL,
    exit_at           TEXT NOT NULL,
    status            TEXT NOT NULL,
    outcome           TEXT NOT NULL,
    pnl               REAL NOT NULL,
    plan_adherence    INTEGER NOT NULL,
    emotional_state   TEXT NOT NULL,
    entry_rationale   TEXT,
    revenge_flag      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_user     ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_session    ON trades(session_id);
CREATE INDEX IF NOT EXISTS idx_trades_user       ON trades(user_id);
"""


async def init_db() -> None:
    import os
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_DDL)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN signals TEXT")
            await db.execute("ALTER TABLE sessions ADD COLUMN risk_profile TEXT")
        except: pass 
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH)


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

async def session_exists(session_id: str, user_id: str) -> bool:
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM sessions WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        ) as cur:
            return await cur.fetchone() is not None


async def global_session_exists(session_id: str) -> bool:
    """Check existence across all users — required for Audit Tool."""
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM sessions WHERE session_id=?",
            (session_id,),
        ) as cur:
            return await cur.fetchone() is not None


async def get_all_session_ids() -> List[str]:
    async with get_db() as db:
        async with db.execute("SELECT session_id FROM sessions") as cur:
            return [r["session_id"] for r in await cur.fetchall()]


async def upsert_session(
    session_id: str,
    user_id: str,
    date: str,
    notes: str = "",
    trade_count: Optional[int] = None,
    win_rate: Optional[float] = None,
    total_pnl: Optional[float] = None,
    summary: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    signals: Optional[List[Dict[str, Any]]] = None,
    risk_profile: Optional[Dict[str, Any]] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    metrics_json = json.dumps(metrics) if metrics is not None else None
    tags_json = json.dumps(tags) if tags is not None else None
    signals_json = json.dumps(signals) if signals is not None else None
    risk_json = json.dumps(risk_profile) if risk_profile is not None else None

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO sessions
                (session_id, user_id, date, notes, trade_count, win_rate, total_pnl,
                 summary, metrics, tags, signals, risk_profile, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(session_id) DO UPDATE SET
                user_id      = excluded.user_id,
                date         = excluded.date,
                notes        = excluded.notes,
                trade_count  = excluded.trade_count,
                win_rate     = excluded.win_rate,
                total_pnl    = excluded.total_pnl,
                summary      = excluded.summary,
                metrics      = excluded.metrics,
                tags         = excluded.tags,
                signals      = excluded.signals,
                risk_profile = excluded.risk_profile,
                updated_at   = excluded.updated_at
            """,
            (session_id, user_id, date, notes, trade_count, win_rate, total_pnl,
             summary, metrics_json, tags_json, signals_json, risk_json, now, now),
        )
        await db.commit()


async def upsert_trade(trade: Dict[str, Any]) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO trades
                (trade_id, user_id, session_id, asset, asset_class, direction,
                 entry_price, exit_price, quantity, entry_at, exit_at, status,
                 outcome, pnl, plan_adherence, emotional_state, entry_rationale, revenge_flag)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(trade_id) DO UPDATE SET
                outcome          = excluded.outcome,
                pnl              = excluded.pnl,
                plan_adherence   = excluded.plan_adherence,
                emotional_state  = excluded.emotional_state,
                entry_rationale  = excluded.entry_rationale,
                revenge_flag     = excluded.revenge_flag
            """,
            (
                trade["tradeId"],
                trade["userId"],
                trade["sessionId"],
                trade["asset"],
                trade["assetClass"],
                trade["direction"],
                trade["entryPrice"],
                trade["exitPrice"],
                trade["quantity"],
                trade["entryAt"] if isinstance(trade["entryAt"], str) else trade["entryAt"].isoformat(),
                trade["exitAt"] if isinstance(trade["exitAt"], str) else trade["exitAt"].isoformat(),
                trade["status"],
                trade["outcome"],
                trade["pnl"],
                trade["planAdherence"],
                trade["emotionalState"],
                trade.get("entryRationale"),
                1 if trade.get("revengeFlag") else 0,
            ),
        )
        await db.commit()


async def get_session(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM sessions WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        ) as cur:
            row = await cur.fetchone()
            if not row: return None
            session = dict(row)

        async with db.execute(
            "SELECT * FROM trades WHERE session_id=? ORDER BY entry_at",
            (session_id,),
        ) as cur:
            trades = [dict(r) for r in await cur.fetchall()]

        session["trades"] = trades
        session["metrics"] = json.loads(session["metrics"]) if session["metrics"] else None
        session["tags"] = json.loads(session["tags"]) if session["tags"] else None
        session["signals"] = json.loads(session["signals"]) if session["signals"] else []
        session["risk_profile"] = json.loads(session["risk_profile"]) if session["risk_profile"] else None
        return session


async def get_sessions_for_user(user_id: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM sessions WHERE user_id=? ORDER BY date DESC",
            (user_id,),
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

        for sess in rows:
            async with db.execute(
                "SELECT * FROM trades WHERE session_id=? ORDER BY entry_at",
                (sess["session_id"],),
            ) as cur:
                sess["trades"] = [dict(r) for r in await cur.fetchall()]
            sess["metrics"] = json.loads(sess["metrics"]) if sess["metrics"] else None
            sess["tags"] = json.loads(sess["tags"]) if sess["tags"] else None
            sess["signals"] = json.loads(sess["signals"]) if sess["signals"] else []
            sess["risk_profile"] = json.loads(sess["risk_profile"]) if sess["risk_profile"] else None
        return rows


async def get_sessions_by_tag(user_id: str, tag: str) -> List[Dict[str, Any]]:
    all_sess = await get_sessions_for_user(user_id)
    return [s for s in all_sess if tag in (s.get("tags") or [])]
