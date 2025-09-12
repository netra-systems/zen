"""
WebSocket Authentication Integration Tests Package

This package contains comprehensive integration tests for WebSocket authentication
covering authentication flows, user context management, and security validation.

Test Structure:
- test_websocket_auth_integration_flow.py: 8 Authentication Flow Tests
- test_websocket_auth_integration_user_context.py: 6 User Context Integration Tests  
- test_websocket_auth_integration_security.py: 6 Security and Validation Tests

Total: 20 High-Quality Integration Tests

Business Value: Validates $500K+ ARR chat functionality authentication mechanisms
"""

# Import all test classes for easy access
from .test_websocket_auth_integration_flow import TestWebSocketAuthenticationFlow
from .test_websocket_auth_integration_user_context import TestWebSocketUserContextIntegration
from .test_websocket_auth_integration_security import TestWebSocketAuthenticationSecurity

__all__ = [
    "TestWebSocketAuthenticationFlow",
    "TestWebSocketUserContextIntegration", 
    "TestWebSocketAuthenticationSecurity"
]