"""
Evaluation router — Strategic Diagnostic Harness.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.evaluation.harness import run_evaluation
from app.models.schemas import EvaluationReport

router = APIRouter(prefix="/evaluate", tags=["Strategic Diagnostics"])

@router.post(
    "", 
    response_model=EvaluationReport, 
    summary="Execute Strategic Performance Evaluation",
    description=(
        "Runs a comprehensive evaluation against the ground truth dataset. "
        "Calculates Accuracy, Macro F1, and Weighted F1 scores, and generates a "
        "detailed confusion matrix with misclassification diagnostics."
    )
)
async def evaluate_system() -> EvaluationReport:
    try:
        report, _ = run_evaluation()
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"Strategic evaluation failed: {exc}"
        )
