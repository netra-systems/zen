"""Error metric calculation utilities for trend analysis.

Provides growth rate, acceleration calculations, and future occurrence 
projections for error pattern analysis.
"""

from typing import List, Optional

from netra_backend.app.core.error_aggregation_base import TimeWindows


class ErrorMetricCalculator:
    """Calculator for error trend metrics."""
    
    def calculate_trend_metrics(self, time_windows: TimeWindows) -> dict:
        """Calculate growth rate and acceleration."""
        growth_rate = self._calculate_growth_rate(time_windows)
        acceleration = self._calculate_acceleration(time_windows)
        
        return {
            'growth_rate': growth_rate,
            'acceleration': acceleration
        }
    
    def _calculate_growth_rate(self, time_windows: TimeWindows) -> float:
        """Calculate error growth rate using linear regression."""
        if len(time_windows) < 2:
            return 0.0
        
        recent_windows = self._get_recent_windows(time_windows)
        if len(recent_windows) < 2:
            return 0.0
        
        return self._compute_slope(recent_windows)
    
    def _get_recent_windows(self, time_windows: TimeWindows) -> TimeWindows:
        """Get recent windows for analysis."""
        return time_windows[-10:]  # Last 10 windows
    
    def _compute_slope(self, windows: TimeWindows) -> float:
        """Compute slope using simple linear regression."""
        x_values = list(range(len(windows)))
        y_values = [count for _, count in windows]
        
        regression_data = self._calculate_regression_sums(x_values, y_values)
        denominator = self._calculate_denominator(x_values, regression_data)
        
        if denominator == 0:
            return 0.0
        
        return self._calculate_slope_value(regression_data, denominator)
    
    def _calculate_regression_sums(self, x_values: List[int], y_values: List[int]) -> dict:
        """Calculate sums needed for regression."""
        return {
            'n': len(x_values),
            'sum_x': sum(x_values),
            'sum_y': sum(y_values),
            'sum_xy': sum(x * y for x, y in zip(x_values, y_values)),
            'sum_x2': sum(x * x for x in x_values)
        }
    
    def _calculate_denominator(self, x_values: List[int], sums: dict) -> float:
        """Calculate regression denominator."""
        return sums['n'] * sums['sum_x2'] - sums['sum_x'] * sums['sum_x']
    
    def _calculate_slope_value(self, sums: dict, denominator: float) -> float:
        """Calculate final slope value."""
        return (sums['n'] * sums['sum_xy'] - sums['sum_x'] * sums['sum_y']) / denominator
    
    def _calculate_acceleration(self, time_windows: TimeWindows) -> float:
        """Calculate acceleration in error rate."""
        if len(time_windows) < 3:
            return 0.0
        
        recent_counts = self._extract_recent_counts(time_windows)
        if len(recent_counts) < 3:
            return 0.0
        
        return self._compute_second_derivative(recent_counts)
    
    def _extract_recent_counts(self, time_windows: TimeWindows) -> List[int]:
        """Extract recent error counts from time windows."""
        return [count for _, count in time_windows[-5:]]
    
    def _compute_second_derivative(self, counts: List[int]) -> float:
        """Compute second derivative for acceleration."""
        first_diffs = self._calculate_first_differences(counts)
        second_diffs = self._calculate_second_differences(first_diffs)
        return self._calculate_average_derivative(second_diffs)
    
    def _calculate_first_differences(self, counts: List[int]) -> List[int]:
        """Calculate first differences between consecutive counts."""
        return [
            counts[i + 1] - counts[i]
            for i in range(len(counts) - 1)
        ]
    
    def _calculate_second_differences(self, first_diffs: List[int]) -> List[int]:
        """Calculate second differences from first differences."""
        return [
            first_diffs[i + 1] - first_diffs[i]
            for i in range(len(first_diffs) - 1)
        ]
    
    def _calculate_average_derivative(self, second_diffs: List[int]) -> float:
        """Calculate average second derivative."""
        return sum(second_diffs) / len(second_diffs) if second_diffs else 0.0
    
    def project_future_occurrences(
        self,
        time_windows: TimeWindows,
        growth_rate: float
    ) -> Optional[int]:
        """Project future error occurrences."""
        if not time_windows or growth_rate <= 0:
            return None
        
        recent_average = self._calculate_recent_average(time_windows)
        projection = int(recent_average + growth_rate * 3)
        
        return max(0, projection)
    
    def _calculate_recent_average(self, time_windows: TimeWindows) -> float:
        """Calculate average of recent windows."""
        recent_counts = [count for _, count in time_windows[-3:]]
        return sum(recent_counts) / len(recent_counts) if recent_counts else 0.0