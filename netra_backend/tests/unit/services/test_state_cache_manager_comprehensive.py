"""
Comprehensive Unit Test Suite for StateCacheManager

MISSION CRITICAL: This class provides state caching functionality for agent execution
persistence and Redis integration for multi-service coordination.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Performance & State Persistence
- Value Impact: Enables agent state persistence across service restarts and scaling
- Strategic Impact: Critical for reliable agent execution and user session continuity

Coverage Requirements:
- 100% line coverage of StateCacheManager methods
- State serialization and deserialization validation
- Redis integration patterns (save, load, delete)
- Error handling for Redis connectivity issues
- Thread context and agent state management
- JSON serialization with datetime handling
- Fallback to local cache when Redis unavailable

Test Categories:
- Happy Path Tests: Standard state operations work correctly
- Serialization Tests: JSON handling with complex data types
- Redis Integration Tests: Redis operations with fallback behavior
- Error Handling Tests: Graceful degradation when Redis fails
- Thread Context Tests: Thread-to-run ID mapping and cleanup
- Performance Tests: Efficient caching and retrieval patterns
"""

import json
import pytest
import time
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# SSOT imports using absolute paths
from netra_backend.app.services.state_persistence import StateCacheManager, state_cache_manager
from netra_backend.app.redis_manager import redis_manager


@pytest.mark.unit
class TestStateCacheManagerInitialization():
    """Test StateCacheManager initialization and basic functionality."""
    
    def test_state_cache_manager_initializes_correctly(self):
        """Test StateCacheManager initializes with proper empty state."""
        manager = StateCacheManager()
        
        assert isinstance(manager._cache, dict)
        assert len(manager._cache) == 0
        assert isinstance(manager._versions, dict)
        assert len(manager._versions) == 0
        
    def test_global_state_cache_manager_instance_available(self):
        """Test global state_cache_manager instance is properly initialized."""
        assert isinstance(state_cache_manager, StateCacheManager)
        assert hasattr(state_cache_manager, '_cache')
        assert hasattr(state_cache_manager, '_versions')


