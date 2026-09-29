from __future__ import annotations

from .models import Bar, Trade


class PaperBroker:
    def __init__(
        self,
        *,
        starting_cash: float = 10_000.0,
        fee_bps: float = 10.0,
        slippage_bps: float = 2.0,
        min_trade_notional: float = 25.0,
    ) -> None:
        self.starting_cash = starting_cash
        self.position = 0.0
        self.avg_entry = 0.0
        self.fee_rate = fee_bps / 10_000.0
        self.slippage_rate = slippage_bps / 10_000.0
        self.min_trade_notional = min_trade_notional
        self.realized = 0.0
        self.fees = 0.0
        self.peak_equity = starting_cash
        self.trades: list[Trade] = []

    def unrealized(self, price: float) -> float:
        return (price - self.avg_entry) * self.position if self.position else 0.0

    def equity(self, price: float) -> float:
        return self.starting_cash + self.realized + self.unrealized(price) - self.fees

    def drawdown(self, price: float) -> float:
        equity = self.equity(price)
        self.peak_equity = max(self.peak_equity, equity)
        return 0.0 if self.peak_equity <= 0 else (self.peak_equity - equity) / self.peak_equity

    def target(self, bar: Bar, *, target_notional: float, reason: str) -> Trade | None:
        target_qty = target_notional / bar.close
        delta = target_qty - self.position
        reference_notional = abs(delta * bar.close)
        if reference_notional < self.min_trade_notional:
            return None

        side = "buy" if delta > 0 else "sell"
        fill_price = bar.close * (
            1.0 + self.slippage_rate if side == "buy" else 1.0 - self.slippage_rate
        )
        qty = abs(delta)
        fee = qty * fill_price * self.fee_rate
        old_position = self.position
        old_avg = self.avg_entry
        signed_delta = qty if side == "buy" else -qty
        new_position = old_position + signed_delta

        opposing = old_position != 0 and (old_position > 0) != (signed_delta > 0)
        closed = min(abs(signed_delta), abs(old_position)) if opposing else 0.0

        if closed:
            self.realized += (
                (fill_price - old_avg) * closed
                if old_position > 0
                else (old_avg - fill_price) * closed
            )

        if new_position == 0:
            self.avg_entry = 0.0
        elif old_position == 0 or (old_position > 0) != (new_position > 0):
            self.avg_entry = fill_price
        elif not opposing:
            self.avg_entry = (
                abs(old_position) * old_avg + abs(signed_delta) * fill_price
            ) / abs(new_position)

        self.position = new_position
        self.fees += fee
        trade = Trade(bar.ts, side, fill_price, qty, fee, reason)
        self.trades.append(trade)
        return trade
