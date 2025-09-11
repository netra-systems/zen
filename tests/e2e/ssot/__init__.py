"""
SSOT End-to-End Tests Package

This package contains E2E tests for validating SSOT (Single Source of Truth) compliance
across complete user journeys in staging environment. Tests are designed to FAIL initially 
to prove Golden Path SSOT violations exist, then PASS after SSOT remediation.

E2E Coverage:
- Complete Golden Path SSOT validation
- Multi-user concurrent SSOT isolation
- Error scenario SSOT consistency
- Performance validation of SSOT implementations

Requirements:
- Real staging environment only
- No Docker dependencies
- Real WebSocket connections
- Real user authentication flows
"""

__all__ = [
    "test_golden_path_logging_ssot_e2e"
]