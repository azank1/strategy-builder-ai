"""Pydantic models for the RSPS (Level 4) portfolio construction system."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from strategy_engine.models import (
    AssetClass,
    IntendedSignalPeriod,
    LTPISystem,
    TrendDirection,
)


# ─── Enums ────────────────────────────────────────────────────────────────────


class IndicatorCategory(str, Enum):
    PERPETUAL = "perpetual"
    OSCILLATOR = "oscillator"


class AllocationStyle(str, Enum):
    SPLIT_80_20 = "80/20"
    SPLIT_100_0 = "100/0"
    CUSTOM = "custom"


class HeadlineAction(str, Enum):
    ACCUMULATE = "accumulate"
    REBALANCE = "rebalance"
    HOLD = "hold"
    REDUCE = "reduce"
    EXIT = "exit"


# ─── RSPS Configuration ──────────────────────────────────────────────────────


class RSPSConfig(BaseModel):
    """Master configuration for an RSPS portfolio system."""

    include_sol: bool = False
    include_gold: bool = False
    allocation_style: AllocationStyle = AllocationStyle.SPLIT_80_20
    custom_weights: Optional[dict[str, float]] = Field(
        None, description="Custom allocation weights when style is 'custom'"
    )
    max_trash_pct: float = Field(0.20, ge=0.0, le=0.5)
    trash_threshold: int = Field(4, ge=1)
    total_capital: float = Field(10000.0, gt=0)
    entry_threshold: float = Field(0.1, ge=0.0, le=1.0)
    exit_threshold: float = Field(-0.1, ge=-1.0, le=0.0)
    divergence_veto_threshold: float = Field(
        0.6, ge=0.0, le=1.0,
        description="Divergence score above which risk is auto-reduced",
    )
    not_long_reduction: float = Field(
        0.5, ge=0.0, le=1.0,
        description="Factor to scale down allocations when TOTALES is NOT-LONG",
    )

    @model_validator(mode="after")
    def custom_weights_required_if_custom(self) -> RSPSConfig:
        if self.allocation_style == AllocationStyle.CUSTOM and not self.custom_weights:
            raise ValueError("custom_weights required when allocation_style is 'custom'")
        return self

    @property
    def conservative_assets(self) -> list[str]:
        """List of active conservative portfolio assets."""
        assets = ["BTC", "ETH"]
        if self.include_sol:
            assets.append("SOL")
        if self.include_gold:
            assets.append("GOLD")
        return assets

    @property
    def required_ratio_pairs(self) -> list[tuple[str, str]]:
        """All ratio pairs needed for conservative trend analysis."""
        assets = self.conservative_assets
        pairs = []
        for i, a in enumerate(assets):
            for b in assets[i + 1 :]:
                pairs.append((a, b))
        return pairs


# ─── Mini-TPI Models ─────────────────────────────────────────────────────────


class MiniTPIIndicator(BaseModel):
    """A single indicator within a mini-TPI."""

    name: str = Field(..., min_length=1)
    category: IndicatorCategory
    author: str = Field(..., min_length=1)
    source_url: str = Field(default="")
    indicator_type: str = Field(..., min_length=1)
    timeframe: str = Field(default="1D")
    inputs: dict = Field(default_factory=dict)
    score: int = Field(..., description="±1 for ratio TPIs, 0/1 for OTHERS.D")
    auto_computed: bool = Field(
        False, description="Whether score was computed from price data"
    )
    manual_override: Optional[int] = Field(
        None, description="User override of auto-computed score"
    )
    comment: str = Field(default="", min_length=0)

    @property
    def effective_score(self) -> int:
        """Return manual override if set, otherwise the computed score."""
        if self.manual_override is not None:
            return self.manual_override
        return self.score


class MiniTPI(BaseModel):
    """A lightweight TPI for ratio or dominance trend analysis."""

    ticker: str = Field(..., min_length=1, description="e.g. ETHBTC, OTHERS.D")
    name: str = Field(default="")
    indicators: list[MiniTPIIndicator] = Field(default_factory=list)
    isp: Optional[IntendedSignalPeriod] = None

    @property
    def average_score(self) -> float:
        """Average of all effective indicator scores."""
        if not self.indicators:
            return 0.0
        return sum(i.effective_score for i in self.indicators) / len(self.indicators)

    @property
    def direction(self) -> float:
        """Positive = numerator asset outperforms, negative = denominator."""
        return self.average_score

    @property
    def perpetual_count(self) -> int:
        return sum(1 for i in self.indicators if i.category == IndicatorCategory.PERPETUAL)

    @property
    def oscillator_count(self) -> int:
        return sum(1 for i in self.indicators if i.category == IndicatorCategory.OSCILLATOR)


# ─── Trash Tournament Models ─────────────────────────────────────────────────


PROHIBITED_FILTER_TYPES = frozenset({
    "ath_distance",
    "sharpe_ratio",
    "sortino_ratio",
    "omega_ratio",
    "qualitative",
    "holder_distribution",
    "mean_reversion",
})


class TrashFilter(BaseModel):
    """A quantitative filter in the trash tournament."""

    name: str = Field(..., min_length=1)
    thesis: str = Field(..., min_length=10, description="Why this filter adds edge")
    indicator_name: str = Field(..., min_length=1)
    indicator_link: str = Field(default="")
    indicator_inputs: dict = Field(default_factory=dict)
    scoring_logic: str = Field(
        ..., min_length=5,
        description="e.g. 'score=1 if trend > 0 else 0'",
    )
    filter_type: str = Field(
        default="custom",
        description="trend, beta, market_cap, ratio, custom",
    )
    is_preliminary: bool = Field(
        False,
        description="If True, failing this instantly disqualifies the token",
    )

    @field_validator("filter_type")
    @classmethod
    def check_not_prohibited(cls, v: str) -> str:
        if v in PROHIBITED_FILTER_TYPES:
            raise ValueError(f"Filter type '{v}' is prohibited in trash tournament")
        return v


class TrashToken(BaseModel):
    """A token in the trash tournament with its filter scores."""

    ticker: str = Field(..., min_length=1)
    name: str = Field(default="")
    filter_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of filter_name → 0 or 1",
    )

    @property
    def total_score(self) -> int:
        return sum(self.filter_scores.values())

    def qualifies(self, threshold: int) -> bool:
        return self.total_score >= threshold

    def passes_preliminary(self, filters: list[TrashFilter]) -> bool:
        """Check if token passes all preliminary filters."""
        for f in filters:
            if f.is_preliminary and self.filter_scores.get(f.name, 0) == 0:
                return False
        return True


# ─── TOTALES State ────────────────────────────────────────────────────────────


class TotalesState(BaseModel):
    """Market direction gate — output of Q1."""

    is_long: bool
    score: float
    entry_criteria: str = Field(default="")
    exit_criteria: str = Field(default="")


# ─── Conservative Allocation ──────────────────────────────────────────────────


class ConservativeAllocation(BaseModel):
    """Per-asset allocation in the conservative portfolio — output of Q2."""

    allocations: dict[str, float] = Field(
        ..., description="Asset → percentage (0.0 to 1.0)"
    )
    rankings: dict[str, int] = Field(
        ..., description="Asset → rank (0=weakest, higher=stronger)"
    )
    ratio_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Ratio pair → average TPI score",
    )

    @model_validator(mode="after")
    def allocations_sum_to_one(self) -> ConservativeAllocation:
        total = sum(self.allocations.values())
        if self.allocations and abs(total - 1.0) > 0.01:
            raise ValueError(f"Conservative allocations must sum to ~1.0, got {total:.4f}")
        return self


# ─── Trash Trend ──────────────────────────────────────────────────────────────


class TrashTrendResult(BaseModel):
    """Output of Q3 — how much goes to altcoins."""

    strength: float = Field(..., ge=0.0, le=1.0)
    allocation_pct: float = Field(..., ge=0.0, le=0.5)
    indicator_count: int = 0


# ─── Tournament Result ────────────────────────────────────────────────────────


class TournamentResult(BaseModel):
    """Output of Q4 — which altcoins qualify."""

    all_tokens: list[TrashToken] = Field(default_factory=list)
    qualifying_tokens: list[str] = Field(default_factory=list)
    allocations: dict[str, float] = Field(
        default_factory=dict,
        description="Token → equal-weight pct among qualifiers",
    )
    threshold_used: int = 4
    score_matrix: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Token → {filter → score} for display",
    )


# ─── Adler-Inspired Features ─────────────────────────────────────────────────


class Move(BaseModel):
    """A single portfolio move (part of action summary)."""

    asset: str
    direction: Literal["increase", "decrease", "add", "exit"]
    amount: float
    description: str = ""


class ActionSummary(BaseModel):
    """Headline action + specific moves — Adler-inspired."""

    headline: HeadlineAction
    specific_moves: list[Move] = Field(default_factory=list)
    net_direction: str = Field(default="neutral")
    estimated_trades: int = 0


class Trigger(BaseModel):
    """A forward-watch trigger — condition that would change the plan."""

    module: str = Field(..., description="totales, conservative, trash_trend, tournament")
    condition: str
    current_value: float
    flip_value: float
    distance_pct: float = Field(..., description="How far from flipping (0-100%)")
    impact: str = Field(..., description="What changes if this triggers")


class DivergenceResult(BaseModel):
    """Cross-module agreement scoring."""

    score: float = Field(..., ge=0.0, le=1.0, description="0=agreement, 1=full divergence")
    details: dict[str, float] = Field(
        default_factory=dict,
        description="Per-pair divergence scores",
    )
    veto_active: bool = False
    risk_reduction_factor: float = Field(1.0, ge=0.0, le=1.0)


# ─── Decision Archive ────────────────────────────────────────────────────────


class DecisionSnapshot(BaseModel):
    """An archived portfolio decision point."""

    timestamp: datetime
    action_taken: HeadlineAction
    portfolio_state: dict = Field(default_factory=dict)
    system_state: dict = Field(default_factory=dict)
    divergence_score: float = 0.0
    notes: str = ""


# ─── Master Portfolio Output ──────────────────────────────────────────────────


class RSPSPortfolio(BaseModel):
    """Complete RSPS portfolio output — the master document."""

    config: RSPSConfig
    totales: TotalesState
    conservative: ConservativeAllocation
    trash_trend: TrashTrendResult
    trash_selection: TournamentResult
    balances: dict[str, float] = Field(
        default_factory=dict,
        description="Asset → implied dollar allocation",
    )
    rebalance_deltas: dict[str, float] = Field(
        default_factory=dict,
        description="Asset → dollar change needed",
    )
    action_summary: Optional[ActionSummary] = None
    forward_watch: list[Trigger] = Field(default_factory=list)
    divergence: Optional[DivergenceResult] = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now())
