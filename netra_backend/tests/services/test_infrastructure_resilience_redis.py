"""Test infrastructure resilience Redis health check - Issue #1312

This test reproduces the AttributeError where check_redis_health() calls
redis_manager.get_redis() but should call redis_manager.get_client().

GitHub Issue: #1312 - Redis health check failure
Business Value: Infrastructure monitoring for $500K+ ARR platform reliability
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from netra_backend.app.services.infrastructure_resilience import InfrastructureResilienceManager


class TestInfrastructureResilienceRedis:
    """Test Redis health check functionality."""

    @pytest.mark.asyncio
    async def test_check_redis_health_method_error(self):
        """Test that check_redis_health() fails with AttributeError when calling get_redis()."""

        # Create the service instance
        service = InfrastructureResilienceManager()

        # Create a mock redis manager that doesn't have get_redis method
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock()
        # Explicitly remove get_redis attribute to force AttributeError
        if hasattr(mock_redis_manager, 'get_redis'):
            delattr(mock_redis_manager, 'get_redis')

        # Mock the redis client returned by get_client
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_manager.get_client.return_value = mock_redis_client

        # Mock the get_redis_manager function to return our mock
        with patch('netra_backend.app.core.redis_manager.get_redis_manager', return_value=mock_redis_manager):
            # This should raise AttributeError: 'MagicMock' object has no attribute 'get_redis'
            with pytest.raises(AttributeError) as exc_info:
                await service._check_redis_health()

            # Verify the exact error message
            assert "get_redis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_redis_health_correct_method_should_work(self):
        """Test that Redis health check would work with the correct method."""

        # Create the service instance
        service = InfrastructureResilienceManager()

        # Mock the redis manager with get_client method
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock()

        # Mock the redis client returned by get_client
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_manager.get_client.return_value = mock_redis_client

        # This test demonstrates what SHOULD happen after the fix
        # (but will be skipped until the fix is applied)
        pytest.skip("This test shows the correct behavior after the fix is applied")

        # Mock the get_redis_manager function to return our mock
        with patch('netra_backend.app.core.redis_manager.get_redis_manager', return_value=mock_redis_manager):
            # After fix: this should call get_client() instead of get_redis()
            result = await service._check_redis_health()

            # Should return True when Redis ping succeeds
            assert result is True

            # Verify get_client was called (not get_redis)
            mock_redis_manager.get_client.assert_called_once()
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_redis_health_with_ping_failure(self):
        """Test Redis health check when ping fails."""

        service = InfrastructureResilienceService()

        # Mock the redis manager
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock()

        # Mock redis client that fails ping
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=False)
        mock_redis_manager.get_client.return_value = mock_redis_client

        # This test demonstrates ping failure handling after the fix
        pytest.skip("This test shows ping failure handling after the fix is applied")

        with patch('netra_backend.app.services.infrastructure_resilience.get_redis_manager', return_value=mock_redis_manager):
            result = await service._check_redis_health()

            # Should return False when Redis ping fails
            assert result is False

    @pytest.mark.asyncio
    async def test_check_redis_health_with_no_client(self):
        """Test Redis health check when get_client returns None."""

        service = InfrastructureResilienceService()

        # Mock the redis manager returning None client
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=None)

        # This test demonstrates None client handling after the fix
        pytest.skip("This test shows None client handling after the fix is applied")

        with patch('netra_backend.app.services.infrastructure_resilience.get_redis_manager', return_value=mock_redis_manager):
            result = await service._check_redis_health()

            # Should return False when no Redis client available
            assert result is False