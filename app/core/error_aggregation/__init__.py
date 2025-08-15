"""Error aggregation system package.

Provides sophisticated error pattern recognition, trend analysis, 
and intelligent alerting to proactively identify system issues.
"""

from .models import (
    AggregationLevel,
    AlertSeverity,
    ErrorSignature,
    ErrorPattern,
    ErrorTrend,
    AlertRule,
    ErrorAlert,
)

from .error_processor import (
    ErrorSignatureExtractor,
    ErrorAggregator,
)

from .trend_analyzer import ErrorTrendAnalyzer
from .alert_engine import AlertEngine
from .aggregation_system import ErrorAggregationSystem

__all__ = [
    # Models
    "AggregationLevel",
    "AlertSeverity", 
    "ErrorSignature",
    "ErrorPattern",
    "ErrorTrend",
    "AlertRule",
    "ErrorAlert",
    # Components
    "ErrorSignatureExtractor",
    "ErrorAggregator",
    "ErrorTrendAnalyzer",
    "AlertEngine",
    "ErrorAggregationSystem",
]