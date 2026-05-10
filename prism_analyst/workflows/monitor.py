"""Monitoring and snapshot comparison workflow.

Produces a Digest that mirrors PRISM-v2's schema: typed deltas
(new/decayed/removed/changed), severity-grouped entries
(critical/warning/update), and a score snapshot showing the previous and
current composite scores plus the per-dimension breakdown.
"""

from __future__ import annotations

from pathlib import Path

from ..models import (
    DeltaType,
    Digest,
    DigestEntry,
    DigestSeverity,
    ScoreSnapshot,
    Scorecard,
    Signal,
    SignalDelta,
    SignalType,
)
from ..render.digest import render_digest
from ..workspace import workspace


_MATERIAL_SCORE_CHANGE = 10.0
_MATERIAL_NEW_SIGNALS = 3

# Signal types whose first-time arrival is treated as critical.
_CRITICAL_TYPES: set[SignalType] = {
    SignalType.FUNDING_ROUND,
    SignalType.NEW_EXECUTIVE_FINANCE,
    SignalType.CHAMPION_DEPARTED,
    SignalType.MIGRATION_SIGNAL,
    SignalType.COMPETITOR_CONTRACT_RENEWAL,
}
_WARNING_TYPES: set[SignalType] = {
    SignalType.NEW_EXECUTIVE_OTHER,
    SignalType.JOB_POSTING_FINANCE,
    SignalType.JOB_POSTING_URGENT,
    SignalType.COMPETITOR_EVALUATION,
    SignalType.GLASSDOOR_TREND,
}


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
            signal_type=s.signal_type,
            category=s.category.value if s.category else "unknown",
            description=s.text[:150],
            delta_type=DeltaType.NEW,
        ))

    decayed: list[SignalDelta] = []
    removed: list[SignalDelta] = []
    for sid in prev_ids - curr_ids:
        s = prev_map[sid]
        # Distinguish "decayed away" (still relevant but weight collapsed) from
        # "removed" (the source disappeared).
        delta_kind = DeltaType.DECAYED if s.decay_weight < 0.2 else DeltaType.REMOVED
        delta = SignalDelta(
            signal_type=s.signal_type,
            category=s.category.value if s.category else "unknown",
            description=s.text[:150],
            delta_type=delta_kind,
            weight_change=-s.decay_weight,
        )
        if delta_kind == DeltaType.DECAYED:
            decayed.append(delta)
        else:
            removed.append(delta)

    changed: list[SignalDelta] = []
    for sid in prev_ids & curr_ids:
        old_s = prev_map[sid]
        new_s = curr_map[sid]
        if abs(old_s.decay_weight - new_s.decay_weight) > 0.15:
            direction = "strengthened" if new_s.decay_weight > old_s.decay_weight else "weakened"
            changed.append(SignalDelta(
                signal_type=new_s.signal_type,
                category=new_s.category.value if new_s.category else "unknown",
                description=f"{direction}: {new_s.text[:120]}",
                delta_type=DeltaType.CHANGED,
                weight_change=round(new_s.decay_weight - old_s.decay_weight, 3),
            ))

    score_change = 0.0
    if prev_card and curr_card:
        score_change = curr_card.composite - prev_card.composite

    is_material = (
        abs(score_change) >= _MATERIAL_SCORE_CHANGE
        or len(new_signals) >= _MATERIAL_NEW_SIGNALS
        or any(d.signal_type in _CRITICAL_TYPES for d in new_signals)
    )

    snapshot = _build_snapshot(prev_card, curr_card)
    entries = _build_entries(new_signals, removed, changed, score_change)
    action = _build_action_update(new_signals, score_change)

    summary_parts: list[str] = []
    if new_signals:
        summary_parts.append(f"{len(new_signals)} new signals")
    if removed:
        summary_parts.append(f"{len(removed)} removed signals")
    if decayed:
        summary_parts.append(f"{len(decayed)} decayed signals")
    if changed:
        summary_parts.append(f"{len(changed)} changed signals")
    if score_change:
        summary_parts.append(f"score {'up' if score_change > 0 else 'down'} {abs(score_change):.1f}")

    return Digest(
        account_slug=account_slug,
        previous_run_id=prev_dir.name,
        current_run_id=curr_dir.name,
        score_snapshot=snapshot,
        entries=entries,
        new_signals=new_signals,
        changed_signals=changed,
        decayed_signals=decayed,
        removed_signals=removed,
        score_change=round(score_change, 1),
        is_material=is_material,
        summary="; ".join(summary_parts) if summary_parts else "No changes detected",
        action_update=action,
    )


