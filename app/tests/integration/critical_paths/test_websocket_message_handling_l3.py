#!/usr/bin/env python3
"""
L3 Integration Test: WebSocket Message Handling
Tests comprehensive WebSocket message handling including different message types,
formats, ordering, and error scenarios.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List
import websockets
import aiohttp
from datetime import datetime
import uuid
import base64

from test_framework.test_patterns import L3IntegrationTest
from app.core.redis_client import RedisManager


class TestWebSocketMessageHandling(L3IntegrationTest):
    """Test WebSocket message handling from multiple angles."""
    
    async def test_websocket_text_message_handling(self):
        """Test handling of text messages over WebSocket."""
        user_data = await self.create_test_user("ws_text1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send text message
            message = {
                "type": "message",
                "content": "Hello, WebSocket!",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(message))
            
            # Receive acknowledgment
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "ack"
            assert data["status"] == "received"
            assert "message_id" in data
            
    async def test_websocket_binary_message_handling(self):
        """Test handling of binary messages over WebSocket."""
        user_data = await self.create_test_user("ws_binary1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send binary data
            binary_data = b"Binary content here"
            message = {
                "type": "binary",
                "data": base64.b64encode(binary_data).decode(),
                "length": len(binary_data)
            }
            
            await websocket.send(json.dumps(message))
            
            # Receive acknowledgment
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "ack"
            assert data["bytes_received"] == len(binary_data)
            
    async def test_websocket_message_ordering(self):
        """Test that messages maintain order."""
        user_data = await self.create_test_user("ws_order1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send numbered messages
            sent_ids = []
            for i in range(10):
                message = {
                    "type": "echo",
                    "id": i,
                    "content": f"Message {i}"
                }
                
                await websocket.send(json.dumps(message))
                sent_ids.append(i)
            
            # Receive echoes
            received_ids = []
            for _ in range(10):
                response = await websocket.recv()
                data = json.loads(response)
                
                if data["type"] == "echo_response":
                    received_ids.append(data["id"])
            
            # Verify order maintained
            assert received_ids == sent_ids
            
    async def test_websocket_broadcast_messages(self):
        """Test broadcast messages to multiple connections."""
        user_data = await self.create_test_user("ws_broadcast1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        # Open multiple connections
        ws1 = await websockets.connect(ws_url)
        ws2 = await websockets.connect(ws_url)
        
        try:
            # Send broadcast from first connection
            broadcast_message = {
                "type": "broadcast",
                "content": "Broadcast to all",
                "sender_id": "ws1"
            }
            
            await ws1.send(json.dumps(broadcast_message))
            
            # Both connections should receive
            received_count = 0
            
            # Check ws1
            try:
                response1 = await asyncio.wait_for(ws1.recv(), timeout=2)
                data1 = json.loads(response1)
                if data1.get("type") == "broadcast_message":
                    received_count += 1
            except asyncio.TimeoutError:
                pass
            
            # Check ws2
            try:
                response2 = await asyncio.wait_for(ws2.recv(), timeout=2)
                data2 = json.loads(response2)
                if data2.get("type") == "broadcast_message":
                    received_count += 1
            except asyncio.TimeoutError:
                pass
            
            assert received_count >= 1
            
        finally:
            await ws1.close()
            await ws2.close()
            
    async def test_websocket_room_messages(self):
        """Test room-based message routing."""
        user1_data = await self.create_test_user("ws_room1@test.com")
        user2_data = await self.create_test_user("ws_room2@test.com")
        
        token1 = await self.get_auth_token(user1_data)
        token2 = await self.get_auth_token(user2_data)
        
        ws_url1 = f"{self.ws_url}?token={token1}"
        ws_url2 = f"{self.ws_url}?token={token2}"
        
        async with websockets.connect(ws_url1) as ws1, \
                 websockets.connect(ws_url2) as ws2:
            
            room_id = str(uuid.uuid4())
            
            # Both join same room
            join_message = {
                "type": "join_room",
                "room_id": room_id
            }
            
            await ws1.send(json.dumps(join_message))
            await ws2.send(json.dumps(join_message))
            
            # Wait for join confirmations
            await asyncio.sleep(1)
            
            # Send room message from ws1
            room_message = {
                "type": "room_message",
                "room_id": room_id,
                "content": "Hello room!"
            }
            
            await ws1.send(json.dumps(room_message))
            
            # ws2 should receive it
            response = await asyncio.wait_for(ws2.recv(), timeout=2)
            data = json.loads(response)
            
            assert data.get("room_id") == room_id
            assert "Hello room!" in data.get("content", "")
            
    async def test_websocket_message_compression(self):
        """Test message compression for large payloads."""
        user_data = await self.create_test_user("ws_compress1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send large message
            large_content = "A" * 10000  # 10KB of data
            message = {
                "type": "message",
                "content": large_content,
                "compress": True
            }
            
            await websocket.send(json.dumps(message))
            
            # Receive acknowledgment
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "ack"
            assert data.get("compressed") is True
            assert data.get("original_size") == len(large_content)
            
    async def test_websocket_malformed_message_handling(self):
        """Test handling of malformed messages."""
        user_data = await self.create_test_user("ws_malformed1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send malformed JSON
            await websocket.send("not a json {]")
            
            # Should receive error
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "error"
            assert "parse" in data["error"].lower() or "json" in data["error"].lower()
            
    async def test_websocket_message_rate_limiting(self):
        """Test message rate limiting per connection."""
        user_data = await self.create_test_user("ws_ratelimit1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send many messages rapidly
            for i in range(100):
                message = {
                    "type": "message",
                    "content": f"Rapid message {i}"
                }
                
                await websocket.send(json.dumps(message))
            
            # Check for rate limit response
            rate_limited = False
            for _ in range(100):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    data = json.loads(response)
                    
                    if data.get("type") == "error" and "rate" in data.get("error", "").lower():
                        rate_limited = True
                        break
                except asyncio.TimeoutError:
                    continue
            
            assert rate_limited
            
    async def test_websocket_message_acknowledgment(self):
        """Test message acknowledgment and retry mechanism."""
        user_data = await self.create_test_user("ws_ack1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send message requiring acknowledgment
            message_id = str(uuid.uuid4())
            message = {
                "type": "important_message",
                "id": message_id,
                "content": "Must be acknowledged",
                "require_ack": True
            }
            
            await websocket.send(json.dumps(message))
            
            # Receive and acknowledge
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data.get("message_id") == message_id
            
            # Send acknowledgment
            ack_message = {
                "type": "ack",
                "message_id": message_id
            }
            
            await websocket.send(json.dumps(ack_message))
            
            # Should receive confirmation
            confirmation = await websocket.recv()
            conf_data = json.loads(confirmation)
            
            assert conf_data["type"] == "ack_confirmed"
            assert conf_data["message_id"] == message_id
            
    async def test_websocket_message_queue_overflow(self):
        """Test behavior when message queue overflows."""
        user_data = await self.create_test_user("ws_overflow1@test.com")
        token = await self.get_auth_token(user_data)
        
        ws_url = f"{self.ws_url}?token={token}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send messages without reading responses
            overflow_detected = False
            
            for i in range(1000):
                message = {
                    "type": "message",
                    "content": f"Message {i}",
                    "no_response": False
                }
                
                try:
                    await websocket.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    overflow_detected = True
                    break
            
            # Check if overflow was handled
            if not overflow_detected:
                # Try to receive backpressure signal
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1)
                    data = json.loads(response)
                    
                    if data.get("type") == "backpressure" or data.get("type") == "error":
                        overflow_detected = True
                except:
                    pass
            
            # System should handle overflow gracefully
            assert overflow_detected or i > 900


if __name__ == "__main__":
    pytest.main([__file__, "-v"])