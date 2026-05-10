"""Batch account analysis workflow."""

from __future__ import annotations

import csv
from pathlib import Path

from ..config import settings
from ..models import Scorecard
from ..render.csv import render_scorecard_csv
from ..workspace import workspace
from .analyze import analyze_account, resolve_company, collect_sources

from ..signals.extract import extract_signals
from ..signals.decay import apply_decay
from ..signals.score import score_account
from ..render.snapshot import render_snapshot


def _get_echo():
    try:
        import click
        return click.echo
    except ImportError:
        return print


def load_accounts_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def batch_analyze(
    csv_path: Path,
    mode: str = "no-llm",
) -> str:
    echo = _get_echo()
    rows = load_accounts_csv(csv_path)
    echo(f"Loaded {len(rows)} accounts from {csv_path}")

    scorecards: list[Scorecard] = []

    for i, row in enumerate(rows, 1):
        account_input = row.get("company") or row.get("domain") or row.get("name", "")
        if not account_input:
            continue

        echo(f"\n[{i}/{len(rows)}] {account_input}")

        if mode == "no-llm":
            profile = resolve_company(account_input)
            if "domain" in row and row["domain"]:
                profile.domain = row["domain"]
            if "industry" in row:
                profile.industry = row["industry"]

            sources = collect_sources(profile)
            signals = extract_signals(sources)
            signals = apply_decay(signals)
            card = score_account(profile.slug, profile.name, sources, signals)
            scorecards.append(card)

            snapshot_md = render_snapshot(profile, card, signals, sources)
            out_dir = workspace.output_account_dir(profile.slug)
            workspace.write_text(out_dir / "account_snapshot.md", snapshot_md)

            echo(f"  Score: {card.composite} ({card.tier.value})")
        else:
            analyze_account(account_input, mode=mode)

            scorecard_path = workspace.output_account_dir(
                resolve_company(account_input).slug
            )
            card_data = workspace.read_json(
                workspace.account_dir(resolve_company(account_input).slug) / "runs"
            )
            profile = resolve_company(account_input)
            sources = collect_sources(profile)
            signals = extract_signals(sources)
            signals = apply_decay(signals)
            card = score_account(profile.slug, profile.name, sources, signals)
            scorecards.append(card)

    scorecard_csv = render_scorecard_csv(scorecards)
    out_path = settings.output_dir / "batch_scorecard.csv"
    workspace.write_text(out_path, scorecard_csv)

    echo(f"\nBatch complete. Scorecard: {out_path}")
    echo(f"Accounts analyzed: {len(scorecards)}")

    if scorecards:
        top = max(scorecards, key=lambda c: c.composite)
        echo(f"Top account: {top.account_name} ({top.composite}, {top.tier.value})")

    return str(out_path)
