"""Analysis routes — validation, z-score, coherency, regime, price data.

These endpoints power the real-time builder UI, providing instant feedback
as users construct their Valuation and Trend systems.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import get_current_user
from api.db_models import SystemType, User

from strategy_engine.core.coherency import CoherencyAnalyzer
from strategy_engine.core.validation import (
    LTPIValidator,
    SDCAValidator,
    ValidationError as EngineValidationError,
)
from strategy_engine.core.zscore import OutlierMethod, ZScoreConfig, ZScoreEngine
from strategy_engine.models import LTPISystem, SDCASystem

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════


class ValidationIssue(BaseModel):
    rule: str
    message: str
    severity: str = "error"
    indicator_name: Optional[str] = None


class ValidationResponse(BaseModel):
    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    error_count: int
    warning_count: int
    summary: str


class ValidateRequest(BaseModel):
    system_type: SystemType
    system_data: dict


class ZScoreRequest(BaseModel):
    values: list[float] = Field(..., min_length=4, description="Historical series")
    current_value: float
    outlier_method: OutlierMethod = OutlierMethod.IQR
    use_log_transform: bool = False


class ZScoreResponse(BaseModel):
    z_score: float
    mean: float
    std: float
    raw_value: float
    data_points_used: int
    outliers_removed: int
    method: str


class CoherencyRequest(BaseModel):
    """Expects a dict of indicator_name → list[int] (signals: +1, -1, 0)."""
    signals: dict[str, list[int]]


class CoherencyResponse(BaseModel):
    agreement_ratio: float
    constructive_ratio: float
    destructive_ratio: float
    mixed_ratio: float
    per_indicator_alignment: dict[str, float]
    avg_pairwise_correlation: float
    is_coherent: bool
    summary: str
    outlier_indicators: list[str]


class RegimeResponse(BaseModel):
    current_regime: str
    confidence: float
    regimes: list[dict]
    description: str


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class PriceResponse(BaseModel):
    asset: str
    frequency: str
    data: list[PricePoint]
    count: int


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Validation endpoint
# ═══════════════════════════════════════════════════════════════════════════════


def _engine_error_to_schema(e: EngineValidationError) -> ValidationIssue:
    return ValidationIssue(
        rule=e.rule,
        message=e.message,
        severity=e.severity,
        indicator_name=e.indicator_name,
    )


@router.post("/validate", response_model=ValidationResponse)
async def validate_system(
    body: ValidateRequest,
    _user: User = Depends(get_current_user),
) -> ValidationResponse:
    """Run validation rules on a system without saving it.

    Returns structured errors/warnings for real-time builder feedback.
    """
    try:
        if body.system_type == SystemType.VALUATION:
            system = SDCASystem(**body.system_data)
            result = SDCAValidator().validate(system)
        elif body.system_type == SystemType.TREND:
            system = LTPISystem(**body.system_data)
            result = LTPIValidator().validate(system)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation not yet supported for type '{body.system_type.value}'",
            )
    except Exception as exc:
        # Pydantic parse errors → return as validation errors
        return ValidationResponse(
            is_valid=False,
            errors=[ValidationIssue(rule="parse_error", message=str(exc))],
            warnings=[],
            error_count=1,
            warning_count=0,
            summary=f"Invalid system data: {exc}",
        )

    return ValidationResponse(
        is_valid=result.is_valid,
        errors=[_engine_error_to_schema(e) for e in result.errors],
        warnings=[_engine_error_to_schema(w) for w in result.warnings],
        error_count=result.error_count,
        warning_count=len(result.warnings),
        summary=result.summary,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Z-Score compute endpoint
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/zscore", response_model=ZScoreResponse)
async def compute_zscore(
    body: ZScoreRequest,
    _user: User = Depends(get_current_user),
) -> ZScoreResponse:
    """Compute a z-score for a value against a historical series.

    Used by the Valuation builder to auto-compute indicator z-scores.
    """
    config = ZScoreConfig(
        outlier_method=body.outlier_method,
        use_log_transform=body.use_log_transform,
    )
    engine = ZScoreEngine(config)
    series = pd.Series(body.values, dtype=float)
    result = engine.compute(series, body.current_value)

    return ZScoreResponse(
        z_score=result.z_score,
        mean=result.mean,
        std=result.std,
        raw_value=result.raw_value,
        data_points_used=result.data_points_used,
        outliers_removed=result.outliers_removed,
        method=result.method.value,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Coherency analysis endpoint
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/coherency", response_model=CoherencyResponse)
async def analyze_coherency(
    body: CoherencyRequest,
    _user: User = Depends(get_current_user),
) -> CoherencyResponse:
    """Analyze time coherency across indicator signals.

    Used by both Valuation and Trend builders to show whether indicators
    agree (constructive interference) or conflict (destructive).
    """
    if len(body.signals) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 indicators for coherency analysis",
        )

    # Build DataFrame from signal dict
    df = pd.DataFrame(body.signals)

    analyzer = CoherencyAnalyzer()
    report = analyzer.analyze(df)
    outliers = analyzer.find_outlier_indicators(df)

    return CoherencyResponse(
        agreement_ratio=report.agreement_ratio,
        constructive_ratio=report.constructive_ratio,
        destructive_ratio=report.destructive_ratio,
        mixed_ratio=report.mixed_ratio,
        per_indicator_alignment=report.per_indicator_alignment,
        avg_pairwise_correlation=report.avg_pairwise_correlation,
        is_coherent=report.is_coherent,
        summary=report.summary,
        outlier_indicators=outliers,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Regime detection endpoint
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/regime/{asset}", response_model=RegimeResponse)
async def detect_regime(
    asset: str,
    _user: User = Depends(get_current_user),
) -> RegimeResponse:
    """Detect the current market regime for an asset.

    Returns regime classification (accumulation/markup/distribution/markdown)
    with confidence score. Powers the contextual overlay on the ISP chart.
    """
    from strategy_engine.ml.regime import RegimeDetector

    # Generate synthetic price data for now (in production, use DataAdapter)
    # TODO: Wire to Yahoo/CoinGecko data adapters when DB caching is ready
    np.random.seed(42)
    n = 365 * 3
    returns = np.random.normal(0.0005, 0.02, n)
    prices = 30000 * np.cumprod(1 + returns)
    price_series = pd.Series(prices, index=pd.date_range(end=date.today(), periods=n, freq="D"))

    detector = RegimeDetector()
    report = detector.detect(price_series)

    regimes = []
    for i, state in enumerate(report.regime_history[-90:]):  # last 90 days
        regimes.append({
            "date": str(price_series.index[-(90 - i)].date()),
            "regime": state.value,
        })

    descriptions = {
        "accumulation": "Market is in accumulation — sideways with declining volatility. Smart money typically enters here.",
        "markup": "Market is in markup phase — trending up with expanding momentum. Trend systems perform best.",
        "distribution": "Market is distributing — topping pattern with high volatility. Consider reducing exposure.",
        "markdown": "Market is in markdown — trending down. Defensive positioning recommended.",
    }

    return RegimeResponse(
        current_regime=report.current_state.value,
        confidence=0.75,  # TODO: derive from HMM posterior
        regimes=regimes,
        description=descriptions.get(
            report.current_state.value,
            "Unable to determine regime.",
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Price data endpoint
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/prices/{asset}", response_model=PriceResponse)
async def get_price_data(
    asset: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    frequency: str = Query("1D", description="Candle frequency: 1D, 3D, 1W"),
    _user: User = Depends(get_current_user),
) -> PriceResponse:
    """Fetch OHLC price data for an asset.

    Powers the ISP chart and all price visualizations in the builders.
    Uses Yahoo Finance / CoinGecko adapters under the hood.
    """
    from strategy_engine.data.yahoo import YahooFinanceAdapter

    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=365 * 5)

    adapter = YahooFinanceAdapter()

    # Check if the asset is supported
    if asset not in adapter.supported_assets():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset '{asset}'. Supported: {adapter.supported_assets()}",
        )

    try:
        result = await adapter.fetch_price(
            symbol=asset,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency.lower().replace("d", "d").replace("w", "wk"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch price data: {exc}",
        )

    # Also fetch OHLC metrics
    try:
        open_data = await adapter.fetch_metric("open", asset, start_date, end_date)
        high_data = await adapter.fetch_metric("high", asset, start_date, end_date)
        low_data = await adapter.fetch_metric("low", asset, start_date, end_date)
        volume_data = await adapter.fetch_metric("volume", asset, start_date, end_date)
    except Exception:
        open_data = high_data = low_data = volume_data = None

    # Build OHLC data points
    close_series = result.data
    data_points: list[PricePoint] = []

    for dt in close_series.index:
        dt_str = str(dt.date()) if hasattr(dt, "date") else str(dt)
        point = PricePoint(
            date=dt_str,
            open=float(open_data.data.get(dt, close_series[dt])) if open_data else float(close_series[dt]),
            high=float(high_data.data.get(dt, close_series[dt])) if high_data else float(close_series[dt]),
            low=float(low_data.data.get(dt, close_series[dt])) if low_data else float(close_series[dt]),
            close=float(close_series[dt]),
            volume=float(volume_data.data.get(dt, 0)) if volume_data else None,
        )
        data_points.append(point)

    return PriceResponse(
        asset=asset,
        frequency=frequency,
        data=data_points,
        count=len(data_points),
    )
