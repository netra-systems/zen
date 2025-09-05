"""Analysis Engine Helper Methods

Modular helper functions for statistical analysis operations.
Maintains the 25-line function limit and provides reusable utilities.

Business Value: Supports critical data analysis features for customer insights.
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np


class StatisticsHelpers:
    """Helper methods for statistical calculations."""
    
    @staticmethod
    def _empty_statistics() -> Dict[str, float]:
        """Return empty statistics structure."""
        return {
            "count": 0, "mean": 0.0, "median": 0.0, "std_dev": 0.0,
            "std": 0.0, "min": 0.0, "max": 0.0, "p25": 0.0,
            "p75": 0.0, "p95": 0.0, "p99": 0.0
        }
    
    @staticmethod
    def _compute_comprehensive_stats(values: List[float]) -> Dict[str, float]:
        """Compute comprehensive statistics from values."""
        arr = np.array(values)
        std_value = float(np.std(arr))
        basic_stats = StatisticsHelpers._calculate_basic_stats(arr, std_value, len(values))
        percentile_stats = StatisticsHelpers._calculate_percentiles(arr)
        return {**basic_stats, **percentile_stats}
    
    @staticmethod
    def _calculate_basic_stats(arr, std_value: float, count: int) -> Dict[str, float]:
        """Calculate basic statistics."""
        central_stats = StatisticsHelpers._calculate_central_tendency(arr, count)
        spread_stats = StatisticsHelpers._calculate_spread_measures(std_value)
        range_stats = StatisticsHelpers._calculate_range_measures(arr)
        return {**central_stats, **spread_stats, **range_stats}
    
    @staticmethod
    def _calculate_central_tendency(arr, count: int) -> Dict[str, float]:
        """Calculate central tendency statistics."""
        return {
            "count": count,
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr))
        }
    
    @staticmethod
    def _calculate_spread_measures(std_value: float) -> Dict[str, float]:
        """Calculate measures of spread."""
        return {
            "std_dev": std_value,
            "std": std_value
        }
    
    @staticmethod
    def _calculate_range_measures(arr) -> Dict[str, float]:
        """Calculate range-based measures."""
        return {
            "min": float(np.min(arr)),
            "max": float(np.max(arr))
        }
    
    @staticmethod
    def _calculate_percentiles(arr) -> Dict[str, float]:
        """Calculate percentile statistics."""
        return {
            "p25": float(np.percentile(arr, 25)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99))
        }


class TrendHelpers:
    """Helper methods for trend analysis."""
    
    @staticmethod
    def _perform_trend_analysis(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Perform trend analysis on prepared data."""
        x_norm, y = TrendHelpers._prepare_trend_data(values, timestamps)
        if x_norm is None:
            return {"has_trend": False, "reason": "no_time_variation"}
        return TrendHelpers._compute_trend_parameters(x_norm, y)
    
    @staticmethod
    def _compute_trend_parameters(x_norm, y) -> Dict[str, Any]:
        """Compute trend parameters and build result."""
        slope, intercept, r_squared = TrendHelpers._calculate_linear_regression(x_norm, y)
        return TrendHelpers._build_trend_result(slope, intercept, r_squared, x_norm)
    
    @staticmethod
    def _prepare_trend_data(values: List[float], timestamps: List[datetime]):
        """Prepare data for trend analysis."""
        x, y = TrendHelpers._convert_to_numeric_arrays(values, timestamps)
        x_std = np.std(x)
        if x_std == 0:
            return None, None
        return TrendHelpers._normalize_time_data(x, y)
    
    @staticmethod
    def _convert_to_numeric_arrays(values: List[float], timestamps: List[datetime]):
        """Convert values and timestamps to numeric arrays."""
        time_numeric = [(t - timestamps[0]).total_seconds() for t in timestamps]
        x = np.array(time_numeric)
        y = np.array(values)
        return x, y
    
    @staticmethod
    def _normalize_time_data(x, y):
        """Normalize time data for trend analysis."""
        x_norm = (x - np.mean(x)) / np.std(x)
        return x_norm, y
    
    @staticmethod
    def _calculate_linear_regression(x_norm, y):
        """Calculate linear regression parameters."""
        slope = np.cov(x_norm, y)[0, 1] / np.var(x_norm)
        intercept = np.mean(y) - slope * np.mean(x_norm)
        
        y_pred = slope * x_norm + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return slope, intercept, r_squared
    
    @staticmethod
    def _build_trend_result(slope: float, intercept: float, r_squared: float, x_norm):
        """Build trend analysis result."""
        trend_direction = "increasing" if slope > 0 else "decreasing"
        trend_strength = "strong" if abs(r_squared) > 0.7 else "moderate" if abs(r_squared) > 0.4 else "weak"
        
        return {
            "has_trend": abs(r_squared) > 0.2,
            "direction": trend_direction,
            "strength": trend_strength,
            "slope": float(slope),
            "r_squared": float(r_squared),
            "predicted_next": float(slope * (x_norm[-1] + 3600) + intercept)
        }


