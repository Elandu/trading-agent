from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .data import date_to_ms, fetch_binance_range, load_csv, save_csv
from .evaluate import evaluate_splits
from .market import fetch_binance_bars, synthetic_bars
from .runner import run_paper


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    paper = sub.add_parser("paper")
    paper.add_argument("--bars", type=int, default=500)
    paper.add_argument("--source", choices=("binance", "synthetic", "csv"), default="binance")
    paper.add_argument("--csv")
    paper.add_argument("--symbol", default="BTCUSDT")
    paper.add_argument("--jev", action="store_true")
    paper.add_argument("--log", default="data/experiments.jsonl")
    paper.add_argument("--fee-bps", type=float, default=10.0)
    paper.add_argument("--slippage-bps", type=float, default=2.0)

    download = sub.add_parser("download")
    download.add_argument("--symbol", default="BTCUSDT")
    download.add_argument("--interval", default="5m")
    download.add_argument("--start", required=True, help="YYYY-MM-DD")
    download.add_argument("--end", required=True, help="YYYY-MM-DD, exclusive")
    download.add_argument("--out", default="data/BTCUSDT-5m.csv")

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--csv", default="data/BTCUSDT-5m.csv")
    evaluate.add_argument("--jev", action="store_true")
    evaluate.add_argument("--out", default="data/evaluations")
    evaluate.add_argument("--fee-bps", type=float, default=10.0)
    evaluate.add_argument("--slippage-bps", type=float, default=2.0)
    return parser


def _bars_for_paper(args: argparse.Namespace):
    if args.source == "csv":
        if not args.csv:
            raise ValueError("--csv is required when --source csv")
        return load_csv(args.csv)
    if args.source == "binance":
        return fetch_binance_bars(args.symbol, "5m", args.bars)
    return synthetic_bars(args.bars)


async def _paper(args: argparse.Namespace) -> None:
    bars = _bars_for_paper(args)
    summary = await run_paper(
        bars,
        use_jev=args.jev,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        log_path=args.log,
    )
    print(json.dumps(summary, indent=2))


def _download(args: argparse.Namespace) -> None:
    bars = fetch_binance_range(
        symbol=args.symbol,
        interval=args.interval,
        start_ms=date_to_ms(args.start),
        end_ms=date_to_ms(args.end),
    )
    target = save_csv(args.out, bars)
    print(json.dumps({"bars": len(bars), "path": str(target)}, indent=2))


async def _evaluate(args: argparse.Namespace) -> None:
    bars = load_csv(Path(args.csv))
    results = await evaluate_splits(
        bars,
        use_jev=args.jev,
        output_dir=args.out,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    print(
        json.dumps(
            {
                item.split: {
                    "bars": item.bars,
                    "agent": item.summary["agent"],
                    "baseline": item.summary["baseline"],
                }
                for item in results
            },
            indent=2,
        )
    )


def main() -> None:
    args = _parser().parse_args()
    if args.command == "paper":
        asyncio.run(_paper(args))
    elif args.command == "download":
        _download(args)
    elif args.command == "evaluate":
        asyncio.run(_evaluate(args))


if __name__ == "__main__":
    main()
