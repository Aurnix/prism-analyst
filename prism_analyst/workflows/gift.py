"""Gift document generation workflow."""

from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..llm.backend import run_gift_doc
from ..llm.evidence_pack import build_evidence_pack
from ..models import AccountProfile, Signal, SourceItem
from ..render.gift import render_gift, render_redaction_report
from ..signals.extract import extract_signals
from ..signals.decay import apply_decay
from ..workspace import workspace
from .analyze import collect_sources, resolve_company


def _get_echo():
    try:
        import click
        return click.echo
    except ImportError:
        return print


def generate_gift(account_slug: str) -> dict[str, str]:
    echo = _get_echo()

    acct_dir = workspace.account_dir(account_slug)
    profile_data = workspace.read_json(acct_dir / "profile.json")
    if not profile_data:
        echo(f"No profile found for {account_slug}. Run analysis first.")
        return {}

    profile = AccountProfile(**profile_data)

    # Look for existing dossier
    out_dir = workspace.output_account_dir(account_slug)
    dossier_text = workspace.read_text(out_dir / "dossier.md")

    if not dossier_text:
        # Fall back to quick brief
        dossier_text = workspace.read_text(out_dir / "quick_brief.md")

    if not dossier_text:
        echo("No dossier or brief found. Generating from sources...")
        dossier_text = ""

    # Load sources and signals for evidence pack
    sources_data = workspace.read_json(acct_dir / "sources.json")
    signals_data = workspace.read_json(acct_dir / "signals.json")

    if sources_data:
        sources = [SourceItem(**s) for s in sources_data]
    else:
        sources = collect_sources(profile)

    if signals_data:
        signals = [Signal(**s) for s in signals_data]
    else:
        signals = extract_signals(sources)
        signals = apply_decay(signals)

    pack = build_evidence_pack(account_slug, sources, signals)

    echo("Generating prospect-safe gift document...")
    gift = run_gift_doc(pack, profile.name, dossier_text or "No prior dossier available.")

    gift_md = render_gift(gift)
    redaction_md = render_redaction_report(gift)

    workspace.write_text(out_dir / "gift.md", gift_md)
    workspace.write_text(out_dir / "redaction_report.md", redaction_md)
    workspace.write_json(
        out_dir / "redaction_report.json",
        {"redacted_items": gift.redacted_items},
    )

    echo(f"Gift document: {out_dir / 'gift.md'}")
    echo(f"Redaction report: {out_dir / 'redaction_report.md'}")
    echo(f"Items redacted: {len(gift.redacted_items)}")

    return {
        "gift": str(out_dir / "gift.md"),
        "redaction_report": str(out_dir / "redaction_report.md"),
    }
