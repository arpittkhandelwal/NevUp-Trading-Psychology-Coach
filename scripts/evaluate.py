#!/usr/bin/env python3
"""
Top-Tier Evaluation Script — NevUp Track 2.
Upgraded with Strategic Diagnostics: Macro F1, Weak Signals, and Confusion Matrix.
"""
from __future__ import annotations

import argparse
import json
import sys
import os

# Allow running from repo root without install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.evaluation.harness import run_evaluation

def main():
    parser = argparse.ArgumentParser(description="NevUp Strategic Evaluation Harness")
    parser.add_argument("--dataset", default="./nevup_seed_dataset.json",
                        help="Path to nevup_seed_dataset.json")
    parser.add_argument("--output", default=None,
                        help="Optional path to write JSON report")
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("  NevUp Platinum — Strategic Behavioral Evaluation")
    print(f"  Dataset: {args.dataset}")
    print(f"{'='*70}\n")

    report, extras = run_evaluation(dataset_path=args.dataset)

    # 1. Classification Report
    header = f"{'Signal':<35} {'Precision':>9} {'Recall':>7} {'F1':>7} {'Support':>8}"
    print(header)
    print("-" * len(header))
    for signal, m in sorted(report.perSignal.items()):
        print(f"{signal:<35} {m.precision:>9.4f} {m.recall:>7.4f} {m.f1:>7.4f} {m.support:>8}")

    print("-" * len(header))
    print(f"{'OVERALL ACCURACY':<35} {report.accuracy:>31.4f}")
    print(f"{'MACRO F1 SCORE':<35} {report.macroF1:>31.4f}")
    print(f"{'WEIGHTED F1 SCORE':<35} {report.weightedF1:>31.4f}")
    print(f"SESSIONS EVAL'D  : {report.evaluatedSessions}\n")

    # 2. Weak Signal Identification
    if report.weakSignals:
        print(f"{'!'*70}")
        print(f"  STRATEGIC ALERT: WEAK SIGNALS DETECTED (F1 < 0.4)")
        print(f"  {', '.join(report.weakSignals)}")
        print(f"{'!'*70}\n")

    # 3. Confusion Matrix (Top entries)
    print(f"{'='*70}")
    print("  CONFUSION MATRIX (Top Misclassifications)")
    print(f"{'='*70}")
    print(f"{'Actual Label':<35} | {'Predicted':<35} | {'Count':<5}")
    print("-" * 80)
    
    matrix = extras["confusion"]
    entries = []
    for actual, preds in matrix.items():
        for pred, count in preds.items():
            if actual != pred:
                entries.append((actual, pred, count))
    
    entries.sort(key=lambda x: x[2], reverse=True)
    for actual, pred, count in entries[:10]:
        print(f"{actual:<35} | {pred:<35} | {count:<5}")

    # 4. Top Mistakes
    print(f"\n{'='*70}")
    print("  DIAGNOSTICS: CRITICAL MISCLASSIFICATIONS")
    print(f"{'='*70}")
    for m in report.topMistakes[:5]:
        print(f"Session: {m.sessionId[:8]}... | Actual: {m.actual} | Predicted: {m.predicted}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            combined = {**report.model_dump(), **extras}
            json.dump(combined, fh, indent=2, default=str)
        print(f"\nStrategic Report saved to {args.output}")

if __name__ == "__main__":
    main()
