"""Tests for RSPS core engine modules."""

import pytest

from strategy_engine.models import LTPISystem, TrendDirection
from strategy_engine.models_rsps import (
    AllocationStyle,
    IndicatorCategory,
    MiniTPI,
    MiniTPIIndicator,
    RSPSConfig,
    TrashFilter,
    TrashToken,
)
from strategy_engine.rsps.totales import TotalesModule
from strategy_engine.rsps.conservative import ConservativeTrendModule
from strategy_engine.rsps.trash_trend import TrashTrendModule
from strategy_engine.rsps.trash_tournament import TrashTournament
from strategy_engine.rsps.portfolio import RSPSPortfolioEngine


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ind(name: str, score: int, cat: str = "perpetual") -> MiniTPIIndicator:
    return MiniTPIIndicator(
        name=name,
        category=IndicatorCategory(cat),
        author="test",
        indicator_type="trend",
        score=score,
    )


def _ratio_tpi(ticker: str, scores: list[int]) -> MiniTPI:
    indicators = [
        _ind(f"{ticker}_ind{i}", s, "perpetual" if i % 2 == 0 else "oscillator")
        for i, s in enumerate(scores)
    ]
    return MiniTPI(ticker=ticker, indicators=indicators)


def _config(**kwargs) -> RSPSConfig:
    defaults = dict(include_sol=True, include_gold=True, total_capital=10000)
    defaults.update(kwargs)
    return RSPSConfig(**defaults)


def _make_filters(n: int = 5) -> list[TrashFilter]:
    return [
        TrashFilter(
            name=f"filter_{i}",
            thesis=f"This is thesis number {i} for testing purposes",
            indicator_name=f"ind_{i}",
            scoring_logic=f"score=1 if value > {i}",
            filter_type="trend",
            is_preliminary=(i == 0),
        )
        for i in range(n)
    ]


def _make_tokens(scores_map: dict[str, list[int]], filters: list[TrashFilter]) -> list[TrashToken]:
    tokens = []
    for ticker, scores in scores_map.items():
        fs = {f.name: s for f, s in zip(filters, scores)}
        tokens.append(TrashToken(ticker=ticker, filter_scores=fs))
    return tokens


# ── Totales Tests ─────────────────────────────────────────────────────────────


class TestTotalesModule:
    def test_long_from_mini_tpi(self) -> None:
        mod = TotalesModule(entry_threshold=0.1)
        tpi = _ratio_tpi("TOTAL", [1, 1, 1])
        result = mod.evaluate_from_mini_tpi(tpi)
        assert result.is_long is True
        assert result.score > 0

    def test_not_long_from_mini_tpi(self) -> None:
        mod = TotalesModule(entry_threshold=0.1)
        tpi = _ratio_tpi("TOTAL", [-1, -1, -1])
        result = mod.evaluate_from_mini_tpi(tpi)
        assert result.is_long is False
        assert result.score < 0

    def test_custom_thresholds(self) -> None:
        mod = TotalesModule(entry_threshold=0.5)
        tpi = _ratio_tpi("TOTAL", [1, -1, 1])  # avg ≈ 0.33
        result = mod.evaluate_from_mini_tpi(tpi)
        assert result.is_long is False  # 0.33 < 0.5


# ── Conservative Tests ────────────────────────────────────────────────────────


