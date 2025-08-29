"""Unit tests for WebSocket run_id handling and message routing."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.synthetic_data_progress_tracker import (
    SyntheticDataProgressTracker
)
from netra_backend.app.schemas.generation import GenerationStatus


class TestWebSocketManagerRunIdHandling:
    """Test WebSocket manager's handling of different ID types."""

    @pytest.fixture
    def manager(self):
        """Create WebSocket manager instance."""
        return WebSocketManager()

    @pytest.fixture
    def mock_logger(self):
        """Mock logger to verify logging behavior."""
        with patch('netra_backend.app.websocket_core.manager.logger') as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_run_id_uses_debug_logging(self, manager, mock_logger):
        """Test that run_ids use debug level logging, not warning."""
        # Test with run_id
        run_id = "run_aaf85d95-ca66-4b0d-875e-f29d36151e27"
        result = await manager.send_to_user(run_id, {"test": "message"})
        
        # Should return False (no connection)
        assert result is False
        
        # Should use debug, not warning
        mock_logger.debug.assert_called()
        assert any("run ID" in str(call) for call in mock_logger.debug.call_args_list)
        
        # Should NOT use warning for run_id
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                        if run_id in str(call)]
        assert len(warning_calls) == 0

    @pytest.mark.asyncio
    async def test_user_id_uses_warning_logging(self, manager, mock_logger):
        """Test that real user_ids use warning level logging."""
        # Test with user_id
        user_id = "user_123"
        result = await manager.send_to_user(user_id, {"test": "message"})
        
        # Should return False (no connection)
        assert result is False
        
        # Should use warning for real user
        mock_logger.warning.assert_called()
        assert any(user_id in str(call) for call in mock_logger.warning.call_args_list)

    @pytest.mark.asyncio
    async def test_id_type_detection(self, manager):
        """Test detection of different ID types."""
        test_cases = [
            ("run_123", True),  # run_id
            ("run_aaf85d95", True),  # run_id
            ("user_123", False),  # user_id
            ("dev-temp-test", False),  # user_id
            ("thread_456", False),  # not a run_id
        ]
        
        for test_id, is_run_id in test_cases:
            # The actual check is in the send_to_user method
            with patch('netra_backend.app.websocket_core.manager.logger') as mock_logger:
                await manager.send_to_user(test_id, {"test": "message"})
                
                if is_run_id:
                    # Should use debug for run_ids
                    assert any("run ID" in str(call) 
                             for call in mock_logger.debug.call_args_list)
                else:
                    # Should use warning for other IDs
                    assert any("No connections found" in str(call) 
                             for call in mock_logger.warning.call_args_list)

    @pytest.mark.asyncio
    async def test_send_to_thread_behavior(self, manager, mock_logger):
        """Test thread-based messaging behavior."""
        thread_id = "thread_789"
        result = await manager.send_to_thread(thread_id, {"test": "message"})
        
        # Should return False (no connections)
        assert result is False
        
        # Should log warning for missing thread connections
        mock_logger.warning.assert_called()
        assert any("No active connections" in str(call) 
                  for call in mock_logger.warning.call_args_list)


