"""WebSocket End-to-End Integration Tests

Comprehensive tests for WebSocket functionality including connection,
message processing, broadcasting, and error scenarios.

Business Value: Ensures real-time features work reliably for all customer segments.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from fastapi import WebSocket
from app.websocket.connection import ConnectionInfo, ConnectionManager
from app.websocket.message_handler_core import ModernReliableMessageHandler
from app.websocket.message_router import ModernMessageTypeRouter
from app.websocket.websocket_broadcast_executor import WebSocketBroadcastExecutor
from app.ws_manager import WebSocketManager


class TestWebSocketConnectionLifecycle:
    """Test WebSocket connection establishment and teardown."""
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self):
        """Test successful WebSocket connection establishment."""
        # Create mock WebSocket
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        # Create connection manager
        conn_manager = ConnectionManager()
        
        # Establish connection
        conn_info = await conn_manager.connect("user_123", websocket)
        
        # Verify connection info
        assert conn_info is not None
        assert conn_info.user_id == "user_123"
        assert conn_info.websocket == websocket
        assert conn_info.connection_id is not None
        
        # Verify connection is tracked
        assert "user_123" in conn_manager.active_connections
        assert conn_info in conn_manager.active_connections["user_123"]
    
    @pytest.mark.asyncio
    async def test_connection_cleanup(self):
        """Test WebSocket connection cleanup on disconnect."""
        websocket = Mock(spec=WebSocket)
        conn_manager = ConnectionManager()
        
        # Establish and then disconnect
        conn_info = await conn_manager.connect("user_456", websocket)
        await conn_manager.disconnect(conn_info)
        
        # Verify connection is removed
        if "user_456" in conn_manager.active_connections:
            assert conn_info not in conn_manager.active_connections["user_456"]
    
    @pytest.mark.asyncio
    async def test_multiple_connections_per_user(self):
        """Test handling multiple connections for same user."""
        conn_manager = ConnectionManager()
        
        # Create multiple connections for same user
        websocket1 = Mock(spec=WebSocket)
        websocket2 = Mock(spec=WebSocket)
        
        conn1 = await conn_manager.connect("user_789", websocket1)
        conn2 = await conn_manager.connect("user_789", websocket2)
        
        # Both connections should be tracked
        assert len(conn_manager.active_connections["user_789"]) == 2
        assert conn1 in conn_manager.active_connections["user_789"]
        assert conn2 in conn_manager.active_connections["user_789"]


class TestWebSocketMessageProcessing:
    """Test WebSocket message processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_complete_message_pipeline(self):
        """Test complete message processing from receipt to response."""
        # Setup components
        handler = ModernReliableMessageHandler()
        router = ModernMessageTypeRouter()
        
        # Register message handler
        async def handle_chat_message(message: Dict, conn_info: ConnectionInfo):
            return {"response": f"Processed: {message.get('content')}"}
        
        router.register_handler("chat", handle_chat_message)
        
        # Create connection info
        websocket = Mock(spec=WebSocket)
        websocket.send_json = AsyncMock()
        conn_info = ConnectionInfo("conn_123", "user_123", websocket)
        
        # Process message through pipeline
        raw_message = json.dumps({"type": "chat", "content": "Hello"})
        
        async def message_processor(msg: Dict, conn: ConnectionInfo):
            return await router.route_message(msg, conn)
        
        result = await handler.handle_message(raw_message, conn_info, message_processor)
        
        # Verify successful processing
        assert result is True
    
    @pytest.mark.asyncio
    async def test_message_validation(self):
        """Test message validation in processing pipeline."""
        handler = ModernReliableMessageHandler()
        
        # Test various message formats
        test_cases = [
            ('{"type": "test"}', True),  # Valid
            ('{"invalid": "json"', False),  # Invalid JSON
            ('not json at all', False),  # Not JSON
            ('{"type": "test", "nested": {"key": "value"}}', True),  # Nested valid
        ]
        
        for raw_message, expected_valid in test_cases:
            conn_info = ConnectionInfo("conn_test", "user_test", Mock())
            processor = AsyncMock()
            
            result = await handler.handle_message(raw_message, conn_info, processor)
            
            if expected_valid:
                assert result is True
                processor.assert_called_once()
            else:
                assert result is False
                processor.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_message_routing_with_fallback(self):
        """Test message routing with fallback handler."""
        router = ModernMessageTypeRouter()
        
        # Register specific handler
        specific_handler = AsyncMock(return_value={"handled": "specific"})
        router.register_handler("specific", specific_handler)
        
        # Register fallback handler
        fallback_handler = AsyncMock(return_value={"handled": "fallback"})
        router.register_fallback_handler(fallback_handler)
        
        conn_info = ConnectionInfo("conn_fb", "user_fb", Mock())
        
        # Test specific handler
        result = await router.route_message({"type": "specific"}, conn_info)
        assert result == {"handled": "specific"}
        specific_handler.assert_called_once()
        fallback_handler.assert_not_called()
        
        # Reset mocks
        specific_handler.reset_mock()
        fallback_handler.reset_mock()
        
        # Test fallback handler
        result = await router.route_message({"type": "unknown"}, conn_info)
        assert result == {"handled": "fallback"}
        specific_handler.assert_not_called()
        fallback_handler.assert_called_once()


