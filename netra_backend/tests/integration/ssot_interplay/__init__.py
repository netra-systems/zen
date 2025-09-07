"""
SSOT Interplay Integration Tests

This package contains integration tests that validate the critical interactions
between Single Source of Truth (SSOT) components across the Netra platform.

These tests focus on "top SSOT interplay" - the most critical interactions that
could cause cascade failures if broken, particularly around IsolatedEnvironment
and its interactions with other core SSOT components.

Test Categories:
- Cross-Service Environment Isolation
- Database Configuration Interplay  
- Authentication Integration
- Multi-User Context Safety
- System Integration

All tests use REAL services (no mocks) to validate actual business scenarios.
"""