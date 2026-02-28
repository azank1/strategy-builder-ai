"""
Validation Engine — enforce system construction rules.

Validates SDCA and LTPI systems against all constraints defined in
the Level 1 and Level 2 guidelines. Returns structured error lists
for real-time feedback during system building.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from strategy_engine.models import (
    AssetClass,
    IndicatorSource,
    LTPISystem,
    SDCASystem,
)


@dataclass
class ValidationError:
    """A single validation error."""

    rule: str
    message: str
    severity: str = "error"  # "error" = blocks submission, "warning" = advisory
    indicator_name: str | None = None


@dataclass
class ValidationResult:
    """Complete validation output."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def summary(self) -> str:
        if self.is_valid:
            return f"Valid ({len(self.warnings)} warnings)"
        return f"Invalid: {len(self.errors)} errors, {len(self.warnings)} warnings"


# ─── Banned Indicators ────────────────────────────────────────────────────────

BANNED_INDICATORS_SDCA: set[str] = {
    "stock to flow",
    "reserve risk",
    "puell multiple",
    "quiverquant sentiment",
    "augmento sentiment",
    "open interest",
    "liquidity",
}

BANNED_SOURCES: set[str] = {
    "woobull.com",
}

# ─── SDCA Validator ──────────────────────────────────────────────────────────


