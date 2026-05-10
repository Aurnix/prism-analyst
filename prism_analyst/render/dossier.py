"""Full dossier markdown renderer.

Mirrors PRISM-v2's dossier shape: nine sections, score-tree breakdown with
weights, decay-bar timeline, and a typed signal taxonomy in the appendix. The
renderer accepts a Dossier with optional pre-computed views (scorecard,
signals, sources, profile) and falls back to the raw LLM section content
when those views aren't attached.
"""

from __future__ import annotations

from ..models import (
    Dossier,
    DossierSection,
    Scorecard,
    Signal,
    SignalConfidence,
    SourceItem,
)
from ..signals.decay import decay_bar


SECTION_ORDER: list[str] = [
    "Executive Summary",
    "Subject Profile",
    "Organizational Intelligence Assessment",
    "Key Personnel — Buying Committee Map",
    "Signal Timeline",
    "Why Now — Hypothesis",
    "Recommended Play",
    "Collection Gaps & Discovery Questions",
    "Appendix — Raw Signals & Sources",
]


def render_dossier(dossier: Dossier) -> str:
    lines: list[str] = []

    # --- Header ---
    name = dossier.profile.name if dossier.profile else dossier.account_slug
    tier = dossier.scorecard.tier.value if dossier.scorecard else "Unscored"
    confidence = (
        dossier.scorecard.confidence.value if dossier.scorecard else "low"
    )
    lines.append("=" * 60)
    lines.append(f"PRISM INTELLIGENCE DOSSIER — {name}")
    lines.append("=" * 60)
    lines.append(
        f"Tier: {tier} | Confidence: {confidence} | "
        f"Generated: {dossier.generated_at.strftime('%Y-%m-%d %H:%M')} UTC"
    )
    lines.append(
        f"Model: {dossier.model or 'n/a'} | Prompt: {dossier.prompt_version}"
    )
    lines.append("")

    section_map = {s.title: s for s in dossier.sections}

    for i, title in enumerate(SECTION_ORDER, 1):
        section = section_map.get(title) or _fuzzy_section(section_map, title)
        lines.append(f"## {i}. {title}")
        lines.append("")

        # Section-specific augmentations using attached structured data.
        if i == 1:
            lines.extend(_executive_summary_block(dossier, section))
        elif i == 2:
            lines.extend(_subject_profile_block(dossier, section))
        elif i == 3:
            lines.extend(_org_intel_block(dossier, section))
        elif i == 5:
            lines.extend(_timeline_block(dossier, section))
        elif i == 9:
            lines.extend(_appendix_block(dossier, section))
        else:
            lines.append(_section_body(section))

        lines.append("")

    lines.append("-" * 60)
    lines.append(f"Dossier ID: {dossier.account_slug}/{dossier.evidence_hash or 'n/a'}")
    lines.append("-" * 60)

    return "\n".join(lines)


# --- Section blocks ---

def _executive_summary_block(d: Dossier, section: DossierSection | None) -> list[str]:
    out: list[str] = []
    if d.scorecard:
        out.append(_score_tree(d.scorecard))
        out.append("")
    out.append(_section_body(section))
    return out


def _subject_profile_block(d: Dossier, section: DossierSection | None) -> list[str]:
    out: list[str] = []
    if d.profile:
        p = d.profile
        out.append("**Firmographics**")
        out.append("")
        rows = [
            ("Domain", p.domain),
            ("Industry", p.industry),
            ("Headcount", p.headcount),
            ("Funding stage", p.funding_stage or p.stage),
            ("Location", p.location),
            ("Tech stack", ", ".join(p.tech_stack) if p.tech_stack else None),
        ]
        for label, value in rows:
            if value:
                out.append(f"- **{label}:** {value}")
        out.append("")
    if d.scorecard:
        out.append("**ICP Fit Components**")
        out.append("")
        out.append(_icp_breakdown_block(d.scorecard))
        out.append("")
    out.append(_section_body(section))
    return out


def _org_intel_block(d: Dossier, section: DossierSection | None) -> list[str]:
    out: list[str] = []
    if d.scorecard:
        out.append("**Buying Readiness Components**")
        out.append("")
        out.append(_readiness_breakdown_block(d.scorecard))
        out.append("")
    out.append(_section_body(section))
    return out


def _timeline_block(d: Dossier, section: DossierSection | None) -> list[str]:
    out: list[str] = []
    if d.signals:
        out.append("**Signal Timeline (decay-weighted, newest first)**")
        out.append("")
        sorted_sigs = sorted(
            d.signals,
            key=lambda s: (s.detected_date or s.detected_at.date()),
            reverse=True,
        )
        for s in sorted_sigs[:25]:
            out.append(_signal_line(s))
        out.append("")
    if d.scorecard:
        out.append("**Timing Components**")
        out.append("")
        out.append(_timing_breakdown_block(d.scorecard))
        out.append("")
    out.append(_section_body(section))
    return out


