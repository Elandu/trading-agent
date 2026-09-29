from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True, slots=True)
class Performance:
    ending_equity: float
    net_pnl: float
    return_pct: float
    max_drawdown: float
    sharpe: float
    sortino: float
    profit_factor: float
    positive_period_rate: float


def summarize(equity_curve: list[float], *, starting_cash: float) -> Performance:
    if not equity_curve:
        raise ValueError("equity curve cannot be empty")

    returns: list[float] = []
    for prev, current in pairwise(equity_curve):
        if prev > 0:
            returns.append(current / prev - 1.0)

    peak = equity_curve[0]
    max_dd = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)

    if returns:
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / max(1, len(returns) - 1)
        std = math.sqrt(variance)
        downside = [min(0.0, r) for r in returns]
        downside_var = sum(r * r for r in downside) / max(1, len(downside))
        downside_std = math.sqrt(downside_var)
        # 5-minute crypto bars: 12 bars/hour * 24 hours * 365 days.
        annualizer = math.sqrt(12 * 24 * 365)
        sharpe = mean / std * annualizer if std > 0 else 0.0
        sortino = mean / downside_std * annualizer if downside_std > 0 else 0.0
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = -sum(r for r in returns if r < 0)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        positive_rate = sum(1 for r in returns if r > 0) / len(returns)
    else:
        sharpe = sortino = profit_factor = positive_rate = 0.0

    ending = equity_curve[-1]
    return Performance(
        ending_equity=ending,
        net_pnl=ending - starting_cash,
        return_pct=(ending / starting_cash - 1.0) * 100.0,
        max_drawdown=max_dd,
        sharpe=sharpe,
        sortino=sortino,
        profit_factor=profit_factor,
        positive_period_rate=positive_rate,
    )


def as_dict(perf: Performance) -> dict[str, float]:
    return {
        "ending_equity": round(perf.ending_equity, 2),
        "net_pnl": round(perf.net_pnl, 2),
        "return_pct": round(perf.return_pct, 4),
        "max_drawdown": round(perf.max_drawdown, 6),
        "sharpe": round(perf.sharpe, 4),
        "sortino": round(perf.sortino, 4),
        "profit_factor": round(perf.profit_factor, 4),
        "positive_period_rate": round(perf.positive_period_rate, 4),
    }
