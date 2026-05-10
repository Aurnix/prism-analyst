"""Tests for signal extraction, scoring, decay, and confidence."""

from prism_analyst.models import (
    ConfidenceLevel,
    Signal,
    SignalCategory,
    SourceItem,
    SourceType,
)
from prism_analyst.signals.confidence import assess_confidence
from prism_analyst.signals.decay import apply_decay, _decay_factor
from prism_analyst.signals.extract import extract_signals
from prism_analyst.signals.score import score_account


def _make_source(content: str, source_type: SourceType = SourceType.WEBSITE) -> SourceItem:
    return SourceItem(
        source_type=source_type,
        title="Test Source",
        content=content,
        excerpt=content[:200],
    )


def test_extract_hiring_signal():
    source = _make_source("We're hiring senior engineers to join our team")
    signals = extract_signals([source])
    categories = {s.category for s in signals}
    assert SignalCategory.HIRING in categories


def test_extract_funding_signal():
    source = _make_source("Company raised $50 million in Series B funding")
    signals = extract_signals([source])
    categories = {s.category for s in signals}
    assert SignalCategory.FUNDING in categories


def test_extract_technology_signal():
    source = _make_source("Migrating our infrastructure to Kubernetes on AWS")
    signals = extract_signals([source])
    categories = {s.category for s in signals}
    assert SignalCategory.TECHNOLOGY in categories


def test_extract_pain_signal():
    source = _make_source("Struggling with manual processes and compliance requirements")
    signals = extract_signals([source])
    categories = {s.category for s in signals}
    assert SignalCategory.PAIN in categories


def test_extract_no_signals_from_empty():
    source = _make_source("Hello world")
    signals = extract_signals([source])
    assert len(signals) == 0


def test_decay_factor_recent():
    assert _decay_factor(3) == 1.0


def test_decay_factor_30d():
    assert _decay_factor(20) == 0.9


def test_decay_factor_90d():
    assert _decay_factor(60) == 0.7


def test_decay_factor_old():
    assert _decay_factor(200) == 0.2


def test_apply_decay_reduces_strength():
    sig = Signal(
        category=SignalCategory.HIRING,
        text="test",
        source_id="x",
        strength=0.8,
        recency_days=100,
    )
    result = apply_decay([sig])
    assert result[0].strength < 0.8


def test_score_account_with_signals():
    sources = [
        _make_source("Hiring engineers, migrating to kubernetes", SourceType.WEBSITE),
        _make_source("Raised $20M Series A funding", SourceType.NEWS),
    ]
    signals = extract_signals(sources)
    card = score_account("test", "Test Co", sources, signals)
    assert card.composite > 0
    assert card.signal_count > 0


def test_score_account_no_signals():
    sources = [_make_source("Hello world")]
    signals = extract_signals(sources)
    card = score_account("test", "Test Co", sources, signals)
    assert card.composite == 0.0


def test_confidence_high():
    sources = [
        _make_source("content", SourceType.WEBSITE),
        _make_source("content", SourceType.NEWS),
        _make_source("content", SourceType.JOBS),
        _make_source("content", SourceType.GITHUB),
        _make_source("content", SourceType.MANUAL),
    ]
    signals = [
        Signal(category=SignalCategory.HIRING, text="t", source_id="x", strength=0.8),
        Signal(category=SignalCategory.FUNDING, text="t", source_id="x", strength=0.9),
        Signal(category=SignalCategory.TECHNOLOGY, text="t", source_id="x", strength=0.7),
        Signal(category=SignalCategory.PAIN, text="t", source_id="x", strength=0.6),
    ]
    level, reason = assess_confidence(sources, signals)
    assert level == ConfidenceLevel.HIGH


def test_confidence_low():
    sources = [_make_source("sparse")]
    signals = [Signal(category=SignalCategory.HIRING, text="t", source_id="x", strength=0.3)]
    level, reason = assess_confidence(sources, signals)
    assert level == ConfidenceLevel.LOW
