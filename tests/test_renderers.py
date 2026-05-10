"""Tests for renderers."""

from prism_analyst.models import (
    AccountProfile,
    DeltaType,
    Digest,
    DigestEntry,
    DigestSeverity,
    Dossier,
    DossierSection,
    GiftDocument,
    ScoreSnapshot,
    Scorecard,
    Signal,
    SignalDelta,
    SignalType,
    SourceItem,
    SourceType,
    Tier,
)
from prism_analyst.render.csv import render_scorecard_csv
from prism_analyst.render.digest import render_digest
from prism_analyst.render.dossier import render_dossier
from prism_analyst.render.gift import render_gift, render_redaction_report
from prism_analyst.render.snapshot import render_snapshot


def test_render_snapshot_includes_score_tree_and_signal_type():
    profile = AccountProfile(name="Test Co", slug="test-co", domain="test.com")
    card = Scorecard(
        account_slug="test-co", account_name="Test Co",
        icp_fit=60, buying_readiness=70, timing=50,
    )
    card.compute_composite()
    signals = [
        Signal(signal_type=SignalType.JOB_POSTING_TECHNICAL,
               text="Hiring senior engineers", source_id="s1"),
    ]
    sources = [
        SourceItem(source_type=SourceType.WEBSITE, title="Test.com", url="https://test.com"),
    ]
    md = render_snapshot(profile, card, signals, sources)
    assert "# Account Snapshot: Test Co" in md
    assert "Composite" in md
    assert "ICP Fit" in md
    assert "job_posting_technical" in md


def test_render_dossier_emits_v2_section_titles_and_score_tree():
    card = Scorecard(
        account_slug="test-co", account_name="Test Co",
        icp_fit=80, buying_readiness=70, timing=60,
    )
    card.compute_composite()
    dossier = Dossier(
        account_slug="test-co",
        scorecard=card,
        sections=[
            DossierSection(title="Executive Summary", content="Headline summary."),
            DossierSection(title="Subject Profile", content="Profile body."),
        ],
    )
    md = render_dossier(dossier)
    assert "PRISM INTELLIGENCE DOSSIER" in md
    assert "1. Executive Summary" in md
    assert "4. Key Personnel — Buying Committee Map" in md
    assert "6. Why Now — Hypothesis" in md
    assert "9. Appendix — Raw Signals & Sources" in md
    assert "Composite Score" in md


def test_render_dossier_signal_timeline_uses_decay_bars():
    card = Scorecard(account_slug="t", account_name="T")
    card.compute_composite()
    sig = Signal(
        signal_type=SignalType.FUNDING_ROUND,
        text="raised series b",
        source_id="s1",
        decay_weight=0.8,
    )
    dossier = Dossier(
        account_slug="t",
        scorecard=card,
        signals=[sig],
        sections=[],
    )
    md = render_dossier(dossier)
    assert "funding_round" in md
    # decay bar uses block characters
    assert "█" in md or "▓" in md


def test_render_digest_severity_groups_and_typed_deltas():
    digest = Digest(
        account_slug="test-co",
        previous_run_id="2026-01-01",
        current_run_id="2026-01-08",
        score_snapshot=ScoreSnapshot(
            composite=72.0, previous_composite=58.0, delta=14.0,
            tier=Tier.TIER_1, icp_fit=70, buying_readiness=75, timing=70,
        ),
        entries=[
            DigestEntry(severity=DigestSeverity.CRITICAL, headline="New funding round"),
            DigestEntry(severity=DigestSeverity.UPDATE, headline="Minor update"),
        ],
        new_signals=[
            SignalDelta(
                signal_type=SignalType.FUNDING_ROUND,
                category="funding",
                description="raised $20M Series B",
                delta_type=DeltaType.NEW,
            ),
        ],
        score_change=14.0,
        is_material=True,
        action_update="Promote to active outreach.",
    )
    md = render_digest(digest)
    assert "PRISM SIGNAL DIGEST" in md
    assert "Material: yes" in md
    assert "Score Snapshot" in md
    assert "Critical" in md
    assert "+ [funding_round]" in md
    assert "►" in md  # action update bullet


def test_render_gift():
    gift = GiftDocument(
        account_slug="test-co",
        content="Market insight content here.",
        redacted_items=["Internal score removed", "Sales tactic removed"],
    )
    md = render_gift(gift)
    assert "Market Insight Brief" in md
    assert "Market insight content here." in md


def test_render_redaction_report():
    gift = GiftDocument(
        account_slug="test-co",
        content="Content",
        redacted_items=["Score removed", "Tactic removed"],
    )
    md = render_redaction_report(gift)
    assert "Redaction Report" in md
    assert "Score removed" in md
    assert "Items redacted or reframed: 2" in md


def test_render_scorecard_csv():
    cards = [
        Scorecard(account_slug="alpha", account_name="Alpha", composite=80),
        Scorecard(account_slug="beta", account_name="Beta", composite=45),
    ]
    csv_text = render_scorecard_csv(cards)
    assert "alpha" in csv_text
    assert "beta" in csv_text
    lines = csv_text.strip().split("\n")
    assert len(lines) == 3
    assert lines[1].startswith("alpha")
