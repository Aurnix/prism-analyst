"""Core data models for PRISM Analyst."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Tier(str, Enum):
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"
    NOT_QUALIFIED = "Not Qualified"


class BuyingStage(str, Enum):
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    EVALUATING = "evaluating"
    DECIDING = "deciding"
    UNKNOWN = "unknown"


class SignalCategory(str, Enum):
    HIRING = "hiring"
    FUNDING = "funding"
    TECHNOLOGY = "technology"
    EXPANSION = "expansion"
    LEADERSHIP = "leadership"
    PRODUCT = "product"
    PAIN = "pain"
    TIMING = "timing"
    COMPETITIVE = "competitive"
    OPERATIONAL = "operational"


class SourceType(str, Enum):
    WEBSITE = "website"
    NEWS = "news"
    JOBS = "jobs"
    GITHUB = "github"
    MANUAL = "manual"


class AccountProfile(BaseModel):
    name: str
    slug: str
    domain: str | None = None
    url: str | None = None
    industry: str | None = None
    headcount: str | None = None
    stage: str | None = None
    location: str | None = None
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceItem(BaseModel):
    id: str = ""
    source_type: SourceType
    url: str | None = None
    title: str = ""
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    content: str = ""
    excerpt: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            raw = f"{self.source_type}:{self.url or self.title}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:12]


class Signal(BaseModel):
    id: str = ""
    category: SignalCategory
    text: str
    source_id: str
    strength: float = Field(ge=0.0, le=1.0, default=0.5)
    recency_days: int | None = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            raw = f"{self.category}:{self.text[:80]}:{self.source_id}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:12]


class Scorecard(BaseModel):
    account_slug: str
    account_name: str
    icp_fit: float = Field(ge=0.0, le=100.0, default=0.0)
    buying_readiness: float = Field(ge=0.0, le=100.0, default=0.0)
    timing: float = Field(ge=0.0, le=100.0, default=0.0)
    composite: float = Field(ge=0.0, le=100.0, default=0.0)
    tier: Tier = Tier.NOT_QUALIFIED
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_reason: str = ""
    signal_count: int = 0
    source_count: int = 0
    scored_at: datetime = Field(default_factory=datetime.utcnow)

    def compute_composite(self) -> None:
        self.composite = round(
            self.icp_fit * 0.35
            + self.buying_readiness * 0.45
            + self.timing * 0.20,
            1,
        )
        if self.composite >= 75:
            self.tier = Tier.TIER_1
        elif self.composite >= 55:
            self.tier = Tier.TIER_2
        elif self.composite >= 35:
            self.tier = Tier.TIER_3
        else:
            self.tier = Tier.NOT_QUALIFIED


class EvidenceItem(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    url: str | None = None
    date: str | None = None
    excerpt: str
    signal_types: list[SignalCategory] = Field(default_factory=list)
    relevance_reason: str = ""
    strength: float = 0.5


class EvidencePack(BaseModel):
    account_slug: str
    items: list[EvidenceItem] = Field(default_factory=list)
    built_at: datetime = Field(default_factory=datetime.utcnow)
    prompt_version: str = "v1"
    model: str = ""

    def content_hash(self) -> str:
        blob = json.dumps(
            [item.model_dump(mode="json") for item in self.items],
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


class Brief(BaseModel):
    account_slug: str
    account_read: str = ""
    important_signals: str = ""
    buying_stage: BuyingStage = BuyingStage.UNKNOWN
    why_now: str = ""
    recommended_action: str = ""
    outreach_angle: str = ""
    collection_gaps: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    raw_llm_output: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model: str = ""
    prompt_version: str = "v1"
    evidence_hash: str = ""


class DossierSection(BaseModel):
    title: str
    content: str


class Dossier(BaseModel):
    account_slug: str
    sections: list[DossierSection] = Field(default_factory=list)
    raw_llm_output: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model: str = ""
    prompt_version: str = "v1"
    evidence_hash: str = ""


class GiftDocument(BaseModel):
    account_slug: str
    content: str = ""
    redacted_items: list[str] = Field(default_factory=list)
    raw_llm_output: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model: str = ""


class RunSnapshot(BaseModel):
    account_slug: str
    run_id: str
    signals: list[Signal] = Field(default_factory=list)
    scorecard: Scorecard | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignalDelta(BaseModel):
    category: str
    description: str
    change_type: str  # "new", "changed", "decayed", "removed"


class Digest(BaseModel):
    account_slug: str
    previous_run_id: str
    current_run_id: str
    new_signals: list[SignalDelta] = Field(default_factory=list)
    changed_signals: list[SignalDelta] = Field(default_factory=list)
    decayed_signals: list[SignalDelta] = Field(default_factory=list)
    score_change: float = 0.0
    is_material: bool = False
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
