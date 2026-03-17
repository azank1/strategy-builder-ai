"""RSPS Validator — 22+ validation rules matching the spreadsheet checklist.

Rules span the full pipeline: config integrity, mini-TPI health,
filter constraints, allocation math, and cross-module coherency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from strategy_engine.models_rsps import (
    PROHIBITED_FILTER_TYPES,
    MiniTPI,
    RSPSConfig,
    RSPSPortfolio,
    TrashFilter,
    TrashToken,
)


@dataclass
class ValidationResult:
    """Outcome of a single validation rule."""

    rule_id: str
    passed: bool
    message: str
    severity: str = "error"  # "error" | "warning"


@dataclass
class RSPSValidationReport:
    """Full validation report across all rules."""

    results: list[ValidationResult] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(r.passed for r in self.results if r.severity == "error")

    @property
    def errors(self) -> list[ValidationResult]:
        return [r for r in self.results if not r.passed and r.severity == "error"]

    @property
    def warnings(self) -> list[ValidationResult]:
        return [r for r in self.results if not r.passed and r.severity == "warning"]


class RSPSValidator:
    """Validate an RSPS portfolio configuration and output."""

    # ── Config rules ───────────────────────────────────────────────────────

    @staticmethod
    def validate_config(config: RSPSConfig) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        # R01: At least 2 conservative assets
        n_assets = len(config.conservative_assets)
        results.append(ValidationResult(
            rule_id="R01",
            passed=n_assets >= 2,
            message=f"Need ≥2 conservative assets, got {n_assets}",
        ))

        # R02: max_trash_pct ≤ 50%
        results.append(ValidationResult(
            rule_id="R02",
            passed=config.max_trash_pct <= 0.5,
            message=f"max_trash_pct={config.max_trash_pct} exceeds 50%",
        ))

        # R03: entry > exit thresholds
        results.append(ValidationResult(
            rule_id="R03",
            passed=config.entry_threshold > config.exit_threshold,
            message="entry_threshold must be > exit_threshold",
        ))

        # R04: custom weights when needed
        if config.allocation_style.value == "custom":
            has_weights = config.custom_weights is not None and len(config.custom_weights) > 0
            results.append(ValidationResult(
                rule_id="R04",
                passed=has_weights,
                message="Custom allocation style requires custom_weights",
            ))

            if has_weights and config.custom_weights:
                total = sum(config.custom_weights.values())
                results.append(ValidationResult(
                    rule_id="R04b",
                    passed=abs(total - 1.0) < 0.01,
                    message=f"Custom weights must sum to ~1.0, got {total:.4f}",
                ))

        # R05: total_capital > 0
        results.append(ValidationResult(
            rule_id="R05",
            passed=config.total_capital > 0,
            message="total_capital must be positive",
        ))

        return results

    # ── Mini-TPI rules ─────────────────────────────────────────────────────

    @staticmethod
    def validate_mini_tpi(tpi: MiniTPI, *, min_indicators: int = 3) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        # R06: Minimum indicator count
        n = len(tpi.indicators)
        results.append(ValidationResult(
            rule_id="R06",
            passed=n >= min_indicators,
            message=f"TPI '{tpi.ticker}' has {n} indicators (min={min_indicators})",
            severity="warning" if n >= 1 else "error",
        ))

        # R07: No duplicate indicator names
        names = [i.name for i in tpi.indicators]
        dupes = [n for n in set(names) if names.count(n) > 1]
        results.append(ValidationResult(
            rule_id="R07",
            passed=len(dupes) == 0,
            message=f"Duplicate indicators in '{tpi.ticker}': {dupes}" if dupes else "OK",
        ))

        # R08: Mix of perpetual + oscillator
        perp_count = tpi.perpetual_count
        osc_count = tpi.oscillator_count
        results.append(ValidationResult(
            rule_id="R08",
            passed=perp_count > 0 and osc_count > 0,
            message=f"TPI '{tpi.ticker}': {perp_count} perpetual, {osc_count} oscillator — need both",
            severity="warning",
        ))

        # R09: Score bounds — ratio TPIs use ±1
        for ind in tpi.indicators:
            score = ind.effective_score
            if abs(score) > 1:
                results.append(ValidationResult(
                    rule_id="R09",
                    passed=False,
                    message=f"Indicator '{ind.name}' score {score} out of [-1, 1]",
                ))

        return results

    @staticmethod
    def validate_others_tpi(tpi: MiniTPI) -> list[ValidationResult]:
        """OTHERS.D TPI uses 0/1 scoring only."""
        results: list[ValidationResult] = []

        for ind in tpi.indicators:
            score = ind.effective_score
            if score not in (0, 1):
                results.append(ValidationResult(
                    rule_id="R10",
                    passed=False,
                    message=f"OTHERS.D indicator '{ind.name}' score {score} must be 0 or 1",
                ))

        if not results:
            results.append(ValidationResult(
                rule_id="R10",
                passed=True,
                message="OTHERS.D scoring OK",
            ))

        return results

    # ── Filter rules ───────────────────────────────────────────────────────

    @staticmethod
    def validate_filters(filters: list[TrashFilter]) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        # R11: At least 3 filters
        results.append(ValidationResult(
            rule_id="R11",
            passed=len(filters) >= 3,
            message=f"Need ≥3 trash filters, got {len(filters)}",
            severity="warning",
        ))

        # R12: No prohibited filter types
        for f in filters:
            if f.filter_type in PROHIBITED_FILTER_TYPES:
                results.append(ValidationResult(
                    rule_id="R12",
                    passed=False,
                    message=f"Filter '{f.name}' type '{f.filter_type}' is prohibited",
                ))

        # R13: No duplicate filter names
        names = [f.name for f in filters]
        dupes = [n for n in set(names) if names.count(n) > 1]
        results.append(ValidationResult(
            rule_id="R13",
            passed=len(dupes) == 0,
            message=f"Duplicate filter names: {dupes}" if dupes else "OK",
        ))

        # R14: At most 2 preliminary filters
        prelim = sum(1 for f in filters if f.is_preliminary)
        results.append(ValidationResult(
            rule_id="R14",
            passed=prelim <= 2,
            message=f"Too many preliminary filters ({prelim}), max 2",
            severity="warning",
        ))

        return results

    # ── Token rules ────────────────────────────────────────────────────────

    @staticmethod
    def validate_tokens(
        tokens: list[TrashToken], filters: list[TrashFilter],
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        # R15: At least 5 tokens in the tournament
        results.append(ValidationResult(
            rule_id="R15",
            passed=len(tokens) >= 5,
            message=f"Need ≥5 trash tokens, got {len(tokens)}",
            severity="warning",
        ))

        # R16: Every token has scores for all filters
        filter_names = {f.name for f in filters}
        for token in tokens:
            missing = filter_names - set(token.filter_scores.keys())
            if missing:
                results.append(ValidationResult(
                    rule_id="R16",
                    passed=False,
                    message=f"Token '{token.ticker}' missing scores: {missing}",
                ))

        # R17: Score values are 0 or 1
        for token in tokens:
            for fname, score in token.filter_scores.items():
                if score not in (0, 1):
                    results.append(ValidationResult(
                        rule_id="R17",
                        passed=False,
                        message=f"Token '{token.ticker}' filter '{fname}' score={score}, must be 0/1",
                    ))

        if all(r.passed for r in results):
            results.append(ValidationResult(
                rule_id="R15-R17",
                passed=True,
                message="Token validation OK",
            ))

        return results

    # ── Portfolio-level rules ──────────────────────────────────────────────

    @staticmethod
    def validate_portfolio(portfolio: RSPSPortfolio) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        # R18: Conservative allocations sum to ~1.0
        cons_total = sum(portfolio.conservative.allocations.values())
        results.append(ValidationResult(
            rule_id="R18",
            passed=abs(cons_total - 1.0) < 0.01,
            message=f"Conservative allocations sum={cons_total:.4f}",
        ))

        # R19: Trash tournament allocations sum to ~1.0 (if any qualifiers)
        if portfolio.trash_selection.qualifying_tokens:
            trash_total = sum(portfolio.trash_selection.allocations.values())
            results.append(ValidationResult(
                rule_id="R19",
                passed=abs(trash_total - 1.0) < 0.01,
                message=f"Trash allocations sum={trash_total:.4f}",
            ))

        # R20: No negative balances
        neg = {k: v for k, v in portfolio.balances.items() if v < 0}
        results.append(ValidationResult(
            rule_id="R20",
            passed=len(neg) == 0,
            message=f"Negative balances: {neg}" if neg else "OK",
        ))

        # R21: Total deployed ≤ total_capital
        deployed = sum(v for k, v in portfolio.balances.items() if k != "CASH")
        results.append(ValidationResult(
            rule_id="R21",
            passed=deployed <= portfolio.config.total_capital + 0.01,
            message=f"Deployed ${deployed:.2f} vs capital ${portfolio.config.total_capital:.2f}",
        ))

        # R22: NOT-LONG reduction applied correctly
        if not portfolio.totales.is_long:
            expected_max = portfolio.config.total_capital * portfolio.config.not_long_reduction
            results.append(ValidationResult(
                rule_id="R22",
                passed=deployed <= expected_max + 0.01,
                message=f"NOT-LONG: deployed ${deployed:.2f} ≤ cap×reduction ${expected_max:.2f}",
            ))

        return results

    # ── Full validation ────────────────────────────────────────────────────

    def validate_full(
        self,
        config: RSPSConfig,
        portfolio: RSPSPortfolio,
        ratio_tpis: dict[str, MiniTPI] | None = None,
        others_tpi: MiniTPI | None = None,
        filters: list[TrashFilter] | None = None,
        tokens: list[TrashToken] | None = None,
    ) -> RSPSValidationReport:
        """Run all applicable validation rules."""
        results: list[ValidationResult] = []

        results.extend(self.validate_config(config))

        if ratio_tpis:
            for key, tpi in ratio_tpis.items():
                results.extend(self.validate_mini_tpi(tpi))

        if others_tpi:
            results.extend(self.validate_others_tpi(others_tpi))
            results.extend(self.validate_mini_tpi(others_tpi))

        if filters:
            results.extend(self.validate_filters(filters))

        if tokens and filters:
            results.extend(self.validate_tokens(tokens, filters))

        results.extend(self.validate_portfolio(portfolio))

        return RSPSValidationReport(results=results)
