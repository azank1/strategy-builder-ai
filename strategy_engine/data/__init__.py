"""
Data sub-package — adapters for external data sources.
"""

from strategy_engine.data.base import DataAdapter, DataResult
from strategy_engine.data.coingecko import CoinGeckoAdapter
from strategy_engine.data.yahoo import YahooFinanceAdapter

__all__ = [
    "DataAdapter",
    "DataResult",
    "CoinGeckoAdapter",
    "YahooFinanceAdapter",
]
