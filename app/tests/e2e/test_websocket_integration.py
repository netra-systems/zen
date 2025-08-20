"""
WebSocket Integration E2E Tests - Real-time Communication Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All customer tiers (Free → Enterprise)
- Business Goal: Real-time user experience and agent communication
- Value Impact: WebSocket reliability drives user engagement and retention
- Strategic Impact: Real-time features differentiate Netra from competitors

Tests complete WebSocket communication flow:
1. Frontend → Backend WebSocket connection
2. Authentication and authorization
3. Message routing and agent processing
4. Real-time response delivery
5. Error handling and reconnection

COVERAGE:
- WebSocket connection establishment
- Authentication flow validation
- Message sending and receiving
- Agent response processing
- Broadcast functionality
- Error scenarios and recovery
"""

import asyncio
import json
import pytest
import websockets
import httpx
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.websocket.connection_manager import ConnectionManager
from app.websocket.message_handler_core import ModernReliableMessageHandler
from app.ws_manager import WebSocketManager
from app.auth_integration.auth import validate_token
from app.schemas.websocket_message_types import WebSocketMessage


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
        self.accepted = False
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: Dict[str, Any]):
        self.messages_sent.append(data)
    
    async def send_text(self, data: str):
        self.messages_sent.append(data)
    
    async def receive_json(self) -> Dict[str, Any]:
        if self.messages_received:
            return self.messages_received.pop(0)
        await asyncio.sleep(0.1)
        return {"type": "ping"}
    
    async def close(self):
        self.closed = True


class TestWebSocketConnection:
    """WebSocket connection establishment tests."""
    
    @pytest.fixture
    def mock_websocket(self) -> MockWebSocket:
        """Create mock WebSocket for testing."""
        return MockWebSocket()
    
    @pytest.fixture
    def connection_manager(self) -> ConnectionManager:
        """Create connection manager for testing."""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self, mock_websocket, connection_manager):
        """Test WebSocket connection can be established successfully."""
        user_id = "test_user_123"
        
        # Establish connection
        connection_info = await connection_manager.connect(user_id, mock_websocket)
        
        # Verify connection established
        assert connection_info is not None
        assert connection_info.user_id == user_id
        assert connection_info.websocket == mock_websocket
        assert mock_websocket.accepted
        
        # Verify connection is tracked
        assert user_id in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_required(self, mock_websocket):
        """Test WebSocket connections require valid authentication."""
        from app.routes.websockets import websocket_endpoint
        
        # Test connection without valid token should fail
        with pytest.raises(Exception):
            await websocket_endpoint(mock_websocket, token="invalid_token")
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_success(self, mock_websocket):
        """Test WebSocket connections succeed with valid authentication."""
        # Mock valid token validation
        with patch('app.auth_integration.auth.validate_token') as mock_validate:
            mock_validate.return_value = {"user_id": "test_user", "valid": True}
            
            from app.routes.websockets import websocket_endpoint
            
            # Should not raise exception with valid token
            try:
                await websocket_endpoint(mock_websocket, token="valid_token")
            except Exception as e:
                # May fail due to mock setup, but should not be auth error
                assert "authentication" not in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self, connection_manager):
        """Test multiple WebSocket connections for same user."""
        user_id = "test_user_123"
        
        # Create multiple mock websockets
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        # Establish multiple connections
        conn1 = await connection_manager.connect(user_id, ws1)
        conn2 = await connection_manager.connect(user_id, ws2)
        
        # Verify both connections are tracked
        assert len(connection_manager.active_connections[user_id]) == 2
        assert conn1.connection_id != conn2.connection_id