class SeasonalityHelpers:
    """Helper methods for seasonality analysis."""
    
    @staticmethod
    def _perform_seasonality_analysis(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Perform comprehensive seasonality analysis."""
        hourly_groups = SeasonalityHelpers._group_by_hour(values, timestamps)
        hourly_means = {h: np.mean(vals) for h, vals in hourly_groups.items()}
        return SeasonalityHelpers._validate_and_analyze_seasonality(hourly_means)
    
    @staticmethod
    def _validate_and_analyze_seasonality(hourly_means: Dict[int, float]) -> Dict[str, Any]:
        """Validate hourly coverage and analyze seasonality patterns."""
        if len(hourly_means) < 12:
            return {"has_seasonality": False, "reason": "insufficient_hourly_coverage"}
        return SeasonalityHelpers._analyze_seasonality_patterns(hourly_means)
    
    @staticmethod
    def _group_by_hour(values: List[float], timestamps: List[datetime]) -> Dict[int, List[float]]:
        """Group values by hour of day."""
        hourly_groups = {}
        for ts, val in zip(timestamps, values):
            hour = ts.hour
            if hour not in hourly_groups:
                hourly_groups[hour] = []
            hourly_groups[hour].append(val)
        return hourly_groups
    
    @staticmethod
    def _analyze_seasonality_patterns(hourly_means: Dict[int, float]) -> Dict[str, Any]:
        """Analyze seasonality patterns from hourly means."""
        cv, has_daily_pattern = SeasonalityHelpers._calculate_daily_pattern_metrics(hourly_means)
        peak_hour, low_hour = SeasonalityHelpers._find_peak_and_low_hours(hourly_means)
        daily_pattern = SeasonalityHelpers._build_daily_pattern_info(peak_hour, low_hour, hourly_means, cv)
        return SeasonalityHelpers._build_seasonality_result(has_daily_pattern, daily_pattern, hourly_means)
    
    @staticmethod
    def _calculate_daily_pattern_metrics(hourly_means: Dict[int, float]) -> tuple:
        """Calculate coefficient of variation and pattern detection."""
        overall_mean = np.mean(list(hourly_means.values()))
        hourly_variance = np.var(list(hourly_means.values()))
        cv = np.sqrt(hourly_variance) / overall_mean if overall_mean != 0 else 0
        has_daily_pattern = cv > 0.2
        return cv, has_daily_pattern
    
    @staticmethod
    def _find_peak_and_low_hours(hourly_means: Dict[int, float]) -> tuple:
        """Find peak and low hours from hourly means."""
        peak_hour = max(hourly_means, key=hourly_means.get)
        low_hour = min(hourly_means, key=hourly_means.get)
        return peak_hour, low_hour
    
    @staticmethod
    def _build_daily_pattern_info(peak_hour: int, low_hour: int, hourly_means: Dict, cv: float) -> Dict[str, Any]:
        """Build daily pattern information structure."""
        return {
            "peak_hour": peak_hour, "peak_value": hourly_means[peak_hour],
            "low_hour": low_hour, "low_value": hourly_means[low_hour],
            "coefficient_of_variation": float(cv)
        }
    
    @staticmethod
    def _build_seasonality_result(has_daily_pattern: bool, daily_pattern: Dict, hourly_means: Dict) -> Dict[str, Any]:
        """Build complete seasonality analysis result."""
        return {
            "has_seasonality": has_daily_pattern,
            "daily_pattern": daily_pattern,
            "hourly_averages": hourly_means
        }


class OutlierHelpers:
    """Helper methods for outlier detection."""
    
    @staticmethod
    def _has_sufficient_data_for_outliers(values: List[float]) -> bool:
        """Check if there is sufficient data for outlier detection."""
        return len(values) >= 4
    
    @staticmethod
    def _apply_outlier_detection_method(arr, method: str) -> List[int]:
        """Apply the specified outlier detection method."""
        if method == "iqr":
            return OutlierHelpers._identify_iqr_outliers(arr)
        elif method == "zscore":
            return OutlierHelpers._identify_zscore_outliers(arr)
        return []
    
    @staticmethod
    def _identify_iqr_outliers(arr) -> List[int]:
        """Identify outliers using IQR method."""
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outlier_indices = []
        for i, val in enumerate(arr):
            if val < lower_bound or val > upper_bound:
                outlier_indices.append(i)
        return outlier_indices
    
    @staticmethod
    def _identify_zscore_outliers(arr) -> List[int]:
        """Identify outliers using Z-score method."""
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return []
        
        outlier_indices = []
        for i, val in enumerate(arr):
            z_score = abs((val - mean) / std)
            if z_score >= 3:
                outlier_indices.append(i)
        return outlier_indices