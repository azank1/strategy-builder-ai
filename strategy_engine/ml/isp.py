"""
ISP Labeling Engine — ML Stage 1.

Generates Intended Signal Period (ISP) labels from price data.
ISP labels define the "ideal" trend direction at each point in time,
serving as ground truth for optimizing indicator parameters.

Method:
1. Identify significant swing highs/lows using a configurable lookback.
2. Connect swings to form a zigzag trend line.
3. Label each bar as LONG (swing low → swing high) or SHORT (swing high → swing low).
4. Optionally smooth labels to remove noise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from strategy_engine.models import ISPSignal, IntendedSignalPeriod, TrendDirection


@dataclass
class SwingPoint:
    """A detected swing high or low."""

    index: int
    date: date
    price: float
    swing_type: str  # "high" or "low"


@dataclass
class ISPLabelResult:
    """Output of the ISP labeling process."""

    labels: pd.Series  # 1 = LONG, -1 = SHORT, index = dates
    swing_points: list[SwingPoint]
    trade_count: int
    avg_trade_duration_days: float
    isp: IntendedSignalPeriod
    method: str = "zigzag"


class ISPLabeler:
    """Generate ISP labels from OHLC price data.

    The ISP defines the "perfect hindsight" trend signal. Indicators are
    then evaluated against it to determine how well they capture the trend.

    Example:
        >>> labeler = ISPLabeler(swing_lookback=20)
        >>> result = labeler.label(ohlc_df, timeframe="1D")
        >>> result.trade_count
        12
    """

    def __init__(
        self,
        swing_lookback: int = 20,
        min_swing_pct: float = 0.05,
        smooth_window: int = 0,
    ):
        """
        Args:
            swing_lookback: Bars to look left/right for swing detection.
            min_swing_pct: Minimum % move to qualify as a valid swing.
            smooth_window: If >0, smooth labels with majority vote over this window.
        """
        self.swing_lookback = swing_lookback
        self.min_swing_pct = min_swing_pct
        self.smooth_window = smooth_window

    def label(
        self,
        ohlc: pd.DataFrame,
        timeframe: str = "1D",
    ) -> ISPLabelResult:
        """Generate ISP labels from OHLC data.

        Args:
            ohlc: DataFrame with columns ['open', 'high', 'low', 'close']
                  and a DatetimeIndex or 'date' column.
            timeframe: Timeframe string for the ISP record.

        Returns:
            ISPLabelResult with labels, swing points, and ISP model.
        """
        ohlc = self._prepare_df(ohlc)
        swings = self._detect_swings(ohlc)
        swings = self._filter_swings(swings, ohlc)
        labels = self._swings_to_labels(swings, len(ohlc), ohlc.index)

        if self.smooth_window > 0:
            labels = self._smooth_labels(labels)

        isp = self._build_isp(labels, timeframe)
        trade_count = isp.trade_count
        avg_duration = self._avg_trade_duration(labels)

        return ISPLabelResult(
            labels=labels,
            swing_points=swings,
            trade_count=trade_count,
            avg_trade_duration_days=avg_duration,
            isp=isp,
        )

    # ── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _prepare_df(ohlc: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names and ensure DatetimeIndex."""
        df = ohlc.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        if "date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        required = {"open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"OHLC data missing columns: {missing}")

        return df.sort_index()

    def _detect_swings(self, ohlc: pd.DataFrame) -> list[SwingPoint]:
        """Detect swing highs and lows using rolling window."""
        highs = ohlc["high"].values
        lows = ohlc["low"].values
        n = len(ohlc)
        lb = self.swing_lookback
        swings: list[SwingPoint] = []

        for i in range(lb, n - lb):
            window_highs = highs[i - lb : i + lb + 1]
            window_lows = lows[i - lb : i + lb + 1]

            if highs[i] == window_highs.max():
                swings.append(SwingPoint(
                    index=i,
                    date=ohlc.index[i].date() if hasattr(ohlc.index[i], "date") else ohlc.index[i],
                    price=float(highs[i]),
                    swing_type="high",
                ))
            elif lows[i] == window_lows.min():
                swings.append(SwingPoint(
                    index=i,
                    date=ohlc.index[i].date() if hasattr(ohlc.index[i], "date") else ohlc.index[i],
                    price=float(lows[i]),
                    swing_type="low",
                ))

        return self._alternate_swings(swings)

    @staticmethod
    def _alternate_swings(swings: list[SwingPoint]) -> list[SwingPoint]:
        """Ensure swings alternate between high and low."""
        if not swings:
            return swings

        result: list[SwingPoint] = [swings[0]]
        for s in swings[1:]:
            if s.swing_type != result[-1].swing_type:
                result.append(s)
            else:
                # Keep the more extreme swing
                if s.swing_type == "high" and s.price > result[-1].price:
                    result[-1] = s
                elif s.swing_type == "low" and s.price < result[-1].price:
                    result[-1] = s

        return result

    def _filter_swings(
        self, swings: list[SwingPoint], ohlc: pd.DataFrame,
    ) -> list[SwingPoint]:
        """Remove swings with insufficient magnitude."""
        if len(swings) < 2:
            return swings

        filtered: list[SwingPoint] = [swings[0]]
        for i in range(1, len(swings)):
            prev = filtered[-1]
            curr = swings[i]
            pct_move = abs(curr.price - prev.price) / max(prev.price, 1e-10)
            if pct_move >= self.min_swing_pct:
                filtered.append(curr)
            else:
                # Merge with previous — keep previous direction
                pass

        return filtered

    @staticmethod
    def _swings_to_labels(
        swings: list[SwingPoint],
        length: int,
        index: pd.DatetimeIndex,
    ) -> pd.Series:
        """Convert swing points to per-bar labels."""
        labels = np.ones(length, dtype=int)  # default LONG

        for i in range(len(swings) - 1):
            start = swings[i].index
            end = swings[i + 1].index
            if swings[i].swing_type == "high":
                labels[start:end] = -1  # HIGH → LOW = SHORT
            else:
                labels[start:end] = 1   # LOW → HIGH = LONG

        # Handle tail after last swing
        if swings and swings[-1].swing_type == "high":
            labels[swings[-1].index :] = -1
        elif swings and swings[-1].swing_type == "low":
            labels[swings[-1].index :] = 1

        return pd.Series(labels, index=index, name="isp_label")

    @staticmethod
    def _smooth_labels(labels: pd.Series) -> pd.Series:
        """Smooth labels via majority vote in rolling window."""
        window = max(3, len(labels) // 50)
        rolled = labels.rolling(window, center=True, min_periods=1).mean()
        return (rolled > 0).astype(int).replace({0: -1, 1: 1}).rename("isp_label")

    @staticmethod
    def _build_isp(labels: pd.Series, timeframe: str) -> IntendedSignalPeriod:
        """Convert labels to an ISP model with signal list."""
        signals: list[ISPSignal] = []
        prev_dir = None

        for dt, val in labels.items():
            direction = TrendDirection.LONG if val == 1 else TrendDirection.SHORT
            if direction != prev_dir:
                d = dt.date() if hasattr(dt, "date") else dt
                signals.append(ISPSignal(date=d, direction=direction))
                prev_dir = direction

        start = labels.index[0]
        end = labels.index[-1]

        return IntendedSignalPeriod(
            start_date=start.date() if hasattr(start, "date") else start,
            end_date=end.date() if hasattr(end, "date") else end,
            timeframe=timeframe,
            signals=signals,
        )

    @staticmethod
    def _avg_trade_duration(labels: pd.Series) -> float:
        """Average number of bars per trade (direction segment)."""
        if labels.empty:
            return 0.0

        changes = (labels != labels.shift()).cumsum()
        segment_lengths = labels.groupby(changes).count()
        return round(float(segment_lengths.mean()), 1)
