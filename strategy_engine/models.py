"""Pydantic models for the strategy engine — indicators, systems, signals."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────


class SDCACategory(str, Enum):
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"


class LTPICategory(str, Enum):
    TECHNICAL_BTC = "technical_btc"
    ON_CHAIN = "on_chain"


class IndicatorSource(str, Enum):
    OWN_RESEARCH = "own_research"
    REFERENCE_SHEET = "reference_sheet"  # e.g., Adam's Macro Sheet


class TrendDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class SignalStrength(str, Enum):
    STRONGEST_BUY = "strongest_buy"
    CAUTIOUS_BUY = "cautious_buy"
    LIGHT_BUY = "light_buy"
    HOLD = "hold"
    REDUCE = "reduce"
    PARTIAL_PROFIT = "partial_profit"
    STRONGEST_SELL = "strongest_sell"


class AssetClass(str, Enum):
    BTC = "btc"
    ETH = "eth"
    GOLD = "gold"
    SPX = "spx"
    ALT = "alt"  # altcoins (premium tier)


# ─── SDCA (Level 1) Models ───────────────────────────────────────────────────


class SDCAComments(BaseModel):
    """Structured research documentation for an SDCA indicator."""

    why_chosen: str = Field(
        ...,
        min_length=50,
        description="Pros, cons, LT/ST suitability, decay status",
    )
    how_it_works: str = Field(
        ...,
        min_length=50,
        description="Calculations, logic, normalization, timeframe, settings",
    )
    scoring_logic: str = Field(
        ...,
        min_length=50,
        description="Positive/negative thresholds, ±2SD values, decay adjustments",
    )


class SDCAIndicator(BaseModel):
    """A single indicator in an SDCA valuation system."""

    name: str = Field(..., min_length=1)
    category: SDCACategory
    source_url: str = Field(..., description="URL to the indicator (not personal chart view)")
    source_website: str = Field(..., description="Domain of the source (for diversification)")
    source_author: Optional[str] = Field(
        None, description="TradingView author, if applicable"
    )
    provided_by: IndicatorSource
    z_score: float = Field(..., ge=-5.0, le=5.0)
    date_updated: date
    comments: SDCAComments
    has_decay: bool = False
    decay_description: Optional[str] = None
    is_logarithmic: bool = False
    is_normalized: bool = False

    @model_validator(mode="after")
    def decay_requires_description(self) -> "SDCAIndicator":
        if self.has_decay and not self.decay_description:
            raise ValueError("Decaying indicators must have a decay_description")
        return self


class SDCASystem(BaseModel):
    """A complete SDCA valuation system for a single asset."""

    asset: AssetClass
    indicators: list[SDCAIndicator] = Field(..., min_length=1)
    date_updated: date

    @property
    def composite_z_score(self) -> float:
        """Average z-score across all indicators."""
        if not self.indicators:
            return 0.0
        return sum(i.z_score for i in self.indicators) / len(self.indicators)

    @property
    def result_by_category(self) -> dict[str, float]:
        """Average z-score per category."""
        from collections import defaultdict

        buckets: dict[str, list[float]] = defaultdict(list)
        for ind in self.indicators:
            buckets[ind.category.value].append(ind.z_score)
        return {cat: sum(scores) / len(scores) for cat, scores in buckets.items()}


# ─── LTPI (Level 2) Models ───────────────────────────────────────────────────


class LTPIIndicator(BaseModel):
    """A single indicator in an LTPI trend system."""

    name: str = Field(..., min_length=1)
    category: LTPICategory
    source_url: str
    source_website: str
    author: str = Field(..., min_length=1, description="TradingView author or data source")
    indicator_type: str = Field(
        ...,
        min_length=1,
        description="e.g. 'supertrend', 'mvrv' — for redundancy checks",
    )
    scoring_criteria: str = Field(
        ...,
        min_length=10,
        description="Short: when +1, when -1, when 0",
    )
    comment: str = Field(..., min_length=30, description="How it works + why chosen")
    score: int = Field(..., ge=-1, le=1)
    repaints: bool = Field(False, description="Must be False — repainting = auto fail")

    @field_validator("repaints")
    @classmethod
    def no_repainting(cls, v: bool) -> bool:
        if v:
            raise ValueError("Repainting indicators are not allowed")
        return v


class ISPSignal(BaseModel):
    """A single signal point in the Intended Signal Period."""

    date: date
    direction: TrendDirection


class IntendedSignalPeriod(BaseModel):
    """Defines the trend duration the LTPI system operates on."""

    start_date: date = Field(default_factory=lambda: date(2018, 1, 1))
    end_date: date = Field(default_factory=date.today)
    timeframe: str = Field(..., description="e.g. '1D', '3D', '1W'")
    signals: list[ISPSignal] = Field(default_factory=list)

    @property
    def trade_count(self) -> int:
        """Number of direction changes (trades)."""
        if len(self.signals) < 2:
            return 0
        changes = 0
        for i in range(1, len(self.signals)):
            if self.signals[i].direction != self.signals[i - 1].direction:
                changes += 1
        return changes


class LTPISystem(BaseModel):
    """A complete LTPI trend system for a single asset."""

    asset: AssetClass
    technical_btc: list[LTPIIndicator] = Field(default_factory=list)
    on_chain: list[LTPIIndicator] = Field(default_factory=list)
    isp: Optional[IntendedSignalPeriod] = None
    date_updated: date

    @property
    def all_indicators(self) -> list[LTPIIndicator]:
        return self.technical_btc + self.on_chain

    @property
    def composite_score(self) -> int:
        """Sum of all indicator scores. Range: -(12+5) to +(12+5)."""
        return sum(ind.score for ind in self.all_indicators)

    @property
    def max_possible(self) -> int:
        return len(self.all_indicators)

    @property
    def trend_ratio(self) -> float:
        """Normalized trend strength: -1.0 to +1.0."""
        if self.max_possible == 0:
            return 0.0
        return self.composite_score / self.max_possible


# ─── Combined Signal ─────────────────────────────────────────────────────────


class CombinedSignal(BaseModel):
    """The unified output combining SDCA valuation + LTPI trend."""

    asset: AssetClass
    sdca_z_score: float
    ltpi_score: int
    ltpi_ratio: float
    signal: SignalStrength
    timestamp: date

    @classmethod
    def from_systems(cls, sdca: SDCASystem, ltpi: LTPISystem) -> CombinedSignal:
        """Derive the combined signal from SDCA + LTPI systems."""
        z = sdca.composite_z_score
        ratio = ltpi.trend_ratio

        signal = cls._derive_signal(z, ratio)

        return cls(
            asset=sdca.asset,
            sdca_z_score=round(z, 4),
            ltpi_score=ltpi.composite_score,
            ltpi_ratio=round(ratio, 4),
            signal=signal,
            timestamp=max(sdca.date_updated, ltpi.date_updated),
        )

    @staticmethod
    def _derive_signal(z_score: float, trend_ratio: float) -> SignalStrength:
        """
        SDCA × LTPI signal matrix:
        
        | Valuation (z)      | Trend (ratio)  | Signal              |
        |--------------------|----------------|---------------------|
        | z <= -1 (underval) | ratio > 0.2    | strongest_buy       |
        | z <= -1 (underval) | ratio <= -0.2  | cautious_buy        |
        | -1 < z < 1 (fair)  | ratio > 0.2    | light_buy           |
        | -1 < z < 1 (fair)  | ratio <= -0.2  | reduce              |
        | z >= 1 (overval)   | ratio > 0.2    | partial_profit      |
        | z >= 1 (overval)   | ratio <= -0.2  | strongest_sell      |
        | any neutral combo  |                | hold                |
        """
        undervalued = z_score <= -1.0
        overvalued = z_score >= 1.0
        uptrend = trend_ratio > 0.2
        downtrend = trend_ratio <= -0.2

        if undervalued and uptrend:
            return SignalStrength.STRONGEST_BUY
        if undervalued and downtrend:
            return SignalStrength.CAUTIOUS_BUY
        if undervalued:
            return SignalStrength.LIGHT_BUY
        if overvalued and downtrend:
            return SignalStrength.STRONGEST_SELL
        if overvalued and uptrend:
            return SignalStrength.PARTIAL_PROFIT
        if overvalued:
            return SignalStrength.REDUCE
        if uptrend:
            return SignalStrength.LIGHT_BUY
        if downtrend:
            return SignalStrength.REDUCE
        return SignalStrength.HOLD
