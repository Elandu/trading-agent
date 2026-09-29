from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from .data import DataSplit, chronological_split, slice_with_warmup
from .models import Bar
from .runner import run_paper


@dataclass(frozen=True, slots=True)
class Evaluation:
    split: str
    first_ts: int
    last_ts: int
    bars: int
    summary: dict[str, object]


async def evaluate_splits(
    bars: list[Bar],
    *,
    use_jev: bool = False,
    output_dir: str = "data/evaluations",
    fee_bps: float = 10.0,
    slippage_bps: float = 2.0,
) -> list[Evaluation]:
    split: DataSplit = chronological_split(bars)
    groups = (
        ("train", split.train),
        ("validation", split.validation),
        ("test", split.test),
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    evaluations: list[Evaluation] = []

    for name, selected in groups:
        warmed = slice_with_warmup(bars, selected)
        warmup_bars = len(warmed) - len(selected)
        summary = await run_paper(
            warmed,
            use_jev=use_jev,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            warmup_bars=warmup_bars,
            log_path=str(output / f"{name}.jsonl"),
        )
        evaluations.append(
            Evaluation(
                split=name,
                first_ts=selected[0].ts,
                last_ts=selected[-1].ts,
                bars=len(selected),
                summary=summary,
            )
        )

    report = {
        item.split: {
            "first_ts": item.first_ts,
            "last_ts": item.last_ts,
            "bars": item.bars,
            "summary": item.summary,
        }
        for item in evaluations
    }
    (output / "summary.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    return evaluations


def evaluate_sync(*args, **kwargs) -> list[Evaluation]:
    return asyncio.run(evaluate_splits(*args, **kwargs))