@pytest.mark.unit
class TestStateCacheManagerSerialization():
    """Test data serialization and deserialization."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    def test_serialize_state_data_handles_simple_data(self):
        """Test serialization works with simple data types."""
        data = {"key": "value", "number": 42, "boolean": True}
        
        serialized = self.manager._serialize_state_data(data)
        
        assert isinstance(serialized, str)
        deserialized = json.loads(serialized)
        assert deserialized == data
        
    def test_serialize_state_data_handles_datetime_objects(self):
        """Test serialization properly handles datetime objects."""
        now = datetime.now()
        data = {"timestamp": now, "message": "test"}
        
        serialized = self.manager._serialize_state_data(data)
        deserialized = json.loads(serialized)
        
        assert "timestamp" in deserialized
        assert isinstance(deserialized["timestamp"], str)
        assert deserialized["message"] == "test"
        
    def test_serialize_state_data_handles_complex_nested_data(self):
        """Test serialization works with complex nested structures."""
        data = {
            "user": {"id": "user123", "name": "Test User"},
            "session": {
                "id": "session456",
                "created_at": datetime.now(),
                "config": {"timeout": 3600, "features": ["a", "b"]}
            }
        }
        
        serialized = self.manager._serialize_state_data(data)
        deserialized = json.loads(serialized)
        
        assert deserialized["user"]["id"] == "user123"
        assert deserialized["session"]["config"]["timeout"] == 3600
        assert isinstance(deserialized["session"]["created_at"], str)
        
    def test_serialize_state_data_raises_error_for_non_serializable_objects(self):
        """Test serialization raises error for non-JSON-serializable objects."""
        class NonSerializable:
            pass
        
        data = {"object": NonSerializable()}
        
        with pytest.raises(TypeError):
            self.manager._serialize_state_data(data)


@pytest.mark.unit
class TestStateCacheManagerPrimaryStateOperations():
    """Test primary state operations (save/load/delete)."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_save_primary_state_with_valid_request(self):
        """Test saving primary state with valid request object."""
        # Mock request with required attributes
        mock_request = Mock()
        mock_request.run_id = "run_123"
        mock_request.state_data = {"step": 1, "status": "processing"}
        mock_request.thread_id = "thread_456"
        mock_request.user_id = "user_789"
        
        # Mock Redis to succeed
        with patch.object(redis_manager, 'get_client', return_value=AsyncMock()) as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis
            
            result = await self.manager.save_primary_state(mock_request)
        
        assert result is True
        assert "run_123" in self.manager._cache
        assert self.manager._cache["run_123"] == {"step": 1, "status": "processing"}
        assert self.manager._versions["run_123"] == 1
        
        # Verify Redis calls were made
        mock_redis.set.assert_called()
        
    @pytest.mark.asyncio
    async def test_save_primary_state_increments_version(self):
        """Test saving state multiple times increments version counter."""
        mock_request = Mock()
        mock_request.run_id = "run_version_test"
        mock_request.state_data = {"step": 1}
        
        with patch.object(redis_manager, 'get_client', return_value=AsyncMock()):
            # First save
            await self.manager.save_primary_state(mock_request)
            assert self.manager._versions["run_version_test"] == 1
            
            # Second save
            mock_request.state_data = {"step": 2}
            await self.manager.save_primary_state(mock_request)
            assert self.manager._versions["run_version_test"] == 2
            
    @pytest.mark.asyncio
    async def test_save_primary_state_handles_redis_failure_gracefully(self):
        """Test state save continues with local cache when Redis fails."""
        mock_request = Mock()
        mock_request.run_id = "run_redis_fail"
        mock_request.state_data = {"data": "test"}
        
        # Mock Redis to fail
        with patch.object(redis_manager, 'get_client', side_effect=Exception("Redis connection failed")):
            result = await self.manager.save_primary_state(mock_request)
        
        # Should still succeed with local cache
        assert result is True
        assert "run_redis_fail" in self.manager._cache
        assert self.manager._cache["run_redis_fail"] == {"data": "test"}
        
    @pytest.mark.asyncio
    async def test_save_primary_state_returns_false_for_invalid_request(self):
        """Test save returns False for request without required attributes."""
        mock_request = Mock()
        # Missing run_id and state_data
        del mock_request.run_id
        del mock_request.state_data
        
        result = await self.manager.save_primary_state(mock_request)
        
        assert result is False
        assert len(self.manager._cache) == 0
        
    @pytest.mark.asyncio
    async def test_load_primary_state_from_local_cache(self):
        """Test loading state from local cache when available."""
        # Manually add to cache
        test_data = {"step": 3, "status": "completed"}
        self.manager._cache["run_load_test"] = test_data
        
        result = await self.manager.load_primary_state("run_load_test")
        
        assert result == test_data
        
    @pytest.mark.asyncio
    async def test_load_primary_state_from_redis_when_not_in_cache(self):
        """Test loading state from Redis when not in local cache."""
        test_data = {"step": 2, "loaded_from": "redis"}
        serialized_data = json.dumps(test_data)
        
        # Mock Redis to return data
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = serialized_data
            mock_get_client.return_value = mock_redis
            
            result = await self.manager.load_primary_state("run_from_redis")
        
        assert result == test_data
        # Should also cache locally after loading
        assert self.manager._cache["run_from_redis"] == test_data
        
    @pytest.mark.asyncio
    async def test_load_primary_state_returns_none_when_not_found(self):
        """Test load returns None when state not found anywhere."""
        # Mock Redis to return None
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_client.return_value = mock_redis
            
            result = await self.manager.load_primary_state("nonexistent_run")
        
        assert result is None
        
    @pytest.mark.asyncio
    async def test_delete_primary_state_removes_from_cache_and_redis(self):
        """Test delete removes state from both local cache and Redis."""
        # Setup test data
        self.manager._cache["run_delete_test"] = {"data": "to_delete"}
        self.manager._versions["run_delete_test"] = 1
        
        # Mock Redis
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis
            
            result = await self.manager.delete_primary_state("run_delete_test")
        
        assert result is True
        assert "run_delete_test" not in self.manager._cache
        assert "run_delete_test" not in self.manager._versions
        
        # Verify Redis delete calls
        mock_redis.delete.assert_called()
        
    @pytest.mark.asyncio
    async def test_delete_primary_state_handles_redis_failure_gracefully(self):
        """Test delete continues when Redis delete fails."""
        # Setup test data
        self.manager._cache["run_delete_redis_fail"] = {"data": "test"}
        self.manager._versions["run_delete_redis_fail"] = 1
        
        # Mock Redis to fail
        with patch.object(redis_manager, 'get_client', side_effect=Exception("Redis delete failed")):
            result = await self.manager.delete_primary_state("run_delete_redis_fail")
        
        # Should still succeed with local cleanup
        assert result is True
        assert "run_delete_redis_fail" not in self.manager._cache
        assert "run_delete_redis_fail" not in self.manager._versions


