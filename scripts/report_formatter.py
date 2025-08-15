#!/usr/bin/env python
"""
Report Formatter for Enhanced Test Reporter
Re-exports formatters from split modules to maintain compatibility
"""

# Import all formatters from split modules
from .report_formatter_base import (
    ReportHeaderFormatter,
    TestResultsFormatter,
    CategoryFormatter
)

from .report_formatter_advanced import (
    PerformanceFormatter,
    FailureFormatter,
    RecommendationFormatter,
    ChangeFormatter
)

# Re-export all classes for backward compatibility
__all__ = [
    'ReportHeaderFormatter',
    'TestResultsFormatter', 
    'CategoryFormatter',
    'PerformanceFormatter',
    'FailureFormatter',
    'RecommendationFormatter',
    'ChangeFormatter'
]