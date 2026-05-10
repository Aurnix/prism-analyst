"""Deterministic signal extraction from source text."""

from __future__ import annotations

import re
from ..models import Signal, SignalCategory, SourceItem


_PATTERNS: list[tuple[SignalCategory, list[str], float]] = [
    # Hiring signals
    (SignalCategory.HIRING, [
        r"(?i)\b(?:hiring|we.re hiring|join our team|open role|open position|now hiring)\b",
        r"(?i)\b(?:head of|vp of|director of|senior|staff|principal|lead)\s+\w+",
        r"(?i)\b(?:engineer|developer|architect|designer|product manager|data scientist)\b",
    ], 0.6),

    # Funding signals
    (SignalCategory.FUNDING, [
        r"(?i)\b(?:series [a-f]|seed round|funding|raised|investment|venture|capital)\b",
        r"(?i)\$\d+[\d,.]*\s*(?:m|mm|million|b|billion)\b",
        r"(?i)\b(?:ipo|pre-ipo|going public|public offering)\b",
    ], 0.8),

    # Technology signals
    (SignalCategory.TECHNOLOGY, [
        r"(?i)\b(?:api|sdk|platform|infrastructure|cloud|aws|gcp|azure|kubernetes)\b",
        r"(?i)\b(?:migration|migrating|moderniz|refactor|re-?architect|re-?platform)\b",
        r"(?i)\b(?:tech stack|microservices|monolith|legacy|technical debt)\b",
        r"(?i)\b(?:ai|machine learning|ml|llm|genai|generative ai|automation)\b",
    ], 0.5),

    # Expansion signals
    (SignalCategory.EXPANSION, [
        r"(?i)\b(?:new market|expansion|expanding|launch|launching|entered|entering)\b",
        r"(?i)\b(?:new office|new region|international|global expansion|new country)\b",
        r"(?i)\b(?:new product|product line|product launch|ga|general availability)\b",
    ], 0.7),

    # Leadership signals
    (SignalCategory.LEADERSHIP, [
        r"(?i)\b(?:new ceo|new cto|new cfo|new coo|new cro|new cmo|new vp)\b",
        r"(?i)\b(?:appointed|promoted|joined as|named as|announces? .{0,20} as)\b",
        r"(?i)\b(?:board of directors|advisory board|new hire|executive team)\b",
    ], 0.7),

    # Product signals
    (SignalCategory.PRODUCT, [
        r"(?i)\b(?:new feature|release|version \d|v\d|update|upgrade|beta|preview)\b",
        r"(?i)\b(?:integration|partnership|partner|ecosystem|marketplace)\b",
        r"(?i)\b(?:pricing|plan|tier|enterprise|free trial|freemium)\b",
    ], 0.5),

    # Pain signals
    (SignalCategory.PAIN, [
        r"(?i)\b(?:challenge|struggling|pain point|bottleneck|inefficien|manual process)\b",
        r"(?i)\b(?:compliance|regulation|audit|security breach|incident|outage)\b",
        r"(?i)\b(?:cost reduction|budget cut|layoff|restructur|downsize)\b",
        r"(?i)\b(?:technical debt|legacy system|outdated|end of life|eol|sunset)\b",
    ], 0.6),

    # Timing signals
    (SignalCategory.TIMING, [
        r"(?i)\b(?:q[1-4]|fiscal year|end of year|budget cycle|planning cycle|renew)\b",
        r"(?i)\b(?:this quarter|next quarter|this year|by end of|deadline|timeline)\b",
        r"(?i)\b(?:ramp|scale|growing fast|rapid growth|hockey stick|hyper-?growth)\b",
    ], 0.6),

    # Competitive signals
    (SignalCategory.COMPETITIVE, [
        r"(?i)\b(?:switch|switching|migrate from|moving from|replacing|alternative to)\b",
        r"(?i)\b(?:compared to|versus|vs\.|competitor|competitive)\b",
        r"(?i)\b(?:rip and replace|vendor evaluation|rfp|request for proposal)\b",
    ], 0.7),

    # Operational signals
    (SignalCategory.OPERATIONAL, [
        r"(?i)\b(?:process improvement|workflow|automation|efficiency|operational)\b",
        r"(?i)\b(?:digital transformation|modernization|cloud native|devops|sre)\b",
    ], 0.5),
]


def extract_signals(sources: list[SourceItem]) -> list[Signal]:
    signals: list[Signal] = []
    seen: set[str] = set()

    for source in sources:
        text = f"{source.title}\n{source.content}"

        for category, patterns, base_strength in _PATTERNS:
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if not matches:
                    continue

                match_text = matches[0] if isinstance(matches[0], str) else matches[0][0]
                dedup_key = f"{category}:{match_text.lower().strip()[:40]}:{source.id}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                context = _get_context(text, match_text)
                strength = min(base_strength + 0.1 * (len(matches) - 1), 1.0)

                signals.append(Signal(
                    category=category,
                    text=context,
                    source_id=source.id,
                    strength=strength,
                ))

    return signals


def _get_context(text: str, match: str, window: int = 120) -> str:
    idx = text.lower().find(match.lower())
    if idx == -1:
        return match
    start = max(0, idx - window // 2)
    end = min(len(text), idx + len(match) + window // 2)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
