"""
Session Security Tester Integration Module

This module provides compatibility imports for SessionSecurityLogoutTester
from the main e2e module. This ensures import paths work correctly for
Golden Path integration tests.

BVJ (Business Value Justification):
- Segment: All customer segments (security affects everyone)
- Business Goal: Enable Golden Path tests that protect $500K+ ARR
- Value Impact: Prevents import errors blocking critical business flow validation
- Revenue Impact: Security test availability protects user trust and compliance
"""

# Import from the actual implementation
from tests.e2e.session_security_tester import SessionSecurityLogoutTester

# Re-export for compatibility
__all__ = ['SessionSecurityLogoutTester']