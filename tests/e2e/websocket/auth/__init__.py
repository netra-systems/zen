"""
WebSocket Authentication E2E Tests Package

This package contains comprehensive E2E tests for WebSocket authentication security.
All tests FAIL HARD when authentication security is compromised.

Test Modules:
- test_websocket_token_lifecycle.py: Token lifecycle management with hard failures
- test_websocket_session_security.py: Session security and isolation validation

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- ALL e2e tests MUST use authentication (JWT/OAuth) except tests directly validating auth
- Tests MUST FAIL HARD when authentication is compromised  
- NO MOCKS in E2E testing - use real WebSocket connections
- Tests with 0-second execution = automatic hard failure

@compliance CLAUDE.md - Real authentication required, hard failures for security violations
"""

__all__ = [
    "test_websocket_token_lifecycle",
    "test_websocket_session_security"
]