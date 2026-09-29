from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .models import Bar

BINANCE_SPOT_KLINES = "https://api.binance.com/api/v3/klines"
INTERVAL_MS = {"5m": 5 * 60 * 1000}


@dataclass(frozen=True, slots=True)
class DataSplit:
    train: list[Bar]
    validation: list[Bar]
    test: list[Bar]


def date_to_ms(value: str) -> int:
    dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def fetch_binance_range(
    *,
    symbol: str = "BTCUSDT",
    interval: str = "5m",
    start_ms: int,
    end_ms: int,
    request_limit: int = 1000,
    pause_s: float = 0.05,
) -> list[Bar]:
    """Download a fixed public Binance spot kline range, oldest to newest."""
    if interval not in INTERVAL_MS:
        raise ValueError(f"unsupported interval: {interval}")
    if end_ms <= start_ms:
        raise ValueError("end_ms must be greater than start_ms")

    step_ms = INTERVAL_MS[interval]
    cursor = start_ms
    bars: list[Bar] = []

    while cursor < end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol.upper(),
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": min(max(request_limit, 1), 1000),
            }
        )
        req = urllib.request.Request(
            f"{BINANCE_SPOT_KLINES}?{params}",
            headers={"User-Agent": "trading-agent/0.1"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            rows = json.load(response)
        if not rows:
            break

        for row in rows:
            ts = int(row[0])
            if ts >= end_ms:
                break
            bars.append(
                Bar(
                    ts=ts,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )

        last_ts = int(rows[-1][0])
        next_cursor = last_ts + step_ms
        if next_cursor <= cursor:
            raise RuntimeError("Binance pagination did not advance")
        cursor = next_cursor
        if len(rows) < request_limit:
            break
        if pause_s:
            time.sleep(pause_s)

    unique = {bar.ts: bar for bar in bars}
    return [unique[ts] for ts in sorted(unique)]


def save_csv(path: str | Path, bars: list[Bar]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ts", "open", "high", "low", "close", "volume"))
        for bar in bars:
            writer.writerow((bar.ts, bar.open, bar.high, bar.low, bar.close, bar.volume))
    return target


def load_csv(path: str | Path) -> list[Bar]:
    source = Path(path)
    with source.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        bars = [
            Bar(
                ts=int(row["ts"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for row in reader
        ]
    bars.sort(key=lambda bar: bar.ts)
    return bars


def chronological_split(
    bars: list[Bar],
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
) -> DataSplit:
    if not bars:
        raise ValueError("bars cannot be empty")
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train + validation fractions must be less than 1")

    train_end = int(len(bars) * train_fraction)
    validation_end = int(len(bars) * (train_fraction + validation_fraction))
    return DataSplit(
        train=bars[:train_end],
        validation=bars[train_end:validation_end],
        test=bars[validation_end:],
    )


def slice_with_warmup(
    all_bars: list[Bar],
    selected: list[Bar],
    *,
    warmup_bars: int = 120,
) -> list[Bar]:
    if not selected:
        return []
    first_ts = selected[0].ts
    first_index = next(i for i, bar in enumerate(all_bars) if bar.ts == first_ts)
    start = max(0, first_index - warmup_bars)
    return all_bars[start : first_index + len(selected)]
