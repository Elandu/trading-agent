from __future__ import annotations

from trading_agent.data import chronological_split, load_csv, save_csv, slice_with_warmup
from trading_agent.market import synthetic_bars


def test_csv_round_trip(tmp_path) -> None:
    bars = synthetic_bars(50, seed=11)
    path = save_csv(tmp_path / "bars.csv", bars)
    loaded = load_csv(path)
    assert loaded == bars


def test_split_is_chronological() -> None:
    bars = synthetic_bars(100, seed=12)
    split = chronological_split(bars)
    assert len(split.train) == 60
    assert len(split.validation) == 20
    assert len(split.test) == 20
    assert split.train[-1].ts < split.validation[0].ts < split.test[0].ts


def test_warmup_prefix() -> None:
    bars = synthetic_bars(200, seed=13)
    split = chronological_split(bars)
    warmed = slice_with_warmup(bars, split.test, warmup_bars=30)
    assert len(warmed) == len(split.test) + 30
    assert warmed[-len(split.test) :] == split.test
