"""Divergence Veto — cross-module agreement scoring.

When modules disagree (e.g. TOTALES is bullish but conservative rankings
are bearish), the divergence score rises. Above the veto threshold,
risk is automatically reduced.
"""

from __future__ import annotations

from strategy_engine.models_rsps import (
    DivergenceResult,
    RSPSConfig,
    RSPSPortfolio,
)


def compute_divergence(
    portfolio: RSPSPortfolio,
) -> DivergenceResult:
    """Measure cross-module disagreement.

    Signals compared:
    1. TOTALES direction vs conservative allocation concentration
    2. TOTALES direction vs trash trend strength
    3. Conservative concentration vs trash trend direction
    4. Trash trend vs tournament qualification rate

    Each pair produces a 0–1 divergence score. Final score is the average.
    """
    config = portfolio.config
    details: dict[str, float] = {}

    # S1: TOTALES vs Conservative concentration
    details["totales_vs_conservative"] = _totales_vs_conservative(portfolio)

    # S2: TOTALES vs Trash trend
    details["totales_vs_trash_trend"] = _totales_vs_trash(portfolio)

    # S3: Conservative vs Trash trend
    details["conservative_vs_trash"] = _conservative_vs_trash(portfolio)

    # S4: Trash trend vs Tournament
    details["trash_trend_vs_tournament"] = _trash_trend_vs_tournament(portfolio)

    # Average divergence
    scores = list(details.values())
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    veto_active = avg_score > config.divergence_veto_threshold
    reduction = 1.0
    if veto_active:
        # Linear reduction: at threshold=0.6, score=0.8 ⇒ factor ~ 0.5
        excess = avg_score - config.divergence_veto_threshold
        remaining = 1.0 - config.divergence_veto_threshold
        reduction = max(0.2, round(1.0 - (excess / max(remaining, 0.01)), 4))

    return DivergenceResult(
        score=avg_score,
        details=details,
        veto_active=veto_active,
        risk_reduction_factor=reduction,
    )


def _totales_vs_conservative(portfolio: RSPSPortfolio) -> float:
    """High divergence if TOTALES is bearish but conservative is concentrated."""
    totales_bullish = portfolio.totales.is_long
    allocs = list(portfolio.conservative.allocations.values())
    if not allocs:
        return 0.0

    # Concentration: how far from equal-weight (Herfindahl-like)
    n = len(allocs)
    equal = 1.0 / n
    concentration = sum((a - equal) ** 2 for a in allocs) / n
    max_conc = (1.0 - equal) ** 2  # max possible concentration
    norm_conc = concentration / max_conc if max_conc > 0 else 0.0

    if totales_bullish:
        # Bullish + concentrated = aligned, low divergence
        return round(0.2 * norm_conc, 4)
    else:
        # Bearish + concentrated = divergent
        return round(0.5 + 0.5 * norm_conc, 4)


def _totales_vs_trash(portfolio: RSPSPortfolio) -> float:
    """High divergence if TOTALES is bearish but trash trend is strong."""
    totales_bullish = portfolio.totales.is_long
    trash_strength = portfolio.trash_trend.strength

    if totales_bullish and trash_strength > 0.5:
        return 0.0  # Both bullish → aligned
    if not totales_bullish and trash_strength < 0.3:
        return 0.0  # Both cautious → aligned
    if not totales_bullish and trash_strength > 0.5:
        return round(0.5 + 0.5 * trash_strength, 4)  # Divergent
    if totales_bullish and trash_strength < 0.2:
        return round(0.3, 4)  # Mild divergence — bullish but alts weak

    return round(abs(trash_strength - (1.0 if totales_bullish else 0.0)) * 0.5, 4)


def _conservative_vs_trash(portfolio: RSPSPortfolio) -> float:
    """Divergence if conservative is risk-off but trash is risk-on."""
    max_alloc = max(portfolio.conservative.allocations.values()) if portfolio.conservative.allocations else 0
    trash_strength = portfolio.trash_trend.strength

    # If BTC is dominant (risk-off signal) but trash is bullish
    btc_alloc = portfolio.conservative.allocations.get("BTC", 0)
    if btc_alloc > 0.7 and trash_strength > 0.6:
        return round(0.6, 4)
    if btc_alloc < 0.3 and trash_strength > 0.6:
        return round(0.1, 4)  # Both risk-on → aligned

    return round(abs(btc_alloc - 0.5) * trash_strength, 4)


def _trash_trend_vs_tournament(portfolio: RSPSPortfolio) -> float:
    """Divergence if trash trend says buy but no tokens qualify."""
    strength = portfolio.trash_trend.strength
    n_qualifiers = len(portfolio.trash_selection.qualifying_tokens)
    n_total = len(portfolio.trash_selection.all_tokens)

    if strength < 0.3:
        return 0.0  # Trash trend weak, doesn't matter

    if n_total == 0:
        return round(0.5 * strength, 4)  # No tokens to evaluate

    qual_rate = n_qualifiers / n_total
    if strength > 0.6 and qual_rate < 0.2:
        return round(0.7, 4)  # Bullish trend but few qualify
    if strength > 0.6 and qual_rate > 0.5:
        return round(0.1, 4)  # Aligned

    return round(abs(strength - qual_rate) * 0.5, 4)
