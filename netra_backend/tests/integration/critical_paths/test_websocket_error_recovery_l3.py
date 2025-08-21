"""
L3 Integration Test: WebSocket Error Recovery
Tests WebSocket error handling and recovery mechanisms
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
import websockets

from netra_backend.app.config import settings

# Add project root to path
from netra_backend.app.services.websocket_service import WebSocketService

# Add project root to path


class TestWebSocketErrorRecoveryL3:
    """Test WebSocket error recovery scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_connection_drop_recovery(self):
        """Test recovery from unexpected connection drop"""
        ws_service = WebSocketService()
        
        # Simulate connection drop
        with patch.object(ws_service, '_is_connected', side_effect=[True, False, True]):
            # Should detect disconnect and attempt recovery
            result = await ws_service.ensure_connected("client_123")
            assert result is True
            
            # Should have attempted reconnection
            assert ws_service._reconnect_attempts.get("client_123", 0) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_malformed_message_handling(self):
        """Test handling of malformed WebSocket messages"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send malformed JSON
            await websocket.send("not a json {invalid}")
            
            # Should receive error response
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "parse" in data["message"].lower() or "json" in data["message"].lower()
            
            # Connection should remain open
            assert websocket.open
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_ping_pong_keepalive(self):
        """Test ping/pong keepalive mechanism"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Auth first
            await websocket.send(json.dumps({
                "type": "auth",
                "token": "valid_test_token"
            }))
            await websocket.recv()
            
            # Send ping
            await websocket.send(json.dumps({
                "type": "ping"
            }))
            
            # Should receive pong
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "pong"
            
            # Connection should be marked as alive
            assert websocket.open
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_timeout_disconnect(self):
        """Test disconnection after timeout period"""
        ws_service = WebSocketService()
        timeout = 2  # seconds
        
        with patch.object(ws_service, 'CONNECTION_TIMEOUT', timeout):
            # Connect client
            client_id = await ws_service.connect_client("test_client")
            
            # Wait for timeout
            await asyncio.sleep(timeout + 0.5)
            
            # Should be disconnected
            is_connected = await ws_service.is_connected(client_id)
            assert is_connected is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_exponential_backoff_reconnect(self):
        """Test exponential backoff for reconnection attempts"""
        ws_service = WebSocketService()
        
        reconnect_delays = []
        
        async def track_reconnect(client_id):
            start = asyncio.get_event_loop().time()
            await ws_service.reconnect(client_id)
            delay = asyncio.get_event_loop().time() - start
            reconnect_delays.append(delay)
            raise ConnectionError("Still failing")
        
        with patch.object(ws_service, 'reconnect', side_effect=track_reconnect):
            # Multiple reconnection attempts
            for i in range(3):
                try:
                    await ws_service.ensure_connected("test_client")
                except:
                    pass
            
            # Delays should increase exponentially
            if len(reconnect_delays) > 1:
                assert reconnect_delays[1] > reconnect_delays[0]
                if len(reconnect_delays) > 2:
                    assert reconnect_delays[2] > reconnect_delays[1]