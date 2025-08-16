"""Unit tests for AuthTokenService class.

Tests JWT token generation, validation, and management functionality.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import pytest
from unittest.mock import patch
import jwt

from app.auth.auth_service import AuthTokenService


class TestAuthTokenService:
    """Test JWT token generation and management service."""
    
    def test_generate_jwt_success(self):
        """Test successful JWT token generation."""
        service = AuthTokenService()
        user_info = {"id": "123", "email": "test@example.com", "name": "Test User"}
        token = service.generate_jwt(user_info)
        assert isinstance(token, str)
        assert len(token) > 0
        
    def test_generate_jwt_with_minimal_info(self):
        """Test JWT generation with minimal user info."""
        service = AuthTokenService()
        user_info = {"id": "123"}
        token = service.generate_jwt(user_info)
        assert isinstance(token, str)
        assert len(token) > 0
        
    def test_build_jwt_payload_success(self):
        """Test JWT payload building with complete user info."""
        from datetime import datetime, timezone
        service = AuthTokenService()
        user_info = {"id": "123", "email": "test@example.com", "name": "Test User"}
        now = datetime.now(timezone.utc)
        payload = service._build_jwt_payload(user_info, now)
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        
    def test_build_jwt_payload_missing_fields(self):
        """Test JWT payload building with missing user fields."""
        from datetime import datetime, timezone
        service = AuthTokenService()
        user_info = {"id": "123"}
        now = datetime.now(timezone.utc)
        payload = service._build_jwt_payload(user_info, now)
        assert payload["sub"] == "123"
        assert payload["email"] is None
        
    def test_validate_jwt_success(self):
        """Test successful JWT token validation."""
        service = AuthTokenService()
        user_info = {"id": "123", "email": "test@example.com"}
        token = service.generate_jwt(user_info)
        with patch('jwt.decode', return_value={"sub": "123", "email": "test@example.com"}):
            claims = service.validate_jwt(token)
            assert claims is not None and claims["sub"] == "123"
        
    def test_validate_jwt_expired_token(self):
        """Test validation of expired JWT token."""
        service = AuthTokenService()
        service.token_expiry = -1  # Force expiration
        user_info = {"id": "123", "email": "test@example.com"}
        token = service.generate_jwt(user_info)
        claims = service.validate_jwt(token)
        assert claims is None
        
    def test_validate_jwt_invalid_token(self):
        """Test validation of invalid JWT token."""
        service = AuthTokenService()
        invalid_token = "invalid.jwt.token"
        claims = service.validate_jwt(invalid_token)
        assert claims is None