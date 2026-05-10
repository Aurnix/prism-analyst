"""Account scoring from extracted signals."""

from __future__ import annotations

from ..config import settings
from ..models import (
    ConfidenceLevel,
    Scorecard,
    Signal,
    SignalCategory,
    SourceItem,
)
from .confidence import assess_confidence


_ICP_CATEGORIES = {
    SignalCategory.TECHNOLOGY,
    SignalCategory.OPERATIONAL,
    SignalCategory.PRODUCT,
}

_BUYING_CATEGORIES = {
    SignalCategory.HIRING,
    SignalCategory.FUNDING,
    SignalCategory.PAIN,
    SignalCategory.COMPETITIVE,
    SignalCategory.EXPANSION,
    SignalCategory.LEADERSHIP,
}

_TIMING_CATEGORIES = {
    SignalCategory.TIMING,
    SignalCategory.FUNDING,
    SignalCategory.EXPANSION,
}


def score_account(
    account_slug: str,
    account_name: str,
    sources: list[SourceItem],
    signals: list[Signal],
) -> Scorecard:
    icp_fit = _dimension_score(signals, _ICP_CATEGORIES)
    buying_readiness = _dimension_score(signals, _BUYING_CATEGORIES)
    timing = _dimension_score(signals, _TIMING_CATEGORIES)

    confidence, confidence_reason = assess_confidence(sources, signals)

    card = Scorecard(
        account_slug=account_slug,
        account_name=account_name,
        icp_fit=icp_fit,
        buying_readiness=buying_readiness,
        timing=timing,
        signal_count=len(signals),
        source_count=len(sources),
        confidence=confidence,
        confidence_reason=confidence_reason,
    )
    card.compute_composite()
    return card


def _dimension_score(signals: list[Signal], categories: set[SignalCategory]) -> float:
    relevant = [s for s in signals if s.category in categories]
    if not relevant:
        return 0.0

    total_strength = sum(s.strength for s in relevant)
    category_count = len({s.category for s in relevant})

    breadth_bonus = min(category_count * 10, 30)
    depth_score = min(total_strength * 20, 70)

    return round(min(depth_score + breadth_bonus, 100), 1)
