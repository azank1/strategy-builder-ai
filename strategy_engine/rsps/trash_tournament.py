"""Trash Tournament Module — Q4: Which altcoins qualify?

Runs N tokens through M quantitative filters.
1. Preliminary filters: instant disqualification if failed.
2. Standard filters: 0/1 scoring.
3. Threshold: total_score >= threshold to qualify.
4. Equal-weight allocation among qualifiers.
"""

from __future__ import annotations

from strategy_engine.models_rsps import (
    PROHIBITED_FILTER_TYPES,
    RSPSConfig,
    TournamentResult,
    TrashFilter,
    TrashToken,
)


class TrashTournament:
    """Filter engine for trash (altcoin) token selection."""

    def __init__(self, config: RSPSConfig):
        self.config = config
        self.threshold = config.trash_threshold

    def evaluate(
        self,
        tokens: list[TrashToken],
        filters: list[TrashFilter],
    ) -> TournamentResult:
        """Run the full tournament.

        1. Validate filters (no prohibited types).
        2. Apply preliminary filters — disqualify failures.
        3. Score remaining tokens across standard filters.
        4. Apply threshold — select qualifiers.
        5. Equal-weight allocate among qualifiers.
        """
        self._validate_filters(filters)

        # Preliminary gate
        surviving = [t for t in tokens if t.passes_preliminary(filters)]

        # Score and select qualifiers
        qualifying_tickers: list[str] = []
        for token in surviving:
            if token.qualifies(self.threshold):
                qualifying_tickers.append(token.ticker)

        # Equal-weight allocation
        n_qual = len(qualifying_tickers)
        allocations: dict[str, float] = {}
        if n_qual > 0:
            per_token = round(1.0 / n_qual, 4)
            for ticker in qualifying_tickers:
                allocations[ticker] = per_token
            # Fix rounding
            diff = round(1.0 - sum(allocations.values()), 4)
            if diff != 0:
                allocations[qualifying_tickers[0]] = round(
                    allocations[qualifying_tickers[0]] + diff, 4
                )

        # Build score matrix for display
        score_matrix = {
            t.ticker: dict(t.filter_scores) for t in tokens
        }

        return TournamentResult(
            all_tokens=tokens,
            qualifying_tokens=qualifying_tickers,
            allocations=allocations,
            threshold_used=self.threshold,
            score_matrix=score_matrix,
        )

    @staticmethod
    def _validate_filters(filters: list[TrashFilter]) -> None:
        """Ensure no prohibited filter types snuck in."""
        for f in filters:
            if f.filter_type in PROHIBITED_FILTER_TYPES:
                raise ValueError(
                    f"Filter '{f.name}' uses prohibited type '{f.filter_type}'"
                )
