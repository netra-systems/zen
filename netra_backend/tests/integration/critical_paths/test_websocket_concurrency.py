"""
L3 Integration Test: WebSocket Concurrency
Tests WebSocket concurrent connection and message handling
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
import websockets

from netra_backend.app.config import get_config

from netra_backend.app.websocket_core import UnifiedWebSocketManager as IWebSocketService

class TestWebSocketConcurrencyL3:
    """Test WebSocket concurrency scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_connections(self):
        """Test handling multiple concurrent WebSocket connections"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        # Create multiple concurrent connections
        connections = []
        connection_tasks = []
        
        async def connect_client(client_id):
            ws = await websockets.connect(uri)
            await ws.send(json.dumps({
                "type": "auth",
                "token": f"token_{client_id}"
            }))
            response = await ws.recv()
            return ws, json.loads(response)
        
        # Connect 20 clients concurrently
        tasks = [connect_client(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 18, "Most connections should succeed"
        
        # Close connections
        for ws, _ in successful:
            await ws.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_message_processing(self):
        """Test concurrent message processing from multiple clients"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        # Connect multiple clients
        clients = []
        for i in range(5):
            ws = await websockets.connect(uri)
            await ws.send(json.dumps({
                "type": "auth",
                "token": f"token_{i}"
            }))
            await ws.recv()
            clients.append(ws)
        
        try:
            # Send messages concurrently
            async def send_messages(ws, client_id):
                for msg_id in range(10):
                    await ws.send(json.dumps({
                        "type": "message",
                        "client": client_id,
                        "id": msg_id
                    }))
            
            send_tasks = [send_messages(ws, i) for i, ws in enumerate(clients)]
            await asyncio.gather(*send_tasks)
            
            # Verify all messages processed
            # Each client should receive acknowledgments
            for ws in clients:
                ack_count = 0
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(msg)
                        if data.get("type") == "ack":
                            ack_count += 1
                except asyncio.TimeoutError:
                    pass
                
                assert ack_count > 0, "Should receive acknowledgments"
        
        finally:
            for ws in clients:
                await ws.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_connection_limit_enforcement(self):
        """Test maximum connection limit enforcement"""
        ws_service = WebSocketService()
        max_connections = 10
        
        with patch.object(ws_service, 'MAX_CONNECTIONS', max_connections):
            connections = []
            
            # Connect up to limit
            for i in range(max_connections):
                conn_id = await ws_service.connect_client(f"client_{i}")
                connections.append(conn_id)
            
            # Next connection should be rejected
            with pytest.raises(Exception) as exc_info:
                await ws_service.connect_client("overflow_client")
            
            assert "limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_race_condition_in_state_updates(self):
        """Test handling of race conditions in connection state updates"""
        ws_service = WebSocketService()
        client_id = "test_client"
        
        # Concurrent state updates
        async def update_state(new_state):
            await ws_service.update_client_state(client_id, new_state)
            return await ws_service.get_client_state(client_id)
        
        # Multiple concurrent updates
        states = ["connecting", "connected", "authenticated", "active"]
        tasks = [update_state(state) for state in states for _ in range(3)]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Final state should be consistent
        final_state = await ws_service.get_client_state(client_id)
        assert final_state in states
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_broadcast_handling(self):
        """Test concurrent broadcast message handling"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        # Connect multiple clients
        num_clients = 10
        clients = []
        
        for i in range(num_clients):
            ws = await websockets.connect(uri)
            await ws.send(json.dumps({
                "type": "auth",
                "token": f"token_{i}"
            }))
            await ws.recv()
            clients.append(ws)
        
        try:
            # Multiple clients broadcast simultaneously
            async def broadcast_from_client(ws, msg):
                await ws.send(json.dumps({
                    "type": "broadcast",
                    "content": msg
                }))
            
            broadcast_tasks = [
                broadcast_from_client(clients[i], f"msg_{i}")
                for i in range(5)
            ]
            
            await asyncio.gather(*broadcast_tasks)
            
            # Each client should receive broadcasts
            received_counts = []
            for ws in clients:
                count = 0
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(msg)
                        if data.get("type") == "broadcast":
                            count += 1
                except asyncio.TimeoutError:
                    pass
                received_counts.append(count)
            
            # All clients should receive broadcasts
            assert all(count > 0 for count in received_counts)
        
        finally:
            for ws in clients:
                await ws.close()