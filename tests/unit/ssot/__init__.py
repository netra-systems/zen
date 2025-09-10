"""
SSOT Unit Tests Package

This package contains unit tests for validating SSOT (Single Source of Truth) compliance
across the Netra platform. Tests are designed to FAIL initially to prove violations exist,
then PASS after SSOT remediation.

Test Categories:
- Logging SSOT validation
- Configuration SSOT compliance
- Factory pattern SSOT verification
- Import pattern SSOT validation

All tests follow SSOT patterns and inherit from SSotBaseTestCase.
"""

__all__ = [
    "test_logging_ssot_validation"
]