@pytest.mark.unit
class TestStateCacheManagerAliasOperations():
    """Test alias methods that delegate to primary operations."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_cache_state_in_redis_delegates_to_save_primary_state(self):
        """Test cache_state_in_redis is an alias for save_primary_state."""
        mock_request = Mock()
        mock_request.run_id = "run_alias_test"
        mock_request.state_data = {"alias": "test"}
        
        with patch.object(self.manager, 'save_primary_state', return_value=True) as mock_save:
            result = await self.manager.cache_state_in_redis(mock_request)
        
        assert result is True
        mock_save.assert_called_once_with(mock_request)
        
    @pytest.mark.asyncio
    async def test_load_from_redis_cache_delegates_to_load_primary_state(self):
        """Test load_from_redis_cache is an alias for load_primary_state."""
        with patch.object(self.manager, 'load_primary_state', return_value={"data": "test"}) as mock_load:
            result = await self.manager.load_from_redis_cache("run_123")
        
        assert result == {"data": "test"}
        mock_load.assert_called_once_with("run_123")


@pytest.mark.unit
class TestStateCacheManagerUtilityOperations():
    """Test utility operations like caching, marking completion, etc."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_cache_deserialized_state_stores_data_directly(self):
        """Test caching deserialized state stores data without serialization."""
        test_data = {"direct": "storage", "no_serialization": True}
        
        result = await self.manager.cache_deserialized_state("run_direct", test_data)
        
        assert result is True
        assert self.manager._cache["run_direct"] == test_data
        
    @pytest.mark.asyncio
    async def test_cache_deserialized_state_handles_errors_gracefully(self):
        """Test cache_deserialized_state handles errors and returns False."""
        # Simulate error by patching dict assignment
        with patch.dict(self.manager._cache, {}, clear=True):
            with patch.object(self.manager._cache, '__setitem__', side_effect=Exception("Cache error")):
                result = await self.manager.cache_deserialized_state("run_error", {"data": "test"})
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_mark_state_completed_adds_completion_flag(self):
        """Test marking state as completed adds _completed flag."""
        # Setup existing state
        self.manager._cache["run_completion"] = {"step": 5, "status": "processing"}
        
        result = await self.manager.mark_state_completed("run_completion")
        
        assert result is True
        assert self.manager._cache["run_completion"]["_completed"] is True
        assert self.manager._cache["run_completion"]["step"] == 5  # Original data preserved
        
    @pytest.mark.asyncio
    async def test_mark_state_completed_returns_false_for_nonexistent_run(self):
        """Test mark_state_completed returns False for non-existent run ID."""
        result = await self.manager.mark_state_completed("nonexistent_run")
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_mark_state_completed_handles_non_dict_state(self):
        """Test mark_state_completed handles non-dict state gracefully."""
        # Setup non-dict state
        self.manager._cache["run_non_dict"] = "string_state"
        
        result = await self.manager.mark_state_completed("run_non_dict")
        
        assert result is True  # Still returns True as run exists
        # String state remains unchanged
        assert self.manager._cache["run_non_dict"] == "string_state"
        
    @pytest.mark.asyncio
    async def test_cache_legacy_state_delegates_to_cache_deserialized_state(self):
        """Test cache_legacy_state is an alias for cache_deserialized_state."""
        test_data = {"legacy": "format", "compatibility": True}
        
        with patch.object(self.manager, 'cache_deserialized_state', return_value=True) as mock_cache:
            result = await self.manager.cache_legacy_state("run_legacy", test_data)
        
        assert result is True
        mock_cache.assert_called_once_with("run_legacy", test_data)


