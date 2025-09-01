from shared.isolated_environment import get_env
"""
Test-Only Authentication Helper

CRITICAL: This module is for TEST USE ONLY and must NEVER be imported by production code.
All test authentication bypass logic is isolated here to prevent accidental security breaches.

This module contains authentication helpers that bypass security for testing purposes.
Production code should NEVER reference this module or its functions.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from netra_backend.app.websocket_core.types import AuthInfo


env = get_env()
class TestAuthHelper:
    """Test-only authentication helper for bypassing auth in test environments."""
    
    @staticmethod
    def is_test_environment() -> bool:
        """Check if we're running in a test environment."""
        # This check is ONLY for test code, never for production
        env = os.environ
        
        # Multiple checks to ensure we're really in a test environment
        is_test = (
            env.get("TESTING", "0") == "1" or
            env.get("TESTING", "").lower() == "true" or
            env.get("E2E_TESTING", "").lower() == "true" or
            env.get("AUTH_FAST_TEST_MODE", "").lower() == "true" or
            env.get("PYTEST_CURRENT_TEST") is not None or
            env.get("ENVIRONMENT", "").lower() in ["test", "testing", "e2e_testing"] or
            env.get("NETRA_ENV", "").lower() in ["testing", "e2e_testing"]
        )
        
        return is_test
    
    @staticmethod
    def should_bypass_auth() -> bool:
        """Check if auth should be bypassed for testing."""
        if not TestAuthHelper.is_test_environment():
            return False
        
        # Additional check for specific bypass flags
        env = os.environ
        bypass_enabled = (
            env.get("ALLOW_DEV_OAUTH_SIMULATION", "false").lower() == "true" or
            env.get("WEBSOCKET_AUTH_BYPASS", "false").lower() == "true" or
            env.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
        )
        
        return bypass_enabled
    
    @staticmethod
    def should_skip_rate_limiting() -> bool:
        """Check if rate limiting should be skipped for testing."""
        # Rate limiting is always skipped in test environments
        return TestAuthHelper.is_test_environment()
    
    @staticmethod
    def create_test_auth_info(user_id: Optional[str] = None) -> AuthInfo:
        """Create a test AuthInfo object for bypassed authentication."""
        return AuthInfo(
            user_id=user_id or "test-user",
            email="test@test.localhost",
            permissions=["read", "write", "test"],
            auth_method="test_bypass",
            token_expires=None,  # No expiration for test tokens
            authenticated_at=datetime.now(timezone.utc)
        )
    
    @staticmethod
    def get_test_jwt_token() -> str:
        """Get a test JWT token for testing purposes."""
        # This is a mock JWT for testing only
        return "test.jwt.token"
    
    @staticmethod
    def validate_test_token(token: str) -> Dict[str, Any]:
        """Validate a test token (always returns valid for test tokens)."""
        if not TestAuthHelper.is_test_environment():
            return {"valid": False, "error": "Not in test environment"}
        
        # For testing, any token that starts with "test" is valid
        if token.startswith("test"):
            return {
                "valid": True,
                "user_id": "test-user",
                "email": "test@test.localhost",
                "permissions": ["read", "write", "test"],
                "expires_at": None
            }
        
        return {"valid": False, "error": "Invalid test token"}


class TestOnlyWebSocketAuth:
    """Test-only WebSocket authentication for use in test suites."""
    
    def __init__(self):
        if not TestAuthHelper.is_test_environment():
            raise RuntimeError(
                "TestOnlyWebSocketAuth can only be instantiated in test environments!"
            )
    
    async def authenticate_for_test(self, token: Optional[str] = None) -> AuthInfo:
        """Authenticate for testing purposes only."""
        if not TestAuthHelper.is_test_environment():
            raise RuntimeError("Test authentication can only be used in test environments!")
        
        if token and token.startswith("test"):
            # Valid test token
            return TestAuthHelper.create_test_auth_info()
        
        if TestAuthHelper.should_bypass_auth():
            # OAUTH SIMULATION enabled for testing
            return TestAuthHelper.create_test_auth_info()
        
        # No valid test auth
        raise ValueError("Test authentication failed")
    
    def should_skip_cors_for_test(self) -> bool:
        """Check if CORS should be skipped for testing."""
        return TestAuthHelper.is_test_environment()
    
    def should_skip_rate_limit_for_test(self) -> bool:
        """Check if rate limiting should be skipped for testing."""
        return TestAuthHelper.should_skip_rate_limiting()


# WARNING: The following should NEVER be imported by production code
def bypass_auth_for_test():
    """Context manager to temporarily bypass auth for testing."""
    if not TestAuthHelper.is_test_environment():
        raise RuntimeError("OAUTH SIMULATION can only be used in test environments!")
    
    # Set bypass flags
    original_values = {}
    bypass_vars = ["ALLOW_DEV_OAUTH_SIMULATION", "AUTH_FAST_TEST_MODE"]
    
    for var in bypass_vars:
        original_values[var] = env.get(var)
        os.environ[var] = "true"
    
    try:
        yield
    finally:
        # Restore original values
        for var, value in original_values.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value