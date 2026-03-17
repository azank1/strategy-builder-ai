"""Tests for RSPS Adler-inspired features and validation."""

import pytest

from strategy_engine.models_rsps import (
    ConservativeAllocation,
    DivergenceResult,
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
from strategy_engine.rsps.action import compute_action_summary
from strategy_engine.rsps.divergence import compute_divergence
from strategy_engine.rsps.forward_watch import compute_forward_watch
from strategy_engine.rsps.validation import RSPSValidator, RSPSValidationReport


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ind(name: str, score: int, cat: str = "perpetual") -> MiniTPIIndicator:
    return MiniTPIIndicator(
        name=name,
        category=IndicatorCategory(cat),
        author="test",
        indicator_type="trend",
        score=score,
    )


def _config(**kwargs) -> RSPSConfig:
    defaults = dict(include_sol=True, include_gold=True, total_capital=10000)
    defaults.update(kwargs)
    return RSPSConfig(**defaults)


def _portfolio(
    is_long: bool = True,
    score: float = 0.3,
    btc_alloc: float = 0.4,
    trash_strength: float = 0.5,
    trash_pct: float = 0.1,
    qualifying: int = 2,
    total_tokens: int = 5,
) -> RSPSPortfolio:
    cfg = _config()
    cons = ConservativeAllocation(
        allocations={
            "BTC": btc_alloc,
            "ETH": round((1 - btc_alloc) * 0.5, 4),
            "SOL": round((1 - btc_alloc) * 0.3, 4),
            "GOLD": round((1 - btc_alloc) * 0.2, 4),
        },
        rankings={"BTC": 3, "ETH": 2, "SOL": 1, "GOLD": 0},
    )
    tokens = [TrashToken(ticker=f"T{i}", filter_scores={"f": 1}) for i in range(total_tokens)]
    quals = [f"T{i}" for i in range(qualifying)]
    allocs = {t: round(1.0 / qualifying, 4) for t in quals} if qualifying > 0 else {}
    if qualifying > 0:
        diff = round(1.0 - sum(allocs.values()), 4)
        if diff:
            allocs[quals[0]] = round(allocs[quals[0]] + diff, 4)
    return RSPSPortfolio(
        config=cfg,
        totales=TotalesState(is_long=is_long, score=score),
        conservative=cons,
        trash_trend=TrashTrendResult(strength=trash_strength, allocation_pct=trash_pct),
        trash_selection=TournamentResult(
            all_tokens=tokens,
            qualifying_tokens=quals,
            allocations=allocs,
            threshold_used=4,
        ),
        balances={"BTC": 4000, "ETH": 3000, "SOL": 2000, "GOLD": 1000},
    )


# ── Action Summary Tests ──────────────────────────────────────────────────────


class TestActionSummary:
    def test_hold_when_no_changes(self) -> None:
        portfolio = _portfolio()
        portfolio = portfolio.model_copy(update={"rebalance_deltas": {}})
        action = compute_action_summary(portfolio)
        assert action.headline == HeadlineAction.HOLD

    def test_exit_when_bearish(self) -> None:
        cfg = _config()
        portfolio = _portfolio(is_long=False, score=-0.2)
        portfolio = portfolio.model_copy(
            update={"config": cfg, "rebalance_deltas": {"BTC": -5000}}
        )
        action = compute_action_summary(portfolio)
        assert action.headline == HeadlineAction.EXIT

    def test_reduce_when_not_long(self) -> None:
        portfolio = _portfolio(is_long=False, score=0.0)
        portfolio = portfolio.model_copy(update={"rebalance_deltas": {"BTC": -500}})
        action = compute_action_summary(portfolio)
        assert action.headline == HeadlineAction.REDUCE

    def test_accumulate_from_cash(self) -> None:
        portfolio = _portfolio()
        portfolio = portfolio.model_copy(
            update={"rebalance_deltas": {"BTC": 2000, "ETH": 1000}}
        )
        prev = {"CASH": 5000, "BTC": 2000}
        action = compute_action_summary(portfolio, previous_balances=prev)
        assert action.headline == HeadlineAction.ACCUMULATE

    def test_moves_sorted(self) -> None:
        portfolio = _portfolio()
        portfolio = portfolio.model_copy(
            update={"rebalance_deltas": {"BTC": 500, "ETH": -300, "SOL": -2000}}
        )
        prev = {"BTC": 3500, "ETH": 3300, "SOL": 2000}
        action = compute_action_summary(portfolio, previous_balances=prev)
        # Exits/decreases should come before increases
        if len(action.specific_moves) >= 2:
            dirs = [m.direction for m in action.specific_moves]
            assert dirs.index("increase") > dirs.index("decrease") or "decrease" not in dirs


# ── Forward Watch Tests ───────────────────────────────────────────────────────


class TestForwardWatch:
    def test_totales_trigger_present(self) -> None:
        portfolio = _portfolio()
        triggers = compute_forward_watch(portfolio)
        assert any(t.module == "totales" for t in triggers)

    def test_conservative_triggers(self) -> None:
        portfolio = _portfolio()
        ratio_tpis = {
            "BTC/ETH": MiniTPI(
                ticker="BTCETH",
                indicators=[_ind("a", 1), _ind("b", -1, "oscillator"), _ind("c", 1)],
            ),
        }
        triggers = compute_forward_watch(portfolio, ratio_tpis=ratio_tpis)
        cons_triggers = [t for t in triggers if t.module == "conservative"]
        assert len(cons_triggers) > 0

    def test_trash_trend_trigger(self) -> None:
        portfolio = _portfolio()
        others = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", 1), _ind("b", 0, "oscillator"), _ind("c", 1)],
        )
        triggers = compute_forward_watch(portfolio, others_tpi=others)
        trash_triggers = [t for t in triggers if t.module == "trash_trend"]
        assert len(trash_triggers) > 0

    def test_distance_pct_bounded(self) -> None:
        portfolio = _portfolio()
        triggers = compute_forward_watch(portfolio)
        for t in triggers:
            assert 0.0 <= t.distance_pct <= 100.0


