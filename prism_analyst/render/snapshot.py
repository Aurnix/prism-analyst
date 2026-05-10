"""Account snapshot markdown renderer."""

from __future__ import annotations

from ..config import ICP_WEIGHTS, READINESS_WEIGHTS, TIMING_WEIGHTS
from ..models import AccountProfile, Scorecard, Signal, SignalCategory, SourceItem
from ..signals.decay import decay_bar


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
    if profile.funding_stage or profile.stage:
        lines.append(f"- **Funding stage:** {profile.funding_stage or profile.stage}")
    if profile.location:
        lines.append(f"- **Location:** {profile.location}")
    if profile.tech_stack:
        lines.append(f"- **Tech stack:** {', '.join(profile.tech_stack)}")
    if profile.description:
        lines.append(f"- **Description:** {profile.description[:200]}")
    lines.append("")

    lines.append("## Score")
    lines.append("")
    lines.append(f"- **Composite:** {scorecard.composite}  ({scorecard.tier.value})")
    lines.append(
        f"  ├── ICP Fit ............ {scorecard.icp_fit:>5.1f}  "
        f"× {scorecard.weights.get('icp_fit', 0):.2f}  {decay_bar(scorecard.icp_fit/100)}"
    )
    lines.append(
        f"  ├── Buying Readiness ... {scorecard.buying_readiness:>5.1f}  "
        f"× {scorecard.weights.get('buying_readiness', 0):.2f}  "
        f"{decay_bar(scorecard.buying_readiness/100)}"
    )
    lines.append(
        f"  └── Timing ............. {scorecard.timing:>5.1f}  "
        f"× {scorecard.weights.get('timing', 0):.2f}  "
        f"{decay_bar(scorecard.timing/100)}"
    )
    lines.append(f"- **Confidence:** {scorecard.confidence.value} — {scorecard.confidence_reason}")
    lines.append("")

    lines.append("## Signals")
    lines.append("")
    by_category: dict[SignalCategory, list[Signal]] = {}
    for s in signals:
        by_category.setdefault(s.category, []).append(s)

    for cat, sigs in sorted(by_category.items(), key=lambda x: x[0].value):
        lines.append(f"### {cat.value.title()}")
        for s in sorted(sigs, key=lambda x: x.effective_weight, reverse=True):
            lines.append(
                f"- [{s.signal_type.value}] {s.text[:140]}  "
                f"_(weight {s.effective_weight:.2f}, {s.confidence.value})_"
            )
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
