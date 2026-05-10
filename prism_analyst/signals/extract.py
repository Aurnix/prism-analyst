"""Deterministic signal extraction from source text.

Each pattern emits a specific PRISM-v2 SignalType, which auto-derives its
coarse SignalCategory via SIGNAL_TYPE_TO_CATEGORY. Strength is the base
relevance before temporal decay; per-source/source-type heuristics narrow
which patterns can fire (e.g. JOB_POSTING_* only on jobs sources).
"""

from __future__ import annotations

import re

from ..models import (
    Signal,
    SignalConfidence,
    SignalType,
    SourceItem,
    SourceType,
)


# (signal_type, regex_patterns, base_strength, allowed_source_types_or_None)
_PATTERNS: list[tuple[SignalType, list[str], float, set[SourceType] | None]] = [
    # --- Funding / financial events ---
    (SignalType.FUNDING_ROUND, [
        r"(?i)\b(?:series\s+[a-f]|seed round|pre-?seed)\b",
        r"(?i)\braised\s+\$\d+[\d,.]*\s*(?:m|mm|million|b|billion)\b",
        r"(?i)\b(?:closed|announced|secures?)\s+(?:a\s+)?\$\d+[\d,.]*\s*(?:m|mm|million|b|billion)\b",
        r"(?i)\b(?:funding round|venture round|growth round)\b",
    ], 0.9, None),

    (SignalType.EARNINGS_MENTION, [
        r"(?i)\b(?:q[1-4]\s+(?:earnings|results)|fiscal\s+(?:year|quarter)|earnings call)\b",
        r"(?i)\b(?:revenue\s+(?:grew|increased|declined)|guidance|10-?k|10-?q)\b",
    ], 0.6, None),

    # --- Leadership / champion ---
    (SignalType.NEW_EXECUTIVE_FINANCE, [
        r"(?i)\b(?:new|appointed|named|hired)\s+(?:cfo|chief financial officer|vp of finance|head of finance)\b",
    ], 0.85, None),

    (SignalType.NEW_EXECUTIVE_OTHER, [
        r"(?i)\b(?:new|appointed|named|hired)\s+(?:ceo|cto|coo|cro|cmo|cio|chief\s+\w+\s+officer)\b",
        r"(?i)\b(?:joined as|named as)\s+(?:vp|svp|head of|director of)\b",
    ], 0.7, None),

    (SignalType.CHAMPION_DEPARTED, [
        r"(?i)\b(?:departed|left|resigned|stepped down)\b.{0,40}\b(?:cfo|cto|ceo|vp|head of|director)\b",
        r"(?i)\b(?:formerly|previously)\s+(?:at|with)\b",
    ], 0.7, None),

    # --- Hiring / job postings (jobs source preferred) ---
    (SignalType.JOB_POSTING_FINANCE, [
        r"(?i)\b(?:financial analyst|controller|accountant|finance manager|fp&a|treasury|revenue operations)\b",
    ], 0.6, {SourceType.JOBS, SourceType.WEBSITE, SourceType.NEWS}),

    (SignalType.JOB_POSTING_TECHNICAL, [
        r"(?i)\b(?:senior|staff|principal|lead)\s+(?:engineer|developer|architect|sre|platform|infrastructure)\b",
        r"(?i)\b(?:engineering manager|director of engineering|head of platform)\b",
    ], 0.55, {SourceType.JOBS, SourceType.WEBSITE, SourceType.NEWS}),

    (SignalType.JOB_POSTING_URGENT, [
        r"(?i)\b(?:urgent|immediate hire|asap|backfill|critical role|fast.?track)\b",
        r"(?i)\b(?:we.?re hiring|now hiring|join our team)\b",
    ], 0.65, None),

    # --- Tech stack / migrations ---
    (SignalType.MIGRATION_SIGNAL, [
        r"(?i)\b(?:migrating?|migration|moving from|switching from|re-?platforming|rip and replace)\b",
        r"(?i)\b(?:replat(?:form|forming)|modernization|digital transformation)\b",
    ], 0.75, None),

    (SignalType.TECH_STACK_CHANGE, [
        r"(?i)\b(?:adopted|deployed|standardized on|rolled out)\s+(?:kubernetes|aws|gcp|azure|snowflake|databricks)\b",
        r"(?i)\b(?:tech stack|microservices|monolith|legacy|technical debt|re-?architect)\b",
        r"(?i)\b(?:llm|genai|generative ai|machine learning platform)\b",
    ], 0.55, None),

    # --- Content pain signals ---
    (SignalType.LINKEDIN_POST_PAIN, [
        r"(?i)\b(?:linkedin|li post|posted on linkedin)\b.{0,80}\b(?:struggling|challenge|frustrat|painful|broken|hard time)\b",
    ], 0.65, None),

    (SignalType.BLOG_POST_PAIN, [
        r"(?i)\b(?:struggling|challenge|pain point|bottleneck|inefficien|manual process|broken)\b",
        r"(?i)\b(?:technical debt|legacy system|outdated|end of life|eol|sunset)\b",
        r"(?i)\b(?:compliance|audit|security breach|incident|outage|downtime)\b",
    ], 0.6, {SourceType.WEBSITE, SourceType.NEWS, SourceType.MANUAL}),

    # --- News / press ---
    (SignalType.PRESS_RELEASE_RELEVANT, [
        r"(?i)\b(?:announces?|launching|launches|today announced|press release)\b",
        r"(?i)\b(?:partnership|integration|acquired|acquisition|merged with)\b",
        r"(?i)\b(?:new market|expansion|expanding|new office|new region|international)\b",
    ], 0.55, {SourceType.NEWS, SourceType.WEBSITE}),

    # --- Engagement / intent ---
    (SignalType.PRICING_PAGE_VISIT, [
        r"(?i)\b(?:pricing page|enterprise pricing|request a quote|talk to sales)\b",
    ], 0.5, None),

    (SignalType.CONTENT_ENGAGEMENT, [
        r"(?i)\b(?:downloaded|registered for|attended|webinar|whitepaper|case study)\b",
    ], 0.5, None),

    (SignalType.G2_RESEARCH_ACTIVITY, [
        r"(?i)\b(?:g2|trustradius|capterra|softwarereviews|gartner peer insights)\b",
    ], 0.6, None),

    # --- Competitive ---
    (SignalType.COMPETITOR_EVALUATION, [
        r"(?i)\b(?:vendor evaluation|rfp|request for proposal|short.?list|bake.?off)\b",
        r"(?i)\b(?:compared to|versus|vs\.|alternative to|switching from)\b",
    ], 0.7, None),

    (SignalType.COMPETITOR_CONTRACT_RENEWAL, [
        r"(?i)\b(?:contract renewal|renewal cycle|up for renewal|renew(?:s|ing)?\s+(?:in|with))\b",
    ], 0.65, None),

    # --- Glassdoor / org health ---
    (SignalType.GLASSDOOR_TREND, [
        r"(?i)\b(?:glassdoor|employee reviews?|culture rating|attrition|turnover)\b",
        r"(?i)\b(?:layoff|restructur|downsize|reorg|reduction in force|rif)\b",
    ], 0.55, None),
]


def extract_signals(sources: list[SourceItem]) -> list[Signal]:
    signals: list[Signal] = []
    seen: set[str] = set()

    for source in sources:
        text = f"{source.title}\n{source.content}"

        for signal_type, patterns, base_strength, allowed in _PATTERNS:
            if allowed is not None and source.source_type not in allowed:
                continue

            for pattern in patterns:
                matches = re.findall(pattern, text)
                if not matches:
                    continue

                match_text = matches[0] if isinstance(matches[0], str) else matches[0][0]
                dedup_key = f"{signal_type}:{match_text.lower().strip()[:40]}:{source.id}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                context = _get_context(text, match_text)
                strength = min(base_strength + 0.1 * (len(matches) - 1), 1.0)

                signals.append(Signal(
                    signal_type=signal_type,
                    text=context,
                    description=context,
                    source_id=source.id,
                    source=source.url or source.title,
                    strength=strength,
                    confidence=SignalConfidence.EXTRACTED,
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
