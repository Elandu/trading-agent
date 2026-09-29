# Trading Agent Plan

## Research question

Can bounded Jev judgments improve a simple BTC/USDT 5-minute strategy after realistic costs and deterministic risk controls?

## Token budget rule

Premium reasoning models are not part of the per-bar trading loop.

- Jev: bounded structured decisions only.
- Deterministic Python: data, indicators, state, sizing, risk, execution and metrics.
- Slow reasoning model: periodic experiment review only.
- No new agent framework, UI or exchange integration until the current phase passes.

## Phase 0 — Runnable harness

- [x] BTC/USDT 5m bar model
- [x] deterministic state builder
- [x] EMA/momentum baseline
- [x] deterministic fallback judge
- [x] optional Jev judge
- [x] hard risk vetoes
- [x] paper broker
- [x] CI smoke run

## Phase 1 — Fixed historical baseline

- [x] exact-date Binance public data downloader
- [x] CSV persistence
- [x] 60/20/20 chronological train-validation-test split
- [x] warm-up history without leaking future bars
- [x] configurable fees
- [x] adverse slippage
- [x] minimum trade notional
- [x] minimum-hold churn guard
- [x] agent-vs-baseline metrics on identical bars
- [x] split reports saved to disk

Next acceptance run:

```
BTCUSDT 5m, one fixed 12-month sample
train 60%
validation 20%
test 20%
```

The final test segment is not used for threshold tuning.

## Phase 2 — Jev comparison

Only after the historical non-Jev runs are sane.

Run:

1. deterministic baseline
2. fallback judge
3. Jev judge

Measure:

- net return after fees/slippage
- max drawdown
- trade count / turnover
- profit factor
- Sharpe / Sortino
- model latency
- Jev cost per 1,000 decisions

Acceptance: Jev must add out-of-sample value relative to both deterministic references. Otherwise stop.

## Phase 3 — Strategy-review agent

Only after Phase 2.

A slower reasoning model may review batches of experiment logs and propose versioned hypotheses. Every proposal must go back through the same historical harness.

The reviewer never places trades.

## Phase 4 — Testnet

Only if Phase 2 shows an edge after realistic costs.

- exchange adapter
- websocket data
- order reconciliation
- kill switch
- testnet only

## Explicit non-goals

- live money
- HFT
- multi-agent swarms
- reinforcement learning
- custom dashboard
- multiple exchanges
- multiple assets
- social/news sentiment
- autonomous self-modifying production code
