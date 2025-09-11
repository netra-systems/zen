"""
SSOT Integration Tests Package

This package contains integration tests for validating SSOT (Single Source of Truth) 
compliance across service boundaries and component interactions. Tests are designed 
to FAIL initially to prove cross-service violations exist, then PASS after SSOT remediation.

Integration Coverage:
- Cross-service SSOT validation
- Multi-component SSOT interaction
- Service boundary SSOT compliance
- Real service integration with SSOT patterns

All tests use real services and follow SSOT patterns from test_framework.
"""

__all__ = [
    "test_unified_log_correlation_integration"
]