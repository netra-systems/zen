"""Quality-Enhanced WebSocket Message Handler - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All classes have been split into focused modules ≤300 lines with functions ≤8 lines.
"""

# Import all modular components for backward compatibility
from .quality_metrics_handler import QualityMetricsHandler
from .quality_alert_handler import QualityAlertHandler
from .quality_enhanced_start_handler import QualityEnhancedStartAgentHandler
from .quality_validation_handler import QualityValidationHandler
from .quality_report_handler import QualityReportHandler
from .quality_manager import WebSocketQualityManager

# Re-export all classes for backward compatibility
__all__ = [
    "QualityMetricsHandler",
    "QualityAlertHandler", 
    "QualityEnhancedStartAgentHandler",
    "QualityValidationHandler",
    "QualityReportHandler",
    "WebSocketQualityManager"
]
