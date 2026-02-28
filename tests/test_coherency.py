"""Tests for the coherency analyzer."""

import numpy as np
import pandas as pd
import pytest

from strategy_engine.core.coherency import CoherencyAnalyzer, CoherencyReport


@pytest.fixture
def analyzer() -> CoherencyAnalyzer:
    return CoherencyAnalyzer()


class TestCoherency:
    def test_perfectly_coherent(self, analyzer: CoherencyAnalyzer) -> None:
        """All indicators agree at every time step."""
        signals = pd.DataFrame({
            "a": [1, 1, -1, -1, 1, 1, -1],
            "b": [1, 1, -1, -1, 1, 1, -1],
            "c": [1, 1, -1, -1, 1, 1, -1],
        })
        report = analyzer.analyze(signals)
        assert report.agreement_ratio == 1.0
        assert report.constructive_ratio == 1.0
        assert report.is_coherent

    def test_perfectly_destructive(self, analyzer: CoherencyAnalyzer) -> None:
        """Half agree, half disagree at every step."""
        signals = pd.DataFrame({
            "a": [1, 1, 1, 1],
            "b": [-1, -1, -1, -1],
        })
        report = analyzer.analyze(signals)
        # 50% agreement at each row
        assert report.agreement_ratio == pytest.approx(0.5, abs=0.01)

    def test_mixed_coherency(self, analyzer: CoherencyAnalyzer) -> None:
        """Some agreement, some not."""
        signals = pd.DataFrame({
            "a": [1, 1, -1, -1, 1],
            "b": [1, -1, -1, 1, 1],
            "c": [1, 1, -1, -1, -1],
        })
        report = analyzer.analyze(signals)
        assert 0.0 < report.agreement_ratio < 1.0

    def test_empty_dataframe(self, analyzer: CoherencyAnalyzer) -> None:
        signals = pd.DataFrame()
        report = analyzer.analyze(signals)
        assert report.is_coherent

    def test_single_indicator(self, analyzer: CoherencyAnalyzer) -> None:
        signals = pd.DataFrame({"a": [1, -1, 1]})
        report = analyzer.analyze(signals)
        assert report.is_coherent

    def test_per_indicator_alignment(self, analyzer: CoherencyAnalyzer) -> None:
        signals = pd.DataFrame({
            "good": [1, 1, -1, -1, 1],
            "good2": [1, 1, -1, -1, 1],
            "bad": [-1, -1, 1, 1, -1],
        })
        report = analyzer.analyze(signals)
        assert report.per_indicator_alignment["good"] > report.per_indicator_alignment["bad"]


class TestFindOutliers:
    def test_find_outlier_indicator(self, analyzer: CoherencyAnalyzer) -> None:
        signals = pd.DataFrame({
            "a": [1, 1, -1, -1, 1, 1],
            "b": [1, 1, -1, -1, 1, 1],
            "c": [1, 1, -1, -1, 1, 1],
            "outlier": [-1, -1, 1, 1, -1, -1],
        })
        outliers = analyzer.find_outlier_indicators(signals, threshold=0.5)
        assert "outlier" in outliers

    def test_no_outliers_in_coherent_system(self, analyzer: CoherencyAnalyzer) -> None:
        signals = pd.DataFrame({
            "a": [1, -1, 1, -1],
            "b": [1, -1, 1, -1],
        })
        outliers = analyzer.find_outlier_indicators(signals)
        assert len(outliers) == 0
