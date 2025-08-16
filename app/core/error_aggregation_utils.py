"""Error aggregation utilities - data models and signature extraction.

Provides core data structures and signature extraction functionality
for error pattern recognition and categorization.
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.error_codes import ErrorSeverity


class AggregationLevel(Enum):
    """Levels of error aggregation for different analysis phases."""
    IMMEDIATE = "immediate"      # Real-time individual errors
    WINDOWED = "windowed"        # Time-windowed aggregation
    PATTERN = "pattern"          # Pattern-based grouping
    TREND = "trend"             # Trend analysis
    PREDICTIVE = "predictive"   # Predictive analysis


class AlertSeverity(Enum):
    """Alert severity levels for escalation and prioritization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorSignature:
    """Unique signature for error pattern identification."""
    error_type: str
    module: str
    function: str
    pattern_hash: str
    key_terms: List[str] = field(default_factory=list)


@dataclass
class ErrorPattern:
    """Aggregated error pattern with occurrence tracking."""
    signature: ErrorSignature
    count: int = 0
    first_occurrence: datetime = field(default_factory=datetime.now)
    last_occurrence: datetime = field(default_factory=datetime.now)
    severity_distribution: Dict[ErrorSeverity, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    affected_users: Set[str] = field(default_factory=set)
    affected_operations: Set[str] = field(default_factory=set)
    sample_errors: List[Dict[str, Any]] = field(default_factory=list)
    trend_score: float = 0.0


@dataclass
class ErrorTrend:
    """Error trend analysis data with predictive metrics."""
    pattern: ErrorPattern
    time_windows: List[Tuple[datetime, int]] = field(default_factory=list)
    growth_rate: float = 0.0
    acceleration: float = 0.0
    projection: Optional[int] = None
    is_spike: bool = False
    is_sustained: bool = False


@dataclass
class AlertRule:
    """Rule definition for generating alerts from patterns."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression for evaluation
    severity: AlertSeverity
    threshold_count: int = 0
    threshold_rate: float = 0.0
    time_window_minutes: int = 60
    cooldown_minutes: int = 30
    active: bool = True


@dataclass
class ErrorAlert:
    """Generated error alert with pattern and rule context."""
    alert_id: str
    rule: AlertRule
    pattern: ErrorPattern
    trend: Optional[ErrorTrend]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    message: str = ""


class ErrorSignatureExtractor:
    """Extracts unique signatures from error data for pattern recognition."""
    
    def __init__(self):
        """Initialize with predefined key terms for categorization."""
        self.key_terms = self._get_default_key_terms()
    
    def extract_signature(self, error_data: Dict[str, Any]) -> ErrorSignature:
        """Extract error signature from error data."""
        error_components = self._extract_error_components(error_data)
        key_terms = self._extract_key_terms(error_components['message'])
        pattern_hash = self._create_pattern_hash(error_components, key_terms)
        return self._build_signature(error_components, pattern_hash, key_terms)
    
    def _build_signature(self, components: Dict[str, str], pattern_hash: str, key_terms: List[str]) -> ErrorSignature:
        """Build ErrorSignature from components."""
        return ErrorSignature(
            error_type=components['error_type'],
            module=components['module'],
            function=components['function'],
            pattern_hash=pattern_hash,
            key_terms=key_terms
        )
    
    def _get_default_key_terms(self) -> Set[str]:
        """Get default set of key terms for error categorization."""
        return {
            'connection', 'timeout', 'permission', 'not found',
            'memory', 'disk', 'network', 'authentication',
            'validation', 'constraint', 'deadlock', 'overflow'
        }
    
    def _extract_error_components(self, error_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract basic error components from data."""
        return {
            'error_type': error_data.get('error_type', 'Unknown'),
            'module': error_data.get('module', 'unknown'),
            'function': error_data.get('function', 'unknown'),
            'message': str(error_data.get('message', '')).lower()
        }
    
    def _extract_key_terms(self, message: str) -> List[str]:
        """Extract relevant key terms from error message."""
        return [
            term for term in self.key_terms
            if term in message
        ]
    
    def _create_pattern_hash(self, components: Dict[str, str], key_terms: List[str]) -> str:
        """Create unique hash for error pattern."""
        pattern_components = self._build_pattern_components(components, key_terms)
        pattern_string = '|'.join(pattern_components)
        return hashlib.md5(pattern_string.encode()).hexdigest()[:16]
    
    def _build_pattern_components(self, components: Dict[str, str], key_terms: List[str]) -> List[str]:
        """Build components for pattern hash generation."""
        return [
            components['error_type'],
            components['module'],
            components['function'],
            ' '.join(sorted(key_terms))
        ]


class ErrorPatternMatcher:
    """Utility for matching errors to existing patterns."""
    
    def matches_pattern(self, error_data: Dict[str, Any], signature: ErrorSignature) -> bool:
        """Check if error matches pattern signature."""
        return (
            error_data.get('error_type') == signature.error_type and
            error_data.get('module') == signature.module and
            error_data.get('function') == signature.function
        )


class TimeWindowCalculator:
    """Utility for time-based calculations and windowing."""
    
    def create_time_windows(
        self,
        pattern_history: List[Tuple[datetime, Dict[str, Any]]],
        window_minutes: int = 10
    ) -> List[Tuple[datetime, int]]:
        """Create time windows with error counts."""
        if not pattern_history:
            return []
        config = self._setup_window_config(pattern_history, window_minutes)
        return self._generate_windows(pattern_history, config)
    
    def _setup_window_config(
        self,
        pattern_history: List[Tuple[datetime, Dict[str, Any]]],
        window_minutes: int
    ) -> Dict[str, Any]:
        """Setup configuration for window generation."""
        from datetime import timedelta
        return {
            'window_size': timedelta(minutes=window_minutes),
            'start_time': pattern_history[0][0],
            'end_time': datetime.now()
        }
    
    def _generate_windows(
        self,
        pattern_history: List[Tuple[datetime, Dict[str, Any]]],
        config: Dict[str, Any]
    ) -> List[Tuple[datetime, int]]:
        """Generate time windows with error counts."""
        windows = []
        current_time = config['start_time']
        while current_time < config['end_time']:
            window_end = current_time + config['window_size']
            count = self._count_errors_in_window(pattern_history, current_time, window_end)
            windows.append((current_time, count))
            current_time = window_end
        return windows
    
    def _count_errors_in_window(
        self,
        pattern_history: List[Tuple[datetime, Dict[str, Any]]],
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count errors within specific time window."""
        return sum(
            1 for timestamp, _ in pattern_history
            if start_time <= timestamp < end_time
        )


class TrendCalculationHelper:
    """Helper for statistical calculations in trend analysis."""
    
    def calculate_linear_slope(self, recent_windows: List[Tuple[datetime, int]]) -> float:
        """Calculate linear slope for trend analysis."""
        if len(recent_windows) < 2:
            return 0.0
        x_values, y_values = self._prepare_slope_data(recent_windows)
        return self._compute_slope(x_values, y_values)
    
    def calculate_acceleration(self, recent_counts: List[int]) -> float:
        """Calculate acceleration as second derivative."""
        if len(recent_counts) < 3:
            return 0.0
        first_diffs = self._calculate_first_differences(recent_counts)
        second_diffs = self._calculate_second_differences(first_diffs)
        return sum(second_diffs) / len(second_diffs) if second_diffs else 0.0
    
    def _prepare_slope_data(self, recent_windows: List[Tuple[datetime, int]]) -> Tuple[List[int], List[int]]:
        """Prepare data arrays for slope calculation."""
        x_values = list(range(len(recent_windows)))
        y_values = [count for _, count in recent_windows]
        return x_values, y_values
    
    def _compute_slope(self, x_values: List[int], y_values: List[int]) -> float:
        """Compute linear regression slope."""
        n = len(x_values)
        sum_x, sum_y = sum(x_values), sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        denominator = n * sum_x2 - sum_x * sum_x
        return (n * sum_xy - sum_x * sum_y) / denominator if denominator != 0 else 0.0
    
    def _calculate_first_differences(self, values: List[int]) -> List[int]:
        """Calculate first differences between consecutive values."""
        return [
            values[i + 1] - values[i]
            for i in range(len(values) - 1)
        ]
    
    def _calculate_second_differences(self, first_diffs: List[int]) -> List[int]:
        """Calculate second differences from first differences."""
        return [
            first_diffs[i + 1] - first_diffs[i]
            for i in range(len(first_diffs) - 1)
        ]