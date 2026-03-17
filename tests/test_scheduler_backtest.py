"""Tests for scheduler and backtest engine."""

import asyncio
from datetime import date, time, datetime, timezone, timedelta

import numpy as np
import pandas as pd
import pytest

from strategy_engine.scheduler import (
    DailyScheduler,
    ScheduledJob,
    create_default_scheduler,
)
from strategy_engine.backtest import (
    RSPSBacktester,
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
)


# ── Scheduler Tests ──────────────────────────────────────────────────────────


class TestDailyScheduler:
    def test_add_job(self):
        scheduler = DailyScheduler()

        async def noop():
            pass

        scheduler.add_job("test_job", noop, time(6, 0))
        assert len(scheduler.state.jobs) == 1
        assert scheduler.state.jobs[0].name == "test_job"

    def test_should_run_matching_time(self):
        async def noop():
            pass

        job = ScheduledJob(name="t", callback=noop, run_time=time(10, 30))
        now = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        assert DailyScheduler._should_run(job, now)

    def test_should_not_run_wrong_time(self):
        async def noop():
            pass

        job = ScheduledJob(name="t", callback=noop, run_time=time(10, 30))
        now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        assert not DailyScheduler._should_run(job, now)

    def test_should_not_rerun_within_minute(self):
        async def noop():
            pass

        now = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        job = ScheduledJob(
            name="t", callback=noop, run_time=time(10, 30),
            last_run=now - timedelta(seconds=30),
        )
        assert not DailyScheduler._should_run(job, now)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        called = []

        async def callback():
            called.append(True)

        job = ScheduledJob(name="t", callback=callback, run_time=time(0, 0))
        await DailyScheduler._execute(job)
        assert len(called) == 1
        assert job.last_status == "success"
        assert job.run_count == 1

    @pytest.mark.asyncio
    async def test_execute_error_handled(self):
        async def failing():
            raise RuntimeError("boom")

        job = ScheduledJob(name="fail", callback=failing, run_time=time(0, 0))
        await DailyScheduler._execute(job)
        assert job.last_status == "error"
        assert job.run_count == 1

    def test_create_default_scheduler(self):
        scheduler = create_default_scheduler()
        assert len(scheduler.state.jobs) == 1
        assert scheduler.state.jobs[0].name == "rsps_daily_refresh"

    def test_stop(self):
        scheduler = DailyScheduler()
        scheduler.state.running = True
        scheduler.stop()
        assert scheduler.state.running is False


# ── Backtest Tests ───────────────────────────────────────────────────────────


def _make_prices(n: int = 252, assets: list[str] | None = None, seed: int = 42) -> dict[str, pd.Series]:
    """Generate synthetic price series."""
    rng = np.random.RandomState(seed)
    assets = assets or ["BTC", "ETH"]
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    prices = {}
    for asset in assets:
        returns = rng.normal(0.0005, 0.02, n)
        price = 100 * np.cumprod(1 + returns)
        prices[asset] = pd.Series(price, index=dates, name=asset)
    return prices


def _equal_weight_fn(dt, prices_df):
    """Simple equal-weight allocation."""
    n = len(prices_df.columns)
    return {col: 1.0 / n for col in prices_df.columns}


class TestRSPSBacktester:
    def test_basic_backtest(self):
        prices = _make_prices()
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) > 0
        assert result.n_rebalances > 0
        assert result.total_trades > 0

    def test_returns_computed(self):
        prices = _make_prices()
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        # Total return should be a reasonable number (not zero)
        assert result.total_return != 0.0
        assert -1.0 < result.total_return < 10.0

    def test_max_drawdown_computed(self):
        prices = _make_prices()
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert 0.0 <= result.max_drawdown <= 1.0

    def test_sharpe_computed(self):
        prices = _make_prices()
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert isinstance(result.sharpe_ratio, float)

    def test_transaction_costs_applied(self):
        prices = _make_prices()
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            transaction_cost_bps=10.0,
            slippage_bps=5.0,
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert result.total_cost > 0

    def test_multiple_assets(self):
        prices = _make_prices(assets=["BTC", "ETH", "SOL", "GOLD"])
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert result.n_rebalances > 0

    def test_daily_rebalance(self):
        prices = _make_prices(n=30)
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 30),
            rebalance_frequency="1D",
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert result.n_rebalances > 10  # Should have many daily rebalances

    def test_custom_allocation(self):
        prices = _make_prices()

        def btc_only(dt, df):
            return {"BTC": 1.0, "ETH": 0.0}

        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, btc_only)

        # Should have snapshots where ETH weight is ~0
        for snap in result.snapshots[-3:]:
            assert snap.weights.get("ETH", 0) < 0.05

    def test_equity_curve_length(self):
        prices = _make_prices(n=100)
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 4, 10),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        assert len(result.equity_curve) == 100

    def test_empty_date_range_raises(self):
        prices = _make_prices(n=100)
        config = BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        bt = RSPSBacktester(config)
        with pytest.raises(ValueError, match="No price data"):
            bt.run(prices, _equal_weight_fn)

    def test_snapshots_have_allocations(self):
        prices = _make_prices()
        config = BacktestConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        bt = RSPSBacktester(config)
        result = bt.run(prices, _equal_weight_fn)

        for snap in result.snapshots:
            assert len(snap.allocations) > 0
            assert len(snap.weights) > 0
