"""Core data models for PRISM Analyst.

The model layer mirrors PRISM-v2's signal taxonomy, scoring breakdown, dossier
sections, and digest schema so outputs stay interchangeable between the two
systems. PRISM Analyst keeps a lighter footprint (filesystem state, optional
LLM, no DB) but produces the same kinds of artifacts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Account-level confidence label shown next to scores."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SignalConfidence(str, Enum):
    """Per-signal confidence tag — matches PRISM-v2's three-state taxonomy.

    - extracted:    pulled verbatim from a source (highest fidelity)
    - interpolated: inferred from adjacent text or pattern (default)
    - generated:    produced by an LLM synthesis pass
    """

    EXTRACTED = "extracted"
    INTERPOLATED = "interpolated"
    GENERATED = "generated"


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
    """Coarse AE-friendly bucket each SignalType rolls up to.

    Used for snapshot grouping and weight assignment in the scoring engine.
    """

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


class SignalType(str, Enum):
    """The 19 PRISM-v2 signal types, kept verbatim for output compatibility."""

    FUNDING_ROUND = "funding_round"
    NEW_EXECUTIVE_FINANCE = "new_executive_finance"
    NEW_EXECUTIVE_OTHER = "new_executive_other"
    CHAMPION_DEPARTED = "champion_departed"
    JOB_POSTING_FINANCE = "job_posting_finance"
    JOB_POSTING_TECHNICAL = "job_posting_technical"
    JOB_POSTING_URGENT = "job_posting_urgent"
    TECH_STACK_CHANGE = "tech_stack_change"
    MIGRATION_SIGNAL = "migration_signal"
    BLOG_POST_PAIN = "blog_post_pain"
    LINKEDIN_POST_PAIN = "linkedin_post_pain"
    EARNINGS_MENTION = "earnings_mention"
    PRESS_RELEASE_RELEVANT = "press_release_relevant"
    PRICING_PAGE_VISIT = "pricing_page_visit"
    CONTENT_ENGAGEMENT = "content_engagement"
    G2_RESEARCH_ACTIVITY = "g2_research_activity"
    COMPETITOR_EVALUATION = "competitor_evaluation"
    COMPETITOR_CONTRACT_RENEWAL = "competitor_contract_renewal"
    GLASSDOOR_TREND = "glassdoor_trend"


SIGNAL_TYPE_TO_CATEGORY: dict[SignalType, SignalCategory] = {
    SignalType.FUNDING_ROUND: SignalCategory.FUNDING,
    SignalType.NEW_EXECUTIVE_FINANCE: SignalCategory.LEADERSHIP,
    SignalType.NEW_EXECUTIVE_OTHER: SignalCategory.LEADERSHIP,
    SignalType.CHAMPION_DEPARTED: SignalCategory.LEADERSHIP,
    SignalType.JOB_POSTING_FINANCE: SignalCategory.HIRING,
    SignalType.JOB_POSTING_TECHNICAL: SignalCategory.HIRING,
    SignalType.JOB_POSTING_URGENT: SignalCategory.HIRING,
    SignalType.TECH_STACK_CHANGE: SignalCategory.TECHNOLOGY,
    SignalType.MIGRATION_SIGNAL: SignalCategory.TECHNOLOGY,
    SignalType.BLOG_POST_PAIN: SignalCategory.PAIN,
    SignalType.LINKEDIN_POST_PAIN: SignalCategory.PAIN,
    SignalType.EARNINGS_MENTION: SignalCategory.OPERATIONAL,
    SignalType.PRESS_RELEASE_RELEVANT: SignalCategory.PRODUCT,
    SignalType.PRICING_PAGE_VISIT: SignalCategory.TIMING,
    SignalType.CONTENT_ENGAGEMENT: SignalCategory.TIMING,
    SignalType.G2_RESEARCH_ACTIVITY: SignalCategory.COMPETITIVE,
    SignalType.COMPETITOR_EVALUATION: SignalCategory.COMPETITIVE,
    SignalType.COMPETITOR_CONTRACT_RENEWAL: SignalCategory.COMPETITIVE,
    SignalType.GLASSDOOR_TREND: SignalCategory.OPERATIONAL,
}


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
    # Optional firmographics that feed deterministic ICP subcomponent scoring.
    funding_stage: str | None = None
    growth_rate: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
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
    """A single piece of evidence-bound signal.

    Field shape matches PRISM-v2's signal model:
      - signal_type: one of 19 specific types
      - category:    coarse AE bucket (derived from signal_type)
      - description: human-readable text snippet
      - source:      origin label (URL or source title)
      - detected_date: when the underlying event happened (date, not datetime)
      - decay_weight: 0..1 temporal weight after decay function applied
      - confidence:  extracted | interpolated | generated
      - contact_name: associated person, if signal is person-level
      - strength:    base relevance before decay (PRISM Analyst extension)
    """

    id: str = ""
    signal_type: SignalType
    category: SignalCategory | None = None
    text: str = ""
    description: str = ""
    source_id: str = ""
    source: str = ""
    strength: float = Field(ge=0.0, le=1.0, default=0.5)
    decay_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    confidence: SignalConfidence = SignalConfidence.INTERPOLATED
    contact_name: str | None = None
    detected_date: date | None = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    recency_days: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.category is None:
            self.category = SIGNAL_TYPE_TO_CATEGORY.get(
                self.signal_type, SignalCategory.OPERATIONAL
            )
        # Keep description and text in sync (description is the v2 field name).
        if self.description and not self.text:
            self.text = self.description
        if self.text and not self.description:
            self.description = self.text
        if not self.id:
            raw = f"{self.signal_type}:{self.text[:80]}:{self.source_id}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def effective_weight(self) -> float:
        """Combined relevance after temporal decay."""
        return round(self.strength * self.decay_weight, 4)


class ICPBreakdown(BaseModel):
    """Per-subcomponent ICP fit scores, mirrors PRISM-v2 weights."""

    funding_stage: float = 0.0
    growth_rate: float = 0.0
    tech_stack: float = 0.0
    headcount: float = 0.0
    industry: float = 0.0
    geo: float = 0.0


class ReadinessBreakdown(BaseModel):
    """Per-subcomponent buying readiness, mirrors PRISM-v2 weights."""

    journey_position: float = 0.0
    pain_coherence: float = 0.0
    new_leader_signal: float = 0.0
    org_stress: float = 0.0
    solution_sophistication: float = 0.0
    active_evaluation: float = 0.0


class TimingBreakdown(BaseModel):
    trigger_event_recency: float = 0.0
    signal_freshness_avg: float = 0.0
    urgency_indicators: float = 0.0
    window_closing: float = 0.0


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
    icp_breakdown: ICPBreakdown = Field(default_factory=ICPBreakdown)
    readiness_breakdown: ReadinessBreakdown = Field(default_factory=ReadinessBreakdown)
    timing_breakdown: TimingBreakdown = Field(default_factory=TimingBreakdown)
    weights: dict[str, float] = Field(default_factory=dict)
    scored_at: datetime = Field(default_factory=datetime.utcnow)

    def compute_composite(self) -> None:
        # Imported lazily so models.py stays import-safe.
        from .config import settings

        self.weights = {
            "icp_fit": settings.icp_weight,
            "buying_readiness": settings.buying_readiness_weight,
            "timing": settings.timing_weight,
        }
        self.composite = round(
            self.icp_fit * settings.icp_weight
            + self.buying_readiness * settings.buying_readiness_weight
            + self.timing * settings.timing_weight,
            1,
        )
        if self.composite >= settings.tier1_threshold:
            self.tier = Tier.TIER_1
        elif self.composite >= settings.tier2_threshold:
            self.tier = Tier.TIER_2
        elif self.composite >= settings.tier3_threshold:
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
    signal_types: list[SignalType] = Field(default_factory=list)
    categories: list[SignalCategory] = Field(default_factory=list)
    relevance_reason: str = ""
    strength: float = 0.5
    confidence: SignalConfidence = SignalConfidence.INTERPOLATED


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
    # Optional pre-computed views attached for the renderer.
    scorecard: Scorecard | None = None
    signals: list[Signal] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)
    profile: AccountProfile | None = None


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


class DeltaType(str, Enum):
    NEW = "new"
    DECAYED = "decayed"
    REMOVED = "removed"
    CHANGED = "changed"


class DigestSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    UPDATE = "update"


class SignalDelta(BaseModel):
    """Single signal change between two runs.

    `delta_type` matches PRISM-v2's vocabulary: new | decayed | removed.
    `change_type` is kept as an alias for backward compatibility.
    """

    signal_type: SignalType | None = None
    category: str
    description: str
    delta_type: DeltaType = DeltaType.NEW
    change_type: str | None = None
    weight_change: float | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.change_type is None:
            self.change_type = self.delta_type.value


class DigestEntry(BaseModel):
    """An entry in the digest's severity-sorted change log."""

    severity: DigestSeverity
    headline: str
    detail: str = ""


class ScoreSnapshot(BaseModel):
    composite: float = 0.0
    previous_composite: float | None = None
    delta: float = 0.0
    tier: Tier = Tier.NOT_QUALIFIED
    icp_fit: float = 0.0
    buying_readiness: float = 0.0
    timing: float = 0.0


class Digest(BaseModel):
    account_slug: str
    previous_run_id: str
    current_run_id: str
    score_snapshot: ScoreSnapshot = Field(default_factory=ScoreSnapshot)
    entries: list[DigestEntry] = Field(default_factory=list)
    new_signals: list[SignalDelta] = Field(default_factory=list)
    changed_signals: list[SignalDelta] = Field(default_factory=list)
    decayed_signals: list[SignalDelta] = Field(default_factory=list)
    removed_signals: list[SignalDelta] = Field(default_factory=list)
    score_change: float = 0.0
    is_material: bool = False
    summary: str = ""
    action_update: str = ""
    llm_narrative: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
