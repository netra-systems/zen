"""
Authentication test helpers for message flow testing.

Simple token creation utilities for testing authentication flows.
"""

import jwt
import time


def create_test_token(user_id: str, exp_offset: int = 3600) -> str:
    """Create test JWT token."""
    payload = {
        "user_id": user_id,
        "exp": time.time() + exp_offset,
        "iat": time.time()
    }
    return jwt.encode(payload, "test_secret", algorithm="HS256")


def create_expired_token(user_id: str) -> str:
    """Create expired JWT token."""
    return create_test_token(user_id, exp_offset=-3600)


def create_invalid_token(user_id: str) -> str:
    """Create invalid JWT token."""
    return "invalid.jwt.token"