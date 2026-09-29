from __future__ import annotations

from .models import Bar, Trade


class PaperBroker:
    def __init__(self, *, starting_cash: float = 10_000.0, fee_bps: float = 6.0) -> None:
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.position = 0.0
        self.avg_entry = 0.0
        self.fee_rate = fee_bps / 10_000.0
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
        if abs(delta * bar.close) < 1.0:
            return None
        side = "buy" if delta > 0 else "sell"
        qty = abs(delta)
        fee = qty * bar.close * self.fee_rate
        old_position = self.position
        old_avg = self.avg_entry
        new_position = old_position + (qty if side == "buy" else -qty)

        if old_position and (old_position > 0) != (new_position > 0) and new_position != 0:
            closed = abs(old_position)
        elif old_position and (old_position > 0) != (delta > 0):
            closed = min(abs(delta), abs(old_position))
        else:
            closed = 0.0

        if closed:
            self.realized += (
                (bar.close - old_avg) * closed
                if old_position > 0
                else (old_avg - bar.close) * closed
            )

        if new_position == 0:
            self.avg_entry = 0.0
        elif old_position == 0 or (old_position > 0) != (new_position > 0):
            self.avg_entry = bar.close
        elif (old_position > 0) == (delta > 0):
            self.avg_entry = (
                abs(old_position) * old_avg + abs(delta) * bar.close
            ) / abs(new_position)

        self.position = new_position
        self.fees += fee
        trade = Trade(bar.ts, side, bar.close, qty, fee, reason)
        self.trades.append(trade)
        return trade
