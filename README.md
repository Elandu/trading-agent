# trading-agent

A deliberately small paper-trading research harness for testing whether Jev-style structured judgments add value over simple deterministic baselines.

## v0 scope

- BTC/USDT only
- 5 minute bars
- paper trading only
- deterministic risk engine always has final authority
- Jev is used for bounded judgments, not order sizing or risk limits
- every Jev run is compared with a baseline strategy

## Architecture

```
market bars
   -> deterministic features/state
   -> baseline signal
   -> Jev/fallback judgment
   -> policy
   -> hard risk veto
   -> paper execution
   -> experiment log
```

The architecture is adapted from the companion `Elandu/jev-trader` fork, especially its separation of deterministic state, model judgment, hard risk and paper execution. Market-making/HFT-specific pricing and policy were intentionally not copied into this repo.

## First milestone

One reproducible loop:

```
BTC/USDT 5m data -> state -> judgment -> risk check -> simulated trade -> JSONL log
```

The system must run without an API key in deterministic fallback mode.

## Quickstart

```bash
uv sync
uv run trading-agent paper --bars 1000
```

With Jev later:

```bash
export TYPESAFE_API_KEY="..."
uv run trading-agent paper --bars 1000 --jev
```

## Guardrails

This repository is for research and paper trading. Live execution is intentionally out of scope for v0.
