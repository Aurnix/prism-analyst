"""Configuration for PRISM Analyst."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.model: str = os.getenv("PRISM_ANALYST_MODEL", "claude-sonnet-4-6")
        self.max_evidence_items: int = int(
            os.getenv("PRISM_ANALYST_MAX_EVIDENCE_ITEMS", "10")
        )
        self.full_threshold: int = int(
            os.getenv("PRISM_ANALYST_FULL_THRESHOLD", "70")
        )
        self.quick_threshold: int = int(
            os.getenv("PRISM_ANALYST_QUICK_THRESHOLD", "45")
        )
        self.cache_ttl_days: int = int(
            os.getenv("PRISM_ANALYST_CACHE_TTL_DAYS", "14")
        )
        self.workspace_dir: Path = Path(
            os.getenv("PRISM_ANALYST_WORKSPACE", ".prism")
        )
        self.output_dir: Path = Path(
            os.getenv("PRISM_ANALYST_OUTPUT", "output")
        )

        # Scoring weights
        self.icp_weight: float = 0.35
        self.buying_readiness_weight: float = 0.45
        self.timing_weight: float = 0.20

        # Tier thresholds
        self.tier1_threshold: int = 75
        self.tier2_threshold: int = 55
        self.tier3_threshold: int = 35

        # HTTP settings
        self.http_timeout: int = int(os.getenv("PRISM_ANALYST_HTTP_TIMEOUT", "15"))
        self.user_agent: str = "PrismAnalyst/0.1"


settings = Settings()
