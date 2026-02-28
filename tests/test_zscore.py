"""Tests for the z-score engine."""

import numpy as np
import pandas as pd
import pytest

from strategy_engine.core.zscore import (
    OutlierMethod,
    ZScoreConfig,
    ZScoreEngine,
)


@pytest.fixture
def engine() -> ZScoreEngine:
    return ZScoreEngine()


@pytest.fixture
def normal_series() -> pd.Series:
    np.random.seed(42)
    return pd.Series(np.random.normal(100, 15, 500))


@pytest.fixture
def series_with_outlier() -> pd.Series:
    np.random.seed(42)
    data = np.random.normal(100, 15, 500)
    data[0] = 1000  # extreme outlier
    data[1] = -500
    return pd.Series(data)


class TestZScoreCompute:
    def test_basic_zscore(self, engine: ZScoreEngine, normal_series: pd.Series) -> None:
        result = engine.compute(normal_series, current_value=100.0)
        assert abs(result.z_score) < 1.0  # mean value → near-zero z
        assert result.data_points_used > 0

    def test_extreme_high(self, engine: ZScoreEngine, normal_series: pd.Series) -> None:
        result = engine.compute(normal_series, current_value=200.0)
        assert result.z_score > 2.0

    def test_extreme_low(self, engine: ZScoreEngine, normal_series: pd.Series) -> None:
        result = engine.compute(normal_series, current_value=0.0)
        assert result.z_score < -2.0

    def test_zscore_clamped(self, engine: ZScoreEngine, normal_series: pd.Series) -> None:
        result = engine.compute(normal_series, current_value=9999.0)
        assert result.z_score <= 4.0
        result = engine.compute(normal_series, current_value=-9999.0)
        assert result.z_score >= -4.0

    def test_empty_series(self, engine: ZScoreEngine) -> None:
        result = engine.compute(pd.Series(dtype=float), current_value=100.0)
        assert result.z_score == 0.0
        assert result.data_points_used == 0


class TestOutlierMethods:
    def test_iqr_removes_outliers(self, series_with_outlier: pd.Series) -> None:
        engine = ZScoreEngine(ZScoreConfig(outlier_method=OutlierMethod.IQR))
        result = engine.compute(series_with_outlier, current_value=100.0)
        assert result.outliers_removed > 0

    def test_no_outlier_removal(self, series_with_outlier: pd.Series) -> None:
        engine = ZScoreEngine(ZScoreConfig(outlier_method=OutlierMethod.NONE))
        result = engine.compute(series_with_outlier, current_value=100.0)
        assert result.outliers_removed == 0

    def test_percentile_filter(self, series_with_outlier: pd.Series) -> None:
        engine = ZScoreEngine(ZScoreConfig(outlier_method=OutlierMethod.PERCENTILE))
        result = engine.compute(series_with_outlier, current_value=100.0)
        assert result.outliers_removed > 0

    def test_winsorize(self, series_with_outlier: pd.Series) -> None:
        engine = ZScoreEngine(ZScoreConfig(outlier_method=OutlierMethod.WINSORIZE))
        result = engine.compute(series_with_outlier, current_value=100.0)
        # Winsorize replaces rather than removes, so count stays the same
        assert result.data_points_used == len(series_with_outlier)

    def test_mad_filter(self, series_with_outlier: pd.Series) -> None:
        engine = ZScoreEngine(ZScoreConfig(outlier_method=OutlierMethod.MAD))
        result = engine.compute(series_with_outlier, current_value=100.0)
        assert result.outliers_removed > 0


class TestLogTransform:
    def test_log_transform(self, engine: ZScoreEngine) -> None:
        config = ZScoreConfig(use_log_transform=True)
        eng = ZScoreEngine(config)
        series = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        result = eng.compute(series, current_value=55.0)
        assert result.data_points_used > 0


class TestComputeSeries:
    def test_series_output_length(self, engine: ZScoreEngine, normal_series: pd.Series) -> None:
        result = engine.compute_series(normal_series)
        assert len(result) == len(normal_series)

    def test_rolling_zscore(self, normal_series: pd.Series) -> None:
        config = ZScoreConfig(rolling_window=50)
        engine = ZScoreEngine(config)
        result = engine.compute_series(normal_series)
        assert len(result) == len(normal_series)
