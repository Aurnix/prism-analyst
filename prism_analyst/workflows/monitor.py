"""Monitoring and snapshot comparison workflow."""

from __future__ import annotations

from ..models import Digest, RunSnapshot, Scorecard, Signal, SignalDelta
from ..workspace import workspace
from .analyze import analyze_account, resolve_company, collect_sources
from ..signals.extract import extract_signals
from ..signals.decay import apply_decay
from ..signals.score import score_account
from ..render.digest import render_digest


_MATERIAL_SCORE_CHANGE = 10.0
_MATERIAL_NEW_SIGNALS = 3


def compare_runs(account_slug: str) -> Digest | None:
    prev_dir = workspace.previous_run_dir(account_slug)
    curr_dir = workspace.latest_run_dir(account_slug)

    if not prev_dir or not curr_dir or prev_dir == curr_dir:
        return None

    prev_signals = _load_signals(prev_dir.parent.parent / "signals.json")
    curr_signals = _load_signals(curr_dir.parent.parent / "signals.json")

    prev_card = _load_scorecard(prev_dir / "scorecard.json")
    curr_card = _load_scorecard(curr_dir / "scorecard.json")

    prev_ids = {s.id for s in prev_signals}
    curr_ids = {s.id for s in curr_signals}
    curr_map = {s.id: s for s in curr_signals}
    prev_map = {s.id: s for s in prev_signals}

    new_signals: list[SignalDelta] = []
    for sid in curr_ids - prev_ids:
        s = curr_map[sid]
        new_signals.append(SignalDelta(
            category=s.category.value,
            description=s.text[:150],
            change_type="new",
        ))

    decayed: list[SignalDelta] = []
    for sid in prev_ids - curr_ids:
        s = prev_map[sid]
        decayed.append(SignalDelta(
            category=s.category.value,
            description=s.text[:150],
            change_type="decayed",
        ))

    changed: list[SignalDelta] = []
    for sid in prev_ids & curr_ids:
        old_s = prev_map[sid]
        new_s = curr_map[sid]
        if abs(old_s.strength - new_s.strength) > 0.15:
            direction = "strengthened" if new_s.strength > old_s.strength else "weakened"
            changed.append(SignalDelta(
                category=new_s.category.value,
                description=f"{direction}: {new_s.text[:120]}",
                change_type="changed",
            ))

    score_change = 0.0
    if prev_card and curr_card:
        score_change = curr_card.composite - prev_card.composite

    is_material = (
        abs(score_change) >= _MATERIAL_SCORE_CHANGE
        or len(new_signals) >= _MATERIAL_NEW_SIGNALS
    )

    summary_parts: list[str] = []
    if new_signals:
        summary_parts.append(f"{len(new_signals)} new signals")
    if decayed:
        summary_parts.append(f"{len(decayed)} decayed signals")
    if changed:
        summary_parts.append(f"{len(changed)} changed signals")
    if score_change:
        summary_parts.append(f"score {'up' if score_change > 0 else 'down'} {abs(score_change):.1f}")

    digest = Digest(
        account_slug=account_slug,
        previous_run_id=prev_dir.name,
        current_run_id=curr_dir.name,
        new_signals=new_signals,
        changed_signals=changed,
        decayed_signals=decayed,
        score_change=score_change,
        is_material=is_material,
        summary="; ".join(summary_parts) if summary_parts else "No changes detected",
    )

    return digest


def run_digest(account_slug: str) -> str | None:
    digest = compare_runs(account_slug)
    if digest is None:
        return None

    md = render_digest(digest)
    out_dir = workspace.output_account_dir(account_slug)
    workspace.write_text(out_dir / "digest.md", md)
    return str(out_dir / "digest.md")


def _load_signals(path) -> list[Signal]:
    from pathlib import Path
    data = workspace.read_json(Path(path))
    if not data:
        return []
    return [Signal(**s) for s in data]


def _load_scorecard(path) -> Scorecard | None:
    from pathlib import Path
    data = workspace.read_json(Path(path))
    if not data:
        return None
    return Scorecard(**data)
