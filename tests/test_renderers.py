"""Tests for renderers."""

from prism_analyst.models import (
    AccountProfile,
    Digest,
    Dossier,
    DossierSection,
    GiftDocument,
    Scorecard,
    Signal,
    SignalCategory,
    SignalDelta,
    SourceItem,
    SourceType,
)
from prism_analyst.render.csv import render_scorecard_csv
from prism_analyst.render.digest import render_digest
from prism_analyst.render.dossier import render_dossier
from prism_analyst.render.gift import render_gift, render_redaction_report
from prism_analyst.render.snapshot import render_snapshot


def test_render_snapshot():
    profile = AccountProfile(name="Test Co", slug="test-co", domain="test.com")
    card = Scorecard(account_slug="test-co", account_name="Test Co", composite=65)
    card.compute_composite()
    signals = [
        Signal(category=SignalCategory.HIRING, text="Hiring engineers", source_id="s1")
    ]
    sources = [
        SourceItem(source_type=SourceType.WEBSITE, title="Test.com", url="https://test.com")
    ]
    md = render_snapshot(profile, card, signals, sources)
    assert "# Account Snapshot: Test Co" in md
    assert "test.com" in md
    assert "Hiring" in md


def test_render_dossier():
    dossier = Dossier(
        account_slug="test-co",
        sections=[
            DossierSection(title="Executive Summary", content="Summary text here."),
            DossierSection(title="Subject Profile", content="Profile text."),
        ],
    )
    md = render_dossier(dossier)
    assert "Intelligence Dossier" in md
    assert "Executive Summary" in md
    assert "Summary text here." in md


def test_render_digest():
    digest = Digest(
        account_slug="test-co",
        previous_run_id="2026-01-01",
        current_run_id="2026-01-08",
        new_signals=[
            SignalDelta(category="hiring", description="New engineering roles", change_type="new")
        ],
        score_change=12.5,
        is_material=True,
        summary="1 new signal; score up 12.5",
    )
    md = render_digest(digest)
    assert "Weekly Digest" in md
    assert "Material changes detected" in md
    assert "New Signals" in md


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
    assert len(lines) == 3  # header + 2 rows
    assert lines[1].startswith("alpha")  # sorted by composite desc
