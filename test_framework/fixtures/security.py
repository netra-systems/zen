"""
Security Test Fixtures Module

This module provides SSOT security fixtures for integration tests.
Prevents import errors and provides consistent security test utilities.

Business Value:
- Prevents test collection failures due to missing security fixtures
- Provides reusable security test components
- Ensures consistent security testing patterns
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.fixture
def security_test_fixture() -> Dict[str, Any]:
    """
    Fixture providing security test utilities for integration tests.
    
    Returns:
        Dictionary with security testing utilities and mock components
    """
    
    class SecurityTestUtils:
        """Security testing utilities"""
        
        def __init__(self):
            self.jwt_secret = "test-security-secret-key-for-integration-tests-must-be-32-chars"
            self.test_user_data = {
                "user_id": "test_security_user",
                "email": "security.test@netra-testing.ai",
                "role": "test_user",
                "permissions": ["read", "write", "execute"]
            }
        
        def generate_valid_jwt(self, user_data: Optional[Dict] = None, expires_in_hours: int = 1) -> str:
            """Generate a valid JWT token for testing"""
            payload = user_data or self.test_user_data.copy()
            payload.update({
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            })
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        def generate_expired_jwt(self, user_data: Optional[Dict] = None) -> str:
            """Generate an expired JWT token for testing"""
            payload = user_data or self.test_user_data.copy()
            payload.update({
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1)
            })
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        def generate_invalid_jwt(self) -> str:
            """Generate an invalid JWT token for testing"""
            return jwt.encode({"invalid": "token"}, "wrong_secret", algorithm="HS256")
        
        def validate_jwt(self, token: str) -> Dict[str, Any]:
            """Validate a JWT token"""
            try:
                return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            except jwt.InvalidTokenError as e:
                return {"valid": False, "error": str(e)}
    
    # Mock security components
    mock_auth_service = AsyncMock()
    mock_auth_service.validate_token = AsyncMock()
    mock_auth_service.refresh_token = AsyncMock()
    mock_auth_service.revoke_token = AsyncMock()
    
    mock_permission_service = MagicMock()
    mock_permission_service.check_permission = MagicMock(return_value=True)
    mock_permission_service.get_user_permissions = MagicMock(return_value=["read", "write"])
    mock_permission_service.has_role = MagicMock(return_value=True)
    
    mock_security_middleware = AsyncMock()
    mock_security_middleware.authenticate = AsyncMock()
    mock_security_middleware.authorize = AsyncMock()
    mock_security_middleware.validate_request = AsyncMock()
    
    return {
        "utils": SecurityTestUtils(),
        "mock_auth_service": mock_auth_service,
        "mock_permission_service": mock_permission_service,
        "mock_security_middleware": mock_security_middleware,
        "jwt_secret": SecurityTestUtils().jwt_secret
    }


@pytest.fixture
def auth_token_fixture() -> Dict[str, str]:
    """
    Fixture providing various auth tokens for testing.
    
    Returns:
        Dictionary with different types of auth tokens
    """
    security_utils = SecurityTestUtils()
    
    return {
        "valid_token": security_utils.generate_valid_jwt(),
        "expired_token": security_utils.generate_expired_jwt(),
        "invalid_token": security_utils.generate_invalid_jwt(),
        "admin_token": security_utils.generate_valid_jwt({
            "user_id": "admin_user",
            "email": "admin@netra-testing.ai", 
            "role": "admin",
            "permissions": ["admin", "read", "write", "execute"]
        }),
        "readonly_token": security_utils.generate_valid_jwt({
            "user_id": "readonly_user",
            "email": "readonly@netra-testing.ai",
            "role": "readonly",
            "permissions": ["read"]
        })
    }


@pytest.fixture
def security_headers_fixture() -> Dict[str, Dict[str, str]]:
    """
    Fixture providing security headers for testing.
    
    Returns:
        Dictionary with various security header configurations
    """
    security_utils = SecurityTestUtils()
    valid_token = security_utils.generate_valid_jwt()
    
    return {
        "authenticated": {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json"
        },
        "unauthenticated": {
            "Content-Type": "application/json"
        },
        "invalid_auth": {
            "Authorization": "Bearer invalid_token_here",
            "Content-Type": "application/json" 
        },
        "expired_auth": {
            "Authorization": f"Bearer {security_utils.generate_expired_jwt()}",
            "Content-Type": "application/json"
        },
        "admin_headers": {
            "Authorization": f"Bearer {security_utils.generate_valid_jwt({'role': 'admin'})}",
            "Content-Type": "application/json",
            "X-Admin-Access": "true"
        }
    }


@pytest.fixture
def mock_security_context_fixture() -> Any:
    """
    Fixture providing a mock security context for testing.
    
    Returns:
        Mock security context with user authentication state
    """
    class MockSecurityContext:
        def __init__(self):
            self.authenticated = True
            self.user_id = "test_security_context_user"
            self.email = "context@netra-testing.ai"
            self.roles = ["test_user"]
            self.permissions = ["read", "write"]
            self.jwt_payload = {
                "user_id": self.user_id,
                "email": self.email,
                "roles": self.roles,
                "permissions": self.permissions
            }
        
        def is_authenticated(self) -> bool:
            return self.authenticated
        
        def has_permission(self, permission: str) -> bool:
            return permission in self.permissions
        
        def has_role(self, role: str) -> bool:
            return role in self.roles
        
        def get_user_id(self) -> str:
            return self.user_id
        
        def get_jwt_payload(self) -> Dict[str, Any]:
            return self.jwt_payload.copy()
    
    return MockSecurityContext()


class SecurityTestUtils:
    """Reusable security testing utilities"""
    
    def __init__(self):
        self.jwt_secret = "test-security-secret-key-for-integration-tests-must-be-32-chars"
        self.test_user_data = {
            "user_id": "test_security_user",
            "email": "security.test@netra-testing.ai",
            "role": "test_user",
            "permissions": ["read", "write", "execute"]
        }
    
    def generate_valid_jwt(self, user_data: Optional[Dict] = None, expires_in_hours: int = 1) -> str:
        """Generate a valid JWT token for testing"""
        payload = user_data or self.test_user_data.copy()
        payload.update({
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        })
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def generate_expired_jwt(self, user_data: Optional[Dict] = None) -> str:
        """Generate an expired JWT token for testing"""
        payload = user_data or self.test_user_data.copy()
        payload.update({
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)
        })
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def generate_invalid_jwt(self) -> str:
        """Generate an invalid JWT token for testing"""
        return jwt.encode({"invalid": "token"}, "wrong_secret", algorithm="HS256")
    
    def validate_jwt(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token"""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": str(e)}