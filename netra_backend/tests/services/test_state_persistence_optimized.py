"""Tests for optimized state persistence service."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from netra_backend.app.services.state_persistence_optimized import OptimizedStatePersistence
from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType, AgentPhase


class TestOptimizedStatePersistence:
    """Test cases for OptimizedStatePersistence."""

    @pytest.fixture
    def persistence_service(self):
        """Create test instance of optimized persistence service."""
        service = OptimizedStatePersistence()
        service.clear_cache()  # Start with clean cache
        return service

    @pytest.fixture
    def sample_persistence_request(self):
        """Create sample persistence request for testing."""
        return StatePersistenceRequest(
            run_id="test-run-123",
            user_id="test-user-456", 
            thread_id="test-thread-789",
            state_data={"key": "value", "status": "active"},
            checkpoint_type=CheckpointType.AUTO,
            agent_phase=AgentPhase.INITIALIZATION
        )

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock()

    def test_initialization(self, persistence_service):
        """Test service initializes correctly."""
        assert persistence_service.fallback_service is not None
        assert persistence_service._state_cache == {}
        assert persistence_service._cache_max_size == 1000
        assert persistence_service._enable_deduplication is True
        assert persistence_service._enable_compression is True

    def test_is_optimizable_save_auto_checkpoint(self, persistence_service, sample_persistence_request):
        """Test that AUTO checkpoints are optimizable."""
        sample_persistence_request.checkpoint_type = CheckpointType.AUTO
        assert persistence_service._is_optimizable_save(sample_persistence_request) is True

    def test_is_optimizable_save_intermediate_checkpoint(self, persistence_service, sample_persistence_request):
        """Test that INTERMEDIATE checkpoints are optimizable."""
        sample_persistence_request.checkpoint_type = CheckpointType.INTERMEDIATE
        assert persistence_service._is_optimizable_save(sample_persistence_request) is True

    def test_is_optimizable_save_manual_checkpoint(self, persistence_service, sample_persistence_request):
        """Test that MANUAL checkpoints are not optimizable (critical)."""
        sample_persistence_request.checkpoint_type = CheckpointType.MANUAL
        assert persistence_service._is_optimizable_save(sample_persistence_request) is False

    def test_calculate_state_hash_deterministic(self, persistence_service):
        """Test that state hash calculation is deterministic."""
        state_data = {"key": "value", "number": 123}
        hash1 = persistence_service._calculate_state_hash(state_data)
        hash2 = persistence_service._calculate_state_hash(state_data)
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

    def test_calculate_state_hash_different_for_different_data(self, persistence_service):
        """Test that different state data produces different hashes."""
        state_data1 = {"key": "value1"}
        state_data2 = {"key": "value2"}
        hash1 = persistence_service._calculate_state_hash(state_data1)
        hash2 = persistence_service._calculate_state_hash(state_data2)
        assert hash1 != hash2

    def test_update_state_cache(self, persistence_service):
        """Test state cache update functionality."""
        cache_key = "test-run:test-user"
        state_hash = "abcd1234"
        
        persistence_service._update_state_cache(cache_key, state_hash)
        
        assert cache_key in persistence_service._state_cache
        cache_entry = persistence_service._state_cache[cache_key]
        assert cache_entry['state_hash'] == state_hash
        assert 'snapshot_id' in cache_entry
        assert 'timestamp' in cache_entry

    @pytest.mark.asyncio
    async def test_should_skip_persistence_first_save(self, persistence_service, sample_persistence_request):
        """Test that first save is not skipped."""
        should_skip = await persistence_service._should_skip_persistence(sample_persistence_request)
        assert should_skip is False

    @pytest.mark.asyncio
    async def test_should_skip_persistence_duplicate_save(self, persistence_service, sample_persistence_request):
        """Test that duplicate save is skipped."""
        # First save - should not skip
        should_skip1 = await persistence_service._should_skip_persistence(sample_persistence_request)
        assert should_skip1 is False
        
        # Second save with same data - should skip
        should_skip2 = await persistence_service._should_skip_persistence(sample_persistence_request)
        assert should_skip2 is True

    @pytest.mark.asyncio
    async def test_should_skip_persistence_different_data(self, persistence_service, sample_persistence_request):
        """Test that save with different data is not skipped."""
        # First save
        should_skip1 = await persistence_service._should_skip_persistence(sample_persistence_request)
        assert should_skip1 is False
        
        # Modify data
        sample_persistence_request.state_data = {"key": "different_value"}
        
        # Second save with different data - should not skip
        should_skip2 = await persistence_service._should_skip_persistence(sample_persistence_request)
        assert should_skip2 is False

    @pytest.mark.asyncio
    async def test_should_skip_persistence_deduplication_disabled(self, persistence_service, sample_persistence_request):
        """Test that persistence is not skipped when deduplication is disabled."""
        persistence_service.configure(enable_deduplication=False)
        
        # Should not skip when deduplication is disabled
        result = await persistence_service._should_skip_persistence(sample_persistence_request)
        assert result is False

    def test_get_cached_snapshot_id(self, persistence_service):
        """Test getting cached snapshot ID."""
        cache_key = "test-run-123:test-user"
        state_hash = "abcd1234"
        
        persistence_service._update_state_cache(cache_key, state_hash)
        snapshot_id = persistence_service._get_cached_snapshot_id("test-run-123")
        
        assert snapshot_id is not None
        assert isinstance(snapshot_id, str)

    def test_optimize_state_data(self, persistence_service, sample_persistence_request):
        """Test state data optimization."""
        optimized_request = persistence_service._optimize_state_data(sample_persistence_request)
        
        assert optimized_request.run_id == sample_persistence_request.run_id
        assert optimized_request.state_data == sample_persistence_request.state_data
        assert optimized_request != sample_persistence_request  # Should be a new object

    @pytest.mark.asyncio
    async def test_save_agent_state_fallback_on_error(self, persistence_service, sample_persistence_request, mock_db_session):
        """Test that service falls back to standard persistence on error."""
        # Mock the optimized save to raise an error
        with patch.object(persistence_service, '_execute_optimized_save', side_effect=Exception("Test error")):
            with patch.object(persistence_service.fallback_service, 'save_agent_state', return_value=(True, "fallback-id")) as mock_fallback:
                success, snapshot_id = await persistence_service.save_agent_state(sample_persistence_request, mock_db_session)
                
                assert success is True
                assert snapshot_id == "fallback-id"
                mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_agent_state_uses_fallback(self, persistence_service, mock_db_session):
        """Test that load operations use fallback service."""
        with patch.object(persistence_service.fallback_service, 'load_agent_state', return_value=None) as mock_fallback:
            result = await persistence_service.load_agent_state("test-run", db_session=mock_db_session)
            
            assert result is None
            mock_fallback.assert_called_once_with("test-run", None, mock_db_session)

    def test_configure_deduplication(self, persistence_service):
        """Test configuring deduplication setting."""
        persistence_service.configure(enable_deduplication=False)
        assert persistence_service._enable_deduplication is False
        
        persistence_service.configure(enable_deduplication=True)
        assert persistence_service._enable_deduplication is True

    def test_configure_compression(self, persistence_service):
        """Test configuring compression setting."""
        persistence_service.configure(enable_compression=False)
        assert persistence_service._enable_compression is False
        
        persistence_service.configure(enable_compression=True)
        assert persistence_service._enable_compression is True

    def test_configure_cache_size(self, persistence_service):
        """Test configuring cache size."""
        persistence_service.configure(cache_max_size=500)
        assert persistence_service._cache_max_size == 500

    def test_get_cache_stats(self, persistence_service):
        """Test getting cache statistics."""
        stats = persistence_service.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'cache_max_size' in stats
        assert 'deduplication_enabled' in stats
        assert 'compression_enabled' in stats
        assert 'cache_entries' in stats
        assert stats['cache_size'] == 0  # Empty cache initially

    def test_clear_cache(self, persistence_service):
        """Test clearing the cache."""
        # Add something to cache
        persistence_service._update_state_cache("test:key", "hash123")
        assert len(persistence_service._state_cache) == 1
        
        # Clear cache
        persistence_service.clear_cache()
        assert len(persistence_service._state_cache) == 0

    def test_cache_eviction_when_full(self, persistence_service):
        """Test cache eviction when max size is reached."""
        # Set small cache size for testing
        persistence_service.configure(cache_max_size=2)
        
        # Fill cache to capacity
        persistence_service._update_state_cache("key1", "hash1")
        persistence_service._update_state_cache("key2", "hash2")
        assert len(persistence_service._state_cache) == 2
        
        # Add one more - should evict oldest
        persistence_service._update_state_cache("key3", "hash3")
        assert len(persistence_service._state_cache) == 2
        assert "key1" not in persistence_service._state_cache  # Oldest should be evicted
        assert "key2" in persistence_service._state_cache
        assert "key3" in persistence_service._state_cache

    @pytest.mark.asyncio
    async def test_execute_optimized_save_with_skipping(self, persistence_service, sample_persistence_request, mock_db_session):
        """Test optimized save skips redundant operations."""
        with patch.object(persistence_service, '_should_skip_persistence', return_value=True):
            with patch.object(persistence_service, '_get_cached_snapshot_id', return_value="cached-id"):
                success, snapshot_id = await persistence_service._execute_optimized_save(sample_persistence_request, mock_db_session)
                
                assert success is True
                assert snapshot_id == "cached-id"

    @pytest.mark.asyncio
    async def test_execute_optimized_save_critical_checkpoint(self, persistence_service, sample_persistence_request, mock_db_session):
        """Test that critical checkpoints use standard persistence."""
        sample_persistence_request.checkpoint_type = CheckpointType.MANUAL  # Critical checkpoint
        
        with patch.object(persistence_service.fallback_service, 'save_agent_state', return_value=(True, "standard-id")) as mock_fallback:
            success, snapshot_id = await persistence_service._execute_optimized_save(sample_persistence_request, mock_db_session)
            
            assert success is True
            assert snapshot_id == "standard-id"
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_optimized_persistence_success(self, persistence_service, sample_persistence_request, mock_db_session):
        """Test successful optimized persistence."""
        with patch.object(persistence_service, '_optimize_state_data', return_value=sample_persistence_request):
            with patch.object(persistence_service.fallback_service, 'save_agent_state', return_value=(True, "optimized-id")) as mock_fallback:
                success, snapshot_id = await persistence_service._execute_optimized_persistence(sample_persistence_request, mock_db_session)
                
                assert success is True
                assert snapshot_id == "optimized-id"
                mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_optimized_persistence_fallback_on_error(self, persistence_service, sample_persistence_request, mock_db_session):
        """Test fallback to standard persistence on optimization error."""
        with patch.object(persistence_service, '_optimize_state_data', side_effect=Exception("Optimization error")):
            with patch.object(persistence_service.fallback_service, 'save_agent_state', return_value=(True, "fallback-id")) as mock_fallback:
                success, snapshot_id = await persistence_service._execute_optimized_persistence(sample_persistence_request, mock_db_session)
                
                assert success is True
                assert snapshot_id == "fallback-id"
                # Should be called twice - once for optimization attempt, once for fallback
                assert mock_fallback.call_count == 2

    @pytest.mark.asyncio
    async def test_recover_agent_state_uses_fallback(self, persistence_service, mock_db_session):
        """Test that recovery operations use fallback service."""
        mock_request = MagicMock()
        with patch.object(persistence_service.fallback_service, 'recover_agent_state', return_value=(True, "recovery-id")) as mock_fallback:
            success, recovery_id = await persistence_service.recover_agent_state(mock_request, mock_db_session)
            
            assert success is True
            assert recovery_id == "recovery-id"
            mock_fallback.assert_called_once_with(mock_request, mock_db_session)

    @pytest.mark.asyncio
    async def test_get_thread_context_uses_fallback(self, persistence_service):
        """Test that thread context operations use fallback service."""
        with patch.object(persistence_service.fallback_service, 'get_thread_context', return_value={"context": "data"}) as mock_fallback:
            result = await persistence_service.get_thread_context("thread-123")
            
            assert result == {"context": "data"}
            mock_fallback.assert_called_once_with("thread-123")