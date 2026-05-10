"""Per-signal-type temporal decay.

Mirrors PRISM-v2's decay model: each SignalType has a peak window (full
weight), a half-life (weight halves), and a maximum relevance period (after
which weight clamps to a floor). The computed value is stored on
``signal.decay_weight`` and combined with ``signal.strength`` when scoring.
"""

from __future__ import annotations

import math
from datetime import datetime

from ..config import SIGNAL_DECAY
from ..models import Signal, SignalType


_FLOOR = 0.05
_DEFAULT_PARAMS = (14, 45, 90)


def apply_decay(signals: list[Signal], reference_date: datetime | None = None) -> list[Signal]:
    now = reference_date or datetime.utcnow()

    for signal in signals:
        days = _days_old(signal, now)
        weight = decay_weight_for(signal.signal_type, days)
        signal.decay_weight = round(weight, 4)
        # Effective strength after decay (used by downstream scoring).
        signal.strength = round(min(signal.strength * weight, 1.0), 3)

    return signals


def decay_weight_for(signal_type: SignalType, days: int) -> float:
    """Return the temporal decay weight (0..1) for a signal of the given age."""
    peak, half_life, max_relevance = SIGNAL_DECAY.get(signal_type, _DEFAULT_PARAMS)

    if days < 0:
        return 1.0
    if days <= peak:
        return 1.0
    if days >= max_relevance:
        return _FLOOR

    # Exponential decay from the end of the peak window.
    elapsed = days - peak
    weight = math.pow(0.5, elapsed / max(half_life, 1))
    return max(weight, _FLOOR)


def _days_old(signal: Signal, now: datetime) -> int:
    if signal.recency_days is not None:
        return int(signal.recency_days)
    if signal.detected_date is not None:
        delta = now.date() - signal.detected_date
        return max(int(delta.days), 0)
    delta = now - signal.detected_at
    return max(int(delta.days), 0)


def decay_bar(weight: float, width: int = 10) -> str:
    """Render a decay bar using the same block characters as PRISM-v2."""
    weight = max(0.0, min(1.0, weight))
    filled = int(round(weight * width))
    if filled == width:
        return "█" * width
    if filled == 0:
        return "░" * width
    head = "█" * max(0, filled - 1)
    if weight >= 0.66:
        tail_char = "▓"
    elif weight >= 0.33:
        tail_char = "▒"
    else:
        tail_char = "░"
    return head + tail_char + "░" * (width - filled)


# Backwards-compatible step function used by older callers/tests.
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