class TestConservativeTrendModule:
    def test_two_asset_80_20(self) -> None:
        cfg = RSPSConfig()  # BTC, ETH only
        mod = ConservativeTrendModule(cfg)
        ratio_tpis = {"BTC/ETH": _ratio_tpi("BTCETH", [1, 1, 1])}
        result = mod.evaluate(ratio_tpis)
        assert result.allocations["BTC"] == pytest.approx(0.8, abs=0.01)
        assert result.allocations["ETH"] == pytest.approx(0.2, abs=0.01)

    def test_two_asset_reversed(self) -> None:
        cfg = RSPSConfig()
        mod = ConservativeTrendModule(cfg)
        ratio_tpis = {"BTC/ETH": _ratio_tpi("BTCETH", [-1, -1, -1])}
        result = mod.evaluate(ratio_tpis)
        assert result.allocations["ETH"] == pytest.approx(0.8, abs=0.01)
        assert result.allocations["BTC"] == pytest.approx(0.2, abs=0.01)

    def test_two_asset_100_0(self) -> None:
        cfg = RSPSConfig(allocation_style=AllocationStyle.SPLIT_100_0)
        mod = ConservativeTrendModule(cfg)
        ratio_tpis = {"BTC/ETH": _ratio_tpi("BTCETH", [1, 1, 1])}
        result = mod.evaluate(ratio_tpis)
        assert result.allocations["BTC"] == pytest.approx(1.0, abs=0.01)
        assert result.allocations["ETH"] == pytest.approx(0.0, abs=0.01)

    def test_four_asset_ranking(self) -> None:
        cfg = _config()
        mod = ConservativeTrendModule(cfg)
        # BTC wins all 3 pairs, ETH wins 2, SOL wins 1, GOLD wins 0
        ratio_tpis = {
            "BTC/ETH": _ratio_tpi("x", [1, 1, 1]),     # BTC > ETH
            "BTC/SOL": _ratio_tpi("x", [1, 1, 1]),      # BTC > SOL
            "BTC/GOLD": _ratio_tpi("x", [1, 1, 1]),     # BTC > GOLD
            "ETH/SOL": _ratio_tpi("x", [1, 1, 1]),      # ETH > SOL
            "ETH/GOLD": _ratio_tpi("x", [1, 1, 1]),     # ETH > GOLD
            "SOL/GOLD": _ratio_tpi("x", [1, 1, 1]),     # SOL > GOLD
        }
        result = mod.evaluate(ratio_tpis)

        # BTC should have highest rank, GOLD lowest
        assert result.rankings["BTC"] > result.rankings["GOLD"]
        assert result.rankings["ETH"] > result.rankings["SOL"]
        assert sum(result.allocations.values()) == pytest.approx(1.0, abs=0.01)

    def test_all_tied(self) -> None:
        cfg = _config()
        mod = ConservativeTrendModule(cfg)
        # All pairs are neutral
        ratio_tpis = {
            "BTC/ETH": _ratio_tpi("x", [1, -1]),
            "BTC/SOL": _ratio_tpi("x", [1, -1]),
            "BTC/GOLD": _ratio_tpi("x", [1, -1]),
            "ETH/SOL": _ratio_tpi("x", [1, -1]),
            "ETH/GOLD": _ratio_tpi("x", [1, -1]),
            "SOL/GOLD": _ratio_tpi("x", [1, -1]),
        }
        result = mod.evaluate(ratio_tpis)
        # All tied → equal weight
        for asset in cfg.conservative_assets:
            assert result.allocations[asset] == pytest.approx(0.25, abs=0.01)

    def test_missing_pair_raises(self) -> None:
        cfg = RSPSConfig()
        mod = ConservativeTrendModule(cfg)
        with pytest.raises(ValueError, match="Missing ratio"):
            mod.evaluate({})

    def test_allocations_sum_to_one(self) -> None:
        """Test across various configs that allocations always sum to 1."""
        for style in [AllocationStyle.SPLIT_80_20, AllocationStyle.SPLIT_100_0]:
            for include_sol in [True, False]:
                for include_gold in [True, False]:
                    cfg = RSPSConfig(
                        include_sol=include_sol,
                        include_gold=include_gold,
                        allocation_style=style,
                    )
                    mod = ConservativeTrendModule(cfg)
                    pairs = cfg.required_ratio_pairs
                    ratio_tpis = {
                        f"{a}/{b}": _ratio_tpi(f"{a}{b}", [1, 1, -1])
                        for a, b in pairs
                    }
                    result = mod.evaluate(ratio_tpis)
                    total = sum(result.allocations.values())
                    assert total == pytest.approx(1.0, abs=0.01), (
                        f"Failed for sol={include_sol} gold={include_gold} style={style}: {total}"
                    )


# ── Trash Trend Tests ─────────────────────────────────────────────────────────


class TestTrashTrendModule:
    def test_full_strength(self) -> None:
        cfg = _config(max_trash_pct=0.20)
        mod = TrashTrendModule(cfg)
        tpi = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", 1), _ind("b", 1, "oscillator"), _ind("c", 1)],
        )
        result = mod.evaluate(tpi)
        assert result.strength == pytest.approx(1.0)
        assert result.allocation_pct == pytest.approx(0.20)

    def test_zero_strength(self) -> None:
        cfg = _config(max_trash_pct=0.20)
        mod = TrashTrendModule(cfg)
        tpi = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", 0), _ind("b", 0, "oscillator")],
        )
        result = mod.evaluate(tpi)
        assert result.strength == 0.0
        assert result.allocation_pct == 0.0

    def test_partial_strength(self) -> None:
        cfg = _config(max_trash_pct=0.20)
        mod = TrashTrendModule(cfg)
        tpi = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", 1), _ind("b", 0, "oscillator"), _ind("c", 1)],
        )
        result = mod.evaluate(tpi)
        assert result.strength == pytest.approx(2 / 3, abs=0.01)
        assert result.allocation_pct == pytest.approx(0.20 * 2 / 3, abs=0.01)

    def test_empty_indicators(self) -> None:
        cfg = _config()
        mod = TrashTrendModule(cfg)
        tpi = MiniTPI(ticker="OTHERS.D")
        result = mod.evaluate(tpi)
        assert result.strength == 0.0
        assert result.allocation_pct == 0.0


# ── Trash Tournament Tests ────────────────────────────────────────────────────