def _appendix_block(d: Dossier, section: DossierSection | None) -> list[str]:
    out: list[str] = []

    if d.signals:
        out.append("**Signal Taxonomy (extracted | interpolated | generated)**")
        out.append("")
        counts: dict[str, int] = {}
        for s in d.signals:
            counts[s.confidence.value] = counts.get(s.confidence.value, 0) + 1
        for label in (SignalConfidence.EXTRACTED, SignalConfidence.INTERPOLATED,
                       SignalConfidence.GENERATED):
            out.append(f"- {label.value}: {counts.get(label.value, 0)}")
        out.append("")

        out.append("**Raw Signals**")
        out.append("")
        for i, s in enumerate(d.signals, 1):
            out.append(
                f"{i}. [{s.signal_type.value}] {s.text[:160]}  "
                f"_(weight {s.effective_weight:.2f}, {s.confidence.value})_"
            )
        out.append("")

    if d.sources:
        out.append("**Sources**")
        out.append("")
        for i, src in enumerate(d.sources, 1):
            url = f" — {src.url}" if src.url else ""
            out.append(f"{i}. [{src.source_type.value}] {src.title}{url}")
        out.append("")

    out.append(_section_body(section))
    return out


# --- Score-tree helpers ---

def _score_tree(card: Scorecard) -> str:
    lines: list[str] = []
    lines.append(f"**Composite Score:** {card.composite}  ({card.tier.value})")
    lines.append(
        f"  ├── ICP Fit ............ {card.icp_fit:>5.1f}  "
        f"× {card.weights.get('icp_fit', 0):.2f}  {decay_bar(card.icp_fit/100)}"
    )
    lines.append(
        f"  ├── Buying Readiness ... {card.buying_readiness:>5.1f}  "
        f"× {card.weights.get('buying_readiness', 0):.2f}  "
        f"{decay_bar(card.buying_readiness/100)}"
    )
    lines.append(
        f"  └── Timing ............. {card.timing:>5.1f}  "
        f"× {card.weights.get('timing', 0):.2f}  {decay_bar(card.timing/100)}"
    )
    lines.append(f"**Confidence:** {card.confidence.value} — {card.confidence_reason}")
    return "\n".join(lines)


def _icp_breakdown_block(card: Scorecard) -> str:
    from ..config import ICP_WEIGHTS

    b = card.icp_breakdown.model_dump()
    rows = []
    for key, weight in ICP_WEIGHTS.items():
        val = b.get(key, 0.0)
        rows.append(
            f"- {key.replace('_', ' ').title():<14} {val:>4.2f}  "
            f"× {weight:.2f}  {decay_bar(val)}"
        )
    return "\n".join(rows)


def _readiness_breakdown_block(card: Scorecard) -> str:
    from ..config import READINESS_WEIGHTS

    b = card.readiness_breakdown.model_dump()
    rows = []
    for key, weight in READINESS_WEIGHTS.items():
        val = b.get(key, 0.0)
        rows.append(
            f"- {key.replace('_', ' ').title():<24} {val:>4.2f}  "
            f"× {weight:.2f}  {decay_bar(val)}"
        )
    return "\n".join(rows)


def _timing_breakdown_block(card: Scorecard) -> str:
    from ..config import TIMING_WEIGHTS

    b = card.timing_breakdown.model_dump()
    rows = []
    for key, weight in TIMING_WEIGHTS.items():
        val = b.get(key, 0.0)
        rows.append(
            f"- {key.replace('_', ' ').title():<26} {val:>4.2f}  "
            f"× {weight:.2f}  {decay_bar(val)}"
        )
    return "\n".join(rows)


def _signal_line(s: Signal) -> str:
    when = (s.detected_date or s.detected_at.date()).isoformat()
    return (
        f"- `{when}` [{s.signal_type.value}] {s.text[:140]}  "
        f"{decay_bar(s.decay_weight, 6)}  ({s.confidence.value})"
    )


def _section_body(section: DossierSection | None) -> str:
    if section and section.content:
        return section.content
    return "_No data available for this section._"


def _fuzzy_section(
    section_map: dict[str, DossierSection],
    target: str,
) -> DossierSection | None:
    """Match LLM-emitted section titles that use slightly different punctuation."""
    norm_target = _normalize(target)
    for title, section in section_map.items():
        if _normalize(title) == norm_target:
            return section
    return None


def _normalize(s: str) -> str:
    return (
        s.lower()
        .replace("—", " ")
        .replace("-", " ")
        .replace("&", "and")
        .replace(":", " ")
        .replace("  ", " ")
        .strip()
    )
