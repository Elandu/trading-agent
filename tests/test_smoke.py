from __future__ import annotations

import asyncio

from trading_agent.market import build_state, synthetic_bars
from trading_agent.runner import run_paper
from trading_agent.strategy import baseline_direction


def test_state_and_baseline() -> None:
    bars = synthetic_bars(80, seed=1)
    state = build_state(bars, position=0.0, unrealized_pnl=0.0, drawdown=0.0)
    assert state.close > 0
    assert 0 <= state.rsi_14 <= 100
    assert baseline_direction(state) in {"long", "short", "flat"}


def test_paper_loop_offline(tmp_path) -> None:
    bars = synthetic_bars(100, seed=2)
    summary = asyncio.run(
        run_paper(bars, log_path=str(tmp_path / "experiment.jsonl"))
    )
    assert summary["bars"] == 100
    assert summary["agent"]["ending_equity"] > 0
    assert summary["baseline"]["ending_equity"] > 0
    assert "sharpe" in summary["agent"]
    assert "sharpe" in summary["baseline"]
