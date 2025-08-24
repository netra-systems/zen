"""
WebSocket Updates Test Suite for Synthetic Data Service
Testing WebSocket real-time updates during generation
"""

import sys
from pathlib import Path

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, MagicMock

import pytest

from netra_backend.app.websocket_core.manager import get_websocket_manager as get_unified_manager
ws_manager = get_unified_manager()

@pytest.fixture
def ws_service():
    return ws_manager

@pytest.fixture
def mock_websocket():
    # Mock: Generic component isolation for controlled unit testing
    ws = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    ws.send_json = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    ws.receive_json = AsyncMock()
    return ws

# ==================== Test Suite: WebSocket Updates ====================

class TestWebSocketUpdates:
    """Test WebSocket real-time updates during generation"""
    @pytest.mark.asyncio
    async def test_websocket_connection_management(self, ws_service, mock_websocket):
        """Test WebSocket connection lifecycle"""
        job_id = str(uuid.uuid4())
        
        # Connect
        await ws_service.connect(mock_websocket, job_id)
        assert job_id in ws_service.active_connections
        
        # Disconnect
        await ws_service.disconnect(job_id)
        assert job_id not in ws_service.active_connections
    @pytest.mark.asyncio
    async def test_generation_progress_broadcast(self, ws_service, mock_websocket):
        """Test broadcasting generation progress to connected clients"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        progress_update = {
            "type": "generation_progress",
            "job_id": job_id,
            "progress_percentage": 50,
            "records_generated": 500,
            "records_ingested": 450
        }
        
        await ws_service.broadcast_to_job(job_id, progress_update)
        
        mock_websocket.send_json.assert_called_with(progress_update)
    @pytest.mark.asyncio
    async def test_batch_completion_notifications(self, ws_service):
        """Test notifications for batch completion"""
        job_id = str(uuid.uuid4())
        
        notifications = []
        
        async def mock_send(data):
            notifications.append(data)
        
        from starlette.websockets import WebSocketState
        # Mock: Generic component isolation for controlled unit testing
        mock_ws = MagicMock()
        mock_ws.send_json = mock_send
        mock_ws.client_state = WebSocketState.CONNECTED
        
        await ws_service.connect(mock_ws, job_id)
        
        for batch_num in range(1, 6):
            await ws_service.notify_batch_complete(
                job_id,
                batch_num,
                batch_size=100
            )
        
        batch_complete_notifications = [n for n in notifications if n["type"] == "batch_complete"]
        assert len(batch_complete_notifications) == 5
        assert all(n["type"] == "batch_complete" for n in batch_complete_notifications)
    @pytest.mark.asyncio
    async def test_error_notification_handling(self, ws_service, mock_websocket):
        """Test error notification through WebSocket"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        error_data = {
            "type": "generation_error",
            "job_id": job_id,
            "error_type": "ClickHouseConnectionError",
            "error_message": "Failed to connect to ClickHouse",
            "recoverable": True,
            "retry_after_seconds": 30
        }
        
        await ws_service.notify_error(job_id, error_data)
        
        mock_websocket.send_json.assert_called_with(error_data)
    @pytest.mark.asyncio
    async def test_websocket_reconnection_handling(self, ws_service):
        """Test WebSocket reconnection and state recovery"""
        job_id = str(uuid.uuid4())
        
        # Initial connection
        # Mock: Generic component isolation for controlled unit testing
        ws1 = AsyncMock()
        await ws_service.connect(ws1, job_id)
        
        # Store some state
        ws_service.set_job_state(job_id, {"progress": 50})
        
        # Disconnect
        await ws_service.disconnect(job_id)
        
        # Reconnect with new socket
        # Mock: Generic component isolation for controlled unit testing
        ws2 = AsyncMock()
        await ws_service.connect(ws2, job_id)
        
        # Should recover state
        state = ws_service.get_job_state(job_id)
        assert state["progress"] == 50
    @pytest.mark.asyncio
    async def test_multiple_client_subscriptions(self, ws_service):
        """Test multiple clients subscribing to same job"""
        job_id = str(uuid.uuid4())
        
        # Mock: Generic component isolation for controlled unit testing
        clients = [AsyncMock() for _ in range(5)]
        
        for client in clients:
            await ws_service.connect(client, job_id)
        
        update = {"type": "progress", "percentage": 75}
        await ws_service.broadcast_to_job(job_id, update)
        
        # All clients should receive update
        for client in clients:
            client.send_json.assert_called_with(update)
    @pytest.mark.asyncio
    async def test_websocket_message_queuing(self, ws_service):
        """Test message queuing for slow clients"""
        job_id = str(uuid.uuid4())
        
        # Mock: Generic component isolation for controlled unit testing
        slow_client = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        slow_client.send_json = AsyncMock(side_effect=lambda x: asyncio.sleep(0.1))
        
        await ws_service.connect(slow_client, job_id)
        
        # Send multiple updates rapidly
        for i in range(10):
            await ws_service.broadcast_to_job(
                job_id,
                {"type": "progress", "percentage": i * 10}
            )
        
        # Should queue messages
        assert ws_service.get_queue_size(job_id) > 0
    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self, ws_service, mock_websocket):
        """Test WebSocket heartbeat/keepalive mechanism"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        # Start heartbeat
        await ws_service.start_heartbeat(job_id, interval_seconds=1)
        
        await asyncio.sleep(2.5)
        
        # Should have sent at least 2 heartbeats
        heartbeat_calls = [
            call for call in mock_websocket.send_json.call_args_list
            if call[0][0].get("type") == "heartbeat"
        ]
        assert len(heartbeat_calls) >= 2
    @pytest.mark.asyncio
    async def test_generation_completion_notification(self, ws_service, mock_websocket):
        """Test generation completion notification"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        completion_data = {
            "type": "generation_complete",
            "job_id": job_id,
            "total_records": 10000,
            "duration_seconds": 45.3,
            "destination_table": "synthetic_data_20240110",
            "quality_metrics": {
                "distribution_accuracy": 0.95,
                "temporal_consistency": 0.98
            }
        }
        
        await ws_service.notify_completion(job_id, completion_data)
        
        mock_websocket.send_json.assert_called_with(completion_data)
    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(self, ws_service):
        """Test WebSocket message rate limiting"""
        job_id = str(uuid.uuid4())
        
        # Mock: Generic component isolation for controlled unit testing
        mock_ws = AsyncMock()
        await ws_service.connect(mock_ws, job_id)
        
        # Configure rate limit
        ws_service.set_rate_limit(job_id, max_messages_per_second=10)
        
        # Try to send 100 messages rapidly
        start_time = asyncio.get_event_loop().time()
        for i in range(100):
            await ws_service.send_with_rate_limit(
                job_id,
                {"type": "progress", "value": i}
            )
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 9 seconds (100 messages / 10 per second)
        assert (end_time - start_time) >= 9

# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])