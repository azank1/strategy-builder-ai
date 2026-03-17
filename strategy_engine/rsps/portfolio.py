"""RSPS Portfolio Engine — Master orchestrator.

Combines all four modules into a final portfolio:
  Q1 TOTALES  →  market gate
  Q2 Conservative  →  asset rankings + allocation
  Q3 Trash Trend  →  alt allocation %
  Q4 Tournament  →  which alts
Then computes dollar balances and rebalance deltas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from strategy_engine.models import LTPISystem
from strategy_engine.models_rsps import (
    ConservativeAllocation,
    MiniTPI,
    RSPSConfig,
    RSPSPortfolio,
    TotalesState,
    TrashFilter,
    TrashToken,
    TrashTrendResult,
    TournamentResult,
)
from strategy_engine.rsps.conservative import ConservativeTrendModule
from strategy_engine.rsps.totales import TotalesModule
from strategy_engine.rsps.trash_tournament import TrashTournament
from strategy_engine.rsps.trash_trend import TrashTrendModule


class RSPSPortfolioEngine:
    """Orchestrate the full RSPS computation pipeline."""

    def __init__(self, config: RSPSConfig):
        self.config = config
        self.totales_mod = TotalesModule(
            entry_threshold=config.entry_threshold,
            exit_threshold=config.exit_threshold,
        )
        self.conservative_mod = ConservativeTrendModule(config)
        self.trash_trend_mod = TrashTrendModule(config)
        self.tournament_mod = TrashTournament(config)

    def compute(
        self,
        *,
        market_tpi: LTPISystem | MiniTPI | None = None,
        ratio_tpis: dict[str, MiniTPI] | None = None,
        others_tpi: MiniTPI | None = None,
        trash_tokens: list[TrashToken] | None = None,
        trash_filters: list[TrashFilter] | None = None,
        current_balances: dict[str, float] | None = None,
    ) -> RSPSPortfolio:
        """Run the full pipeline and produce a portfolio snapshot.

        All inputs are optional — modules return neutral defaults
        when their inputs are missing (allows partial evaluation).
        """
        # Q1: TOTALES — market direction gate
        totales = self._evaluate_totales(market_tpi)

        # Q2: Conservative — asset ranking
        conservative = self._evaluate_conservative(ratio_tpis)

        # Q3: Trash trend — alt allocation sizing
        trash_trend = self._evaluate_trash_trend(others_tpi)

        # Q4: Tournament — which alts
        tournament = self._evaluate_tournament(trash_tokens, trash_filters)

        # Compute dollar allocations
        balances = self._compute_balances(
            totales, conservative, trash_trend, tournament,
        )

        # Compute rebalance deltas
        deltas = self._compute_deltas(balances, current_balances or {})

        return RSPSPortfolio(
            config=self.config,
            totales=totales,
            conservative=conservative,
            trash_trend=trash_trend,
            trash_selection=tournament,
            balances=balances,
            rebalance_deltas=deltas,
            computed_at=datetime.now(),
        )

    # ── Module evaluations ─────────────────────────────────────────────────

    def _evaluate_totales(
        self, market_tpi: LTPISystem | MiniTPI | None,
    ) -> TotalesState:
        if market_tpi is None:
            return TotalesState(is_long=True, score=0.0)
        if isinstance(market_tpi, LTPISystem):
            return self.totales_mod.evaluate_from_ltpi(market_tpi)
        return self.totales_mod.evaluate_from_mini_tpi(market_tpi)

    def _evaluate_conservative(
        self, ratio_tpis: dict[str, MiniTPI] | None,
    ) -> ConservativeAllocation:
        if ratio_tpis is None:
            n = len(self.config.conservative_assets)
            equal = round(1.0 / n, 4) if n > 0 else 0.0
            allocs = {a: equal for a in self.config.conservative_assets}
            # Fix rounding
            if allocs:
                diff = round(1.0 - sum(allocs.values()), 4)
                if diff != 0:
                    first = next(iter(allocs))
                    allocs[first] = round(allocs[first] + diff, 4)
            return ConservativeAllocation(
                allocations=allocs,
                rankings={a: 0 for a in self.config.conservative_assets},
            )
        return self.conservative_mod.evaluate(ratio_tpis)

    def _evaluate_trash_trend(
        self, others_tpi: MiniTPI | None,
    ) -> TrashTrendResult:
        if others_tpi is None:
            return TrashTrendResult(strength=0.0, allocation_pct=0.0)
        return self.trash_trend_mod.evaluate(others_tpi)

    def _evaluate_tournament(
        self,
        tokens: list[TrashToken] | None,
        filters: list[TrashFilter] | None,
    ) -> TournamentResult:
        if tokens is None or filters is None:
            return TournamentResult()
        return self.tournament_mod.evaluate(tokens, filters)

    # ── Dollar allocation ──────────────────────────────────────────────────

    def _compute_balances(
        self,
        totales: TotalesState,
        conservative: ConservativeAllocation,
        trash_trend: TrashTrendResult,
        tournament: TournamentResult,
    ) -> dict[str, float]:
        """Convert percentages to dollar amounts.

        Total capital splits into:
          - Conservative portion: (1 - trash_allocation_pct) × capital
          - Trash portion: trash_allocation_pct × capital

        If TOTALES is NOT-LONG, apply not_long_reduction factor.
        """
        capital = self.config.total_capital
        reduction = 1.0 if totales.is_long else self.config.not_long_reduction
        effective_capital = capital * reduction

        trash_pct = trash_trend.allocation_pct
        conservative_capital = effective_capital * (1.0 - trash_pct)
        trash_capital = effective_capital * trash_pct

        balances: dict[str, float] = {}

        # Conservative assets
        for asset, pct in conservative.allocations.items():
            balances[asset] = round(conservative_capital * pct, 2)

        # Trash tokens
        for ticker, pct in tournament.allocations.items():
            balances[ticker] = round(trash_capital * pct, 2)

        # Cash (if reduced)
        cash = round(capital - effective_capital, 2)
        if cash > 0:
            balances["CASH"] = cash

        return balances

    def _compute_deltas(
        self,
        target: dict[str, float],
        current: dict[str, float],
    ) -> dict[str, float]:
        """Compute the difference between target and current balances."""
        all_assets = set(target.keys()) | set(current.keys())
        deltas: dict[str, float] = {}
        for asset in all_assets:
            t = target.get(asset, 0.0)
            c = current.get(asset, 0.0)
            delta = round(t - c, 2)
            if delta != 0:
                deltas[asset] = delta
        return deltas
