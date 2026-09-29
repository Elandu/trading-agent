from __future__ import annotations

import argparse
import asyncio
import json

from .market import fetch_binance_bars, synthetic_bars
from .runner import run_paper


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    paper = sub.add_parser("paper")
    paper.add_argument("--bars", type=int, default=500)
    paper.add_argument("--source", choices=("binance", "synthetic"), default="binance")
    paper.add_argument("--symbol", default="BTCUSDT")
    paper.add_argument("--jev", action="store_true")
    paper.add_argument("--log", default="data/experiments.jsonl")
    return parser


async def _paper(args: argparse.Namespace) -> None:
    if args.source == "binance":
        try:
            bars = fetch_binance_bars(args.symbol, "5m", args.bars)
        except Exception as exc:
            print(f"Binance fetch failed ({exc}); using deterministic synthetic bars.")
            bars = synthetic_bars(args.bars)
    else:
        bars = synthetic_bars(args.bars)
    summary = await run_paper(bars, use_jev=args.jev, log_path=args.log)
    print(json.dumps(summary, indent=2))


def main() -> None:
    args = _parser().parse_args()
    if args.command == "paper":
        asyncio.run(_paper(args))


if __name__ == "__main__":
    main()