class SDCAValidator:
    """
    Validate an SDCA valuation system against Level 1 guidelines.

    Configurable thresholds allow generalization across asset classes
    while maintaining the core constraint structure.
    """

    def __init__(
        self,
        min_total: int = 15,
        min_fundamental: int = 5,
        min_technical: int = 5,
        min_sentiment: int = 2,
        max_reference_sheet: int = 5,
        max_per_website_per_category: int = 2,
        max_tv_per_author: int = 2,
        min_comment_length: int = 50,
        banned_indicators: set[str] | None = None,
        banned_sources: set[str] | None = None,
    ):
        self.min_total = min_total
        self.min_fundamental = min_fundamental
        self.min_technical = min_technical
        self.min_sentiment = min_sentiment
        self.max_reference_sheet = max_reference_sheet
        self.max_per_website = max_per_website_per_category
        self.max_tv_per_author = max_tv_per_author
        self.min_comment_length = min_comment_length
        self.banned_indicators = banned_indicators or BANNED_INDICATORS_SDCA
        self.banned_sources = banned_sources or BANNED_SOURCES

    def validate(self, system: SDCASystem) -> ValidationResult:
        """Run all validation rules on the SDCA system."""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        self._check_counts(system, errors)
        self._check_originality(system, errors)
        self._check_banned(system, errors)
        self._check_source_diversification(system, errors, warnings)
        self._check_completeness(system, errors, warnings)
        self._check_decay(system, errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_counts(self, system: SDCASystem, errors: list[ValidationError]) -> None:
        """Validate minimum indicator counts per category."""
        indicators = system.indicators
        total = len(indicators)

        if total < self.min_total:
            errors.append(ValidationError(
                rule="min_total",
                message=f"Need at least {self.min_total} indicators, have {total}",
            ))

        by_cat = Counter(i.category.value for i in indicators)
        checks = [
            ("fundamental", self.min_fundamental),
            ("technical", self.min_technical),
            ("sentiment", self.min_sentiment),
        ]
        for cat, minimum in checks:
            count = by_cat.get(cat, 0)
            if count < minimum:
                errors.append(ValidationError(
                    rule=f"min_{cat}",
                    message=f"Need at least {minimum} {cat} indicators, have {count}",
                ))

    def _check_originality(self, system: SDCASystem, errors: list[ValidationError]) -> None:
        """Validate originality constraints (max from reference sheet)."""
        ref_count = sum(
            1 for i in system.indicators
            if i.provided_by == IndicatorSource.REFERENCE_SHEET
        )
        if ref_count > self.max_reference_sheet:
            errors.append(ValidationError(
                rule="max_reference_sheet",
                message=f"Max {self.max_reference_sheet} from reference sheet, have {ref_count}",
            ))

        total = len(system.indicators)
        original = total - ref_count
        min_original = self.min_total - self.max_reference_sheet
        if original < min_original and total >= self.min_total:
            errors.append(ValidationError(
                rule="min_original",
                message=f"Need at least {min_original} original indicators, have {original}",
            ))

    def _check_banned(self, system: SDCASystem, errors: list[ValidationError]) -> None:
        """Check for banned indicators and sources."""
        for ind in system.indicators:
            name_lower = ind.name.lower().strip()
            if name_lower in self.banned_indicators:
                errors.append(ValidationError(
                    rule="banned_indicator",
                    message=f"'{ind.name}' is a banned indicator",
                    indicator_name=ind.name,
                ))

            for banned_domain in self.banned_sources:
                if banned_domain in ind.source_url.lower():
                    errors.append(ValidationError(
                        rule="banned_source",
                        message=f"'{ind.name}' uses a banned source ({banned_domain})",
                        indicator_name=ind.name,
                    ))

    def _check_source_diversification(
        self,
        system: SDCASystem,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Validate source diversification per category."""
        by_cat_site: dict[str, Counter[str]] = {}
        for ind in system.indicators:
            cat = ind.category.value
            if cat not in by_cat_site:
                by_cat_site[cat] = Counter()
            by_cat_site[cat][ind.source_website] += 1

        for cat, site_counts in by_cat_site.items():
            for site, count in site_counts.items():
                if count > self.max_per_website:
                    errors.append(ValidationError(
                        rule="source_diversification",
                        message=(
                            f"Max {self.max_per_website} {cat} indicators per website, "
                            f"have {count} from {site}"
                        ),
                    ))

        # Check TradingView author diversification
        tv_authors: Counter[str] = Counter()
        for ind in system.indicators:
            if ind.source_author and "tradingview" in ind.source_website.lower():
                tv_authors[ind.source_author] += 1

        for author, count in tv_authors.items():
            if count > self.max_tv_per_author:
                warnings.append(ValidationError(
                    rule="tv_author_diversification",
                    message=f"Max {self.max_tv_per_author} indicators per TradingView author, have {count} from '{author}'",
                    severity="warning",
                ))

    def _check_completeness(
        self,
        system: SDCASystem,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Validate that all required fields are substantively filled."""
        for ind in system.indicators:
            if not ind.source_url:
                errors.append(ValidationError(
                    rule="missing_source",
                    message=f"'{ind.name}': Missing source URL",
                    indicator_name=ind.name,
                ))

            for field_name in ["why_chosen", "how_it_works", "scoring_logic"]:
                value = getattr(ind.comments, field_name, "")
                if len(value) < self.min_comment_length:
                    warnings.append(ValidationError(
                        rule="comment_depth",
                        message=f"'{ind.name}': {field_name} is too brief ({len(value)} chars, need {self.min_comment_length}+)",
                        severity="warning",
                        indicator_name=ind.name,
                    ))

    def _check_decay(self, system: SDCASystem, errors: list[ValidationError]) -> None:
        """Ensure decaying indicators have proper documentation."""
        for ind in system.indicators:
            if ind.has_decay and not ind.decay_description:
                errors.append(ValidationError(
                    rule="decay_undocumented",
                    message=f"'{ind.name}' is flagged as decaying but has no decay description",
                    indicator_name=ind.name,
                ))


# ─── LTPI Validator ──────────────────────────────────────────────────────────


class LTPIValidator:
    """
    Validate an LTPI trend system against Level 2 guidelines.
    """

    def __init__(
        self,
        c1_exact_count: int = 12,
        c2_min_count: int = 4,
        c2_max_count: int = 5,
        c1_max_per_author: int = 1,
        c2_max_per_author: int = 1,
        c2_max_per_website: int = 2,
        isp_min_trades: int = 11,
    ):
        self.c1_exact_count = c1_exact_count
        self.c2_min_count = c2_min_count
        self.c2_max_count = c2_max_count
        self.c1_max_per_author = c1_max_per_author
        self.c2_max_per_author = c2_max_per_author
        self.c2_max_per_website = c2_max_per_website
        self.isp_min_trades = isp_min_trades

    def validate(self, system: LTPISystem) -> ValidationResult:
        """Run all validation rules on the LTPI system."""
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        self._check_counts(system, errors)
        self._check_repainting(system, errors)
        self._check_author_uniqueness(system, errors)
        self._check_cross_category_authors(system, errors)
        self._check_indicator_type_diversity(system, errors)
        self._check_c2_website_diversification(system, errors)
        self._check_isp(system, errors, warnings)
        self._check_completeness(system, errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_counts(self, system: LTPISystem, errors: list[ValidationError]) -> None:
        tc = len(system.technical_btc)
        oc = len(system.on_chain)

        if tc != self.c1_exact_count:
            errors.append(ValidationError(
                rule="c1_count",
                message=f"Category 1 requires exactly {self.c1_exact_count} indicators, have {tc}",
            ))

        if not (self.c2_min_count <= oc <= self.c2_max_count):
            errors.append(ValidationError(
                rule="c2_count",
                message=f"Category 2 requires {self.c2_min_count}-{self.c2_max_count} indicators, have {oc}",
            ))

    def _check_repainting(self, system: LTPISystem, errors: list[ValidationError]) -> None:
        for ind in system.all_indicators:
            if ind.repaints:
                errors.append(ValidationError(
                    rule="repainting",
                    message=f"'{ind.name}' repaints — automatic fail",
                    indicator_name=ind.name,
                ))

    def _check_author_uniqueness(self, system: LTPISystem, errors: list[ValidationError]) -> None:
        for label, indicators in [("C1", system.technical_btc), ("C2", system.on_chain)]:
            authors = Counter(i.author.lower() for i in indicators)
            max_per = self.c1_max_per_author if label == "C1" else self.c2_max_per_author
            for author, count in authors.items():
                if count > max_per:
                    errors.append(ValidationError(
                        rule=f"{label.lower()}_author_uniqueness",
                        message=f"{label}: Max {max_per} indicator per author, have {count} from '{author}'",
                    ))

    def _check_cross_category_authors(
        self, system: LTPISystem, errors: list[ValidationError]
    ) -> None:
        c1_authors = {i.author.lower() for i in system.technical_btc}
        c2_authors = {i.author.lower() for i in system.on_chain}
        overlap = c1_authors & c2_authors
        if overlap:
            errors.append(ValidationError(
                rule="cross_category_authors",
                message=f"Authors used in both C1 and C2: {overlap}",
            ))

    def _check_indicator_type_diversity(
        self, system: LTPISystem, errors: list[ValidationError]
    ) -> None:
        for label, indicators in [("C1", system.technical_btc), ("C2", system.on_chain)]:
            types = Counter(i.indicator_type.lower() for i in indicators)
            for ind_type, count in types.items():
                if count > 1:
                    errors.append(ValidationError(
                        rule=f"{label.lower()}_type_diversity",
                        message=f"{label}: Duplicate indicator type '{ind_type}' ({count} instances). Max 1 per type.",
                    ))

    def _check_c2_website_diversification(
        self, system: LTPISystem, errors: list[ValidationError]
    ) -> None:
        sites = Counter(i.source_website.lower() for i in system.on_chain)
        for site, count in sites.items():
            if count > self.c2_max_per_website:
                errors.append(ValidationError(
                    rule="c2_website_diversification",
                    message=f"C2: Max {self.c2_max_per_website} per website, have {count} from '{site}'",
                ))

    def _check_isp(
        self,
        system: LTPISystem,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        if not system.isp:
            warnings.append(ValidationError(
                rule="isp_missing",
                message="No Intended Signal Period defined",
                severity="warning",
            ))
            return

        trades = system.isp.trade_count
        if trades < self.isp_min_trades:
            warnings.append(ValidationError(
                rule="isp_min_trades",
                message=f"ISP has {trades} trades, recommended minimum is {self.isp_min_trades}",
                severity="warning",
            ))

    def _check_completeness(self, system: LTPISystem, errors: list[ValidationError]) -> None:
        for ind in system.all_indicators:
            if not ind.scoring_criteria:
                errors.append(ValidationError(
                    rule="missing_scoring",
                    message=f"'{ind.name}': Missing scoring criteria",
                    indicator_name=ind.name,
                ))
            if not ind.comment:
                errors.append(ValidationError(
                    rule="missing_comment",
                    message=f"'{ind.name}': Missing comment",
                    indicator_name=ind.name,
                ))
            if not ind.source_url:
                errors.append(ValidationError(
                    rule="missing_source",
                    message=f"'{ind.name}': Missing source URL",
                    indicator_name=ind.name,
                ))
