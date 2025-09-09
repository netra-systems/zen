"""
JWT Test Utilities for Authentication Testing

This module provides utilities for generating valid JWT tokens for testing
authentication flows between services.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable reliable authentication testing
- Value Impact: Prevents authentication test failures due to token format issues
- Strategic Impact: Ensures authentication system reliability
"""

import jwt
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from shared.isolated_environment import get_env


def generate_test_jwt_token(
    user_id: str = "test-user",
    email: str = "test@example.com",
    permissions: Optional[List[str]] = None,
    expires_in_minutes: int = 60,
    issuer: str = "netra-test",
    audience: str = "netra-backend",
    secret: Optional[str] = None
) -> str:
    """
    Generate a valid JWT token for testing purposes.
    
    Args:
        user_id: User ID to include in the token
        email: User email to include in the token
        permissions: List of user permissions
        expires_in_minutes: Token expiration in minutes
        issuer: Token issuer
        audience: Token audience
        secret: JWT secret key (defaults to environment JWT_SECRET_KEY)
        
    Returns:
        Valid JWT token string
    """
    if permissions is None:
        permissions = ["read", "write"]
    
    if secret is None:
        env = get_env()
        secret = env.get("JWT_SECRET_KEY", "test-jwt-secret-32-character-minimum-length-required")
    
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "permissions": permissions,
        "iat": now,
        "exp": now + timedelta(minutes=expires_in_minutes),
        "iss": issuer,
        "aud": audience,
        "jti": str(uuid.uuid4())
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def generate_service_token(
    service_name: str,
    expires_in_minutes: int = 60,
    secret: Optional[str] = None
) -> str:
    """
    Generate a service-to-service authentication token.
    
    Args:
        service_name: Name of the service
        expires_in_minutes: Token expiration in minutes
        secret: JWT secret key
        
    Returns:
        Valid service JWT token
    """
    if secret is None:
        env = get_env()
        secret = env.get("JWT_SECRET_KEY", "test-jwt-secret-32-character-minimum-length-required")
    
    now = datetime.now(UTC)
    payload = {
        "sub": f"service:{service_name}",
        "service_name": service_name,
        "type": "service",
        "permissions": ["service:*"],
        "iat": now,
        "exp": now + timedelta(minutes=expires_in_minutes),
        "iss": "netra-service",
        "aud": "netra-backend",
        "jti": str(uuid.uuid4())
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def generate_expired_token(
    user_id: str = "test-user",
    secret: Optional[str] = None
) -> str:
    """
    Generate an expired JWT token for testing expired token handling.
    
    Args:
        user_id: User ID to include in the token
        secret: JWT secret key
        
    Returns:
        Expired JWT token
    """
    if secret is None:
        env = get_env()
        secret = env.get("JWT_SECRET_KEY", "test-jwt-secret-32-character-minimum-length-required")
    
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),  # Expired 1 hour ago
        "iss": "netra-test",
        "aud": "netra-backend",
        "jti": str(uuid.uuid4())
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_test_token(token: str, secret: Optional[str] = None) -> Dict[str, Any]:
    """
    Decode a JWT token for testing purposes (without expiration checking).
    
    Args:
        token: JWT token to decode
        secret: JWT secret key
        
    Returns:
        Decoded token payload
    """
    if secret is None:
        env = get_env()
        secret = env.get("JWT_SECRET_KEY", "test-jwt-secret-32-character-minimum-length-required")
    
    return jwt.decode(
        token, 
        secret, 
        algorithms=["HS256"],
        options={
            "verify_exp": False,  # Skip expiration check for testing
            "verify_aud": False,  # Skip audience verification for testing
            "verify_iss": False   # Skip issuer verification for testing
        }
    )


def create_bearer_token(token: str) -> str:
    """
    Create a Bearer authorization header value.
    
    Args:
        token: JWT token
        
    Returns:
        Bearer token string for Authorization header
    """
    return f"Bearer {token}"


def create_request_context_with_auth(
    token: str,
    method: str = "GET",
    path: str = "/api/test",
    service_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a request context with authentication headers for testing.
    
    Args:
        token: JWT token
        method: HTTP method
        path: Request path
        service_name: Optional service name for service-to-service auth
        
    Returns:
        Request context dictionary
    """
    headers = {
        "Authorization": create_bearer_token(token),
        "Content-Type": "application/json"
    }
    
    if service_name:
        headers.update({
            "x-service-name": service_name,
            "x-service-version": "1.0.0"
        })
    
    return {
        "method": method,
        "path": path,
        "headers": headers
    }


class JWTTestHelper:
    """Helper class for JWT testing utilities."""
    
    def __init__(self, secret: Optional[str] = None):
        """
        Initialize JWT test helper.
        
        Args:
            secret: JWT secret key
        """
        if secret is None:
            env = get_env()
            secret = env.get("JWT_SECRET_KEY", "test-jwt-secret-32-character-minimum-length-required")
        self.secret = secret
    
    def create_user_token(self, user_id: str = "test-user", **kwargs) -> str:
        """Create a user JWT token."""
        return generate_test_jwt_token(user_id=user_id, secret=self.secret, **kwargs)
    
    def create_service_token(self, service_name: str = "test-service", **kwargs) -> str:
        """Create a service JWT token."""
        return generate_service_token(service_name=service_name, secret=self.secret, **kwargs)
    
    def create_expired_token(self, user_id: str = "test-user") -> str:
        """Create an expired JWT token."""
        return generate_expired_token(user_id=user_id, secret=self.secret)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode a JWT token."""
        return decode_test_token(token, secret=self.secret)
    
    def validate_token_structure(self, token: str) -> bool:
        """
        Validate that a token has the correct JWT structure.
        
        Args:
            token: Token to validate
            
        Returns:
            True if token has valid JWT structure
        """
        try:
            # Check for three parts separated by dots
            parts = token.split('.')
            if len(parts) != 3:
                return False
            
            # Try to decode without verification
            jwt.decode(token, options={"verify_signature": False})
            return True
        except Exception:
            return False