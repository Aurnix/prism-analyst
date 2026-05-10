"""Monitoring digest renderer.

Mirrors PRISM-v2's digest layout: header banner, score snapshot with
previous/current/delta, severity-grouped entries (critical/warning/update),
typed delta lines (new/decayed/removed), action update line, optional LLM
narrative, footer.
"""

from __future__ import annotations

from ..models import Digest, DigestSeverity, SignalDelta


def render_digest(digest: Digest) -> str:
    lines: list[str] = []

    bar = "-" * 60
    lines.append(bar)
    lines.append("PRISM SIGNAL DIGEST")
    lines.append(bar)
    lines.append(
        f"Account: {digest.account_slug} | "
        f"Generated: {digest.generated_at.strftime('%Y-%m-%d %H:%M')} UTC | "
        f"Material: {'yes' if digest.is_material else 'no'}"
    )
    lines.append(
        f"Run: {digest.previous_run_id} → {digest.current_run_id}"
    )
    lines.append("")

    # --- Score snapshot ---
    snap = digest.score_snapshot
    lines.append("**Score Snapshot**")
    delta_arrow = "↑" if snap.delta > 0 else ("↓" if snap.delta < 0 else "·")
    prev = (
        f"{snap.previous_composite:.1f}" if snap.previous_composite is not None else "—"
    )
    lines.append(
        f"- Composite: {snap.composite:.1f} ({snap.tier.value})  "
        f"prev {prev}  {delta_arrow} {abs(snap.delta):.1f}"
    )
    lines.append(
        f"  ├── ICP Fit ............ {snap.icp_fit:.1f}"
    )
    lines.append(
        f"  ├── Buying Readiness ... {snap.buying_readiness:.1f}"
    )
    lines.append(
        f"  └── Timing ............. {snap.timing:.1f}"
    )
    lines.append("")

    # --- Severity entries ---
    if digest.entries:
        critical = [e for e in digest.entries if e.severity == DigestSeverity.CRITICAL]
        warnings = [e for e in digest.entries if e.severity == DigestSeverity.WARNING]
        updates = [e for e in digest.entries if e.severity == DigestSeverity.UPDATE]

        if critical:
            lines.append("**Critical**")
            for e in critical:
                lines.append(f"● {e.headline}")
                if e.detail:
                    lines.append(f"   {e.detail}")
            lines.append("")
        if warnings:
            lines.append("**Warnings**")
            for e in warnings:
                lines.append(f"▲ {e.headline}")
                if e.detail:
                    lines.append(f"   {e.detail}")
            lines.append("")
        if updates:
            lines.append("**Updates**")
            for e in updates:
                lines.append(f"○ {e.headline}")
                if e.detail:
                    lines.append(f"   {e.detail}")
            lines.append("")

    # --- Signal deltas (typed) ---
    if digest.new_signals or digest.decayed_signals or digest.removed_signals:
        lines.append("**Signal Deltas**")
        for d in digest.new_signals:
            lines.append(_delta_line("+", d))
        for d in digest.decayed_signals:
            lines.append(_delta_line("↓", d))
        for d in digest.removed_signals:
            lines.append(_delta_line("-", d))
        for d in digest.changed_signals:
            lines.append(_delta_line("~", d))
        lines.append("")

    if digest.action_update:
        lines.append(f"► {digest.action_update}")
        lines.append("")

    if digest.llm_narrative:
        lines.append("**Analysis**")
        lines.append("")
        lines.append(digest.llm_narrative)
        lines.append("")

    if digest.summary:
        lines.append(f"_Summary: {digest.summary}_")
        lines.append("")

    lines.append(bar)
    lines.append(f"end-of-digest :: {digest.account_slug}")
    lines.append(bar)

    return "\n".join(lines)


def _delta_line(prefix: str, d: SignalDelta) -> str:
    type_label = d.signal_type.value if d.signal_type else d.category
    suffix = ""
    if d.weight_change is not None:
        suffix = f" (Δ weight {d.weight_change:+.2f})"
    return f"{prefix} [{type_label}] {d.description}{suffix}"
