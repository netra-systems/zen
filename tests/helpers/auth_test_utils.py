"""Canonical test authentication helper - SSOT for test tokens

This is the single source of truth for creating test tokens across all tests.
All tests should use this helper instead of implementing auth logic directly.

Business Value: Eliminates test code duplication and ensures consistent token creation
across all test suites, improving maintainability and reducing test development time.

Usage:
    from tests.helpers.auth_test_utils import TestAuthHelper
    
    # Basic usage
    auth_helper = TestAuthHelper()
    token = auth_helper.create_test_token("user123")
    
    # With specific email and permissions
    token = auth_helper.create_test_token_with_permissions(
        "user123", 
        ["read", "write", "admin"],
        tier="enterprise"
    )
    
    # Environment-specific usage
    auth_helper = TestAuthHelper(environment="dev")
    token = auth_helper.create_test_token("user123")

IMPORTANT: This helper is for TEST purposes only. It provides a consistent
interface for all tests to create tokens without duplicating JWT logic.
"""

from typing import List, Optional

# Use absolute imports per CLAUDE.md standards
from tests.e2e.jwt_token_helpers import JWTTestHelper


class TestAuthHelper:
    """Canonical test authentication helper - SSOT for test tokens
    
    This is the single source of truth for creating test tokens.
    All tests should use this helper instead of implementing auth logic.
    
    Key Benefits:
    - Eliminates code duplication across test files
    - Ensures consistent token format across all tests  
    - Provides simple, focused API for test token creation
    - Maintains environment-specific behavior
    - Follows SSOT principles from CLAUDE.md
    """
    
    def __init__(self, environment: Optional[str] = None):
        """Initialize the test auth helper.
        
        Args:
            environment: Optional environment override ('test', 'dev', 'staging', etc.)
                        If None, will auto-detect from environment variables
        """
        self.environment = environment
        self.jwt_helper = JWTTestHelper(environment)
    
    def create_test_token(self, user_id: str, email: Optional[str] = None) -> str:
        """Create test token for integration tests
        
        This is the most commonly used method - creates a standard test token
        with default permissions for the given user.
        
        Args:
            user_id: The user ID for the token
            email: Optional email (defaults to {user_id}@test.com)
            
        Returns:
            A valid JWT token for testing
            
        Example:
            token = auth_helper.create_test_token("user123")
            token = auth_helper.create_test_token("user123", "custom@test.com")
        """
        if email is None:
            email = f"{user_id}@test.com"
        
        # CRITICAL FIX: For staging environment, use special staging token creation
        if self.environment == "staging":
            return self.create_staging_token(user_id, email)
        
        # Use default permissions for standard test scenarios
        return self.jwt_helper.create_access_token(user_id, email)
    
    def create_staging_token(self, user_id: str, email: Optional[str] = None) -> str:
        """Create staging-specific token using unified JWT secret manager.
        
        CRITICAL FIX: This method ensures staging tokens are created with the EXACT
        same secret resolution as the backend UserContextExtractor, fixing the
        WebSocket 403 authentication failures.
        
        Args:
            user_id: The user ID for the token
            email: Optional email (defaults to {user_id}@netrasystems.ai)
            
        Returns:
            A valid JWT token for staging testing
            
        Example:
            auth_helper = TestAuthHelper(environment="staging")
            token = auth_helper.create_staging_token("staging_user")
        """
        if email is None:
            email = f"{user_id}@netrasystems.ai"
        
        # Use the staging JWT token creation from JWTTestHelper
        import asyncio
        return asyncio.run(self.jwt_helper.get_staging_jwt_token(user_id, email))
    
    def create_test_token_with_permissions(
        self, 
        user_id: str, 
        permissions: List[str], 
        tier: str = "free",
        email: Optional[str] = None
    ) -> str:
        """Create test token with specific permissions and tier
        
        Use this when you need to test specific permission scenarios
        or different user tiers.
        
        Args:
            user_id: The user ID for the token
            permissions: List of permissions to include (e.g., ["read", "write", "admin"])
            tier: User tier (default: "free", options: "free", "early", "mid", "enterprise")
            email: Optional email (defaults to {user_id}@test.com)
            
        Returns:
            A valid JWT token with specified permissions and tier
            
        Example:
            # Enterprise user with admin permissions
            token = auth_helper.create_test_token_with_permissions(
                "admin_user", 
                ["read", "write", "admin"], 
                tier="enterprise"
            )
        """
        if email is None:
            email = f"{user_id}@test.com"
        
        return self.jwt_helper.create_access_token(user_id, email, permissions)
    
    def create_expired_test_token(self, user_id: str, email: Optional[str] = None) -> str:
        """Create an expired test token for testing auth failure scenarios
        
        Use this to test that your code properly handles expired tokens.
        
        Args:
            user_id: The user ID for the token
            email: Optional email (defaults to {user_id}@test.com)
            
        Returns:
            An expired JWT token for testing auth failures
            
        Example:
            expired_token = auth_helper.create_expired_test_token("user123")
            # Use to verify 401 responses are handled correctly
        """
        if email is None:
            email = f"{user_id}@test.com"
        
        payload = self.jwt_helper.create_expired_payload()
        payload['sub'] = user_id
        payload['email'] = email
        
        return self.jwt_helper.create_token(payload)
    
    def create_admin_test_token(self, user_id: str = "admin_user") -> str:
        """Create test token with admin permissions
        
        Convenience method for creating admin tokens in tests.
        
        Args:
            user_id: The admin user ID (defaults to "admin_user")
            
        Returns:
            A valid JWT token with admin permissions
            
        Example:
            admin_token = auth_helper.create_admin_test_token()
            # Use for testing admin-only endpoints
        """
        return self.create_test_token_with_permissions(
            user_id,
            ["read", "write", "admin"],
            tier="enterprise",
            email=f"{user_id}@netrasystems.ai"
        )
    
    def create_readonly_test_token(self, user_id: str) -> str:
        """Create test token with only read permissions
        
        Convenience method for testing read-only scenarios.
        
        Args:
            user_id: The user ID for the token
            
        Returns:
            A valid JWT token with only read permissions
            
        Example:
            readonly_token = auth_helper.create_readonly_test_token("user123")
            # Use for testing permission restrictions
        """
        return self.create_test_token_with_permissions(
            user_id,
            ["read"],
            tier="free"
        )
    
    def get_auth_headers(self, token: str) -> dict:
        """Get authorization headers for HTTP requests
        
        Convenience method to get properly formatted auth headers.
        
        Args:
            token: The JWT token to use
            
        Returns:
            Dictionary with Authorization header
            
        Example:
            token = auth_helper.create_test_token("user123")
            headers = auth_helper.get_auth_headers(token)
            response = client.get("/api/endpoint", headers=headers)
        """
        from netra_backend.app.core.auth_constants import HeaderConstants
        return {
            HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{token}"
        }
    
    def validate_token_structure(self, token: str) -> bool:
        """Validate that a token has the correct JWT structure
        
        Utility method for tests that need to verify token format.
        
        Args:
            token: The JWT token to validate
            
        Returns:
            True if token has valid JWT structure, False otherwise
            
        Example:
            token = auth_helper.create_test_token("user123")
            assert auth_helper.validate_token_structure(token)
        """
        return self.jwt_helper.validate_token_structure(token)


# Convenience functions for common use cases
def create_standard_test_token(user_id: str = "test_user") -> str:
    """Quick function to create a standard test token
    
    Use this for simple tests that just need any valid token.
    
    Args:
        user_id: User ID for the token (defaults to "test_user")
        
    Returns:
        A standard test token
        
    Example:
        token = create_standard_test_token()
        # Use in simple integration tests
    """
    helper = TestAuthHelper()
    return helper.create_test_token(user_id)


def create_admin_token(user_id: str = "admin_test") -> str:
    """Quick function to create an admin test token
    
    Use this for tests that need admin access.
    
    Args:
        user_id: Admin user ID (defaults to "admin_test")
        
    Returns:
        An admin test token
        
    Example:
        admin_token = create_admin_token()
        # Use for testing admin endpoints
    """
    helper = TestAuthHelper()
    return helper.create_admin_test_token(user_id)


# Export the main class and convenience functions
__all__ = [
    'TestAuthHelper',
    'create_standard_test_token',
    'create_admin_token'
]