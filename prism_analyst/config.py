"""Configuration for PRISM Analyst.

Weights, thresholds, decay parameters, and scoring tables are kept in this
single module so output behavior aligns with PRISM-v2 without changes to
workflow code. The tables below are copied from the v2 spec; tweak per-engine
behavior here, never inside renderers or workflows.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .models import SignalType

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

        # Composite scoring weights — matches PRISM-v2 (25/50/25).
        self.icp_weight: float = 0.25
        self.buying_readiness_weight: float = 0.50
        self.timing_weight: float = 0.25

        # Tier thresholds — matches PRISM-v2 (70/45/25 on a 0-100 scale).
        self.tier1_threshold: int = 70
        self.tier2_threshold: int = 45
        self.tier3_threshold: int = 25

        # HTTP settings
        self.http_timeout: int = int(os.getenv("PRISM_ANALYST_HTTP_TIMEOUT", "15"))
        self.user_agent: str = "PrismAnalyst/0.1"

        # Prompt version stamp shared by all renderers/prompts.
        self.prompt_version: str = "v1"


settings = Settings()


# ICP fit subcomponent weights — matches PRISM-v2.
ICP_WEIGHTS: dict[str, float] = {
    "funding_stage": 0.25,
    "growth_rate": 0.20,
    "tech_stack": 0.20,
    "headcount": 0.15,
    "industry": 0.10,
    "geo": 0.10,
}

# Buying readiness subcomponent weights — matches PRISM-v2.
READINESS_WEIGHTS: dict[str, float] = {
    "journey_position": 0.20,
    "pain_coherence": 0.20,
    "new_leader_signal": 0.20,
    "org_stress": 0.15,
    "solution_sophistication": 0.15,
    "active_evaluation": 0.10,
}

# Timing subcomponent weights — matches PRISM-v2.
TIMING_WEIGHTS: dict[str, float] = {
    "trigger_event_recency": 0.35,
    "signal_freshness_avg": 0.25,
    "urgency_indicators": 0.25,
    "window_closing": 0.15,
}


# Per-signal-type decay parameters: (peak_days, half_life_days, max_relevance_days)
# Values copied verbatim from PRISM-v2's signal decay configuration.
SIGNAL_DECAY: dict[SignalType, tuple[int, int, int]] = {
    SignalType.FUNDING_ROUND: (30, 90, 180),
    SignalType.NEW_EXECUTIVE_FINANCE: (60, 150, 365),
    SignalType.NEW_EXECUTIVE_OTHER: (45, 90, 180),
    SignalType.CHAMPION_DEPARTED: (7, 30, 60),
    SignalType.JOB_POSTING_FINANCE: (14, 45, 90),
    SignalType.JOB_POSTING_TECHNICAL: (14, 45, 90),
    SignalType.JOB_POSTING_URGENT: (7, 21, 45),
    SignalType.TECH_STACK_CHANGE: (7, 30, 60),
    SignalType.MIGRATION_SIGNAL: (14, 45, 90),
    SignalType.BLOG_POST_PAIN: (7, 30, 90),
    SignalType.LINKEDIN_POST_PAIN: (3, 14, 30),
    SignalType.EARNINGS_MENTION: (14, 45, 90),
    SignalType.PRESS_RELEASE_RELEVANT: (7, 30, 60),
    SignalType.PRICING_PAGE_VISIT: (1, 7, 21),
    SignalType.CONTENT_ENGAGEMENT: (3, 14, 30),
    SignalType.G2_RESEARCH_ACTIVITY: (7, 21, 45),
    SignalType.COMPETITOR_EVALUATION: (7, 30, 60),
    SignalType.COMPETITOR_CONTRACT_RENEWAL: (30, 60, 120),
    SignalType.GLASSDOOR_TREND: (30, 90, 180),
}


# Funding stage scoring (0..1) — matches PRISM-v2.
FUNDING_STAGE_SCORES: dict[str, float] = {
    "pre-seed": 0.10,
    "preseed": 0.10,
    "seed": 0.30,
    "series a": 0.70,
    "series b": 1.00,
    "series c": 0.95,
    "series d": 0.50,
    "series e": 0.40,
    "bootstrapped": 0.10,
    "public": 0.20,
    "ipo": 0.20,
}

# Industry vertical scores (0..1).
INDUSTRY_SCORES: dict[str, float] = {
    "saas": 1.00,
    "fintech": 0.95,
    "ecommerce": 0.90,
    "e-commerce": 0.90,
    "marketplace": 0.90,
    "b2b services": 0.75,
    "healthcare": 0.70,
    "life sciences": 0.70,
    "tech": 0.60,
    "non-tech": 0.30,
}

# Major North American tech hubs that earn full geo score.
TECH_HUBS: set[str] = {
    "san francisco", "sf", "new york", "nyc", "austin", "seattle", "boston",
    "los angeles", "la", "denver", "chicago", "miami", "palo alto",
    "mountain view", "menlo park", "san jose", "sunnyvale", "cupertino",
    "redwood city", "south san francisco", "ssf",
}


# Engagement play matrix — keyed by (situation, awareness_level, urgency).
# Subset of PRISM-v2's full play matrix, kept human-readable for AE use.
PLAY_MATRIX: dict[str, dict[str, str]] = {
    "educational_urgency": {
        "description": "Pain-aware but uninformed about solutions",
        "sequence": "Education → Diagnostic → Discovery",
        "timeline": "2-week sequence",
    },
    "direct_solution": {
        "description": "Actively exploring with elevated urgency",
        "sequence": "Direct outreach → Demo → Proposal",
        "timeline": "3-day to 1-week",
    },
    "accelerated_close": {
        "description": "Active evaluation under stress",
        "sequence": "Executive intro → POC → Close",
        "timeline": "3-day to 1-week",
    },
    "competitive_wedge": {
        "description": "Competitor in use, evaluating alternatives",
        "sequence": "Competitive teardown → Differentiated demo → Proposal",
        "timeline": "1-week to 3-day",
    },
    "competitive_education": {
        "description": "Has competitor, exploring options",
        "sequence": "Educational drip → Competitive comparison → Discovery",
        "timeline": "2-week sequence",
    },
    "long_nurture": {
        "description": "Status quo, low urgency",
        "sequence": "Quarterly check-ins → Insight drops → Re-evaluate",
        "timeline": "3-month nurture",
    },
    "educational_nurture": {
        "description": "Problem-aware, low urgency",
        "sequence": "Education → POV content → Discovery",
        "timeline": "6-week sequence",
    },
}
