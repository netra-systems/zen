"""
Comprehensive tests for Rate Limiting Service.

Tests rate limiting policies, token bucket algorithms,
user-based limits, API endpoint protection, and burst handling.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any

from netra_backend.app.services.rate_limiting.rate_limiting_service import (
    RateLimitingService,
    RateLimitConfig,
    RateLimitResult
)


class TestRateLimitingService:
    """Tests for rate limiting service functionality."""

    @pytest.fixture
    def service(self):
        """Create a fresh rate limiting service for testing."""
        return RateLimitingService()

    @pytest.fixture
    def basic_config(self):
        """Create a basic rate limit configuration."""
        return RateLimitConfig(requests_per_second=5, burst_size=10)

    @pytest.fixture
    def strict_config(self):
        """Create a strict rate limit configuration."""
        return RateLimitConfig(requests_per_second=1, burst_size=2)

    def test_service_initialization(self, service):
        """Test rate limiting service is properly initialized."""
        assert service._limiters == {}
        assert service._default_limiter is not None

    def test_rate_limit_config_creation(self, basic_config):
        """Test rate limit configuration is created correctly."""
        assert basic_config.requests_per_second == 5
        assert basic_config.burst_size == 10

    def test_rate_limit_config_defaults(self):
        """Test rate limit config has sensible defaults."""
        config = RateLimitConfig()
        assert config.requests_per_second == 10
        assert config.burst_size == 20

    def test_rate_limit_result_structure(self):
        """Test rate limit result structure."""
        result = RateLimitResult(
            allowed=True,
            remaining=9,
            reset_time=datetime.now(),
            retry_after=0,
            limit_type="api"
        )
        
        assert result.allowed is True
        assert result.remaining == 9
        assert result.reset_time is not None
        assert result.retry_after == 0
        assert result.limit_type == "api"

    def test_add_named_limiter(self, service, basic_config):
        """Test adding named rate limiters."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter:
            mock_instance = Mock()
            mock_limiter.return_value = mock_instance
            
            service.add_limiter("api_v1", basic_config)
            
            assert "api_v1" in service._limiters
            assert service._limiters["api_v1"] == mock_instance
            mock_limiter.assert_called_once_with(basic_config)

    def test_get_existing_limiter(self, service, basic_config):
        """Test getting an existing rate limiter."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter:
            mock_instance = Mock()
            mock_limiter.return_value = mock_instance
            
            service.add_limiter("test_limiter", basic_config)
            limiter = service.get_limiter("test_limiter")
            
            assert limiter == mock_instance

    def test_get_nonexistent_limiter_returns_default(self, service):
        """Test getting non-existent limiter returns default."""
        limiter = service.get_limiter("unknown")
        assert limiter == service._default_limiter

    @pytest.mark.asyncio
    async def test_rate_limit_check_allowed(self, service, basic_config):
        """Test rate limit check when request is allowed."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=True)
            mock_limiter.get_remaining = Mock(return_value=4)
            mock_limiter.get_reset_time = Mock(return_value=datetime.now() + timedelta(seconds=60))
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("test", basic_config)
            
            result = await service.check_rate_limit("user123", "test")
            
            assert result.allowed is True
            assert result.remaining == 4
            assert result.reset_time is not None

    @pytest.mark.asyncio
    async def test_rate_limit_check_denied(self, service, strict_config):
        """Test rate limit check when request is denied."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=False)
            mock_limiter.get_remaining = Mock(return_value=0)
            mock_limiter.get_retry_after = Mock(return_value=30)
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("strict", strict_config)
            
            result = await service.check_rate_limit("user456", "strict")
            
            assert result.allowed is False
            assert result.remaining == 0
            assert result.retry_after == 30

    @pytest.mark.asyncio
    async def test_burst_handling(self, service):
        """Test handling of burst requests within burst size."""
        burst_config = RateLimitConfig(requests_per_second=2, burst_size=5)
        
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            # First few requests allowed (burst), then denied
            mock_limiter.is_allowed = AsyncMock(side_effect=[True, True, True, True, True, False])
            mock_limiter.get_remaining = Mock(side_effect=[4, 3, 2, 1, 0, 0])
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("burst_test", burst_config)
            
            # Make burst requests
            results = []
            for i in range(6):
                result = await service.check_rate_limit(f"user{i}", "burst_test")
                results.append(result.allowed)
            
            # First 5 should be allowed (burst), 6th denied
            assert results == [True, True, True, True, True, False]

    @pytest.mark.asyncio
    async def test_user_isolation(self, service, basic_config):
        """Test that different users have separate rate limits."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=True)
            mock_limiter.get_remaining = Mock(return_value=9)
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("isolated", basic_config)
            
            # Different users should each get their own rate limit
            result1 = await service.check_rate_limit("user1", "isolated")
            result2 = await service.check_rate_limit("user2", "isolated")
            
            assert result1.allowed is True
            assert result2.allowed is True
            
            # Should have been called for each user separately
            assert mock_limiter.is_allowed.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_limiters_independence(self, service):
        """Test multiple rate limiters work independently."""
        config1 = RateLimitConfig(requests_per_second=10, burst_size=15)
        config2 = RateLimitConfig(requests_per_second=5, burst_size=8)
        
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter1 = Mock()
            mock_limiter2 = Mock()
            mock_limiter1.is_allowed = AsyncMock(return_value=True)
            mock_limiter2.is_allowed = AsyncMock(return_value=False)
            mock_limiter_class.side_effect = [mock_limiter1, mock_limiter2]
            
            service.add_limiter("fast", config1)
            service.add_limiter("slow", config2)
            
            result1 = await service.check_rate_limit("user1", "fast")
            result2 = await service.check_rate_limit("user1", "slow")
            
            assert result1.allowed is True
            assert result2.allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_reset_after_time(self, service, strict_config):
        """Test rate limit resets after timeout period."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            # First denied, then allowed after reset
            mock_limiter.is_allowed = AsyncMock(side_effect=[False, True])
            mock_limiter.get_remaining = Mock(side_effect=[0, 1])
            mock_limiter.get_retry_after = Mock(return_value=1)
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("reset_test", strict_config)
            
            # First request denied
            result1 = await service.check_rate_limit("user1", "reset_test")
            assert result1.allowed is False
            
            # Simulate time passage (in real implementation, limiter handles this)
            await asyncio.sleep(0.1)
            
            # Second request allowed (after reset)
            result2 = await service.check_rate_limit("user1", "reset_test")
            assert result2.allowed is True

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_checks(self, service, basic_config):
        """Test concurrent rate limit checks are handled correctly."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=True)
            mock_limiter.get_remaining = Mock(return_value=5)
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("concurrent", basic_config)
            
            # Make concurrent requests
            tasks = []
            for i in range(10):
                task = service.check_rate_limit(f"user{i}", "concurrent")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(results) == 10
            assert all(result.allowed for result in results)

    @pytest.mark.asyncio
    async def test_rate_limit_metrics_tracking(self, service, basic_config):
        """Test rate limit metrics are tracked correctly."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=True)
            mock_limiter.get_metrics = Mock(return_value={
                'total_requests': 100,
                'allowed_requests': 95,
                'denied_requests': 5,
                'current_usage': 3
            })
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("metrics_test", basic_config)
            
            # Make some requests
            await service.check_rate_limit("user1", "metrics_test")
            
            metrics = await service.get_limiter_metrics("metrics_test")
            
            assert metrics['total_requests'] == 100
            assert metrics['allowed_requests'] == 95
            assert metrics['denied_requests'] == 5

    @pytest.mark.asyncio
    async def test_get_metrics_for_nonexistent_limiter(self, service):
        """Test getting metrics for non-existent limiter."""
        metrics = await service.get_limiter_metrics("unknown")
        assert metrics is None

    @pytest.mark.asyncio
    async def test_remove_limiter(self, service, basic_config):
        """Test removing a rate limiter."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter_class.return_value = Mock()
            
            service.add_limiter("removable", basic_config)
            assert "removable" in service._limiters
            
            service.remove_limiter("removable")
            assert "removable" not in service._limiters

    def test_remove_nonexistent_limiter_safe(self, service):
        """Test removing non-existent limiter is safe."""
        # Should not raise exception
        service.remove_limiter("nonexistent")

    @pytest.mark.asyncio
    async def test_clear_user_limits(self, service, basic_config):
        """Test clearing rate limits for specific user."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.clear_user_limits = AsyncMock()
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("clearable", basic_config)
            
            await service.clear_user_limits("user123", "clearable")
            
            mock_limiter.clear_user_limits.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_global_rate_limit_override(self, service):
        """Test global rate limit override functionality."""
        override_config = RateLimitConfig(requests_per_second=1000, burst_size=2000)
        
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=True)
            mock_limiter_class.return_value = mock_limiter
            
            # Set global override
            service.set_global_override(override_config)
            
            # All requests should use override config
            result = await service.check_rate_limit("user1", "any_limiter")
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_whitelist_functionality(self, service, strict_config):
        """Test user whitelist bypasses rate limits."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(return_value=False)  # Would normally deny
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("strict_test", strict_config)
            
            # Add user to whitelist
            service.add_to_whitelist("vip_user")
            
            # Whitelisted user should be allowed despite rate limit
            result = await service.check_rate_limit("vip_user", "strict_test")
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_with_different_time_windows(self, service):
        """Test rate limiting with different time windows."""
        minute_config = RateLimitConfig(requests_per_second=60, burst_size=100)  # Per minute
        hour_config = RateLimitConfig(requests_per_second=1, burst_size=3600)   # Per hour
        
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter1 = Mock()
            mock_limiter2 = Mock()
            mock_limiter1.is_allowed = AsyncMock(return_value=True)
            mock_limiter2.is_allowed = AsyncMock(return_value=True)
            mock_limiter_class.side_effect = [mock_limiter1, mock_limiter2]
            
            service.add_limiter("per_minute", minute_config)
            service.add_limiter("per_hour", hour_config)
            
            # Both should be allowed initially
            result1 = await service.check_rate_limit("user1", "per_minute")
            result2 = await service.check_rate_limit("user1", "per_hour")
            
            assert result1.allowed is True
            assert result2.allowed is True

    @pytest.mark.asyncio
    async def test_error_handling_in_rate_limiter(self, service, basic_config):
        """Test error handling when rate limiter fails."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.is_allowed = AsyncMock(side_effect=Exception("Limiter error"))
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("error_test", basic_config)
            
            # Should handle error gracefully (implementation dependent)
            with patch('netra_backend.app.services.rate_limiting.rate_limiting_service.logger') as mock_logger:
                result = await service.check_rate_limit("user1", "error_test")
                
                # Implementation might log error and allow/deny based on policy
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_rate_limit_configuration_updates(self, service):
        """Test updating rate limit configuration dynamically."""
        initial_config = RateLimitConfig(requests_per_second=5, burst_size=10)
        updated_config = RateLimitConfig(requests_per_second=10, burst_size=20)
        
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter1 = Mock()
            mock_limiter2 = Mock()
            mock_limiter_class.side_effect = [mock_limiter1, mock_limiter2]
            
            # Add initial config
            service.add_limiter("updatable", initial_config)
            assert service._limiters["updatable"] == mock_limiter1
            
            # Update config (replace limiter)
            service.add_limiter("updatable", updated_config)
            assert service._limiters["updatable"] == mock_limiter2

    @pytest.mark.asyncio
    async def test_service_shutdown_cleanup(self, service, basic_config):
        """Test service shutdown cleans up resources."""
        with patch('netra_backend.app.services.api_gateway.rate_limiter.ApiGatewayRateLimiter') as mock_limiter_class:
            mock_limiter = Mock()
            mock_limiter.shutdown = AsyncMock()
            mock_limiter_class.return_value = mock_limiter
            
            service.add_limiter("cleanup_test", basic_config)
            
            await service.shutdown()
            
            # Should have called shutdown on limiter
            mock_limiter.shutdown.assert_called_once()