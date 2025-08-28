"""Tests for Optimized State Persistence Service

Comprehensive tests covering:
- State diffing logic
- Selective persistence behavior  
- Performance monitoring
- Feature flag control
- Fallback mechanisms
- Connection pool optimization
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent_state import CheckpointType, StatePersistenceRequest
from netra_backend.app.services.state_persistence_optimized import (
    OptimizedStatePersistence,
    StateDiffer,
    PerformanceMonitor
)


class TestStateDiffer:
    """Test state diffing functionality."""
    
    def test_first_state_always_persisted(self):
        """First state for a run_id should always be persisted."""
        differ = StateDiffer()
        state_data = {"key1": "value1", "key2": {"nested": "data"}}
        
        result = differ.has_meaningful_changes("run_1", state_data)
        assert result is True
    
    def test_identical_state_skipped(self):
        """Identical state should be skipped."""
        differ = StateDiffer()
        state_data = {"key1": "value1", "key2": {"nested": "data"}}
        
        # First call should return True
        assert differ.has_meaningful_changes("run_1", state_data) is True
        
        # Second call with same data should return False
        assert differ.has_meaningful_changes("run_1", state_data) is False
    
    def test_meaningful_changes_detected(self):
        """Meaningful changes should be detected."""
        differ = StateDiffer()
        initial_state = {"key1": "value1", "key2": {"nested": "data"}}
        changed_state = {"key1": "value2", "key2": {"nested": "data"}}
        
        # First call
        assert differ.has_meaningful_changes("run_1", initial_state) is True
        
        # Changed state should be detected
        assert differ.has_meaningful_changes("run_1", changed_state) is True
    
    def test_trivial_fields_ignored(self):
        """Trivial fields should be ignored in change detection."""
        differ = StateDiffer()
        initial_state = {"key1": "value1", "timestamp": "2023-01-01"}
        changed_state = {"key1": "value1", "timestamp": "2023-01-02"}
        
        # First call
        assert differ.has_meaningful_changes("run_1", initial_state) is True
        
        # Only trivial field changed - should be skipped
        assert differ.has_meaningful_changes("run_1", changed_state) is False
    
    def test_changed_fields_detection(self):
        """Should correctly identify which fields changed."""
        differ = StateDiffer()
        old_data = {"key1": "value1", "key2": "value2", "timestamp": "old"}
        new_data = {"key1": "changed", "key2": "value2", "timestamp": "new"}
        
        changed_fields = differ.get_changed_fields(old_data, new_data)
        assert changed_fields == {"key1"}  # timestamp excluded as trivial


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor for testing."""
        monitor = PerformanceMonitor()
        monitor._enabled = True
        return monitor
    
    def test_monitoring_disabled_by_default(self):
        """Monitoring should be disabled by default in tests."""
        with patch.dict('os.environ', {'OPTIMIZED_PERSISTENCE_MONITORING': 'false'}):
            monitor = PerformanceMonitor()
            assert monitor._enabled is False
    
    def test_metrics_recording(self, monitor):
        """Should record metrics when enabled."""
        monitor.record_persistence_metrics(
            "run_1", "optimized_save", 50.0, True, 3
        )
        
        # Queue should have one item
        assert monitor._metrics_queue.qsize() == 1
    
    def test_queue_full_handling(self, monitor):
        """Should handle queue full gracefully."""
        # Fill the queue beyond capacity
        for i in range(1001):  # Queue maxsize is 1000
            monitor.record_persistence_metrics(f"run_{i}", "test", 1.0, True, 1)
        
        # Should not raise exception
        assert monitor._metrics_queue.qsize() <= 1000
    
    @pytest.mark.asyncio
    async def test_monitoring_task_lifecycle(self, monitor):
        """Test monitoring task start/stop lifecycle."""
        monitor.start_monitoring()
        assert monitor._monitoring_task is not None
        assert not monitor._monitoring_task.done()
        
        monitor.stop_monitoring()
        await asyncio.sleep(0.1)  # Allow task to complete
        assert monitor._monitoring_task.cancelled()


