"""Unit tests for AuthSessionManager class.

Tests OAuth session and state management functionality.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.auth.auth_service import AuthSessionManager


class TestAuthSessionManager:
    """Test OAuth session and state management."""
    
    @pytest.mark.asyncio
    async def test_create_oauth_state_success(self):
        """Test successful OAuth state creation."""
        manager = AuthSessionManager()
        with patch.object(manager, '_store_state_data', return_value="state123"):
            state_id = await manager.create_oauth_state("42", "http://example.com")
            assert state_id == "state123"
            
    @pytest.mark.asyncio
    async def test_create_oauth_state_no_pr(self):
        """Test OAuth state creation without PR number."""
        manager = AuthSessionManager()
        with patch.object(manager, '_store_state_data', return_value="state123"):
            state_id = await manager.create_oauth_state(None, "http://example.com")
            assert state_id == "state123"
            
    def test_build_state_data_with_pr(self):
        """Test state data building with PR number."""
        manager = AuthSessionManager()
        csrf_token = "csrf123"
        data = manager._build_state_data("42", "http://example.com", csrf_token)
        assert data["pr_number"] == "42"
        assert data["return_url"] == "http://example.com"
        assert data["csrf_token"] == csrf_token
        
    def test_build_state_data_without_pr(self):
        """Test state data building without PR number."""
        manager = AuthSessionManager()
        csrf_token = "csrf123"
        data = manager._build_state_data(None, "http://example.com", csrf_token)
        assert "pr_number" not in data
        assert data["return_url"] == "http://example.com"
        assert data["csrf_token"] == csrf_token
        
    @pytest.mark.asyncio 
    async def test_store_state_data_success(self):
        """Test successful state data storage."""
        manager = AuthSessionManager()
        state_data = {"csrf_token": "csrf123", "return_url": "http://example.com"}
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.setex = AsyncMock()
            state_id = await manager._store_state_data(state_data)
            assert isinstance(state_id, str)
            assert len(state_id) > 0
            
    @pytest.mark.asyncio
    async def test_validate_and_consume_state_success(self):
        """Test successful state validation and consumption."""
        manager = AuthSessionManager()
        state_data = {"csrf_token": "csrf123", "timestamp": int(time.time())}
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.get = AsyncMock(return_value=json.dumps(state_data))
            mock_redis.delete = AsyncMock()
            result = await manager.validate_and_consume_state("state123")
            assert result["csrf_token"] == "csrf123"
            
    @pytest.mark.asyncio
    async def test_validate_and_consume_state_not_found(self):
        """Test state validation with non-existent state."""
        manager = AuthSessionManager()
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await manager.validate_and_consume_state("invalid_state")
            assert exc_info.value.status_code == 400
            
    def test_validate_state_data_success(self):
        """Test successful state data validation."""
        manager = AuthSessionManager()
        state_data = {"csrf_token": "csrf123", "timestamp": int(time.time())}
        result = manager._validate_state_data(state_data)
        assert result["csrf_token"] == "csrf123"
        
    def test_validate_state_data_expired(self):
        """Test validation of expired state data."""
        manager = AuthSessionManager()
        old_timestamp = int(time.time()) - 400  # Older than TTL
        state_data = {"csrf_token": "csrf123", "timestamp": old_timestamp}
        with pytest.raises(HTTPException) as exc_info:
            manager._validate_state_data(state_data)
        assert exc_info.value.status_code == 400