"""Single-account analysis workflow."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..collect.github import collect_github
from ..collect.jobs import collect_jobs
from ..collect.manual import collect_manual
from ..collect.news import collect_news
from ..collect.website import collect_website, normalize_domain
from ..config import settings
from ..llm.backend import run_full_dossier, run_quick_brief
from ..llm.evidence_pack import build_evidence_pack
from ..models import AccountProfile, Brief, Dossier, EvidencePack, Scorecard, SourceItem, Signal
from ..render.dossier import render_dossier
from ..render.snapshot import render_snapshot
from ..signals.decay import apply_decay
from ..signals.extract import extract_signals
from ..signals.score import score_account
from ..workspace import workspace


def _make_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def resolve_company(input_str: str) -> AccountProfile:
    input_str = input_str.strip()
    if "." in input_str and " " not in input_str:
        domain = normalize_domain(input_str)
        name = domain.split(".")[0].title()
        slug = _make_slug(name)
    else:
        name = input_str
        slug = _make_slug(name)
        domain = None

    return AccountProfile(name=name, slug=slug, domain=domain)


def collect_sources(profile: AccountProfile) -> list[SourceItem]:
    sources: list[SourceItem] = []

    if profile.domain:
        sources.extend(collect_website(profile.domain))
        sources.extend(collect_jobs(profile.domain))
        sources.extend(collect_github(profile.domain))

    sources.extend(collect_news(profile.name, profile.domain))

    notes_dir = workspace.account_dir(profile.slug) / "notes"
    sources.extend(collect_manual(notes_dir))

    return sources


def analyze_account(
    input_str: str,
    mode: str = "quick",
) -> dict[str, str]:
    profile = resolve_company(input_str)
    click_echo = _get_echo()

    click_echo(f"Resolving: {profile.name} ({profile.domain or 'no domain'})")

    # Collect sources
    click_echo("Collecting sources...")
    sources = collect_sources(profile)
    click_echo(f"  Found {len(sources)} sources")

    # Extract and score
    click_echo("Extracting signals...")
    signals = extract_signals(sources)
    signals = apply_decay(signals)
    click_echo(f"  Found {len(signals)} signals")

    scorecard = score_account(profile.slug, profile.name, sources, signals)
    click_echo(f"  Score: {scorecard.composite} ({scorecard.tier.value}, {scorecard.confidence.value} confidence)")

    # Save workspace state
    run_dir = workspace.run_dir(profile.slug)
    _save_state(run_dir, profile, sources, signals, scorecard)

    # Render snapshot
    snapshot_md = render_snapshot(profile, scorecard, signals, sources)
    out_dir = workspace.output_account_dir(profile.slug)
    workspace.write_text(out_dir / "account_snapshot.md", snapshot_md)

    outputs = {"snapshot": str(out_dir / "account_snapshot.md")}

    if mode in ("quick", "full", "gated"):
        if mode == "gated" and scorecard.composite < settings.quick_threshold:
            click_echo(f"  Score below quick threshold ({settings.quick_threshold}), skipping LLM analysis")
            return outputs

        click_echo("Building evidence pack...")
        pack = build_evidence_pack(profile.slug, sources, signals)
        workspace.write_json(run_dir / "evidence_pack.json", pack.model_dump(mode="json"))

        click_echo("Generating quick brief...")
        brief = run_quick_brief(pack, profile.name)
        brief_md = _render_brief(brief)
        workspace.write_text(out_dir / "quick_brief.md", brief_md)
        workspace.write_text(run_dir / "quick_brief.md", brief_md)
        outputs["brief"] = str(out_dir / "quick_brief.md")

        if mode == "full" or (
            mode == "gated" and scorecard.composite >= settings.full_threshold
        ):
            click_echo("Generating full dossier...")
            dossier = run_full_dossier(pack, profile.name)
            dossier_md = render_dossier(dossier)
            workspace.write_text(out_dir / "dossier.md", dossier_md)
            workspace.write_text(run_dir / "dossier.md", dossier_md)
            outputs["dossier"] = str(out_dir / "dossier.md")

    click_echo(f"Done. Outputs in {out_dir}")
    return outputs


def _save_state(
    run_dir: Path,
    profile: AccountProfile,
    sources: list[SourceItem],
    signals: list[Signal],
    scorecard: Scorecard,
) -> None:
    acct_dir = run_dir.parent.parent
    workspace.write_json(acct_dir / "profile.json", profile.model_dump(mode="json"))
    workspace.write_json(acct_dir / "sources.json", [s.model_dump(mode="json") for s in sources])
    workspace.write_json(acct_dir / "signals.json", [s.model_dump(mode="json") for s in signals])
    workspace.write_json(run_dir / "scorecard.json", scorecard.model_dump(mode="json"))


def _render_brief(brief: Brief) -> str:
    lines = [
        f"# Quick Brief: {brief.account_slug}",
        "",
        f"*Generated: {brief.generated_at.strftime('%Y-%m-%d %H:%M')} UTC*",
        f"*Model: {brief.model} | Confidence: {brief.confidence.value}*",
        "",
        "---",
        "",
    ]
    if brief.raw_llm_output:
        lines.append(brief.raw_llm_output)
    else:
        lines.append("*No LLM output available.*")
    lines.append("")
    return "\n".join(lines)


def _get_echo():
    try:
        import click
        return click.echo
    except ImportError:
        return print
