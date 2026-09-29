from __future__ import annotations

import json
import random
import urllib.parse
import urllib.request
from collections.abc import Iterable

from .models import Bar, MarketState


def fetch_binance_bars(
    symbol: str = "BTCUSDT", interval: str = "5m", limit: int = 1000
) -> list[Bar]:
    """Fetch public Binance spot klines. No API key is required."""
    params = urllib.parse.urlencode(
        {"symbol": symbol.upper(), "interval": interval, "limit": min(limit, 1000)}
    )
    url = f"https://api.binance.com/api/v3/klines?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "trading-agent/0.1"})
    with urllib.request.urlopen(req, timeout=15) as response:
        rows = json.load(response)
    return [
        Bar(
            ts=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )
        for row in rows
    ]


def synthetic_bars(count: int, *, seed: int = 7, start: float = 60_000.0) -> list[Bar]:
    """Deterministic BTC-like 5m bars for offline tests and fallback runs."""
    rng = random.Random(seed)
    bars: list[Bar] = []
    price = start
    ts = 1_700_000_000_000
    drift = 0.0
    vol = 0.002
    regime_left = 0
    for i in range(count):
        if regime_left <= 0:
            regime = rng.choice(("calm", "calm", "trend_up", "trend_down", "volatile"))
            drift = {"trend_up": 0.0008, "trend_down": -0.0008}.get(regime, 0.0)
            vol = 0.005 if regime == "volatile" else 0.002
            regime_left = rng.randint(20, 80)
        regime_left -= 1
        ret = rng.gauss(drift, vol)
        open_ = price
        close = max(100.0, open_ * (1.0 + ret))
        wiggle = abs(rng.gauss(0.0, vol / 2))
        high = max(open_, close) * (1.0 + wiggle)
        low = min(open_, close) * (1.0 - wiggle)
        volume = 100.0 * (0.5 + rng.random()) * (1.0 + abs(ret) * 50)
        bars.append(Bar(ts=ts + i * 300_000, open=open_, high=high, low=low, close=close, volume=volume))
        price = close
    return bars


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    value = values[0]
    for x in values[1:]:
        value = alpha * x + (1.0 - alpha) * value
    return value


def _rsi(values: list[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0
    gains = losses = 0.0
    for a, b in zip(values[-period - 1 : -1], values[-period:]):
        delta = b - a
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - 100.0 / (1.0 + rs)


def build_state(
    history: Iterable[Bar],
    *,
    position: float,
    unrealized_pnl: float,
    drawdown: float,
) -> MarketState:
    bars = list(history)
    if not bars:
        raise ValueError("at least one bar is required")
    closes = [b.close for b in bars]
    last = bars[-1]

    def ret(n: int) -> float:
        if len(closes) <= n:
            return 0.0
        return closes[-1] / closes[-1 - n] - 1.0

    ema_fast = _ema(closes[-60:], 9)
    ema_slow = _ema(closes[-120:], 21)
    trs = [
        max(
            b.high - b.low,
            abs(b.high - bars[i - 1].close),
            abs(b.low - bars[i - 1].close),
        )
        for i, b in enumerate(bars[-15:], start=max(0, len(bars) - 15))
        if i > 0
    ]
    atr = sum(trs[-14:]) / max(1, len(trs[-14:]))
    recent_vol = sum(b.volume for b in bars[-12:]) / max(1, len(bars[-12:]))
    prior = bars[-60:-12]
    prior_vol = sum(b.volume for b in prior) / max(1, len(prior)) if prior else recent_vol

    return MarketState(
        ts=last.ts,
        close=last.close,
        ret_1=ret(1),
        ret_3=ret(3),
        ret_12=ret(12),
        ema_fast_gap=(last.close / ema_fast - 1.0) if ema_fast else 0.0,
        ema_slow_gap=(last.close / ema_slow - 1.0) if ema_slow else 0.0,
        rsi_14=_rsi(closes),
        atr_pct=(atr / last.close) if last.close else 0.0,
        volume_ratio=(recent_vol / prior_vol) if prior_vol else 1.0,
        position=position,
        unrealized_pnl=unrealized_pnl,
        drawdown=drawdown,
    )
