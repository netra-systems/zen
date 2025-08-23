"""
Authentication test helper functions.
Consolidates auth-related helpers from across the project.
"""

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from unittest.mock import patch


def create_test_jwt_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    expiry_hours: int = 24
) -> str:
    """Create a test JWT token for testing purposes"""
    # This is a mock implementation for testing
    payload = {
        "sub": email,
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + (expiry_hours * 3600),
        "iss": "test-issuer"
    }
    # Return a mock token (not actually signed)
    return f"test.{encode_base64(json.dumps(payload))}.signature"


def encode_base64(data: str) -> str:
    """Base64 encode string for JWT payload"""
    import base64
    return base64.urlsafe_b64encode(data.encode()).decode().rstrip('=')


def create_test_auth_headers(
    token: Optional[str] = None,
    user_id: str = "test-user-123"
) -> Dict[str, str]:
    """Create authorization headers for testing"""
    if not token:
        token = create_test_jwt_token(user_id=user_id)
    
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_test_user_data(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    tier: str = "free"
) -> Dict[str, Any]:
    """Create test user data"""
    return {
        "id": user_id,
        "email": email,
        "name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "tier": tier,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    }


def create_oauth_test_data(
    provider: str = "google",
    user_id: str = "oauth-user-123"
) -> Dict[str, Any]:
    """Create OAuth test data"""
    return {
        "provider": provider,
        "provider_user_id": f"{provider}-{user_id}",
        "email": f"test+{provider}@example.com",
        "name": f"Test {provider.title()} User",
        "avatar_url": f"https://{provider}.com/avatar.jpg",
        "access_token": f"test-{provider}-access-token",
        "refresh_token": f"test-{provider}-refresh-token",
        "expires_at": "2025-12-31T23:59:59Z"
    }


def mock_jwt_validation(valid: bool = True, user_data: Optional[Dict[str, Any]] = None):
    """Context manager to mock JWT validation"""
    if user_data is None:
        user_data = create_test_user_data()
    
    def mock_validate(token: str):
        if valid:
            return {
                "valid": True,
                "user_id": user_data["id"],
                "email": user_data["email"],
                "data": user_data
            }
        else:
            return {"valid": False, "error": "Invalid token"}
    
    return patch('netra_backend.app.auth_integration.auth.validate_token_jwt', side_effect=mock_validate)


def create_session_data(
    session_id: str = "test-session-123",
    user_id: str = "test-user-123"
) -> Dict[str, Any]:
    """Create test session data"""
    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": "2025-01-01T00:00:00Z",
        "expires_at": "2025-01-02T00:00:00Z",
        "is_active": True,
        "ip_address": "127.0.0.1",
        "user_agent": "test-client"
    }


def create_api_key_data(
    api_key: str = "test-api-key-123",
    user_id: str = "test-user-123"
) -> Dict[str, Any]:
    """Create test API key data"""
    return {
        "api_key": api_key,
        "user_id": user_id,
        "name": "Test API Key",
        "is_active": True,
        "permissions": ["read", "write"],
        "created_at": "2025-01-01T00:00:00Z",
        "last_used_at": None,
        "expires_at": "2025-12-31T23:59:59Z"
    }


def validate_auth_response(response_data: Dict[str, Any]) -> bool:
    """Validate authentication response structure"""
    required_fields = ["user_id", "token", "expires_at"]
    return all(field in response_data for field in required_fields)


def validate_user_data(user_data: Dict[str, Any]) -> bool:
    """Validate user data structure"""
    required_fields = ["id", "email", "is_active"]
    return all(field in user_data for field in required_fields)


class AuthTestHelpers:
    """Auth test helper class with common operations"""
    
    @staticmethod
    def create_test_auth_context(
        user_id: str = "test-user-123",
        email: str = "test@example.com",
        tier: str = "free"
    ) -> Dict[str, Any]:
        """Create complete auth context for testing"""
        user_data = create_test_user_data(user_id, email, tier)
        token = create_test_jwt_token(user_id, email)
        headers = create_test_auth_headers(token, user_id)
        session = create_session_data(user_id=user_id)
        
        return {
            "user": user_data,
            "token": token,
            "headers": headers,
            "session": session
        }
    
    @staticmethod
    def create_multiple_test_users(count: int = 3) -> list[Dict[str, Any]]:
        """Create multiple test users with auth contexts"""
        users = []
        for i in range(count):
            user_id = f"test-user-{i}"
            email = f"test{i}@example.com"
            context = AuthTestHelpers.create_test_auth_context(user_id, email)
            users.append(context)
        return users
    
    @staticmethod
    def simulate_token_expiry(token: str) -> str:
        """Simulate an expired token for testing"""
        # Return a token that will be treated as expired
        return token.replace("test.", "expired.")
    
    @staticmethod
    def create_permission_test_data(permissions: list[str]) -> Dict[str, Any]:
        """Create test data for permission testing"""
        return {
            "user_id": "test-user-123",
            "permissions": permissions,
            "roles": ["user"],
            "tier": "free",
            "tier_limits": {
                "api_calls": 1000,
                "storage": "1GB",
                "features": ["basic"]
            }
        }


# Utility functions for common auth test patterns

def assert_authenticated_response(response_data: Dict[str, Any]):
    """Assert that response indicates successful authentication"""
    assert "user_id" in response_data
    assert "token" in response_data
    assert response_data.get("authenticated") is True


def assert_unauthenticated_response(response_data: Dict[str, Any]):
    """Assert that response indicates failed authentication"""
    assert response_data.get("authenticated") is False
    assert "error" in response_data


def assert_permission_denied(response_data: Dict[str, Any]):
    """Assert that response indicates permission denied"""
    assert response_data.get("error") == "permission_denied"
    assert response_data.get("status_code", 403) == 403


def create_oauth_flow_test_data() -> Dict[str, Any]:
    """Create complete OAuth flow test data"""
    return {
        "authorization_url": "https://accounts.google.com/oauth/authorize?client_id=test",
        "state": "test-state-123",
        "code": "test-authorization-code",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token", 
        "user_info": {
            "id": "google-123",
            "email": "oauth@example.com",
            "name": "OAuth Test User",
            "picture": "https://example.com/avatar.jpg"
        }
    }