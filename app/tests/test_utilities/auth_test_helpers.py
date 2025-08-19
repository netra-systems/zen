"""
Authentication test helpers for message flow testing.

Simple token creation utilities for testing authentication flows.
"""

import jwt
import time
import os


def create_test_token(user_id: str, exp_offset: int = 3600) -> str:
    """Create test JWT token with proper secret."""
    payload = {
        "user_id": user_id,
        "exp": time.time() + exp_offset,
        "iat": time.time()
    }
    # Use test secret from environment, fallback to hardcoded test secret
    secret = os.environ.get("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
    return jwt.encode(payload, secret, algorithm="HS256")


def create_expired_token(user_id: str) -> str:
    """Create expired JWT token."""
    return create_test_token(user_id, exp_offset=-3600)


def create_invalid_token(user_id: str) -> str:
    """Create invalid JWT token."""
    return "invalid.jwt.token"