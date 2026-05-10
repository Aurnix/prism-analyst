"""Confidence assessment for account analysis."""

from __future__ import annotations

from ..models import ConfidenceLevel, Signal, SourceItem, SourceType


def assess_confidence(
    sources: list[SourceItem],
    signals: list[Signal],
) -> tuple[ConfidenceLevel, str]:
    source_types = {s.source_type for s in sources}
    source_count = len(sources)
    signal_count = len(signals)
    strong_signals = [s for s in signals if s.strength >= 0.6]

    reasons: list[str] = []

    if source_count >= 5 and len(source_types) >= 3 and len(strong_signals) >= 4:
        level = ConfidenceLevel.HIGH
        reasons.append(f"{source_count} sources across {len(source_types)} types")
        reasons.append(f"{len(strong_signals)} strong signals")
    elif source_count >= 2 and signal_count >= 2:
        level = ConfidenceLevel.MEDIUM
        if len(source_types) < 3:
            reasons.append("limited source diversity")
        if len(strong_signals) < 3:
            reasons.append("few strong signals")
        if source_count < 5:
            reasons.append(f"only {source_count} sources")
    else:
        level = ConfidenceLevel.LOW
        if source_count < 2:
            reasons.append("sparse source corpus")
        if signal_count < 2:
            reasons.append("weak signal coverage")

    gaps: list[str] = []
    if SourceType.WEBSITE not in source_types:
        gaps.append("no website content")
    if SourceType.NEWS not in source_types:
        gaps.append("no news coverage")
    if SourceType.JOBS not in source_types:
        gaps.append("no job postings found")

    if gaps:
        reasons.append("gaps: " + ", ".join(gaps))

    return level, "; ".join(reasons) if reasons else "insufficient data"
