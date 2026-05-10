"""Account scoring with PRISM-v2-aligned subcomponent breakdowns.

Composite weights, ICP weights, readiness weights and timing weights are read
from ``prism_analyst.config`` so renderers can show the breakdown verbatim.
"""

from __future__ import annotations

from ..config import (
    FUNDING_STAGE_SCORES,
    ICP_WEIGHTS,
    INDUSTRY_SCORES,
    READINESS_WEIGHTS,
    TECH_HUBS,
    TIMING_WEIGHTS,
    settings,
)
from ..models import (
    AccountProfile,
    ICPBreakdown,
    ReadinessBreakdown,
    Scorecard,
    Signal,
    SignalCategory,
    SignalType,
    SourceItem,
    TimingBreakdown,
)
from .confidence import assess_confidence


def score_account(
    account_slug: str,
    account_name: str,
    sources: list[SourceItem],
    signals: list[Signal],
    profile: AccountProfile | None = None,
) -> Scorecard:
    icp_breakdown = _icp_breakdown(profile, signals)
    readiness_breakdown = _readiness_breakdown(signals)
    timing_breakdown = _timing_breakdown(signals)

    icp_fit = _weighted(icp_breakdown.model_dump(), ICP_WEIGHTS) * 100
    buying_readiness = _weighted(readiness_breakdown.model_dump(), READINESS_WEIGHTS) * 100
    timing = _weighted(timing_breakdown.model_dump(), TIMING_WEIGHTS) * 100

    confidence, confidence_reason = assess_confidence(sources, signals)

    card = Scorecard(
        account_slug=account_slug,
        account_name=account_name,
        icp_fit=round(icp_fit, 1),
        buying_readiness=round(buying_readiness, 1),
        timing=round(timing, 1),
        signal_count=len(signals),
        source_count=len(sources),
        confidence=confidence,
        confidence_reason=confidence_reason,
        icp_breakdown=icp_breakdown,
        readiness_breakdown=readiness_breakdown,
        timing_breakdown=timing_breakdown,
    )
    card.compute_composite()
    return card


# --- Subcomponent scorers (each returns a 0..1 value per dimension) ---

def _icp_breakdown(
    profile: AccountProfile | None,
    signals: list[Signal],
) -> ICPBreakdown:
    funding = 0.0
    growth = 0.0
    tech = 0.0
    headcount = 0.0
    industry = 0.0
    geo = 0.0

    if profile:
        if profile.funding_stage:
            funding = FUNDING_STAGE_SCORES.get(profile.funding_stage.lower().strip(), 0.0)
        if profile.industry:
            industry = INDUSTRY_SCORES.get(profile.industry.lower().strip(), 0.4)
        if profile.location:
            loc = profile.location.lower()
            geo = 1.0 if any(hub in loc for hub in TECH_HUBS) else 0.4
        if profile.headcount:
            headcount = _bucket_headcount(profile.headcount)
        if profile.tech_stack:
            tech = min(0.4 + 0.15 * len(profile.tech_stack), 1.0)
        if profile.growth_rate:
            growth = _parse_growth_rate(profile.growth_rate)

    # Fall back to signal-derived hints when firmographics aren't supplied.
    if tech == 0.0:
        tech = min(_signal_density(signals, {SignalType.TECH_STACK_CHANGE,
                                              SignalType.MIGRATION_SIGNAL}) * 0.6, 1.0)
    if growth == 0.0:
        growth = min(_signal_density(signals, {SignalType.JOB_POSTING_TECHNICAL,
                                                SignalType.JOB_POSTING_FINANCE,
                                                SignalType.JOB_POSTING_URGENT}) * 0.5, 1.0)

    return ICPBreakdown(
        funding_stage=round(funding, 3),
        growth_rate=round(growth, 3),
        tech_stack=round(tech, 3),
        headcount=round(headcount, 3),
        industry=round(industry, 3),
        geo=round(geo, 3),
    )


