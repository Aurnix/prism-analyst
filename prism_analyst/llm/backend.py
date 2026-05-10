"""LLM backend abstraction using Anthropic SDK."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import settings
from ..models import (
    Brief,
    BuyingStage,
    ConfidenceLevel,
    Dossier,
    DossierSection,
    EvidencePack,
    GiftDocument,
)
from ..workspace import workspace


_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


def _format_evidence(pack: EvidencePack) -> str:
    lines: list[str] = []
    for i, item in enumerate(pack.items, 1):
        types = ", ".join(t.value for t in item.signal_types)
        lines.append(
            f"[{i}] {item.title}\n"
            f"    Source: {item.source_type.value} | {item.url or 'N/A'}\n"
            f"    Date: {item.date or 'Unknown'}\n"
            f"    Signal types: {types}\n"
            f"    Confidence: {item.confidence.value}\n"
            f"    Relevance: {item.relevance_reason}\n"
            f"    Excerpt: {item.excerpt}\n"
        )
    return "\n".join(lines)


def _call_llm(prompt: str, cache_key: str) -> str:
    cached = workspace.get_cache(cache_key)
    if cached:
        return cached

    if not settings.anthropic_api_key:
        return "[LLM unavailable — no ANTHROPIC_API_KEY configured]"

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model=settings.model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    workspace.set_cache(cache_key, text)
    return text


def run_quick_brief(pack: EvidencePack, account_name: str) -> Brief:
    template = _load_prompt("quick_brief.md")
    evidence_text = _format_evidence(pack)
    prompt = template.replace("{{ACCOUNT_NAME}}", account_name).replace(
        "{{EVIDENCE}}", evidence_text
    )

    cache_key = workspace.cache_key(
        "quick_brief", pack.account_slug, pack.content_hash(), settings.model, "v1"
    )
    raw = _call_llm(prompt, cache_key)

    return Brief(
        account_slug=pack.account_slug,
        raw_llm_output=raw,
        account_read=_extract_section(raw, "Account Read"),
        important_signals=_extract_section(raw, "Most Important Signals"),
        buying_stage=_parse_buying_stage(
            _extract_section(raw, "Buying-Readiness Stage")
        ),
        why_now=_extract_section(raw, "Why-Now Hypothesis"),
        recommended_action=_extract_section(raw, "Recommended Next Action"),
        outreach_angle=_extract_section(raw, "Suggested Outreach Angle"),
        collection_gaps=_extract_section(raw, "Collection Gaps"),
        confidence=_parse_confidence(_extract_section(raw, "Confidence")),
        model=settings.model,
        prompt_version="v1",
        evidence_hash=pack.content_hash(),
    )


def run_full_dossier(pack: EvidencePack, account_name: str) -> Dossier:
    template = _load_prompt("full_dossier.md")
    evidence_text = _format_evidence(pack)
    prompt = template.replace("{{ACCOUNT_NAME}}", account_name).replace(
        "{{EVIDENCE}}", evidence_text
    )

    cache_key = workspace.cache_key(
        "full_dossier", pack.account_slug, pack.content_hash(), settings.model, "v1"
    )
    raw = _call_llm(prompt, cache_key)

    section_titles = [
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

    sections: list[DossierSection] = []
    for title in section_titles:
        content = _extract_section(raw, title)
        sections.append(DossierSection(title=title, content=content))

    return Dossier(
        account_slug=pack.account_slug,
        sections=sections,
        raw_llm_output=raw,
        model=settings.model,
        prompt_version="v1",
        evidence_hash=pack.content_hash(),
    )


def run_gift_doc(pack: EvidencePack, account_name: str, dossier_text: str) -> GiftDocument:
    template = _load_prompt("gift_doc.md")
    prompt = (
        template.replace("{{ACCOUNT_NAME}}", account_name)
        .replace("{{DOSSIER}}", dossier_text)
        .replace("{{EVIDENCE}}", _format_evidence(pack))
    )

    cache_key = workspace.cache_key(
        "gift_doc", pack.account_slug, pack.content_hash(), settings.model, "v1"
    )
    raw = _call_llm(prompt, cache_key)

    redacted: list[str] = []
    redaction_section = _extract_section(raw, "Redaction Report")
    if redaction_section:
        for line in redaction_section.splitlines():
            line = line.strip().lstrip("- ")
            if line:
                redacted.append(line)

    content = _extract_section(raw, "Gift Document")
    if not content:
        content = raw

    return GiftDocument(
        account_slug=pack.account_slug,
        content=content,
        redacted_items=redacted,
        raw_llm_output=raw,
        model=settings.model,
    )


def _extract_section(text: str, heading: str) -> str:
    import re

    # Try the exact heading first, then a normalized variant that tolerates
    # different punctuation (em-dash vs hyphen, ampersand vs "and").
    candidates = [heading]
    normalized = (
        heading.replace("—", "-").replace("&", "and").replace(" - ", " ")
    )
    if normalized != heading:
        candidates.append(normalized)

    for candidate in candidates:
        pattern = rf"#+\s*{re.escape(candidate)}\s*\n(.*?)(?=\n#+\s|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _parse_buying_stage(text: str) -> BuyingStage:
    text_lower = text.lower()
    for stage in BuyingStage:
        if stage.value.replace("_", " ") in text_lower or stage.value in text_lower:
            return stage
    return BuyingStage.UNKNOWN


def _parse_confidence(text: str) -> ConfidenceLevel:
    text_lower = text.lower()
    if "high" in text_lower:
        return ConfidenceLevel.HIGH
    if "medium" in text_lower:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW
