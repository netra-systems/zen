"""Integration tests for optimized state persistence."""

import pytest
from unittest.mock import patch, AsyncMock
import os

from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.services.state_persistence_optimized import OptimizedStatePersistence
from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType, AgentPhase


class TestOptimizedPersistenceIntegration:
    """Integration tests for the optimized persistence system."""

    def test_feature_flag_enabled_uses_optimized_service(self):
        """Test that enabled feature flag uses optimized service."""
        with patch.dict(os.environ, {'ENABLE_OPTIMIZED_PERSISTENCE': 'true'}):
            # Create mock dependencies
            mock_engine = AsyncMock()
            mock_websocket = AsyncMock()
            mock_session = AsyncMock()
            
            # Create pipeline executor
            executor = PipelineExecutor(mock_engine, mock_websocket, mock_session)
            
            # Verify it uses optimized service
            assert isinstance(executor.state_persistence, OptimizedStatePersistence)

    def test_feature_flag_disabled_uses_standard_service(self):
        """Test that disabled feature flag uses standard service."""
        with patch.dict(os.environ, {'ENABLE_OPTIMIZED_PERSISTENCE': 'false'}):
            # Create mock dependencies
            mock_engine = AsyncMock()
            mock_websocket = AsyncMock()
            mock_session = AsyncMock()
            
            # Create pipeline executor
            executor = PipelineExecutor(mock_engine, mock_websocket, mock_session)
            
            # Verify it uses standard service
            assert isinstance(executor.state_persistence, StatePersistenceService)

    @pytest.mark.asyncio
    async def test_optimized_service_fallback_behavior(self):
        """Test that optimized service properly falls back to standard service."""
        service = OptimizedStatePersistence()
        
        # Create test request
        request = StatePersistenceRequest(
            run_id="integration-test-123",
            user_id="test-user",
            thread_id="test-thread",
            state_data={"test": "data"},
            checkpoint_type=CheckpointType.AUTO,
            agent_phase=AgentPhase.INITIALIZATION
        )
        
        mock_session = AsyncMock()
        
        # Mock fallback service to return success
        with patch.object(service.fallback_service, 'save_agent_state', return_value=(True, "test-snapshot-id")) as mock_fallback:
            success, snapshot_id = await service.save_agent_state(request, mock_session)
            
            # Verify successful operation
            assert success is True
            assert snapshot_id == "test-snapshot-id"
            
            # Verify fallback was called (either through optimization path or direct fallback)
            assert mock_fallback.called

    @pytest.mark.asyncio
    async def test_deduplication_functionality(self):
        """Test that deduplication works correctly."""
        service = OptimizedStatePersistence()
        service.configure(enable_deduplication=True)
        
        # Create identical requests
        request1 = StatePersistenceRequest(
            run_id="dedup-test-123",
            user_id="test-user",
            thread_id="test-thread",
            state_data={"test": "data", "value": 42},
            checkpoint_type=CheckpointType.AUTO,
            agent_phase=AgentPhase.INITIALIZATION
        )
        
        request2 = StatePersistenceRequest(
            run_id="dedup-test-123",
            user_id="test-user",
            thread_id="test-thread",
            state_data={"test": "data", "value": 42},  # Identical data
            checkpoint_type=CheckpointType.AUTO,
            agent_phase=AgentPhase.INITIALIZATION
        )
        
        # First request should not be skipped
        should_skip_1 = await service._should_skip_persistence(request1)
        assert should_skip_1 is False
        
        # Second request with identical data should be skipped
        should_skip_2 = await service._should_skip_persistence(request2)
        assert should_skip_2 is True

    @pytest.mark.asyncio
    async def test_critical_checkpoint_always_persisted(self):
        """Test that critical checkpoints are always persisted."""
        service = OptimizedStatePersistence()
        
        request = StatePersistenceRequest(
            run_id="critical-test-123",
            user_id="test-user",
            thread_id="test-thread",
            state_data={"critical": "data"},
            checkpoint_type=CheckpointType.MANUAL,  # Critical checkpoint
            agent_phase=AgentPhase.COMPLETION
        )
        
        mock_session = AsyncMock()
        
        # Mock fallback service
        with patch.object(service.fallback_service, 'save_agent_state', return_value=(True, "critical-snapshot")) as mock_fallback:
            success, snapshot_id = await service.save_agent_state(request, mock_session)
            
            # Verify it went through fallback service (critical checkpoints bypass optimization)
            assert success is True
            assert snapshot_id == "critical-snapshot"
            mock_fallback.assert_called_once()

    def test_cache_eviction_with_lru(self):
        """Test cache eviction behavior."""
        service = OptimizedStatePersistence()
        service.configure(cache_max_size=3)  # Small cache for testing
        
        # Fill cache beyond capacity
        service._update_state_cache("key1", "hash1")
        service._update_state_cache("key2", "hash2")
        service._update_state_cache("key3", "hash3")
        
        assert len(service._state_cache) == 3
        
        # Add one more - should evict oldest (key1)
        service._update_state_cache("key4", "hash4")
        
        assert len(service._state_cache) == 3
        assert "key1" not in service._state_cache  # Oldest evicted
        assert "key2" in service._state_cache
        assert "key3" in service._state_cache
        assert "key4" in service._state_cache

    def test_cache_statistics(self):
        """Test cache statistics reporting."""
        service = OptimizedStatePersistence()
        service.clear_cache()  # Start fresh
        
        # Get initial stats
        stats = service.get_cache_stats()
        assert stats['cache_size'] == 0
        assert stats['deduplication_enabled'] is True
        assert stats['compression_enabled'] is True
        assert len(stats['cache_entries']) == 0
        
        # Add cache entries
        service._update_state_cache("test1", "hash1")
        service._update_state_cache("test2", "hash2")
        
        # Get updated stats
        stats = service.get_cache_stats()
        assert stats['cache_size'] == 2
        assert len(stats['cache_entries']) == 2

    def test_configuration_changes(self):
        """Test dynamic configuration changes."""
        service = OptimizedStatePersistence()
        
        # Test initial defaults
        assert service._enable_deduplication is True
        assert service._enable_compression is True
        assert service._cache_max_size == 1000
        
        # Change configuration
        service.configure(
            enable_deduplication=False,
            enable_compression=False,
            cache_max_size=500
        )
        
        # Verify changes
        assert service._enable_deduplication is False
        assert service._enable_compression is False
        assert service._cache_max_size == 500