class TestTrashTournament:
    def test_qualifying_tokens(self) -> None:
        cfg = _config(trash_threshold=3)
        mod = TrashTournament(cfg)
        filters = _make_filters(5)
        tokens = _make_tokens(
            {
                "DOGE": [1, 1, 1, 1, 1],    # 5 — qualifies
                "SHIB": [1, 1, 1, 0, 0],    # 3 — qualifies
                "PEPE": [1, 0, 0, 0, 0],    # 1 — no
                "BONK": [1, 1, 1, 1, 0],    # 4 — qualifies
            },
            filters,
        )
        result = mod.evaluate(tokens, filters)
        assert len(result.qualifying_tokens) == 3
        assert "DOGE" in result.qualifying_tokens
        assert "PEPE" not in result.qualifying_tokens

    def test_equal_weight(self) -> None:
        cfg = _config(trash_threshold=2)
        mod = TrashTournament(cfg)
        filters = _make_filters(3)
        tokens = _make_tokens(
            {"A": [1, 1, 1], "B": [1, 1, 1], "C": [1, 1, 1]},
            filters,
        )
        result = mod.evaluate(tokens, filters)
        for pct in result.allocations.values():
            assert pct == pytest.approx(1 / 3, abs=0.01)

    def test_preliminary_filter_disqualifies(self) -> None:
        cfg = _config(trash_threshold=2)
        mod = TrashTournament(cfg)
        filters = _make_filters(3)  # filter_0 is preliminary
        tokens = _make_tokens(
            {
                "GOOD": [1, 1, 1],   # passes prelim (filter_0=1)
                "BAD": [0, 1, 1],    # fails prelim (filter_0=0)
            },
            filters,
        )
        result = mod.evaluate(tokens, filters)
        assert "GOOD" in result.qualifying_tokens
        assert "BAD" not in result.qualifying_tokens

    def test_no_qualifiers(self) -> None:
        cfg = _config(trash_threshold=10)
        mod = TrashTournament(cfg)
        filters = _make_filters(3)
        tokens = _make_tokens({"A": [1, 1, 1]}, filters)
        result = mod.evaluate(tokens, filters)
        assert len(result.qualifying_tokens) == 0
        assert len(result.allocations) == 0

    def test_score_matrix_built(self) -> None:
        cfg = _config(trash_threshold=1)
        mod = TrashTournament(cfg)
        filters = _make_filters(2)
        tokens = _make_tokens({"X": [1, 0]}, filters)
        result = mod.evaluate(tokens, filters)
        assert "X" in result.score_matrix
        assert result.score_matrix["X"]["filter_0"] == 1


# ── Portfolio Engine Tests ────────────────────────────────────────────────────


class TestRSPSPortfolioEngine:
    def test_minimal_compute(self) -> None:
        cfg = _config()
        engine = RSPSPortfolioEngine(cfg)
        portfolio = engine.compute()
        assert portfolio.totales.is_long  # default when no TPI provided
        assert sum(portfolio.conservative.allocations.values()) == pytest.approx(1.0, abs=0.01)
        assert portfolio.trash_trend.allocation_pct == 0.0

    def test_full_pipeline(self) -> None:
        cfg = _config(max_trash_pct=0.20, trash_threshold=2)
        engine = RSPSPortfolioEngine(cfg)

        # Market gate
        market_tpi = _ratio_tpi("TOTAL", [1, 1, 1])

        # 6 ratio TPIs — BTC strongest
        ratio_tpis = {
            "BTC/ETH": _ratio_tpi("x", [1, 1, 1]),
            "BTC/SOL": _ratio_tpi("x", [1, 1, 1]),
            "BTC/GOLD": _ratio_tpi("x", [1, 1, 1]),
            "ETH/SOL": _ratio_tpi("x", [1, 1, 1]),
            "ETH/GOLD": _ratio_tpi("x", [1, 1, 1]),
            "SOL/GOLD": _ratio_tpi("x", [1, 1, 1]),
        }

        # Others.D — bullish
        others = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", 1), _ind("b", 1, "oscillator")],
        )

        # Tournament
        filters = _make_filters(3)
        tokens = _make_tokens(
            {"DOGE": [1, 1, 1], "SHIB": [1, 1, 0]},
            filters,
        )

        portfolio = engine.compute(
            market_tpi=market_tpi,
            ratio_tpis=ratio_tpis,
            others_tpi=others,
            trash_tokens=tokens,
            trash_filters=filters,
        )

        assert portfolio.totales.is_long
        assert portfolio.trash_trend.allocation_pct > 0
        assert len(portfolio.trash_selection.qualifying_tokens) >= 1
        total_balance = sum(portfolio.balances.values())
        assert total_balance == pytest.approx(cfg.total_capital, abs=0.01)

    def test_not_long_reduces_exposure(self) -> None:
        cfg = _config(not_long_reduction=0.5)
        engine = RSPSPortfolioEngine(cfg)
        # Bearish market
        market_tpi = _ratio_tpi("TOTAL", [-1, -1, -1])
        portfolio = engine.compute(market_tpi=market_tpi)

        deployed = sum(v for k, v in portfolio.balances.items() if k != "CASH")
        assert deployed == pytest.approx(cfg.total_capital * 0.5, abs=1.0)
        assert portfolio.balances.get("CASH", 0) == pytest.approx(
            cfg.total_capital * 0.5, abs=1.0
        )

    def test_rebalance_deltas(self) -> None:
        cfg = _config()
        engine = RSPSPortfolioEngine(cfg)
        current = {"BTC": 3000, "ETH": 7000}
        portfolio = engine.compute(current_balances=current)
        # Deltas should exist
        assert len(portfolio.rebalance_deltas) > 0