class TestOptimizedStatePersistence:
    """Test optimized state persistence functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample persistence request."""
        return StatePersistenceRequest(
            run_id="test_run_1",
            thread_id="thread_1", 
            user_id="user_1",
            state_data={"key1": "value1", "data": {"nested": "info"}},
            checkpoint_type=CheckpointType.AUTO,
            is_recovery_point=False
        )
    
    @pytest.fixture
    def optimized_service(self):
        """Create optimized persistence service."""
        service = OptimizedStatePersistence()
        service.enabled = True  # Enable for testing
        return service
    
    def test_disabled_fallback(self, mock_db_session, sample_request):
        """When disabled, should fall back to standard service."""
        service = OptimizedStatePersistence()
        service.enabled = False
        
        with patch.object(service._fallback_service, 'save_agent_state') as mock_save:
            mock_save.return_value = (True, "snapshot_1")
            
            # Should call fallback service
            result = asyncio.run(service.save_agent_state(sample_request, mock_db_session))
            assert result == (True, "snapshot_1")
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_recovery_point_always_persisted(self, optimized_service, mock_db_session):
        """Recovery points should always be persisted."""
        request = StatePersistenceRequest(
            run_id="test_run_1",
            thread_id="thread_1",
            user_id="user_1", 
            state_data={"key1": "value1"},
            checkpoint_type=CheckpointType.AUTO,
            is_recovery_point=True
        )
        
        with patch.object(optimized_service._fallback_service, 'save_agent_state') as mock_save:
            mock_save.return_value = (True, "snapshot_1")
            
            result = await optimized_service.save_agent_state(request, mock_db_session)
            assert result == (True, "snapshot_1")
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manual_checkpoint_always_persisted(self, optimized_service, mock_db_session):
        """Manual checkpoints should always be persisted."""
        request = StatePersistenceRequest(
            run_id="test_run_1",
            thread_id="thread_1", 
            user_id="user_1",
            state_data={"key1": "value1"},
            checkpoint_type=CheckpointType.MANUAL,
            is_recovery_point=False
        )
        
        with patch.object(optimized_service._fallback_service, 'save_agent_state') as mock_save:
            mock_save.return_value = (True, "snapshot_1")
            
            result = await optimized_service.save_agent_state(request, mock_db_session)
            assert result == (True, "snapshot_1")
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_changes_skipped(self, optimized_service, mock_db_session, sample_request):
        """States with no meaningful changes should be skipped."""
        # First save should proceed
        with patch.object(optimized_service._fallback_service, 'save_agent_state') as mock_save:
            mock_save.return_value = (True, "snapshot_1")
            
            result1 = await optimized_service.save_agent_state(sample_request, mock_db_session)
            assert result1 == (True, "snapshot_1")
            assert mock_save.call_count == 1
        
        # Second save with same data should be skipped
        with patch.object(optimized_service._fallback_service, 'save_agent_state') as mock_save:
            result2 = await optimized_service.save_agent_state(sample_request, mock_db_session)
            assert result2 == (True, "skipped_no_changes")
            mock_save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fallback_on_error(self, optimized_service, mock_db_session, sample_request):
        """Should fallback to standard service on error."""
        with patch.object(optimized_service, '_should_persist_state', side_effect=Exception("Test error")):
            with patch.object(optimized_service._fallback_service, 'save_agent_state') as mock_save:
                mock_save.return_value = (True, "snapshot_1")
                
                result = await optimized_service.save_agent_state(sample_request, mock_db_session)
                assert result == (True, "snapshot_1")
                mock_save.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_metrics_recorded_on_success(self, optimized_service, mock_db_session, sample_request):
        """Success metrics should be recorded."""
        with patch.object(optimized_service._fallback_service, 'save_agent_state') as mock_save:
            mock_save.return_value = (True, "snapshot_1")
            
            with patch.object(optimized_service.performance_monitor, 'record_persistence_metrics') as mock_metrics:
                await optimized_service.save_agent_state(sample_request, mock_db_session)
                
                # Should record success metrics
                mock_metrics.assert_called()
                args = mock_metrics.call_args[0]
                assert args[0] == "test_run_1"  # run_id
                assert args[1] == "optimized_save"  # operation_type
                assert args[3] is True  # success
    
    @pytest.mark.asyncio
    async def test_load_delegates_to_standard_service(self, optimized_service):
        """Load operations should delegate to standard service."""
        with patch.object(optimized_service._fallback_service, 'load_agent_state') as mock_load:
            mock_state = DeepAgentState(run_id="test_run_1")
            mock_load.return_value = mock_state
            
            result = await optimized_service.load_agent_state("test_run_1")
            assert result == mock_state
            mock_load.assert_called_once_with("test_run_1", None, None)
    
    def test_cleanup(self, optimized_service):
        """Cleanup should stop monitoring and clear state."""
        optimized_service.performance_monitor.start_monitoring()
        optimized_service.state_differ._state_hashes["test"] = "hash"
        
        optimized_service.cleanup()
        
        assert len(optimized_service.state_differ._state_hashes) == 0


