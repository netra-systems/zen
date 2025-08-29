"""Comprehensive Unit Tests for StateCacheManager

StateCacheManager is critical for the 3-tier architecture, managing:
- Primary Redis state storage (not just cache)
- State serialization and compression
- TTL management for active vs completed states
- Version tracking for optimistic locking
- Thread context updates

Business Context: StateCacheManager handles PRIMARY storage for all active agent states,
supporting $25K+ MRR workloads with sub-100ms latency requirements. This is the
authoritative storage layer for active states in the 3-tier persistence architecture:
- Redis: PRIMARY active state storage (hot data)
- ClickHouse: Historical analytics (completed runs)
- PostgreSQL: Metadata and recovery checkpoints only

Test Coverage:
- All primary methods: save_primary_state, load_primary_state, cache_legacy_state
- Error handling: Redis unavailable, connection failures, serialization errors
- Business rules: TTL management (24h active, 1h completed, 1w checkpoints)
- Version tracking for optimistic locking and concurrency control
- Thread context management for active run tracking
- Backward compatibility with deprecated methods
- Performance validation with realistic large datasets
"""

import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent_state import (
    AgentPhase,
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_cache_manager import StateCacheManager
from netra_backend.app.services.state_serialization import DateTimeEncoder


class TestStateCacheManager:
    """Test suite for StateCacheManager primary state storage functionality."""

    @pytest.fixture
    def cache_manager(self):
        """Create StateCacheManager instance for testing."""
        return StateCacheManager()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client with common methods."""
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.expire = AsyncMock(return_value=True)
        mock_client.keys = AsyncMock(return_value=[])
        mock_client.ttl = AsyncMock(return_value=3600)
        return mock_client

    @pytest.fixture
    def sample_state_data(self):
        """Create sample state data for testing."""
        return {
            "user_request": "Optimize database performance",
            "chat_thread_id": "thread_123",
            "user_id": "user_456",
            "run_id": "run_789",
            "step_count": 5,
            "messages": [{"role": "user", "content": "Hello"}],
            "metadata": {
                "agent_phase": "data_analysis",
                "checkpoint_type": "auto"
            }
        }

    @pytest.fixture
    def sample_request(self, sample_state_data):
        """Create sample StatePersistenceRequest for testing."""
        return StatePersistenceRequest(
            run_id="run_789",
            thread_id="thread_123",
            user_id="user_456",
            state_data=sample_state_data,
            checkpoint_type=CheckpointType.AUTO,
            agent_phase=AgentPhase.DATA_ANALYSIS,
            execution_context={"environment": "test"},
            is_recovery_point=False
        )

    @pytest.fixture
    def large_state_data(self):
        """Create large state data for compression testing."""
        return {
            "user_request": "Large optimization request",
            "large_field": "x" * 2000,  # 2KB of data
            "metadata": {"size": "large"},
            "step_count": 10
        }

    @pytest.mark.asyncio
    async def test_save_primary_state_success(self, cache_manager, mock_redis_client, sample_request):
        """Test successful primary state save to Redis."""
        # Arrange
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(sample_request)
            
            # Assert
            assert result is True
            
            # Verify Redis calls were made (state save + thread context update)
            assert mock_redis_client.set.call_count == 2  # Agent state + thread context
            mock_redis_client.incr.assert_called_once()
            mock_redis_client.expire.assert_called_once()
            
            # Find the agent state set call
            state_set_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0].startswith("agent_state:"):
                    state_set_call = call
                    break
            
            assert state_set_call is not None
            redis_key = state_set_call[0][0]
            assert redis_key == f"agent_state:{sample_request.run_id}"
            
            # Verify state record structure
            state_json = state_set_call[0][1]
            state_record = json.loads(state_json)
            assert "state_data" in state_record
            assert "metadata" in state_record
            assert state_record["metadata"]["run_id"] == sample_request.run_id
            assert state_record["metadata"]["source"] == "primary_redis"

    @pytest.mark.asyncio
    async def test_save_primary_state_with_compression(self, cache_manager, mock_redis_client, large_state_data):
        """Test primary state save with large data (validates JSON serialization)."""
        # Arrange
        large_request = StatePersistenceRequest(
            run_id="run_large",
            thread_id="thread_large",
            user_id="user_large",
            state_data=large_state_data,
            checkpoint_type=CheckpointType.AUTO
        )
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(large_request)
            
            # Assert
            assert result is True
            assert mock_redis_client.set.call_count == 2  # Agent state + thread context
            
            # Find the agent state set call
            state_set_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0].startswith("agent_state:"):
                    state_set_call = call
                    break
            
            # Verify large data is properly serialized
            state_json = state_set_call[0][1]
            state_record = json.loads(state_json)
            assert len(state_record["state_data"]["large_field"]) == 2000

    @pytest.mark.asyncio
    async def test_save_primary_state_redis_unavailable(self, cache_manager, sample_request):
        """Test save behavior when Redis client is unavailable."""
        # Arrange
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=None):
            # Act
            result = await cache_manager.save_primary_state(sample_request)
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_save_primary_state_redis_exception(self, cache_manager, mock_redis_client, sample_request):
        """Test save behavior when Redis operation fails."""
        # Arrange
        mock_redis_client.set.side_effect = Exception("Redis connection error")
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(sample_request)
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_load_primary_state_success(self, cache_manager, mock_redis_client, sample_state_data):
        """Test successful primary state load from Redis."""
        # Arrange
        run_id = "run_789"
        state_record = {
            "state_data": sample_state_data,
            "metadata": {
                "run_id": run_id,
                "agent_phase": "data_analysis",
                "step_count": 5,
                "source": "primary_redis"
            }
        }
        mock_redis_client.get.return_value = json.dumps(state_record, cls=DateTimeEncoder)
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.load_primary_state(run_id)
            
            # Assert
            assert result is not None
            assert isinstance(result, DeepAgentState)
            assert result.user_request == sample_state_data["user_request"]
            assert result.run_id == sample_state_data["run_id"]
            assert result.step_count == sample_state_data["step_count"]
            
            # Verify Redis key
            mock_redis_client.get.assert_called_once_with(f"agent_state:{run_id}")

    @pytest.mark.asyncio
    async def test_load_primary_state_not_found(self, cache_manager, mock_redis_client):
        """Test load behavior when state not found in Redis."""
        # Arrange
        run_id = "nonexistent_run"
        mock_redis_client.get.return_value = None
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.load_primary_state(run_id)
            
            # Assert
            assert result is None
            mock_redis_client.get.assert_called_once_with(f"agent_state:{run_id}")

    @pytest.mark.asyncio
    async def test_load_primary_state_redis_unavailable(self, cache_manager):
        """Test load behavior when Redis client is unavailable."""
        # Arrange
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=None):
            # Act
            result = await cache_manager.load_primary_state("run_123")
            
            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_legacy_state(self, cache_manager, mock_redis_client, sample_state_data):
        """Test backward compatibility caching of legacy PostgreSQL state."""
        # Arrange
        run_id = "legacy_run_123"
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            await cache_manager.cache_legacy_state(run_id, sample_state_data)
            
            # Assert
            mock_redis_client.set.assert_called_once()
            
            # Verify legacy state record structure
            set_call_args = mock_redis_client.set.call_args
            state_json = set_call_args[0][1]
            state_record = json.loads(state_json)
            assert state_record["metadata"]["source"] == "legacy_postgresql"
            assert "migrated_at" in state_record["metadata"]
            assert state_record["state_data"] == sample_state_data

    @pytest.mark.asyncio
    async def test_version_tracking_increment(self, cache_manager, mock_redis_client, sample_request):
        """Test version tracking for optimistic locking."""
        # Arrange
        mock_redis_client.incr.return_value = 5  # Version 5
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(sample_request)
            
            # Assert
            assert result is True
            
            # Verify version key operations
            version_key = f"agent_state_version:{sample_request.run_id}"
            mock_redis_client.incr.assert_called_once_with(version_key)
            mock_redis_client.expire.assert_called_with(version_key, cache_manager.active_state_ttl)

    @pytest.mark.asyncio
    async def test_ttl_management_active_vs_completed(self, cache_manager, mock_redis_client, sample_request):
        """Test TTL management for different state types."""
        # Arrange - Test active state TTL
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act - Save active state
            await cache_manager.save_primary_state(sample_request)
            
            # Assert - Should use active state TTL
            set_call_args = mock_redis_client.set.call_args
            ttl_used = set_call_args.kwargs.get('ex', set_call_args[0][2] if len(set_call_args[0]) > 2 else None)
            assert ttl_used == cache_manager.active_state_ttl
            
            # Act - Mark state as completed
            await cache_manager.mark_state_completed(sample_request.run_id)
            
            # Assert - Should update TTL to completed state TTL
            mock_redis_client.expire.assert_called_with(
                f"agent_state:{sample_request.run_id}", 
                cache_manager.completed_state_ttl
            )

    @pytest.mark.asyncio
    async def test_ttl_management_recovery_point(self, cache_manager, mock_redis_client):
        """Test TTL management for recovery checkpoints."""
        # Arrange - Create recovery point request
        recovery_request = StatePersistenceRequest(
            run_id="recovery_run",
            thread_id="thread_recovery",
            user_id="user_recovery",
            state_data={"test": "data"},
            is_recovery_point=True
        )
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(recovery_request)
            
            # Assert
            assert result is True
            
            # Find the agent state set call
            state_set_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0].startswith("agent_state:"):
                    state_set_call = call
                    break
            
            # Verify recovery point uses longer TTL
            ttl_used = state_set_call.kwargs.get('ex')
            assert ttl_used == cache_manager.checkpoint_ttl

    @pytest.mark.asyncio
    async def test_thread_context_updates(self, cache_manager, mock_redis_client, sample_request):
        """Test thread context updates during state save."""
        # Arrange
        mock_redis_client.get.return_value = "1"  # Version number
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            await cache_manager.save_primary_state(sample_request)
            
            # Assert thread context was updated
            thread_key = f"thread_context:{sample_request.thread_id}"
            
            # Find the thread context set call
            thread_context_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0] == thread_key:
                    thread_context_call = call
                    break
            
            assert thread_context_call is not None
            
            # Verify thread context structure
            context_json = thread_context_call[0][1]
            context = json.loads(context_json)
            assert context["current_run_id"] == sample_request.run_id
            assert context["user_id"] == sample_request.user_id
            assert "last_updated" in context
            # sample_request.checkpoint_type is already a string value from the enum
            assert context["checkpoint_type"] == sample_request.checkpoint_type

    @pytest.mark.asyncio
    async def test_serialization_with_datetime_objects(self, cache_manager, mock_redis_client):
        """Test serialization handles datetime objects properly."""
        # Arrange
        current_time = datetime.now(timezone.utc)
        state_data_with_datetime = {
            "user_request": "Test request",
            "created_at": current_time,
            "metadata": {
                "timestamp": current_time
            }
        }
        
        request = StatePersistenceRequest(
            run_id="datetime_run",
            thread_id="datetime_thread",
            user_id="datetime_user",
            state_data=state_data_with_datetime
        )
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(request)
            
            # Assert
            assert result is True
            
            # Find the agent state set call
            state_set_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0].startswith("agent_state:"):
                    state_set_call = call
                    break
            
            # Verify datetime serialization
            state_json = state_set_call[0][1]
            # Should not raise exception when parsing JSON with datetime
            state_record = json.loads(state_json)
            assert isinstance(state_record["state_data"]["created_at"], str)
            assert current_time.isoformat() in state_record["state_data"]["created_at"]

    @pytest.mark.asyncio
    async def test_compression_threshold_behavior(self, cache_manager, mock_redis_client):
        """Test behavior with data at compression threshold."""
        # Arrange - Create data just over typical compression threshold
        large_content = "x" * 1500  # 1.5KB
        large_state_data = {
            "user_request": "Large request",
            "large_content": large_content,
            "metadata": {"size": "large"}
        }
        
        request = StatePersistenceRequest(
            run_id="compression_run",
            thread_id="compression_thread", 
            user_id="compression_user",
            state_data=large_state_data
        )
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.save_primary_state(request)
            
            # Assert
            assert result is True
            
            # Find the agent state set call
            state_set_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0].startswith("agent_state:"):
                    state_set_call = call
                    break
            
            # Verify data is stored as JSON (no compression in Redis layer)
            state_json = state_set_call[0][1]
            state_record = json.loads(state_json)
            assert state_record["state_data"]["large_content"] == large_content

    @pytest.mark.asyncio
    async def test_error_handling_redis_connection_failure(self, cache_manager):
        """Test comprehensive error handling for Redis connection failures."""
        # Arrange
        sample_request = StatePersistenceRequest(
            run_id="error_run",
            thread_id="error_thread",
            user_id="error_user",
            state_data={"test": "data"}
        )
        
        # Test different failure scenarios
        failure_scenarios = [
            None,  # Redis client unavailable
            Exception("Connection timeout"),  # Connection exception
            Exception("Memory full"),  # Memory exception
        ]
        
        for scenario in failure_scenarios:
            if scenario is None:
                with patch.object(cache_manager.redis_manager, 'get_client', return_value=None):
                    # Act
                    result = await cache_manager.save_primary_state(sample_request)
                    
                    # Assert
                    assert result is False
            else:
                mock_client = AsyncMock()
                mock_client.set.side_effect = scenario
                
                with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_client):
                    # Act
                    result = await cache_manager.save_primary_state(sample_request)
                    
                    # Assert
                    assert result is False

    @pytest.mark.asyncio
    async def test_cache_state_in_redis_backward_compatibility(self, cache_manager, sample_request):
        """Test backward compatibility method (deprecated)."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_redis_client.set.return_value = True
        mock_redis_client.incr.return_value = 1
        mock_redis_client.expire.return_value = True
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            with patch.object(cache_manager, 'save_primary_state', return_value=True) as mock_save:
                # Act
                await cache_manager.cache_state_in_redis(sample_request)
                
                # Assert
                mock_save.assert_called_once_with(sample_request)

    @pytest.mark.asyncio
    async def test_load_from_redis_cache_backward_compatibility(self, cache_manager, mock_redis_client):
        """Test backward compatibility load method (deprecated)."""
        # Arrange
        run_id = "compat_run"
        expected_state = DeepAgentState(user_request="Test")
        
        with patch.object(cache_manager, 'load_primary_state', return_value=expected_state) as mock_load:
            # Act
            result = await cache_manager.load_from_redis_cache(run_id)
            
            # Assert
            mock_load.assert_called_once_with(run_id)
            assert result == expected_state

    @pytest.mark.asyncio
    async def test_get_active_runs_by_thread(self, cache_manager, mock_redis_client):
        """Test retrieving active runs for a specific thread."""
        # Arrange
        thread_id = "test_thread_123"
        context_data = {
            "current_run_id": "active_run_456",
            "user_id": "user_789",
            "last_updated": time.time()
        }
        mock_redis_client.get.return_value = json.dumps(context_data)
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.get_active_runs(thread_id)
            
            # Assert
            assert result == ["active_run_456"]
            mock_redis_client.get.assert_called_once_with(f"thread_context:{thread_id}")

    @pytest.mark.asyncio
    async def test_get_active_runs_all_threads(self, cache_manager, mock_redis_client):
        """Test retrieving all active runs across threads."""
        # Arrange
        mock_redis_client.keys.return_value = [
            "agent_state:run_123",
            "agent_state:run_456",
            "agent_state:run_789"
        ]
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.get_active_runs()
            
            # Assert
            assert result == ["run_123", "run_456", "run_789"]
            mock_redis_client.keys.assert_called_once_with("agent_state:*")

    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, cache_manager, mock_redis_client):
        """Test cleanup of states without TTL."""
        # Arrange
        mock_redis_client.keys.return_value = [
            "agent_state:run_no_ttl",
            "agent_state:run_with_ttl"
        ]
        mock_redis_client.ttl.side_effect = [-1, 3600]  # First has no TTL, second has TTL
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            result = await cache_manager.cleanup_expired_states()
            
            # Assert
            assert result == 1  # One state had TTL set
            mock_redis_client.expire.assert_called_once_with(
                "agent_state:run_no_ttl", 
                cache_manager.active_state_ttl
            )

    @pytest.mark.asyncio
    async def test_extract_value_enum_handling(self, cache_manager):
        """Test extract_value helper method with enums and strings."""
        # Arrange
        enum_value = CheckpointType.AUTO
        string_value = "manual"
        
        # Act & Assert
        assert cache_manager.extract_value(enum_value) == "auto"
        assert cache_manager.extract_value(string_value) == "manual"
        assert cache_manager.extract_value(None) is None

    @pytest.mark.asyncio
    async def test_performance_considerations_large_dataset(self, cache_manager, mock_redis_client):
        """Test performance considerations with realistic large datasets."""
        # Arrange - Create realistic large agent state
        large_messages = [{"role": "user", "content": f"Message {i}" * 100} for i in range(50)]
        large_metadata = {f"key_{i}": f"value_{i}" * 20 for i in range(100)}
        
        large_state_data = {
            "user_request": "Complex optimization analysis",
            "messages": large_messages,
            "metadata": large_metadata,
            "step_count": 25,
            "processing_logs": ["log entry " * 50 for _ in range(20)]
        }
        
        request = StatePersistenceRequest(
            run_id="perf_run",
            thread_id="perf_thread",
            user_id="perf_user",
            state_data=large_state_data
        )
        
        with patch.object(cache_manager.redis_manager, 'get_client', return_value=mock_redis_client):
            # Act
            start_time = time.time()
            result = await cache_manager.save_primary_state(request)
            end_time = time.time()
            
            # Assert
            assert result is True
            
            # Verify serialization completes within reasonable time (< 100ms for this size)
            execution_time = end_time - start_time
            assert execution_time < 0.1, f"Serialization took {execution_time:.3f}s, exceeding 100ms limit"
            
            # Find the agent state set call and verify large data is properly handled
            state_set_call = None
            for call in mock_redis_client.set.call_args_list:
                if call[0][0].startswith("agent_state:"):
                    state_set_call = call
                    break
            
            state_json = state_set_call[0][1]
            assert len(state_json) > 10000  # Should be substantial JSON
            
            # Verify JSON is valid
            state_record = json.loads(state_json)
            assert len(state_record["state_data"]["messages"]) == 50
            assert len(state_record["state_data"]["metadata"]) == 100