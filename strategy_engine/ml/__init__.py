"""
ML sub-package — machine learning utilities for strategy analysis.

- Alpha decay detection
- Correlation matrix & redundancy analysis  
- Regime detection (Hidden Markov Models)
- Repainting detection
"""

from strategy_engine.ml.decay import AlphaDecayDetector
from strategy_engine.ml.correlation import CorrelationAnalyzer
from strategy_engine.ml.regime import RegimeDetector

__all__ = [
    "AlphaDecayDetector",
    "CorrelationAnalyzer",
    "RegimeDetector",
]
