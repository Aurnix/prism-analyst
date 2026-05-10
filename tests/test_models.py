"""Tests for core data models."""

from prism_analyst.models import (
    AccountProfile,
    ConfidenceLevel,
    EvidencePack,
    Scorecard,
    Signal,
    SignalCategory,
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
    assert card.composite >= 75
    assert card.tier == Tier.TIER_1


def test_scorecard_compute_composite_tier2():
    card = Scorecard(
        account_slug="test",
        account_name="Test",
        icp_fit=60,
        buying_readiness=55,
        timing=50,
    )
    card.compute_composite()
    assert 55 <= card.composite < 75
    assert card.tier == Tier.TIER_2


def test_scorecard_compute_composite_tier3():
    card = Scorecard(
        account_slug="test",
        account_name="Test",
        icp_fit=40,
        buying_readiness=35,
        timing=30,
    )
    card.compute_composite()
    assert 35 <= card.composite < 55
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
    assert card.composite < 35
    assert card.tier == Tier.NOT_QUALIFIED


def test_source_item_auto_id():
    item = SourceItem(source_type=SourceType.WEBSITE, url="https://example.com")
    assert len(item.id) == 12


def test_signal_auto_id():
    sig = Signal(
        category=SignalCategory.HIRING,
        text="We are hiring engineers",
        source_id="abc123",
    )
    assert len(sig.id) == 12


def test_evidence_pack_content_hash():
    pack = EvidencePack(account_slug="test")
    h1 = pack.content_hash()
    assert len(h1) == 16

    pack2 = EvidencePack(account_slug="test")
    assert pack2.content_hash() == h1
