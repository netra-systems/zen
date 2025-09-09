"""
Real WebSocket E2E Tests - Multi-User Isolation Security

This module contains critical security tests that validate multi-user isolation
in WebSocket connections using ONLY real connections (NO MOCKS).

CRITICAL REQUIREMENTS:
- All tests use real WebSocket connections to backend services
- All tests use proper JWT authentication 
- Tests FAIL HARD when isolation violations are detected
- Multi-user data privacy is strictly enforced

Test Modules:
- test_real_multi_user_websocket_isolation.py: Core isolation security tests
- test_isolation_violation_detection.py: Verification that violation detection works

Business Value: Protects user privacy in multi-tenant AI interactions,
ensuring User A's data never leaks to User B.

@compliance CLAUDE.md - Real services, E2E auth, fail-hard security
"""

from test_framework.ssot.real_websocket_test_client import (
    RealWebSocketTestClient,
    SecurityError,
    create_authenticated_websocket_client
)
from test_framework.ssot.real_websocket_connection_manager import (
    RealWebSocketConnectionManager,
    IsolationTestType
)

__all__ = [
    "RealWebSocketTestClient",
    "RealWebSocketConnectionManager", 
    "SecurityError",
    "IsolationTestType",
    "create_authenticated_websocket_client"
]