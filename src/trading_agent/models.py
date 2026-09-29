from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Bar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class MarketState:
    ts: int
    close: float
    ret_1: float
    ret_3: float
    ret_12: float
    ema_fast_gap: float
    ema_slow_gap: float
    rsi_14: float
    atr_pct: float
    volume_ratio: float
    position: float
    unrealized_pnl: float
    drawdown: float

    def to_state_dict(self) -> dict[str, float]:
        return {k: round(float(v), 6) for k, v in asdict(self).items()}


@dataclass(frozen=True, slots=True)
class Judgment:
    regime: str
    direction: str
    setup_quality: float
    confidence: float
    source: str = "fallback"
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class RiskVerdict:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Trade:
    ts: int
    side: str
    price: float
    quantity: float
    fee: float
    reason: str
