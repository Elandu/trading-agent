from __future__ import annotations

from trading_agent.execution import PaperBroker
from trading_agent.models import Bar


def test_slippage_moves_fill_against_trader() -> None:
    broker = PaperBroker(slippage_bps=10.0, fee_bps=0.0, min_trade_notional=1.0)
    bar = Bar(ts=1, open=100, high=101, low=99, close=100, volume=10)
    trade = broker.target(bar, target_notional=1000.0, reason="test")
    assert trade is not None
    assert trade.price > bar.close


def test_min_notional_suppresses_churn() -> None:
    broker = PaperBroker(min_trade_notional=100.0)
    bar = Bar(ts=1, open=100, high=101, low=99, close=100, volume=10)
    assert broker.target(bar, target_notional=50.0, reason="tiny") is None
