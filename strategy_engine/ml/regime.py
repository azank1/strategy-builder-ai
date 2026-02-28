"""
Regime Detector — identify market regimes using Hidden Markov Models.

Detects accumulation, markup, distribution, and markdown phases
to contextualize SDCA valuations and LTPI trend signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd


class MarketRegime(str, Enum):
    ACCUMULATION = "accumulation"  # Low volatility, bottoming
    MARKUP = "markup"  # Rising prices, expanding vol
    DISTRIBUTION = "distribution"  # High volatility, topping
    MARKDOWN = "markdown"  # Falling prices, high vol


@dataclass
class RegimeState:
    """Current regime classification."""

    regime: MarketRegime
    probability: float  # Confidence in current regime
    duration_days: int  # How long in this regime

    @property
    def summary(self) -> str:
        return f"{self.regime.value} ({self.probability:.1%} confidence, {self.duration_days}d)"


@dataclass
class RegimeReport:
    """Full regime analysis report."""

    current_state: RegimeState
    regime_history: pd.Series  # DatetimeIndex → MarketRegime.value
    transition_matrix: dict[str, dict[str, float]]
    state_means: dict[str, float]  # Regime → average return
    state_volatilities: dict[str, float]  # Regime → average vol
    feature_names: list[str] = field(default_factory=list)


class RegimeDetector:
    """
    Detect market regimes using Gaussian HMM or simple momentum-based rules.

    If hmmlearn is available, uses a proper Hidden Markov Model.
    Otherwise, falls back to a rule-based approach using returns & volatility.

    Example:
        >>> detector = RegimeDetector(n_regimes=4)
        >>> report = detector.detect(price_series)
        >>> report.current_state.regime
        MarketRegime.MARKUP
    """

    def __init__(
        self,
        n_regimes: int = 4,
        lookback_vol: int = 30,
        lookback_trend: int = 60,
        use_hmm: bool = True,
    ):
        self.n_regimes = n_regimes
        self.lookback_vol = lookback_vol
        self.lookback_trend = lookback_trend
        self.use_hmm = use_hmm
        self._hmm_available = False

        if use_hmm:
            try:
                from hmmlearn.hmm import GaussianHMM  # noqa: F401
                self._hmm_available = True
            except ImportError:
                self._hmm_available = False

    def detect(self, prices: pd.Series) -> RegimeReport:
        """
        Detect market regime from price series.

        Args:
            prices: Historical price series with DatetimeIndex.

        Returns:
            RegimeReport with current state and history.
        """
        if self._hmm_available and self.use_hmm:
            return self._detect_hmm(prices)
        return self._detect_rules(prices)

    def _detect_hmm(self, prices: pd.Series) -> RegimeReport:
        """HMM-based regime detection."""
        from hmmlearn.hmm import GaussianHMM

        # Feature engineering
        returns = prices.pct_change().dropna()
        vol = returns.rolling(self.lookback_vol).std().dropna()
        momentum = prices.pct_change(self.lookback_trend).dropna()

        # Align all features
        features_df = pd.DataFrame({
            "returns": returns,
            "volatility": vol,
            "momentum": momentum,
        }).dropna()

        if len(features_df) < 100:
            return self._detect_rules(prices)

        X = features_df.values

        # Fit HMM
        model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=200,
            random_state=42,
        )
        model.fit(X)
        hidden_states = model.predict(X)
        state_probs = model.predict_proba(X)

        # Map HMM states to regime labels based on mean returns & volatility
        state_means = {}
        state_vols = {}
        for s in range(self.n_regimes):
            mask = hidden_states == s
            state_means[s] = float(features_df["returns"][mask].mean()) if mask.any() else 0.0
            state_vols[s] = float(features_df["volatility"][mask].mean()) if mask.any() else 0.0

        regime_map = self._map_states_to_regimes(state_means, state_vols)

        # Build history
        regime_labels = pd.Series(
            [regime_map[s].value for s in hidden_states],
            index=features_df.index,
            name="regime",
        )

        # Current state
        current_hmm = hidden_states[-1]
        current_regime = regime_map[current_hmm]
        current_prob = float(state_probs[-1, current_hmm])

        # Duration
        duration = 1
        for i in range(len(hidden_states) - 2, -1, -1):
            if hidden_states[i] == current_hmm:
                duration += 1
            else:
                break

        # Transition matrix
        trans = {}
        for s_from in range(self.n_regimes):
            label_from = regime_map[s_from].value
            trans[label_from] = {}
            for s_to in range(self.n_regimes):
                label_to = regime_map[s_to].value
                trans[label_from][label_to] = round(float(model.transmat_[s_from, s_to]), 4)

        return RegimeReport(
            current_state=RegimeState(
                regime=current_regime,
                probability=round(current_prob, 4),
                duration_days=duration,
            ),
            regime_history=regime_labels,
            transition_matrix=trans,
            state_means={regime_map[s].value: round(v, 6) for s, v in state_means.items()},
            state_volatilities={regime_map[s].value: round(v, 6) for s, v in state_vols.items()},
            feature_names=["returns", "volatility", "momentum"],
        )

    def _detect_rules(self, prices: pd.Series) -> RegimeReport:
        """Rule-based regime detection as fallback."""
        returns = prices.pct_change().dropna()
        vol = returns.rolling(self.lookback_vol).std().dropna()
        momentum = prices.pct_change(self.lookback_trend).dropna()

        features_df = pd.DataFrame({
            "returns": returns,
            "volatility": vol,
            "momentum": momentum,
        }).dropna()

        if features_df.empty:
            return RegimeReport(
                current_state=RegimeState(
                    regime=MarketRegime.ACCUMULATION,
                    probability=0.5,
                    duration_days=0,
                ),
                regime_history=pd.Series(dtype=str),
                transition_matrix={},
                state_means={},
                state_volatilities={},
            )

        # Median thresholds
        vol_median = vol.median()
        mom_median = momentum.median()

        regimes = []
        for _, row in features_df.iterrows():
            v = row["volatility"]
            m = row["momentum"]

            if m > mom_median and v <= vol_median:
                regimes.append(MarketRegime.MARKUP.value)
            elif m > mom_median and v > vol_median:
                regimes.append(MarketRegime.DISTRIBUTION.value)
            elif m <= mom_median and v > vol_median:
                regimes.append(MarketRegime.MARKDOWN.value)
            else:
                regimes.append(MarketRegime.ACCUMULATION.value)

        regime_series = pd.Series(regimes, index=features_df.index, name="regime")

        # Current state
        current = MarketRegime(regime_series.iloc[-1])
        duration = 1
        for i in range(len(regime_series) - 2, -1, -1):
            if regime_series.iloc[i] == current.value:
                duration += 1
            else:
                break

        # Simple transition matrix from observed frequencies
        trans: dict[str, dict[str, float]] = {}
        for r in MarketRegime:
            trans[r.value] = {r2.value: 0.0 for r2 in MarketRegime}

        for i in range(1, len(regime_series)):
            prev = regime_series.iloc[i - 1]
            curr = regime_series.iloc[i]
            trans[prev][curr] += 1.0

        # Normalize
        for r_from in trans:
            total = sum(trans[r_from].values())
            if total > 0:
                trans[r_from] = {k: round(v / total, 4) for k, v in trans[r_from].items()}

        return RegimeReport(
            current_state=RegimeState(
                regime=current,
                probability=0.75,  # Somewhat confident (rule-based)
                duration_days=duration,
            ),
            regime_history=regime_series,
            transition_matrix=trans,
            state_means={
                r.value: round(float(features_df["returns"][regime_series == r.value].mean()), 6)
                for r in MarketRegime
                if (regime_series == r.value).any()
            },
            state_volatilities={
                r.value: round(float(features_df["volatility"][regime_series == r.value].mean()), 6)
                for r in MarketRegime
                if (regime_series == r.value).any()
            },
        )

    def _map_states_to_regimes(
        self,
        state_means: dict[int, float],
        state_vols: dict[int, float],
    ) -> dict[int, MarketRegime]:
        """Map HMM state numbers to named regimes based on characteristics."""
        # Sort states by mean return
        sorted_by_return = sorted(state_means.keys(), key=lambda s: state_means[s])

        # Simple heuristic mapping for 4 regimes:
        # Lowest return = markdown, highest = markup
        # Among middle states: higher vol = distribution, lower vol = accumulation
        if self.n_regimes >= 4:
            mapping = {
                sorted_by_return[0]: MarketRegime.MARKDOWN,
                sorted_by_return[-1]: MarketRegime.MARKUP,
            }
            middle = sorted_by_return[1:-1]
            if len(middle) >= 2:
                if state_vols.get(middle[0], 0) > state_vols.get(middle[1], 0):
                    mapping[middle[0]] = MarketRegime.DISTRIBUTION
                    mapping[middle[1]] = MarketRegime.ACCUMULATION
                else:
                    mapping[middle[0]] = MarketRegime.ACCUMULATION
                    mapping[middle[1]] = MarketRegime.DISTRIBUTION
            elif middle:
                mapping[middle[0]] = MarketRegime.ACCUMULATION
        else:
            # 2-3 regime fallback
            mapping = {}
            for i, s in enumerate(sorted_by_return):
                if i == 0:
                    mapping[s] = MarketRegime.MARKDOWN
                elif i == len(sorted_by_return) - 1:
                    mapping[s] = MarketRegime.MARKUP
                else:
                    mapping[s] = MarketRegime.ACCUMULATION

        return mapping
