"""Monitoring digest renderer."""

from __future__ import annotations

from ..models import Digest


def render_digest(digest: Digest) -> str:
    lines: list[str] = []

    lines.append(f"# Weekly Digest: {digest.account_slug}")
    lines.append("")
    lines.append(f"*Comparing run `{digest.previous_run_id}` → `{digest.current_run_id}`*")
    lines.append(f"*Generated: {digest.generated_at.strftime('%Y-%m-%d %H:%M')} UTC*")
    lines.append("")

    if digest.is_material:
        lines.append("**⚠ Material changes detected.**")
    else:
        lines.append("No material changes detected.")
    lines.append("")

    if digest.score_change:
        direction = "↑" if digest.score_change > 0 else "↓"
        lines.append(f"**Score change:** {direction} {abs(digest.score_change):.1f} points")
        lines.append("")

    if digest.new_signals:
        lines.append("## New Signals")
        lines.append("")
        for delta in digest.new_signals:
            lines.append(f"- **{delta.category}:** {delta.description}")
        lines.append("")

    if digest.changed_signals:
        lines.append("## Changed Signals")
        lines.append("")
        for delta in digest.changed_signals:
            lines.append(f"- **{delta.category}:** {delta.description}")
        lines.append("")

    if digest.decayed_signals:
        lines.append("## Decayed Signals")
        lines.append("")
        for delta in digest.decayed_signals:
            lines.append(f"- **{delta.category}:** {delta.description}")
        lines.append("")

    if digest.summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(digest.summary)
        lines.append("")

    return "\n".join(lines)
