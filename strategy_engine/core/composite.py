"""
Composite Scorer — aggregate signals from SDCA and LTPI into unified outputs.

Handles:
- SDCA z-score aggregation (weighted/unweighted)
- LTPI binary score aggregation
- SDCA × LTPI combined signal matrix
- Multi-asset portfolio allocation suggestions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from strategy_engine.models import (
    AssetClass,
    CombinedSignal,
    LTPISystem,
    SDCASystem,
    SignalStrength,
)


@dataclass
class SDCAComposite:
    """Aggregated SDCA valuation result."""

    asset: AssetClass
    composite_z: float
    by_category: dict[str, float]
    indicator_count: int
    interpretation: str

    @staticmethod
    def interpret_z(z: float) -> str:
        if z <= -2.0:
            return "Extremely oversold — strong buy zone"
        if z <= -1.0:
            return "Oversold — accumulation zone"
        if z <= 1.0:
            return "Fair value — normal DCA"
        if z <= 2.0:
            return "Overbought — reduce / take profit"
        return "Extremely overbought — strong sell zone"


@dataclass
class LTPIComposite:
    """Aggregated LTPI trend result."""

    asset: AssetClass
    composite_score: int
    max_possible: int
    trend_ratio: float
    interpretation: str

    @staticmethod
    def interpret_ratio(ratio: float) -> str:
        if ratio > 0.6:
            return "Strong uptrend"
        if ratio > 0.2:
            return "Moderate uptrend"
        if ratio > -0.2:
            return "Neutral — no clear trend"
        if ratio > -0.6:
            return "Moderate downtrend"
        return "Strong downtrend"


@dataclass
class AllocationSuggestion:
    """Suggested allocation for a single asset."""

    asset: AssetClass
    signal: SignalStrength
    allocation_pct: float  # 0.0 to 1.0 — suggested % of available capital
    reasoning: str


@dataclass
class PortfolioSignal:
    """Combined signal across all tracked assets."""

    assets: list[AllocationSuggestion] = field(default_factory=list)
    total_risk_score: float = 0.0  # -1.0 (max risk-off) to 1.0 (max risk-on)

    @property
    def summary(self) -> dict[str, float]:
        return {a.asset.value: a.allocation_pct for a in self.assets}


class CompositeScorer:
    """
    Compute composite scores and generate portfolio signals.

    Supports weighted aggregation for SDCA and configurable
    allocation logic for the combined SDCA × LTPI matrix.
    """

    def __init__(
        self,
        sdca_weights: Optional[dict[str, float]] = None,
    ):
        """
        Args:
            sdca_weights: Optional per-category weights for SDCA.
                          e.g., {"fundamental": 0.4, "technical": 0.35, "sentiment": 0.25}
                          If None, equal weighting is used.
        """
        self.sdca_weights = sdca_weights

    def score_sdca(self, system: SDCASystem) -> SDCAComposite:
        """Compute the SDCA composite valuation score."""
        if not system.indicators:
            return SDCAComposite(
                asset=system.asset,
                composite_z=0.0,
                by_category={},
                indicator_count=0,
                interpretation="No indicators",
            )

        by_cat = system.result_by_category

        if self.sdca_weights:
            # Weighted composite
            total_weight = 0.0
            weighted_sum = 0.0
            for cat, avg_z in by_cat.items():
                w = self.sdca_weights.get(cat, 1.0)
                weighted_sum += avg_z * w
                total_weight += w
            composite = weighted_sum / total_weight if total_weight > 0 else 0.0
        else:
            # Equal-weight: simple average of all z-scores
            composite = system.composite_z_score

        return SDCAComposite(
            asset=system.asset,
            composite_z=round(composite, 4),
            by_category={k: round(v, 4) for k, v in by_cat.items()},
            indicator_count=len(system.indicators),
            interpretation=SDCAComposite.interpret_z(composite),
        )

    def score_ltpi(self, system: LTPISystem) -> LTPIComposite:
        """Compute the LTPI composite trend score."""
        return LTPIComposite(
            asset=system.asset,
            composite_score=system.composite_score,
            max_possible=system.max_possible,
            trend_ratio=round(system.trend_ratio, 4),
            interpretation=LTPIComposite.interpret_ratio(system.trend_ratio),
        )

    def combined_signal(self, sdca: SDCASystem, ltpi: LTPISystem) -> CombinedSignal:
        """Generate the unified SDCA × LTPI signal for an asset."""
        return CombinedSignal.from_systems(sdca, ltpi)

    def portfolio_signal(
        self,
        systems: list[tuple[SDCASystem, LTPISystem]],
    ) -> PortfolioSignal:
        """
        Generate portfolio-wide allocation suggestions across multiple assets.

        Args:
            systems: List of (SDCA, LTPI) pairs, one per asset.

        Returns:
            PortfolioSignal with per-asset allocation suggestions.
        """
        suggestions: list[AllocationSuggestion] = []
        risk_scores: list[float] = []

        for sdca, ltpi in systems:
            signal = self.combined_signal(sdca, ltpi)
            alloc, reasoning, risk = self._signal_to_allocation(signal)
            suggestions.append(AllocationSuggestion(
                asset=signal.asset,
                signal=signal.signal,
                allocation_pct=alloc,
                reasoning=reasoning,
            ))
            risk_scores.append(risk)

        # Normalize allocations to sum to 1.0
        total = sum(s.allocation_pct for s in suggestions)
        if total > 0:
            for s in suggestions:
                s.allocation_pct = round(s.allocation_pct / total, 4)

        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

        return PortfolioSignal(
            assets=suggestions,
            total_risk_score=round(avg_risk, 4),
        )

    @staticmethod
    def _signal_to_allocation(
        signal: CombinedSignal,
    ) -> tuple[float, str, float]:
        """
        Map a combined signal to an allocation weight, reasoning, and risk score.

        Returns:
            (allocation_weight, reasoning_text, risk_score)
        """
        mapping: dict[SignalStrength, tuple[float, str, float]] = {
            SignalStrength.STRONGEST_BUY: (
                1.0,
                "Undervalued + uptrend — maximum accumulation",
                0.9,
            ),
            SignalStrength.CAUTIOUS_BUY: (
                0.5,
                "Undervalued but downtrend — small DCA, wait for trend confirmation",
                0.3,
            ),
            SignalStrength.LIGHT_BUY: (
                0.6,
                "Fair value with positive momentum — standard DCA",
                0.5,
            ),
            SignalStrength.HOLD: (
                0.3,
                "Neutral conditions — maintain current position",
                0.0,
            ),
            SignalStrength.REDUCE: (
                0.15,
                "Fading momentum or fair value declining — pause DCA",
                -0.3,
            ),
            SignalStrength.PARTIAL_PROFIT: (
                0.1,
                "Overvalued but momentum continues — scale out slowly",
                -0.5,
            ),
            SignalStrength.STRONGEST_SELL: (
                0.0,
                "Overvalued + downtrend — aggressive de-risk",
                -0.9,
            ),
        }

        alloc, reason, risk = mapping.get(
            signal.signal,
            (0.3, "Unknown signal state", 0.0),
        )
        return alloc, reason, risk