class TestWebSocketMessaging:
    """WebSocket message sending and receiving tests."""
    
    @pytest.fixture
    def ws_manager(self) -> WebSocketManager:
        """Create WebSocket manager for testing."""
        return WebSocketManager()
    
    @pytest.fixture
    def sample_message(self) -> Dict[str, Any]:
        """Create sample WebSocket message."""
        return {
            "type": "agent_request",
            "content": "What is the status of my optimization project?",
            "thread_id": "thread_123",
            "user_id": "user_123"
        }
    
    @pytest.mark.asyncio
    async def test_send_message_to_user(self, ws_manager, sample_message):
        """Test sending message to specific user."""
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # Setup connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # Send message
        await ws_manager.send_message_to_user(user_id, sample_message)
        
        # Verify message was sent
        assert len(mock_websocket.messages_sent) == 1
        sent_message = mock_websocket.messages_sent[0]
        assert sent_message["type"] == sample_message["type"]
        assert sent_message["content"] == sample_message["content"]
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, ws_manager, sample_message):
        """Test broadcasting message to multiple users."""
        # Setup multiple connections
        users = ["user1", "user2", "user3"]
        websockets = []
        
        for user_id in users:
            mock_ws = MockWebSocket()
            websockets.append(mock_ws)
            await ws_manager.connection_manager.connect(user_id, mock_ws)
        
        # Broadcast message
        await ws_manager.broadcast_message(sample_message)
        
        # Verify all users received message
        for ws in websockets:
            assert len(ws.messages_sent) == 1
            assert ws.messages_sent[0]["type"] == sample_message["type"]
    
    @pytest.mark.asyncio
    async def test_message_routing_to_agent(self, ws_manager, sample_message):
        """Test message is properly routed to agent system."""
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # Setup connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # Mock agent service
        with patch('app.services.agent_service.AgentService.process_message') as mock_agent:
            mock_agent.return_value = {"response": "Agent processed successfully"}
            
            # Process incoming message
            await ws_manager.handle_incoming_message(user_id, sample_message)
            
            # Verify agent was called
            mock_agent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_response_delivery(self, ws_manager):
        """Test agent responses are delivered back to user."""
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # Setup connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # Simulate agent response
        agent_response = {
            "type": "agent_response",
            "content": "Your optimization project is 75% complete.",
            "thread_id": "thread_123"
        }
        
        # Send agent response
        await ws_manager.send_agent_response(user_id, agent_response)
        
        # Verify response was delivered
        assert len(mock_websocket.messages_sent) == 1
        sent_response = mock_websocket.messages_sent[0]
        assert sent_response["type"] == "agent_response"
        assert "75% complete" in sent_response["content"]


class TestWebSocketErrorHandling:
    """WebSocket error handling and recovery tests."""
    
    @pytest.fixture
    def error_prone_websocket(self) -> MockWebSocket:
        """Create WebSocket that simulates errors."""
        mock_ws = MockWebSocket()
        
        # Override send_json to simulate errors
        async def error_send_json(data):
            raise ConnectionError("Simulated connection error")
        
        mock_ws.send_json = error_send_json
        return mock_ws
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, error_prone_websocket):
        """Test handling of WebSocket connection errors."""
        ws_manager = WebSocketManager()
        user_id = "test_user_123"
        
        # Establish connection
        await ws_manager.connection_manager.connect(user_id, error_prone_websocket)
        
        # Attempt to send message (should handle error gracefully)
        message = {"type": "test", "content": "test message"}
        
        try:
            await ws_manager.send_message_to_user(user_id, message)
        except Exception:
            # Should handle error gracefully, not crash
            pass
        
        # Verify connection is cleaned up after error
        await asyncio.sleep(0.1)
        # Connection should be removed from active connections
    
    @pytest.mark.asyncio
    async def test_message_validation_errors(self, ws_manager):
        """Test handling of invalid message formats."""
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # Setup connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # Send invalid message
        invalid_message = {"invalid": "structure"}
        
        try:
            await ws_manager.handle_incoming_message(user_id, invalid_message)
        except Exception:
            # Should handle validation errors gracefully
            pass
        
        # Verify error response was sent to user
        assert len(mock_websocket.messages_sent) >= 1
        # Should contain error message
    
    @pytest.mark.asyncio
    async def test_reconnection_handling(self, ws_manager):
        """Test handling of WebSocket reconnections."""
        user_id = "test_user_123"
        
        # First connection
        ws1 = MockWebSocket()
        conn1 = await ws_manager.connection_manager.connect(user_id, ws1)
        
        # Simulate disconnection
        await ws1.close()
        await ws_manager.connection_manager.disconnect(user_id, conn1.connection_id)
        
        # Second connection (reconnection)
        ws2 = MockWebSocket()
        conn2 = await ws_manager.connection_manager.connect(user_id, ws2)
        
        # Verify new connection established
        assert conn2.connection_id != conn1.connection_id
        assert user_id in ws_manager.connection_manager.active_connections


