"""Forward Watch — distance-to-flip computation.

For each TPI indicator, computes how close the indicator is to flipping
its score, producing triggers that warn the user of impending changes.
"""

from __future__ import annotations

from strategy_engine.models_rsps import (
    MiniTPI,
    RSPSConfig,
    RSPSPortfolio,
    Trigger,
)


def compute_forward_watch(
    portfolio: RSPSPortfolio,
    ratio_tpis: dict[str, MiniTPI] | None = None,
    others_tpi: MiniTPI | None = None,
) -> list[Trigger]:
    """Compute forward-watch triggers for proximity to regime changes.

    Three types of triggers:
    1. TOTALES proximity to entry/exit thresholds
    2. Conservative ratio TPI flip (majority direction change)
    3. Trash trend proximity to activation/deactivation
    """
    triggers: list[Trigger] = []
    config = portfolio.config

    # T1: TOTALES proximity
    triggers.extend(_totales_triggers(portfolio))

    # T2: Conservative ratio flips
    if ratio_tpis:
        triggers.extend(_conservative_triggers(ratio_tpis))

    # T3: Trash trend proximity
    if others_tpi:
        triggers.extend(_trash_trend_triggers(others_tpi, config))

    return triggers


def _totales_triggers(portfolio: RSPSPortfolio) -> list[Trigger]:
    config = portfolio.config
    score = portfolio.totales.score
    triggers: list[Trigger] = []

    if portfolio.totales.is_long:
        # Distance to exit
        dist = score - config.exit_threshold
        if dist > 0:
            pct = min(100.0, round((1.0 - dist / max(abs(score), 0.001)) * 100, 1))
        else:
            pct = 100.0
        triggers.append(Trigger(
            module="totales",
            condition="score drops below exit threshold",
            current_value=round(score, 4),
            flip_value=config.exit_threshold,
            distance_pct=max(0.0, min(100.0, pct)),
            impact="Portfolio shifts to NOT-LONG, reduces exposure",
        ))
    else:
        # Distance to entry
        dist = config.entry_threshold - score
        if dist > 0:
            pct = min(100.0, round((1.0 - dist / max(config.entry_threshold, 0.001)) * 100, 1))
        else:
            pct = 100.0
        triggers.append(Trigger(
            module="totales",
            condition="score rises above entry threshold",
            current_value=round(score, 4),
            flip_value=config.entry_threshold,
            distance_pct=max(0.0, min(100.0, pct)),
            impact="Portfolio shifts to LONG, increases exposure",
        ))

    return triggers


def _conservative_triggers(ratio_tpis: dict[str, MiniTPI]) -> list[Trigger]:
    """Check each ratio TPI for proximity to flipping direction."""
    triggers: list[Trigger] = []

    for key, tpi in ratio_tpis.items():
        avg = tpi.average_score
        if not tpi.indicators:
            continue

        # Count how many indicators would need to flip to cross zero
        n = len(tpi.indicators)
        scores = [i.effective_score for i in tpi.indicators]
        positive = sum(1 for s in scores if s > 0)
        negative = sum(1 for s in scores if s < 0)

        if avg > 0:
            flips_needed = positive - n // 2
            pct = round((1.0 - flips_needed / max(n, 1)) * 100, 1)
            triggers.append(Trigger(
                module="conservative",
                condition=f"{key} flips from positive to negative",
                current_value=round(avg, 4),
                flip_value=0.0,
                distance_pct=max(0.0, min(100.0, pct)),
                impact=f"Asset ranking changes — {key} reverses",
            ))
        elif avg < 0:
            flips_needed = negative - n // 2
            pct = round((1.0 - flips_needed / max(n, 1)) * 100, 1)
            triggers.append(Trigger(
                module="conservative",
                condition=f"{key} flips from negative to positive",
                current_value=round(avg, 4),
                flip_value=0.0,
                distance_pct=max(0.0, min(100.0, pct)),
                impact=f"Asset ranking changes — {key} reverses",
            ))

    return triggers


def _trash_trend_triggers(others_tpi: MiniTPI, config: RSPSConfig) -> list[Trigger]:
    """Check OTHERS.D proximity to activating/deactivating trash allocation."""
    if not others_tpi.indicators:
        return []

    avg = others_tpi.average_score
    n = len(others_tpi.indicators)
    bullish = sum(1 for i in others_tpi.indicators if i.effective_score > 0)

    # Distance to flipping majority
    majority = n // 2 + 1
    if avg > 0.5:
        flips_to_neutral = bullish - n // 2
        pct = round((1.0 - flips_to_neutral / max(n, 1)) * 100, 1)
        triggers = [Trigger(
            module="trash_trend",
            condition="OTHERS.D trend weakens — trash allocation decreases",
            current_value=round(avg, 4),
            flip_value=0.5,
            distance_pct=max(0.0, min(100.0, pct)),
            impact=f"Trash allocation drops from {config.max_trash_pct * avg:.1%}",
        )]
    else:
        flips_to_bullish = majority - bullish
        pct = round((1.0 - flips_to_bullish / max(n, 1)) * 100, 1)
        triggers = [Trigger(
            module="trash_trend",
            condition="OTHERS.D trend strengthens — trash allocation increases",
            current_value=round(avg, 4),
            flip_value=0.5,
            distance_pct=max(0.0, min(100.0, pct)),
            impact=f"Trash allocation increases toward {config.max_trash_pct:.1%}",
        )]

    return triggers
