"""
Alpha Decay Detector — identify indicators losing predictive power over time.

Key concern for SDCA Level 1: some indicators (e.g., stock-to-flow) decay
as markets evolve. This module quantifies that decay statistically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class DecayReport:
    """Results from alpha decay analysis."""

    indicator_name: str
    has_decay: bool
    decay_rate: float  # Slope of rolling correlation trend (negative = decaying)
    r_squared: float  # How well the decay trend fits
    p_value: float  # Statistical significance of the decay
    recent_correlation: float  # Correlation in most recent window
    historical_correlation: float  # Correlation in earliest window
    half_life_periods: Optional[float]  # Estimated half-life if decaying
    recommendation: str

    @property
    def summary(self) -> str:
        if self.has_decay:
            return (
                f"{self.indicator_name}: DECAYING (rate={self.decay_rate:.4f}, "
                f"p={self.p_value:.4f}, half-life≈{self.half_life_periods:.0f} periods)"
            )
        return f"{self.indicator_name}: Stable (rate={self.decay_rate:.4f}, p={self.p_value:.4f})"


class AlphaDecayDetector:
    """
    Detect whether an indicator's predictive power is decaying over time.

    Method:
    1. Compute rolling correlation between indicator and forward returns
    2. Fit a linear trend to the rolling correlations
    3. If the trend is significantly negative, flag as decaying

    Example:
        >>> detector = AlphaDecayDetector()
        >>> report = detector.analyze(
        ...     indicator_series=mayer_multiple,
        ...     returns_series=btc_30d_fwd_returns,
        ...     name="Mayer Multiple"
        ... )
        >>> report.has_decay
        False
    """

    def __init__(
        self,
        rolling_window: int = 365,
        min_correlation: float = 0.1,
        decay_significance: float = 0.05,
    ):
        """
        Args:
            rolling_window: Window size for rolling correlation.
            min_correlation: Min abs correlation to consider indicator useful at all.
            decay_significance: p-value threshold for decay to be significant.
        """
        self.rolling_window = rolling_window
        self.min_correlation = min_correlation
        self.decay_significance = decay_significance

    def analyze(
        self,
        indicator_series: pd.Series,
        returns_series: pd.Series,
        name: str = "indicator",
    ) -> DecayReport:
        """
        Analyze an indicator for alpha decay.

        Args:
            indicator_series: The indicator values over time.
            returns_series: Forward returns (e.g., 30-day forward return).
            name: Name of the indicator for the report.

        Returns:
            DecayReport with decay status and statistics.
        """
        # Align series
        aligned = pd.DataFrame({
            "indicator": indicator_series,
            "returns": returns_series,
        }).dropna()

        if len(aligned) < self.rolling_window * 2:
            return DecayReport(
                indicator_name=name,
                has_decay=False,
                decay_rate=0.0,
                r_squared=0.0,
                p_value=1.0,
                recent_correlation=0.0,
                historical_correlation=0.0,
                half_life_periods=None,
                recommendation="Insufficient data for decay analysis",
            )

        # Rolling correlation
        rolling_corr = (
            aligned["indicator"]
            .rolling(self.rolling_window)
            .corr(aligned["returns"])
            .dropna()
        )

        if len(rolling_corr) < 10:
            return DecayReport(
                indicator_name=name,
                has_decay=False,
                decay_rate=0.0,
                r_squared=0.0,
                p_value=1.0,
                recent_correlation=0.0,
                historical_correlation=0.0,
                half_life_periods=None,
                recommendation="Insufficient rolling correlation data",
            )

        # Fit linear trend to rolling correlations
        x = np.arange(len(rolling_corr))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, rolling_corr.values)

        # Recent vs historical correlation
        split = len(rolling_corr) // 4
        historical_corr = float(rolling_corr.iloc[:split].mean())
        recent_corr = float(rolling_corr.iloc[-split:].mean())

        # Determine decay
        is_decaying = slope < 0 and p_value < self.decay_significance

        # Estimate half-life (periods until correlation halves)
        half_life: Optional[float] = None
        if is_decaying and abs(slope) > 1e-8 and abs(historical_corr) > self.min_correlation:
            half_life = abs(historical_corr / (2 * slope))

        # Recommendation
        if is_decaying:
            if abs(recent_corr) < self.min_correlation:
                rec = "REMOVE — indicator has decayed below usefulness"
            elif half_life and half_life < 365:
                rec = "MONITOR CLOSELY — rapid decay, consider replacement"
            else:
                rec = "FLAG — slow decay detected, document in comments"
        elif abs(recent_corr) < self.min_correlation:
            rec = "REVIEW — low recent correlation, may not be useful"
        else:
            rec = "STABLE — no significant decay detected"

        return DecayReport(
            indicator_name=name,
            has_decay=is_decaying,
            decay_rate=round(float(slope), 6),
            r_squared=round(float(r_value ** 2), 4),
            p_value=round(float(p_value), 6),
            recent_correlation=round(recent_corr, 4),
            historical_correlation=round(historical_corr, 4),
            half_life_periods=round(half_life, 1) if half_life else None,
            recommendation=rec,
        )
