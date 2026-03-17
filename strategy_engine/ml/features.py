"""
Feature Extraction Pipeline — ML Stage 3.

Extracts quantitative features from price data and indicator outputs
for use in scoring and analysis. Features include trend metrics,
momentum, volatility, and cross-asset ratios.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class FeatureSet:
    """Extracted features for a single ticker/timeframe."""

    ticker: str
    timeframe: str
    features: pd.DataFrame  # columns = feature names, index = dates
    feature_names: list[str] = field(default_factory=list)

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    @property
    def n_samples(self) -> int:
        return len(self.features)

    def get(self, name: str) -> pd.Series:
        """Get a single feature series by name."""
        if name not in self.features.columns:
            raise KeyError(f"Feature '{name}' not found. Available: {self.feature_names}")
        return self.features[name]


class FeatureExtractor:
    """Extract standard features from OHLCV price data.

    Features extracted:
    - Trend: SMA ratios, linear regression slope, ADX proxy
    - Momentum: ROC at multiple periods, RSI proxy
    - Volatility: rolling std, ATR proxy, Bollinger bandwidth
    - Volume: OBV slope, volume ratio (if volume column present)

    Example:
        >>> extractor = FeatureExtractor()
        >>> features = extractor.extract(ohlcv_df, ticker="BTCUSD")
        >>> features.n_features
        14
    """

    DEFAULT_PERIODS = [7, 14, 21, 50]

    def __init__(self, periods: list[int] | None = None):
        self.periods = periods or self.DEFAULT_PERIODS

    def extract(
        self,
        ohlcv: pd.DataFrame,
        ticker: str = "unknown",
        timeframe: str = "1D",
    ) -> FeatureSet:
        """Extract all features from OHLCV data.

        Args:
            ohlcv: DataFrame with columns [open, high, low, close]
                   and optionally [volume]. DatetimeIndex expected.
            ticker: Name of the instrument.
            timeframe: Timeframe string.

        Returns:
            FeatureSet with extracted feature DataFrame.
        """
        df = self._prepare(ohlcv)
        features = pd.DataFrame(index=df.index)

        # Trend features
        for p in self.periods:
            features[f"sma_ratio_{p}"] = df["close"] / df["close"].rolling(p).mean()

        features["linreg_slope_21"] = self._rolling_slope(df["close"], 21)
        features["linreg_slope_50"] = self._rolling_slope(df["close"], 50)

        # Momentum features
        for p in self.periods:
            features[f"roc_{p}"] = df["close"].pct_change(p)

        features["rsi_14"] = self._rsi(df["close"], 14)

        # Volatility features
        features["volatility_21"] = df["close"].pct_change().rolling(21).std()
        features["atr_14"] = self._atr(df, 14)
        features["bbw_20"] = self._bollinger_bandwidth(df["close"], 20)

        # Volume features (if available)
        if "volume" in df.columns:
            features["volume_ratio_20"] = df["volume"] / df["volume"].rolling(20).mean()
            features["obv_slope_14"] = self._obv_slope(df, 14)

        features = features.dropna()

        return FeatureSet(
            ticker=ticker,
            timeframe=timeframe,
            features=features,
            feature_names=list(features.columns),
        )

    # ── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _prepare(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names."""
        df = df.copy()
        df.columns = [c.lower().strip() for c in df.columns]
        return df

    @staticmethod
    def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
        """Compute rolling linear regression slope."""
        def _slope(arr):
            if len(arr) < window:
                return np.nan
            x = np.arange(len(arr))
            try:
                coeffs = np.polyfit(x, arr, 1)
                return coeffs[0]
            except (np.linalg.LinAlgError, ValueError):
                return np.nan

        return series.rolling(window).apply(_slope, raw=True)

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Compute RSI."""
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute Average True Range (normalized by close)."""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        return (tr.rolling(period).mean() / close).round(6)

    @staticmethod
    def _bollinger_bandwidth(close: pd.Series, period: int = 20) -> pd.Series:
        """Compute Bollinger Bandwidth (width / middle band)."""
        middle = close.rolling(period).mean()
        std = close.rolling(period).std()
        return (2 * std / (middle + 1e-10)).round(6)

    @staticmethod
    def _obv_slope(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute OBV and return its rolling slope."""
        direction = np.sign(df["close"].diff())
        obv = (direction * df["volume"]).cumsum()

        def _slope(arr):
            if len(arr) < period:
                return np.nan
            x = np.arange(len(arr))
            try:
                return np.polyfit(x, arr, 1)[0]
            except (np.linalg.LinAlgError, ValueError):
                return np.nan

        return obv.rolling(period).apply(_slope, raw=True)
