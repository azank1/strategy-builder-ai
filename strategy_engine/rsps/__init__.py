"""RSPS — Relative Strength Portfolio System (Level 4)."""

from strategy_engine.rsps.totales import TotalesModule
from strategy_engine.rsps.conservative import ConservativeTrendModule
from strategy_engine.rsps.trash_trend import TrashTrendModule
from strategy_engine.rsps.trash_tournament import TrashTournament
from strategy_engine.rsps.portfolio import RSPSPortfolioEngine
from strategy_engine.rsps.validation import RSPSValidator
from strategy_engine.rsps.action import compute_action_summary
from strategy_engine.rsps.forward_watch import compute_forward_watch
from strategy_engine.rsps.divergence import compute_divergence

__all__ = [
    "TotalesModule",
    "ConservativeTrendModule",
    "TrashTrendModule",
    "TrashTournament",
    "RSPSPortfolioEngine",
    "RSPSValidator",
    "compute_action_summary",
    "compute_forward_watch",
    "compute_divergence",
]
