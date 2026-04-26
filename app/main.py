"""
NevUp Trading Psychology Coach — High-Precision Entry Point.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api import audit, auth, coaching, evaluation, memory
from app.memory.database import init_db
from app.utils.config import get_settings
from app.utils.dataset_loader import seed_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    os.makedirs("data", exist_ok=True)
    await init_db()
    seeded = await seed_database()
    logger.info("Seeded %d new sessions from dataset", seeded)
    yield
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# App Configuration (Judge-Ready Docs)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="🧠 NevUp Trading Psychology Coach",
    version="1.0.0",
    description=(
        "### Stateful AI Trading Psychology Coach\n\n"
        "**Platinum Submission Feature-Set:**\n"
        "*   **Deterministic Behavioral Profiling**: Rule-based detection of trading pathologies.\n"
        "*   **Explainability Layer (XAI)**: Evidence-grounded reasoning with trade-level citations.\n"
        "*   **Quantitative Risk Intelligence**: 0-100 risk scoring for psychological exposure.\n"
        "*   **SSE Coaching Stream**: Real-time actionable guidance via pluggable LLM architecture.\n"
        "*   **Anti-Hallucination Audit**: Post-inference verification of referenced IDs.\n"
        "*   **Strategic Evaluation Harness**: Deep-dive analytics for model performance monitoring."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Error Handling
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(memory.router)
app.include_router(coaching.router)
app.include_router(audit.router)
app.include_router(evaluation.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"], summary="Service Health & Configuration Status")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llmProvider": settings.LLM_PROVIDER,
        "features": ["XAI", "RiskScoring", "SSE", "Audit"]
    }
