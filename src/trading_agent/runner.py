from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from .decision import FallbackJudge, JevJudge
from .execution import PaperBroker
from .market import build_state
from .models import Bar
from .risk import RiskEngine
from .strategy import baseline_direction, target_fraction


@asynccontextmanager
async def _judge(use_jev: bool):
    if use_jev:
        async with JevJudge() as judge:
            yield judge
    else:
        yield FallbackJudge()


async def run_paper(
    bars: list[Bar],
    *,
    use_jev: bool = False,
    starting_cash: float = 10_000.0,
    fee_bps: float = 6.0,
    log_path: str = "data/experiments.jsonl",
) -> dict[str, float | int]:
    if len(bars) < 30:
        raise ValueError("need at least 30 bars")

    broker = PaperBroker(starting_cash=starting_cash, fee_bps=fee_bps)
    risk = RiskEngine()
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    async with _judge(use_jev) as judge:
        with path.open("w", encoding="utf-8") as log:
            for i in range(30, len(bars)):
                bar = bars[i]
                state = build_state(
                    bars[: i + 1],
                    position=broker.position,
                    unrealized_pnl=broker.unrealized(bar.close),
                    drawdown=broker.drawdown(bar.close),
                )
                judgment = await judge.judge(state)
                baseline = baseline_direction(state)
                equity = broker.equity(bar.close)
                verdict = risk.check(
                    state,
                    equity=equity,
                    daily_pnl=broker.realized - broker.fees,
                    confidence=judgment.confidence,
                    setup_quality=judgment.setup_quality,
                )

                if verdict.allowed:
                    target_notional = equity * target_fraction(judgment)
                    reason = f"{judgment.source}:{judgment.direction}"
                else:
                    # A veto can never create/increase exposure. Existing exposure
                    # is flattened so risk/uncertainty does not leave stale positions.
                    target_notional = 0.0
                    reason = f"risk:{verdict.reason}"

                trade = None
                if verdict.allowed or broker.position != 0.0:
                    trade = broker.target(
                        bar,
                        target_notional=target_notional,
                        reason=reason,
                    )

                record = {
                    "ts": bar.ts,
                    "price": bar.close,
                    "state": state.to_state_dict(),
                    "judgment": {
                        "regime": judgment.regime,
                        "direction": judgment.direction,
                        "setup_quality": judgment.setup_quality,
                        "confidence": judgment.confidence,
                        "source": judgment.source,
                        "latency_ms": judgment.latency_ms,
                    },
                    "baseline_direction": baseline,
                    "risk": {"allowed": verdict.allowed, "reason": verdict.reason},
                    "target_notional": target_notional,
                    "trade": None
                    if trade is None
                    else {
                        "side": trade.side,
                        "price": trade.price,
                        "quantity": trade.quantity,
                        "fee": trade.fee,
                    },
                    "equity": broker.equity(bar.close),
                }
                log.write(json.dumps(record, separators=(",", ":")) + "\n")

    last = bars[-1]
    return {
        "bars": len(bars),
        "trades": len(broker.trades),
        "ending_equity": round(broker.equity(last.close), 2),
        "net_pnl": round(broker.equity(last.close) - starting_cash, 2),
        "max_drawdown": round(broker.drawdown(last.close), 6),
    }
