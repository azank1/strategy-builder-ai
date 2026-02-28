"""Tests for the composite scorer."""

from datetime import date

import pytest

from strategy_engine.core.composite import CompositeScorer, SDCAComposite, LTPIComposite
from strategy_engine.models import (
    AssetClass,
    CombinedSignal,
    IndicatorSource,
    IntendedSignalPeriod,
    LTPICategory,
    LTPIIndicator,
    LTPISystem,
    SDCACategory,
    SDCAComments,
    SDCAIndicator,
    SDCASystem,
    SignalStrength,
)


def _comments() -> SDCAComments:
    return SDCAComments(
        why_chosen="A" * 60,
        how_it_works="B" * 60,
        scoring_logic="C" * 60,
    )


def _sdca(z_scores: list[float], asset: AssetClass = AssetClass.BTC) -> SDCASystem:
    indicators = [
        SDCAIndicator(
            name=f"Ind {i}",
            category=[SDCACategory.FUNDAMENTAL, SDCACategory.TECHNICAL, SDCACategory.SENTIMENT][i % 3],
            source_url=f"https://site{i}.com/ind",
            source_website=f"site{i}.com",
            provided_by=IndicatorSource.OWN_RESEARCH,
            z_score=z,
            date_updated=date.today(),
            comments=_comments(),
        )
        for i, z in enumerate(z_scores)
    ]
    return SDCASystem(asset=asset, indicators=indicators, date_updated=date.today())


def _ltpi(scores: list[int], asset: AssetClass = AssetClass.BTC) -> LTPISystem:
    c1 = [
        LTPIIndicator(
            name=f"Tech {i}",
            category=LTPICategory.TECHNICAL_BTC,
            source_url=f"https://tv.com/t{i}",
            source_website="tradingview.com",
            author=f"auth_{i}",
            indicator_type=f"type_{i}",
            scoring_criteria="Long > 0, Short < 0",
            comment="A" * 40,
            score=scores[i] if i < len(scores) else 0,
        )
        for i in range(min(12, len(scores)))
    ]
    return LTPISystem(
        asset=asset,
        technical_btc=c1,
        on_chain=[],
        date_updated=date.today(),
    )


class TestSDCAComposite:
    def test_equal_weight(self) -> None:
        scorer = CompositeScorer()
        system = _sdca([-2.0, -1.5, -1.0])
        result = scorer.score_sdca(system)
        assert result.composite_z == pytest.approx(-1.5, abs=0.01)
        assert "oversold" in result.interpretation.lower() or "accumulation" in result.interpretation.lower()

    def test_weighted(self) -> None:
        scorer = CompositeScorer(
            sdca_weights={"fundamental": 2.0, "technical": 1.0, "sentiment": 0.5}
        )
        system = _sdca([-2.0, 0.0, 1.0])  # F=-2, T=0, S=1
        result = scorer.score_sdca(system)
        # Weighted: (-2*2 + 0*1 + 1*0.5) / 3.5 = -3.5/3.5 = -1.0
        assert result.composite_z == pytest.approx(-1.0, abs=0.01)

    def test_empty_system_raises(self) -> None:
        """An SDCASystem requires at least 1 indicator."""
        with pytest.raises(Exception):
            SDCASystem(
                asset=AssetClass.BTC,
                indicators=[],
                date_updated=date.today(),
            )


class TestLTPIComposite:
    def test_bullish(self) -> None:
        scorer = CompositeScorer()
        system = _ltpi([1] * 10 + [-1] * 2)
        result = scorer.score_ltpi(system)
        assert result.trend_ratio > 0.5
        assert "uptrend" in result.interpretation.lower()

    def test_bearish(self) -> None:
        scorer = CompositeScorer()
        system = _ltpi([-1] * 10 + [1] * 2)
        result = scorer.score_ltpi(system)
        assert result.trend_ratio < -0.5
        assert "downtrend" in result.interpretation.lower()


class TestCombinedSignal:
    def test_strongest_buy(self) -> None:
        """Undervalued + uptrend = strongest buy."""
        scorer = CompositeScorer()
        sdca = _sdca([-2.0] * 5)  # Very undervalued
        ltpi = _ltpi([1] * 12)  # Strong uptrend
        signal = scorer.combined_signal(sdca, ltpi)
        assert signal.signal == SignalStrength.STRONGEST_BUY

    def test_strongest_sell(self) -> None:
        """Overvalued + downtrend = strongest sell."""
        scorer = CompositeScorer()
        sdca = _sdca([2.0] * 5)  # Very overvalued
        ltpi = _ltpi([-1] * 12)  # Strong downtrend
        signal = scorer.combined_signal(sdca, ltpi)
        assert signal.signal == SignalStrength.STRONGEST_SELL

    def test_cautious_buy(self) -> None:
        """Undervalued + downtrend = cautious buy."""
        scorer = CompositeScorer()
        sdca = _sdca([-2.0] * 5)
        ltpi = _ltpi([-1] * 12)
        signal = scorer.combined_signal(sdca, ltpi)
        assert signal.signal == SignalStrength.CAUTIOUS_BUY

    def test_partial_profit(self) -> None:
        """Overvalued + uptrend = partial profit."""
        scorer = CompositeScorer()
        sdca = _sdca([2.0] * 5)
        ltpi = _ltpi([1] * 12)
        signal = scorer.combined_signal(sdca, ltpi)
        assert signal.signal == SignalStrength.PARTIAL_PROFIT


class TestPortfolioSignal:
    def test_multi_asset_portfolio(self) -> None:
        scorer = CompositeScorer()
        systems = [
            (_sdca([-1.5] * 3, AssetClass.BTC), _ltpi([1] * 12, AssetClass.BTC)),
            (_sdca([0.5] * 3, AssetClass.GOLD), _ltpi([1] * 8 + [-1] * 4, AssetClass.GOLD)),
        ]
        portfolio = scorer.portfolio_signal(systems)
        assert len(portfolio.assets) == 2
        total = sum(a.allocation_pct for a in portfolio.assets)
        assert total == pytest.approx(1.0, abs=0.01)
