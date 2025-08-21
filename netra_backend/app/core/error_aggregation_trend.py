"""Error trend analysis module - pattern analysis and prediction.

Provides sophisticated trend analysis functionality for error pattern
recognition, spike detection, and predictive analytics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import central_logger
from netra_backend.app.error_aggregation_utils import (
    ErrorPattern, ErrorTrend, ErrorPatternMatcher, 
    TimeWindowCalculator, TrendCalculationHelper
)

logger = central_logger.get_logger(__name__)


class ErrorTrendAnalyzer:
    """Analyzes error trends and patterns for predictive insights."""
    
    def __init__(self, analysis_window_hours: int = 24):
        """Initialize trend analyzer with configurable parameters."""
        self.analysis_window = timedelta(hours=analysis_window_hours)
        self.spike_threshold = 5.0  # 5x normal rate
        self.sustained_threshold_minutes = 30
        self.pattern_matcher = ErrorPatternMatcher()
        self.window_calculator = TimeWindowCalculator()
        self.trend_calculator = TrendCalculationHelper()
    
    def analyze_pattern_trend(
        self,
        pattern: ErrorPattern,
        error_history: List[Tuple[datetime, Dict[str, Any]]]
    ) -> ErrorTrend:
        """Analyze comprehensive trend for specific error pattern."""
        pattern_history = self._filter_pattern_history(pattern, error_history)
        time_windows = self.window_calculator.create_time_windows(pattern_history)
        return self._build_trend_from_windows(pattern, time_windows)
    
    def _build_trend_from_windows(self, pattern: ErrorPattern, time_windows: List[Tuple[datetime, int]]) -> ErrorTrend:
        """Build trend analysis from time windows."""
        trend_metrics = self._calculate_trend_metrics(time_windows)
        pattern_indicators = self._detect_pattern_indicators(time_windows)
        projection = self._project_future_occurrences(time_windows, trend_metrics['growth_rate'])
        return self._build_error_trend(pattern, time_windows, trend_metrics, pattern_indicators, projection)
    
    def _filter_pattern_history(
        self,
        pattern: ErrorPattern,
        error_history: List[Tuple[datetime, Dict[str, Any]]]
    ) -> List[Tuple[datetime, Dict[str, Any]]]:
        """Filter history for specific pattern signature."""
        return [
            (timestamp, data) for timestamp, data in error_history
            if self.pattern_matcher.matches_pattern(data, pattern.signature)
        ]
    
    def _calculate_trend_metrics(self, time_windows: List[Tuple[datetime, int]]) -> Dict[str, float]:
        """Calculate growth rate and acceleration metrics."""
        recent_windows = time_windows[-10:]  # Last 10 windows
        growth_rate = self.trend_calculator.calculate_linear_slope(recent_windows)
        recent_counts = [count for _, count in time_windows[-5:]]
        acceleration = self.trend_calculator.calculate_acceleration(recent_counts)
        return {'growth_rate': growth_rate, 'acceleration': acceleration}
    
    def _detect_pattern_indicators(self, time_windows: List[Tuple[datetime, int]]) -> Dict[str, bool]:
        """Detect spike and sustained error patterns."""
        return {
            'is_spike': self._detect_spike(time_windows),
            'is_sustained': self._detect_sustained_error(time_windows)
        }
    
    def _detect_spike(self, time_windows: List[Tuple[datetime, int]]) -> bool:
        """Detect error spikes based on historical baseline."""
        if len(time_windows) < 5:
            return False
        recent_counts = [count for _, count in time_windows[-5:]]
        baseline = self._calculate_baseline(recent_counts[:-1])
        current_count = recent_counts[-1]
        return self._is_spike_detected(baseline, current_count)
    
    def _calculate_baseline(self, historical_counts: List[int]) -> float:
        """Calculate baseline error rate from historical data."""
        return sum(historical_counts) / len(historical_counts) if historical_counts else 0.0
    
    def _is_spike_detected(self, baseline: float, current_count: int) -> bool:
        """Determine if current count represents a spike."""
        if baseline == 0:
            return current_count > 10  # Arbitrary spike threshold for zero baseline
        return current_count / baseline >= self.spike_threshold
    
    def _detect_sustained_error(self, time_windows: List[Tuple[datetime, int]]) -> bool:
        """Detect sustained error patterns over time."""
        if not time_windows:
            return False
        sustained_windows = self._count_active_windows(time_windows[-6:])  # Last hour
        return sustained_windows >= 4  # At least 4 out of 6 windows have errors
    
    def _count_active_windows(self, recent_windows: List[Tuple[datetime, int]]) -> int:
        """Count windows with error occurrences."""
        return sum(1 for _, count in recent_windows if count > 0)
    
    def _project_future_occurrences(
        self,
        time_windows: List[Tuple[datetime, int]],
        growth_rate: float
    ) -> Optional[int]:
        """Project future error occurrences based on trend."""
        if not time_windows or growth_rate <= 0:
            return None
        recent_average = self._calculate_recent_average(time_windows[-3:])
        projection = int(recent_average + growth_rate * 3)
        return max(0, projection)
    
    def _calculate_recent_average(self, recent_windows: List[Tuple[datetime, int]]) -> float:
        """Calculate average from recent time windows."""
        counts = [count for _, count in recent_windows]
        return sum(counts) / len(counts) if counts else 0.0
    
    def _build_error_trend(
        self,
        pattern: ErrorPattern,
        time_windows: List[Tuple[datetime, int]],
        metrics: Dict[str, float],
        indicators: Dict[str, bool],
        projection: Optional[int]
    ) -> ErrorTrend:
        """Build complete ErrorTrend object from analysis."""
        return ErrorTrend(
            pattern=pattern,
            time_windows=time_windows,
            growth_rate=metrics['growth_rate'],
            acceleration=metrics['acceleration'],
            projection=projection,
            is_spike=indicators['is_spike'],
            is_sustained=indicators['is_sustained']
        )