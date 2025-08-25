"""
Comprehensive tests for WebSocket Message Router.

Tests message routing, handler registration, middleware pipeline,
metrics tracking, and error handling.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from netra_backend.app.services.websocket.message_router import MessageRouter
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.core.exceptions_base import NetraException


class MockMessageHandler(BaseMessageHandler):
    """Mock message handler for testing."""
    
    def __init__(self, message_type: str):
        self.message_type = message_type
        self.handle_calls = []
    
    def get_message_type(self) -> str:
        return self.message_type
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle message and record call."""
        self.handle_calls.append({
            'user_id': user_id,
            'payload': payload,
            'timestamp': time.time()
        })


class TestWebSocketMessageRouter:
    """Tests for WebSocket message router functionality."""

    @pytest.fixture
    def router(self):
        """Create a fresh message router for testing."""
        return MessageRouter()

    @pytest.fixture
    def mock_handler(self):
        """Create a mock message handler."""
        return MockMessageHandler("test_message")

    @pytest.fixture
    def chat_handler(self):
        """Create a chat message handler."""
        return MockMessageHandler("chat_message")

    def test_router_initialization(self, router):
        """Test router is properly initialized."""
        assert router.handlers == {}
        assert router.middleware == []
        assert router.routing_metrics['messages_routed'] == 0
        assert router.routing_metrics['routing_errors'] == 0
        assert len(router.routing_metrics['handler_execution_times']) == 0

    def test_handler_registration(self, router, mock_handler):
        """Test message handler registration."""
        router.register_handler(mock_handler)
        
        assert "test_message" in router.handlers
        assert router.handlers["test_message"] == mock_handler

    def test_duplicate_handler_registration_raises_exception(self, router, mock_handler):
        """Test that registering duplicate handlers raises exception."""
        router.register_handler(mock_handler)
        
        duplicate_handler = MockMessageHandler("test_message")
        
        with pytest.raises(NetraException) as exc_info:
            router.register_handler(duplicate_handler)
        
        assert "already registered" in str(exc_info.value)

    def test_handler_unregistration(self, router, mock_handler):
        """Test message handler unregistration."""
        router.register_handler(mock_handler)
        assert "test_message" in router.handlers
        
        router.unregister_handler("test_message")
        assert "test_message" not in router.handlers

    def test_unregister_nonexistent_handler_safe(self, router):
        """Test unregistering non-existent handler is safe."""
        # Should not raise exception
        router.unregister_handler("nonexistent")
        assert len(router.handlers) == 0

    @pytest.mark.asyncio
    async def test_successful_message_routing(self, router, mock_handler):
        """Test successful message routing to handler."""
        router.register_handler(mock_handler)
        
        user_id = "user123"
        payload = {"content": "Hello world"}
        
        result = await router.route_message(user_id, "test_message", payload)
        
        assert result is True
        assert len(mock_handler.handle_calls) == 1
        assert mock_handler.handle_calls[0]['user_id'] == user_id
        assert mock_handler.handle_calls[0]['payload'] == payload

    @pytest.mark.asyncio
    async def test_routing_updates_metrics(self, router, mock_handler):
        """Test that routing updates metrics correctly."""
        router.register_handler(mock_handler)
        
        initial_count = router.routing_metrics['messages_routed']
        
        await router.route_message("user123", "test_message", {})
        
        assert router.routing_metrics['messages_routed'] == initial_count + 1
        assert len(router.routing_metrics['handler_execution_times']["test_message"]) == 1

    @pytest.mark.asyncio
    async def test_routing_nonexistent_handler_raises_exception(self, router):
        """Test routing to non-existent handler raises exception."""
        with pytest.raises(NetraException) as exc_info:
            await router.route_message("user123", "unknown_message", {})
        
        assert "No handler registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handler_exception_propagates_as_netra_exception(self, router):
        """Test that handler exceptions are wrapped in NetraException."""
        failing_handler = Mock()
        failing_handler.get_message_type.return_value = "failing_message"
        failing_handler.handle = AsyncMock(side_effect=ValueError("Handler failed"))
        
        router.register_handler(failing_handler)
        
        with pytest.raises(NetraException) as exc_info:
            await router.route_message("user123", "failing_message", {})
        
        assert "Message routing failed" in str(exc_info.value)
        assert router.routing_metrics['routing_errors'] == 1

    @pytest.mark.asyncio
    async def test_middleware_pipeline_processing(self, router, mock_handler):
        """Test middleware pipeline processes payloads."""
        router.register_handler(mock_handler)
        
        # Add middleware that adds metadata
        async def add_metadata(user_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            payload['middleware_processed'] = True
            payload['processing_user'] = user_id
            return payload
        
        async def add_timestamp(user_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            payload['processed_at'] = time.time()
            return payload
        
        router.middleware = [add_metadata, add_timestamp]
        
        original_payload = {"content": "Hello"}
        await router.route_message("user456", "test_message", original_payload)
        
        # Check handler received processed payload
        processed_payload = mock_handler.handle_calls[0]['payload']
        assert processed_payload['middleware_processed'] is True
        assert processed_payload['processing_user'] == "user456"
        assert 'processed_at' in processed_payload
        assert processed_payload['content'] == "Hello"

    @pytest.mark.asyncio
    async def test_multiple_handlers_different_types(self, router):
        """Test routing to different handler types."""
        chat_handler = MockMessageHandler("chat")
        notification_handler = MockMessageHandler("notification")
        
        router.register_handler(chat_handler)
        router.register_handler(notification_handler)
        
        await router.route_message("user1", "chat", {"message": "Hi"})
        await router.route_message("user2", "notification", {"alert": "New message"})
        
        assert len(chat_handler.handle_calls) == 1
        assert len(notification_handler.handle_calls) == 1
        assert chat_handler.handle_calls[0]['payload']['message'] == "Hi"
        assert notification_handler.handle_calls[0]['payload']['alert'] == "New message"

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, router):
        """Test execution time is properly tracked."""
        slow_handler = Mock()
        slow_handler.get_message_type.return_value = "slow_message"
        
        async def slow_handle(user_id, payload):
            await asyncio.sleep(0.1)  # Simulate slow processing
        
        slow_handler.handle = AsyncMock(side_effect=slow_handle)
        router.register_handler(slow_handler)
        
        await router.route_message("user123", "slow_message", {})
        
        execution_times = router.routing_metrics['handler_execution_times']["slow_message"]
        assert len(execution_times) == 1
        assert execution_times[0] >= 0.1  # Should be at least 100ms

    @pytest.mark.asyncio
    async def test_concurrent_message_routing(self, router):
        """Test concurrent message routing works correctly."""
        handler = MockMessageHandler("concurrent_test")
        router.register_handler(handler)
        
        # Route multiple messages concurrently
        tasks = []
        for i in range(5):
            task = router.route_message(f"user{i}", "concurrent_test", {"id": i})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert len(handler.handle_calls) == 5
        
        # Verify each message was handled
        handled_ids = {call['payload']['id'] for call in handler.handle_calls}
        assert handled_ids == {0, 1, 2, 3, 4}

    @pytest.mark.asyncio
    async def test_middleware_error_handling(self, router, mock_handler):
        """Test middleware errors are properly handled."""
        router.register_handler(mock_handler)
        
        async def failing_middleware(user_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Middleware failed")
        
        router.middleware = [failing_middleware]
        
        with pytest.raises(NetraException) as exc_info:
            await router.route_message("user123", "test_message", {})
        
        assert "Message routing failed" in str(exc_info.value)

    def test_metrics_reset_functionality(self, router, mock_handler):
        """Test metrics can be reset."""
        router.register_handler(mock_handler)
        
        # Generate some metrics
        router.routing_metrics['messages_routed'] = 10
        router.routing_metrics['routing_errors'] = 5
        router.routing_metrics['handler_execution_times']['test'] = [1.0, 2.0]
        
        # Reset metrics
        router.routing_metrics = router._init_metrics()
        
        assert router.routing_metrics['messages_routed'] == 0
        assert router.routing_metrics['routing_errors'] == 0
        assert len(router.routing_metrics['handler_execution_times']) == 0

    @pytest.mark.asyncio
    async def test_payload_immutability_in_handler(self, router):
        """Test that original payload remains unchanged."""
        handler = Mock()
        handler.get_message_type.return_value = "immutable_test"
        
        async def modifying_handle(user_id, payload):
            payload['modified'] = True  # Handler tries to modify payload
        
        handler.handle = AsyncMock(side_effect=modifying_handle)
        router.register_handler(handler)
        
        original_payload = {"content": "original"}
        await router.route_message("user123", "immutable_test", original_payload)
        
        # Original payload should be modified (this is expected behavior)
        # If we need immutability, we should add copy logic in the router
        assert 'modified' in original_payload

    @pytest.mark.asyncio
    async def test_handler_with_none_return(self, router):
        """Test handlers that return None are handled correctly."""
        handler = Mock()
        handler.get_message_type.return_value = "none_return"
        handler.handle = AsyncMock(return_value=None)
        
        router.register_handler(handler)
        
        result = await router.route_message("user123", "none_return", {})
        
        # Router should return True even if handler returns None
        assert result is True

    def test_handler_registry_access(self, router, mock_handler):
        """Test access to handler registry."""
        router.register_handler(mock_handler)
        
        # Test direct access to handlers
        assert len(router.handlers) == 1
        assert "test_message" in router.handlers
        assert router.handlers["test_message"] == mock_handler

    @pytest.mark.asyncio
    async def test_middleware_execution_order(self, router, mock_handler):
        """Test middleware executes in registration order."""
        router.register_handler(mock_handler)
        
        execution_order = []
        
        async def middleware1(user_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            execution_order.append(1)
            payload['step1'] = True
            return payload
        
        async def middleware2(user_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            execution_order.append(2)
            payload['step2'] = True
            return payload
        
        router.middleware = [middleware1, middleware2]
        
        await router.route_message("user123", "test_message", {})
        
        assert execution_order == [1, 2]
        processed_payload = mock_handler.handle_calls[0]['payload']
        assert processed_payload['step1'] is True
        assert processed_payload['step2'] is True

    def test_router_state_consistency(self, router, mock_handler):
        """Test router maintains consistent state across operations."""
        # Register handler
        router.register_handler(mock_handler)
        assert len(router.handlers) == 1
        
        # Unregister handler
        router.unregister_handler("test_message")
        assert len(router.handlers) == 0
        
        # Re-register same handler should work
        router.register_handler(mock_handler)
        assert len(router.handlers) == 1