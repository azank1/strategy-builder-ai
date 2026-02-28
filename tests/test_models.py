"""Tests for the models module."""

from datetime import date

import pytest

from strategy_engine.models import (
    AssetClass,
    CombinedSignal,
    ISPSignal,
    IntendedSignalPeriod,
    LTPICategory,
    LTPIIndicator,
    LTPISystem,
    SDCACategory,
    SDCAComments,
    SDCAIndicator,
    SDCASystem,
    IndicatorSource,
    SignalStrength,
    TrendDirection,
)


class TestSDCAIndicator:
    def test_valid_creation(self) -> None:
        ind = SDCAIndicator(
            name="Mayer Multiple",
            category=SDCACategory.TECHNICAL,
            source_url="https://example.com",
            source_website="example.com",
            provided_by=IndicatorSource.OWN_RESEARCH,
            z_score=1.5,
            date_updated=date.today(),
            comments=SDCAComments(
                why_chosen="A" * 60,
                how_it_works="B" * 60,
                scoring_logic="C" * 60,
            ),
        )
        assert ind.z_score == 1.5
        assert ind.category == SDCACategory.TECHNICAL

    def test_z_score_bounds(self) -> None:
        with pytest.raises(Exception):
            SDCAIndicator(
                name="Bad",
                category=SDCACategory.FUNDAMENTAL,
                source_url="https://bad.com",
                source_website="bad.com",
                provided_by=IndicatorSource.OWN_RESEARCH,
                z_score=6.0,  # Out of bounds
                date_updated=date.today(),
                comments=SDCAComments(
                    why_chosen="A" * 60,
                    how_it_works="B" * 60,
                    scoring_logic="C" * 60,
                ),
            )

    def test_decay_requires_description(self) -> None:
        with pytest.raises(Exception):
            SDCAIndicator(
                name="Decaying",
                category=SDCACategory.FUNDAMENTAL,
                source_url="https://d.com",
                source_website="d.com",
                provided_by=IndicatorSource.OWN_RESEARCH,
                z_score=0.0,
                date_updated=date.today(),
                has_decay=True,
                comments=SDCAComments(
                    why_chosen="A" * 60,
                    how_it_works="B" * 60,
                    scoring_logic="C" * 60,
                ),
            )


class TestSDCASystem:
    def test_composite_z_score(self) -> None:
        indicators = [
            SDCAIndicator(
                name=f"Ind{i}",
                category=SDCACategory.FUNDAMENTAL,
                source_url=f"https://s{i}.com",
                source_website=f"s{i}.com",
                provided_by=IndicatorSource.OWN_RESEARCH,
                z_score=z,
                date_updated=date.today(),
                comments=SDCAComments(
                    why_chosen="A" * 60,
                    how_it_works="B" * 60,
                    scoring_logic="C" * 60,
                ),
            )
            for i, z in enumerate([-1.0, 0.0, 1.0])
        ]
        system = SDCASystem(
            asset=AssetClass.BTC,
            indicators=indicators,
            date_updated=date.today(),
        )
        assert system.composite_z_score == pytest.approx(0.0)


class TestLTPIIndicator:
    def test_repainting_raises(self) -> None:
        with pytest.raises(Exception):
            LTPIIndicator(
                name="Bad Repainter",
                category=LTPICategory.TECHNICAL_BTC,
                source_url="https://tv.com",
                source_website="tradingview.com",
                author="someone",
                indicator_type="supertrend",
                scoring_criteria="Long > 0, Short < 0",
                comment="A" * 40,
                score=1,
                repaints=True,
            )


class TestISP:
    def test_trade_count(self) -> None:
        isp = IntendedSignalPeriod(
            timeframe="1D",
            signals=[
                ISPSignal(date=date(2020, 1, 1), direction=TrendDirection.LONG),
                ISPSignal(date=date(2020, 2, 1), direction=TrendDirection.SHORT),
                ISPSignal(date=date(2020, 3, 1), direction=TrendDirection.LONG),
                ISPSignal(date=date(2020, 4, 1), direction=TrendDirection.LONG),
            ],
        )
        assert isp.trade_count == 2


class TestCombinedSignal:
    def test_derive_strongest_buy(self) -> None:
        signal = CombinedSignal._derive_signal(z_score=-2.0, trend_ratio=0.8)
        assert signal == SignalStrength.STRONGEST_BUY

    def test_derive_strongest_sell(self) -> None:
        signal = CombinedSignal._derive_signal(z_score=2.0, trend_ratio=-0.8)
        assert signal == SignalStrength.STRONGEST_SELL

    def test_derive_hold(self) -> None:
        signal = CombinedSignal._derive_signal(z_score=0.0, trend_ratio=0.0)
        assert signal == SignalStrength.HOLD
