"""
Test Thread Detection Fix - Prevent False Error Messages

CRITICAL: This test validates the P0 bug fix for test thread detection
that prevents "Cannot deliver message" errors during startup health checks.

Business Value: Prevents false alarms during system health checks that
could cause unnecessary debugging and deployment delays.

Test Coverage:
1. WebSocket manager correctly identifies test threads
2. Test threads return success without triggering errors  
3. Real threads still work normally
4. Event monitor skips test threads appropriately
5. No false "Cannot deliver message" errors are logged
"""

import asyncio
import logging
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

# Set up logger for this test
logger = central_logger.get_logger(__name__)


class TestThreadDetectionFix:
    """Test suite for test thread detection bug fix."""

    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager instance for testing."""
        return WebSocketManager()
    
    @pytest.fixture  
    def event_monitor(self):
        """Create event monitor instance for testing."""
        return ChatEventMonitor()

    def test_is_test_thread_detection(self, websocket_manager):
        """Test that _is_test_thread correctly identifies test threads."""
        # Test thread patterns that should be detected
        test_thread_ids = [
            "startup_test_12345",
            "health_check_67890", 
            "test_abc123",
            "unit_test_something",
            "integration_test_xyz",
            "validation_check_456",
            "mock_thread_789"
        ]
        
        for thread_id in test_thread_ids:
            assert websocket_manager._is_test_thread(thread_id), \
                f"Failed to detect test thread: {thread_id}"
            
        # Real thread patterns that should NOT be detected as test threads
        real_thread_ids = [
            "chat_thread_12345",
            "user_session_67890",
            "agent_execution_abc123",
            "normal_thread",
            "production_thread_456"
        ]
        
        for thread_id in real_thread_ids:
            assert not websocket_manager._is_test_thread(thread_id), \
                f"Incorrectly detected real thread as test: {thread_id}"

    def test_non_string_thread_id_handling(self, websocket_manager):
        """Test that non-string thread IDs are handled safely."""
        non_string_ids = [None, 123, [], {}, object()]
        
        for thread_id in non_string_ids:
            # Should not crash and should return False
            assert not websocket_manager._is_test_thread(thread_id), \
                f"Non-string thread ID not handled safely: {thread_id}"

    @pytest.mark.asyncio
    async def test_send_to_thread_test_thread_handling(self, websocket_manager):
        """Test that send_to_thread gracefully handles test threads."""
        test_thread_id = "startup_test_12345" 
        test_message = {"type": "test_message", "data": "test"}
        
        # Mock the logger to capture debug messages
        with patch('netra_backend.app.websocket_core.manager.logger') as mock_logger:
            # Send message to test thread
            result = await websocket_manager.send_to_thread(test_thread_id, test_message)
            
            # Should return True (success) for test threads
            assert result is True, "Test thread message delivery should return success"
            
            # Should log debug message about skipping test thread
            mock_logger.debug.assert_called_with(f"Skipping message delivery for test thread: {test_thread_id}")
            
            # Should NOT log error messages
            assert not mock_logger.error.called, "Should not log errors for test threads"
            assert not mock_logger.warning.called, "Should not log warnings for test threads"

    @pytest.mark.asyncio 
    async def test_real_thread_normal_processing(self, websocket_manager):
        """Test that real threads still go through normal processing."""
        real_thread_id = "chat_thread_12345"
        test_message = {"type": "test_message", "data": "test"}
        
        # Mock _get_thread_connections to simulate no connections (normal failure case)
        with patch.object(websocket_manager, '_get_thread_connections', return_value=[]):
            with patch('netra_backend.app.websocket_core.manager.logger') as mock_logger:
                # Send message to real thread
                result = await websocket_manager.send_to_thread(real_thread_id, test_message)
                
                # Should go through normal processing (may succeed or fail depending on connections)
                # But should NOT skip with debug message
                debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list if call[0]]
                skip_messages = [msg for msg in debug_calls if "Skipping message delivery for test thread" in msg]
                assert not skip_messages, "Real thread should not be skipped as test thread"

    @pytest.mark.asyncio
    async def test_event_monitor_test_thread_handling(self, event_monitor):
        """Test that event monitor skips test threads."""
        test_thread_id = "health_check_67890"
        
        # Mock the logger to capture debug messages  
        with patch('netra_backend.app.websocket_core.event_monitor.logger') as mock_logger:
            # Record event for test thread
            await event_monitor.record_event("agent_started", test_thread_id)
            
            # Should log debug message about skipping test thread
            mock_logger.debug.assert_called_with(f"Skipping event monitoring for test thread: {test_thread_id}")
            
            # Test thread should not be tracked in internal state
            assert test_thread_id not in event_monitor.thread_start_time, \
                "Test thread should not be tracked in monitor state"
            assert test_thread_id not in event_monitor.event_counts, \
                "Test thread events should not be counted"

    def test_event_monitor_test_thread_status(self, event_monitor):
        """Test that event monitor returns special status for test threads."""
        test_thread_id = "validation_check_123"
        
        status = event_monitor.get_thread_status(test_thread_id)
        
        assert status["status"] == "test_thread", "Test thread should have special status"
        assert status["thread_id"] == test_thread_id, "Should return correct thread ID"
        assert "Test thread - not monitored" in status["message"], "Should explain why not monitored"

    @pytest.mark.asyncio
    async def test_no_false_error_logging_integration(self):
        """Integration test ensuring no false errors are logged for test threads."""
        # Create real instances
        websocket_manager = WebSocketManager()
        event_monitor = ChatEventMonitor()
        
        test_thread_patterns = [
            "startup_test_integration",
            "health_check_integration", 
            "test_integration_123"
        ]
        
        # Capture all log messages
        captured_logs = []
        
        class LogCapture(logging.Handler):
            def emit(self, record):
                captured_logs.append(record.getMessage())
        
        log_capture = LogCapture()
        
        # Add handler to both loggers
        ws_logger = central_logger.get_logger('netra_backend.app.websocket_core.manager')
        event_logger = central_logger.get_logger('netra_backend.app.websocket_core.event_monitor')
        
        ws_logger.addHandler(log_capture)
        event_logger.addHandler(log_capture)
        
        try:
            # Test WebSocket manager with test threads
            for thread_id in test_thread_patterns:
                result = await websocket_manager.send_to_thread(thread_id, {"type": "test"})
                assert result is True, f"Test thread {thread_id} should return success"
                
                # Test event monitor with test threads
                await event_monitor.record_event("agent_started", thread_id)
            
            # Verify no error/warning messages about "Cannot deliver message"
            error_messages = [msg for msg in captured_logs if "ERROR" in msg or "CRITICAL" in msg]
            delivery_errors = [msg for msg in error_messages if "Cannot deliver message" in msg]
            
            assert not delivery_errors, f"Found false delivery errors: {delivery_errors}"
            
            # Verify we do have debug messages showing test threads were skipped
            debug_messages = [msg for msg in captured_logs if "Skipping" in msg and "test thread" in msg]
            assert len(debug_messages) >= len(test_thread_patterns), \
                "Should have debug messages for skipped test threads"
                
        finally:
            # Clean up handlers
            ws_logger.removeHandler(log_capture)
            event_logger.removeHandler(log_capture)

    @pytest.mark.asyncio
    async def test_comprehensive_test_thread_patterns(self, websocket_manager, event_monitor):
        """Test comprehensive coverage of test thread patterns from implementation plan."""
        # Test patterns from STAGING_STARTUP_FIXES_IMPLEMENTATION_PLAN.md
        comprehensive_patterns = [
            "startup_test_12345",      # Startup health checks
            "health_check_67890",      # Health validation  
            "test_unit_abc123",        # Unit tests
            "test_integration_def456", # Integration tests
            "unit_test_ghi789",        # Unit test variations
            "integration_test_jkl012", # Integration test variations
            "validation_mno345",       # System validation
            "mock_pqr678"             # Mock threads
        ]
        
        for pattern in comprehensive_patterns:
            # Test WebSocket manager detection
            assert websocket_manager._is_test_thread(pattern), \
                f"WebSocket manager should detect test thread: {pattern}"
            
            # Test event monitor detection  
            assert event_monitor._is_test_thread(pattern), \
                f"Event monitor should detect test thread: {pattern}"
            
            # Test WebSocket manager handling
            result = await websocket_manager.send_to_thread(pattern, {"test": "data"})
            assert result is True, f"WebSocket manager should handle test thread gracefully: {pattern}"
            
            # Test event monitor handling (should not track)
            await event_monitor.record_event("test_event", pattern)
            assert pattern not in event_monitor.thread_start_time, \
                f"Event monitor should not track test thread: {pattern}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
