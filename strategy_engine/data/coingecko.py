"""
CoinGecko data adapter — free crypto price & metric data.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import httpx
import pandas as pd

from strategy_engine.data.base import DataAdapter, DataFrequency, DataResult

_BASE_URL = "https://api.coingecko.com/api/v3"

# Map our asset IDs to CoinGecko IDs
_ASSET_MAP: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "ada": "cardano",
    "avax": "avalanche-2",
    "dot": "polkadot",
    "link": "chainlink",
}


class CoinGeckoAdapter(DataAdapter):
    """
    Adapter for CoinGecko's free API (no key required, rate-limited).

    Supports historical price and limited market metrics for crypto assets.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["x-cg-demo-key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    async def fetch_price(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> DataResult:
        """Fetch historical daily price from CoinGecko."""
        cg_id = _ASSET_MAP.get(symbol.lower())
        if not cg_id:
            raise ValueError(f"Unsupported asset: {symbol}. Supported: {list(_ASSET_MAP.keys())}")

        end = end_date or date.today()
        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(end, datetime.min.time()).timestamp())

        resp = await self._client.get(
            f"/coins/{cg_id}/market_chart/range",
            params={
                "vs_currency": "usd",
                "from": start_ts,
                "to": end_ts,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        prices = data.get("prices", [])
        if not prices:
            return DataResult(series=pd.Series(dtype=float), source="coingecko")

        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)

        series = df["price"]
        series.name = f"{symbol}_price_usd"

        return DataResult(
            series=series,
            metadata={"cg_id": cg_id, "frequency": frequency.value},
            source="coingecko",
        )

    async def fetch_metric(
        self,
        metric_name: str,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> DataResult:
        """
        Fetch a market metric from CoinGecko.

        Available metrics:
        - market_cap: Market capitalization in USD
        - total_volume: 24h trading volume in USD
        """
        cg_id = _ASSET_MAP.get(symbol.lower())
        if not cg_id:
            raise ValueError(f"Unsupported asset: {symbol}")

        end = end_date or date.today()
        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(end, datetime.min.time()).timestamp())

        resp = await self._client.get(
            f"/coins/{cg_id}/market_chart/range",
            params={
                "vs_currency": "usd",
                "from": start_ts,
                "to": end_ts,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        metric_key_map = {
            "market_cap": "market_caps",
            "total_volume": "total_volumes",
            "price": "prices",
        }

        key = metric_key_map.get(metric_name)
        if not key or key not in data:
            raise ValueError(
                f"Unsupported metric: {metric_name}. Available: {list(metric_key_map.keys())}"
            )

        raw = data[key]
        if not raw:
            return DataResult(series=pd.Series(dtype=float), source="coingecko")

        df = pd.DataFrame(raw, columns=["timestamp", "value"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)

        series = df["value"]
        series.name = f"{symbol}_{metric_name}"

        return DataResult(
            series=series,
            metadata={"cg_id": cg_id, "metric": metric_name},
            source="coingecko",
        )

    def supported_assets(self) -> list[str]:
        return list(_ASSET_MAP.keys())

    def supported_metrics(self) -> list[str]:
        return ["market_cap", "total_volume", "price"]

    async def close(self) -> None:
        await self._client.aclose()
