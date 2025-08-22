"""Critical WebSocket Execution Engine Tests

Tests to prevent regression of WebSocket execution engine being None.
These tests ensure all WebSocket components have properly initialized
execution engines and can process messages end-to-end.

Business Value: Prevents $8K MRR loss from WebSocket failures.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.websocket.connection import ConnectionInfo, ConnectionManager
from netra_backend.app.websocket.connection_executor import ConnectionExecutor

from netra_backend.app.websocket.message_handler_core import (
    ModernReliableMessageHandler,
)
from netra_backend.app.websocket.message_router import ModernMessageTypeRouter
from netra_backend.app.websocket.websocket_broadcast_executor import (
    WebSocketBroadcastExecutor,
)

class TestWebSocketExecutionEngineInitialization:
    """Test that all WebSocket components have initialized execution engines."""
    
    def test_message_handler_has_execution_engine(self):
        """Test ModernReliableMessageHandler has execution_engine initialized."""
        handler = ModernReliableMessageHandler()
        
        assert handler.execution_engine is not None
        assert isinstance(handler.execution_engine, BaseExecutionEngine)
        assert handler.reliability_manager is not None
        assert handler.monitor is not None
    
    def test_message_router_has_execution_engine(self):
        """Test ModernMessageTypeRouter has execution_engine initialized."""
        router = ModernMessageTypeRouter()
        
        assert router.execution_engine is not None
        assert isinstance(router.execution_engine, BaseExecutionEngine)
        assert router.reliability_manager is not None
        assert router.monitor is not None
    
    def test_broadcast_executor_has_execution_engine(self):
        """Test WebSocketBroadcastExecutor has execution_engine initialized."""
        conn_manager = Mock(spec=ConnectionManager)
        executor = WebSocketBroadcastExecutor(conn_manager)
        
        assert executor.execution_engine is not None
        assert isinstance(executor.execution_engine, BaseExecutionEngine)
        assert executor.reliability_manager is not None
        assert executor.monitor is not None
    
    def test_connection_executor_has_execution_engine(self):
        """Test ConnectionExecutor has execution_engine initialized."""
        executor = ConnectionExecutor()
        
        assert executor.execution_engine is not None
        assert isinstance(executor.execution_engine, BaseExecutionEngine)
        assert executor.reliability_manager is not None
        assert executor.monitor is not None

class TestWebSocketMessageFlow:
    """Test end-to-end WebSocket message processing flow."""
    
    @pytest.mark.asyncio
    async def test_message_handler_processes_valid_message(self):
        """Test that message handler can process a valid message."""
        handler = ModernReliableMessageHandler()
        
        # Create mock connection info
        conn_info = ConnectionInfo(
            connection_id="test_conn_1",
            user_id="user_123",
            websocket=Mock()
        )
        
        # Create mock message processor
        message_processor = AsyncMock()
        message_processor.return_value = None
        
        # Valid JSON message
        raw_message = '{"type": "test", "content": "Hello"}'
        
        # Process message
        result = await handler.handle_message(raw_message, conn_info, message_processor)
        
        # Verify message was processed
        assert result is True
        message_processor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_router_routes_to_correct_handler(self):
        """Test that message router routes messages to correct handlers."""
        router = ModernMessageTypeRouter()
        
        # Register test handler
        test_handler = AsyncMock()
        test_handler.return_value = {"success": True}
        router.register_handler("test_type", test_handler)
        
        # Create test message and connection
        message = {"type": "test_type", "data": "test_data"}
        conn_info = ConnectionInfo(
            connection_id="test_conn_2",
            user_id="user_456",
            websocket=Mock()
        )
        
        # Route message
        result = await router.route_message(message, conn_info)
        
        # Verify handler was called
        test_handler.assert_called_once_with(message, conn_info)
        assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_broadcast_executor_sends_to_all_connections(self):
        """Test that broadcast executor can send to all connections."""
        # Create mock connection manager
        conn_manager = Mock(spec=ConnectionManager)
        conn_manager.get_all_connections.return_value = [
            Mock(connection_id="conn_1"),
            Mock(connection_id="conn_2")
        ]
        
        executor = WebSocketBroadcastExecutor(conn_manager)
        
        # Mock the actual broadcast execution
        with patch.object(executor.executor, 'execute_all_broadcast') as mock_broadcast:
            mock_broadcast.return_value = Mock(successful=2, failed=0)
            
            # Create broadcast context
            from netra_backend.app.websocket.broadcast_context import (
                BroadcastContext,
                BroadcastOperation,
            )
            broadcast_ctx = BroadcastContext(
                operation=BroadcastOperation.ALL_CONNECTIONS,
                message={"type": "broadcast", "content": "Hello all"}
            )
            
            # Execute broadcast
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
            
            state = DeepAgentState(user_request="broadcast_test")
            context = ExecutionContext(
                run_id="test_broadcast_1",
                agent_name="websocket_broadcast",
                state=state,
                metadata={"broadcast_context": broadcast_ctx}
            )
            
            result = await executor.execute_core_logic(context)
            
            # Verify broadcast was attempted
            assert result is not None
            mock_broadcast.assert_called_once()

class TestWebSocketErrorHandling:
    """Test WebSocket error handling with execution engine."""
    
    @pytest.mark.asyncio
    async def test_message_handler_handles_invalid_json(self):
        """Test that message handler gracefully handles invalid JSON."""
        handler = ModernReliableMessageHandler()
        
        conn_info = ConnectionInfo(
            connection_id="test_conn_3",
            user_id="user_789",
            websocket=Mock()
        )
        
        message_processor = AsyncMock()
        
        # Invalid JSON message
        raw_message = '{"invalid": json}'
        
        # Process should handle error gracefully
        result = await handler.handle_message(raw_message, conn_info, message_processor)
        
        # Should return False for invalid message
        assert result is False
        # Processor should not be called for invalid JSON
        message_processor.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_router_handles_missing_handler(self):
        """Test that router handles messages with no registered handler."""
        router = ModernMessageTypeRouter()
        
        # No handlers registered
        message = {"type": "unknown_type", "data": "test"}
        conn_info = ConnectionInfo(
            connection_id="test_conn_4",
            user_id="user_000",
            websocket=Mock()
        )
        
        # Should raise error for unknown type
        with pytest.raises(ValueError, match="No handler available"):
            await router.route_message(message, conn_info)

class TestCircularImportPrevention:
    """Test that circular imports are properly avoided."""
    
    def test_late_import_pattern_works(self):
        """Test that late import of BaseExecutionEngine works."""
        # This test verifies the late import pattern doesn't cause issues
        
        # Import should work without circular dependency
        from netra_backend.app.websocket.connection_executor import ConnectionExecutor
        from netra_backend.app.websocket.message_handler_core import (
            ModernReliableMessageHandler,
        )
        from netra_backend.app.websocket.message_router import ModernMessageTypeRouter
        from netra_backend.app.websocket.websocket_broadcast_executor import (
            WebSocketBroadcastExecutor,
        )
        
        # All components should initialize successfully
        handler = ModernReliableMessageHandler()
        router = ModernMessageTypeRouter()
        executor = WebSocketBroadcastExecutor(Mock())
        conn_executor = ConnectionExecutor()
        
        # All should have execution engines
        assert all([
            handler.execution_engine is not None,
            router.execution_engine is not None,
            executor.execution_engine is not None,
            conn_executor.execution_engine is not None
        ])

class TestMetricsCollectorResilience:
    """Test that metrics collector handles None connection manager."""
    
    @pytest.mark.asyncio
    async def test_metrics_collector_handles_none_connection_manager(self):
        """Test metrics collector doesn't crash with None connection manager."""
        from netra_backend.app.monitoring.models import MetricsCollector
        
        collector = MetricsCollector()
        
        # Mock get_connection_manager to return None
        with patch('app.monitoring.metrics_collector.get_connection_manager', return_value=None):
            # Should not raise exception
            metrics = await collector._gather_websocket_metrics()
            
            # Should return empty metrics
            assert metrics.active_connections == 0
            assert metrics.total_connections == 0
    
    @pytest.mark.asyncio
    async def test_metrics_collector_handles_connection_manager_error(self):
        """Test metrics collector handles errors from connection manager."""
        from netra_backend.app.monitoring.models import MetricsCollector
        
        collector = MetricsCollector()
        
        # Mock connection manager that raises error
        mock_conn_manager = Mock()
        mock_conn_manager.get_stats = AsyncMock(side_effect=Exception("Connection error"))
        
        with patch('app.monitoring.metrics_collector.get_connection_manager', return_value=mock_conn_manager):
            # Should not raise exception
            metrics = await collector._gather_websocket_metrics()
            
            # Should return empty metrics
            assert metrics.active_connections == 0
            assert metrics.total_connections == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])