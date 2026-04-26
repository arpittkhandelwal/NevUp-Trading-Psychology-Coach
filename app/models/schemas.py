"""
Enhanced Pydantic schemas — Optimized for Swagger UI and Judge-Ready Docs.
Includes high-fidelity examples and product-focused descriptions.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetClass(str, Enum):
    equity = "equity"
    forex = "forex"
    crypto = "crypto"
    futures = "futures"

class TradeDirection(str, Enum):
    long = "long"
    short = "short"

class TradeStatus(str, Enum):
    open = "open"
    closed = "closed"

class TradeOutcome(str, Enum):
    win = "win"
    loss = "loss"
    breakeven = "breakeven"


# ---------------------------------------------------------------------------
# Core Entities
# ---------------------------------------------------------------------------

class TradeEvent(BaseModel):
    tradeId: str = Field(..., description="Unique UUID for the trade", examples=["f412f236-4edc-47a2-8f54-8763a6ed2ce8"])
    userId: Optional[str] = Field(None, examples=["trader_alpha_1"])
    sessionId: Optional[str] = Field(None, examples=["session_992"])
    asset: str = Field(..., examples=["NVDA"])
    assetClass: AssetClass = Field(default=AssetClass.equity)
    direction: TradeDirection = Field(default=TradeDirection.long)
    entryPrice: float = Field(..., examples=[124.50])
    exitPrice: float = Field(..., examples=[128.20])
    quantity: float = Field(..., examples=[100])
    entryAt: datetime = Field(..., examples=["2026-04-26T10:00:00Z"])
    exitAt: datetime = Field(..., examples=["2026-04-26T10:45:00Z"])
    status: TradeStatus = Field(default=TradeStatus.closed)
    outcome: TradeOutcome = Field(default=TradeOutcome.win)
    pnl: float = Field(..., examples=[370.00])
    planAdherence: int = Field(..., ge=1, le=5, description="1-5 rating of how well the trader followed their plan", examples=[5])
    emotionalState: str = Field(..., examples=["focused", "greedy", "anxious"])
    entryRationale: Optional[str] = Field(None, examples=["Breakout above 20MA with high volume"])
    revengeFlag: bool = Field(default=False, description="Explicit flag for revenge trading entry")


class BehavioralEvidence(BaseModel):
    sessionId: str = Field(..., examples=["session_992"])
    tradeId: str = Field(..., examples=["f412f236-4edc-47a2-8f54-8763a6ed2ce8"])
    detail: str = Field(..., examples=["Entered trade within 45 seconds of a $500 loss on NVDA"])


class BehavioralSignal(BaseModel):
    signal: str = Field(..., examples=["revenge_trading"])
    confidence: float = Field(..., examples=[0.92])
    severity: float = Field(..., examples=[0.95])
    reasoning: str = Field(..., examples=["Repeated impulsive entries after losses detected in NVDA."])
    evidence: List[BehavioralEvidence] = Field(default_factory=list)


class RiskProfile(BaseModel):
    score: int = Field(..., ge=0, le=100, examples=[82])
    level: str = Field(..., examples=["high"])
    drivers: List[str] = Field(default_factory=list, examples=[["revenge_trading", "overtrading"]])
    description: str = Field(..., examples=["Psychological risk is high due to detected revenge trading signatures."])


# ---------------------------------------------------------------------------
# API Payloads & Responses
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    userId: str = Field(..., examples=["f412f236-4edc-47a2-8f54-8763a6ed2ce8"])
    secret: str = Field(..., examples=["nevup2026"])

class TokenResponse(BaseModel):
    accessToken: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    tokenType: str = Field(default="bearer")

class TokenData(BaseModel):
    userId: str

class SessionPayload(BaseModel):
    userId: str = Field(..., examples=["f412f236-4edc-47a2-8f54-8763a6ed2ce8"])
    date: str = Field(..., examples=["2026-04-26"])
    notes: Optional[str] = Field(None, examples=["Challenging market morning, focused on discipline."])
    trades: List[TradeEvent]
    tradeCount: Optional[int] = Field(None, examples=[14])
    winRate: Optional[float] = Field(None, examples=[0.64])
    totalPnl: Optional[float] = Field(None, examples=[1250.45])

class SessionRecord(SessionPayload):
    sessionId: str = Field(..., examples=["session_992"])
    summary: Optional[str] = Field(None, examples=["Session session_992 — 14 trades, PnL=1250.45"])
    metrics: Optional[Dict[str, Any]] = Field(None)
    tags: Optional[List[str]] = Field(None, examples=[["overtrading", "fomo_entries"]])
    signals: List[BehavioralSignal] = Field(default_factory=list)
    risk_profile: Optional[RiskProfile] = Field(None)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

class MemoryContext(BaseModel):
    userId: str
    relevantSessions: List[SessionRecord]
    signal: Optional[str] = None
    retrievedAt: datetime

class CoachingRequest(BaseModel):
    trades: List[TradeEvent]
    streamTokens: bool = Field(default=True, description="Enable SSE token streaming")

class AuditRequest(BaseModel):
    coachingMessage: str = Field(..., examples=["I noticed you entered NVDA right after a loss in S-101. Let's stick to the 15-minute wait rule."])

class AuditResponse(BaseModel):
    isHallucination: bool = Field(..., examples=[False])
    hallucinatedIds: List[str] = Field(default_factory=list)
    validatedIds: List[str] = Field(default_factory=list, examples=[["S-101"]])
    auditLog: str = Field(..., examples=["Validated session S-101. No fabricated IDs detected."])

class ExplanationReport(BaseModel):
    prediction: str = Field(..., examples=["revenge_trading"])
    confidence: float = Field(..., examples=[0.91])
    severity: float = Field(..., examples=[0.95])
    reasoning: str = Field(..., examples=["Repeated impulsive entries after losses detected in NVDA."])
    evidence: List[BehavioralEvidence] = Field(default_factory=list)
    risk: RiskProfile

class ClassMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    support: int

class MistakeRecord(BaseModel):
    sessionId: str
    actual: List[str]
    predicted: str

class EvaluationReport(BaseModel):
    accuracy: float = Field(..., examples=[0.5385])
    macroF1: float = Field(..., examples=[0.5127])
    weightedF1: float = Field(..., examples=[0.5137])
    perSignal: Dict[str, ClassMetrics]
    confusionMatrix: List[Dict[str, Any]]
    topMistakes: List[MistakeRecord]
    weakSignals: List[str]
    evaluatedSessions: int
