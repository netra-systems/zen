"""Error pattern aggregation and intelligent reporting system.

REFACTORED: This file now imports from modular components that comply
with 450-line module and 25-line function requirements while maintaining
backward compatibility for existing code.
"""

# Import all classes and components from the new modular architecture
from .error_aggregation_utils import (
    AggregationLevel, AlertSeverity, ErrorSignature, ErrorPattern, 
    ErrorTrend, AlertRule, ErrorAlert, ErrorSignatureExtractor
)
from .error_aggregation_core import ErrorAggregator, ErrorAggregationSystem
from .error_aggregation_trend import ErrorTrendAnalyzer
from .error_aggregation_alerts import AlertEngine

# Re-export the global system instance for backward compatibility
from .error_aggregation_core import error_aggregation_system

# Maintain backward compatibility for any code importing these classes
__all__ = [
    'AggregationLevel',
    'AlertSeverity', 
    'ErrorSignature',
    'ErrorPattern',
    'ErrorTrend',
    'AlertRule',
    'ErrorAlert',
    'ErrorSignatureExtractor',
    'ErrorAggregator',
    'ErrorTrendAnalyzer',
    'AlertEngine',
    'ErrorAggregationSystem',
    'error_aggregation_system'
]