"""
Authentication helper functions for E2E testing.

This module provides functions for creating JWT tokens and user authentication
data for E2E test scenarios.

Business Value Justification (BVJ):
- Segment: Internal/Platform stability
- Business Goal: Enable reliable authentication testing
- Value Impact: Ensures auth flows work correctly in tests
- Revenue Impact: Protects user authentication and access
"""

import time
import jwt
from typing import Dict, Any, Optional
from uuid import uuid4

from shared.isolated_environment import IsolatedEnvironment


def create_real_jwt_token(
    user_id: str = "test_user_123",
    email: str = "test@example.com",
    tier: str = "free",
    permissions: Optional[list] = None,
    expires_in_seconds: int = 3600
) -> str:
    """
    Create a real JWT token for testing purposes.
    
    Args:
        user_id: User ID to encode in token
        email: User email to encode in token
        tier: Customer tier (free, early, mid, enterprise)
        permissions: List of permissions for the user
        expires_in_seconds: Token expiration time in seconds
    
    Returns:
        JWT token string
    """
    env = IsolatedEnvironment()
    
    # Use test secret key
    secret_key = env.get("JWT_SECRET_KEY", "test_jwt_secret_key_for_e2e_testing_only")
    
    # Default permissions based on tier
    if permissions is None:
        permissions = {
            "free": ["chat"],
            "early": ["chat", "agents", "data_export"],
            "mid": ["chat", "agents", "data_export", "api_access"],
            "enterprise": ["chat", "agents", "data_export", "api_access", "admin"]
        }.get(tier, ["chat"])
    
    # JWT payload
    now = int(time.time())
    payload = {
        "sub": email,
        "user_id": user_id,
        "email": email,
        "tier": tier,
        "permissions": permissions,
        "iat": now,
        "exp": now + expires_in_seconds,
        "jti": str(uuid4()),  # JWT ID for token tracking
        "aud": "netra-apex",
        "iss": "netra-auth-service"
    }
    
    # Create JWT token
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    return token


def create_test_user_token(
    tier: str = "free",
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    permissions: Optional[list] = None
) -> Dict[str, Any]:
    """
    Create a complete test user token data structure.
    
    Args:
        tier: Customer tier (free, early, mid, enterprise)
        user_id: Optional user ID (generated if not provided)
        email: Optional email (generated if not provided)
        permissions: Optional permissions list
    
    Returns:
        Dictionary containing user data and JWT token
    """
    # Generate defaults if not provided
    if user_id is None:
        user_id = f"test_user_{tier}_{int(time.time())}"
    
    if email is None:
        email = f"{user_id}@test.example.com"
    
    # Create JWT token
    jwt_token = create_real_jwt_token(
        user_id=user_id,
        email=email,
        tier=tier,
        permissions=permissions
    )
    
    # Return complete user data
    return {
        "user_id": user_id,
        "email": email,
        "tier": tier,
        "permissions": permissions or ["chat"],
        "jwt_token": jwt_token,
        "token": jwt_token,  # Alias for compatibility
        "created_at": time.time(),
        "expires_at": time.time() + 3600,
        "metadata": {
            "test_user": True,
            "tier": tier,
            "created_for_testing": True
        }
    }


def validate_test_token(token: str) -> Dict[str, Any]:
    """
    Validate a test JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or None if invalid
    """
    env = IsolatedEnvironment()
    secret_key = env.get("JWT_SECRET_KEY", "test_jwt_secret_key_for_e2e_testing_only")
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return {
            "valid": True,
            "payload": payload,
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "tier": payload.get("tier"),
            "permissions": payload.get("permissions", [])
        }
    except jwt.ExpiredSignatureError:
        return {
            "valid": False,
            "error": "Token has expired",
            "error_type": "expired"
        }
    except jwt.InvalidTokenError as e:
        return {
            "valid": False,
            "error": f"Invalid token: {str(e)}",
            "error_type": "invalid"
        }


def create_expired_test_token(user_id: str = "test_user_123", email: str = "test@example.com") -> str:
    """
    Create an expired JWT token for testing token validation.
    
    Args:
        user_id: User ID to encode in token
        email: User email to encode in token
    
    Returns:
        Expired JWT token string
    """
    return create_real_jwt_token(
        user_id=user_id,
        email=email,
        expires_in_seconds=-3600  # Expired 1 hour ago
    )


def create_malformed_test_token() -> str:
    """
    Create a malformed JWT token for testing error handling.
    
    Returns:
        Malformed JWT token string
    """
    return "invalid.jwt.token.format.for.testing"


def get_test_auth_headers(token: str) -> Dict[str, str]:
    """
    Get HTTP headers with authorization token.
    
    Args:
        token: JWT token string
    
    Returns:
        Dictionary of HTTP headers
    """
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Test-Auth": "true"
    }


def create_multi_tier_test_users() -> Dict[str, Dict[str, Any]]:
    """
    Create test users for all customer tiers.
    
    Returns:
        Dictionary mapping tier names to user data
    """
    tiers = ["free", "early", "mid", "enterprise"]
    users = {}
    
    for tier in tiers:
        users[tier] = create_test_user_token(tier=tier)
    
    return users


def create_oauth_test_data(provider: str = "google") -> Dict[str, Any]:
    """
    Create OAuth test data for authentication flows.
    
    Args:
        provider: OAuth provider name (google, github, etc.)
    
    Returns:
        OAuth test data structure
    """
    return {
        "provider": provider,
        "client_id": f"test-{provider}-client-id",
        "client_secret": f"test-{provider}-client-secret",
        "redirect_uri": "http://localhost:3000/auth/callback",
        "scope": "openid email profile",
        "state": str(uuid4()),
        "nonce": str(uuid4()),
        "authorization_code": f"test-auth-code-{provider}-{int(time.time())}",
        "access_token": f"test-access-token-{provider}-{int(time.time())}",
        "refresh_token": f"test-refresh-token-{provider}-{int(time.time())}",
        "expires_in": 3600,
        "token_type": "Bearer"
    }