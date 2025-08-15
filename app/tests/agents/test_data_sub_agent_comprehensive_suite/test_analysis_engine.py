"""
Tests for AnalysisEngine class methods
"""

import pytest
import numpy as np
from datetime import datetime
from app.agents.data_sub_agent.analysis_engine import AnalysisEngine


class TestAnalysisEngine:
    """Test AnalysisEngine class methods"""
    
    def test_calculate_statistics_empty(self):
        """Test statistics calculation with empty data"""
        stats = AnalysisEngine.calculate_statistics([])
        assert stats["count"] == 0
        assert stats["mean"] == 0
        assert stats["median"] == 0
        assert stats["std_dev"] == 0
        
    def test_calculate_statistics_single_value(self):
        """Test statistics calculation with single value"""
        stats = AnalysisEngine.calculate_statistics([5.0])
        assert stats["count"] == 1
        assert stats["mean"] == 5.0
        assert stats["median"] == 5.0
        assert stats["min"] == 5.0
        assert stats["max"] == 5.0
        
    def test_calculate_statistics_multiple_values(self):
        """Test statistics calculation with multiple values"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        stats = AnalysisEngine.calculate_statistics(values)
        assert stats["count"] == 10
        assert stats["mean"] == 5.5
        assert stats["median"] == 5.5
        assert stats["min"] == 1.0
        assert stats["max"] == 10.0
        assert stats["p25"] == pytest.approx(3.25, rel=0.01)
        assert stats["p75"] == pytest.approx(7.75, rel=0.01)
        assert stats["p95"] == pytest.approx(9.55, rel=0.01)
        assert stats["p99"] == pytest.approx(9.91, rel=0.01)
        
    def test_detect_trend_insufficient_data(self):
        """Test trend detection with insufficient data"""
        values = [1.0, 2.0]
        timestamps = [datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 1)]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == False
        assert trend["reason"] == "insufficient_data"
        
    def test_detect_trend_no_time_variation(self):
        """Test trend detection with no time variation"""
        values = [1.0, 2.0, 3.0]
        timestamps = [datetime(2024, 1, 1, 12, 0)] * 3  # Same timestamp
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == False
        assert trend["reason"] == "no_time_variation"
        
    def test_detect_trend_increasing(self):
        """Test trend detection with increasing values"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 12, 15),
            datetime(2024, 1, 1, 12, 30),
            datetime(2024, 1, 1, 12, 45),
            datetime(2024, 1, 1, 13, 0)
        ]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == True
        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0
        
    def test_detect_trend_decreasing(self):
        """Test trend detection with decreasing values"""
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 12, 15),
            datetime(2024, 1, 1, 12, 30),
            datetime(2024, 1, 1, 12, 45),
            datetime(2024, 1, 1, 13, 0)
        ]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        assert trend["has_trend"] == True
        assert trend["direction"] == "decreasing"
        assert trend["slope"] < 0
        
    def test_detect_trend_weak(self):
        """Test trend detection with weak correlation"""
        values = [1.0, 2.0, 1.5, 2.5, 2.0]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 12, 15),
            datetime(2024, 1, 1, 12, 30),
            datetime(2024, 1, 1, 12, 45),
            datetime(2024, 1, 1, 13, 0)
        ]
        trend = AnalysisEngine.detect_trend(values, timestamps)
        if trend["has_trend"]:
            assert trend["strength"] in ["weak", "moderate"]
            
    def test_detect_seasonality_insufficient_data(self):
        """Test seasonality detection with insufficient data"""
        values = [1.0] * 10  # Less than 24 points
        timestamps = [datetime(2024, 1, 1, i, 0) for i in range(10)]
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        assert seasonality["has_seasonality"] == False
        assert seasonality["reason"] == "insufficient_data"
        
    def test_detect_seasonality_insufficient_hourly_coverage(self):
        """Test seasonality detection with insufficient hourly coverage"""
        # Create 24 data points but only in 6 different hours
        values = []
        timestamps = []
        for hour in range(6):
            for _ in range(4):
                values.append(float(hour))
                timestamps.append(datetime(2024, 1, 1, hour, 0))
        
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        assert seasonality["has_seasonality"] == False
        assert seasonality["reason"] == "insufficient_hourly_coverage"
        
    def test_detect_seasonality_with_pattern(self):
        """Test seasonality detection with daily pattern"""
        values = []
        timestamps = []
        # Create data with clear hourly pattern over 2 days
        for day in range(2):
            for hour in range(24):
                # Peak at noon, low at midnight
                value = 100 + 50 * np.sin((hour - 6) * np.pi / 12)
                values.append(value)
                timestamps.append(datetime(2024, 1, day + 1, hour, 0))
                
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        assert seasonality["has_seasonality"] == True
        assert "daily_pattern" in seasonality
        assert "peak_hour" in seasonality["daily_pattern"]
        assert "low_hour" in seasonality["daily_pattern"]
        
    def test_detect_seasonality_no_pattern(self):
        """Test seasonality detection with no pattern"""
        values = []
        timestamps = []
        # Create random data
        np.random.seed(42)
        for day in range(2):
            for hour in range(24):
                values.append(100.0 + np.random.randn())  # Small variation
                timestamps.append(datetime(2024, 1, day + 1, hour, 0))
                
        seasonality = AnalysisEngine.detect_seasonality(values, timestamps)
        # With small random variation, should not detect seasonality
        assert seasonality["has_seasonality"] == False
        
    def test_identify_outliers_insufficient_data(self):
        """Test outlier identification with insufficient data"""
        outliers = AnalysisEngine.identify_outliers([1.0, 2.0, 3.0])
        assert outliers == []
        
    def test_identify_outliers_iqr_method(self):
        """Test outlier identification using IQR method"""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]  # 100 is an outlier
        outliers = AnalysisEngine.identify_outliers(values, method="iqr")
        assert 9 in outliers  # Index of value 100
        
    def test_identify_outliers_zscore_method(self):
        """Test outlier identification using Z-score method"""
        values = [10, 10, 10, 10, 10, 10, 10, 10, 10, 51]  # 51 is an outlier (z-score > 3)
        outliers = AnalysisEngine.identify_outliers(values, method="zscore")
        assert 9 in outliers  # Index of value 51
        
    def test_identify_outliers_zscore_no_variance(self):
        """Test outlier identification with no variance"""
        values = [5.0] * 10  # All same values
        outliers = AnalysisEngine.identify_outliers(values, method="zscore")
        assert outliers == []
        
    def test_identify_outliers_invalid_method(self):
        """Test outlier identification with invalid method"""
        values = [1, 2, 3, 4, 5, 100]
        outliers = AnalysisEngine.identify_outliers(values, method="invalid")
        assert outliers == []  # Should return empty list for invalid method