from __future__ import annotations

from dataclasses import dataclass

from .models import MarketState, RiskVerdict


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_position_pct: float = 0.10
    max_drawdown: float = 0.05
    max_daily_loss_pct: float = 0.02
    min_confidence: float = 0.55
    min_setup_quality: float = 35.0


class RiskEngine:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def check(
        self,
        state: MarketState,
        *,
        equity: float,
        daily_pnl: float,
        confidence: float,
        setup_quality: float,
    ) -> RiskVerdict:
        l = self.limits
        if state.drawdown >= l.max_drawdown:
            return RiskVerdict(False, "max drawdown reached")
        if daily_pnl <= -(equity * l.max_daily_loss_pct):
            return RiskVerdict(False, "daily loss limit reached")
        if abs(state.position * state.close) >= equity * l.max_position_pct:
            return RiskVerdict(False, "max position reached")
        if confidence < l.min_confidence:
            return RiskVerdict(False, "confidence below threshold")
        if setup_quality < l.min_setup_quality:
            return RiskVerdict(False, "setup quality below threshold")
        return RiskVerdict(True, "ok")
