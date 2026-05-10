"""Tests for core data models."""

from prism_analyst.models import (
    AccountProfile,
    DeltaType,
    DigestEntry,
    DigestSeverity,
    EvidencePack,
    SIGNAL_TYPE_TO_CATEGORY,
    Scorecard,
    Signal,
    SignalCategory,
    SignalConfidence,
    SignalDelta,
    SignalType,
    SourceItem,
    SourceType,
    Tier,
)


def test_scorecard_compute_composite_tier1():
    card = Scorecard(
        account_slug="test",
        account_name="Test",
        icp_fit=80,
        buying_readiness=85,
        timing=70,
    )
    card.compute_composite()
    # weights: 0.25 / 0.50 / 0.25 → 80*.25 + 85*.5 + 70*.25 = 80
    assert card.composite >= 70
    assert card.tier == Tier.TIER_1
    assert card.weights["buying_readiness"] == 0.50


def test_scorecard_compute_composite_tier2():
    card = Scorecard(
        account_slug="test",
        account_name="Test",
        icp_fit=50,
        buying_readiness=50,
        timing=40,
    )
    card.compute_composite()
    assert 45 <= card.composite < 70
    assert card.tier == Tier.TIER_2


def test_scorecard_compute_composite_tier3():
    card = Scorecard(
        account_slug="test",
        account_name="Test",
        icp_fit=30,
        buying_readiness=25,
        timing=30,
    )
    card.compute_composite()
    assert 25 <= card.composite < 45
    assert card.tier == Tier.TIER_3


def test_scorecard_compute_composite_not_qualified():
    card = Scorecard(
        account_slug="test",
        account_name="Test",
        icp_fit=10,
        buying_readiness=10,
        timing=10,
    )
    card.compute_composite()
    assert card.composite < 25
    assert card.tier == Tier.NOT_QUALIFIED


def test_source_item_auto_id():
    item = SourceItem(source_type=SourceType.WEBSITE, url="https://example.com")
    assert len(item.id) == 12


def test_signal_auto_id_and_category_derived():
    sig = Signal(
        signal_type=SignalType.JOB_POSTING_TECHNICAL,
        text="Hiring senior engineers",
        source_id="abc123",
    )
    assert len(sig.id) == 12
    assert sig.category == SignalCategory.HIRING
    assert sig.confidence == SignalConfidence.INTERPOLATED


def test_signal_text_description_sync():
    sig = Signal(signal_type=SignalType.FUNDING_ROUND, description="Raised $20M", source_id="x")
    assert sig.text == "Raised $20M"
    assert sig.description == "Raised $20M"


def test_signal_effective_weight_combines_strength_and_decay():
    sig = Signal(
        signal_type=SignalType.FUNDING_ROUND,
        text="t",
        source_id="x",
        strength=0.8,
        decay_weight=0.5,
    )
    assert sig.effective_weight == 0.4


def test_signal_type_to_category_map_is_complete():
    for st in SignalType:
        assert st in SIGNAL_TYPE_TO_CATEGORY


def test_signal_delta_back_compat_change_type():
    d = SignalDelta(category="funding", description="raised", delta_type=DeltaType.NEW)
    assert d.change_type == "new"


def test_digest_entry_severity():
    e = DigestEntry(severity=DigestSeverity.CRITICAL, headline="hi")
    assert e.severity == DigestSeverity.CRITICAL


def test_evidence_pack_content_hash():
    pack = EvidencePack(account_slug="test")
    h1 = pack.content_hash()
    assert len(h1) == 16

    pack2 = EvidencePack(account_slug="test")
    assert pack2.content_hash() == h1


def test_account_profile_optional_firmographics():
    p = AccountProfile(name="Acme", slug="acme", industry="SaaS", funding_stage="Series B")
    assert p.industry == "SaaS"
    assert p.funding_stage == "Series B"
    assert p.tech_stack == []