@pytest.mark.unit
class TestStateCacheManagerThreadContextHandling():
    """Test thread context handling in Redis operations."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_save_primary_state_stores_thread_context_in_redis(self):
        """Test saving state stores thread context mapping in Redis."""
        mock_request = Mock()
        mock_request.run_id = "run_thread_context"
        mock_request.state_data = {"data": "test"}
        mock_request.thread_id = "thread_123"
        mock_request.user_id = "user_456"
        
        # Mock Redis
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis
            
            await self.manager.save_primary_state(mock_request)
        
        # Verify thread context was saved
        thread_context_calls = [
            call for call in mock_redis.set.call_args_list
            if 'thread_context:' in str(call)
        ]
        assert len(thread_context_calls) > 0
        
        # Extract the thread context data
        thread_context_call = thread_context_calls[0]
        context_data = json.loads(thread_context_call[0][1])
        assert context_data["current_run_id"] == "run_thread_context"
        assert context_data["user_id"] == "user_456"
        
    @pytest.mark.asyncio
    async def test_save_primary_state_handles_missing_thread_context_gracefully(self):
        """Test save handles requests without thread context gracefully."""
        mock_request = Mock()
        mock_request.run_id = "run_no_thread"
        mock_request.state_data = {"data": "test"}
        # No thread_id or user_id attributes
        
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis
            
            result = await self.manager.save_primary_state(mock_request)
        
        # Should still succeed
        assert result is True
        assert "run_no_thread" in self.manager._cache


@pytest.mark.unit
class TestStateCacheManagerErrorHandling():
    """Test error handling and exception scenarios."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_save_primary_state_handles_serialization_errors(self):
        """Test save handles serialization errors gracefully."""
        class NonSerializable:
            def __repr__(self):
                return "NonSerializable()"
        
        mock_request = Mock()
        mock_request.run_id = "run_serialization_error"
        mock_request.state_data = {"bad_object": NonSerializable()}
        
        result = await self.manager.save_primary_state(mock_request)
        
        # Should fail due to serialization error
        assert result is False
        assert "run_serialization_error" not in self.manager._cache
        
    @pytest.mark.asyncio
    async def test_load_primary_state_handles_redis_connection_errors(self):
        """Test load handles Redis connection errors gracefully."""
        with patch.object(redis_manager, 'get_client', side_effect=Exception("Redis connection lost")):
            result = await self.manager.load_primary_state("run_redis_error")
        
        assert result is None  # Should return None, not raise exception
        
    @pytest.mark.asyncio
    async def test_load_primary_state_handles_invalid_json_in_redis(self):
        """Test load handles invalid JSON data in Redis gracefully."""
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = "invalid json data"
            mock_get_client.return_value = mock_redis
            
            result = await self.manager.load_primary_state("run_invalid_json")
        
        assert result is None  # Should handle JSON decode error gracefully
        
    @pytest.mark.asyncio
    async def test_delete_primary_state_handles_missing_keys_gracefully(self):
        """Test delete handles missing keys without errors."""
        result = await self.manager.delete_primary_state("nonexistent_key")
        
        assert result is True  # Should still return True for idempotent operation