def run_digest(account_slug: str) -> str | None:
    digest = compare_runs(account_slug)
    if digest is None:
        return None

    md = render_digest(digest)
    out_dir = workspace.output_account_dir(account_slug)
    workspace.write_text(out_dir / "digest.md", md)
    workspace.write_json(out_dir / "digest.json", digest.model_dump(mode="json"))
    return str(out_dir / "digest.md")


def _build_snapshot(prev: Scorecard | None, curr: Scorecard | None) -> ScoreSnapshot:
    if not curr:
        return ScoreSnapshot()
    return ScoreSnapshot(
        composite=curr.composite,
        previous_composite=prev.composite if prev else None,
        delta=round(curr.composite - prev.composite, 1) if prev else 0.0,
        tier=curr.tier,
        icp_fit=curr.icp_fit,
        buying_readiness=curr.buying_readiness,
        timing=curr.timing,
    )


def _build_entries(
    new_signals: list[SignalDelta],
    removed: list[SignalDelta],
    changed: list[SignalDelta],
    score_change: float,
) -> list[DigestEntry]:
    entries: list[DigestEntry] = []

    for d in new_signals:
        if d.signal_type in _CRITICAL_TYPES:
            entries.append(DigestEntry(
                severity=DigestSeverity.CRITICAL,
                headline=f"New {d.signal_type.value}",
                detail=d.description,
            ))
        elif d.signal_type in _WARNING_TYPES:
            entries.append(DigestEntry(
                severity=DigestSeverity.WARNING,
                headline=f"New {d.signal_type.value}",
                detail=d.description,
            ))
        else:
            entries.append(DigestEntry(
                severity=DigestSeverity.UPDATE,
                headline=f"New {d.signal_type.value if d.signal_type else d.category} signal",
                detail=d.description,
            ))

    for d in removed:
        entries.append(DigestEntry(
            severity=DigestSeverity.WARNING,
            headline=f"Removed {d.signal_type.value if d.signal_type else d.category} signal",
            detail=d.description,
        ))

    if score_change >= _MATERIAL_SCORE_CHANGE:
        entries.append(DigestEntry(
            severity=DigestSeverity.CRITICAL,
            headline=f"Score up {score_change:.1f} points",
        ))
    elif score_change <= -_MATERIAL_SCORE_CHANGE:
        entries.append(DigestEntry(
            severity=DigestSeverity.WARNING,
            headline=f"Score down {abs(score_change):.1f} points",
        ))

    return entries


def _build_action_update(new_signals: list[SignalDelta], score_change: float) -> str:
    critical = [d for d in new_signals if d.signal_type in _CRITICAL_TYPES]
    if critical:
        return (
            "Re-run the full dossier — critical event detected "
            f"({critical[0].signal_type.value})."
        )
    if score_change >= _MATERIAL_SCORE_CHANGE:
        return "Promote to active outreach — score crossed material threshold."
    if score_change <= -_MATERIAL_SCORE_CHANGE:
        return "Demote priority — buying signals weakened."
    return ""


def _load_signals(path: Path) -> list[Signal]:
    data = workspace.read_json(path)
    if not data:
        return []
    return [Signal(**s) for s in data]


def _load_scorecard(path: Path) -> Scorecard | None:
    data = workspace.read_json(path)
    if not data:
        return None
    return Scorecard(**data)
