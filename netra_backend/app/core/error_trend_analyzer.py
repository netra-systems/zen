"""Core error trend analyzer with main analysis logic.

Primary interface for analyzing error patterns and trends with
modular helpers for specific calculations.
"""

from datetime import timedelta
from typing import Optional

from netra_backend.app.core.error_aggregation_base import (
    ErrorPattern, ErrorTrend, PatternHistory, TimeWindows
)
from netra_backend.app.core.error_pattern_helpers import ErrorPatternHelpers
from netra_backend.app.core.error_metric_calculator import ErrorMetricCalculator
from netra_backend.app.core.error_pattern_detector import ErrorPatternDetector
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorTrendAnalyzer:
    """Analyzes error trends and patterns."""
    
    def __init__(self, analysis_window_hours: int = 24):
        """Initialize trend analyzer."""
        self.analysis_window = timedelta(hours=analysis_window_hours)
        self.spike_threshold = 5.0  # 5x normal rate
        self.sustained_threshold_minutes = 30
        self._helpers = ErrorPatternHelpers()
        self._calculator = ErrorMetricCalculator()
        self._detector = ErrorPatternDetector(self.spike_threshold)
    
    def analyze_pattern_trend(
        self,
        pattern: ErrorPattern,
        error_history: PatternHistory
    ) -> ErrorTrend:
        """Analyze trend for specific error pattern."""
        pattern_history = self._helpers.filter_pattern_history(pattern, error_history)
        time_windows = self._helpers.create_time_windows(pattern_history)
        analysis_results = self._perform_trend_analysis(time_windows)
        return self._build_error_trend(pattern, time_windows, analysis_results)
    
    def _perform_trend_analysis(self, time_windows: TimeWindows) -> dict:
        """Perform comprehensive trend analysis."""
        metrics = self._calculator.calculate_trend_metrics(time_windows)
        patterns = self._detector.detect_patterns(time_windows)
        projection = self._calculator.project_future_occurrences(
            time_windows, metrics['growth_rate']
        )
        return {'metrics': metrics, 'patterns': patterns, 'projection': projection}
    
    def _build_error_trend(
        self, pattern: ErrorPattern, time_windows: TimeWindows, results: dict
    ) -> ErrorTrend:
        """Build ErrorTrend object from analysis results."""
        metrics = results['metrics']
        patterns = results['patterns']
        trend_params = self._create_trend_parameters(
            pattern, time_windows, metrics, patterns, results['projection']
        )
        return ErrorTrend(**trend_params)
    
    def _create_trend_parameters(
        self, pattern: ErrorPattern, time_windows: TimeWindows,
        metrics: dict, patterns: dict, projection: Optional[int]
    ) -> dict:
        """Create parameters for ErrorTrend construction."""
        return {
            'pattern': pattern,
            'time_windows': time_windows,
            'growth_rate': metrics['growth_rate'],
            'acceleration': metrics['acceleration'],
            'projection': projection,
            'is_spike': patterns['is_spike'],
            'is_sustained': patterns['is_sustained']
        }