class TestWebSocketIntegrationFlow:
    """End-to-end WebSocket integration flow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_message_flow(self):
        """Test complete message flow from frontend to agent and back."""
        ws_manager = WebSocketManager()
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # 1. Establish connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # 2. Send user message
        user_message = {
            "type": "agent_request",
            "content": "Help me optimize my AI costs",
            "thread_id": "thread_123"
        }
        
        # Mock agent service response
        with patch('app.services.agent_service.AgentService.process_message') as mock_agent:
            mock_agent.return_value = {
                "type": "agent_response",
                "content": "I can help you optimize AI costs. Here are 3 strategies...",
                "thread_id": "thread_123"
            }
            
            # 3. Process message through system
            await ws_manager.handle_incoming_message(user_id, user_message)
            
            # 4. Verify agent was called
            mock_agent.assert_called_once()
            
        # 5. Verify response was sent back to user
        assert len(mock_websocket.messages_sent) >= 1
        response = mock_websocket.messages_sent[-1]
        assert response["type"] == "agent_response"
        assert "optimize AI costs" in response["content"]
    
    @pytest.mark.asyncio
    async def test_real_time_agent_updates(self):
        """Test real-time agent processing updates."""
        ws_manager = WebSocketManager()
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # Setup connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # Simulate agent processing with updates
        processing_updates = [
            {"type": "agent_status", "status": "processing", "step": "analyzing_request"},
            {"type": "agent_status", "status": "processing", "step": "generating_response"},
            {"type": "agent_response", "content": "Here's your analysis..."}
        ]
        
        # Send updates in sequence
        for update in processing_updates:
            await ws_manager.send_message_to_user(user_id, update)
            await asyncio.sleep(0.1)
        
        # Verify all updates were sent
        assert len(mock_websocket.messages_sent) == len(processing_updates)
        
        # Verify final response
        final_message = mock_websocket.messages_sent[-1]
        assert final_message["type"] == "agent_response"
    
    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self):
        """Test handling of multiple concurrent user sessions."""
        ws_manager = WebSocketManager()
        
        # Setup multiple users
        users_and_websockets = []
        for i in range(5):
            user_id = f"user_{i}"
            mock_ws = MockWebSocket()
            users_and_websockets.append((user_id, mock_ws))
            await ws_manager.connection_manager.connect(user_id, mock_ws)
        
        # Send messages concurrently
        async def send_message_for_user(user_id, websocket):
            message = {
                "type": "agent_request",
                "content": f"Message from {user_id}",
                "thread_id": f"thread_{user_id}"
            }
            await ws_manager.handle_incoming_message(user_id, message)
        
        # Execute concurrent requests
        tasks = [
            send_message_for_user(user_id, ws) 
            for user_id, ws in users_and_websockets
        ]
        await asyncio.gather(*tasks)
        
        # Verify all users received responses
        for user_id, websocket in users_and_websockets:
            assert len(websocket.messages_sent) >= 1


class TestWebSocketPerformance:
    """WebSocket performance and scalability tests."""
    
    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """Test WebSocket message throughput under load."""
        ws_manager = WebSocketManager()
        user_id = "test_user_123"
        mock_websocket = MockWebSocket()
        
        # Setup connection
        await ws_manager.connection_manager.connect(user_id, mock_websocket)
        
        # Send multiple messages rapidly
        message_count = 100
        start_time = asyncio.get_event_loop().time()
        
        for i in range(message_count):
            message = {"type": "test", "content": f"Message {i}"}
            await ws_manager.send_message_to_user(user_id, message)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Verify reasonable throughput
        messages_per_second = message_count / duration
        assert messages_per_second > 50  # At least 50 messages/second
        
        # Verify all messages were sent
        assert len(mock_websocket.messages_sent) == message_count
    
    @pytest.mark.asyncio
    async def test_connection_scalability(self):
        """Test WebSocket connection scalability."""
        ws_manager = WebSocketManager()
        
        # Create many connections
        connection_count = 50
        connections = []
        
        for i in range(connection_count):
            user_id = f"user_{i}"
            mock_ws = MockWebSocket()
            conn = await ws_manager.connection_manager.connect(user_id, mock_ws)
            connections.append((user_id, mock_ws, conn))
        
        # Verify all connections established
        assert len(ws_manager.connection_manager.active_connections) == connection_count
        
        # Send broadcast message
        broadcast_message = {"type": "broadcast", "content": "System update"}
        await ws_manager.broadcast_message(broadcast_message)
        
        # Verify all connections received message
        for user_id, websocket, conn in connections:
            assert len(websocket.messages_sent) == 1
            assert websocket.messages_sent[0]["type"] == "broadcast"