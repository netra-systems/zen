"""WebSocket State Synchronizer Exception Handling Tests.

Tests for critical exception handling requirements from websocket_reliability.xml.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
from unittest.mock import MagicMock, AsyncMock, Mock, patch

import pytest

from netra_backend.app.websocket_core.types import ConnectionInfo
from netra_backend.app.websocket_core import WebSocketManager as ConnectionManager

from netra_backend.app.websocket_core.state_synchronizer import ConnectionStateSynchronizer
from netra_backend.app.websocket_core.sync_types import CriticalCallbackFailure

class TestStateSynchronizerExceptionHandling:
    """Test exception handling in state synchronizer."""
    
    @pytest.mark.asyncio
    async def test_critical_callback_failure_propagation(self):
        """Test that critical callback failures are properly propagated."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
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
    
    @pytest.mark.asyncio
    async def test_non_critical_callback_failure_handling(self):
        """Test that non-critical callback failures are handled gracefully."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
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
    
    @pytest.mark.asyncio
    async def test_mixed_callback_failures(self):
        """Test mixed critical and non-critical callback failures."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
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
    
    @pytest.mark.asyncio
    async def test_callback_timeout_handling(self):
        """Test callback timeout handling."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
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
    
    @pytest.mark.asyncio
    async def test_callback_exception_classification(self):
        """Test that exception types are correctly classified."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Test critical exceptions
        assert synchronizer._is_critical_failure(ConnectionError("test"))
        assert synchronizer._is_critical_failure(TimeoutError("test"))
        assert synchronizer._is_critical_failure(CriticalCallbackFailure("test"))
        
        # Test non-critical exceptions
        assert not synchronizer._is_critical_failure(ValueError("test"))
        assert not synchronizer._is_critical_failure(RuntimeError("test"))
        assert not synchronizer._is_critical_failure(KeyError("test"))
    
    @pytest.mark.asyncio
    async def test_successful_callback_execution(self):
        """Test that successful callbacks execute without issues."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        results = []
        
        async def successful_callback(conn_id, event_type):
            results.append(f"{conn_id}:{event_type}")
            return "success"
        
        synchronizer.register_sync_callback("test_conn", successful_callback)
        
        # Should complete successfully
        await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        assert results == ["test_conn:state_desync"]
    
    @pytest.mark.asyncio
    async def test_no_callbacks_registered(self):
        """Test behavior when no callbacks are registered."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Should complete successfully with no callbacks
        await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
    
    @pytest.mark.asyncio
    async def test_sync_callback_task_creation_failure(self):
        """Test handling of task creation failures."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create a callback that's neither async nor sync callable
        invalid_callback = "not_a_function"
        
        # Register the invalid callback
        synchronizer.register_sync_callback("test_conn", invalid_callback)
        
        # Should handle invalid callback gracefully (logs warning, doesn't raise)
        try:
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        except Exception as e:
            pytest.fail(f"Invalid callback should be handled gracefully, but raised: {e}")

class TestStateSynchronizerExceptionClassification:
    """Test exception classification functionality directly."""
    
    @pytest.mark.asyncio
    async def test_explicit_exception_classification(self):
        """Test explicit exception classification per specification."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        # Create callbacks that raise different types of exceptions
        async def critical_callback_1(conn_id, event_type):
            raise ConnectionError("critical_error")
        
        async def critical_callback_2(conn_id, event_type):
            raise TimeoutError("another_critical_error")
        
        async def non_critical_callback(conn_id, event_type):
            raise ValueError("non_critical_error")
        
        async def successful_callback(conn_id, event_type):
            return "success_result"
        
        # Register all callbacks
        synchronizer.register_sync_callback("test_conn", critical_callback_1)
        synchronizer.register_sync_callback("test_conn", critical_callback_2)
        synchronizer.register_sync_callback("test_conn", non_critical_callback)
        synchronizer.register_sync_callback("test_conn", successful_callback)
        
        # Should raise CriticalCallbackFailure due to critical exceptions
        with pytest.raises(CriticalCallbackFailure) as exc_info:
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        
        # Should contain information about critical failures
        assert "Critical callback failures" in str(exc_info.value)
        assert "test_conn" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_no_exceptions_in_callbacks(self):
        """Test behavior when no exceptions occur in callbacks."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        results = []
        
        async def successful_callback_1(conn_id, event_type):
            results.append("success_1")
            return "success_1"
            
        async def successful_callback_2(conn_id, event_type):
            results.append("success_2")
            return "success_2"
            
        async def successful_callback_3(conn_id, event_type):
            results.append("success_3")
            return "success_3"
        
        # Register successful callbacks
        synchronizer.register_sync_callback("test_conn", successful_callback_1)
        synchronizer.register_sync_callback("test_conn", successful_callback_2)
        synchronizer.register_sync_callback("test_conn", successful_callback_3)
        
        # Should complete without raising
        await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        assert results == ["success_1", "success_2", "success_3"]
    
    @pytest.mark.asyncio
    async def test_only_non_critical_exceptions(self):
        """Test behavior with only non-critical exceptions."""
        # Mock: Generic component isolation for controlled unit testing
        connection_manager = MagicMock()  # TODO: Use real service instance
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        async def non_critical_callback_1(conn_id, event_type):
            raise ValueError("error_1")
            
        async def non_critical_callback_2(conn_id, event_type):
            raise RuntimeError("error_2")
        
        # Register non-critical callbacks
        synchronizer.register_sync_callback("test_conn", non_critical_callback_1)
        synchronizer.register_sync_callback("test_conn", non_critical_callback_2)
        
        # Should NOT raise CriticalCallbackFailure
        try:
            await synchronizer._notify_sync_callbacks("test_conn", "state_desync")
        except CriticalCallbackFailure:
            pytest.fail("Non-critical exceptions should not raise CriticalCallbackFailure")