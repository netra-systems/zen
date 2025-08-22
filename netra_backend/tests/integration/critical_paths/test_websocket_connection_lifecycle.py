"""
L3 Integration Test: WebSocket Connection Lifecycle
Tests complete WebSocket connection lifecycle from connect to disconnect
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
import websockets

from netra_backend.app.config import get_config

from netra_backend.app.services.websocket_service import WebSocketService

class TestWebSocketConnectionLifecycleL3:
    """Test WebSocket connection lifecycle scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_websocket_initial_connection(self):
        """Test initial WebSocket connection establishment"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Connection should be established
            assert websocket.open
            
            # Should receive welcome message
            welcome = await websocket.recv()
            data = json.loads(welcome)
            assert data["type"] == "connection"
            assert data["status"] == "connected"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_websocket_authentication_required(self):
        """Test WebSocket requires authentication"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send message without auth
            await websocket.send(json.dumps({
                "type": "message",
                "content": "test"
            }))
            
            # Should receive auth required response
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "auth" in data["message"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_websocket_authentication_flow(self):
        """Test WebSocket authentication with token"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send auth message
            await websocket.send(json.dumps({
                "type": "auth",
                "token": "valid_test_token"
            }))
            
            # Should receive auth success
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "auth"
            assert data["status"] == "authenticated"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_websocket_graceful_disconnect(self):
        """Test graceful WebSocket disconnection"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send disconnect message
            await websocket.send(json.dumps({
                "type": "disconnect"
            }))
            
            # Should receive disconnect acknowledgment
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "disconnect"
            assert data["status"] == "disconnecting"
            
            # Connection should close
            await websocket.wait_closed()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_websocket_reconnection_handling(self):
        """Test WebSocket reconnection with session recovery"""
        uri = f"ws://localhost:{settings.WS_PORT}/ws"
        session_id = None
        
        # Initial connection
        async with websockets.connect(uri) as ws1:
            await ws1.send(json.dumps({
                "type": "auth",
                "token": "valid_test_token"
            }))
            
            response = await ws1.recv()
            data = json.loads(response)
            session_id = data.get("session_id")
        
        # Reconnect with session
        async with websockets.connect(uri) as ws2:
            await ws2.send(json.dumps({
                "type": "reconnect",
                "session_id": session_id
            }))
            
            response = await ws2.recv()
            data = json.loads(response)
            assert data["type"] == "reconnect"
            assert data["status"] == "restored"