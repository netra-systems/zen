#!/usr/bin/env python3
"""
L3 Integration Test: WebSocket Basic Connection Flow
Tests fundamental WebSocket connection establishment, authentication,
and basic message exchange from different angles.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, Optional
import aiohttp
import websockets
from datetime import datetime
import uuid

from test_framework.test_patterns import L3IntegrationTest
from app.core.redis_client import RedisManager
from app.websocket.manager import WebSocketManager


class TestWebSocketBasicConnection(L3IntegrationTest):
    """Test WebSocket basic connection flows from multiple angles."""
    
    async def test_successful_websocket_connection(self):
        """Test successful WebSocket connection with valid auth."""
        # Get auth token
        user_data = await self.create_test_user("ws_basic1@test.com")
        token = await self.get_auth_token(user_data)
        
        # Connect to WebSocket
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send initial ping
            await websocket.send(json.dumps({
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Receive pong
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "pong"
            assert "timestamp" in data
            
    async def test_websocket_connection_without_auth(self):
        """Test WebSocket connection attempt without authentication."""
        ws_url = self.ws_url  # No token
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url):
                pass
                
        assert exc_info.value.status_code == 401
        
    async def test_websocket_connection_with_invalid_token(self):
        """Test WebSocket connection with invalid auth token."""
        ws_url = f"{self.ws_url}?token=invalid_token_here"
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url):
                pass
                
        assert exc_info.value.status_code == 401
        
    async def test_websocket_connection_with_expired_token(self):
        """Test WebSocket connection with expired auth token."""
        # Create expired token (mock or use test token)
        expired_token = self.create_expired_token()
        ws_url = f"{self.ws_url}?token={expired_token}"
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url):
                pass
                
        assert exc_info.value.status_code == 401
        
    async def test_websocket_multiple_connections_same_user(self):
        """Test multiple WebSocket connections from same user."""
        user_data = await self.create_test_user("ws_multi@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        # Open multiple connections
        websockets_list = []
        for i in range(3):
            ws = await websockets.connect(ws_url)
            websockets_list.append(ws)
            
        try:
            # Send message from each connection
            for i, ws in enumerate(websockets_list):
                await ws.send(json.dumps({
                    "type": "ping",
                    "connection_id": i
                }))
            
            # Verify all connections receive responses
            for i, ws in enumerate(websockets_list):
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "pong"
                
        finally:
            # Clean up connections
            for ws in websockets_list:
                await ws.close()
                
    async def test_websocket_connection_limit_per_user(self):
        """Test connection limit enforcement per user."""
        user_data = await self.create_test_user("ws_limit@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        max_connections = 10  # Assumed limit
        
        connections = []
        try:
            # Try to open more than allowed connections
            for i in range(max_connections + 5):
                try:
                    ws = await websockets.connect(ws_url)
                    connections.append(ws)
                except websockets.exceptions.InvalidStatusCode as e:
                    # Should fail after reaching limit
                    assert i >= max_connections
                    assert e.status_code == 429  # Too Many Requests
                    break
                    
        finally:
            for ws in connections:
                await ws.close()
                
    async def test_websocket_heartbeat_mechanism(self):
        """Test WebSocket heartbeat/keepalive mechanism."""
        user_data = await self.create_test_user("ws_heartbeat@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Wait for heartbeat
            heartbeat_received = False
            
            # Set timeout for receiving heartbeat
            try:
                async with asyncio.timeout(30):  # 30 second timeout
                    while not heartbeat_received:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if data.get("type") == "heartbeat":
                            heartbeat_received = True
                            
                            # Respond to heartbeat
                            await websocket.send(json.dumps({
                                "type": "heartbeat_ack",
                                "timestamp": datetime.utcnow().isoformat()
                            }))
                            
            except asyncio.TimeoutError:
                pytest.fail("No heartbeat received within timeout")
                
            assert heartbeat_received
            
    async def test_websocket_reconnection_flow(self):
        """Test WebSocket reconnection after disconnect."""
        user_data = await self.create_test_user("ws_reconnect@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        connection_id = str(uuid.uuid4())
        
        # First connection
        async with websockets.connect(ws_url) as websocket:
            await websocket.send(json.dumps({
                "type": "identify",
                "connection_id": connection_id
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            assert data.get("status") == "identified"
            
        # Simulate disconnect and reconnect
        await asyncio.sleep(1)
        
        # Reconnect with same connection_id
        async with websockets.connect(ws_url) as websocket:
            await websocket.send(json.dumps({
                "type": "reconnect",
                "connection_id": connection_id
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            # Should recognize previous connection
            assert data.get("status") == "reconnected"
            assert data.get("connection_id") == connection_id
            
    async def test_websocket_message_size_limits(self):
        """Test WebSocket message size limit enforcement."""
        user_data = await self.create_test_user("ws_size@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send normal size message
            normal_message = {
                "type": "message",
                "content": "A" * 1000  # 1KB
            }
            
            await websocket.send(json.dumps(normal_message))
            response = await websocket.recv()
            assert json.loads(response).get("status") == "received"
            
            # Send oversized message
            oversized_message = {
                "type": "message",
                "content": "B" * (1024 * 1024 * 10)  # 10MB
            }
            
            try:
                await websocket.send(json.dumps(oversized_message))
                response = await websocket.recv()
                data = json.loads(response)
                
                # Should get error response
                assert data.get("type") == "error"
                assert "size limit" in data.get("error", "").lower()
                
            except websockets.exceptions.ConnectionClosed:
                # Connection might be closed for oversized message
                pass
                
    async def test_websocket_protocol_upgrade(self):
        """Test proper WebSocket protocol upgrade from HTTP."""
        user_data = await self.create_test_user("ws_upgrade@test.com")
        token = await self.get_auth_token(user_data)
        
        # Manual HTTP upgrade request
        async with aiohttp.ClientSession() as session:
            headers = {
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Version": "13",
                "Authorization": f"Bearer {token}"
            }
            
            async with session.get(
                self.ws_url.replace("ws://", "http://"),
                headers=headers
            ) as resp:
                # Should get 101 Switching Protocols
                assert resp.status == 101
                assert resp.headers.get("Upgrade") == "websocket"
                
    async def test_websocket_concurrent_message_handling(self):
        """Test concurrent message handling on WebSocket."""
        user_data = await self.create_test_user("ws_concurrent@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send multiple messages concurrently
            messages = []
            for i in range(10):
                messages.append(json.dumps({
                    "type": "echo",
                    "id": i,
                    "content": f"Message {i}"
                }))
            
            # Send all messages without waiting
            send_tasks = [websocket.send(msg) for msg in messages]
            await asyncio.gather(*send_tasks)
            
            # Receive all responses
            responses = []
            for _ in range(10):
                response = await websocket.recv()
                responses.append(json.loads(response))
            
            # Verify all messages were processed
            received_ids = {r.get("id") for r in responses}
            expected_ids = set(range(10))
            assert received_ids == expected_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])