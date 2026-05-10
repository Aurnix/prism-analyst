"""Account snapshot markdown renderer."""

from __future__ import annotations

from ..models import AccountProfile, Scorecard, Signal, SignalCategory, SourceItem


def render_snapshot(
    profile: AccountProfile,
    scorecard: Scorecard,
    signals: list[Signal],
    sources: list[SourceItem],
) -> str:
    lines: list[str] = []

    lines.append(f"# Account Snapshot: {profile.name}")
    lines.append("")

    lines.append("## Profile")
    lines.append("")
    lines.append(f"- **Domain:** {profile.domain or 'Unknown'}")
    if profile.industry:
        lines.append(f"- **Industry:** {profile.industry}")
    if profile.headcount:
        lines.append(f"- **Headcount:** {profile.headcount}")
    if profile.stage:
        lines.append(f"- **Stage:** {profile.stage}")
    if profile.location:
        lines.append(f"- **Location:** {profile.location}")
    if profile.description:
        lines.append(f"- **Description:** {profile.description[:200]}")
    lines.append("")

    lines.append("## Score")
    lines.append("")
    lines.append(f"- **Composite:** {scorecard.composite}")
    lines.append(f"- **Tier:** {scorecard.tier.value}")
    lines.append(f"- **ICP Fit:** {scorecard.icp_fit}")
    lines.append(f"- **Buying Readiness:** {scorecard.buying_readiness}")
    lines.append(f"- **Timing:** {scorecard.timing}")
    lines.append(f"- **Confidence:** {scorecard.confidence.value}")
    lines.append(f"- **Confidence Reason:** {scorecard.confidence_reason}")
    lines.append("")

    lines.append("## Signals")
    lines.append("")
    by_category: dict[SignalCategory, list[Signal]] = {}
    for s in signals:
        by_category.setdefault(s.category, []).append(s)

    for cat, sigs in sorted(by_category.items(), key=lambda x: x[0].value):
        lines.append(f"### {cat.value.title()}")
        for s in sorted(sigs, key=lambda x: x.strength, reverse=True):
            lines.append(f"- [{s.strength:.2f}] {s.text[:150]}")
        lines.append("")

    lines.append("## Sources")
    lines.append("")
    for src in sources:
        url_str = f" — {src.url}" if src.url else ""
        lines.append(f"- **{src.source_type.value}:** {src.title}{url_str}")
    lines.append("")

    lines.append(f"*{scorecard.signal_count} signals from {scorecard.source_count} sources*")
    lines.append("")

    return "\n".join(lines)
