"""
SSOT Compliance Test Suite

**PURPOSE**: Critical SSOT compliance validation tests protecting $500K+ ARR
Golden Path functionality from duplicate implementations and silent failures.

**TEST MODULES**:
- test_ssot_test_runner_compliance_suite.py: Comprehensive SSOT validation
- test_golden_path_test_runner_protection.py: Golden Path revenue protection

**BUSINESS IMPACT**: These tests validate SSOT compliance patterns that protect
business-critical Golden Path user flows representing 90% of platform value.

Created: 2025-09-10
GitHub Issue: #299 - UnifiedTestRunner SSOT violation
"""

# Export main test classes for easier importing
from .test_ssot_test_runner_compliance_suite import TestSSOTTestRunnerCompliance
from .test_golden_path_test_runner_protection import TestGoldenPathTestRunnerProtection

__all__ = [
    "TestSSOTTestRunnerCompliance",
    "TestGoldenPathTestRunnerProtection"
]