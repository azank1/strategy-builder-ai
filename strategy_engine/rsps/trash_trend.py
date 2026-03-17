"""Trash Trend Module — Q3: How much goes to altcoins?

Uses OTHERS.D (alt dominance) mini-TPI with 0/1 scoring.
Strength = average score (0.0 to 1.0).
Allocation = max_trash_pct × strength.
"""

from __future__ import annotations

from strategy_engine.models_rsps import MiniTPI, RSPSConfig, TrashTrendResult


class TrashTrendModule:
    """Determine altcoin allocation percentage from dominance trend."""

    def __init__(self, config: RSPSConfig):
        self.config = config

    def evaluate(self, others_tpi: MiniTPI) -> TrashTrendResult:
        """Evaluate trash allocation from OTHERS.D mini-TPI.

        Scoring: 0/1 per indicator (NOT ±1).
        Strength: average of effective scores.
        Allocation: max_trash_pct × strength.
        """
        if not others_tpi.indicators:
            return TrashTrendResult(
                strength=0.0,
                allocation_pct=0.0,
                indicator_count=0,
            )

        strength = others_tpi.average_score
        # Clamp to [0, 1] since we use 0/1 scoring
        strength = max(0.0, min(1.0, strength))

        allocation_pct = round(self.config.max_trash_pct * strength, 4)

        return TrashTrendResult(
            strength=round(strength, 4),
            allocation_pct=allocation_pct,
            indicator_count=len(others_tpi.indicators),
        )
