"""
L3 Integration Test: WebSocket Message Delivery
Tests WebSocket message delivery reliability and ordering
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import websockets
import json
from unittest.mock import patch, AsyncMock

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.websocket_service import WebSocketService
from netra_backend.app.config import settings
import time

# Add project root to path


class TestWebSocketMessageDeliveryL3:
    """Test WebSocket message delivery scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_message_delivery_confirmation(self):
        """Test message delivery with acknowledgment"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Authenticate first
            await websocket.send(json.dumps({
                "type": "auth",
                "token": "valid_test_token"
            }))
            await websocket.recv()  # Auth response
            
            # Send message with ID for tracking
            message_id = "msg_123"
            await websocket.send(json.dumps({
                "type": "message",
                "id": message_id,
                "content": "test message"
            }))
            
            # Should receive acknowledgment
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "ack"
            assert data["message_id"] == message_id
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_message_ordering_preservation(self):
        """Test message order is preserved"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Authenticate
            await websocket.send(json.dumps({
                "type": "auth",
                "token": "valid_test_token"
            }))
            await websocket.recv()
            
            # Send multiple messages
            messages = []
            for i in range(10):
                msg = {
                    "type": "message",
                    "id": f"msg_{i}",
                    "sequence": i,
                    "content": f"message {i}"
                }
                messages.append(msg)
                await websocket.send(json.dumps(msg))
            
            # Receive acknowledgments
            acks = []
            for _ in range(10):
                response = await websocket.recv()
                data = json.loads(response)
                if data["type"] == "ack":
                    acks.append(int(data["message_id"].split("_")[1]))
            
            # Check order preserved
            assert acks == list(range(10))
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_message_retry_on_failure(self):
        """Test message retry mechanism on delivery failure"""
        ws_service = WebSocketService()
        
        with patch.object(ws_service, '_send_message') as mock_send:
            # First attempt fails, second succeeds
            mock_send.side_effect = [Exception("Network error"), True]
            
            result = await ws_service.send_with_retry(
                client_id="test_client",
                message={"type": "test"},
                max_retries=3
            )
            
            assert result is True
            assert mock_send.call_count == 2
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_message_broadcast_delivery(self):
        """Test broadcast message delivery to multiple clients"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        # Connect multiple clients
        clients = []
        for i in range(3):
            ws = await websockets.connect(uri)
            await ws.send(json.dumps({
                "type": "auth",
                "token": f"token_{i}"
            }))
            await ws.recv()  # Auth response
            clients.append(ws)
        
        try:
            # Send broadcast from first client
            await clients[0].send(json.dumps({
                "type": "broadcast",
                "content": "broadcast message"
            }))
            
            # All clients should receive
            received = []
            for client in clients:
                msg = await client.recv()
                data = json.loads(msg)
                if data["type"] == "broadcast":
                    received.append(data)
            
            assert len(received) == 3
            assert all(r["content"] == "broadcast message" for r in received)
        
        finally:
            for client in clients:
                await client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_message_queue_overflow_handling(self):
        """Test handling of message queue overflow"""
        ws_service = WebSocketService()
        max_queue_size = 10
        
        with patch.object(ws_service, 'MAX_QUEUE_SIZE', max_queue_size):
            # Fill queue
            for i in range(max_queue_size + 5):
                result = await ws_service.queue_message(
                    client_id="test_client",
                    message={"id": i}
                )
                
                if i < max_queue_size:
                    assert result is True
                else:
                    # Should drop or handle overflow
                    assert result is False or result == "queue_full"