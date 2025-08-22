"""Error aggregation system package.

Provides sophisticated error pattern recognition, trend analysis, 
and intelligent alerting to proactively identify system issues.
"""

from netra_backend.app.aggregation_system import ErrorAggregationSystem
from netra_backend.app.alert_engine import AlertEngine
from netra_backend.app.error_processor import (
    ErrorAggregator,
    ErrorSignatureExtractor,
)
from netra_backend.app.services.apex_optimizer_agent.models import (
    AggregationLevel,
    AlertRule,
    AlertSeverity,
    ErrorAlert,
    ErrorPattern,
    ErrorSignature,
    ErrorTrend,
)
from netra_backend.app.trend_analyzer import ErrorTrendAnalyzer

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