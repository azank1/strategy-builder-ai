"""TOTALES Module — Q1: What is the direction of the overall market?

Wraps the user's approved L2 TPI as a binary market gate.
RSPS is long-only: LONG means proceed, NOT-LONG means reduce exposure.
"""

from __future__ import annotations

from strategy_engine.models import LTPISystem
from strategy_engine.models_rsps import MiniTPI, TotalesState


class TotalesModule:
    """Determine overall market direction from a TPI."""

    def __init__(
        self,
        entry_threshold: float = 0.1,
        exit_threshold: float = -0.1,
    ):
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    def evaluate_from_ltpi(
        self,
        system: LTPISystem,
        entry_criteria: str = "",
        exit_criteria: str = "",
    ) -> TotalesState:
        """Evaluate market direction from an approved L2 TPI system."""
        ratio = system.trend_ratio
        is_long = ratio > self.entry_threshold
        return TotalesState(
            is_long=is_long,
            score=round(ratio, 4),
            entry_criteria=entry_criteria or f"Score > {self.entry_threshold}",
            exit_criteria=exit_criteria or f"Score < {self.exit_threshold}",
        )

    def evaluate_from_mini_tpi(
        self,
        tpi: MiniTPI,
        entry_criteria: str = "",
        exit_criteria: str = "",
    ) -> TotalesState:
        """Evaluate market direction from a mini-TPI on TOTALES."""
        avg = tpi.average_score
        is_long = avg > self.entry_threshold
        return TotalesState(
            is_long=is_long,
            score=round(avg, 4),
            entry_criteria=entry_criteria or f"Score > {self.entry_threshold}",
            exit_criteria=exit_criteria or f"Score < {self.exit_threshold}",
        )
