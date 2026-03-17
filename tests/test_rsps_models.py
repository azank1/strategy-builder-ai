"""Tests for RSPS models (models_rsps.py)."""

import pytest

from strategy_engine.models_rsps import (
    AllocationStyle,
    ConservativeAllocation,
    DivergenceResult,
    HeadlineAction,
    IndicatorCategory,
    MiniTPI,
    MiniTPIIndicator,
    Move,
    PROHIBITED_FILTER_TYPES,
    RSPSConfig,
    RSPSPortfolio,
    TotalesState,
    TrashFilter,
    TrashToken,
    TrashTrendResult,
    TournamentResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_indicator(name: str, score: int = 1, category: str = "perpetual") -> MiniTPIIndicator:
    return MiniTPIIndicator(
        name=name,
        category=IndicatorCategory(category),
        author="test",
        indicator_type="trend",
        score=score,
    )


def _make_config(**kwargs) -> RSPSConfig:
    defaults = dict(include_sol=True, include_gold=True)
    defaults.update(kwargs)
    return RSPSConfig(**defaults)


# ── RSPSConfig Tests ──────────────────────────────────────────────────────────


class TestRSPSConfig:
    def test_default_assets_btc_eth(self) -> None:
        cfg = RSPSConfig()
        assert cfg.conservative_assets == ["BTC", "ETH"]

    def test_four_assets(self) -> None:
        cfg = _make_config()
        assert cfg.conservative_assets == ["BTC", "ETH", "SOL", "GOLD"]

    def test_ratio_pairs_two(self) -> None:
        cfg = RSPSConfig()
        assert cfg.required_ratio_pairs == [("BTC", "ETH")]

    def test_ratio_pairs_four(self) -> None:
        cfg = _make_config()
        pairs = cfg.required_ratio_pairs
        assert len(pairs) == 6  # C(4,2) = 6

    def test_custom_requires_weights(self) -> None:
        with pytest.raises(ValueError, match="custom_weights required"):
            RSPSConfig(allocation_style=AllocationStyle.CUSTOM)

    def test_custom_with_weights(self) -> None:
        cfg = RSPSConfig(
            allocation_style=AllocationStyle.CUSTOM,
            custom_weights={"0": 0.5, "1": 0.3, "2": 0.2},
        )
        assert cfg.allocation_style == AllocationStyle.CUSTOM

    def test_max_trash_pct_bounds(self) -> None:
        with pytest.raises(Exception):
            RSPSConfig(max_trash_pct=0.6)


# ── MiniTPIIndicator Tests ────────────────────────────────────────────────────


class TestMiniTPIIndicator:
    def test_effective_score_default(self) -> None:
        ind = _make_indicator("test", score=1)
        assert ind.effective_score == 1

    def test_effective_score_override(self) -> None:
        ind = _make_indicator("test", score=1)
        ind = ind.model_copy(update={"manual_override": -1})
        assert ind.effective_score == -1


# ── MiniTPI Tests ─────────────────────────────────────────────────────────────


class TestMiniTPI:
    def test_average_score(self) -> None:
        tpi = MiniTPI(
            ticker="ETHBTC",
            indicators=[
                _make_indicator("a", 1),
                _make_indicator("b", -1),
                _make_indicator("c", 1, "oscillator"),
            ],
        )
        assert abs(tpi.average_score - (1 / 3)) < 0.01

    def test_empty_average(self) -> None:
        tpi = MiniTPI(ticker="ETHBTC")
        assert tpi.average_score == 0.0

    def test_category_counts(self) -> None:
        tpi = MiniTPI(
            ticker="ETHBTC",
            indicators=[
                _make_indicator("a", 1, "perpetual"),
                _make_indicator("b", 1, "perpetual"),
                _make_indicator("c", -1, "oscillator"),
            ],
        )
        assert tpi.perpetual_count == 2
        assert tpi.oscillator_count == 1


# ── TrashFilter Tests ─────────────────────────────────────────────────────────


class TestTrashFilter:
    def test_valid_filter(self) -> None:
        f = TrashFilter(
            name="Beta Filter",
            thesis="Filters for high-beta tokens that correlate well",
            indicator_name="beta_vs_btc",
            scoring_logic="score=1 if beta > 1.5 else 0",
            filter_type="beta",
        )
        assert f.filter_type == "beta"

    def test_prohibited_filter_type(self) -> None:
        for ft in PROHIBITED_FILTER_TYPES:
            with pytest.raises(ValueError, match="prohibited"):
                TrashFilter(
                    name="Bad Filter",
                    thesis="This should fail validation",
                    indicator_name="bad",
                    scoring_logic="score=1 always",
                    filter_type=ft,
                )


# ── TrashToken Tests ──────────────────────────────────────────────────────────


class TestTrashToken:
    def test_total_score(self) -> None:
        t = TrashToken(ticker="DOGE", filter_scores={"a": 1, "b": 0, "c": 1})
        assert t.total_score == 2

    def test_qualifies(self) -> None:
        t = TrashToken(ticker="DOGE", filter_scores={"a": 1, "b": 1, "c": 1, "d": 1})
        assert t.qualifies(4)
        assert not t.qualifies(5)

    def test_passes_preliminary(self) -> None:
        prelim = TrashFilter(
            name="mcap",
            thesis="Market cap filter for minimum size",
            indicator_name="market_cap",
            scoring_logic="score=1 if mcap > 1B",
            filter_type="market_cap",
            is_preliminary=True,
        )
        t1 = TrashToken(ticker="DOGE", filter_scores={"mcap": 1})
        t2 = TrashToken(ticker="SHIB", filter_scores={"mcap": 0})
        assert t1.passes_preliminary([prelim])
        assert not t2.passes_preliminary([prelim])


# ── ConservativeAllocation Tests ──────────────────────────────────────────────


class TestConservativeAllocation:
    def test_valid_allocation(self) -> None:
        ca = ConservativeAllocation(
            allocations={"BTC": 0.5, "ETH": 0.3, "SOL": 0.2},
            rankings={"BTC": 2, "ETH": 1, "SOL": 0},
        )
        assert sum(ca.allocations.values()) == pytest.approx(1.0)

    def test_invalid_sum(self) -> None:
        with pytest.raises(ValueError, match="sum to ~1.0"):
            ConservativeAllocation(
                allocations={"BTC": 0.5, "ETH": 0.3},
                rankings={"BTC": 1, "ETH": 0},
            )


# ── TrashTrendResult Tests ────────────────────────────────────────────────────


class TestTrashTrendResult:
    def test_creation(self) -> None:
        tr = TrashTrendResult(strength=0.75, allocation_pct=0.15)
        assert tr.allocation_pct == 0.15


# ── TotalesState Tests ────────────────────────────────────────────────────────


class TestTotalesState:
    def test_long(self) -> None:
        ts = TotalesState(is_long=True, score=0.3)
        assert ts.is_long

    def test_not_long(self) -> None:
        ts = TotalesState(is_long=False, score=-0.2)
        assert not ts.is_long
