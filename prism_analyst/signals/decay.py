"""Signal recency decay."""

from __future__ import annotations

import math
from datetime import datetime

from ..models import Signal


def apply_decay(signals: list[Signal], reference_date: datetime | None = None) -> list[Signal]:
    now = reference_date or datetime.utcnow()

    for signal in signals:
        if signal.recency_days is not None:
            days = signal.recency_days
        else:
            delta = now - signal.detected_at
            days = delta.days

        decay_factor = _decay_factor(days)
        signal.strength = round(signal.strength * decay_factor, 3)

    return signals


def _decay_factor(days: int) -> float:
    if days <= 7:
        return 1.0
    if days <= 30:
        return 0.9
    if days <= 90:
        return 0.7
    if days <= 180:
        return 0.4
    return 0.2
