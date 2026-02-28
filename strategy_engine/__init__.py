"""
Strategy Engine — Open-source quantitative allocation signal toolkit.

Modules:
    core        Z-scoring, composite signals, indicator validation
    data        Data source adapters and ingestion pipelines
    ml          Machine learning: decay detection, correlation, regime detection
    models      Pydantic data models for indicators, systems, signals
"""

__version__ = "0.1.0"

from strategy_engine.models import (
    AssetClass,
    CombinedSignal,
    LTPISystem,
    SDCASystem,
    SignalStrength,
)

__all__ = [
    "AssetClass",
    "CombinedSignal",
    "LTPISystem",
    "SDCASystem",
    "SignalStrength",
]
