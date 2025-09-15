"""
Critical E2E Test Suite

This directory contains the most critical E2E tests that must pass for basic system functionality.
These tests use real services with minimal mocking and focus on core business-critical paths.

Test Categories:
- test_dev_launcher_critical_path.py: Critical startup and initialization tests
- test_auth_jwt_critical.py: Essential JWT authentication and security tests  
- test_service_health_critical.py: Core service availability and health tests
- test_websocket_critical.py: Critical real-time WebSocket functionality tests

Usage:
- Run critical tests: `python unified_test_runner.py --categories e2e_critical`
- These tests should complete in under 5 minutes
- All tests use real services - no mocking of critical system components
- Tests are designed to fail when real issues exist (not silenced with mocks)
"""
