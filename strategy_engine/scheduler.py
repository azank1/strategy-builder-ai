"""
Auto-refresh scheduler — daily recomputation of RSPS portfolios.

Uses asyncio scheduling (no external deps like Celery/APScheduler).
Designed to be started from FastAPI lifespan or run standalone.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Callable, Awaitable, Any

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """A single scheduled job definition."""

    name: str
    callback: Callable[..., Awaitable[Any]]
    run_time: time  # UTC time of day to run
    enabled: bool = True
    last_run: datetime | None = None
    last_status: str = "never"
    run_count: int = 0


@dataclass
class SchedulerState:
    """Observable state for health checks."""

    running: bool = False
    jobs: list[ScheduledJob] = field(default_factory=list)
    started_at: datetime | None = None


class DailyScheduler:
    """Lightweight daily scheduler using asyncio.

    Example:
        scheduler = DailyScheduler()
        scheduler.add_job("rsps_refresh", my_async_fn, time(6, 0))
        await scheduler.start()  # runs until cancelled
    """

    def __init__(self):
        self.state = SchedulerState()
        self._task: asyncio.Task | None = None

    def add_job(
        self,
        name: str,
        callback: Callable[..., Awaitable[Any]],
        run_time: time,
        enabled: bool = True,
    ) -> None:
        """Register a daily job."""
        job = ScheduledJob(name=name, callback=callback, run_time=run_time, enabled=enabled)
        self.state.jobs.append(job)

    async def start(self) -> None:
        """Start the scheduler loop. Blocks until stop() is called."""
        self.state.running = True
        self.state.started_at = datetime.now(timezone.utc)
        logger.info("Scheduler started with %d jobs", len(self.state.jobs))

        try:
            while self.state.running:
                now = datetime.now(timezone.utc)

                for job in self.state.jobs:
                    if not job.enabled:
                        continue
                    if self._should_run(job, now):
                        await self._execute(job)

                # Sleep until next minute boundary
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Scheduler cancelled")
        finally:
            self.state.running = False

    def stop(self) -> None:
        """Signal the scheduler to stop."""
        self.state.running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def start_background(self) -> asyncio.Task:
        """Start the scheduler as a background task."""
        self._task = asyncio.create_task(self.start())
        return self._task

    @staticmethod
    def _should_run(job: ScheduledJob, now: datetime) -> bool:
        """Check if a job should run based on current time and last run."""
        # Match current hour and minute
        if now.hour != job.run_time.hour or now.minute != job.run_time.minute:
            return False
        # Don't re-run within the same minute
        if job.last_run and (now - job.last_run) < timedelta(minutes=2):
            return False
        return True

    @staticmethod
    async def _execute(job: ScheduledJob) -> None:
        """Execute a job with error handling."""
        logger.info("Running job: %s", job.name)
        try:
            await job.callback()
            job.last_status = "success"
            logger.info("Job %s completed", job.name)
        except Exception:
            job.last_status = "error"
            logger.exception("Job %s failed", job.name)
        finally:
            job.last_run = datetime.now(timezone.utc)
            job.run_count += 1


# ── Pre-built RSPS refresh job ────────────────────────────────────────────────


async def rsps_daily_refresh() -> None:
    """Placeholder for daily RSPS portfolio refresh.

    In production this would:
    1. Query all active users with RSPS systems.
    2. Fetch fresh price data via DataAdapter.
    3. Recompute each portfolio via RSPSPortfolioEngine.
    4. Store snapshots in the decision_snapshots table.
    5. Trigger alerts for significant allocation changes.
    """
    logger.info("RSPS daily refresh — stub (wire to DB when ready)")


def create_default_scheduler() -> DailyScheduler:
    """Create a scheduler with default RSPS refresh job at 06:00 UTC."""
    scheduler = DailyScheduler()
    scheduler.add_job(
        name="rsps_daily_refresh",
        callback=rsps_daily_refresh,
        run_time=time(6, 0),
    )
    return scheduler