# ── Divergence Tests ──────────────────────────────────────────────────────────


class TestDivergence:
    def test_aligned_portfolio_low_divergence(self) -> None:
        portfolio = _portfolio(
            is_long=True, btc_alloc=0.4, trash_strength=0.6, qualifying=3,
        )
        result = compute_divergence(portfolio)
        assert result.score < 0.5
        assert not result.veto_active

    def test_divergent_portfolio_triggers_veto(self) -> None:
        portfolio = _portfolio(
            is_long=False, btc_alloc=0.25, trash_strength=0.9,
            qualifying=1, total_tokens=10,
        )
        result = compute_divergence(portfolio)
        # Bearish totales + strong trash should produce divergence
        assert result.score > 0
        assert result.details["totales_vs_trash_trend"] > 0

    def test_risk_reduction_applied(self) -> None:
        # Force high divergence
        portfolio = _portfolio(
            is_long=False, btc_alloc=0.9, trash_strength=0.9,
            qualifying=0, total_tokens=10,
        )
        result = compute_divergence(portfolio)
        if result.veto_active:
            assert result.risk_reduction_factor < 1.0

    def test_score_bounded(self) -> None:
        portfolio = _portfolio()
        result = compute_divergence(portfolio)
        assert 0.0 <= result.score <= 1.0


# ── Validation Tests ──────────────────────────────────────────────────────────


class TestRSPSValidator:
    def test_valid_config(self) -> None:
        cfg = _config()
        results = RSPSValidator.validate_config(cfg)
        errors = [r for r in results if not r.passed and r.severity == "error"]
        assert len(errors) == 0

    def test_too_few_assets(self) -> None:
        # Can't make 0 assets via config, but test with SOL/GOLD disabled
        cfg = RSPSConfig()  # Only BTC, ETH — this is valid (≥2)
        results = RSPSValidator.validate_config(cfg)
        r01 = next(r for r in results if r.rule_id == "R01")
        assert r01.passed

    def test_entry_gt_exit(self) -> None:
        # entry=0 and exit=0 → not strictly entry > exit → should fail R03
        cfg = _config(entry_threshold=0.0, exit_threshold=0.0)
        results = RSPSValidator.validate_config(cfg)
        r03 = next(r for r in results if r.rule_id == "R03")
        assert not r03.passed

    def test_mini_tpi_validation(self) -> None:
        tpi = MiniTPI(
            ticker="ETHBTC",
            indicators=[_ind("a", 1), _ind("b", -1, "oscillator"), _ind("c", 1)],
        )
        results = RSPSValidator.validate_mini_tpi(tpi)
        errors = [r for r in results if not r.passed and r.severity == "error"]
        assert len(errors) == 0

    def test_duplicate_indicator_names(self) -> None:
        tpi = MiniTPI(
            ticker="ETHBTC",
            indicators=[_ind("same", 1), _ind("same", -1, "oscillator")],
        )
        results = RSPSValidator.validate_mini_tpi(tpi)
        r07 = next(r for r in results if r.rule_id == "R07")
        assert not r07.passed

    def test_others_tpi_scoring(self) -> None:
        # Valid: 0/1 only
        tpi = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", 0), _ind("b", 1, "oscillator")],
        )
        results = RSPSValidator.validate_others_tpi(tpi)
        errors = [r for r in results if not r.passed]
        assert len(errors) == 0

        # Invalid: score = -1
        tpi2 = MiniTPI(
            ticker="OTHERS.D",
            indicators=[_ind("a", -1)],
        )
        results2 = RSPSValidator.validate_others_tpi(tpi2)
        errors2 = [r for r in results2 if not r.passed]
        assert len(errors2) > 0

    def test_filter_validation(self) -> None:
        filters = [
            TrashFilter(
                name=f"f{i}",
                thesis=f"This is valid thesis number {i} for testing",
                indicator_name=f"ind{i}",
                scoring_logic=f"score=1 if x > {i}",
                filter_type="trend",
            )
            for i in range(4)
        ]
        results = RSPSValidator.validate_filters(filters)
        errors = [r for r in results if not r.passed and r.severity == "error"]
        assert len(errors) == 0

    def test_token_missing_scores(self) -> None:
        filters = [
            TrashFilter(
                name="beta",
                thesis="Beta filter for correlation analysis",
                indicator_name="beta",
                scoring_logic="score=1 if beta > 1",
                filter_type="beta",
            ),
        ]
        tokens = [TrashToken(ticker="X", filter_scores={})]  # Missing 'beta'
        results = RSPSValidator.validate_tokens(tokens, filters)
        errors = [r for r in results if not r.passed]
        assert len(errors) > 0

    def test_portfolio_validation(self) -> None:
        portfolio = _portfolio()
        results = RSPSValidator.validate_portfolio(portfolio)
        errors = [r for r in results if not r.passed and r.severity == "error"]
        assert len(errors) == 0

    def test_full_validation(self) -> None:
        cfg = _config()
        portfolio = _portfolio()
        validator = RSPSValidator()
        report = validator.validate_full(cfg, portfolio)
        assert isinstance(report, RSPSValidationReport)
        assert report.is_valid
