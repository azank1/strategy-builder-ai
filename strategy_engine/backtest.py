"""
RSPS Backtest Engine — historical simulation of portfolio performance.

Simulates the RSPS allocation process over historical data, computing
returns, drawdown, and allocation metrics at each rebalance point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    """Configuration for an RSPS backtest run."""

    start_date: date
    end_date: date
    initial_capital: float = 10000.0
    rebalance_frequency: str = "1W"  # "1D", "1W", "2W", "1M"
    transaction_cost_bps: float = 10.0  # 10 bps = 0.1%
    slippage_bps: float = 5.0


@dataclass
class BacktestTrade:
    """A single rebalance trade."""

    date: date
    asset: str
    side: str  # "buy" or "sell"
    amount: float  # dollar amount
    cost: float  # transaction cost


@dataclass
class BacktestSnapshot:
    """Portfolio state at a single point in time."""

    date: date
    portfolio_value: float
    allocations: dict[str, float]  # asset → dollar value
    weights: dict[str, float]  # asset → pct weight
    trades: list[BacktestTrade] = field(default_factory=list)


@dataclass
class BacktestResult:
    """Full backtest output."""

    config: BacktestConfig
    snapshots: list[BacktestSnapshot]
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    total_trades: int
    total_cost: float
    equity_curve: pd.Series  # date → portfolio value

    @property
    def n_rebalances(self) -> int:
        return len(self.snapshots)


class RSPSBacktester:
    """Run RSPS backtest over historical price data.

    Example:
        bt = RSPSBacktester(config)
        result = bt.run(price_data, allocation_fn)
        print(f"Return: {result.total_return:.2%}")
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cost_rate = (config.transaction_cost_bps + config.slippage_bps) / 10000

    def run(
        self,
        prices: dict[str, pd.Series],
        allocation_fn: callable,
    ) -> BacktestResult:
        """Run a backtest.

        Args:
            prices: Mapping of asset → pd.Series (date-indexed close prices).
            allocation_fn: Function(date, prices_up_to_date) → dict[str, float]
                          Returns target weights (asset → 0.0-1.0).

        Returns:
            BacktestResult with full performance metrics.
        """
        # Align all price series to common date range
        price_df = pd.DataFrame(prices)
        price_df = price_df.loc[
            str(self.config.start_date):str(self.config.end_date)
        ].dropna()

        if price_df.empty:
            raise ValueError("No price data available for the specified date range")

        rebalance_dates = self._get_rebalance_dates(price_df.index)
        capital = self.config.initial_capital
        holdings: dict[str, float] = {}  # asset → number of units
        snapshots: list[BacktestSnapshot] = []
        all_trades: list[BacktestTrade] = []
        equity_values: list[float] = []
        equity_dates: list = []
        total_cost = 0.0

        for dt in price_df.index:
            current_date = dt.date() if hasattr(dt, "date") else dt
            current_prices = price_df.loc[dt]

            # Compute current portfolio value
            port_value = sum(
                holdings.get(asset, 0.0) * current_prices[asset]
                for asset in price_df.columns
                if asset in current_prices and not np.isnan(current_prices[asset])
            )
            if not holdings:
                port_value = capital

            equity_values.append(port_value)
            equity_dates.append(dt)

            # Rebalance if on a rebalance date
            if dt in rebalance_dates:
                prices_so_far = price_df.loc[:dt]
                target_weights = allocation_fn(current_date, prices_so_far)

                trades, cost = self._rebalance(
                    holdings, target_weights, current_prices, port_value, current_date
                )
                total_cost += cost
                all_trades.extend(trades)

                # Compute allocations
                allocations = {
                    asset: holdings.get(asset, 0.0) * current_prices.get(asset, 0.0)
                    for asset in price_df.columns
                }
                weights = {
                    asset: v / max(port_value, 1e-10)
                    for asset, v in allocations.items()
                }

                snapshots.append(BacktestSnapshot(
                    date=current_date,
                    portfolio_value=round(port_value, 2),
                    allocations={k: round(v, 2) for k, v in allocations.items()},
                    weights={k: round(v, 4) for k, v in weights.items()},
                    trades=trades,
                ))

        equity = pd.Series(equity_values, index=equity_dates, name="equity")

        # Performance metrics
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1 if len(equity) > 1 else 0.0
        days = (equity.index[-1] - equity.index[0]).days if len(equity) > 1 else 1
        ann_return = (1 + total_return) ** (365 / max(days, 1)) - 1
        max_dd = self._max_drawdown(equity)
        sharpe = self._sharpe_ratio(equity)

        return BacktestResult(
            config=self.config,
            snapshots=snapshots,
            total_return=round(total_return, 6),
            annualized_return=round(ann_return, 6),
            max_drawdown=round(max_dd, 6),
            sharpe_ratio=round(sharpe, 4),
            total_trades=len(all_trades),
            total_cost=round(total_cost, 2),
            equity_curve=equity,
        )

    # ── Internals ──────────────────────────────────────────────────────────

    def _get_rebalance_dates(self, index: pd.DatetimeIndex) -> set:
        """Select rebalance dates from the data index."""
        freq = self.config.rebalance_frequency
        mapping = {"1D": "D", "1W": "W", "2W": "2W", "1M": "ME"}
        rule = mapping.get(freq, "W")

        # Resample to get period boundaries, pick the last date in each period
        dummy = pd.Series(1, index=index)
        boundaries = dummy.resample(rule).last().index
        return set(index) & set(boundaries)

    def _rebalance(
        self,
        holdings: dict[str, float],
        target_weights: dict[str, float],
        prices: pd.Series,
        portfolio_value: float,
        current_date: date,
    ) -> tuple[list[BacktestTrade], float]:
        """Execute rebalance trades."""
        trades: list[BacktestTrade] = []
        total_cost = 0.0

        for asset, target_w in target_weights.items():
            if asset not in prices or np.isnan(prices[asset]):
                continue

            price = prices[asset]
            target_value = portfolio_value * target_w
            current_value = holdings.get(asset, 0.0) * price
            delta = target_value - current_value

            if abs(delta) < 1.0:  # Skip trivial trades
                continue

            cost = abs(delta) * self.cost_rate
            total_cost += cost

            # Adjust for cost
            if delta > 0:
                actual_delta = delta - cost
                side = "buy"
            else:
                actual_delta = delta + cost
                side = "sell"

            holdings[asset] = holdings.get(asset, 0.0) + actual_delta / price

            trades.append(BacktestTrade(
                date=current_date,
                asset=asset,
                side=side,
                amount=round(abs(delta), 2),
                cost=round(cost, 2),
            ))

        return trades, total_cost

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        """Compute maximum drawdown from equity curve."""
        if len(equity) < 2:
            return 0.0
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak
        return float(abs(drawdown.min()))

    @staticmethod
    def _sharpe_ratio(equity: pd.Series, risk_free: float = 0.0) -> float:
        """Compute annualized Sharpe ratio."""
        if len(equity) < 10:
            return 0.0
        returns = equity.pct_change().dropna()
        if returns.std() < 1e-10:
            return 0.0
        excess = returns.mean() - risk_free / 252
        return float(excess / returns.std() * np.sqrt(252))
