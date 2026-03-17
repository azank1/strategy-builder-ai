"""RSPS routes — Level 4 portfolio construction endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import get_current_user
from api.db_models import User

from strategy_engine.models import TrendDirection
from strategy_engine.models_rsps import (
    ActionSummary,
    AllocationStyle,
    ConservativeAllocation,
    DivergenceResult,
    HeadlineAction,
    MiniTPI,
    MiniTPIIndicator,
    Move,
    RSPSConfig,
    RSPSPortfolio,
    TotalesState,
    TrashFilter,
    TrashToken,
    TrashTrendResult,
    Trigger,
    TournamentResult,
)
from strategy_engine.rsps import (
    RSPSPortfolioEngine,
    RSPSValidator,
    compute_action_summary,
    compute_forward_watch,
    compute_divergence,
)

router = APIRouter(prefix="/rsps", tags=["rsps"])


# ═══════════════════════════════════════════════════════════════════════════════
# Request / Response schemas
# ═══════════════════════════════════════════════════════════════════════════════


class RSPSComputeRequest(BaseModel):
    """Full RSPS computation request."""

    config: RSPSConfig
    market_tpi: Optional[MiniTPI] = Field(
        None, description="TOTALES market mini-TPI (for auto-scoring)"
    )
    ratio_tpis: dict[str, MiniTPI] = Field(
        default_factory=dict,
        description="Ratio pair → mini-TPI, e.g. {'BTC/ETH': ...}",
    )
    others_tpi: Optional[MiniTPI] = Field(
        None, description="OTHERS.D dominance mini-TPI for trash trend",
    )
    trash_filters: list[TrashFilter] = Field(default_factory=list)
    trash_tokens: list[TrashToken] = Field(default_factory=list)
    previous_portfolio: Optional[dict[str, float]] = Field(
        None, description="Previous portfolio balances for delta calculation"
    )


class RSPSComputeResponse(BaseModel):
    portfolio: RSPSPortfolio
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class RSPSValidateRequest(BaseModel):
    config: RSPSConfig
    ratio_tpis: dict[str, MiniTPI] = Field(default_factory=dict)
    others_tpi: Optional[MiniTPI] = None
    trash_filters: list[TrashFilter] = Field(default_factory=list)
    trash_tokens: list[TrashToken] = Field(default_factory=list)


class RSPSValidateResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class ActionResponse(BaseModel):
    headline: HeadlineAction
    specific_moves: list[Move]
    net_direction: str
    estimated_trades: int


class ForwardWatchResponse(BaseModel):
    triggers: list[Trigger]
    count: int


class DivergenceResponse(BaseModel):
    score: float
    details: dict[str, float]
    veto_active: bool
    risk_reduction_factor: float


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _compute_portfolio(body: RSPSComputeRequest) -> RSPSPortfolio:
    """Shared helper to compute an RSPS portfolio from request body."""
    engine = RSPSPortfolioEngine(body.config)
    portfolio = engine.compute(
        market_tpi=body.market_tpi,
        ratio_tpis=body.ratio_tpis or None,
        others_tpi=body.others_tpi,
        trash_tokens=body.trash_tokens or None,
        trash_filters=body.trash_filters or None,
        current_balances=body.previous_portfolio,
    )
    return portfolio


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/compute", response_model=RSPSComputeResponse)
async def compute_portfolio(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> RSPSComputeResponse:
    """Compute a full RSPS portfolio allocation.

    Runs all 4 questions (TOTALES, Conservative, Trash Trend, Tournament)
    and returns the complete portfolio with action summary and forward watch.
    """
    portfolio = _compute_portfolio(body)

    # Adler features
    portfolio.action_summary = compute_action_summary(
        portfolio, body.previous_portfolio
    )
    portfolio.forward_watch = compute_forward_watch(portfolio)
    portfolio.divergence = compute_divergence(portfolio)

    # Validate
    validator = RSPSValidator()
    result = validator.validate_full(
        config=body.config,
        portfolio=portfolio,
        ratio_tpis=body.ratio_tpis or None,
        others_tpi=body.others_tpi,
        filters=body.trash_filters or None,
        tokens=body.trash_tokens or None,
    )

    return RSPSComputeResponse(
        portfolio=portfolio,
        validation_errors=[e.message for e in result.errors],
        validation_warnings=[w.message for w in result.warnings],
    )


@router.post("/validate", response_model=RSPSValidateResponse)
async def validate_rsps(
    body: RSPSValidateRequest,
    _user: User = Depends(get_current_user),
) -> RSPSValidateResponse:
    """Validate RSPS configuration and inputs without computing portfolio.

    Used by the builder UI for real-time validation feedback.
    """
    results = RSPSValidator.validate_config(body.config)
    if body.ratio_tpis:
        for tpi in body.ratio_tpis.values():
            results.extend(RSPSValidator.validate_mini_tpi(tpi))
    if body.others_tpi:
        results.extend(RSPSValidator.validate_others_tpi(body.others_tpi))
    if body.trash_filters:
        results.extend(RSPSValidator.validate_filters(body.trash_filters))
    if body.trash_tokens and body.trash_filters:
        results.extend(RSPSValidator.validate_tokens(body.trash_tokens, body.trash_filters))

    error_list = [r for r in results if not r.passed and r.severity == "error"]
    warn_list = [r for r in results if not r.passed and r.severity == "warning"]

    return RSPSValidateResponse(
        is_valid=len(error_list) == 0,
        errors=[e.message for e in error_list],
        warnings=[w.message for w in warn_list],
    )


@router.post("/action", response_model=ActionResponse)
async def compute_action(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> ActionResponse:
    """Compute just the action summary for a portfolio state."""
    portfolio = _compute_portfolio(body)
    action = compute_action_summary(portfolio, body.previous_portfolio)

    return ActionResponse(
        headline=action.headline,
        specific_moves=action.specific_moves,
        net_direction=action.net_direction,
        estimated_trades=action.estimated_trades,
    )


@router.post("/watch", response_model=ForwardWatchResponse)
async def compute_watch(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> ForwardWatchResponse:
    """Compute forward-watch triggers for a portfolio state."""
    portfolio = _compute_portfolio(body)
    triggers = compute_forward_watch(portfolio)
    return ForwardWatchResponse(triggers=triggers, count=len(triggers))


@router.post("/divergence", response_model=DivergenceResponse)
async def compute_div(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> DivergenceResponse:
    """Compute divergence analysis across RSPS modules."""
    portfolio = _compute_portfolio(body)
    div = compute_divergence(portfolio)

    return DivergenceResponse(
        score=div.score,
        details=div.details,
        veto_active=div.veto_active,
        risk_reduction_factor=div.risk_reduction_factor,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Request / Response schemas
# ═══════════════════════════════════════════════════════════════════════════════


class RSPSComputeRequest(BaseModel):
    """Full RSPS computation request."""

    config: RSPSConfig
    totales_score: float = Field(..., ge=-1.0, le=1.0)
    ratio_tpis: list[MiniTPI] = Field(
        ..., min_length=1, description="Mini-TPIs for ratio pairs"
    )
    trash_indicators: list[MiniTPIIndicator] = Field(
        default_factory=list,
        description="Indicators for trash trend strength (OTHERS.D)",
    )
    trash_filters: list[TrashFilter] = Field(default_factory=list)
    trash_tokens: list[TrashToken] = Field(default_factory=list)
    previous_portfolio: Optional[dict[str, float]] = Field(
        None, description="Previous portfolio balances for delta calculation"
    )


class RSPSComputeResponse(BaseModel):
    portfolio: RSPSPortfolio
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class RSPSValidateRequest(BaseModel):
    config: RSPSConfig
    ratio_tpis: list[MiniTPI] = Field(default_factory=list)
    trash_filters: list[TrashFilter] = Field(default_factory=list)
    trash_tokens: list[TrashToken] = Field(default_factory=list)


class RSPSValidateResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class ActionResponse(BaseModel):
    headline: HeadlineAction
    specific_moves: list[Move]
    net_direction: str
    estimated_trades: int


class ForwardWatchResponse(BaseModel):
    triggers: list[Trigger]
    count: int


class DivergenceResponse(BaseModel):
    score: float
    details: dict[str, float]
    veto_active: bool
    risk_reduction_factor: float


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/compute", response_model=RSPSComputeResponse)
async def compute_portfolio(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> RSPSComputeResponse:
    """Compute a full RSPS portfolio allocation.

    Runs all 4 questions (TOTALES, Conservative, Trash Trend, Tournament)
    and returns the complete portfolio with action summary and forward watch.
    """
    config = body.config

    # Q1: TOTALES
    totales = TotalesState(
        is_long=body.totales_score > config.exit_threshold,
        score=body.totales_score,
    )

    # Q2: Conservative allocation
    conservative_mod = ConservativeTrendModule(config)
    conservative = conservative_mod.compute(body.ratio_tpis)

    # Q3: Trash trend strength
    trash_mod = TrashTrendModule(config)
    trash_trend = trash_mod.compute(body.trash_indicators)

    # Q4: Trash tournament
    tournament = TrashTournament(config)
    trash_selection = tournament.run(body.trash_filters, body.trash_tokens)

    # Build portfolio
    engine = RSPSPortfolioEngine(config)
    portfolio = engine.build(
        totales=totales,
        conservative=conservative,
        trash_trend=trash_trend,
        trash_selection=trash_selection,
    )

    # Adler features
    portfolio.action_summary = compute_action_summary(
        portfolio, body.previous_portfolio
    )
    portfolio.forward_watch = compute_forward_watch(portfolio)
    portfolio.divergence = compute_divergence(portfolio)

    # Validate
    validator = RSPSValidator()
    result = validator.validate_full(
        config=config,
        portfolio=portfolio,
        filters=body.trash_filters,
        tokens=body.trash_tokens,
    )

    return RSPSComputeResponse(
        portfolio=portfolio,
        validation_errors=[e.message for e in result.errors],
        validation_warnings=[w.message for w in result.warnings],
    )


@router.post("/validate", response_model=RSPSValidateResponse)
async def validate_rsps(
    body: RSPSValidateRequest,
    _user: User = Depends(get_current_user),
) -> RSPSValidateResponse:
    """Validate RSPS configuration and inputs without computing portfolio.

    Used by the builder UI for real-time validation feedback.
    """
    errors = RSPSValidator.validate_config(body.config)
    for tpi in body.ratio_tpis:
        errors.extend(RSPSValidator.validate_mini_tpi(tpi))
    if body.trash_filters:
        errors.extend(RSPSValidator.validate_filters(body.trash_filters))
    if body.trash_tokens and body.trash_filters:
        errors.extend(RSPSValidator.validate_tokens(body.trash_tokens, body.trash_filters))

    error_list = [r for r in errors if not r.passed and r.severity == "error"]
    warn_list = [r for r in errors if not r.passed and r.severity == "warning"]

    return RSPSValidateResponse(
        is_valid=len(error_list) == 0,
        errors=[e.message for e in error_list],
        warnings=[w.message for w in warn_list],
    )


@router.post("/action", response_model=ActionResponse)
async def compute_action(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> ActionResponse:
    """Compute just the action summary for a portfolio state.

    Lighter endpoint for displaying the headline action without
    full recomputation.
    """
    config = body.config

    totales = TotalesState(
        is_long=body.totales_score > config.exit_threshold,
        score=body.totales_score,
    )

    conservative_mod = ConservativeTrendModule(config)
    conservative = conservative_mod.compute(body.ratio_tpis)

    trash_mod = TrashTrendModule(config)
    trash_trend = trash_mod.compute(body.trash_indicators)

    tournament = TrashTournament(config)
    trash_selection = tournament.run(body.trash_filters, body.trash_tokens)

    engine = RSPSPortfolioEngine(config)
    portfolio = engine.build(
        totales=totales,
        conservative=conservative,
        trash_trend=trash_trend,
        trash_selection=trash_selection,
    )

    action = compute_action_summary(portfolio, body.previous_portfolio)

    return ActionResponse(
        headline=action.headline,
        specific_moves=action.specific_moves,
        net_direction=action.net_direction,
        estimated_trades=action.estimated_trades,
    )


@router.post("/watch", response_model=ForwardWatchResponse)
async def compute_watch(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> ForwardWatchResponse:
    """Compute forward-watch triggers for a portfolio state.

    Shows conditions that would change the current allocation plan.
    """
    config = body.config

    totales = TotalesState(
        is_long=body.totales_score > config.exit_threshold,
        score=body.totales_score,
    )

    conservative_mod = ConservativeTrendModule(config)
    conservative = conservative_mod.compute(body.ratio_tpis)

    trash_mod = TrashTrendModule(config)
    trash_trend = trash_mod.compute(body.trash_indicators)

    tournament = TrashTournament(config)
    trash_selection = tournament.run(body.trash_filters, body.trash_tokens)

    engine = RSPSPortfolioEngine(config)
    portfolio = engine.build(
        totales=totales,
        conservative=conservative,
        trash_trend=trash_trend,
        trash_selection=trash_selection,
    )

    triggers = compute_forward_watch(portfolio)

    return ForwardWatchResponse(triggers=triggers, count=len(triggers))


@router.post("/divergence", response_model=DivergenceResponse)
async def compute_div(
    body: RSPSComputeRequest,
    _user: User = Depends(get_current_user),
) -> DivergenceResponse:
    """Compute divergence analysis across RSPS modules.

    Returns a score from 0 (full agreement) to 1 (full divergence),
    with per-module-pair breakdowns.
    """
    config = body.config

    totales = TotalesState(
        is_long=body.totales_score > config.exit_threshold,
        score=body.totales_score,
    )

    conservative_mod = ConservativeTrendModule(config)
    conservative = conservative_mod.compute(body.ratio_tpis)

    trash_mod = TrashTrendModule(config)
    trash_trend = trash_mod.compute(body.trash_indicators)

    tournament = TrashTournament(config)
    trash_selection = tournament.run(body.trash_filters, body.trash_tokens)

    engine = RSPSPortfolioEngine(config)
    portfolio = engine.build(
        totales=totales,
        conservative=conservative,
        trash_trend=trash_trend,
        trash_selection=trash_selection,
    )

    div = compute_divergence(portfolio)

    return DivergenceResponse(
        score=div.score,
        details=div.details,
        veto_active=div.veto_active,
        risk_reduction_factor=div.risk_reduction_factor,
    )
