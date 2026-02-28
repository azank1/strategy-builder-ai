"""Tests for SDCA and LTPI validators."""

from datetime import date

import pytest

from strategy_engine.core.validation import (
    SDCAValidator,
    LTPIValidator,
    BANNED_INDICATORS_SDCA,
)
from strategy_engine.models import (
    AssetClass,
    IndicatorSource,
    IntendedSignalPeriod,
    ISPSignal,
    LTPICategory,
    LTPIIndicator,
    LTPISystem,
    SDCACategory,
    SDCAComments,
    SDCAIndicator,
    SDCASystem,
    TrendDirection,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_sdca_indicator(
    name: str = "Test Indicator",
    category: SDCACategory = SDCACategory.FUNDAMENTAL,
    source_website: str = "example.com",
    source_author: str | None = None,
    provided_by: IndicatorSource = IndicatorSource.OWN_RESEARCH,
    z_score: float = 0.5,
) -> SDCAIndicator:
    return SDCAIndicator(
        name=name,
        category=category,
        source_url=f"https://{source_website}/indicator",
        source_website=source_website,
        source_author=source_author,
        provided_by=provided_by,
        z_score=z_score,
        date_updated=date.today(),
        comments=SDCAComments(
            why_chosen="A" * 60,
            how_it_works="B" * 60,
            scoring_logic="C" * 60,
        ),
    )


def _make_ltpi_indicator(
    name: str = "Test LTPI",
    category: LTPICategory = LTPICategory.TECHNICAL_BTC,
    author: str = "author1",
    indicator_type: str = "supertrend",
    source_website: str = "tradingview.com",
    score: int = 1,
) -> LTPIIndicator:
    return LTPIIndicator(
        name=name,
        category=category,
        source_url=f"https://{source_website}/{name.lower().replace(' ', '-')}",
        source_website=source_website,
        author=author,
        indicator_type=indicator_type,
        scoring_criteria="Long when above zero, short when below",
        comment="A" * 40 + " — this indicator measures momentum.",
        score=score,
    )


def _make_valid_sdca_system() -> SDCASystem:
    """Generate a valid SDCA system with 15+ indicators passing all rules."""
    indicators = []

    # 5 fundamental
    for i in range(5):
        indicators.append(
            _make_sdca_indicator(
                name=f"Fundamental {i+1}",
                category=SDCACategory.FUNDAMENTAL,
                source_website=f"site-f{i}.com",
            )
        )

    # 5 technical
    for i in range(5):
        indicators.append(
            _make_sdca_indicator(
                name=f"Technical {i+1}",
                category=SDCACategory.TECHNICAL,
                source_website=f"site-t{i}.com",
            )
        )

    # 3 sentiment
    for i in range(3):
        indicators.append(
            _make_sdca_indicator(
                name=f"Sentiment {i+1}",
                category=SDCACategory.SENTIMENT,
                source_website=f"site-s{i}.com",
            )
        )

    # 2 flex (technical)
    for i in range(2):
        indicators.append(
            _make_sdca_indicator(
                name=f"Flex {i+1}",
                category=SDCACategory.TECHNICAL,
                source_website=f"site-x{i}.com",
            )
        )

    return SDCASystem(
        asset=AssetClass.BTC,
        indicators=indicators,
        date_updated=date.today(),
    )


def _make_valid_ltpi_system() -> LTPISystem:
    """Generate a valid LTPI system with 12 C1 + 5 C2 indicators."""
    c1 = [
        _make_ltpi_indicator(
            name=f"Tech {i+1}",
            category=LTPICategory.TECHNICAL_BTC,
            author=f"author_c1_{i}",
            indicator_type=f"type_{i}",
        )
        for i in range(12)
    ]

    c2 = [
        _make_ltpi_indicator(
            name=f"OnChain {i+1}",
            category=LTPICategory.ON_CHAIN,
            author=f"author_c2_{i}",
            indicator_type=f"onchain_type_{i}",
            source_website=f"onchain-{i}.com",
        )
        for i in range(5)
    ]

    return LTPISystem(
        asset=AssetClass.BTC,
        technical_btc=c1,
        on_chain=c2,
        date_updated=date.today(),
        isp=IntendedSignalPeriod(
            timeframe="1D",
            signals=[
                ISPSignal(date=date(2020, 1, i + 1), direction=d)
                for i, d in enumerate(
                    [TrendDirection.LONG, TrendDirection.SHORT] * 7
                )
            ],
        ),
    )


# ─── SDCA Validator Tests ────────────────────────────────────────────────────


class TestSDCAValidator:
    def test_valid_system_passes(self) -> None:
        v = SDCAValidator()
        result = v.validate(_make_valid_sdca_system())
        assert result.is_valid, result.errors

    def test_too_few_indicators(self) -> None:
        v = SDCAValidator()
        system = SDCASystem(
            asset=AssetClass.BTC,
            indicators=[_make_sdca_indicator()],
            date_updated=date.today(),
        )
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "min_total" in rules

    def test_missing_category(self) -> None:
        v = SDCAValidator()
        # Only fundamentals
        indicators = [
            _make_sdca_indicator(name=f"F{i}", source_website=f"s{i}.com")
            for i in range(15)
        ]
        system = SDCASystem(
            asset=AssetClass.BTC,
            indicators=indicators,
            date_updated=date.today(),
        )
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "min_technical" in rules
        assert "min_sentiment" in rules

    def test_banned_indicator(self) -> None:
        v = SDCAValidator()
        system = _make_valid_sdca_system()
        system.indicators[0].name = "Stock to Flow"
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "banned_indicator" in rules

    def test_too_many_from_reference_sheet(self) -> None:
        v = SDCAValidator()
        system = _make_valid_sdca_system()
        for i in range(6):
            system.indicators[i].provided_by = IndicatorSource.REFERENCE_SHEET
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "max_reference_sheet" in rules

    def test_source_diversification(self) -> None:
        v = SDCAValidator()
        system = _make_valid_sdca_system()
        # Set 3 fundamental indicators to same website
        for i in range(3):
            system.indicators[i].source_website = "same-site.com"
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "source_diversification" in rules


# ─── LTPI Validator Tests ────────────────────────────────────────────────────


class TestLTPIValidator:
    def test_valid_system_passes(self) -> None:
        v = LTPIValidator()
        result = v.validate(_make_valid_ltpi_system())
        assert result.is_valid, result.errors

    def test_wrong_c1_count(self) -> None:
        v = LTPIValidator()
        system = _make_valid_ltpi_system()
        system.technical_btc = system.technical_btc[:10]  # only 10
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "c1_count" in rules

    def test_wrong_c2_count(self) -> None:
        v = LTPIValidator()
        system = _make_valid_ltpi_system()
        system.on_chain = system.on_chain[:2]  # only 2
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "c2_count" in rules

    def test_duplicate_author_c1(self) -> None:
        v = LTPIValidator()
        system = _make_valid_ltpi_system()
        system.technical_btc[0].author = "same_author"
        system.technical_btc[1].author = "same_author"
        result = v.validate(system)
        assert not result.is_valid

    def test_cross_category_author_overlap(self) -> None:
        v = LTPIValidator()
        system = _make_valid_ltpi_system()
        system.technical_btc[0].author = "shared_author"
        system.on_chain[0].author = "shared_author"
        result = v.validate(system)
        assert not result.is_valid
        rules = {e.rule for e in result.errors}
        assert "cross_category_authors" in rules

    def test_duplicate_indicator_type(self) -> None:
        v = LTPIValidator()
        system = _make_valid_ltpi_system()
        system.technical_btc[0].indicator_type = "same_type"
        system.technical_btc[1].indicator_type = "same_type"
        result = v.validate(system)
        assert not result.is_valid
