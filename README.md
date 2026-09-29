# trading-agent

A deliberately small paper-trading research harness for testing whether Jev-style structured judgments add value over deterministic baselines.

## Scope

- BTC/USDT
- 5-minute bars
- paper trading only
- deterministic risk engine always has final authority
- Jev is used only for bounded judgments
- every Jev run is compared against a deterministic baseline on identical data

## Data

Historical data is free. The preferred source is Binance public Spot klines / Data Vision. The repo downloads an exact date range once and persists it as CSV so all later experiments are reproducible.

Example: download one year of BTC/USDT 5-minute bars:

```bash
uv sync
uv run trading-agent download \
  --symbol BTCUSDT \
  --interval 5m \
  --start 2025-09-01 \
  --end 2026-09-01 \
  --out data/BTCUSDT-5m-2025-09_2026-09.csv
```

Then evaluate chronological 60% / 20% / 20% train-validation-test splits:

```bash
uv run trading-agent evaluate \
  --csv data/BTCUSDT-5m-2025-09_2026-09.csv
```

Outputs are written under `data/evaluations/`.

## Cost model

Paper fills include configurable fees and adverse slippage. Defaults are intentionally conservative for early research:

- fee: 10 bps
- slippage: 2 bps per fill
- minimum trade notional: $25
- minimum hold before reversing: 3 bars

These are assumptions, not claims about any particular account's actual trading costs.

## Architecture

```
fixed historical bars
   -> deterministic features/state
   -> baseline signal
   -> Jev/fallback judgment
   -> hard risk veto
   -> churn guard
   -> paper execution + costs
   -> train/validation/test report
```

## Offline smoke run

```bash
uv run trading-agent paper --source synthetic --bars 500
```

## Jev

Do not spend Jev calls until the deterministic historical harness is behaving sensibly.

Later:

```bash
export TYPESAFE_API_KEY="..."
uv run trading-agent evaluate --csv data/BTCUSDT-5m.csv --jev
```

## Guardrails

Research and paper trading only. No live-money execution is included.
