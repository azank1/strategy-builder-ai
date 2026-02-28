"""
Base data adapter interface and shared types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd


class DataFrequency(str, Enum):
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"


@dataclass
class DataResult:
    """Standardized result from any data adapter."""

    series: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    is_cached: bool = False

    @property
    def start_date(self) -> Optional[date]:
        if self.series.empty:
            return None
        return self.series.index.min().date() if hasattr(self.series.index.min(), "date") else None

    @property
    def end_date(self) -> Optional[date]:
        if self.series.empty:
            return None
        return self.series.index.max().date() if hasattr(self.series.index.max(), "date") else None

    @property
    def data_points(self) -> int:
        return len(self.series)


class DataAdapter(ABC):
    """
    Abstract base for all data source adapters.

    Implementations must provide:
    - `fetch_price()` for OHLCV price data
    - `fetch_metric()` for named on-chain / macro metrics
    - `supported_assets` listing available asset identifiers
    """

    @abstractmethod
    async def fetch_price(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> DataResult:
        """Fetch historical price data for a symbol."""
        ...

    @abstractmethod
    async def fetch_metric(
        self,
        metric_name: str,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> DataResult:
        """Fetch a named metric (e.g., NVT ratio, MVRV, Fear & Greed)."""
        ...

    @abstractmethod
    def supported_assets(self) -> list[str]:
        """Return the list of supported asset identifiers."""
        ...

    @abstractmethod
    def supported_metrics(self) -> list[str]:
        """Return the list of available metric names."""
        ...
