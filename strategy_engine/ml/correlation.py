"""
Correlation Analyzer — detect redundancy between indicators.

Critical for both SDCA and LTPI: indicators measuring the same underlying
signal add noise, not information. This module identifies and flags
highly correlated indicator pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class RedundancyPair:
    """A pair of indicators that are potentially redundant."""

    indicator_a: str
    indicator_b: str
    correlation: float
    recommendation: str


@dataclass
class CorrelationReport:
    """Results from correlation/redundancy analysis."""

    correlation_matrix: pd.DataFrame
    redundant_pairs: list[RedundancyPair] = field(default_factory=list)
    cluster_assignments: dict[str, int] = field(default_factory=dict)
    effective_n: float = 0.0  # Effective number of independent indicators

    @property
    def redundancy_ratio(self) -> float:
        """Fraction of pairs that are redundant."""
        total = len(self.correlation_matrix)
        if total <= 1:
            return 0.0
        total_pairs = total * (total - 1) / 2
        return len(self.redundant_pairs) / total_pairs if total_pairs > 0 else 0.0


class CorrelationAnalyzer:
    """
    Analyze indicator correlations and detect redundancy.

    Flags pairs above a threshold and computes effective degrees of freedom
    to understand the true information content of an indicator set.

    Example:
        >>> analyzer = CorrelationAnalyzer()
        >>> indicators = pd.DataFrame({
        ...     "mayer": [1.2, 0.8, 1.1, 0.9],
        ...     "200dma_ratio": [1.15, 0.82, 1.08, 0.91],
        ...     "nvt": [45, 80, 50, 70],
        ... })
        >>> report = analyzer.analyze(indicators)
        >>> report.redundant_pairs  # mayer & 200dma_ratio likely flagged
    """

    def __init__(
        self,
        redundancy_threshold: float = 0.85,
        method: str = "spearman",
    ):
        """
        Args:
            redundancy_threshold: Abs correlation above which pairs are flagged.
            method: Correlation method ('pearson', 'spearman', 'kendall').
        """
        self.threshold = redundancy_threshold
        self.method = method

    def analyze(self, indicators: pd.DataFrame) -> CorrelationReport:
        """
        Analyze correlation structure of a set of indicators.

        Args:
            indicators: DataFrame where each column is an indicator time series.

        Returns:
            CorrelationReport with correlation matrix and redundancy flags.
        """
        corr = indicators.corr(method=self.method)

        # Find redundant pairs
        pairs: list[RedundancyPair] = []
        cols = list(corr.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c = abs(corr.iloc[i, j])
                if c >= self.threshold:
                    pairs.append(RedundancyPair(
                        indicator_a=cols[i],
                        indicator_b=cols[j],
                        correlation=round(float(corr.iloc[i, j]), 4),
                        recommendation=self._recommend(float(corr.iloc[i, j])),
                    ))

        # Effective N (based on eigenvalue decomposition)
        effective_n = self._compute_effective_n(corr)

        # Simple clustering via thresholding
        clusters = self._cluster_indicators(corr)

        return CorrelationReport(
            correlation_matrix=corr,
            redundant_pairs=pairs,
            cluster_assignments=clusters,
            effective_n=round(effective_n, 2),
        )

    def _recommend(self, correlation: float) -> str:
        """Generate a recommendation for a correlated pair."""
        abs_c = abs(correlation)
        if abs_c >= 0.95:
            return "REMOVE ONE — near-duplicate signals"
        if abs_c >= 0.90:
            return "STRONGLY consider removing one"
        return "REVIEW — moderately correlated, may be acceptable with justification"

    def _compute_effective_n(self, corr: pd.DataFrame) -> float:
        """
        Compute effective number of independent indicators.

        Uses the eigenvalue approach: effective_n = (sum of eigenvalues)^2 / sum(eigenvalues^2).
        This is equivalent to the inverse participation ratio.
        """
        try:
            eigenvalues = np.linalg.eigvalsh(corr.values)
            eigenvalues = eigenvalues[eigenvalues > 0]
            if len(eigenvalues) == 0:
                return float(len(corr))
            return float(np.sum(eigenvalues) ** 2 / np.sum(eigenvalues ** 2))
        except np.linalg.LinAlgError:
            return float(len(corr))

    def _cluster_indicators(self, corr: pd.DataFrame) -> dict[str, int]:
        """
        Simple clustering: group indicators that are highly correlated.

        Uses a greedy approach — each unclustered indicator starts a new cluster,
        then absorbs any unclustered indicators above the threshold.
        """
        cols = list(corr.columns)
        assigned: dict[str, int] = {}
        cluster_id = 0

        for col in cols:
            if col in assigned:
                continue
            assigned[col] = cluster_id
            for other in cols:
                if other in assigned:
                    continue
                if abs(corr.loc[col, other]) >= self.threshold:
                    assigned[other] = cluster_id
            cluster_id += 1

        return assigned
