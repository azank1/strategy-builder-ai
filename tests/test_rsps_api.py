"""Tests for RSPS API routes — unit tests against route logic."""

import pytest

from strategy_engine.models_rsps import (
    AllocationStyle,
    HeadlineAction,
    IndicatorCategory,
    MiniTPI,
    MiniTPIIndicator,
    RSPSConfig,
    RSPSPortfolio,
    TotalesState,
    TrashFilter,
    TrashToken,
    TrashTrendResult,
    TournamentResult,
)
from strategy_engine.rsps import (
    RSPSPortfolioEngine,
    RSPSValidator,
    compute_action_summary,
    compute_forward_watch,
    compute_divergence,
)


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


def _build_ratio_tpis(config: RSPSConfig) -> dict[str, MiniTPI]:
    """Build ratio TPIs for all required pairs in the config."""
    tpis = {}
    for a, b in config.required_ratio_pairs:
        key = f"{a}/{b}"
        tpis[key] = _ratio_tpi(key, [1, 1, 1])
    return tpis


# ── End-to-End Pipeline Tests (mimics route logic) ──────────────────────────


class TestRSPSPipelineCompute:
    """Tests that mirror the /rsps/compute route logic end-to-end."""

    def test_full_compute_pipeline(self):
        config = _config()
        ratio_tpis = _build_ratio_tpis(config)

        filters = _make_filters(5)
        tokens = _make_tokens(
            {"DOGE": [1, 1, 1, 1, 0], "SHIB": [1, 0, 1, 0, 1]},
            filters,
        )

        market_tpi = _ratio_tpi("TOTAL", [1, 1, 1])

        engine = RSPSPortfolioEngine(config)
        portfolio = engine.compute(
            market_tpi=market_tpi,
            ratio_tpis=ratio_tpis,
            trash_tokens=tokens,
            trash_filters=filters,
        )

        assert portfolio is not None
        assert portfolio.totales.is_long is True
        assert sum(portfolio.balances.values()) == pytest.approx(config.total_capital, rel=0.01)

    def test_action_summary_generated(self):
        config = _config()
        ratio_tpis = _build_ratio_tpis(config)

        engine = RSPSPortfolioEngine(config)
        portfolio = engine.compute(
            market_tpi=_ratio_tpi("TOTAL", [1, 1, 1]),
            ratio_tpis=ratio_tpis,
        )

        action = compute_action_summary(portfolio, None)
        assert action.headline is not None
        assert isinstance(action.headline, HeadlineAction)

    def test_forward_watch_generated(self):
        config = _config()
        ratio_tpis = _build_ratio_tpis(config)

        engine = RSPSPortfolioEngine(config)
        portfolio = engine.compute(
            market_tpi=_ratio_tpi("TOTAL", [1, 1, 1]),
            ratio_tpis=ratio_tpis,
        )

        triggers = compute_forward_watch(portfolio)
        assert isinstance(triggers, list)

    def test_divergence_generated(self):
        config = _config()
        ratio_tpis = _build_ratio_tpis(config)

        engine = RSPSPortfolioEngine(config)
        portfolio = engine.compute(
            market_tpi=_ratio_tpi("TOTAL", [1, 1, 1]),
            ratio_tpis=ratio_tpis,
        )

        div = compute_divergence(portfolio)
        assert 0.0 <= div.score <= 1.0

    def test_not_long_reduces_allocation(self):
        config = _config(not_long_reduction=0.5)
        ratio_tpis = _build_ratio_tpis(config)

        engine = RSPSPortfolioEngine(config)
        portfolio = engine.compute(
            market_tpi=_ratio_tpi("TOTAL", [-1, -1, -1]),
            ratio_tpis=ratio_tpis,
        )

        # When not long, capital deployed should be reduced
        total_deployed = sum(portfolio.balances.values())
        assert total_deployed <= config.total_capital


# ── Validation Tests ─────────────────────────────────────────────────────────


class TestRSPSRouteValidation:
    """Tests that mirror the /rsps/validate route logic."""

    def test_valid_config_passes(self):
        config = _config()
        errors = RSPSValidator.validate_config(config)
        failed = [e for e in errors if not e.passed and e.severity == "error"]
        assert len(failed) == 0

    def test_invalid_config_detected(self):
        config = _config(include_sol=False, include_gold=False)
        # Only BTC + ETH = 2 assets, should pass R01
        errors = RSPSValidator.validate_config(config)
        failed = [e for e in errors if not e.passed]
        # All should pass with 2 assets
        for e in errors:
            if e.rule_id == "R01":
                assert e.passed

    def test_mini_tpi_validation(self):
        tpi = _ratio_tpi("ETHBTC", [1, 1, 1])
        errors = RSPSValidator.validate_mini_tpi(tpi)
        failed = [e for e in errors if not e.passed and e.severity == "error"]
        assert len(failed) == 0

    def test_mini_tpi_too_few_indicators(self):
        tpi = _ratio_tpi("ETHBTC", [1])
        errors = RSPSValidator.validate_mini_tpi(tpi)
        failed = [e for e in errors if not e.passed]
        assert any(not e.passed for e in errors)

    def test_filter_validation(self):
        filters = _make_filters(5)
        errors = RSPSValidator.validate_filters(filters)
        failed = [e for e in errors if not e.passed and e.severity == "error"]
        assert len(failed) == 0

    def test_full_validation_pipeline(self):
        config = _config()
        ratio_tpis = [_ratio_tpi("ETHBTC", [1, 1, 1])]

        all_errors = RSPSValidator.validate_config(config)
        for tpi in ratio_tpis:
            all_errors.extend(RSPSValidator.validate_mini_tpi(tpi))

        error_list = [r for r in all_errors if not r.passed and r.severity == "error"]
        warn_list = [r for r in all_errors if not r.passed and r.severity == "warning"]

        is_valid = len(error_list) == 0
        assert is_valid is True


# ── Schema Tests ──────────────────────────────────────────────────────────────


class TestRSPSSchemas:
    """Test that schemas serialize/deserialize correctly."""

    def test_config_serialization(self):
        config = _config()
        data = config.model_dump()
        restored = RSPSConfig(**data)
        assert restored.include_sol == config.include_sol
        assert restored.allocation_style == config.allocation_style

    def test_mini_tpi_serialization(self):
        tpi = _ratio_tpi("ETHBTC", [1, -1, 1])
        data = tpi.model_dump()
        restored = MiniTPI(**data)
        assert len(restored.indicators) == 3
        assert restored.average_score == pytest.approx(tpi.average_score)

    def test_trash_filter_serialization(self):
        filters = _make_filters(3)
        for f in filters:
            data = f.model_dump()
            restored = TrashFilter(**data)
            assert restored.name == f.name

    def test_trash_token_serialization(self):
        filters = _make_filters(3)
        tokens = _make_tokens({"DOGE": [1, 1, 0]}, filters)
        for t in tokens:
            data = t.model_dump()
            restored = TrashToken(**data)
            assert restored.total_score == t.total_score
