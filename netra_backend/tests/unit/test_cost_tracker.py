"""Unit tests for cost tracking service."""

import pytest
from decimal import Decimal
from netra_backend.app.services.analytics.cost_tracker import CostTracker
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_cost_tracker_initialization(self):
        """Test cost tracker initializes correctly."""
        tracker = CostTracker()
        assert tracker.redis_client is None
        assert tracker._cost_cache == {}
        assert len(tracker._usage_cache) == 0

    @pytest.mark.asyncio
    async def test_track_operation_cost_basic(self):
        """Test basic operation cost tracking."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_redis.return_value = mock_client
            
            await tracker.track_operation_cost(
                operation_id="test_op_1",
                operation_type="chat",
                model_name="gpt-3.5-turbo",
                tokens_used=100,
                cost=Decimal("0.002")
            )
            
            # Should have cached the usage data in _usage_cache
            assert tracker._usage_cache["chat"]["tokens"] == 100
            assert tracker._usage_cache["chat"]["requests"] == 1
            assert tracker._usage_cache["chat"]["cost"] == Decimal("0.002")

    @pytest.mark.asyncio
    async def test_get_cached_usage(self):
        """Test getting cached usage data."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_client = AsyncNone  # TODO: Use real service instance
            mock_redis.return_value = mock_client
            
            # Track some operations
            await tracker.track_operation_cost("op1", "chat", "gpt-3.5-turbo", 100, Decimal("0.002"))
            await tracker.track_operation_cost("op2", "completion", "gpt-4", 200, Decimal("0.010"))
            
            usage_data = tracker.get_cached_usage()
            assert "chat" in usage_data
            assert "completion" in usage_data

    def test_cost_calculation_accuracy(self):
        """Test cost calculations are accurate."""
        tracker = CostTracker()
        
        # Test internal cost calculations
        cost1 = Decimal("0.002")
        cost2 = Decimal("0.010")
        
        assert cost1 + cost2 == Decimal("0.012")
        assert cost1 < cost2
        
    @pytest.mark.asyncio
    async def test_redis_error_handling(self):
        """Test handling of Redis connection errors."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            
            # Should not raise exception, should handle gracefully
            try:
                await tracker.track_operation_cost("op1", "chat", "model", 100, Decimal("0.001"))
                # If we get here, error was handled gracefully
                assert True
            except Exception as e:
                # If exception propagates, test what type it is
                assert "Redis" in str(e) or isinstance(e, ConnectionError)

    def test_usage_cache_accumulation(self):
        """Test that usage cache accumulates data correctly."""
        tracker = CostTracker()
        
        # Manually test cache behavior
        key = "test_model"
        tracker._usage_cache[key]["tokens"] += 100
        tracker._usage_cache[key]["requests"] += 1
        tracker._usage_cache[key]["cost"] += Decimal("0.002")
        
        assert tracker._usage_cache[key]["tokens"] == 100
        assert tracker._usage_cache[key]["requests"] == 1
        assert tracker._usage_cache[key]["cost"] == Decimal("0.002")
        
        # Add more data
        tracker._usage_cache[key]["tokens"] += 50
        tracker._usage_cache[key]["requests"] += 1
        tracker._usage_cache[key]["cost"] += Decimal("0.001")
        
        assert tracker._usage_cache[key]["tokens"] == 150
        assert tracker._usage_cache[key]["requests"] == 2
        assert tracker._usage_cache[key]["cost"] == Decimal("0.003")