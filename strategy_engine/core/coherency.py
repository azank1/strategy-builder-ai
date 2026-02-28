"""
Time Coherency Analyzer — measure signal alignment across indicators.

Evaluates whether a set of binary (+1/-1) indicators produce constructive,
destructive, or mixed interference relative to an Intended Signal Period.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class CoherencyReport:
    """Results of time coherency analysis."""

    agreement_ratio: float  # 0.0 to 1.0 — what % of time all indicators agree
    constructive_ratio: float  # % of periods with >80% agreement
    destructive_ratio: float  # % of periods with <20% agreement
    mixed_ratio: float  # % of periods in between
    per_indicator_alignment: dict[str, float]  # name → alignment % with consensus
    avg_pairwise_correlation: float  # mean pairwise correlation across indicators
    is_coherent: bool  # True if constructive_ratio > 0.6

    @property
    def summary(self) -> str:
        if self.is_coherent:
            return (
                f"Coherent system: {self.agreement_ratio:.1%} agreement, "
                f"{self.constructive_ratio:.1%} constructive"
            )
        return (
            f"Incoherent system: {self.agreement_ratio:.1%} agreement, "
            f"{self.destructive_ratio:.1%} destructive, "
            f"{self.mixed_ratio:.1%} mixed"
        )


class CoherencyAnalyzer:
    """
    Analyze time coherency across a set of binary signal indicators.

    Time coherency is THE critical concept for TPI systems (Level 2 LTPI).
    All indicators should go long together and short together — this is
    constructive interference. Destructive or mixed interference invalidates
    the system.

    Example:
        >>> analyzer = CoherencyAnalyzer()
        >>> signals = pd.DataFrame({
        ...     "ind_a": [1, 1, -1, -1, 1],
        ...     "ind_b": [1, 1, -1, -1, 1],
        ...     "ind_c": [1, -1, -1, -1, 1],
        ... })
        >>> report = analyzer.analyze(signals)
        >>> report.is_coherent
        True
    """

    def __init__(
        self,
        constructive_threshold: float = 0.8,
        destructive_threshold: float = 0.2,
        coherency_min: float = 0.6,
    ):
        """
        Args:
            constructive_threshold: Min agreement ratio for a period to count as constructive.
            destructive_threshold: Max agreement ratio for a period to count as destructive.
            coherency_min: Min constructive_ratio for the system to be considered coherent.
        """
        self.constructive_threshold = constructive_threshold
        self.destructive_threshold = destructive_threshold
        self.coherency_min = coherency_min

    def analyze(
        self,
        signals: pd.DataFrame,
        isp_direction: Optional[pd.Series] = None,
    ) -> CoherencyReport:
        """
        Analyze coherency across indicator signals.

        Args:
            signals: DataFrame where each column is an indicator with values +1, -1, or 0.
                     Index should be dates/timestamps.
            isp_direction: Optional Series of intended directions (+1/-1) to compare against.

        Returns:
            CoherencyReport with detailed coherency metrics.
        """
        if signals.empty or signals.shape[1] < 2:
            return CoherencyReport(
                agreement_ratio=1.0,
                constructive_ratio=1.0,
                destructive_ratio=0.0,
                mixed_ratio=0.0,
                per_indicator_alignment={},
                avg_pairwise_correlation=1.0,
                is_coherent=True,
            )

        n_indicators = signals.shape[1]

        # Calculate consensus direction at each time point
        row_sums = signals.sum(axis=1)
        consensus = np.sign(row_sums)

        # Agreement: what fraction of indicators agree with consensus at each point
        agreement_per_row = []
        for _, row in signals.iterrows():
            nonzero = row[row != 0]
            if len(nonzero) == 0:
                agreement_per_row.append(0.5)
                continue
            majority_direction = 1 if nonzero.sum() >= 0 else -1
            agree_count = (nonzero == majority_direction).sum()
            agreement_per_row.append(agree_count / len(nonzero))

        agreement_series = pd.Series(agreement_per_row, index=signals.index)
        overall_agreement = float(agreement_series.mean())

        # Classify periods
        constructive = float((agreement_series >= self.constructive_threshold).mean())
        destructive = float((agreement_series <= self.destructive_threshold).mean())
        mixed = 1.0 - constructive - destructive

        # Per-indicator alignment with consensus
        per_indicator: dict[str, float] = {}
        for col in signals.columns:
            indicator = signals[col]
            nonzero_mask = indicator != 0
            if nonzero_mask.sum() == 0:
                per_indicator[col] = 0.0
                continue
            matches = (indicator[nonzero_mask] == consensus[nonzero_mask]).sum()
            per_indicator[col] = float(matches / nonzero_mask.sum())

        # Average pairwise correlation
        corr_matrix = signals.corr()
        n = len(corr_matrix)
        if n > 1:
            # Extract upper triangle (excluding diagonal)
            mask = np.triu(np.ones((n, n), dtype=bool), k=1)
            pairwise = corr_matrix.values[mask]
            avg_corr = float(np.nanmean(pairwise))
        else:
            avg_corr = 1.0

        return CoherencyReport(
            agreement_ratio=round(overall_agreement, 4),
            constructive_ratio=round(constructive, 4),
            destructive_ratio=round(destructive, 4),
            mixed_ratio=round(mixed, 4),
            per_indicator_alignment={k: round(v, 4) for k, v in per_indicator.items()},
            avg_pairwise_correlation=round(avg_corr, 4),
            is_coherent=constructive >= self.coherency_min,
        )

    def find_outlier_indicators(
        self, signals: pd.DataFrame, threshold: float = 0.5
    ) -> list[str]:
        """
        Find indicators that are poorly aligned with the consensus.

        Args:
            signals: DataFrame of binary signals.
            threshold: Indicators with alignment below this are flagged.

        Returns:
            List of indicator names that are poorly aligned.
        """
        report = self.analyze(signals)
        return [
            name
            for name, alignment in report.per_indicator_alignment.items()
            if alignment < threshold
        ]
