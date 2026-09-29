# Trading Agent Plan

## Research question

Can bounded Jev judgments improve a simple BTC/USDT 5-minute strategy after fees and risk controls, compared with a deterministic baseline?

## Token budget rule

Premium reasoning models are **not** part of the per-bar trading loop.

- Jev: bounded structured decisions only.
- Deterministic Python: indicators, state, sizing, risk, execution and metrics.
- Opus/Sol-class model: periodic experiment review only, after a meaningful batch of results.
- No new agent framework, UI or exchange integration until the current phase passes its acceptance test.

## Phase 0 — Runnable harness

- [x] BTC/USDT 5m bar model
- [x] public Binance historical bar fetch with offline synthetic fallback
- [x] deterministic feature/state builder
- [x] simple EMA/momentum baseline
- [x] deterministic fallback judge
- [x] optional Jev structured judge
- [x] hard risk veto layer
- [x] paper broker with fees and PnL
- [x] JSONL experiment log
- [x] smoke tests

Acceptance: `uv run trading-agent paper --source synthetic --bars 500` completes without an API key.

## Phase 1 — Establish baselines

Run the same data through:

1. flat/no-trade control
2. deterministic EMA/momentum baseline
3. fallback judge
4. Jev judge

Metrics:

- net return after fees
- max drawdown
- trade count / turnover
- hit rate
- profit factor
- Sharpe / Sortino
- average trade
- exposure
- Jev cost per 1,000 bars

Acceptance: baseline report saved under `data/` and reproducible from a fixed data sample.

## Phase 2 — Real historical evaluation

- Persist a fixed BTC/USDT 5m dataset.
- Add train / validation / walk-forward splits.
- Never tune thresholds on the final test period.
- Model slippage in addition to fees.
- Compare Jev with the deterministic baseline on identical bars.

Acceptance: Jev adds measurable out-of-sample value or the experiment stops.

## Phase 3 — Strategy-review agent

Only after Phase 2.

A slower reasoning model may review batches of logs and propose:

- feature additions/removals
- threshold changes
- new bounded Jev questions
- hypotheses for the next experiment

Every proposal must be represented as a versioned config/code change and re-run through the same walk-forward harness.

The reviewer never places trades.

## Phase 4 — Testnet

Only if Phase 2 shows an edge after realistic costs.

- exchange adapter
- websocket data
- order reconciliation
- kill switch
- testnet only

## Explicit non-goals for now

- live money
- HFT / sub-second execution
- multi-agent swarms
- reinforcement learning
- custom dashboards
- multiple exchanges
- multiple assets
- news/social sentiment
- autonomous self-modifying production code
