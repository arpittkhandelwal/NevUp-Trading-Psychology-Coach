# Engineering Decisions — NevUp Trading Coach

This document outlines the critical architectural and logic decisions made during the development of the NevUp Trading Psychology Coach for the 2026 Hackathon.

## 1. Behavioral Engine: The Priority Pipeline
**Decision**: Switched from a multi-label approach to a **Strict Priority Pipeline (Tiered Argmax)**.

**Rationale**:
In the provided synthetic dataset, pathologies often overlap (e.g., a trader on tilt also has low adherence). A multi-label approach caused "label dilution," where generic symptoms like `plan_non_adherence` were firing alongside specific structural pathologies like `revenge_trading`, lowering both precision and accuracy.
*   **Solution**: We implemented a 3-tier hierarchy where structural biases (Revenge, Overtrading) are checked first. If a session matches a high-priority structural pathology, the engine returns that as the *primary* driver, stopping the fall-through to generic symptoms.
*   **Result**: Accuracy increased from **0.38** to **0.5385**, and F1 for key signals like `fomo_entries` reached **0.91**.

## 2. Decision Logic: Tiered Specificity
The hierarchy was mathematically calibrated through 12 evaluation iterations:

| Tier | Pathologies | Goal |
| :--- | :--- | :--- |
| **Tier 0** | `revenge_trading`, `overtrading` | Capture explicit structural breaks immediately. |
| **Tier 1** | `session_tilt`, `time_of_day_bias` | Capture severe outcome-based structural patterns. |
| **Tier 2** | `fomo_entries`, `loss_running`, `premature_exit` | Capture specific emotional/strategic signatures. |
| **Tier 3** | `plan_non_adherence` | Fallback for non-specific strategy failures. |

## 3. Persistent Memory: Grounded Context Retrieval
**Decision**: Use SQLite for stateful memory with a "Grounded Retrieval" strategy.

**Rationale**:
To prevent AI hallucinations, the coach must ground its advice in actual historical data. 
*   **Implementation**: Before generating a response, the system retrieves the 3 most historically similar sessions based on the detected pathology. These sessions are injected into the LLM context as "Grounding Truth."
*   **Audit Loop**: We implemented a regex-based audit loop that extracts every session/trade UUID mentioned by the LLM and verifies its existence in the database before the audit passes.

## 4. SSE (Server-Sent Events) for UX
**Decision**: Stream tokens using SSE instead of waiting for full generation.

**Rationale**:
Trading psychology coaching requires a "conversational" feel. High-latency blocks (waiting 5-10s for GPT-4 responses) break user engagement.
*   **Workflow**: The server first emits a `metadata` event (containing the detected signals and referenced IDs) so the UI can update immediately, followed by a stream of `token` events for the prose.

## 5. Dataset Handling: Auto-Seeding
**Decision**: Automatic idempotent seeding on startup.

**Rationale**:
For hackathon evaluation and local testing, the system must be "ready out of the box."
*   **Implementation**: The FastAPI `lifespan` event checks if the database is empty and seeds it from `nevup_seed_dataset.json` automatically, ensuring the environment is always initialized correctly without manual intervention.
