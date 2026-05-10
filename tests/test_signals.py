"""Tests for signal extraction, scoring, decay, and confidence."""

from prism_analyst.config import SIGNAL_DECAY
from prism_analyst.models import (
    AccountProfile,
    ConfidenceLevel,
    Signal,
    SignalCategory,
    SignalConfidence,
    SignalType,
    SourceItem,
    SourceType,
)
from prism_analyst.signals.confidence import assess_confidence
from prism_analyst.signals.decay import (
    _decay_factor,
    apply_decay,
    decay_bar,
    decay_weight_for,
)
from prism_analyst.signals.extract import extract_signals
from prism_analyst.signals.score import score_account


def _make_source(content: str, source_type: SourceType = SourceType.WEBSITE) -> SourceItem:
    return SourceItem(
        source_type=source_type,
        title="Test Source",
        content=content,
        excerpt=content[:200],
    )


def test_extract_funding_signal():
    source = _make_source("Company raised $50 million in Series B funding")
    signals = extract_signals([source])
    types = {s.signal_type for s in signals}
    assert SignalType.FUNDING_ROUND in types
    # Each emitted signal should auto-derive its category bucket.
    funding = next(s for s in signals if s.signal_type == SignalType.FUNDING_ROUND)
    assert funding.category == SignalCategory.FUNDING
    assert funding.confidence == SignalConfidence.EXTRACTED


def test_extract_migration_signal():
    source = _make_source("We are migrating our infrastructure off the legacy monolith")
    signals = extract_signals([source])
    types = {s.signal_type for s in signals}
    assert SignalType.MIGRATION_SIGNAL in types


def test_extract_pain_signal():
    source = _make_source("Struggling with manual processes and compliance audits")
    signals = extract_signals([source])
    types = {s.signal_type for s in signals}
    assert SignalType.BLOG_POST_PAIN in types


def test_extract_no_signals_from_empty():
    source = _make_source("Hello world")
    signals = extract_signals([source])
    assert len(signals) == 0


def test_decay_table_covers_all_signal_types():
    for st in SignalType:
        assert st in SIGNAL_DECAY, f"Missing decay params for {st}"


def test_decay_weight_within_peak_is_one():
    assert decay_weight_for(SignalType.FUNDING_ROUND, 10) == 1.0
    assert decay_weight_for(SignalType.LINKEDIN_POST_PAIN, 1) == 1.0


def test_decay_weight_after_max_relevance_clamps_to_floor():
    # max_relevance for LINKEDIN_POST_PAIN is 30 days.
    assert decay_weight_for(SignalType.LINKEDIN_POST_PAIN, 365) <= 0.10


def test_decay_weight_decreases_after_peak():
    fresh = decay_weight_for(SignalType.FUNDING_ROUND, 30)  # at peak
    older = decay_weight_for(SignalType.FUNDING_ROUND, 120)
    assert fresh > older


def test_apply_decay_sets_decay_weight():
    sig = Signal(
        signal_type=SignalType.FUNDING_ROUND,
        text="raised series b",
        source_id="x",
        strength=0.8,
        recency_days=120,
    )
    apply_decay([sig])
    assert sig.decay_weight < 1.0
    assert sig.decay_weight > 0.0


def test_decay_bar_renders_full_and_empty():
    assert decay_bar(1.0) == "█" * 10
    assert decay_bar(0.0) == "░" * 10
    assert len(decay_bar(0.5)) == 10


def test_legacy_decay_factor_kept_for_compat():
    assert _decay_factor(3) == 1.0
    assert _decay_factor(200) == 0.2


def test_score_account_with_signals():
    sources = [
        _make_source("Hiring senior engineers, migrating to kubernetes", SourceType.WEBSITE),
        _make_source("Raised $20M Series A funding", SourceType.NEWS),
    ]
    signals = extract_signals(sources)
    apply_decay(signals)
    card = score_account("test", "Test Co", sources, signals)
    assert card.composite > 0
    assert card.signal_count > 0
    # Subcomponent breakdowns must be populated.
    assert card.icp_breakdown.tech_stack >= 0
    assert card.readiness_breakdown.pain_coherence >= 0


def test_score_account_uses_profile_firmographics():
    profile = AccountProfile(
        name="Test", slug="test",
        industry="SaaS", funding_stage="Series B",
        location="San Francisco", headcount="250",
    )
    card = score_account("test", "Test", [], [], profile=profile)
    assert card.icp_breakdown.funding_stage == 1.0
    assert card.icp_breakdown.industry == 1.0
    assert card.icp_breakdown.geo == 1.0
    assert card.icp_fit > 0


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
        Signal(signal_type=SignalType.JOB_POSTING_TECHNICAL, text="t", source_id="x", strength=0.8),
        Signal(signal_type=SignalType.FUNDING_ROUND, text="t", source_id="x", strength=0.9),
        Signal(signal_type=SignalType.MIGRATION_SIGNAL, text="t", source_id="x", strength=0.7),
        Signal(signal_type=SignalType.BLOG_POST_PAIN, text="t", source_id="x", strength=0.6),
    ]
    level, _ = assess_confidence(sources, signals)
    assert level == ConfidenceLevel.HIGH


def test_confidence_low():
    sources = [_make_source("sparse")]
    signals = [Signal(signal_type=SignalType.JOB_POSTING_TECHNICAL, text="t", source_id="x", strength=0.3)]
    level, _ = assess_confidence(sources, signals)
    assert level == ConfidenceLevel.LOW
