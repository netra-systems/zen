"""Error pattern detection for spikes and sustained errors.

Detects abnormal error patterns including sudden spikes and
sustained error conditions for alerting and monitoring.
"""

from typing import List

from app.core.error_aggregation_base import TimeWindows


class ErrorPatternDetector:
    """Detector for error patterns like spikes and sustained errors."""
    
    def __init__(self, spike_threshold: float = 5.0):
        """Initialize pattern detector."""
        self.spike_threshold = spike_threshold
    
    def detect_patterns(self, time_windows: TimeWindows) -> dict:
        """Detect spike and sustained patterns."""
        return {
            'is_spike': self._detect_spike(time_windows),
            'is_sustained': self._detect_sustained_error(time_windows)
        }
    
    def _detect_spike(self, time_windows: TimeWindows) -> bool:
        """Detect error spikes."""
        if len(time_windows) < 5:
            return False
        
        spike_data = self._prepare_spike_analysis_data(time_windows)
        return self._evaluate_spike_condition(spike_data)
    
    def _prepare_spike_analysis_data(self, time_windows: TimeWindows) -> dict:
        """Prepare data for spike analysis."""
        recent_counts = [count for _, count in time_windows[-5:]]
        return {
            'baseline': self._calculate_baseline(recent_counts[:-1]),
            'current': recent_counts[-1]
        }
    
    def _evaluate_spike_condition(self, spike_data: dict) -> bool:
        """Evaluate whether spike condition is met."""
        if spike_data['baseline'] == 0:
            return spike_data['current'] > 10  # Arbitrary spike threshold
        
        return spike_data['current'] / spike_data['baseline'] >= self.spike_threshold
    
    def _calculate_baseline(self, counts: List[int]) -> float:
        """Calculate baseline from count list."""
        return sum(counts) / len(counts) if counts else 0.0
    
    def _detect_sustained_error(self, time_windows: TimeWindows) -> bool:
        """Detect sustained error patterns."""
        if not time_windows:
            return False
        
        sustained_windows = self._count_sustained_windows(time_windows)
        return sustained_windows >= 4  # At least 4 out of 6 windows have errors
    
    def _count_sustained_windows(self, time_windows: TimeWindows) -> int:
        """Count windows with sustained errors in last hour."""
        # Check last hour (6 * 10min windows)
        return sum(
            1 for _, count in time_windows[-6:]
            if count > 0
        )