class TestSyntheticDataProgressTracker:
    """Test progress tracker's WebSocket routing."""

    @pytest.fixture
    def tracker(self):
        """Create progress tracker instance."""
        return SyntheticDataProgressTracker()

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        manager = AsyncMock()
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.send_to_user = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def sample_status(self):
        """Create sample generation status."""
        return GenerationStatus(
            status="generating",
            total_records=1000,
            records_generated=500,
            progress_percentage=50.0
        )

    @pytest.mark.asyncio
    async def test_prefers_thread_over_user(self, tracker, mock_websocket_manager, sample_status):
        """Test that thread_id is preferred over user_id."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager', 
                  return_value=mock_websocket_manager):
            await tracker.send_progress_update(
                run_id="run_123",
                status=sample_status,
                thread_id="thread_456",
                user_id="user_789"
            )
            
            # Should call send_to_thread, not send_to_user
            mock_websocket_manager.send_to_thread.assert_called_once()
            mock_websocket_manager.send_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_user_when_no_thread(self, tracker, mock_websocket_manager, sample_status):
        """Test that user_id is used when thread_id is not available."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager', 
                  return_value=mock_websocket_manager):
            await tracker.send_progress_update(
                run_id="run_123",
                status=sample_status,
                thread_id=None,
                user_id="user_789"
            )
            
            # Should call send_to_user
            mock_websocket_manager.send_to_user.assert_called_once()
            mock_websocket_manager.send_to_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_run_id_as_user(self, tracker, mock_websocket_manager, sample_status):
        """Test that run_ids are not used as user_ids."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager', 
                  return_value=mock_websocket_manager):
            with patch('netra_backend.app.agents.synthetic_data_progress_tracker.logger') as mock_logger:
                await tracker.send_progress_update(
                    run_id="run_123",
                    status=sample_status,
                    thread_id=None,
                    user_id="run_456"  # run_id used as user_id
                )
                
                # Should NOT call either send method
                mock_websocket_manager.send_to_thread.assert_not_called()
                mock_websocket_manager.send_to_user.assert_not_called()
                
                # Should log debug message
                mock_logger.debug.assert_called()
                assert any("No valid recipient" in str(call) 
                          for call in mock_logger.debug.call_args_list)

    @pytest.mark.asyncio
    async def test_handles_no_recipient_gracefully(self, tracker, sample_status):
        """Test graceful handling when no valid recipient is available."""
        with patch('netra_backend.app.agents.synthetic_data_progress_tracker.logger') as mock_logger:
            # Mock get_websocket_manager to return a mock
            mock_manager = AsyncMock()
            with patch('netra_backend.app.websocket_core.get_websocket_manager', 
                      return_value=mock_manager):
                await tracker.send_progress_update(
                    run_id="run_123",
                    status=sample_status,
                    thread_id=None,
                    user_id=None
                )
                
                # Should log debug message about no recipient
                mock_logger.debug.assert_called()
                assert any("No valid recipient" in str(call) 
                          for call in mock_logger.debug.call_args_list)

    @pytest.mark.asyncio
    async def test_handle_progress_update_conditional(self, tracker, sample_status):
        """Test that progress updates are sent conditionally based on batch position."""
        with patch.object(tracker, 'send_progress_update', new_callable=AsyncMock) as mock_send:
            # Should send update (0 % (1000 * 5) == 0)
            await tracker.handle_progress_update(
                run_id="run_123",
                status=sample_status,
                stream_updates=True,
                batch_start=0,
                batch_size=1000
            )
            mock_send.assert_called_once()
            
            # Reset mock
            mock_send.reset_mock()
            
            # Should NOT send update (1000 % 5000 != 0)
            await tracker.handle_progress_update(
                run_id="run_123",
                status=sample_status,
                stream_updates=True,
                batch_start=1000,
                batch_size=1000
            )
            mock_send.assert_not_called()
            
            # Reset mock
            mock_send.reset_mock()
            
            # Should send update (5000 % 5000 == 0)
            await tracker.handle_progress_update(
                run_id="run_123",
                status=sample_status,
                stream_updates=True,
                batch_start=5000,
                batch_size=1000
            )
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_import_error_handling(self, tracker, sample_status):
        """Test handling of WebSocket manager import errors."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager', 
                  side_effect=ImportError("Module not found")):
            with patch('netra_backend.app.agents.synthetic_data_progress_tracker.logger') as mock_logger:
                # Should not raise, just log
                await tracker.send_progress_update(
                    run_id="run_123",
                    status=sample_status,
                    thread_id="thread_456"
                )
                
                # Should log about unavailability
                mock_logger.debug.assert_called()
                assert any("not available" in str(call) 
                          for call in mock_logger.debug.call_args_list)


class TestWebSocketMessageContent:
    """Test WebSocket message content and structure."""

    @pytest.fixture
    def tracker(self):
        """Create progress tracker instance."""
        return SyntheticDataProgressTracker()

    def test_progress_message_structure(self, tracker):
        """Test the structure of progress messages."""
        status = GenerationStatus(
            status="generating",
            total_records=1000,
            records_generated=500,
            progress_percentage=50.0,
            table_name="synthetic_data_20250829"
        )
        
        message = tracker.create_progress_message(status)
        
        assert message["type"] == "synthetic_data_progress"
        assert "data" in message
        
        data = message["data"]
        assert data["status"] == "generating"
        assert data["records_generated"] == 500
        assert data["total_records"] == 1000
        assert data["progress_percentage"] == 50.0
        assert data["table_name"] == "synthetic_data_20250829"

    def test_progress_update_logic(self, tracker):
        """Test progress percentage calculation."""
        status = GenerationStatus(
            status="generating",
            total_records=1000
        )
        
        # Update progress
        tracker.update_progress(status, 250, 1000)
        assert status.records_generated == 250
        assert status.progress_percentage == 25.0
        
        # Update again
        tracker.update_progress(status, 750, 1000)
        assert status.records_generated == 750
        assert status.progress_percentage == 75.0
        
        # Complete
        tracker.update_progress(status, 1000, 1000)
        assert status.records_generated == 1000
        assert status.progress_percentage == 100.0

    def test_finalize_generation(self, tracker):
        """Test generation finalization."""
        status = GenerationStatus(
            status="generating",
            total_records=1000,
            records_generated=950,
            progress_percentage=95.0
        )
        
        tracker.finalize_generation(status)
        
        assert status.status == "completed"
        assert status.progress_percentage == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])