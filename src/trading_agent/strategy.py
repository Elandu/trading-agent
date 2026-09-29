from __future__ import annotations

from .models import Judgment, MarketState


def baseline_direction(state: MarketState) -> str:
    """Simple benchmark the agent must beat: EMA/momentum with RSI guardrails."""
    if state.ema_fast_gap > 0.001 and state.ret_3 > 0 and state.rsi_14 < 75:
        return "long"
    if state.ema_fast_gap < -0.001 and state.ret_3 < 0 and state.rsi_14 > 25:
        return "short"
    return "flat"


def target_fraction(judgment: Judgment) -> float:
    if judgment.direction == "flat":
        return 0.0
    strength = min(1.0, max(0.0, judgment.setup_quality / 100.0))
    confidence = min(1.0, max(0.0, judgment.confidence))
    fraction = 0.10 * strength * confidence
    return fraction if judgment.direction == "long" else -fraction
