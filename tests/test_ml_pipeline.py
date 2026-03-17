"""Tests for ML pipeline modules (Stages 1-4)."""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta

from strategy_engine.ml.isp import ISPLabeler, SwingPoint, ISPLabelResult
from strategy_engine.ml.optimization import (
    BayesianOptimizer,
    ParameterSpace,
    OptimizationResult,
)
from strategy_engine.ml.features import FeatureExtractor, FeatureSet
from strategy_engine.ml.timeframe import (
    TimeframeScaler,
    ScaledParameter,
    TimeframeScaleResult,
    TIMEFRAME_BARS,
)
from strategy_engine.models import TrendDirection


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_ohlcv(n: int = 200, trend: str = "up", seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")

    if trend == "up":
        base = np.cumsum(rng.randn(n) * 2 + 0.3) + 100
    elif trend == "down":
        base = np.cumsum(rng.randn(n) * 2 - 0.3) + 200
    else:
        # Zigzag: alternating up and down segments
        base = np.zeros(n)
        base[0] = 100
        segment_len = n // 6
        for i in range(1, n):
            seg = i // segment_len
            direction = 1 if seg % 2 == 0 else -1
            base[i] = base[i - 1] + direction * abs(rng.randn()) * 1.5

    high = base + abs(rng.randn(n)) * 2
    low = base - abs(rng.randn(n)) * 2
    open_ = base + rng.randn(n) * 0.5
    close = base + rng.randn(n) * 0.5
    volume = rng.randint(1000, 100000, n).astype(float)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ── ISP Labeler Tests ─────────────────────────────────────────────────────────


class TestISPLabeler:
    def test_basic_label(self):
        df = _make_ohlcv(200, trend="zigzag")
        labeler = ISPLabeler(swing_lookback=10, min_swing_pct=0.02)
        result = labeler.label(df, timeframe="1D")

        assert isinstance(result, ISPLabelResult)
        assert len(result.labels) > 0
        assert set(result.labels.unique()).issubset({-1, 1})
        assert result.trade_count > 0

    def test_label_output_length(self):
        df = _make_ohlcv(150)
        labeler = ISPLabeler(swing_lookback=5, min_swing_pct=0.01)
        result = labeler.label(df)
        assert len(result.labels) == len(df)

    def test_swing_detection(self):
        df = _make_ohlcv(200, trend="zigzag")
        labeler = ISPLabeler(swing_lookback=10, min_swing_pct=0.01)
        result = labeler.label(df)
        assert len(result.swing_points) >= 2
        for sp in result.swing_points:
            assert isinstance(sp, SwingPoint)
            assert sp.swing_type in ("high", "low")

    def test_swings_alternate(self):
        df = _make_ohlcv(300, trend="zigzag")
        labeler = ISPLabeler(swing_lookback=10, min_swing_pct=0.01)
        result = labeler.label(df)
        for i in range(1, len(result.swing_points)):
            assert result.swing_points[i].swing_type != result.swing_points[i - 1].swing_type

    def test_isp_model_generated(self):
        df = _make_ohlcv(200, trend="zigzag")
        labeler = ISPLabeler(swing_lookback=10, min_swing_pct=0.02)
        result = labeler.label(df, timeframe="1D")
        isp = result.isp
        assert isp.timeframe == "1D"
        assert len(isp.signals) > 0
        assert isp.start_date is not None
        assert isp.end_date is not None

    def test_avg_trade_duration(self):
        df = _make_ohlcv(200, trend="zigzag")
        labeler = ISPLabeler(swing_lookback=10, min_swing_pct=0.02)
        result = labeler.label(df)
        assert result.avg_trade_duration_days > 0

    def test_smooth_labels(self):
        df = _make_ohlcv(200, trend="zigzag")
        labeler = ISPLabeler(swing_lookback=10, min_swing_pct=0.01, smooth_window=5)
        result = labeler.label(df)
        assert set(result.labels.unique()).issubset({-1, 1})

    def test_column_normalization(self):
        df = _make_ohlcv(100)
        df.columns = ["Open", " High", "Low ", "CLOSE", "Volume"]
        labeler = ISPLabeler(swing_lookback=5, min_swing_pct=0.01)
        result = labeler.label(df)
        assert len(result.labels) == 100

    def test_missing_columns_raises(self):
        df = pd.DataFrame({"close": [1, 2, 3], "open": [1, 2, 3]},
                          index=pd.date_range("2020-01-01", periods=3))
        labeler = ISPLabeler()
        with pytest.raises(ValueError, match="missing columns"):
            labeler.label(df)

    def test_date_column_input(self):
        """Test with 'date' column instead of DatetimeIndex."""
        df = _make_ohlcv(100)
        df = df.reset_index().rename(columns={"index": "date"})
        labeler = ISPLabeler(swing_lookback=5, min_swing_pct=0.01)
        result = labeler.label(df)
        assert len(result.labels) == 100


# ── Bayesian Optimizer Tests ─────────────────────────────────────────────────


class TestBayesianOptimizer:
    def _simple_objective(self, params: dict) -> float:
        """Rosenbrock-like: best at period=20, threshold=0.2."""
        p = params.get("period", 20)
        t = params.get("threshold", 0.2)
        return -((p - 20) ** 2 + 100 * (t - 0.2) ** 2)

    def test_basic_optimization(self):
        space = [
            ParameterSpace("period", 5, 50, "int"),
            ParameterSpace("threshold", 0.01, 0.5),
        ]
        opt = BayesianOptimizer(space, n_iterations=20, n_initial=8)
        result = opt.optimize(self._simple_objective)

        assert isinstance(result, OptimizationResult)
        assert result.best_score > -500
        assert "period" in result.best_params
        assert "threshold" in result.best_params
        assert len(result.all_trials) == 20

    def test_convergence_improves(self):
        space = [ParameterSpace("x", -5, 5)]
        opt = BayesianOptimizer(space, n_iterations=25, n_initial=10)
        result = opt.optimize(lambda p: -(p["x"] ** 2))

        # Convergence history should be non-decreasing
        for i in range(1, len(result.convergence_history)):
            assert result.convergence_history[i] >= result.convergence_history[i - 1]

    def test_default_params_comparison(self):
        space = [ParameterSpace("x", 0, 10)]
        opt = BayesianOptimizer(space, n_iterations=15, n_initial=8)
        result = opt.optimize(
            lambda p: -(p["x"] - 5) ** 2,
            default_params={"x": 0},
        )
        assert result.improvement_over_default >= 0

    def test_integer_params(self):
        space = [ParameterSpace("n", 1, 100, "int")]
        opt = BayesianOptimizer(space, n_iterations=15, n_initial=10)
        result = opt.optimize(lambda p: -(p["n"] - 42) ** 2)
        assert isinstance(result.best_params["n"], int)

    def test_log_scale_params(self):
        space = [ParameterSpace("lr", 0.0001, 1.0, log_scale=True)]
        opt = BayesianOptimizer(space, n_iterations=15, n_initial=10)
        result = opt.optimize(lambda p: -(np.log(p["lr"]) - np.log(0.01)) ** 2)
        assert 0.0001 <= result.best_params["lr"] <= 1.0

    def test_multi_dimensional(self):
        space = [
            ParameterSpace("a", -5, 5),
            ParameterSpace("b", -5, 5),
            ParameterSpace("c", -5, 5),
        ]
        opt = BayesianOptimizer(space, n_iterations=30, n_initial=15)
        result = opt.optimize(
            lambda p: -(p["a"] ** 2 + p["b"] ** 2 + p["c"] ** 2)
        )
        assert result.best_score > -50

    def test_n_iterations_respected(self):
        space = [ParameterSpace("x", 0, 1)]
        opt = BayesianOptimizer(space, n_iterations=12, n_initial=5)
        result = opt.optimize(lambda p: p["x"])
        assert result.n_iterations == 12


# ── Feature Extractor Tests ──────────────────────────────────────────────────


class TestFeatureExtractor:
    def test_basic_extraction(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df, ticker="BTCUSD", timeframe="1D")

        assert isinstance(fs, FeatureSet)
        assert fs.ticker == "BTCUSD"
        assert fs.timeframe == "1D"
        assert fs.n_features > 0
        assert fs.n_samples > 0

    def test_expected_features_present(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df)

        expected = [
            "sma_ratio_7", "sma_ratio_14", "sma_ratio_21", "sma_ratio_50",
            "roc_7", "roc_14", "rsi_14", "volatility_21", "atr_14", "bbw_20",
        ]
        for name in expected:
            assert name in fs.feature_names

    def test_volume_features_with_volume(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df)
        assert "volume_ratio_20" in fs.feature_names
        assert "obv_slope_14" in fs.feature_names

    def test_no_volume_column(self):
        df = _make_ohlcv(200).drop(columns=["volume"])
        ext = FeatureExtractor()
        fs = ext.extract(df)
        assert "volume_ratio_20" not in fs.feature_names
        assert "obv_slope_14" not in fs.feature_names

    def test_no_nans_in_features(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df)
        assert not fs.features.isna().any().any()

    def test_custom_periods(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor(periods=[5, 10])
        fs = ext.extract(df)
        assert "sma_ratio_5" in fs.feature_names
        assert "sma_ratio_10" in fs.feature_names
        assert "sma_ratio_14" not in fs.feature_names

    def test_get_feature(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df)
        series = fs.get("rsi_14")
        assert isinstance(series, pd.Series)
        assert len(series) == fs.n_samples

    def test_get_missing_feature_raises(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df)
        with pytest.raises(KeyError, match="not found"):
            fs.get("nonexistent_feature")

    def test_rsi_bounds(self):
        df = _make_ohlcv(200)
        ext = FeatureExtractor()
        fs = ext.extract(df)
        rsi = fs.get("rsi_14")
        assert rsi.min() >= 0
        assert rsi.max() <= 100


# ── Timeframe Scaler Tests ───────────────────────────────────────────────────


class TestTimeframeScaler:
    def test_scale_factor_1d_to_1w(self):
        scaler = TimeframeScaler()
        factor = scaler.scale_factor("1D", "1W")
        assert factor == pytest.approx(1.0 / 7, rel=1e-3)

    def test_scale_factor_1d_to_1d(self):
        scaler = TimeframeScaler()
        factor = scaler.scale_factor("1D", "1D")
        assert factor == pytest.approx(1.0)

    def test_scale_factor_1h_to_1d(self):
        scaler = TimeframeScaler()
        factor = scaler.scale_factor("1H", "1D")
        assert factor == pytest.approx(1.0 / 24)

    def test_scale_params_period(self):
        scaler = TimeframeScaler()
        result = scaler.scale_params(
            params={"period": 14},
            param_types={"period": "period"},
            source_tf="1D",
            target_tf="1W",
        )
        assert isinstance(result, TimeframeScaleResult)
        assert result.scaled_params[0].scaled_value == 2.0  # 14/7=2

    def test_scale_params_fixed_unchanged(self):
        scaler = TimeframeScaler()
        result = scaler.scale_params(
            params={"threshold": 0.5},
            param_types={"threshold": "fixed"},
            source_tf="1D",
            target_tf="1W",
        )
        assert result.scaled_params[0].scaled_value == 0.5

    def test_scale_params_volatility_sqrt(self):
        scaler = TimeframeScaler()
        factor = scaler.scale_factor("1D", "1W")
        result = scaler.scale_params(
            params={"vol": 1.0},
            param_types={"vol": "volatility"},
            source_tf="1D",
            target_tf="1W",
        )
        expected = np.sqrt(factor)
        assert result.scaled_params[0].scaled_value == pytest.approx(expected, rel=1e-4)

    def test_scale_params_multiple(self):
        scaler = TimeframeScaler()
        result = scaler.scale_params(
            params={"period": 21, "threshold": 0.5, "vol": 1.0},
            param_types={"period": "period", "threshold": "fixed", "vol": "volatility"},
            source_tf="1D",
            target_tf="1W",
        )
        assert len(result.scaled_params) == 3

    def test_period_min_1(self):
        """Period should never scale below 1."""
        scaler = TimeframeScaler()
        result = scaler.scale_params(
            params={"period": 1},
            param_types={"period": "period"},
            source_tf="1H",
            target_tf="1M",
        )
        assert result.scaled_params[0].scaled_value >= 1.0

    def test_unknown_timeframe_raises(self):
        scaler = TimeframeScaler()
        with pytest.raises(ValueError, match="Unknown"):
            scaler.scale_factor("1D", "5MIN")

    def test_resample_daily_to_weekly(self):
        df = _make_ohlcv(100)
        scaler = TimeframeScaler()
        weekly = scaler.resample_ohlcv(df, "1D", "1W")
        assert len(weekly) < len(df)
        assert "open" in weekly.columns
        assert "high" in weekly.columns
        assert "close" in weekly.columns

    def test_resample_preserves_volume(self):
        df = _make_ohlcv(100)
        scaler = TimeframeScaler()
        weekly = scaler.resample_ohlcv(df, "1D", "1W")
        assert "volume" in weekly.columns

    def test_resample_downsample_raises(self):
        scaler = TimeframeScaler()
        df = _make_ohlcv(100)
        with pytest.raises(ValueError, match="Cannot downsample"):
            scaler.resample_ohlcv(df, "1W", "1D")

    def test_all_timeframes_in_mapping(self):
        """Verify all timeframes have valid bars-per-day values."""
        for tf, bpd in TIMEFRAME_BARS.items():
            assert bpd > 0


# ── Integration: __init__ exports ─────────────────────────────────────────────


class TestMLExports:
    def test_all_exports(self):
        from strategy_engine.ml import (
            AlphaDecayDetector,
            CorrelationAnalyzer,
            RegimeDetector,
            ISPLabeler,
            BayesianOptimizer,
            FeatureExtractor,
            TimeframeScaler,
        )
        assert ISPLabeler is not None
        assert BayesianOptimizer is not None
        assert FeatureExtractor is not None
        assert TimeframeScaler is not None
