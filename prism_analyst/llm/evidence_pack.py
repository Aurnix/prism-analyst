"""Evidence pack builder — selects the strongest evidence for LLM analysis."""

from __future__ import annotations

from ..config import settings
from ..models import (
    EvidenceItem,
    EvidencePack,
    Signal,
    SignalCategory,
    SignalType,
    SourceItem,
)


def build_evidence_pack(
    account_slug: str,
    sources: list[SourceItem],
    signals: list[Signal],
    max_items: int | None = None,
) -> EvidencePack:
    max_items = max_items or settings.max_evidence_items
    source_map = {s.id: s for s in sources}

    scored_items: list[tuple[float, EvidenceItem]] = []

    for signal in signals:
        source = source_map.get(signal.source_id)
        if source is None:
            continue

        signal_types: list[SignalType] = [signal.signal_type]
        categories: list[SignalCategory] = [signal.category] if signal.category else []
        sibling_signals = [
            s for s in signals
            if s.source_id == signal.source_id and s.id != signal.id
        ]
        for sib in sibling_signals:
            if sib.signal_type not in signal_types:
                signal_types.append(sib.signal_type)
            if sib.category and sib.category not in categories:
                categories.append(sib.category)

        item = EvidenceItem(
            source_id=source.id,
            source_type=source.source_type,
            title=source.title,
            url=source.url,
            date=source.metadata.get("published", source.fetched_at.isoformat()),
            excerpt=signal.text[:400],
            signal_types=signal_types,
            categories=categories,
            relevance_reason=_relevance_reason(signal),
            strength=signal.effective_weight,
            confidence=signal.confidence,
        )

        rank = signal.effective_weight + 0.1 * len(signal_types)
        scored_items.append((rank, item))

    scored_items.sort(key=lambda x: x[0], reverse=True)

    seen_sources: set[str] = set()
    items: list[EvidenceItem] = []
    for _, item in scored_items:
        if item.source_id in seen_sources and len(items) >= max_items // 2:
            continue
        seen_sources.add(item.source_id)
        items.append(item)
        if len(items) >= max_items:
            break

    return EvidencePack(
        account_slug=account_slug,
        items=items,
        model=settings.model,
    )


def _relevance_reason(signal: Signal) -> str:
    templates = {
        SignalCategory.HIRING: "Active hiring indicates growth or capability gap",
        SignalCategory.FUNDING: "Recent funding signals budget availability and growth mandate",
        SignalCategory.TECHNOLOGY: "Technology signals suggest infrastructure focus",
        SignalCategory.EXPANSION: "Expansion activity indicates scaling needs",
        SignalCategory.LEADERSHIP: "Leadership change may shift priorities and vendor decisions",
        SignalCategory.PRODUCT: "Product activity reveals strategic direction",
        SignalCategory.PAIN: "Pain signal suggests active problem awareness",
        SignalCategory.TIMING: "Timing indicator suggests a decision window",
        SignalCategory.COMPETITIVE: "Competitive signal indicates vendor evaluation",
        SignalCategory.OPERATIONAL: "Operational focus suggests process improvement priority",
    }
    return templates.get(signal.category, "Relevant signal detected")
