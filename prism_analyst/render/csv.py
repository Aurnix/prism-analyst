"""CSV scorecard renderer."""

from __future__ import annotations

import csv
import io

from ..models import Scorecard


_FIELDS = [
    "account_slug",
    "account_name",
    "composite",
    "tier",
    "icp_fit",
    "buying_readiness",
    "timing",
    "confidence",
    "confidence_reason",
    "signal_count",
    "source_count",
    "scored_at",
]


def render_scorecard_csv(scorecards: list[Scorecard]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FIELDS)
    writer.writeheader()

    for card in sorted(scorecards, key=lambda c: c.composite, reverse=True):
        writer.writerow({
            "account_slug": card.account_slug,
            "account_name": card.account_name,
            "composite": card.composite,
            "tier": card.tier.value,
            "icp_fit": card.icp_fit,
            "buying_readiness": card.buying_readiness,
            "timing": card.timing,
            "confidence": card.confidence.value,
            "confidence_reason": card.confidence_reason,
            "signal_count": card.signal_count,
            "source_count": card.source_count,
            "scored_at": card.scored_at.isoformat(),
        })

    return buf.getvalue()