@pytest.mark.integration
class TestOptimizedPersistenceIntegration:
    """Integration tests for optimized persistence."""
    
    @pytest.mark.asyncio
    async def test_database_pool_optimization(self):
        """Test that optimized persistence affects database pool configuration."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Test with optimization disabled
        with patch.dict('os.environ', {'ENABLE_OPTIMIZED_PERSISTENCE': 'false'}):
            config = DatabaseManager._get_optimized_pool_config()
            assert config["pool_size"] == 10
            assert config["max_overflow"] == 15
        
        # Test with optimization enabled
        with patch.dict('os.environ', {'ENABLE_OPTIMIZED_PERSISTENCE': 'true'}):
            config = DatabaseManager._get_optimized_pool_config()
            assert config["pool_size"] == 15
            assert config["max_overflow"] == 25
    
    @pytest.mark.asyncio
    async def test_feature_flag_integration(self):
        """Test feature flag integration with pipeline executor."""
        from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
        
        # Mock dependencies
        mock_engine = Mock()
        mock_websocket = Mock()
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Test with optimization disabled
        with patch.dict('os.environ', {'ENABLE_OPTIMIZED_PERSISTENCE': 'false'}):
            executor = PipelineExecutor(mock_engine, mock_websocket, mock_session)
            assert executor.state_persistence.__class__.__name__ == "StatePersistenceService"
        
        # Test with optimization enabled  
        with patch.dict('os.environ', {'ENABLE_OPTIMIZED_PERSISTENCE': 'true'}):
            executor = PipelineExecutor(mock_engine, mock_websocket, mock_session)
            assert executor.state_persistence.__class__.__name__ == "OptimizedStatePersistence"


@pytest.mark.performance
class TestOptimizedPersistencePerformance:
    """Performance tests for optimized persistence."""
    
    @pytest.mark.asyncio
    async def test_skip_performance(self):
        """Test that skipped saves are fast."""
        import time
        
        service = OptimizedStatePersistence()
        service.enabled = True
        
        request = StatePersistenceRequest(
            run_id="perf_test",
            thread_id="thread_1",
            user_id="user_1", 
            state_data={"key": "value"},
            checkpoint_type=CheckpointType.AUTO,
            is_recovery_point=False
        )
        
        mock_session = AsyncMock(spec=AsyncSession)
        
        # First save to establish baseline
        with patch.object(service._fallback_service, 'save_agent_state') as mock_save:
            mock_save.return_value = (True, "snapshot_1")
            await service.save_agent_state(request, mock_session)
        
        # Second save should be fast (skipped)
        start_time = time.time()
        result = await service.save_agent_state(request, mock_session)
        duration = time.time() - start_time
        
        assert result == (True, "skipped_no_changes")
        assert duration < 0.001  # Should be very fast
    
    @pytest.mark.asyncio
    async def test_state_differ_performance(self):
        """Test state differ performance with large states."""
        import time
        
        differ = StateDiffer()
        
        # Create large state data
        large_state = {f"key_{i}": f"value_{i}" for i in range(1000)}
        large_state["nested"] = {f"nested_key_{i}": f"nested_value_{i}" for i in range(500)}
        
        # Time the hashing operation
        start_time = time.time()
        result1 = differ.has_meaningful_changes("large_run", large_state)
        first_duration = time.time() - start_time
        
        start_time = time.time()  
        result2 = differ.has_meaningful_changes("large_run", large_state)
        second_duration = time.time() - start_time
        
        assert result1 is True  # First time should persist
        assert result2 is False  # Second time should skip
        assert first_duration < 0.01  # Should be reasonably fast
        assert second_duration < 0.01  # Should be reasonably fast