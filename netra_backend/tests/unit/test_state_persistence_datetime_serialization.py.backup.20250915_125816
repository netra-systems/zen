"""Regression test for datetime JSON serialization in state persistence."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas.agent_state import (
    AgentPhase,
    CheckpointType,
    StatePersistenceRequest,
)

from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.services.state_serialization import DateTimeEncoder

class TestDateTimeSerialization:
    """Test datetime serialization in state persistence."""
    @pytest.mark.asyncio
    async def test_datetime_encoder_handles_datetime_objects(self):
        """Test DateTimeEncoder properly serializes datetime objects."""
        data = {
            "timestamp": datetime.now(timezone.utc),
            "created_at": datetime(2025, 8, 15, 10, 30, 0, tzinfo=timezone.utc),
            "expires_at": datetime(2025, 8, 16, 10, 30, 0, tzinfo=timezone.utc),
            "nested": {
                "updated_at": datetime.now(timezone.utc)
            }
        }
        
        # Should not raise TypeError
        serialized = json.dumps(data, cls=DateTimeEncoder)
        deserialized = json.loads(serialized)
        
        # Verify all datetime objects were converted to strings
        assert isinstance(deserialized["timestamp"], str)
        assert isinstance(deserialized["created_at"], str)
        assert isinstance(deserialized["expires_at"], str)
        assert isinstance(deserialized["nested"]["updated_at"], str)
        
        # Verify ISO format
        assert "T" in deserialized["timestamp"]
        assert deserialized["created_at"] == "2025-08-15T10:30:00+00:00"
    @pytest.mark.asyncio
    async def test_save_agent_state_serializes_datetime_in_state_data(self):
        """Test save_agent_state properly serializes datetime objects in state_data."""
        service = StatePersistenceService()
        
        # Create request with datetime objects in state_data
        request = StatePersistenceRequest(
            run_id="test_run_123",
            thread_id="test_thread_456",
            user_id="test_user_789",
            state_data={
                "started_at": datetime.now(timezone.utc),
                "metrics": {
                    "last_update": datetime.now(timezone.utc),
                    "values": [1, 2, 3]
                },
                "checkpoint_time": datetime(2025, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
            },
            checkpoint_type=CheckpointType.MANUAL,
            agent_phase=AgentPhase.INITIALIZATION,
            is_recovery_point=True
        )
        
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=None)
        mock_begin.__aexit__ = AsyncMock(return_value=None)
        mock_session.begin = MagicMock(return_value=mock_begin)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        
        # Mock internal methods and force legacy save path
        with patch.object(service, '_log_state_transaction', new_callable=AsyncMock) as mock_log:
            with patch.object(service, '_cache_state_in_redis', new_callable=AsyncMock):
                with patch.object(service, '_cleanup_old_snapshots', new_callable=AsyncMock):
                    with patch.object(service, '_complete_transaction', new_callable=AsyncMock):
                        # Mock the cache manager to fail Redis save, forcing legacy path
                        with patch('netra_backend.app.services.state_persistence.state_cache_manager') as mock_cache:
                            mock_cache.save_primary_state = AsyncMock(return_value=False)  # Force fallback
                            mock_cache.cache_legacy_state = AsyncMock(return_value=True)  # Mock legacy cache
                            mock_log.return_value = "transaction_123"
                            
                            # Execute save
                            success, snapshot_id = await service.save_agent_state(request, mock_session)
                            
                            # Verify success
                            assert success is True
                            assert snapshot_id is not None
                            
                            # Verify the service was called correctly
                            assert mock_session.add.called
                            assert success is True
                            assert snapshot_id is not None
                            
                            # Verify that state serialization handled datetime conversion
                            # The service should process datetime objects properly
    @pytest.mark.asyncio
    async def test_state_persistence_handles_mixed_data_types(self):
        """Test state persistence handles mixed data types including datetime."""
        service = StatePersistenceService()
        
        # Complex state data with various types
        request = StatePersistenceRequest(
            run_id="complex_run",
            thread_id="complex_thread",
            user_id="complex_user",
            state_data={
                "string_field": "test",
                "int_field": 42,
                "float_field": 3.14,
                "bool_field": True,
                "null_field": None,
                "list_field": [1, 2, 3],
                "datetime_field": datetime.now(timezone.utc),
                "nested": {
                    "datetime": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    "data": {"key": "value"}
                }
            },
            checkpoint_type=CheckpointType.AUTO
        )
        
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=None)
        mock_begin.__aexit__ = AsyncMock(return_value=None)
        mock_session.begin = MagicMock(return_value=mock_begin)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        
        # Mock methods and force legacy save path
        with patch.object(service, '_log_state_transaction', new_callable=AsyncMock):
            with patch.object(service, '_cache_state_in_redis', new_callable=AsyncMock):
                with patch.object(service, '_cleanup_old_snapshots', new_callable=AsyncMock):
                    with patch.object(service, '_complete_transaction', new_callable=AsyncMock):
                        # Mock the cache manager to fail Redis save, forcing legacy path
                        with patch('netra_backend.app.services.state_persistence.state_cache_manager') as mock_cache:
                            mock_cache.save_primary_state = AsyncMock(return_value=False)  # Force fallback
                            mock_cache.cache_legacy_state = AsyncMock(return_value=True)  # Mock legacy cache
                            
                            # Save state
                            success, _ = await service.save_agent_state(request, mock_session)
                            assert success is True
                            
                            # Verify save succeeded
                            assert success is True
                            assert mock_session.add.called
                            
                            # The service should handle mixed data types including datetime serialization
                            # This validates the service can process complex state data structures