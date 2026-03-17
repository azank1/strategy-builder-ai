"""
ML sub-package — machine learning utilities for strategy analysis.

- Alpha decay detection
- Correlation matrix & redundancy analysis  
- Regime detection (Hidden Markov Models)
- ISP labeling (Intended Signal Period)
- Bayesian hyperparameter optimization
- Feature extraction pipeline
- Timeframe scaling
"""

from strategy_engine.ml.decay import AlphaDecayDetector
from strategy_engine.ml.correlation import CorrelationAnalyzer
from strategy_engine.ml.regime import RegimeDetector
from strategy_engine.ml.isp import ISPLabeler
from strategy_engine.ml.optimization import BayesianOptimizer
from strategy_engine.ml.features import FeatureExtractor
from strategy_engine.ml.timeframe import TimeframeScaler

__all__ = [
    "AlphaDecayDetector",
    "CorrelationAnalyzer",
    "RegimeDetector",
    "ISPLabeler",
    "BayesianOptimizer",
    "FeatureExtractor",
    "TimeframeScaler",
]
