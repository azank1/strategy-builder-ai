"""
Z-Score Engine — compute z-scores with outlier exclusion.

Supports multiple outlier removal methods and normalization approaches
suitable for long-term valuation indicators (SDCA Level 1).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class OutlierMethod(str, Enum):
    """Methods for excluding outliers before z-score computation."""

    NONE = "none"
    IQR = "iqr"  # Interquartile Range
    PERCENTILE = "percentile"  # Clip to percentile bounds
    WINSORIZE = "winsorize"  # Replace outliers with boundary values
    MAD = "mad"  # Median Absolute Deviation


class ZScoreConfig(BaseModel):
    """Configuration for z-score calculation."""

    outlier_method: OutlierMethod = OutlierMethod.IQR
    iqr_multiplier: float = Field(1.5, ge=1.0, le=3.0)
    percentile_lower: float = Field(2.5, ge=0.0, le=10.0)
    percentile_upper: float = Field(97.5, ge=90.0, le=100.0)
    mad_threshold: float = Field(3.0, ge=2.0, le=5.0)
    use_log_transform: bool = False
    rolling_window: Optional[int] = Field(
        None, description="If set, compute rolling z-score over this many periods"
    )


class ZScoreResult(BaseModel):
    """Result of a z-score computation."""

    z_score: float
    mean: float
    std: float
    raw_value: float
    data_points_used: int
    outliers_removed: int
    method: OutlierMethod


class ZScoreEngine:
    """
    Compute z-scores for indicator values with configurable outlier exclusion.

    The SDCA system requires z-scoring every indicator to create a normalized
    composite signal. Outliers MUST be excluded to avoid distortion.

    Example:
        >>> engine = ZScoreEngine()
        >>> series = pd.Series([10, 12, 11, 13, 100, 12, 11, 14, 10, 13])
        >>> result = engine.compute(series, current_value=12.5)
        >>> result.z_score  # Will exclude the 100 outlier
    """

    def __init__(self, config: Optional[ZScoreConfig] = None) -> None:
        self.config = config or ZScoreConfig()

    def compute(self, series: pd.Series, current_value: float) -> ZScoreResult:
        """
        Compute the z-score of current_value against a historical series.

        Args:
            series: Historical data points for the indicator.
            current_value: The current indicator reading to score.

        Returns:
            ZScoreResult with the z-score and computation metadata.
        """
        clean = series.dropna().copy()
        original_count = len(clean)

        if self.config.use_log_transform:
            # Apply log transform for skewed distributions (e.g., price data)
            clean = clean[clean > 0]
            clean = np.log(clean)
            current_value = np.log(current_value) if current_value > 0 else 0.0

        # Remove outliers
        cleaned = self._remove_outliers(clean)
        outliers_removed = original_count - len(cleaned)

        if len(cleaned) < 3:
            return ZScoreResult(
                z_score=0.0,
                mean=float(clean.mean()) if len(clean) > 0 else 0.0,
                std=0.0,
                raw_value=current_value,
                data_points_used=len(cleaned),
                outliers_removed=outliers_removed,
                method=self.config.outlier_method,
            )

        mean = float(cleaned.mean())
        std = float(cleaned.std(ddof=1))

        if std == 0:
            z = 0.0
        else:
            z = (current_value - mean) / std

        # Clamp to ±4 SD to prevent extreme scores
        z = max(-4.0, min(4.0, z))

        return ZScoreResult(
            z_score=round(z, 4),
            mean=round(mean, 6),
            std=round(std, 6),
            raw_value=current_value,
            data_points_used=len(cleaned),
            outliers_removed=outliers_removed,
            method=self.config.outlier_method,
        )

    def compute_series(self, series: pd.Series) -> pd.Series:
        """Compute rolling z-scores for an entire series."""
        window = self.config.rolling_window
        if window:
            return self._rolling_zscore(series, window)
        # Full-history z-score at each point
        results = []
        for i in range(len(series)):
            if i < 3:
                results.append(0.0)
                continue
            historical = series.iloc[:i]
            result = self.compute(historical, series.iloc[i])
            results.append(result.z_score)
        return pd.Series(results, index=series.index, name=f"{series.name}_zscore")

    def _rolling_zscore(self, series: pd.Series, window: int) -> pd.Series:
        """Compute z-scores over a rolling window."""
        results = []
        for i in range(len(series)):
            start = max(0, i - window)
            window_data = series.iloc[start:i]
            if len(window_data) < 3:
                results.append(0.0)
                continue
            result = self.compute(window_data, series.iloc[i])
            results.append(result.z_score)
        return pd.Series(results, index=series.index, name=f"{series.name}_zscore")

    def _remove_outliers(self, series: pd.Series) -> pd.Series:
        """Remove outliers from a series based on the configured method."""
        method = self.config.outlier_method

        if method == OutlierMethod.NONE:
            return series

        if method == OutlierMethod.IQR:
            return self._iqr_filter(series)

        if method == OutlierMethod.PERCENTILE:
            return self._percentile_filter(series)

        if method == OutlierMethod.WINSORIZE:
            return self._winsorize(series)

        if method == OutlierMethod.MAD:
            return self._mad_filter(series)

        return series

    def _iqr_filter(self, series: pd.Series) -> pd.Series:
        """Remove outliers using the IQR method."""
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        multiplier = self.config.iqr_multiplier
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        return series[(series >= lower) & (series <= upper)]

    def _percentile_filter(self, series: pd.Series) -> pd.Series:
        """Remove outliers by clipping to percentile bounds."""
        lower = series.quantile(self.config.percentile_lower / 100)
        upper = series.quantile(self.config.percentile_upper / 100)
        return series[(series >= lower) & (series <= upper)]

    def _winsorize(self, series: pd.Series) -> pd.Series:
        """Replace outliers with boundary values (Winsorization)."""
        lower = series.quantile(self.config.percentile_lower / 100)
        upper = series.quantile(self.config.percentile_upper / 100)
        return series.clip(lower=lower, upper=upper)

    def _mad_filter(self, series: pd.Series) -> pd.Series:
        """Remove outliers using Median Absolute Deviation."""
        median = series.median()
        mad = (series - median).abs().median()
        if mad == 0:
            return series
        threshold = self.config.mad_threshold
        modified_z = 0.6745 * (series - median) / mad
        return series[modified_z.abs() <= threshold]
