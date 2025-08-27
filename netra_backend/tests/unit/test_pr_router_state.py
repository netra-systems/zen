"""Tests for PR router state encoding/decoding and CSRF functions."""

import sys
from pathlib import Path

import time
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from netra_backend.app.auth_integration.auth import (
    PR_STATE_TTL,
    _build_pr_state_data,
    _decode_state_from_base64,
    _encode_state_to_base64,
    _store_csrf_token_in_redis,
    _validate_and_consume_csrf_token,
    _validate_state_timestamp,
)
from netra_backend.app.core.exceptions_auth import NetraSecurityException

# Shared fixtures
@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for testing."""
    # Mock: Redis caching isolation to prevent test interference and external dependencies
    redis = Mock()
    redis.enabled = True
    # Mock: Redis caching isolation to prevent test interference and external dependencies
    redis.get = AsyncMock(return_value="active")
    # Mock: Redis caching isolation to prevent test interference and external dependencies
    redis.setex = AsyncMock()
    # Mock: Redis caching isolation to prevent test interference and external dependencies
    redis.delete = AsyncMock()
    return redis

# Tests for state encoding/decoding functions
class TestStateEncoding:
    """Test state encoding and decoding functions."""

    def test_build_pr_state_data_success(self):
        """Test building PR state data structure.
        
        Note: This function is deprecated and has simplified functionality.
        """
        state_data = _build_pr_state_data("123", "csrf-token")
        
        assert state_data["pr_number"] == "123"
        assert state_data["csrf_token"] == "csrf-token"
        assert "timestamp" in state_data
        # Note: Deprecated function no longer includes return_url or version

    def test_encode_decode_state_roundtrip(self):
        """Test state encoding and decoding roundtrip."""
        original_data = {
            "pr_number": "123",
            "return_url": "https://example.com",
            "csrf_token": "test-token",
            "timestamp": 1234567890,
            "version": "1.0"
        }
        
        encoded = _encode_state_to_base64(original_data)
        decoded = _decode_state_from_base64(encoded)
        
        assert decoded == original_data

# Tests for timestamp validation
class TestTimestampValidation:
    """Test timestamp validation functions."""

    def test_validate_state_timestamp_valid(self):
        """Test validation of current timestamp.
        
        Note: This function is deprecated and takes only a timestamp parameter.
        """
        current_time = time.time()
        
        # Should not raise exception
        _validate_state_timestamp(current_time)

    def test_validate_state_timestamp_expired(self):
        """Test validation of expired timestamp.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        expired_timestamp = int(time.time()) - 400  # Expired timestamp
        
        # Function is deprecated and does not validate - should not raise exception
        _validate_state_timestamp(expired_timestamp)

# Tests for CSRF token validation
class TestCsrfTokenValidation:
    """Test CSRF token validation functions."""

    @pytest.mark.asyncio
    async def test_store_csrf_token_redis_enabled(self, mock_redis_manager):
        """Test storing CSRF token when Redis is enabled.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        await _store_csrf_token_in_redis("csrf-token", mock_redis_manager)
        
        # Function is deprecated and does not interact with Redis
        # No assertions needed for deprecated stub function

    @pytest.mark.asyncio
    async def test_validate_csrf_token_success(self, mock_redis_manager):
        """Test successful CSRF token validation.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        csrf_token = "valid-token"
        mock_redis_manager.get.return_value = "valid"
        
        # Function is deprecated and does not validate - should not raise exception
        await _validate_and_consume_csrf_token(csrf_token, mock_redis_manager)

    @pytest.mark.asyncio
    async def test_validate_csrf_token_invalid(self, mock_redis_manager):
        """Test CSRF token validation with invalid token.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        csrf_token = "invalid-token"
        mock_redis_manager.get.return_value = None
        
        # Function is deprecated and does not validate - should not raise exception
        await _validate_and_consume_csrf_token(csrf_token, mock_redis_manager)

    @pytest.mark.asyncio
    async def test_store_csrf_token_redis_disabled(self):
        """Test storing CSRF token when Redis is disabled.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        mock_redis = Mock()
        mock_redis.enabled = False
        
        # Function is deprecated - should not raise exception
        await _store_csrf_token_in_redis("csrf-token", mock_redis)

    @pytest.mark.asyncio
    async def test_validate_csrf_token_redis_disabled(self):
        """Test CSRF token validation when Redis is disabled."""
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis = Mock()
        mock_redis.enabled = False
        state_data = {"pr_number": "123", "csrf_token": "test-token"}
        
        # Should not raise exception when Redis is disabled
        await _validate_and_consume_csrf_token(state_data, mock_redis)

    def test_encode_state_special_characters(self):
        """Test encoding state with special characters."""
        state_data = {
            "pr_number": "123",
            "return_url": "https://example.com/path?param=value&other=test",
            "csrf_token": "token-with-special-chars_123",
            "timestamp": 1234567890,
            "version": "1.0"
        }
        
        encoded = _encode_state_to_base64(state_data)
        decoded = _decode_state_from_base64(encoded)
        
        assert decoded == state_data

    def test_decode_state_malformed_base64(self):
        """Test decoding malformed base64 state data."""
        with pytest.raises(NetraSecurityException, match="Malformed state parameter"):
            _decode_state_from_base64("invalid-base64!")

    def test_decode_state_invalid_json(self):
        """Test decoding state with invalid JSON."""
        import base64
        invalid_json = base64.urlsafe_b64encode(b"invalid json").decode('utf-8')
        
        with pytest.raises(NetraSecurityException, match="Malformed state parameter"):
            _decode_state_from_base64(invalid_json)