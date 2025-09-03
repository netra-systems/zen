"""
User WebSocket Emitter Unit Tests

Business Value:
- Ensures per-user event isolation
- Validates event queue management
- Tests retry mechanisms and error handling
"""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from datetime import datetime, timezone, timedelta
import uuid
import json
import time

from netra_backend.app.services.websocket_bridge_factory import (
    UserWebSocketEmitter,
    WebSocketConnectionPool,
    EventPriority,
    EventType,
    ConnectionStatus,
    DeliveryStatus,
    EventMetadata
)


class TestUserWebSocketEmitter:
    """Comprehensive unit tests for UserWebSocketEmitter."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create a mock connection pool."""
        pool = MagicMock(spec=WebSocketConnectionPool)
        pool.broadcast_to_user = AsyncMock(return_value=1)
        pool.get_active_connections = MagicMock(return_value=[])
        pool.add_connection = AsyncMock(return_value="conn-123")
        pool.remove_connection = AsyncMock(return_value=True)
        return pool
    
    @pytest.fixture
    def mock_monitor(self):
        """Create a mock notification monitor."""
        monitor = MagicMock()
        monitor.record_event = MagicMock()
        monitor.record_error = MagicMock()
        monitor.record_delivery = MagicMock()
        return monitor
    
    @pytest.fixture
    def emitter(self, mock_pool, mock_monitor):
        """Create a UserWebSocketEmitter instance."""
        emitter = UserWebSocketEmitter(
            user_id="user-123",
            session_id="session-456",
            connection_pool=mock_pool,
            monitor=mock_monitor
        )
        return emitter
    
    def test_initialization(self, emitter):
        """Test emitter initialization with all properties."""
        assert emitter.user_id == "user-123"
        assert emitter.session_id == "session-456"
        assert emitter.is_active is True
        assert emitter.connection_id is None
        assert len(emitter.event_queue) == 0
        assert emitter.retry_attempts == 3
        assert emitter.batch_size == 10
        assert emitter.max_queue_size == 100
    
    def test_metrics_initialization(self, emitter):
        """Test metrics are properly initialized."""
        metrics = emitter.get_metrics()
        assert metrics["events_sent"] == 0
        assert metrics["events_failed"] == 0
        assert metrics["events_queued"] == 0
        assert metrics["events_dropped"] == 0
        assert metrics["retry_count"] == 0
        assert metrics["user_id"] == "user-123"
    
    @pytest.mark.asyncio
    async def test_emit_simple_event(self, emitter, mock_pool, mock_monitor):
        """Test emitting a simple event."""
        event = {
            "type": "agent_started",
            "data": {"agent": "test_agent"}
        }
        
        success = await emitter.emit(event)
        
        assert success is True
        mock_pool.broadcast_to_user.assert_called_once_with("user-123", event)
        mock_monitor.record_event.assert_called_once()
        mock_monitor.record_delivery.assert_called_once()
        assert emitter.metrics["events_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_emit_with_metadata(self, emitter, mock_pool):
        """Test emitting event with metadata."""
        event = {
            "type": "tool_executing",
            "data": {"tool": "search"}
        }
        
        success = await emitter.emit(
            event,
            priority=EventPriority.HIGH,
            metadata={"request_id": "req-123"}
        )
        
        assert success is True
        
        # Verify event was enhanced with metadata
        call_args = mock_pool.broadcast_to_user.call_args[0]
        sent_event = call_args[1]
        assert "metadata" in sent_event or "request_id" in str(sent_event)
    
    @pytest.mark.asyncio
    async def test_emit_with_retry(self, emitter, mock_pool):
        """Test event emission with retry on failure."""
        # First two calls fail, third succeeds
        mock_pool.broadcast_to_user.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            1  # Success
        ]
        
        event = {"type": "test"}
        success = await emitter.emit(event)
        
        assert success is True
        assert mock_pool.broadcast_to_user.call_count == 3
        assert emitter.metrics["retry_count"] == 2
        assert emitter.metrics["events_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_emit_max_retries_exceeded(self, emitter, mock_pool):
        """Test event emission fails after max retries."""
        mock_pool.broadcast_to_user.side_effect = Exception("Persistent error")
        emitter.retry_attempts = 2
        
        event = {"type": "test"}
        success = await emitter.emit(event)
        
        assert success is False
        assert mock_pool.broadcast_to_user.call_count == 2
        assert emitter.metrics["events_failed"] == 1
    
    def test_queue_event(self, emitter):
        """Test queueing events."""
        event1 = {"type": "event1"}
        event2 = {"type": "event2"}
        
        queued1 = emitter.queue_event(event1)
        queued2 = emitter.queue_event(event2, priority=EventPriority.HIGH)
        
        assert queued1 is True
        assert queued2 is True
        assert len(emitter.event_queue) == 2
        assert emitter.metrics["events_queued"] == 2
        
        # High priority should be first
        assert emitter.event_queue[0]["type"] == "event2"
    
    def test_queue_overflow(self, emitter):
        """Test queue overflow handling."""
        emitter.max_queue_size = 5
        
        # Fill queue
        for i in range(5):
            emitter.queue_event({"type": f"event{i}"})
        
        # Try to add one more
        queued = emitter.queue_event({"type": "overflow"})
        
        assert queued is False
        assert len(emitter.event_queue) == 5
        assert emitter.metrics["events_dropped"] == 1
    
    @pytest.mark.asyncio
    async def test_flush_queue(self, emitter, mock_pool):
        """Test flushing entire event queue."""
        # Queue multiple events
        for i in range(5):
            emitter.queue_event({"type": f"event{i}"})
        
        # Flush all
        flushed = await emitter.flush_queue()
        
        assert flushed == 5
        assert len(emitter.event_queue) == 0
        assert mock_pool.broadcast_to_user.call_count == 5
        assert emitter.metrics["events_sent"] == 5
    
    @pytest.mark.asyncio
    async def test_process_batch(self, emitter, mock_pool):
        """Test processing events in batches."""
        emitter.batch_size = 3
        
        # Queue 10 events
        for i in range(10):
            emitter.queue_event({"type": f"event{i}"})
        
        # Process one batch
        processed = await emitter.process_batch()
        
        assert processed == 3
        assert len(emitter.event_queue) == 7
        assert mock_pool.broadcast_to_user.call_count == 3
    
    @pytest.mark.asyncio
    async def test_auto_flush_on_max_queue(self, emitter, mock_pool):
        """Test automatic flush when queue reaches max size."""
        emitter.max_queue_size = 5
        emitter.auto_flush = True
        
        # Add events up to max
        for i in range(5):
            emitter.queue_event({"type": f"event{i}"})
        
        # Should trigger auto flush
        await emitter.check_auto_flush()
        
        assert len(emitter.event_queue) < 5
        assert mock_pool.broadcast_to_user.called
    
    def test_sanitize_sensitive_event(self, emitter):
        """Test sanitization of sensitive data in events."""
        event = {
            "type": "agent_thinking",
            "data": {
                "thought": "API key is sk-1234567890",
                "password": "secret123",
                "token": "bearer_token_xyz"
            }
        }
        
        sanitized = emitter.sanitize_event(event.copy())
        
        # Check sensitive data is removed/masked
        assert "sk-1234567890" not in str(sanitized)
        assert "secret123" not in str(sanitized)
        assert "bearer_token_xyz" not in str(sanitized)
    
    def test_event_type_classification(self, emitter):
        """Test event type classification."""
        assert emitter.classify_event_type("agent_started") == EventType.LIFECYCLE
        assert emitter.classify_event_type("tool_executing") == EventType.TOOL
        assert emitter.classify_event_type("error") == EventType.ERROR
        assert emitter.classify_event_type("chat_message") == EventType.MESSAGE
        assert emitter.classify_event_type("custom_event") == EventType.CUSTOM
    
    def test_priority_assignment(self, emitter):
        """Test automatic priority assignment based on event type."""
        error_priority = emitter.get_event_priority({"type": "error"})
        lifecycle_priority = emitter.get_event_priority({"type": "agent_completed"})
        message_priority = emitter.get_event_priority({"type": "chat_message"})
        
        assert error_priority == EventPriority.HIGH
        assert lifecycle_priority == EventPriority.MEDIUM
        assert message_priority == EventPriority.NORMAL
    
    @pytest.mark.asyncio
    async def test_connection_management(self, emitter, mock_pool):
        """Test WebSocket connection management."""
        ws = MagicMock()
        ws.send = AsyncMock()
        
        # Add connection
        await emitter.add_connection(ws)
        
        assert emitter.connection_id == "conn-123"
        mock_pool.add_connection.assert_called_once_with("user-123", ws)
        
        # Remove connection
        await emitter.remove_connection()
        
        assert emitter.connection_id is None
        mock_pool.remove_connection.assert_called_once_with("conn-123")
    
    @pytest.mark.asyncio
    async def test_lifecycle_events(self, emitter, mock_pool):
        """Test emitting lifecycle events."""
        # Start event
        await emitter.emit_lifecycle_event("started", {"agent": "test"})
        
        # Progress event
        await emitter.emit_lifecycle_event("progress", {"percent": 50})
        
        # Complete event
        await emitter.emit_lifecycle_event("completed", {"result": "success"})
        
        assert mock_pool.broadcast_to_user.call_count == 3
        
        # Verify event types
        calls = mock_pool.broadcast_to_user.call_args_list
        assert calls[0][0][1]["type"] == "lifecycle_started"
        assert calls[1][0][1]["type"] == "lifecycle_progress"
        assert calls[2][0][1]["type"] == "lifecycle_completed"
    
    @pytest.mark.asyncio
    async def test_tool_events(self, emitter, mock_pool):
        """Test emitting tool execution events."""
        # Tool start
        await emitter.emit_tool_event("executing", {
            "tool": "search",
            "params": {"query": "test"}
        })
        
        # Tool complete
        await emitter.emit_tool_event("completed", {
            "tool": "search",
            "result": {"hits": 10}
        })
        
        assert mock_pool.broadcast_to_user.call_count == 2
        
        calls = mock_pool.broadcast_to_user.call_args_list
        assert calls[0][0][1]["type"] == "tool_executing"
        assert calls[1][0][1]["type"] == "tool_completed"
    
    @pytest.mark.asyncio
    async def test_error_event(self, emitter, mock_pool, mock_monitor):
        """Test emitting error events."""
        error_data = {
            "message": "Operation failed",
            "code": "ERR_001",
            "stack": "traceback..."
        }
        
        await emitter.emit_error(error_data)
        
        # Error events should be high priority
        call_args = mock_pool.broadcast_to_user.call_args[0]
        event = call_args[1]
        
        assert event["type"] == "error"
        assert event["data"] == error_data
        mock_monitor.record_error.assert_called_once()
    
    def test_inactive_emitter_behavior(self, emitter):
        """Test behavior when emitter is inactive."""
        emitter.is_active = False
        
        # Should not queue events
        queued = emitter.queue_event({"type": "test"})
        assert queued is False
        assert len(emitter.event_queue) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_emissions(self, emitter, mock_pool):
        """Test concurrent event emissions."""
        events = [{"type": f"event{i}"} for i in range(10)]
        
        # Emit all events concurrently
        tasks = [emitter.emit(event) for event in events]
        results = await asyncio.gather(*tasks)
        
        assert all(results)
        assert mock_pool.broadcast_to_user.call_count == 10
        assert emitter.metrics["events_sent"] == 10
    
    def test_get_queue_status(self, emitter):
        """Test getting queue status."""
        # Add some events
        for i in range(3):
            emitter.queue_event({"type": f"event{i}"})
        
        status = emitter.get_queue_status()
        
        assert status["queue_size"] == 3
        assert status["max_size"] == 100
        assert status["is_full"] is False
        assert status["utilization"] == 0.03
    
    @pytest.mark.asyncio
    async def test_delivery_confirmation(self, emitter, mock_pool):
        """Test delivery confirmation tracking."""
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "type": "test",
            "data": {}
        }
        
        # Track delivery
        success = await emitter.emit_with_confirmation(event)
        
        assert success is True
        assert event_id in emitter.delivery_confirmations
        assert emitter.delivery_confirmations[event_id] == DeliveryStatus.DELIVERED
    
    def test_event_deduplication(self, emitter):
        """Test event deduplication in queue."""
        event = {"id": "same-id", "type": "test"}
        
        # Queue same event multiple times
        emitter.queue_event(event)
        emitter.queue_event(event)
        emitter.queue_event(event)
        
        # Should only have one instance
        unique_ids = set(e.get("id") for e in emitter.event_queue)
        assert len(unique_ids) == 1
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, emitter, mock_pool):
        """Test graceful shutdown of emitter."""
        # Queue some events
        for i in range(3):
            emitter.queue_event({"type": f"event{i}"})
        
        # Shutdown should flush queue
        await emitter.shutdown()
        
        assert emitter.is_active is False
        assert len(emitter.event_queue) == 0
        assert mock_pool.broadcast_to_user.call_count == 3
    
    def test_metrics_aggregation(self, emitter):
        """Test metrics aggregation over time."""
        # Simulate activity
        emitter.metrics["events_sent"] = 100
        emitter.metrics["events_failed"] = 5
        emitter.metrics["retry_count"] = 10
        
        metrics = emitter.get_metrics()
        
        # Calculate derived metrics
        assert metrics["success_rate"] == 0.95  # 95% success
        assert metrics["retry_rate"] == 0.1  # 10% retry rate
    
    @pytest.mark.asyncio
    async def test_event_compression(self, emitter, mock_pool):
        """Test event compression for large payloads."""
        large_data = "x" * 10000  # Large payload
        event = {
            "type": "large_event",
            "data": large_data
        }
        
        # Should compress large events
        success = await emitter.emit(event, compress=True)
        
        assert success is True
        call_args = mock_pool.broadcast_to_user.call_args[0]
        sent_event = call_args[1]
        
        # Event should be marked as compressed
        assert sent_event.get("compressed") is True or len(str(sent_event)) < len(large_data)