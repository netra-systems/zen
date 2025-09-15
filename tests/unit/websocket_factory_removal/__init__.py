"""WebSocket Factory Removal Validation Tests - Phase 1 SSOT Validation

This test package contains targeted validation tests for safe WebSocket Manager
Factory removal as part of SSOT consolidation efforts.

Test Categories:
1. Import Validation - Ensures SSOT imports work after factory removal
2. Authentication SSOT Compliance - Validates auth service works without factory
3. Factory Deprecation Proof - Proves factory can be completely removed
4. Golden Path Integration - End-to-end validation of chat functionality

All tests are designed to initially FAIL (detecting deprecated state) and
PASS after complete factory removal and SSOT migration.
"""

# SSOT compliance marker
__version__ = "1.0.0"
__purpose__ = "WebSocket Manager Factory Removal Validation"