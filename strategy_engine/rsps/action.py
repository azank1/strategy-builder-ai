"""Action Summary — Adler-inspired headline action generator.

Takes the full RSPS portfolio and produces a single-sentence action
with specific moves, similar to Adler's weekly playbook.
"""

from __future__ import annotations

from strategy_engine.models_rsps import (
    ActionSummary,
    HeadlineAction,
    Move,
    RSPSPortfolio,
)


def compute_action_summary(
    portfolio: RSPSPortfolio,
    previous_balances: dict[str, float] | None = None,
) -> ActionSummary:
    """Derive the headline action and specific moves from a portfolio.

    Logic:
    - EXIT: TOTALES is NOT-LONG and score < exit_threshold
    - REDUCE: TOTALES is NOT-LONG but score ≥ exit_threshold
    - ACCUMULATE: TOTALES is LONG and previous had CASH or was underweight
    - REBALANCE: TOTALES is LONG and allocations shifted significantly
    - HOLD: TOTALES is LONG and no meaningful delta
    """
    prev = previous_balances or {}
    deltas = portfolio.rebalance_deltas
    totales = portfolio.totales
    config = portfolio.config

    # Determine headline
    if not totales.is_long and totales.score < config.exit_threshold:
        headline = HeadlineAction.EXIT
    elif not totales.is_long:
        headline = HeadlineAction.REDUCE
    elif _has_significant_rebalance(deltas, config.total_capital):
        if prev.get("CASH", 0) > config.total_capital * 0.1:
            headline = HeadlineAction.ACCUMULATE
        else:
            headline = HeadlineAction.REBALANCE
    else:
        headline = HeadlineAction.HOLD

    # Build specific moves
    moves = _build_moves(deltas, prev)

    # Net direction
    total_delta = sum(v for k, v in deltas.items() if k != "CASH")
    if total_delta > 0:
        net_direction = "risk-on"
    elif total_delta < 0:
        net_direction = "risk-off"
    else:
        net_direction = "neutral"

    return ActionSummary(
        headline=headline,
        specific_moves=moves,
        net_direction=net_direction,
        estimated_trades=len(moves),
    )


def _has_significant_rebalance(deltas: dict[str, float], capital: float) -> bool:
    """Check if any delta exceeds 2% of capital."""
    threshold = capital * 0.02
    return any(abs(v) > threshold for v in deltas.values())


def _build_moves(
    deltas: dict[str, float],
    prev: dict[str, float],
) -> list[Move]:
    """Convert deltas to Move objects."""
    moves: list[Move] = []
    for asset, delta in deltas.items():
        if asset == "CASH":
            continue
        if abs(delta) < 0.01:
            continue

        was_held = prev.get(asset, 0) > 0
        if delta > 0:
            direction = "increase" if was_held else "add"
        else:
            remaining = prev.get(asset, 0) + delta
            direction = "decrease" if remaining > 0.01 else "exit"

        moves.append(Move(
            asset=asset,
            direction=direction,
            amount=abs(round(delta, 2)),
        ))

    # Sort: exits first, then decreases, then increases, then adds
    order = {"exit": 0, "decrease": 1, "increase": 2, "add": 3}
    moves.sort(key=lambda m: order.get(m.direction, 4))
    return moves
