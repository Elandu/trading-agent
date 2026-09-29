from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from .decision import FallbackJudge, JevJudge
from .execution import PaperBroker
from .market import build_state
from .metrics import as_dict, summarize
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


def _baseline_fraction(direction: str) -> float:
    if direction == "long":
        return 0.10
    if direction == "short":
        return -0.10
    return 0.0


def _position_direction(position: float) -> str:
    if position > 0:
        return "long"
    if position < 0:
        return "short"
    return "flat"


def _write_log(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_paper(
    bars: list[Bar],
    *,
    use_jev: bool = False,
    starting_cash: float = 10_000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 2.0,
    min_hold_bars: int = 3,
    min_trade_notional: float = 25.0,
    log_path: str = "data/experiments.jsonl",
) -> dict[str, object]:
    if len(bars) < 30:
        raise ValueError("need at least 30 bars")

    agent = PaperBroker(
        starting_cash=starting_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        min_trade_notional=min_trade_notional,
    )
    baseline_broker = PaperBroker(
        starting_cash=starting_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        min_trade_notional=min_trade_notional,
    )
    risk = RiskEngine()
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    agent_equity = [starting_cash]
    baseline_equity = [starting_cash]
    log_lines: list[str] = []
    agent_last_trade_i = -10_000
    baseline_last_trade_i = -10_000

    async with _judge(use_jev) as judge:
        for i in range(30, len(bars)):
            bar = bars[i]

            state = build_state(
                bars[: i + 1],
                position=agent.position,
                unrealized_pnl=agent.unrealized(bar.close),
                drawdown=agent.drawdown(bar.close),
            )
            judgment = await judge.judge(state)
            agent_value = agent.equity(bar.close)
            verdict = risk.check(
                state,
                equity=agent_value,
                daily_pnl=agent.realized - agent.fees,
                confidence=judgment.confidence,
                setup_quality=judgment.setup_quality,
            )

            requested_direction = judgment.direction if verdict.allowed else "flat"
            current_direction = _position_direction(agent.position)
            hold_ok = (
                current_direction == "flat"
                or requested_direction == current_direction
                or i - agent_last_trade_i >= min_hold_bars
            )
            if verdict.allowed and hold_ok:
                agent_target = agent_value * target_fraction(judgment)
                agent_reason = f"{judgment.source}:{judgment.direction}"
            elif not verdict.allowed:
                agent_target = 0.0
                agent_reason = f"risk:{verdict.reason}"
            else:
                agent_target = agent.position * bar.close
                agent_reason = "churn_guard:min_hold"

            agent_trade = agent.target(
                bar,
                target_notional=agent_target,
                reason=agent_reason,
            )
            if agent_trade is not None:
                agent_last_trade_i = i

            baseline_state = build_state(
                bars[: i + 1],
                position=baseline_broker.position,
                unrealized_pnl=baseline_broker.unrealized(bar.close),
                drawdown=baseline_broker.drawdown(bar.close),
            )
            baseline_signal = baseline_direction(baseline_state)
            baseline_value = baseline_broker.equity(bar.close)
            baseline_verdict = risk.check(
                baseline_state,
                equity=baseline_value,
                daily_pnl=baseline_broker.realized - baseline_broker.fees,
                confidence=1.0,
                setup_quality=100.0,
            )
            baseline_requested = baseline_signal if baseline_verdict.allowed else "flat"
            baseline_current = _position_direction(baseline_broker.position)
            baseline_hold_ok = (
                baseline_current == "flat"
                or baseline_requested == baseline_current
                or i - baseline_last_trade_i >= min_hold_bars
            )
            if baseline_verdict.allowed and baseline_hold_ok:
                baseline_target = baseline_value * _baseline_fraction(baseline_signal)
                baseline_reason = f"baseline:{baseline_signal}"
            elif not baseline_verdict.allowed:
                baseline_target = 0.0
                baseline_reason = f"risk:{baseline_verdict.reason}"
            else:
                baseline_target = baseline_broker.position * bar.close
                baseline_reason = "churn_guard:min_hold"

            baseline_trade = baseline_broker.target(
                bar,
                target_notional=baseline_target,
                reason=baseline_reason,
            )
            if baseline_trade is not None:
                baseline_last_trade_i = i

            agent_value = agent.equity(bar.close)
            baseline_value = baseline_broker.equity(bar.close)
            agent_equity.append(agent_value)
            baseline_equity.append(baseline_value)

            record = {
                "ts": bar.ts,
                "price": bar.close,
                "state": state.to_state_dict(),
                "agent": {
                    "judgment": {
                        "regime": judgment.regime,
                        "direction": judgment.direction,
                        "setup_quality": judgment.setup_quality,
                        "confidence": judgment.confidence,
                        "source": judgment.source,
                        "latency_ms": judgment.latency_ms,
                    },
                    "risk": {"allowed": verdict.allowed, "reason": verdict.reason},
                    "trade": None
                    if agent_trade is None
                    else {
                        "side": agent_trade.side,
                        "price": agent_trade.price,
                        "quantity": agent_trade.quantity,
                        "fee": agent_trade.fee,
                    },
                    "equity": agent_value,
                },
                "baseline": {
                    "direction": baseline_signal,
                    "risk": {
                        "allowed": baseline_verdict.allowed,
                        "reason": baseline_verdict.reason,
                    },
                    "trade": None
                    if baseline_trade is None
                    else {
                        "side": baseline_trade.side,
                        "price": baseline_trade.price,
                        "quantity": baseline_trade.quantity,
                        "fee": baseline_trade.fee,
                    },
                    "equity": baseline_value,
                },
            }
            log_lines.append(json.dumps(record, separators=(",", ":")))

    _write_log(path, log_lines)

    return {
        "bars": len(bars),
        "costs": {
            "fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
            "min_trade_notional": min_trade_notional,
            "min_hold_bars": min_hold_bars,
        },
        "agent": {
            **as_dict(summarize(agent_equity, starting_cash=starting_cash)),
            "trades": len(agent.trades),
            "fees": round(agent.fees, 2),
        },
        "baseline": {
            **as_dict(summarize(baseline_equity, starting_cash=starting_cash)),
            "trades": len(baseline_broker.trades),
            "fees": round(baseline_broker.fees, 2),
        },
    }
