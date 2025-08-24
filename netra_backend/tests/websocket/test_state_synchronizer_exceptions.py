"""WebSocket State Synchronizer Exception Handling Tests.

Tests for critical exception handling requirements from websocket_reliability.xml.
"""

import sys
from pathlib import Path

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.websocket_core.types import ConnectionInfo
from netra_backend.app.websocket_core.manager import WebSocketManager as ConnectionManager

from netra_backend.app.websocket_core.state_synchronizer import ConnectionStateSynchronizer
from netra_backend.app.websocket_core.sync_types import CriticalCallbackFailure

class TestStateSynchronizerExceptionHandling:
    """Test exception handling in state synchronizer."""
    
    async def test_critical_callback_failure_propagation(self):
        """Test that critical callback failures are properly propagated."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create a critical callback that raises ConnectionError
        async def critical_callback(conn_id, event_type):
            raise ConnectionError("Critical connection failure")
        
        # Register the critical callback
        synchronizer.register_sync_callback("test_conn", critical_callback)
        
        # This should raise CriticalCallbackFailure
        with pytest.raises(CriticalCallbackFailure) as exc_info:
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        
        assert "Critical callback failures" in str(exc_info.value)
        assert "test_conn" in str(exc_info.value)
    
    async def test_non_critical_callback_failure_handling(self):
        """Test that non-critical callback failures are handled gracefully."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create a non-critical callback that raises ValueError
        async def non_critical_callback(conn_id, event_type):
            raise ValueError("Non-critical processing error")
        
        # Register the non-critical callback
        synchronizer.register_sync_callback("test_conn", non_critical_callback)
        
        # This should NOT raise an exception (non-critical failure)
        try:
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        except CriticalCallbackFailure:
            pytest.fail("Non-critical callback failure should not propagate")
    
    async def test_mixed_callback_failures(self):
        """Test mixed critical and non-critical callback failures."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create mixed callbacks
        async def critical_callback(conn_id, event_type):
            raise TimeoutError("Critical timeout")
        
        async def non_critical_callback(conn_id, event_type):
            raise ValueError("Non-critical error")
        
        async def successful_callback(conn_id, event_type):
            return "success"
        
        # Register all callbacks
        synchronizer.register_sync_callback("test_conn", critical_callback)
        synchronizer.register_sync_callback("test_conn", non_critical_callback)
        synchronizer.register_sync_callback("test_conn", successful_callback)
        
        # Should raise due to critical failure
        with pytest.raises(CriticalCallbackFailure):
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
    
    async def test_callback_timeout_handling(self):
        """Test callback timeout handling."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create a callback that hangs
        async def hanging_callback(conn_id, event_type):
            await asyncio.sleep(10)  # Exceeds 5-second timeout
        
        synchronizer.register_sync_callback("test_conn", hanging_callback)
        
        # Should handle timeout gracefully (log warning, not critical)
        try:
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        except CriticalCallbackFailure:
            pytest.fail("Timeout should not be treated as critical failure")
    
    async def test_callback_exception_classification(self):
        """Test that exception types are correctly classified."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        handler = synchronizer._callback_handler
        
        # Test critical exceptions
        assert handler._is_critical_failure(ConnectionError("test"))
        assert handler._is_critical_failure(TimeoutError("test"))
        assert handler._is_critical_failure(CriticalCallbackFailure("test"))
        
        # Test non-critical exceptions
        assert not handler._is_critical_failure(ValueError("test"))
        assert not handler._is_critical_failure(RuntimeError("test"))
        assert not handler._is_critical_failure(KeyError("test"))
    
    async def test_successful_callback_execution(self):
        """Test that successful callbacks execute without issues."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        results = []
        
        async def successful_callback(conn_id, event_type):
            results.append(f"{conn_id}:{event_type}")
            return "success"
        
        synchronizer.register_sync_callback("test_conn", successful_callback)
        
        # Should complete successfully
        await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        assert results == ["test_conn:state_desync"]
    
    async def test_no_callbacks_registered(self):
        """Test behavior when no callbacks are registered."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Should complete successfully with no callbacks
        await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
    
    async def test_sync_callback_task_creation_failure(self):
        """Test handling of task creation failures."""
        connection_manager = MagicMock()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create a callback that's neither async nor sync callable
        invalid_callback = "not_a_function"
        
        handler = synchronizer._callback_handler
        
        # Should handle task creation error gracefully
        result = await handler._process_single_callback(
            invalid_callback, "test_conn", "state_desync"
        )
        assert result is None  # Failed task creation returns None

class TestCallbackHandlerDirectly:
    """Test callback handler functionality directly."""
    
    async def test_explicit_exception_inspection(self):
        """Test explicit exception inspection per specification."""
        from netra_backend.app.websocket_core.callback_handler import CallbackHandler
        
        handler = CallbackHandler()
        
        # Simulate gather results with mixed success/failure
        results = [
            "success_result_1",
            ConnectionError("critical_error"),
            "success_result_2",
            ValueError("non_critical_error"),
            TimeoutError("another_critical_error")
        ]
        
        # Should raise CriticalCallbackFailure due to critical exceptions
        with pytest.raises(CriticalCallbackFailure) as exc_info:
            await handler._inspect_callback_results(results, "test_conn")
        
        assert "2 failures" in str(exc_info.value)  # Two critical failures
    
    async def test_no_exceptions_in_results(self):
        """Test behavior when no exceptions are in results."""
        from netra_backend.app.websocket_core.callback_handler import CallbackHandler
        
        handler = CallbackHandler()
        
        results = ["success_1", "success_2", "success_3"]
        
        # Should complete without raising
        await handler._inspect_callback_results(results, "test_conn")
    
    async def test_only_non_critical_exceptions(self):
        """Test behavior with only non-critical exceptions."""
        from netra_backend.app.websocket_core.callback_handler import CallbackHandler
        
        handler = CallbackHandler()
        
        results = [ValueError("error_1"), RuntimeError("error_2")]
        
        # Should NOT raise CriticalCallbackFailure
        try:
            await handler._inspect_callback_results(results, "test_conn")
        except CriticalCallbackFailure:
            pytest.fail("Non-critical exceptions should not raise CriticalCallbackFailure")