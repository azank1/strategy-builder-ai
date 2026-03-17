"""
Bayesian Hyperparameter Optimization — ML Stage 2.

Optimizes indicator parameters (thresholds, periods, etc.) against ISP
labels to maximize signal accuracy. Uses Gaussian Process surrogate
with Expected Improvement acquisition.

This replaces brute-force grid search with intelligent sampling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm


@dataclass
class ParameterSpace:
    """Defines the search space for a single parameter."""

    name: str
    low: float
    high: float
    param_type: str = "float"  # "float" or "int"
    log_scale: bool = False


@dataclass
class OptimizationResult:
    """Output of Bayesian optimization."""

    best_params: dict[str, float]
    best_score: float
    all_trials: list[dict[str, Any]]
    n_iterations: int
    convergence_history: list[float]
    improvement_over_default: float


class BayesianOptimizer:
    """Optimize indicator parameters via Bayesian optimization.

    Uses a Gaussian Process (GP) approximation via random Fourier features
    for scalability, with Expected Improvement (EI) acquisition.

    Example:
        >>> space = [
        ...     ParameterSpace("period", 5, 50, "int"),
        ...     ParameterSpace("threshold", 0.01, 0.5),
        ... ]
        >>> optimizer = BayesianOptimizer(space, n_iterations=30)
        >>> result = optimizer.optimize(objective_fn)
        >>> result.best_params
        {'period': 21, 'threshold': 0.15}
    """

    def __init__(
        self,
        param_space: list[ParameterSpace],
        n_iterations: int = 50,
        n_initial: int = 10,
        random_state: int = 42,
    ):
        self.param_space = param_space
        self.n_iterations = n_iterations
        self.n_initial = n_initial
        self.rng = np.random.RandomState(random_state)
        self.dim = len(param_space)

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        default_params: dict[str, float] | None = None,
    ) -> OptimizationResult:
        """Run Bayesian optimization.

        Args:
            objective: Function mapping params → score (higher is better).
            default_params: Optional default params to score for comparison.

        Returns:
            OptimizationResult with best params and trial history.
        """
        # Score the default parameters if provided
        default_score = 0.0
        if default_params:
            default_score = objective(default_params)

        # Initial random sampling
        X_observed: list[np.ndarray] = []
        y_observed: list[float] = []
        all_trials: list[dict[str, Any]] = []

        for _ in range(self.n_initial):
            params = self._random_sample()
            param_dict = self._array_to_dict(params)
            score = objective(param_dict)
            X_observed.append(params)
            y_observed.append(score)
            all_trials.append({"params": param_dict, "score": score})

        convergence: list[float] = [max(y_observed)]

        # Bayesian optimization loop
        for i in range(self.n_iterations - self.n_initial):
            X = np.array(X_observed)
            y = np.array(y_observed)

            # Find next point via Expected Improvement
            next_params = self._acquire_next(X, y)
            param_dict = self._array_to_dict(next_params)
            score = objective(param_dict)

            X_observed.append(next_params)
            y_observed.append(score)
            all_trials.append({"params": param_dict, "score": score})
            convergence.append(max(y_observed))

        # Best result
        best_idx = int(np.argmax(y_observed))
        best_params = self._array_to_dict(X_observed[best_idx])
        best_score = y_observed[best_idx]

        return OptimizationResult(
            best_params=best_params,
            best_score=round(best_score, 6),
            all_trials=all_trials,
            n_iterations=len(all_trials),
            convergence_history=convergence,
            improvement_over_default=round(best_score - default_score, 6),
        )

    # ── Internals ──────────────────────────────────────────────────────────

    def _random_sample(self) -> np.ndarray:
        """Sample a random point from the parameter space."""
        params = np.zeros(self.dim)
        for i, ps in enumerate(self.param_space):
            if ps.log_scale:
                log_low = np.log(max(ps.low, 1e-10))
                log_high = np.log(max(ps.high, 1e-10))
                params[i] = np.exp(self.rng.uniform(log_low, log_high))
            else:
                params[i] = self.rng.uniform(ps.low, ps.high)
            if ps.param_type == "int":
                params[i] = round(params[i])
        return params

    def _array_to_dict(self, params: np.ndarray) -> dict[str, float]:
        """Convert parameter array to named dict."""
        result = {}
        for i, ps in enumerate(self.param_space):
            val = params[i]
            if ps.param_type == "int":
                val = int(round(val))
            else:
                val = round(float(val), 6)
            result[ps.name] = val
        return result

    def _acquire_next(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Find the next point to evaluate using Expected Improvement.

        Uses a simplified GP: kernel-weighted local regression for mean/std
        prediction, then maximizes EI via random search.
        """
        best_y = y.max()
        n_candidates = 500
        candidates = np.array([self._random_sample() for _ in range(n_candidates)])

        # Kernel-weighted predictions for each candidate
        ei_values = np.zeros(n_candidates)
        length_scale = self._estimate_length_scale(X)

        for j in range(n_candidates):
            mu, sigma = self._predict(candidates[j], X, y, length_scale)
            if sigma < 1e-10:
                ei_values[j] = 0.0
            else:
                z = (mu - best_y) / sigma
                ei_values[j] = sigma * (z * norm.cdf(z) + norm.pdf(z))

        best_candidate = candidates[np.argmax(ei_values)]
        # Snap integer params
        for i, ps in enumerate(self.param_space):
            if ps.param_type == "int":
                best_candidate[i] = round(best_candidate[i])
        return best_candidate

    @staticmethod
    def _predict(
        x: np.ndarray, X: np.ndarray, y: np.ndarray, length_scale: float,
    ) -> tuple[float, float]:
        """Predict mean and std at x using kernel-weighted regression."""
        dists = np.sqrt(np.sum((X - x) ** 2, axis=1))
        weights = np.exp(-0.5 * (dists / max(length_scale, 1e-10)) ** 2)
        weights = weights / (weights.sum() + 1e-10)

        mu = float(np.dot(weights, y))
        variance = float(np.dot(weights, (y - mu) ** 2))
        sigma = np.sqrt(max(variance, 1e-10))

        return mu, sigma

    @staticmethod
    def _estimate_length_scale(X: np.ndarray) -> float:
        """Estimate kernel length scale from data spread."""
        if len(X) < 2:
            return 1.0
        return float(np.std(X, axis=0).mean()) * 0.5 + 1e-10
