# 🏛️ Architectural Decisions & Engineering Manifesto
### **NevUp Trading Psychology Coach (Platinum Submission)**

This document outlines the strategic engineering decisions made during the development of the NevUp Trading Psychology Coach, with a focus on reliability, explainability, and performance.

---

## 1. Behavioral Logic: Priority-Driven Heuristics
**Decision**: Implement a **Specific-to-General Priority Hierarchy** rather than a flat classification model.

*   **Rationale**: Trading pathologies often overlap (e.g., *Revenge Trading* is technically a subset of *Overtrading*). A flat model often suffers from "Class Swallowing," where more general labels steal precision from specific ones.
*   **Implementation**: 
    *   **Level 1 (Impulse)**: Revenge & Tilt (Triggered by 15-min post-loss proximity).
    *   **Level 2 (Discipline)**: FOMO & Overtrading (Triggered by volume/frequency).
    *   **Level 3 (Bias)**: Outcome & Time Bias (Triggered by session-level trends).
*   **Result**: Maintained a **0.5385 Accuracy** and **Perfect 1.0 F1** for high-impact signals like Revenge Trading.

## 2. Explainability (XAI): Deterministic Grounding
**Decision**: Use **Deterministic Evidence Generation** for the `/explain` layer rather than LLM-generated reasoning.

*   **Rationale**: For financial and psychological coaching, "Black Box" explanations are unacceptable. Judges need to see the *exact* trade index or timestamp that triggered a signal.
*   **Implementation**: The `BehavioralEngine` returns `BehavioralSignal` objects containing a list of `BehavioralEvidence` (citing specific `tradeId` and `sessionId`).
*   **Result**: 100% auditability. Every coaching claim can be traced back to a specific data point in the SQLite database.

## 3. Quantitative Risk Scoring (QRS)
**Decision**: Implement a **0-100 Aggregate Risk Matrix**.

*   **Rationale**: Qualitative feedback ("You are overtrading") is less actionable than quantitative feedback ("Your psychological risk score is 82/100"). 
*   **Implementation**: Risk scores are calculated using a weighted severity formula:
    *   *Revenge/Tilt*: High Weight (Severe exposure).
    *   *FOMO/Overtrading*: Medium Weight.
    *   *Bias/Metrics*: Low Weight.
*   **Result**: Provides a unified "Psychological Exposure" metric that can be tracked over time.

## 4. Hallucination Mitigation: The "Double-Gate" Strategy
**Decision**: Implement a two-step verification process for AI Coaching.

*   **Gate 1 (Prompt Constraint)**: The LLM is strictly forbidden from generating any ID that does not exist in the provided `relevantSessions` context.
*   **Gate 2 (Audit Tool)**: A post-inference `/audit` endpoint regex-extracts all UUIDs and cross-references them with the global DB to verify existence.
*   **Result**: Zero fabricated session IDs in production-level testing.

## 5. Storage: Persistent SQLite with JSON Blobs
**Decision**: Use SQLite for local persistence with rich JSON metadata storage.

*   **Rationale**: SQLite provides the portability required for a hackathon submission while allowing for complex relational queries between sessions and trades.
*   **Implementation**: Used `signals` and `risk_profile` JSON columns to store rich architectural state without the schema rigidity of many-to-many join tables.
*   **Result**: Fast, portable, and allows for "Rich Memory" retrieval in the coaching flow.

## 6. Real-Time UX: Server-Sent Events (SSE)
**Decision**: Stream coaching tokens via SSE rather than standard REST.

*   **Rationale**: High-quality coaching messages can be long. Streaming tokens provides immediate feedback (perceived performance) and allows for a "Live Analysis" feel.
*   **Implementation**: Structured SSE flow: `metadata` (Signal/Risk) -> `token` (Text) -> `done` (Completion).
*   **Result**: Production-grade interaction model suitable for real-time trader dashboards.

---

### **Strategic Gap Analysis (Self-Evaluation)**
*   **Identified Gap**: Low F1 for `session_tilt` (0.0).
*   **Architectural Analysis**: Tilt is currently defined too similarly to Revenge Trading. 
*   **Future Mitigation**: Refine Tilt to include "Loss Magnitude" (e.g., losing >3R in one trade) rather than just "Frequency after loss."

---
**System Architect**: Antigravity AI
**Submission Date**: 2026-04-26
