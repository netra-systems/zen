"""
Logging Unit Tests Package

This package contains comprehensive unit tests for the SSOT (Single Source of Truth) 
logging system that consolidates all logging functionality across the Netra platform.

Test Modules:
- test_unified_logging_ssot_comprehensive.py: Complete test suite for UnifiedLoggingSSOT class

CRITICAL BUSINESS IMPACT:
These tests validate the SSOT logging system that consolidates 5 competing logging
configurations and prevents $500K+ ARR Golden Path debugging failures.

ROOT CAUSE COVERAGE:
Special focus on the GCP staging traceback pollution issue (lines 465-470 in
_get_json_formatter method) which was causing single-line JSON output violations.
"""

# Test discovery exports
from .test_unified_logging_ssot_comprehensive import *

__all__ = [
    # Test classes for pytest discovery
    "TestSensitiveDataFilter",
    "TestUnifiedLoggingContext", 
    "TestUnifiedLoggingSSOTSingletonPattern",
    "TestUnifiedLoggingSSOTServiceIdentification",
    "TestUnifiedLoggingSSOTConfigurationManagement",
    "TestUnifiedLoggingSSOTCloudRunOptimization",
    "TestUnifiedLoggingSSOTGCPJSONFormatterCRITICAL",
    "TestUnifiedLoggingSSOTHandlerConfiguration",
    "TestUnifiedLoggingSSOTStdlibInterception",
    "TestUnifiedLoggingSSOTGCPErrorReporter", 
    "TestUnifiedLoggingSSOTPublicLoggingMethods",
    "TestUnifiedLoggingSSOTContextManagement",
    "TestUnifiedLoggingSSOTPerformanceMonitoring",
    "TestUnifiedLoggingSSOTErrorScenariosAndEdgeCases",
    "TestUnifiedLoggingSSOTPerformanceBenchmarks",
    "TestUnifiedLoggingSSOTRegressionTests",
]