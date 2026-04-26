"""
Enhanced Evaluation Harness — NevUp Hackathon 2026 TOP-TIER.
Upgraded with Confusion Matrix, Weak Signal Analysis, and Macro F1 tracking.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from app.engine.behavioral import analyze_session, _SIGNAL_NAMES
from app.models.schemas import (
    ClassMetrics, EvaluationReport, TradeEvent, MistakeRecord
)
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ALL_LABELS = _SIGNAL_NAMES

def _load_dataset(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def _parse_trades(raw_trades: List[Dict[str, Any]], user_id: str, session_id: str) -> List[TradeEvent]:
    trades = []
    for t in raw_trades:
        try:
            trades.append(TradeEvent(
                tradeId=t["tradeId"],
                userId=user_id,
                sessionId=session_id,
                asset=t.get("asset", ""),
                assetClass=t.get("assetClass", "equity"),
                direction=t.get("direction", "long"),
                entryPrice=float(t.get("entryPrice", 0)),
                exitPrice=float(t.get("exitPrice", 0)),
                quantity=float(t.get("quantity", 0)),
                entryAt=t.get("entryAt", ""),
                exitAt=t.get("exitAt", ""),
                status=t.get("status", "closed"),
                outcome=t.get("outcome", "loss"),
                pnl=float(t.get("pnl", 0)),
                planAdherence=int(t.get("planAdherence", 3)),
                emotionalState=t.get("emotionalState", "neutral"),
                entryRationale=t.get("entryRationale"),
                revengeFlag=bool(t.get("revengeFlag", False)),
            ))
        except: continue
    return trades

def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0

def run_evaluation(dataset_path: str | None = None) -> Tuple[EvaluationReport, Dict[str, Any]]:
    path = dataset_path or settings.DATASET_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")

    dataset = _load_dataset(path)
    gt_map: Dict[str, Set[str]] = {}
    for entry in dataset.get("groundTruthLabels", []):
        gt_map[entry["userId"]] = set(entry.get("pathologies", []))

    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    confusion = defaultdict(lambda: defaultdict(int)) 
    mistakes: List[MistakeRecord] = []
    
    total_sessions = 0
    correct_sessions = 0

    for trader in dataset.get("traders", []):
        user_id = trader["userId"]
        gt_labels = gt_map.get(user_id, set())
        if not gt_labels: gt_labels = {"none"}

        for session in trader.get("sessions", []):
            session_id = session["sessionId"]
            trades = _parse_trades(session.get("trades", []), user_id, session_id)
            if not trades: continue

            total_sessions += 1
            signals, _ = analyze_session(session_id, trades)
            prediction = signals[0].signal if signals else "none"
            
            actual_label = list(gt_labels)[0]
            confusion[actual_label][prediction] += 1
            
            if prediction in gt_labels:
                correct_sessions += 1
            else:
                mistakes.append(MistakeRecord(
                    sessionId=session_id,
                    actual=list(gt_labels),
                    predicted=prediction
                ))

            for label in ALL_LABELS:
                pred_bool = (prediction == label)
                actual_bool = (label in gt_labels)
                if pred_bool and actual_bool: tp[label] += 1
                elif pred_bool and not actual_bool: fp[label] += 1
                elif not pred_bool and actual_bool: fn[label] += 1

    per_signal = {}
    weak_signals = []
    for label in ALL_LABELS:
        p = _safe_div(tp[label], tp[label] + fp[label])
        r = _safe_div(tp[label], tp[label] + fn[label])
        f1 = _safe_div(2 * p * r, p + r)
        support = tp[label] + fn[label]
        per_signal[label] = ClassMetrics(
            precision=round(p, 4), recall=round(r, 4), f1=round(f1, 4), support=support
        )
        if support > 0 and f1 < 0.4:
            weak_signals.append(label)

    # Averages
    macro_f1 = round(sum(m.f1 for m in per_signal.values()) / len(ALL_LABELS), 4)
    total_support = sum(m.support for m in per_signal.values()) or 1
    weighted_f1 = round(sum(m.f1 * m.support for m in per_signal.values()) / total_support, 4)

    # Flatten confusion matrix for JSON response
    matrix_flat = []
    for actual, preds in confusion.items():
        for pred, count in preds.items():
            matrix_flat.append({"actual": actual, "predicted": pred, "count": count})

    report = EvaluationReport(
        accuracy=round(_safe_div(correct_sessions, total_sessions), 4),
        macroF1=macro_f1,
        weightedF1=weighted_f1,
        perSignal=per_signal,
        confusionMatrix=matrix_flat,
        topMistakes=mistakes[:5],
        weakSignals=weak_signals,
        evaluatedSessions=total_sessions
    )
    
    return report, {"confusion": confusion, "mistakes": mistakes}
