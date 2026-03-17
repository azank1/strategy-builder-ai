"""Conservative Trend Module — Q2: How to rank conservative assets?

For N assets, build C(N,2) ratio mini-TPIs (e.g. ETHBTC, SOLBTC, SOLETH…).
Each mini-TPI's average score tells us which asset in the pair is outperforming.
We count wins per asset across all its pairs, rank by wins, then allocate.
"""

from __future__ import annotations

from itertools import combinations

from strategy_engine.models_rsps import (
    AllocationStyle,
    ConservativeAllocation,
    MiniTPI,
    RSPSConfig,
)


class ConservativeTrendModule:
    """Rank N conservative assets via pairwise ratio mini-TPIs."""

    def __init__(self, config: RSPSConfig):
        self.config = config
        self.assets = config.conservative_assets
        self.pairs = config.required_ratio_pairs

    def evaluate(
        self,
        ratio_tpis: dict[str, MiniTPI],
    ) -> ConservativeAllocation:
        """Run full conservative ranking from a set of ratio mini-TPIs.

        Args:
            ratio_tpis: Mapping of "A/B" → MiniTPI for each pair.
                        Positive average ⇒ A outperforms B.

        Returns:
            ConservativeAllocation with rankings and weights.
        """
        self._validate_pairs(ratio_tpis)
        ratio_scores = {k: round(v.average_score, 4) for k, v in ratio_tpis.items()}
        wins = self._count_wins(ratio_tpis)
        rankings = self._rank_from_wins(wins)
        allocations = self._allocate(rankings)
        return ConservativeAllocation(
            allocations=allocations,
            rankings=rankings,
            ratio_scores=ratio_scores,
        )

    # ── internals ──────────────────────────────────────────────────────────

    def _validate_pairs(self, ratio_tpis: dict[str, MiniTPI]) -> None:
        """Ensure we have a TPI for every required pair."""
        for a, b in self.pairs:
            key = f"{a}/{b}"
            if key not in ratio_tpis:
                raise ValueError(f"Missing ratio mini-TPI for pair {key}")

    def _count_wins(self, ratio_tpis: dict[str, MiniTPI]) -> dict[str, int]:
        """Count how many pairwise comparisons each asset wins."""
        wins: dict[str, int] = {a: 0 for a in self.assets}
        for a, b in self.pairs:
            key = f"{a}/{b}"
            avg = ratio_tpis[key].average_score
            if avg > 0:
                wins[a] += 1       # numerator asset outperforming
            elif avg < 0:
                wins[b] += 1       # denominator asset outperforming
            # avg == 0 ⇒ neither gets a win (tie on this pair)
        return wins

    def _rank_from_wins(self, wins: dict[str, int]) -> dict[str, int]:
        """Rank assets by win count (higher rank = more wins).

        Uses dense ranking: tied assets share the same rank.
        """
        sorted_assets = sorted(wins.keys(), key=lambda a: wins[a])
        rankings: dict[str, int] = {}
        prev_wins = -1
        current_rank = -1
        for asset in sorted_assets:
            if wins[asset] != prev_wins:
                current_rank += 1
                prev_wins = wins[asset]
            rankings[asset] = current_rank
        return rankings

    def _allocate(self, rankings: dict[str, int]) -> dict[str, float]:
        """Convert ranks to allocation percentages."""
        n = len(self.assets)
        if n == 0:
            return {}

        max_rank = max(rankings.values()) if rankings else 0

        # Check for ties
        all_tied = len(set(rankings.values())) == 1
        if all_tied:
            equal = round(1.0 / n, 4)
            allocations = {a: equal for a in self.assets}
            # Fix rounding to sum exactly to 1.0
            diff = round(1.0 - sum(allocations.values()), 4)
            if diff != 0:
                first = next(iter(allocations))
                allocations[first] = round(allocations[first] + diff, 4)
            return allocations

        style = self.config.allocation_style

        if style == AllocationStyle.CUSTOM and self.config.custom_weights:
            return self._apply_custom_weights(rankings)

        if n == 2:
            return self._allocate_two(rankings, style)

        if n == 3:
            return self._allocate_three(rankings, style)

        if n == 4:
            return self._allocate_four(rankings, style)

        # Generic fallback for arbitrary N
        return self._allocate_generic(rankings)

    def _allocate_two(
        self, rankings: dict[str, int], style: AllocationStyle,
    ) -> dict[str, float]:
        """2-asset allocation (BTC, ETH only)."""
        if style == AllocationStyle.SPLIT_100_0:
            top = [a for a, r in rankings.items() if r == max(rankings.values())]
            return {a: (1.0 / len(top) if a in top else 0.0) for a in self.assets}

        # 80/20 default
        top = [a for a, r in rankings.items() if r == max(rankings.values())]
        bot = [a for a in self.assets if a not in top]
        alloc: dict[str, float] = {}
        for a in top:
            alloc[a] = round(0.8 / len(top), 4)
        for a in bot:
            alloc[a] = round(0.2 / len(bot), 4) if bot else 0.0
        return self._fix_rounding(alloc)

    def _allocate_three(
        self, rankings: dict[str, int], style: AllocationStyle,
    ) -> dict[str, float]:
        """3-asset allocation (BTC, ETH, SOL or BTC, ETH, GOLD)."""
        rank_groups = self._group_by_rank(rankings)

        if style == AllocationStyle.SPLIT_100_0:
            top_rank = max(rank_groups.keys())
            alloc = {}
            top_assets = rank_groups[top_rank]
            for a in self.assets:
                alloc[a] = round(1.0 / len(top_assets), 4) if a in top_assets else 0.0
            return self._fix_rounding(alloc)

        # 80/20 spread: top rank gets 80%, rest share 20%
        top_rank = max(rank_groups.keys())
        alloc = {}
        top_assets = rank_groups[top_rank]
        rest = [a for a in self.assets if a not in top_assets]
        for a in top_assets:
            alloc[a] = round(0.8 / len(top_assets), 4)
        for a in rest:
            alloc[a] = round(0.2 / len(rest), 4) if rest else 0.0
        return self._fix_rounding(alloc)

    def _allocate_four(
        self, rankings: dict[str, int], style: AllocationStyle,
    ) -> dict[str, float]:
        """4-asset allocation (BTC, ETH, SOL, GOLD).

        Spreadsheet logic: Rank 3=top, 2=second, 1=third, 0=weakest.
        80/20 ⇒ top gets 40%, second 30%, third 20%, bottom 10%.
        100/0 ⇒ top gets 50%, second 30%, third 20%, bottom 0%.
        """
        rank_groups = self._group_by_rank(rankings)

        if style == AllocationStyle.SPLIT_100_0:
            tiers = [0.50, 0.30, 0.20, 0.0]
        else:
            tiers = [0.40, 0.30, 0.20, 0.10]

        sorted_ranks = sorted(rank_groups.keys(), reverse=True)
        alloc: dict[str, float] = {}
        tier_idx = 0
        for rank in sorted_ranks:
            group = rank_groups[rank]
            # Assets at same rank share the sum of their tiers
            tier_sum = sum(tiers[tier_idx + j] for j in range(len(group))
                          if tier_idx + j < len(tiers))
            per_asset = round(tier_sum / len(group), 4)
            for a in group:
                alloc[a] = per_asset
            tier_idx += len(group)

        # Ensure all assets present
        for a in self.assets:
            if a not in alloc:
                alloc[a] = 0.0
        return self._fix_rounding(alloc)

    def _allocate_generic(self, rankings: dict[str, int]) -> dict[str, float]:
        """Fallback: proportional allocation by rank."""
        total_rank = sum(rankings.values())
        if total_rank == 0:
            equal = round(1.0 / len(self.assets), 4)
            return {a: equal for a in self.assets}
        alloc = {a: round(r / total_rank, 4) for a, r in rankings.items()}
        return self._fix_rounding(alloc)

    def _apply_custom_weights(self, rankings: dict[str, int]) -> dict[str, float]:
        """Apply user-defined weights per rank position."""
        weights = self.config.custom_weights or {}
        rank_groups = self._group_by_rank(rankings)
        sorted_ranks = sorted(rank_groups.keys(), reverse=True)

        alloc: dict[str, float] = {}
        for idx, rank in enumerate(sorted_ranks):
            group = rank_groups[rank]
            key = str(idx)
            weight = weights.get(key, 0.0)
            per_asset = round(weight / len(group), 4)
            for a in group:
                alloc[a] = per_asset

        for a in self.assets:
            if a not in alloc:
                alloc[a] = 0.0
        return self._fix_rounding(alloc)

    def _group_by_rank(self, rankings: dict[str, int]) -> dict[int, list[str]]:
        groups: dict[int, list[str]] = {}
        for asset, rank in rankings.items():
            groups.setdefault(rank, []).append(asset)
        return groups

    @staticmethod
    def _fix_rounding(alloc: dict[str, float]) -> dict[str, float]:
        """Adjust largest allocation so values sum to exactly 1.0."""
        if not alloc:
            return alloc
        total = sum(alloc.values())
        diff = round(1.0 - total, 4)
        if diff != 0:
            biggest = max(alloc, key=lambda k: alloc[k])
            alloc[biggest] = round(alloc[biggest] + diff, 4)
        return alloc