def _readiness_breakdown(signals: list[Signal]) -> ReadinessBreakdown:
    pain = _category_score(signals, {SignalCategory.PAIN})
    leader = _signal_density(signals, {SignalType.NEW_EXECUTIVE_FINANCE,
                                        SignalType.NEW_EXECUTIVE_OTHER})
    stress = _signal_density(signals, {SignalType.GLASSDOOR_TREND,
                                        SignalType.CHAMPION_DEPARTED})
    sophistication = _category_score(signals, {SignalCategory.TECHNOLOGY,
                                                 SignalCategory.OPERATIONAL})
    evaluation = _signal_density(signals, {SignalType.COMPETITOR_EVALUATION,
                                            SignalType.G2_RESEARCH_ACTIVITY,
                                            SignalType.PRICING_PAGE_VISIT,
                                            SignalType.CONTENT_ENGAGEMENT})
    journey = min((pain + evaluation) / 2, 1.0)

    return ReadinessBreakdown(
        journey_position=round(journey, 3),
        pain_coherence=round(pain, 3),
        new_leader_signal=round(min(leader, 1.0), 3),
        org_stress=round(min(stress, 1.0), 3),
        solution_sophistication=round(sophistication, 3),
        active_evaluation=round(min(evaluation, 1.0), 3),
    )


def _timing_breakdown(signals: list[Signal]) -> TimingBreakdown:
    if not signals:
        return TimingBreakdown()

    weights = [s.decay_weight for s in signals]
    avg_freshness = sum(weights) / len(weights)

    trigger_types = {SignalType.FUNDING_ROUND, SignalType.NEW_EXECUTIVE_FINANCE,
                      SignalType.NEW_EXECUTIVE_OTHER, SignalType.MIGRATION_SIGNAL,
                      SignalType.JOB_POSTING_URGENT}
    trigger = max(
        (s.decay_weight for s in signals if s.signal_type in trigger_types),
        default=0.0,
    )

    urgency = _signal_density(signals, {SignalType.JOB_POSTING_URGENT,
                                         SignalType.PRICING_PAGE_VISIT,
                                         SignalType.COMPETITOR_EVALUATION})
    window_close = _signal_density(signals, {SignalType.COMPETITOR_CONTRACT_RENEWAL,
                                              SignalType.CHAMPION_DEPARTED})

    return TimingBreakdown(
        trigger_event_recency=round(trigger, 3),
        signal_freshness_avg=round(avg_freshness, 3),
        urgency_indicators=round(min(urgency, 1.0), 3),
        window_closing=round(min(window_close, 1.0), 3),
    )


# --- Helpers ---

def _weighted(values: dict[str, float], weights: dict[str, float]) -> float:
    total = 0.0
    for key, weight in weights.items():
        total += values.get(key, 0.0) * weight
    return total


def _signal_density(signals: list[Signal], types: set[SignalType]) -> float:
    matched = [s for s in signals if s.signal_type in types]
    if not matched:
        return 0.0
    # Sum effective weights, soft-capped via 1 - exp-like saturation.
    total = sum(s.strength for s in matched)
    return min(total / 2.0, 1.0)


def _category_score(signals: list[Signal], categories: set[SignalCategory]) -> float:
    matched = [s for s in signals if s.category in categories]
    if not matched:
        return 0.0
    total = sum(s.strength for s in matched)
    breadth = len({s.signal_type for s in matched}) / 5.0
    return min(total / 3.0 + breadth * 0.2, 1.0)


def _bucket_headcount(value: str) -> float:
    digits = "".join(c for c in value if c.isdigit())
    if not digits:
        return 0.5
    n = int(digits)
    if n < 25:
        return 0.2
    if n < 100:
        return 0.6
    if n < 500:
        return 1.0
    if n < 2000:
        return 0.85
    return 0.5


def _parse_growth_rate(value: str) -> float:
    digits = "".join(c for c in value if c.isdigit() or c == ".")
    if not digits:
        return 0.5
    pct = float(digits)
    if pct >= 100:
        return 1.0
    if pct >= 50:
        return 0.9
    if pct >= 25:
        return 0.7
    if pct >= 10:
        return 0.4
    return 0.2
