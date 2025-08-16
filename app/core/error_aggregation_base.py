"""Core interfaces and data structures for error aggregation system.

Contains enums, dataclasses, and base types used throughout the error
aggregation system. Maintains strong typing and single source of truth.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.error_codes import ErrorSeverity


class AggregationLevel(Enum):
    """Levels of error aggregation."""
    IMMEDIATE = "immediate"      # Real-time individual errors
    WINDOWED = "windowed"        # Time-windowed aggregation
    PATTERN = "pattern"          # Pattern-based grouping
    TREND = "trend"             # Trend analysis
    PREDICTIVE = "predictive"   # Predictive analysis


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorSignature:
    """Unique signature for error patterns."""
    error_type: str
    module: str
    function: str
    pattern_hash: str
    key_terms: List[str] = field(default_factory=list)


@dataclass
class ErrorPattern:
    """Aggregated error pattern."""
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
    """Error trend analysis data."""
    pattern: ErrorPattern
    time_windows: List[Tuple[datetime, int]] = field(default_factory=list)
    growth_rate: float = 0.0
    acceleration: float = 0.0
    projection: Optional[int] = None
    is_spike: bool = False
    is_sustained: bool = False


@dataclass
class AlertRule:
    """Rule for generating alerts."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression
    severity: AlertSeverity
    threshold_count: int = 0
    threshold_rate: float = 0.0
    time_window_minutes: int = 60
    cooldown_minutes: int = 30
    active: bool = True


@dataclass
class ErrorAlert:
    """Generated error alert."""
    alert_id: str
    rule: AlertRule
    pattern: ErrorPattern
    trend: Optional[ErrorTrend]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    message: str = ""


# Type aliases for better readability
ErrorData = Dict[str, Any]
PatternHistory = List[Tuple[datetime, ErrorData]]
TimeWindows = List[Tuple[datetime, int]]