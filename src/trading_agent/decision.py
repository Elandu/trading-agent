from __future__ import annotations

import os
import time

from typesafe_sdk import AsyncTypeSafeClient, Choice, Score

from .models import Judgment, MarketState


class FallbackJudge:
    async def judge(self, state: MarketState) -> Judgment:
        trend = 0.65 * state.ema_fast_gap + 0.35 * state.ret_3
        if state.atr_pct > 0.025:
            regime = "high_vol"
        elif abs(state.ema_slow_gap) > 0.01:
            regime = "trending"
        else:
            regime = "ranging"

        if trend > 0.0015 and state.rsi_14 < 78:
            direction = "long"
        elif trend < -0.0015 and state.rsi_14 > 22:
            direction = "short"
        else:
            direction = "flat"

        quality = min(
            100.0,
            abs(trend) * 15_000
            + max(0.0, state.volume_ratio - 1.0) * 15
            + abs(state.rsi_14 - 50.0) * 0.4,
        )
        confidence = min(0.85, 0.45 + quality / 250.0)
        return Judgment(regime, direction, quality, confidence, source="fallback")


class JevJudge:
    def __init__(self, model: str | None = None) -> None:
        if not os.getenv("TYPESAFE_API_KEY"):
            raise ValueError("TYPESAFE_API_KEY is required for live Jev mode")
        self.model = model or os.getenv("JEV_MODEL", "jev-latest")
        self._client: AsyncTypeSafeClient | None = None
        self._questions = {
            "regime": Choice(
                instructions="Classify the current 5 minute BTC/USDT market regime.",
                criteria={"trending": None, "ranging": None, "high_vol": None},
            ),
            "direction": Choice(
                instructions="What is the directional bias over the next few 5 minute bars?",
                criteria={"long": None, "short": None, "flat": None},
            ),
            "setup_quality": Score(
                instructions="How strong and tradeable is this setup?",
                criteria=[
                    "No edge",
                    "Weak",
                    "Moderate",
                    "Strong",
                    "Exceptional",
                ],
            ),
        }

    async def __aenter__(self) -> "JevJudge":
        self._client = AsyncTypeSafeClient(model=self.model)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    async def judge(self, state: MarketState) -> Judgment:
        if not self._client:
            raise RuntimeError("JevJudge must be used as an async context manager")
        started = time.perf_counter()
        response = await self._client.system_one(
            state=state.to_state_dict(),
            questions=self._questions,
        )
        latency = (time.perf_counter() - started) * 1000.0
        regime = response.choices["regime"]
        direction = response.choices["direction"]
        quality = response.scores["setup_quality"]
        confidence = min(regime.confidence, direction.confidence, quality.confidence)
        return Judgment(
            regime=regime.choice,
            direction=direction.choice,
            setup_quality=float(quality.score) * 25.0,
            confidence=float(confidence),
            source="jev",
            latency_ms=latency,
        )
