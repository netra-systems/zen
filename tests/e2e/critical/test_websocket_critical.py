"""
Critical WebSocket Tests - Real-time communication essentials

Tests core WebSocket functionality that's essential for user experience.
Critical for real-time features and user interaction.

Business Value Justification (BVJ):
- Segment: All tiers (real-time features are core to UX)
- Business Goal: Enable seamless real-time user interactions
- Value Impact: Real-time messaging and status updates improve user experience
- Revenue Impact: Poor WebSocket performance leads to user frustration and churn

Test Coverage:
- WebSocket connections can be established
- Authentication works with WebSockets
- Messages can be sent and received
- Connections remain stable
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any

from tests.e2e.config import TEST_CONFIG, TEST_ENDPOINTS
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.enforce_real_services import E2EServiceValidator


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestCriticalWebSocket:
    """Critical WebSocket functionality tests using real connections"""
    
    def setup_method(self):
        """Setup with real WebSocket connections"""
        self.services_manager = RealServicesManager()
        
    def teardown_method(self):
        """Cleanup WebSocket connections"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connections can be established successfully"""
        
        connection_result = await self.services_manager.establish_websocket_connection()
        assert connection_result['connected'], f"WebSocket connection failed: {connection_result.get('error')}"
        assert connection_result.get('websocket'), "No WebSocket object returned"

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_websocket_authentication(self):
        """Test WebSocket authentication works properly"""
        
        # First establish connection
        connection_result = await self.services_manager.establish_websocket_connection()
        assert connection_result['connected'], "WebSocket connection failed"
        
        # Test authentication
        auth_result = await self.services_manager.authenticate_websocket()
        assert auth_result['authenticated'], f"WebSocket authentication failed: {auth_result.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_websocket_message_sending(self):
        """Test messages can be sent through WebSocket"""
        
        # Establish authenticated connection
        connection_result = await self.services_manager.establish_authenticated_websocket()
        assert connection_result['ready'], "WebSocket setup failed"
        
        # Send test message
        message_result = await self.services_manager.send_websocket_message({
            "type": "test_message",
            "content": "Hello WebSocket"
        })
        assert message_result['sent'], f"Message sending failed: {message_result.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical  
    @pytest.mark.asyncio
    async def test_websocket_message_receiving(self):
        """Test messages can be received through WebSocket"""
        
        # Setup WebSocket connection
        setup_result = await self.services_manager.setup_websocket_for_receiving()
        assert setup_result['ready'], "WebSocket receiver setup failed"
        
        # Trigger a message from server side
        trigger_result = await self.services_manager.trigger_server_message()
        assert trigger_result['triggered'], "Server message trigger failed"
        
        # Wait for and verify message receipt
        receive_result = await self.services_manager.wait_for_websocket_message(timeout=5)
        assert receive_result['received'], f"Message receiving failed: {receive_result.get('error')}"
        assert receive_result.get('message'), "No message content received"

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_websocket_connection_stability(self):
        """Test WebSocket connections remain stable"""
        
        # Establish connection
        connection_result = await self.services_manager.establish_websocket_connection()
        assert connection_result['connected'], "WebSocket connection failed"
        
        # Test connection stays alive for reasonable duration
        stability_result = await self.services_manager.test_websocket_stability(duration_seconds=10)
        assert stability_result['stable'], f"WebSocket connection unstable: {stability_result.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio  
    async def test_websocket_reconnection(self):
        """Test WebSocket can reconnect after disconnection"""
        
        # Establish initial connection
        initial_connection = await self.services_manager.establish_websocket_connection()
        assert initial_connection['connected'], "Initial connection failed"
        
        # Simulate disconnect
        disconnect_result = await self.services_manager.disconnect_websocket()
        assert disconnect_result['disconnected'], "Disconnect simulation failed"
        
        # Test reconnection
        reconnect_result = await self.services_manager.reconnect_websocket()
        assert reconnect_result['reconnected'], f"Reconnection failed: {reconnect_result.get('error')}"


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestCriticalWebSocketMessaging:
    """Critical WebSocket messaging patterns"""
    
    def setup_method(self):
        """Setup"""
        self.services_manager = RealServicesManager()
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_bidirectional_messaging(self):
        """Test bidirectional messaging works correctly"""
        
        # Setup bidirectional WebSocket
        setup_result = await self.services_manager.setup_bidirectional_websocket()
        assert setup_result['ready'], "Bidirectional setup failed"
        
        # Send message from client to server
        client_to_server = await self.services_manager.send_client_message("client_message")
        assert client_to_server['sent'], "Client to server message failed"
        
        # Verify server received message
        server_received = await self.services_manager.verify_server_received_message()
        assert server_received['received'], "Server did not receive client message"
        
        # Send response from server to client  
        server_to_client = await self.services_manager.send_server_response("server_response")
        assert server_to_client['sent'], "Server to client response failed"
        
        # Verify client received response
        client_received = await self.services_manager.verify_client_received_response()
        assert client_received['received'], "Client did not receive server response"

    @pytest.mark.e2e
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket handles errors gracefully"""
        
        # Setup WebSocket
        connection_result = await self.services_manager.establish_websocket_connection()
        assert connection_result['connected'], "WebSocket connection failed"
        
        # Send malformed message and verify graceful handling
        error_handling = await self.services_manager.test_malformed_message_handling()
        assert error_handling['handled_gracefully'], f"Error handling failed: {error_handling.get('error')}"
        
        # Verify connection remains stable after error
        stability_check = await self.services_manager.check_connection_stability_after_error()
        assert stability_check['stable'], "Connection unstable after error"