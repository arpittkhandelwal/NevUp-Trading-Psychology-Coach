"""
Application configuration — reads from environment variables with sensible defaults.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "NevUp Trading Psychology Coach"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/nevup.db"

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str = "nevup-hackathon-secret-2026-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── LLM ──────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"          # "openai" | "groq" | "ollama"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama3-8b-8192"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3"

    # ── Dataset ───────────────────────────────────────────────────────────────
    DATASET_PATH: str = "./nevup_seed_dataset.json"

    # ── Behaviour detection thresholds ───────────────────────────────────────
    REVENGE_WINDOW_SECONDS: int = 90
    OVERTRADING_WINDOW_MINUTES: int = 30
    OVERTRADING_THRESHOLD: int = 10
    SESSION_TILT_LOSS_RATIO: float = 0.6        # ≥60 % loss-following trades
    FOMO_PLAN_ADHERENCE_MAX: int = 2            # planAdherence ≤ 2 + greedy state
    LOSS_RUNNING_PNL_THRESHOLD: float = -200.0  # individual trade pnl
    PREMATURE_EXIT_RATIO: float = 0.5           # wins that close within 5 min
    POSITION_SIZING_CV_THRESHOLD: float = 0.5  # coefficient of variation


@lru_cache
def get_settings() -> Settings:
    return Settings()
