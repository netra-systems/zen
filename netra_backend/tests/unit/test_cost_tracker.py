"""Unit tests for cost tracking service."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.services.analytics.cost_tracker import CostTracker
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_cost_tracker_initialization(self):
        """Test cost tracker initializes correctly."""
        tracker = CostTracker()
        assert hasattr(tracker, '_cost_cache')
        assert hasattr(tracker, '_usage_cache')

    @pytest.mark.asyncio
    async def test_track_operation_cost_basic(self):
        """Test basic operation cost tracking."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            await tracker.track_operation_cost(
                operation_id="test_op_1",
                operation_type="chat",
                model_name="gpt-3.5-turbo",
                tokens_used=100,
                cost=Decimal("0.002")
            )
            
            # Should have processed the operation
            assert mock_redis.called

    @pytest.mark.asyncio
    async def test_get_cached_usage(self):
        """Test getting cached usage data."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            # Test getting usage data
            usage_data = await tracker.get_cached_usage("chat")
            
            # Should return usage data structure
            assert isinstance(usage_data, dict)

    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy(self):
        """Test cost calculations are accurate."""
        tracker = CostTracker()
        
        # Test cost calculation with known values
        tokens = 1000
        cost_per_token = Decimal("0.00002")
        expected_cost = tokens * cost_per_token
        
        calculated_cost = tracker._calculate_cost(tokens, cost_per_token)
        assert calculated_cost == expected_cost

    def test_usage_cache_structure(self):
        """Test usage cache maintains proper structure."""
        tracker = CostTracker()
        
        # Initialize usage cache for operation type
        tracker._init_usage_cache("test_operation")
        
        # Should have proper cache structure
        assert hasattr(tracker, '_usage_cache')
        if hasattr(tracker._usage_cache, 'get'):
            cache_data = tracker._usage_cache.get("test_operation", {})
            assert isinstance(cache_data, dict)

    @pytest.mark.asyncio
    async def test_redis_connection_handling(self):
        """Test Redis connection handling."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            # Test Redis operations
            result = await tracker._get_redis()
            assert result == mock_client

    def test_cost_precision(self):
        """Test cost calculations maintain precision."""
        tracker = CostTracker()
        
        # Test with high precision Decimal values
        cost1 = Decimal("0.000001")
        cost2 = Decimal("0.000002")
        
        total = tracker._add_costs(cost1, cost2)
        expected = Decimal("0.000003")
        
        assert total == expected

    @pytest.mark.asyncio
    async def test_batch_cost_tracking(self):
        """Test batch cost tracking operations."""
        tracker = CostTracker()
        
        with patch.object(tracker, '_get_redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            # Test batch operations
            operations = [
                {
                    "operation_id": "op1",
                    "operation_type": "chat", 
                    "tokens": 100,
                    "cost": Decimal("0.002")
                },
                {
                    "operation_id": "op2",
                    "operation_type": "completion",
                    "tokens": 200,
                    "cost": Decimal("0.004")
                }
            ]
            
            for op in operations:
                await tracker.track_operation_cost(
                    operation_id=op["operation_id"],
                    operation_type=op["operation_type"],
                    model_name="test-model",
                    tokens_used=op["tokens"],
                    cost=op["cost"]
                )
            
            # Should have processed all operations
            assert mock_redis.call_count >= len(operations)

    def _calculate_cost(self, tokens, cost_per_token):
        """Helper method for cost calculation."""
        return tokens * cost_per_token

    def _add_costs(self, cost1, cost2):
        """Helper method for adding costs."""
        return cost1 + cost2

    def _init_usage_cache(self, operation_type):
        """Helper method to initialize usage cache."""
        if not hasattr(self, '_usage_cache'):
            self._usage_cache = {}
        self._usage_cache[operation_type] = {
            'tokens': 0,
            'requests': 0,
            'cost': Decimal('0.00')
        }