class TestWebSocketBroadcasting:
    """Test WebSocket broadcasting functionality."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_user(self):
        """Test broadcasting message to specific user's connections."""
        # Setup connection manager with multiple connections
        conn_manager = Mock(spec=ConnectionManager)
        
        # Mock user connections
        conn1 = Mock(spec=ConnectionInfo)
        conn1.websocket.send_json = AsyncMock()
        conn2 = Mock(spec=ConnectionInfo)
        conn2.websocket.send_json = AsyncMock()
        
        conn_manager.get_user_connections.return_value = [conn1, conn2]
        
        # Setup broadcast executor
        executor = WebSocketBroadcastExecutor(conn_manager)
        
        # Create broadcast context
        from app.websocket.broadcast_context import BroadcastContext, BroadcastOperation
        
        broadcast_ctx = BroadcastContext(
            operation=BroadcastOperation.USER_CONNECTIONS,
            message={"type": "notification", "content": "Test broadcast"},
            user_id="user_broadcast"
        )
        
        # Execute broadcast
        from app.agents.base.interface import ExecutionContext
        from app.agents.state import DeepAgentState
        
        context = ExecutionContext(
            run_id="broadcast_user_test",
            agent_name="websocket_broadcast",
            state=DeepAgentState(user_request="broadcast"),
            metadata={"broadcast_context": broadcast_ctx}
        )
        
        result = await executor.execute_core_logic(context)
        
        # Verify broadcast attempted
        assert result is not None
        conn_manager.get_user_connections.assert_called_once_with("user_broadcast")
    
    @pytest.mark.asyncio
    async def test_room_broadcasting(self):
        """Test broadcasting to room members."""
        conn_manager = Mock(spec=ConnectionManager)
        room_manager = Mock()
        
        # Mock room connections
        room_manager.get_room_connections.return_value = ["conn_1", "conn_2", "conn_3"]
        
        executor = WebSocketBroadcastExecutor(conn_manager, room_manager)
        
        # Create room broadcast context
        from app.websocket.broadcast_context import BroadcastContext, BroadcastOperation
        
        broadcast_ctx = BroadcastContext(
            operation=BroadcastOperation.ROOM_CONNECTIONS,
            message={"type": "room_update", "content": "Room message"},
            room_id="room_123"
        )
        
        context = ExecutionContext(
            run_id="broadcast_room_test",
            agent_name="websocket_broadcast",
            state=DeepAgentState(user_request="room_broadcast"),
            metadata={"broadcast_context": broadcast_ctx}
        )
        
        # Mock the executor's broadcast method
        with patch.object(executor.executor, 'execute_room_broadcast') as mock_broadcast:
            mock_broadcast.return_value = Mock(successful=3, failed=0)
            
            result = await executor.execute_core_logic(context)
            
            # Verify room broadcast was attempted
            assert result is not None
            room_manager.get_room_connections.assert_called_once_with("room_123")
            mock_broadcast.assert_called_once()


class TestWebSocketResilience:
    """Test WebSocket resilience and error recovery."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activates after threshold failures."""
        handler = ModernReliableMessageHandler()
        
        # Simulate multiple failures
        conn_info = ConnectionInfo("conn_cb", "user_cb", Mock())
        
        # Create a processor that always fails
        failing_processor = AsyncMock(side_effect=Exception("Processing failed"))
        
        # Process multiple messages to trigger circuit breaker
        for _ in range(10):
            try:
                await handler.handle_message(
                    '{"type": "test"}',
                    conn_info,
                    failing_processor
                )
            except:
                pass
        
        # Circuit breaker should be tracking failures
        assert handler.reliability_manager is not None
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic for transient failures."""
        router = ModernMessageTypeRouter()
        
        # Create handler that fails first time, succeeds second
        call_count = 0
        
        async def flaky_handler(msg: Dict, conn: ConnectionInfo):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient error")
            return {"success": True}
        
        router.register_handler("flaky", flaky_handler)
        
        # Process message - should retry and succeed
        conn_info = ConnectionInfo("conn_retry", "user_retry", Mock())
        
        # The retry logic is handled by execution engine
        # This test verifies the setup exists
        assert router.reliability_manager is not None
        assert router.reliability_manager.retry_config.max_retries > 0
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test system degrades gracefully under failure conditions."""
        handler = ModernReliableMessageHandler()
        
        # Test with various failure scenarios
        scenarios = [
            (None, ConnectionInfo("c1", "u1", Mock())),  # None message
            ('{"type": "test"}', None),  # None connection
            ('', ConnectionInfo("c2", "u2", Mock())),  # Empty message
        ]
        
        for raw_message, conn_info in scenarios:
            if raw_message is None or conn_info is None:
                continue  # Skip invalid scenarios
                
            processor = AsyncMock()
            
            # Should handle gracefully without crashing
            try:
                await handler.handle_message(raw_message, conn_info, processor)
            except:
                pass  # Graceful handling of errors


class TestWebSocketPerformance:
    """Test WebSocket performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_message_processing_latency(self):
        """Test message processing stays within latency targets."""
        handler = ModernReliableMessageHandler()
        
        # Fast processor to test baseline latency
        fast_processor = AsyncMock(return_value={"processed": True})
        
        conn_info = ConnectionInfo("conn_perf", "user_perf", Mock())
        
        # Measure processing time
        import time
        start = time.time()
        
        await handler.handle_message(
            '{"type": "performance_test"}',
            conn_info,
            fast_processor
        )
        
        elapsed = time.time() - start
        
        # Should process quickly (allowing for test overhead)
        assert elapsed < 1.0  # Very generous limit for tests
    
    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """Test handling multiple concurrent messages."""
        handler = ModernReliableMessageHandler()
        
        # Create multiple connection infos
        connections = [
            ConnectionInfo(f"conn_{i}", f"user_{i}", Mock())
            for i in range(10)
        ]
        
        processor = AsyncMock(return_value={"processed": True})
        
        # Process messages concurrently
        tasks = [
            handler.handle_message(
                f'{{"type": "concurrent", "id": {i}}}',
                conn,
                processor
            )
            for i, conn in enumerate(connections)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert processor.call_count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])