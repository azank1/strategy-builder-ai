"""
Yahoo Finance data adapter — stocks, ETFs, gold, indices.

Uses the yfinance library for free market data.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from strategy_engine.data.base import DataAdapter, DataFrequency, DataResult

# Map our asset IDs to Yahoo Finance tickers
_TICKER_MAP: dict[str, str] = {
    "btc": "BTC-USD",
    "eth": "ETH-USD",
    "gold": "GC=F",
    "xau": "GC=F",
    "spx": "^GSPC",
    "spy": "SPY",
    "qqq": "QQQ",
    "sol": "SOL-USD",
    "bnb": "BNB-USD",
}

_FREQ_MAP: dict[DataFrequency, str] = {
    DataFrequency.DAILY: "1d",
    DataFrequency.WEEKLY: "1wk",
    DataFrequency.MONTHLY: "1mo",
}


class YahooFinanceAdapter(DataAdapter):
    """
    Adapter for Yahoo Finance data via the `yfinance` library.

    Supports stocks, ETFs, commodities, and crypto pairs.
    """

    def __init__(self) -> None:
        try:
            import yfinance  # noqa: F401

            self._yf = yfinance
        except ImportError:
            raise ImportError(
                "yfinance is required for YahooFinanceAdapter. "
                "Install it with: pip install yfinance"
            )

    async def fetch_price(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> DataResult:
        """Fetch historical OHLCV price data from Yahoo Finance."""
        ticker = _TICKER_MAP.get(symbol.lower(), symbol.upper())
        end = end_date or date.today()

        # yfinance is synchronous — run directly (consider wrapping in threadpool)
        df = self._yf.download(
            ticker,
            start=start_date.isoformat(),
            end=end.isoformat(),
            interval=_FREQ_MAP.get(frequency, "1d"),
            progress=False,
        )

        if df.empty:
            return DataResult(series=pd.Series(dtype=float), source="yahoo_finance")

        # Use adjusted close if available, else close
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
        series = df[col].squeeze()
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        series.name = f"{symbol}_close"

        return DataResult(
            series=series,
            metadata={
                "ticker": ticker,
                "frequency": frequency.value,
                "columns": list(df.columns),
            },
            source="yahoo_finance",
        )

    async def fetch_metric(
        self,
        metric_name: str,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> DataResult:
        """
        Fetch a market metric from Yahoo Finance.

        Available metrics: open, high, low, close, volume, adj_close
        """
        ticker = _TICKER_MAP.get(symbol.lower(), symbol.upper())
        end = end_date or date.today()

        df = self._yf.download(
            ticker,
            start=start_date.isoformat(),
            end=end.isoformat(),
            progress=False,
        )

        col_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "adj_close": "Adj Close",
        }

        col = col_map.get(metric_name.lower())
        if not col or col not in df.columns:
            raise ValueError(
                f"Unsupported metric: {metric_name}. Available: {list(col_map.keys())}"
            )

        series = df[col].squeeze()
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        series.name = f"{symbol}_{metric_name}"

        return DataResult(
            series=series,
            metadata={"ticker": ticker, "metric": metric_name},
            source="yahoo_finance",
        )

    def supported_assets(self) -> list[str]:
        return list(_TICKER_MAP.keys())

    def supported_metrics(self) -> list[str]:
        return ["open", "high", "low", "close", "volume", "adj_close"]
