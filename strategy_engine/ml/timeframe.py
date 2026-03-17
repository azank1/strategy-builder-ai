"""
Timeframe Scaling — ML Stage 4.

Adapts indicator parameters and signals across different timeframes.
An indicator optimized on 1D data needs parameter adjustment to work
on 3D or 1W charts. This module handles the conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# Canonical bars-per-day for each timeframe
TIMEFRAME_BARS: dict[str, float] = {
    "1H": 24.0,
    "2H": 12.0,
    "4H": 6.0,
    "6H": 4.0,
    "8H": 3.0,
    "12H": 2.0,
    "1D": 1.0,
    "2D": 0.5,
    "3D": 1.0 / 3,
    "1W": 1.0 / 7,
    "2W": 1.0 / 14,
    "1M": 1.0 / 30,
}


@dataclass
class ScaledParameter:
    """A single parameter scaled between timeframes."""

    name: str
    original_value: float
    scaled_value: float
    source_tf: str
    target_tf: str
    scale_factor: float


@dataclass
class TimeframeScaleResult:
    """Output of timeframe scaling."""

    source_timeframe: str
    target_timeframe: str
    scale_factor: float
    scaled_params: list[ScaledParameter]


class TimeframeScaler:
    """Scale indicator parameters and signals across timeframes.

    Example:
        >>> scaler = TimeframeScaler()
        >>> result = scaler.scale_params(
        ...     params={"period": 14, "threshold": 0.5},
        ...     param_types={"period": "period", "threshold": "fixed"},
        ...     source_tf="1D",
        ...     target_tf="1W",
        ... )
        >>> result.scaled_params[0].scaled_value  # period: 14 → 2
        2.0
    """

    def scale_factor(self, source_tf: str, target_tf: str) -> float:
        """Compute the bar-count ratio between timeframes.

        E.g., 1D → 1W: each weekly bar = 7 daily bars, so factor = 1/7.
        Period params get divided by this factor (14D ≈ 2W).
        """
        source_bpd = TIMEFRAME_BARS.get(source_tf)
        target_bpd = TIMEFRAME_BARS.get(target_tf)
        if source_bpd is None:
            raise ValueError(f"Unknown source timeframe: {source_tf}")
        if target_bpd is None:
            raise ValueError(f"Unknown target timeframe: {target_tf}")
        return target_bpd / source_bpd

    def scale_params(
        self,
        params: dict[str, float],
        param_types: dict[str, str],
        source_tf: str,
        target_tf: str,
    ) -> TimeframeScaleResult:
        """Scale a set of parameters from source to target timeframe.

        Args:
            params: Parameter name → value.
            param_types: Parameter name → type. Types:
                - "period": Lookback period — scale by factor, round to int, min 1.
                - "threshold": Price/percentage threshold — no scaling.
                - "volatility": Volatility-based — scale by sqrt(factor).
                - "fixed": No scaling.
            source_tf: Source timeframe (e.g. "1D").
            target_tf: Target timeframe (e.g. "1W").

        Returns:
            TimeframeScaleResult with all scaled parameters.
        """
        factor = self.scale_factor(source_tf, target_tf)
        scaled: list[ScaledParameter] = []

        for name, value in params.items():
            ptype = param_types.get(name, "fixed")
            new_value = self._scale_single(value, ptype, factor)
            scaled.append(ScaledParameter(
                name=name,
                original_value=value,
                scaled_value=new_value,
                source_tf=source_tf,
                target_tf=target_tf,
                scale_factor=factor,
            ))

        return TimeframeScaleResult(
            source_timeframe=source_tf,
            target_timeframe=target_tf,
            scale_factor=round(factor, 6),
            scaled_params=scaled,
        )

    def resample_ohlcv(
        self,
        ohlcv: pd.DataFrame,
        source_tf: str,
        target_tf: str,
    ) -> pd.DataFrame:
        """Resample OHLCV data from source to target timeframe.

        Only supports upsampling (e.g. 1D → 1W), not downsampling.
        """
        factor = self.scale_factor(source_tf, target_tf)
        if factor > 1.0:
            raise ValueError(
                f"Cannot downsample from {source_tf} to {target_tf}. "
                "Target timeframe must be >= source."
            )

        df = ohlcv.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        # Determine pandas resample rule
        rule = self._tf_to_pandas_rule(target_tf)

        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
        if "volume" in df.columns:
            agg["volume"] = "sum"

        return df.resample(rule).agg(agg).dropna()

    # ── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _scale_single(value: float, param_type: str, factor: float) -> float:
        """Scale a single parameter value."""
        if param_type == "period":
            scaled = value * factor
            return float(max(1, round(scaled)))
        elif param_type == "volatility":
            return round(value * np.sqrt(factor), 6)
        elif param_type in ("threshold", "fixed"):
            return value
        else:
            return value

    @staticmethod
    def _tf_to_pandas_rule(tf: str) -> str:
        """Convert timeframe string to pandas resample rule."""
        mapping = {
            "1H": "1h",
            "2H": "2h",
            "4H": "4h",
            "6H": "6h",
            "8H": "8h",
            "12H": "12h",
            "1D": "1D",
            "2D": "2D",
            "3D": "3D",
            "1W": "1W",
            "2W": "2W",
            "1M": "1ME",
        }
        rule = mapping.get(tf)
        if rule is None:
            raise ValueError(f"No pandas resample rule for timeframe: {tf}")
        return rule
