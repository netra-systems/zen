"""Error aggregation system package.

Provides sophisticated error pattern recognition, trend analysis, 
and intelligent alerting to proactively identify system issues.
"""

from netra_backend.app.services.apex_optimizer_agent.models import (
    AggregationLevel,
    AlertSeverity,
    ErrorSignature,
    ErrorPattern,
    ErrorTrend,
    AlertRule,
    ErrorAlert,
)

from netra_backend.app.error_processor import (
    ErrorSignatureExtractor,
    ErrorAggregator,
)

from netra_backend.app.trend_analyzer import ErrorTrendAnalyzer
from netra_backend.app.alert_engine import AlertEngine
from netra_backend.app.aggregation_system import ErrorAggregationSystem

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