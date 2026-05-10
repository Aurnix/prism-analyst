"""Gift document renderer."""

from __future__ import annotations

from ..models import GiftDocument


def render_gift(gift: GiftDocument) -> str:
    lines: list[str] = []

    lines.append(f"# Market Insight Brief: {gift.account_slug}")
    lines.append("")
    lines.append(f"*Prepared: {gift.generated_at.strftime('%Y-%m-%d')}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(gift.content)
    lines.append("")

    return "\n".join(lines)


def render_redaction_report(gift: GiftDocument) -> str:
    lines: list[str] = []

    lines.append(f"# Redaction Report: {gift.account_slug}")
    lines.append("")
    lines.append(f"Items redacted or reframed: {len(gift.redacted_items)}")
    lines.append("")

    for item in gift.redacted_items:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)
