"""
SSOT Auth Test Helpers - Single Source of Truth for Auth Testing

Business Value Justification (BVJ):
- Segment: Platform/Testing Infrastructure
- Business Goal: Enable SSOT-compliant auth testing across all test suites
- Value Impact: Prevents auth SSOT violations in test code, enables unified testing
- Strategic Impact: Foundation for $500K+ ARR auth security compliance

This module provides the Single Source of Truth (SSOT) for authentication
testing utilities that delegate to auth service instead of performing
direct JWT operations.

Key Features:
- Delegates all auth operations to AuthServiceClient
- Provides test-friendly interfaces for common auth scenarios
- Supports multi-user isolation and context management
- Uses IsolatedEnvironment for configuration
- Replaces direct JWT operations in test files

Usage Example:
    from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
    
    helper = SSOTAuthTestHelper()
    user_data = await helper.create_test_user_with_token(email="test@example.com")
    token = user_data["access_token"]
    
    validation = await helper.validate_token_via_service(token)
    assert validation["valid"] is True
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedTestUser:
    """Data class for authenticated test user information."""
    user_id: str
    email: str
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    permissions: Optional[List[str]] = None
    created_at: Optional[datetime] = None


class SSOTAuthTestHelper:
    """
    SSOT Auth Test Helper - Single Source of Truth for auth testing.
    
    Provides centralized auth test utilities that delegate to auth service
    instead of performing direct JWT operations.
    
    This class replaces all direct JWT operations in test files with
    proper auth service delegation patterns.
    """
    
    def __init__(self, auth_client: Optional[Any] = None):
        """
        Initialize SSOT Auth Test Helper.
        
        Args:
            auth_client: Optional AuthServiceClient instance. If not provided,
                        will be created based on environment configuration.
        """
        self.env = get_env()
        
        # Import auth client here to avoid circular imports
        if auth_client is None:
            try:
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                self.auth_client = AuthServiceClient()
            except ImportError as e:
                logger.warning(f"Could not import AuthServiceClient: {e}")
                self.auth_client = None
        else:
            self.auth_client = auth_client
            
        self._test_users: List[AuthenticatedTestUser] = []
    
    def _get_auth_service_url(self) -> str:
        """Get auth service URL from environment."""
        return self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
    
    async def create_test_user_with_token(
        self,
        email: str = "test@example.com",
        password: str = "TestPassword123!",
        name: str = "Test User",
        permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create test user and token via auth service.
        
        This method delegates user creation and token generation to the auth service
        instead of performing direct JWT operations.
        
        Args:
            email: User email address
            password: User password  
            name: User display name
            permissions: List of user permissions
            
        Returns:
            Dict containing user_id, email, access_token, and other auth data
            
        Raises:
            AuthServiceError: If auth service operations fail
        """
        if self.auth_client is None:
            raise ImportError("AuthServiceClient not available for testing")
            
        try:
            # Create user via auth service
            user_data = await self.auth_client.create_user(
                email=email,
                password=password,
                name=name
            )
            
            # Generate token via auth service
            token_data = await self.auth_client.generate_token(
                user_id=user_data["user_id"],
                email=email,
                permissions=permissions or ["read", "write"]
            )
            
            # Combine user and token data
            result = {
                "user_id": user_data["user_id"],
                "email": email,
                "name": name,
                "access_token": token_data["access_token"],
                "token_type": token_data.get("token_type", "bearer"),
                "expires_in": token_data.get("expires_in", 3600),
                "permissions": permissions or ["read", "write"]
            }
            
            # Track test user for cleanup
            test_user = AuthenticatedTestUser(
                user_id=result["user_id"],
                email=email,
                access_token=result["access_token"],
                token_type=result["token_type"],
                expires_in=result["expires_in"],
                permissions=result["permissions"],
                created_at=datetime.now(UTC)
            )
            self._test_users.append(test_user)
            
            logger.info(f"Created test user via auth service: {email}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create test user via auth service: {e}")
            raise
    
    async def validate_token_via_service(self, token: str) -> Dict[str, Any]:
        """
        Validate token via auth service.
        
        This method delegates token validation to the auth service
        instead of performing direct JWT decode operations.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict containing validation result and user information
            
        Raises:
            AuthServiceError: If auth service validation fails
        """
        if self.auth_client is None:
            raise ImportError("AuthServiceClient not available for testing")
            
        try:
            # Validate token via auth service
            validation_result = await self.auth_client.validate_token(token)
            
            logger.debug(f"Token validation via auth service: {validation_result.get('valid', False)}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate token via auth service: {e}")
            raise
    
    async def create_websocket_auth_token(
        self, 
        user_id: str,
        scopes: Optional[List[str]] = None
    ) -> str:
        """
        Create WebSocket auth token via auth service.
        
        WebSocket tokens may need special claims or scopes,
        but should still be generated via auth service delegation.
        
        Args:
            user_id: User ID for token
            scopes: Optional WebSocket-specific scopes
            
        Returns:
            WebSocket authentication token string
            
        Raises:
            AuthServiceError: If auth service token generation fails
        """
        if self.auth_client is None:
            raise ImportError("AuthServiceClient not available for testing")
            
        try:
            # Check if auth client has WebSocket-specific token method
            if hasattr(self.auth_client, 'generate_websocket_token'):
                token_data = await self.auth_client.generate_websocket_token(
                    user_id=user_id,
                    scopes=scopes or ["websocket", "chat"]
                )
                return token_data["access_token"]
            else:
                # Fall back to regular token generation with WebSocket permissions
                token_data = await self.auth_client.generate_token(
                    user_id=user_id,
                    permissions=scopes or ["websocket", "chat", "read", "write"]
                )
                return token_data["access_token"]
                
        except Exception as e:
            logger.error(f"Failed to create WebSocket token via auth service: {e}")
            raise
    
    async def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from token via auth service.
        
        This method gets user data through auth service validation
        instead of decoding JWT tokens directly.
        
        Args:
            token: JWT token to get user info from
            
        Returns:
            User information dict or None if token invalid
        """
        try:
            validation_result = await self.validate_token_via_service(token)
            
            if validation_result.get("valid", False):
                return {
                    "user_id": validation_result.get("user_id"),
                    "email": validation_result.get("email"),
                    "permissions": validation_result.get("permissions", [])
                }
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get user from token: {e}")
            return None
    
    async def refresh_token_via_service(
        self, 
        token: str,
        extend_expiry: bool = True
    ) -> Dict[str, Any]:
        """
        Refresh token via auth service.
        
        This method refreshes or extends token validity through
        auth service instead of generating new tokens locally.
        
        Args:
            token: Current token to refresh
            extend_expiry: Whether to extend token expiry
            
        Returns:
            Dict containing new token information
            
        Raises:
            AuthServiceError: If auth service refresh fails
        """
        if self.auth_client is None:
            raise ImportError("AuthServiceClient not available for testing")
            
        try:
            # Check if auth client has refresh token method
            if hasattr(self.auth_client, 'refresh_token'):
                refresh_result = await self.auth_client.refresh_token(
                    token=token,
                    extend_expiry=extend_expiry
                )
                return refresh_result
            else:
                # Fall back to validation and re-generation
                validation = await self.validate_token_via_service(token)
                
                if validation.get("valid", False):
                    # Generate new token for same user
                    new_token = await self.auth_client.generate_token(
                        user_id=validation["user_id"],
                        email=validation.get("email"),
                        permissions=validation.get("permissions", ["read", "write"])
                    )
                    return new_token
                else:
                    raise ValueError("Cannot refresh invalid token")
                    
        except Exception as e:
            logger.error(f"Failed to refresh token via auth service: {e}")
            raise
    
    async def create_multiple_test_users(
        self, 
        count: int = 2,
        email_prefix: str = "test-user"
    ) -> List[Dict[str, Any]]:
        """
        Create multiple test users for isolation testing.
        
        This method creates multiple isolated users via auth service
        to test multi-user scenarios and isolation.
        
        Args:
            count: Number of users to create
            email_prefix: Prefix for user email addresses
            
        Returns:
            List of user data dictionaries
        """
        users = []
        
        for i in range(count):
            user_email = f"{email_prefix}-{i+1}@example.com"
            user_password = f"TestUser{i+1}Pass123!"
            user_name = f"Test User {i+1}"
            
            try:
                user_data = await self.create_test_user_with_token(
                    email=user_email,
                    password=user_password,
                    name=user_name
                )
                users.append(user_data)
                
            except Exception as e:
                logger.warning(f"Failed to create test user {user_email}: {e}")
        
        logger.info(f"Created {len(users)} test users via auth service")
        return users
    
    async def cleanup_test_users(self) -> None:
        """
        Clean up test users created during testing.
        
        This method attempts to clean up test users through auth service
        to prevent test data accumulation.
        """
        if self.auth_client is None or not self._test_users:
            return
            
        cleaned_count = 0
        
        for test_user in self._test_users:
            try:
                # Check if auth client has user deletion method
                if hasattr(self.auth_client, 'delete_user'):
                    await self.auth_client.delete_user(test_user.user_id)
                    cleaned_count += 1
                elif hasattr(self.auth_client, 'deactivate_user'):
                    await self.auth_client.deactivate_user(test_user.user_id)
                    cleaned_count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to cleanup test user {test_user.email}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} test users")
            
        self._test_users.clear()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup_test_users()


# Convenience functions for backwards compatibility
async def create_test_auth_token(
    user_id: str = "test-user", 
    email: str = "test@example.com",
    permissions: Optional[List[str]] = None
) -> str:
    """
    Convenience function to create test auth token via auth service.
    
    This function provides a simple interface for tests that just need
    a valid token without full user creation.
    """
    helper = SSOTAuthTestHelper()
    user_data = await helper.create_test_user_with_token(
        email=email,
        permissions=permissions
    )
    return user_data["access_token"]


async def validate_test_token(token: str) -> bool:
    """
    Convenience function to validate test token via auth service.
    
    This function provides a simple interface for tests that just need
    to check if a token is valid.
    """
    helper = SSOTAuthTestHelper()
    validation = await helper.validate_token_via_service(token)
    return validation.get("valid", False)


# Export main class and convenience functions
__all__ = [
    "SSOTAuthTestHelper",
    "AuthenticatedTestUser", 
    "create_test_auth_token",
    "validate_test_token"
]