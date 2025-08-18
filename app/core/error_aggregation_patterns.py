"""Error trend analysis and pattern detection.

Analyzes error patterns for trends, spikes, and sustained issues to
enable proactive system monitoring and alerting.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.core.error_aggregation_base import (
    ErrorData, ErrorPattern, ErrorSignature, ErrorTrend, 
    PatternHistory, TimeWindows
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorTrendAnalyzer:
    """Analyzes error trends and patterns."""
    
    def __init__(self, analysis_window_hours: int = 24):
        """Initialize trend analyzer."""
        self.analysis_window = timedelta(hours=analysis_window_hours)
        self.spike_threshold = 5.0  # 5x normal rate
        self.sustained_threshold_minutes = 30
    
    def analyze_pattern_trend(
        self,
        pattern: ErrorPattern,
        error_history: PatternHistory
    ) -> ErrorTrend:
        """Analyze trend for specific error pattern."""
        pattern_history = self._filter_pattern_history(pattern, error_history)
        time_windows = self._create_time_windows(pattern_history)
        analysis_results = self._perform_trend_analysis(time_windows)
        return self._build_error_trend(pattern, time_windows, analysis_results)
    
    def _perform_trend_analysis(self, time_windows: TimeWindows) -> dict:
        """Perform comprehensive trend analysis."""
        metrics = self._calculate_trend_metrics(time_windows)
        patterns = self._detect_patterns(time_windows)
        projection = self._project_future_occurrences(
            time_windows, metrics['growth_rate']
        )
        return {'metrics': metrics, 'patterns': patterns, 'projection': projection}
    
    def _build_error_trend(
        self, pattern: ErrorPattern, time_windows: TimeWindows, results: dict
    ) -> ErrorTrend:
        """Build ErrorTrend object from analysis results."""
        metrics = results['metrics']
        patterns = results['patterns']
        return ErrorTrend(
            pattern=pattern,
            time_windows=time_windows,
            growth_rate=metrics['growth_rate'],
            acceleration=metrics['acceleration'],
            projection=results['projection'],
            is_spike=patterns['is_spike'],
            is_sustained=patterns['is_sustained']
        )
    
    def _filter_pattern_history(
        self, 
        pattern: ErrorPattern, 
        error_history: PatternHistory
    ) -> PatternHistory:
        """Filter history for specific pattern."""
        return [
            (timestamp, data) for timestamp, data in error_history
            if self._matches_pattern(data, pattern.signature)
        ]
    
    def _matches_pattern(
        self,
        error_data: ErrorData,
        signature: ErrorSignature
    ) -> bool:
        """Check if error matches pattern signature."""
        return (
            error_data.get('error_type') == signature.error_type and
            error_data.get('module') == signature.module and
            error_data.get('function') == signature.function
        )
    
    def _create_time_windows(
        self,
        pattern_history: PatternHistory,
        window_minutes: int = 10
    ) -> TimeWindows:
        """Create time windows with error counts."""
        if not pattern_history:
            return []
        
        window_size = timedelta(minutes=window_minutes)
        start_time = pattern_history[0][0]
        end_time = datetime.now()
        
        return self._build_windows(
            pattern_history, start_time, end_time, window_size
        )
    
    def _build_windows(
        self,
        pattern_history: PatternHistory,
        start_time: datetime,
        end_time: datetime,
        window_size: timedelta
    ) -> TimeWindows:
        """Build time windows with counts."""
        windows = []
        current_time = start_time
        while current_time < end_time:
            window_end = current_time + window_size
            self._add_window_count(windows, pattern_history, current_time, window_end)
            current_time = window_end
        return windows
    
    def _add_window_count(
        self, windows: list, pattern_history: PatternHistory, 
        current_time: datetime, window_end: datetime
    ) -> None:
        """Add window with error count to windows list."""
        count = self._count_errors_in_window(
            pattern_history, current_time, window_end
        )
        windows.append((current_time, count))
    
    def _count_errors_in_window(
        self,
        pattern_history: PatternHistory,
        start: datetime,
        end: datetime
    ) -> int:
        """Count errors in time window."""
        return sum(
            1 for timestamp, _ in pattern_history
            if start <= timestamp < end
        )
    
    def _calculate_trend_metrics(self, time_windows: TimeWindows) -> dict:
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
        
        recent_windows = time_windows[-10:]  # Last 10 windows
        
        if len(recent_windows) < 2:
            return 0.0
        
        return self._compute_slope(recent_windows)
    
    def _compute_slope(self, windows: TimeWindows) -> float:
        """Compute slope using simple linear regression."""
        x_values = list(range(len(windows)))
        y_values = [count for _, count in windows]
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        return (n * sum_xy - sum_x * sum_y) / denominator
    
    def _calculate_acceleration(self, time_windows: TimeWindows) -> float:
        """Calculate acceleration in error rate."""
        if len(time_windows) < 3:
            return 0.0
        
        recent_counts = [count for _, count in time_windows[-5:]]
        
        if len(recent_counts) < 3:
            return 0.0
        
        return self._compute_second_derivative(recent_counts)
    
    def _compute_second_derivative(self, counts: List[int]) -> float:
        """Compute second derivative for acceleration."""
        first_diffs = [
            counts[i + 1] - counts[i]
            for i in range(len(counts) - 1)
        ]
        
        second_diffs = [
            first_diffs[i + 1] - first_diffs[i]
            for i in range(len(first_diffs) - 1)
        ]
        
        return sum(second_diffs) / len(second_diffs) if second_diffs else 0.0
    
    def _detect_patterns(self, time_windows: TimeWindows) -> dict:
        """Detect spike and sustained patterns."""
        return {
            'is_spike': self._detect_spike(time_windows),
            'is_sustained': self._detect_sustained_error(time_windows)
        }
    
    def _detect_spike(self, time_windows: TimeWindows) -> bool:
        """Detect error spikes."""
        if len(time_windows) < 5:
            return False
        
        recent_counts = [count for _, count in time_windows[-5:]]
        baseline = self._calculate_baseline(recent_counts[:-1])
        current = recent_counts[-1]
        
        if baseline == 0:
            return current > 10  # Arbitrary spike threshold
        
        return current / baseline >= self.spike_threshold
    
    def _calculate_baseline(self, counts: List[int]) -> float:
        """Calculate baseline from count list."""
        return sum(counts) / len(counts) if counts else 0.0
    
    def _detect_sustained_error(self, time_windows: TimeWindows) -> bool:
        """Detect sustained error patterns."""
        if not time_windows:
            return False
        
        # Check last hour (6 * 10min windows)
        sustained_windows = sum(
            1 for _, count in time_windows[-6:]
            if count > 0
        )
        
        return sustained_windows >= 4  # At least 4 out of 6 windows have errors
    
    def _project_future_occurrences(
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