@pytest.mark.unit
class TestStateCacheManagerRedisVersionHandling():
    """Test version tracking in Redis operations."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_save_primary_state_stores_version_in_redis(self):
        """Test saving state stores version information in Redis."""
        mock_request = Mock()
        mock_request.run_id = "run_version_redis"
        mock_request.state_data = {"version": "test"}
        
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis
            
            await self.manager.save_primary_state(mock_request)
        
        # Check for version set call
        version_calls = [
            call for call in mock_redis.set.call_args_list
            if 'agent_state_version:' in str(call)
        ]
        assert len(version_calls) > 0
        
        # Version should be "1" for first save
        version_call = version_calls[0]
        assert version_call[0][1] == "1"  # Version value
        
    @pytest.mark.asyncio
    async def test_delete_primary_state_removes_version_from_redis(self):
        """Test delete removes both state and version from Redis."""
        self.manager._cache["run_version_delete"] = {"data": "test"}
        self.manager._versions["run_version_delete"] = 3
        
        with patch.object(redis_manager, 'get_client') as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis
            
            await self.manager.delete_primary_state("run_version_delete")
        
        # Check for both state and version delete calls
        delete_calls = mock_redis.delete.call_args_list
        deleted_keys = [call[0][0] for call in delete_calls]
        
        assert "agent_state:run_version_delete" in deleted_keys
        assert "agent_state_version:run_version_delete" in deleted_keys


@pytest.mark.unit  
class TestStateCacheManagerIntegrationPatterns():
    """Test integration patterns and realistic usage scenarios."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = StateCacheManager()
        
    @pytest.mark.asyncio
    async def test_complete_agent_state_lifecycle(self):
        """Test complete lifecycle: save -> load -> update -> mark complete -> delete."""
        # Create realistic agent request
        mock_request = Mock()
        mock_request.run_id = "run_lifecycle_test"
        mock_request.thread_id = "thread_lifecycle"
        mock_request.user_id = "user_lifecycle"
        mock_request.state_data = {
            "step": 1,
            "status": "started",
            "agent_type": "cost_optimizer",
            "created_at": datetime.now()
        }
        
        with patch.object(redis_manager, 'get_client', return_value=AsyncMock()):
            # 1. Save initial state
            save_result = await self.manager.save_primary_state(mock_request)
            assert save_result is True
            
            # 2. Load state back
            loaded_state = await self.manager.load_primary_state("run_lifecycle_test")
            assert loaded_state["step"] == 1
            assert loaded_state["status"] == "started"
            
            # 3. Update state
            mock_request.state_data = {
                "step": 2,
                "status": "processing",
                "agent_type": "cost_optimizer",
                "progress": 0.5
            }
            update_result = await self.manager.save_primary_state(mock_request)
            assert update_result is True
            assert self.manager._versions["run_lifecycle_test"] == 2
            
            # 4. Mark as completed
            complete_result = await self.manager.mark_state_completed("run_lifecycle_test")
            assert complete_result is True
            assert self.manager._cache["run_lifecycle_test"]["_completed"] is True
            
            # 5. Clean up
            delete_result = await self.manager.delete_primary_state("run_lifecycle_test")
            assert delete_result is True
            assert "run_lifecycle_test" not in self.manager._cache
            
    @pytest.mark.asyncio
    async def test_concurrent_state_operations_maintain_consistency(self):
        """Test concurrent operations on different run IDs maintain consistency.""" 
        # Setup multiple mock requests
        requests = []
        for i in range(5):
            mock_request = Mock()
            mock_request.run_id = f"run_concurrent_{i}"
            mock_request.state_data = {"step": i, "concurrent_test": True}
            requests.append(mock_request)
        
        with patch.object(redis_manager, 'get_client', return_value=AsyncMock()):
            # Save all states concurrently
            save_tasks = [self.manager.save_primary_state(req) for req in requests]
            save_results = await asyncio.gather(*save_tasks)
            
            # All saves should succeed
            assert all(save_results)
            assert len(self.manager._cache) == 5
            
            # Load all states concurrently
            load_tasks = [self.manager.load_primary_state(f"run_concurrent_{i}") for i in range(5)]
            load_results = await asyncio.gather(*load_tasks)
            
            # Verify each state maintained its data
            for i, loaded_state in enumerate(load_results):
                assert loaded_state["step"] == i
                assert loaded_state["concurrent_test"] is True
                
    @pytest.mark.asyncio
    async def test_redis_fallback_behavior_maintains_functionality(self):
        """Test system maintains functionality when Redis is unavailable."""
        mock_request = Mock()
        mock_request.run_id = "run_fallback_test"
        mock_request.state_data = {"fallback": True, "redis_unavailable": True}
        
        # Simulate Redis being completely unavailable
        with patch.object(redis_manager, 'get_client', side_effect=Exception("Redis service down")):
            # Should still work with local cache
            save_result = await self.manager.save_primary_state(mock_request)
            assert save_result is True
            
            # Load should work from local cache
            load_result = await self.manager.load_primary_state("run_fallback_test")
            assert load_result["fallback"] is True
            
            # Mark completed should work
            complete_result = await self.manager.mark_state_completed("run_fallback_test")
            assert complete_result is True
            
            # Delete should work
            delete_result = await self.manager.delete_primary_state("run_fallback_test")
            assert delete_result is True