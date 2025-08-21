"""Error pattern filtering and time window creation helpers.

Provides utilities for filtering error history by patterns and creating
time-based analysis windows for trend detection.
"""

from datetime import datetime, timedelta

from netra_backend.app.core.error_aggregation_base import (
    ErrorData, ErrorPattern, ErrorSignature, PatternHistory, TimeWindows
)


class ErrorPatternHelpers:
    """Helper functions for error pattern processing."""
    
    def filter_pattern_history(
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
    
    def create_time_windows(
        self,
        pattern_history: PatternHistory,
        window_minutes: int = 10
    ) -> TimeWindows:
        """Create time windows with error counts."""
        if not pattern_history:
            return []
        
        window_config = self._prepare_window_config(pattern_history, window_minutes)
        return self._build_windows(
            pattern_history, window_config['start'], 
            window_config['end'], window_config['size']
        )
    
    def _prepare_window_config(
        self, pattern_history: PatternHistory, window_minutes: int
    ) -> dict:
        """Prepare window configuration parameters."""
        return {
            'size': timedelta(minutes=window_minutes),
            'start': pattern_history[0][0],
            'end': datetime.now()
        }
    
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
        self._populate_windows(windows, pattern_history, current_time, end_time, window_size)
        return windows
    
    def _populate_windows(
        self, windows: list, pattern_history: PatternHistory,
        current_time: datetime, end_time: datetime, window_size: timedelta
    ) -> None:
        """Populate windows list with time windows and counts."""
        while current_time < end_time:
            window_end = current_time + window_size
            self._add_window_count(windows, pattern_history, current_time, window_end)
            current_time = window_end
    
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