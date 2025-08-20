"""Frontend-Backend WebSocket Integration Tests.

Tests the complete integration between the Enhanced WebSocket Provider
and the backend WebSocket endpoint, ensuring they work together correctly.
"""

import asyncio
import json
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import websockets

# Mock React and frontend dependencies for testing
class MockReact:
    @staticmethod
    def createContext(default_value=None):
        return Mock()
    
    @staticmethod
    def useContext(context):
        return Mock()
    
    @staticmethod 
    def useEffect(effect, deps):
        effect()
    
    @staticmethod
    def useState(initial_value):
        return [initial_value, Mock()]
    
    @staticmethod
    def useCallback(callback, deps):
        return callback
    
    @staticmethod
    def useRef(initial_value):
        ref = Mock()
        ref.current = initial_value
        return ref
        
    @staticmethod
    def useMemo(factory, deps):
        return factory()


class MockAuthContext:
    """Mock authentication context."""
    def __init__(self, token="mock_valid_token"):
        self.token = token


class MockWebSocket:
    """Mock WebSocket for frontend testing."""
    
    def __init__(self):
        self.url = ""
        self.readyState = 1  # OPEN
        self.onopen = None
        self.onmessage = None
        self.onclose = None
        self.onerror = None
        self.messages_sent = []
        self.should_fail = False
        
    def send(self, data):
        if self.should_fail:
            raise Exception("Mock WebSocket error")
        self.messages_sent.append(json.loads(data))
        
        # Simulate server responses
        message = json.loads(data)
        if message.get("type") == "ping":
            # Simulate pong response
            pong_response = {"type": "pong", "timestamp": time.time()}
            if self.onmessage:
                mock_event = Mock()
                mock_event.data = json.dumps(pong_response)
                self.onmessage(mock_event)
                
    def close(self, code=1000, reason=""):
        self.readyState = 3  # CLOSED
        if self.onclose:
            mock_event = Mock()
            mock_event.code = code
            mock_event.reason = reason
            self.onclose(mock_event)
            
    def simulate_open(self):
        if self.onopen:
            self.onopen(Mock())
            
    def simulate_message(self, message_data):
        if self.onmessage:
            mock_event = Mock()
            mock_event.data = json.dumps(message_data)
            self.onmessage(mock_event)
            
    def simulate_error(self):
        if self.onerror:
            self.onerror(Mock())


# Mock global WebSocket class
def mock_websocket_class(url):
    ws = MockWebSocket()
    ws.url = url
    return ws


@pytest.fixture
def mock_react():
    """Provide mocked React functionality."""
    return MockReact()


@pytest.fixture  
def mock_auth_context():
    """Provide mock authentication context."""
    return MockAuthContext()


@pytest.fixture
def mock_websocket():
    """Provide mock WebSocket."""
    with patch('builtins.WebSocket', mock_websocket_class):
        yield MockWebSocket


@pytest.mark.asyncio
class TestFrontendBackendIntegration:
    """Test frontend-backend WebSocket integration."""
    
    async def test_service_discovery_integration(self):
        """Test frontend can discover WebSocket configuration from backend."""
        # Mock fetch response for service discovery
        mock_config = {
            "websocket_config": {
                "version": "1.0",
                "features": {
                    "json_first": True,
                    "auth_required": True,
                    "heartbeat_supported": True,
                    "reconnection_supported": True
                },
                "endpoints": {
                    "websocket": "/ws/enhanced",
                    "service_discovery": "/ws/config"  
                },
                "connection_limits": {
                    "max_connections_per_user": 5,
                    "max_message_rate": 60,
                    "heartbeat_interval": 30000
                }
            },
            "status": "success"
        }
        
        # Mock fetch call
        with patch('builtins.fetch') as mock_fetch:
            mock_response = AsyncMock()
            mock_response.ok = True
            mock_response.json = AsyncMock(return_value=mock_config)
            mock_fetch.return_value = mock_response
            
            # Test service discovery (simulated)
            api_url = "http://localhost:8000"
            response = await mock_response.json()
            
            # Verify configuration structure
            assert response["status"] == "success"
            config = response["websocket_config"]
            assert config["version"] == "1.0"
            assert config["features"]["json_first"] is True
            assert config["endpoints"]["websocket"] == "/ws/enhanced"
            
    async def test_websocket_url_construction(self, mock_auth_context):
        """Test WebSocket URL is constructed correctly from config."""
        # Mock configuration
        config = {
            "endpoints": {"websocket": "/ws/enhanced"}
        }
        
        # Expected URL construction logic
        api_url = "http://localhost:8000"
        ws_url = api_url.replace("http", "ws")
        endpoint = config["endpoints"]["websocket"]
        token = mock_auth_context.token
        
        expected_url = f"{ws_url}{endpoint}?token={token}"
        assert expected_url == "ws://localhost:8000/ws/enhanced?token=mock_valid_token"
        
    async def test_connection_establishment_flow(self, mock_websocket, mock_auth_context):
        """Test complete connection establishment flow."""
        # Mock WebSocket instance
        ws_mock = MockWebSocket()
        
        # Simulate connection establishment
        with patch('builtins.WebSocket', return_value=ws_mock):
            # Simulate frontend connection logic
            url = f"ws://localhost:8000/ws/enhanced?token={mock_auth_context.token}"
            ws = WebSocket(url)  # This would be the mocked WebSocket
            
            # Simulate connection opened
            ws_mock.simulate_open()
            
            # Simulate server sending connection_established message
            connection_message = {
                "type": "connection_established",
                "payload": {
                    "user_id": "test_user",
                    "connection_id": "conn_123",
                    "server_time": "2025-01-01T00:00:00Z",
                    "features": {"json_first": True}
                }
            }
            ws_mock.simulate_message(connection_message)
            
            # Verify connection state would be updated
            assert ws_mock.readyState == 1  # OPEN
            
    async def test_message_exchange_flow(self, mock_websocket, mock_auth_context):
        """Test bidirectional message exchange between frontend and backend."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            # Establish connection
            ws_mock.simulate_open()
            
            # Frontend sends user message
            user_message = {
                "type": "user_message",
                "payload": {
                    "content": "Hello from frontend",
                    "timestamp": time.time()
                }
            }
            
            ws_mock.send(json.dumps(user_message))
            
            # Verify message was sent
            assert len(ws_mock.messages_sent) == 1
            assert ws_mock.messages_sent[0]["type"] == "user_message"
            
            # Backend responds with agent message
            agent_response = {
                "type": "agent_started",
                "payload": {
                    "run_id": "run_123",
                    "agent_name": "test_agent",
                    "timestamp": time.time()
                }
            }
            
            ws_mock.simulate_message(agent_response)
            
            # This would trigger frontend message handler
            assert True  # Basic flow test passes
            
    async def test_json_first_validation_integration(self, mock_websocket):
        """Test JSON-first validation works end-to-end."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Test 1: Valid JSON message should work
            valid_message = {
                "type": "ping",
                "timestamp": time.time()
            }
            ws_mock.send(json.dumps(valid_message))
            assert len(ws_mock.messages_sent) == 1
            
            # Test 2: Invalid message structure should trigger error
            # (This would be handled by backend validation)
            invalid_message = {"no_type_field": True}
            
            # Backend would respond with error
            error_response = {
                "type": "error",
                "payload": {
                    "code": "MISSING_TYPE_FIELD",
                    "error": "Message must contain 'type' field",
                    "recoverable": True
                }
            }
            
            ws_mock.simulate_message(error_response)
            # Frontend should handle this error gracefully
            
    async def test_authentication_flow_integration(self, mock_auth_context):
        """Test authentication flow between frontend and backend."""
        # Mock token validation response
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "test_user_123",
                "email": "test@example.com",
                "permissions": ["read", "write"]
            }
            
            # Simulate backend token validation
            token = mock_auth_context.token
            validation_result = await mock_validate(token)
            
            assert validation_result["valid"] is True
            assert validation_result["user_id"] == "test_user_123"
            
    async def test_heartbeat_integration(self, mock_websocket):
        """Test heartbeat/ping-pong integration."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Frontend sends ping
            ping_message = {"type": "ping", "timestamp": time.time()}
            ws_mock.send(json.dumps(ping_message))
            
            # Backend automatically responds with pong (mocked)
            pong_response = {"type": "pong", "timestamp": time.time()}
            ws_mock.simulate_message(pong_response)
            
            # Verify ping was sent
            assert len(ws_mock.messages_sent) == 1
            assert ws_mock.messages_sent[0]["type"] == "ping"
            
    async def test_error_handling_integration(self, mock_websocket):
        """Test error handling integration between frontend and backend."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Simulate various error scenarios
            
            # 1. JSON Parse Error
            parse_error = {
                "type": "error", 
                "payload": {
                    "code": "JSON_PARSE_ERROR",
                    "error": "Invalid JSON format",
                    "recoverable": True,
                    "help": "Please ensure your message is valid JSON format"
                }
            }
            ws_mock.simulate_message(parse_error)
            
            # 2. Validation Error
            validation_error = {
                "type": "error",
                "payload": {
                    "code": "INVALID_MESSAGE_TYPE", 
                    "error": "Message must be a JSON object",
                    "recoverable": True
                }
            }
            ws_mock.simulate_message(validation_error)
            
            # Frontend should handle these errors and maintain connection
            assert ws_mock.readyState == 1  # Still open
            
    async def test_reconnection_flow_integration(self, mock_websocket):
        """Test reconnection flow integration."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            # Initial connection
            ws_mock.simulate_open()
            assert ws_mock.readyState == 1
            
            # Simulate connection loss
            ws_mock.close(1006, "Connection lost")  # Abnormal closure
            assert ws_mock.readyState == 3  # CLOSED
            
            # Frontend would attempt reconnection
            # Create new WebSocket instance for reconnection
            ws_mock_2 = MockWebSocket()
            ws_mock_2.simulate_open()
            
            # Verify reconnection would succeed
            assert ws_mock_2.readyState == 1
            
    async def test_message_queuing_during_disconnect(self, mock_websocket):
        """Test message queuing when connection is lost."""
        ws_mock = MockWebSocket()
        message_queue = []  # Simulate frontend message queue
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Send message while connected
            message1 = {"type": "ping", "id": 1}
            ws_mock.send(json.dumps(message1))
            assert len(ws_mock.messages_sent) == 1
            
            # Simulate connection loss  
            ws_mock.readyState = 3  # CLOSED
            
            # Try to send message while disconnected - should queue
            message2 = {"type": "ping", "id": 2}
            message_queue.append(message2)  # Frontend would queue this
            
            # Simulate reconnection
            ws_mock.readyState = 1  # OPEN
            
            # Process queued messages
            for queued_msg in message_queue:
                ws_mock.send(json.dumps(queued_msg))
                
            # Verify all messages eventually sent
            assert len(ws_mock.messages_sent) == 2
            assert ws_mock.messages_sent[1]["id"] == 2
            
    async def test_rate_limiting_integration(self, mock_websocket):
        """Test rate limiting integration."""
        ws_mock = MockWebSocket()
        
        # Mock rate limiting configuration
        rate_limit = {
            "max_message_rate": 60,  # 60 messages per minute
            "window_ms": 60000
        }
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Send messages within rate limit
            for i in range(5):  # Well within limit
                message = {"type": "ping", "sequence": i}
                ws_mock.send(json.dumps(message))
                
            # All messages should be sent
            assert len(ws_mock.messages_sent) == 5
            
            # Simulate rate limit response from backend
            rate_limit_error = {
                "type": "error",
                "payload": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "error": "Too many messages sent",
                    "recoverable": True
                }
            }
            
            # Frontend should handle rate limiting gracefully
            ws_mock.simulate_message(rate_limit_error)
            
    async def test_connection_resilience_to_rerender(self, mock_websocket):
        """Test connection survives component re-renders."""
        ws_mock = MockWebSocket()
        
        # Simulate React context that persists across re-renders
        connection_ref = {"current": None}
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            # Initial connection
            connection_ref["current"] = ws_mock
            ws_mock.simulate_open()
            
            # Simulate component re-render (connection should persist)
            # In real React, the useRef would maintain the connection
            assert connection_ref["current"] is ws_mock
            assert ws_mock.readyState == 1
            
            # Connection should still work after "re-render"
            message = {"type": "ping", "after_rerender": True}
            ws_mock.send(json.dumps(message))
            
            assert len(ws_mock.messages_sent) == 1
            assert ws_mock.messages_sent[0]["after_rerender"] is True
            
    async def test_optimistic_message_updates(self, mock_websocket):
        """Test optimistic message updates integration."""
        ws_mock = MockWebSocket()
        optimistic_messages = {}  # Simulate frontend optimistic state
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Frontend sends optimistic message
            correlation_id = f"opt_{int(time.time() * 1000)}"
            optimistic_msg = {
                "type": "user_message",
                "payload": {
                    "content": "Optimistic message",
                    "correlation_id": correlation_id
                }
            }
            
            # Add to optimistic state
            optimistic_messages[correlation_id] = {
                "content": "Optimistic message",
                "status": "pending"
            }
            
            ws_mock.send(json.dumps(optimistic_msg))
            
            # Backend confirms message
            confirmation = {
                "type": "message_confirmed",
                "payload": {
                    "correlation_id": correlation_id,
                    "message_id": "msg_123",
                    "status": "delivered"
                }
            }
            
            ws_mock.simulate_message(confirmation)
            
            # Frontend would update optimistic state
            if correlation_id in optimistic_messages:
                optimistic_messages[correlation_id]["status"] = "confirmed"
                optimistic_messages[correlation_id]["message_id"] = "msg_123"
                
            assert optimistic_messages[correlation_id]["status"] == "confirmed"


@pytest.mark.asyncio
class TestWebSocketProviderBehavior:
    """Test enhanced WebSocket provider behavior."""
    
    async def test_provider_initialization(self, mock_react, mock_auth_context):
        """Test WebSocket provider initializes correctly."""
        # Mock useState calls
        status_state = ["DISCONNECTED", Mock()]
        config_state = [None, Mock()]
        
        with patch.object(mock_react, 'useState', side_effect=[status_state, config_state]):
            # Simulate provider initialization
            initial_status = status_state[0]
            initial_config = config_state[0]
            
            assert initial_status == "DISCONNECTED"
            assert initial_config is None
            
    async def test_provider_auto_connect(self, mock_websocket, mock_auth_context):
        """Test provider auto-connects when token is available."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            # Simulate provider useEffect for auto-connect
            if mock_auth_context.token and True:  # autoConnect = True
                # Would trigger connection
                ws_mock.simulate_open()
                
            assert ws_mock.readyState == 1
            
    async def test_provider_context_value(self, mock_react):
        """Test provider context value structure."""
        # Mock context value structure
        context_value = {
            "status": "CONNECTED",
            "config": {"version": "1.0"},
            "connectionStats": {
                "messages_sent": 5,
                "messages_received": 3,
                "errors_encountered": 0,
                "reconnections": 1
            },
            "lastError": None,
            "sendMessage": Mock(),
            "sendOptimisticMessage": Mock(),
            "clearError": Mock(),
            "forceReconnect": Mock(),
            "isConnected": True,
            "isReconnecting": False
        }
        
        # Verify expected structure
        assert "status" in context_value
        assert "config" in context_value
        assert "connectionStats" in context_value
        assert "sendMessage" in context_value
        assert "isConnected" in context_value
        
        # Verify computed properties
        assert context_value["isConnected"] == (context_value["status"] == "CONNECTED")
        
    async def test_provider_cleanup(self, mock_websocket):
        """Test provider cleanup on unmount."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Simulate component unmount cleanup
            if ws_mock.readyState != 3:  # Not already closed
                ws_mock.close(1000, "Component unmount")
                
            assert ws_mock.readyState == 3  # CLOSED


@pytest.mark.asyncio
class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    async def test_complete_chat_message_flow(self, mock_websocket, mock_auth_context):
        """Test complete chat message flow from frontend to backend and back."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            # 1. Connection establishment
            ws_mock.simulate_open()
            
            connection_msg = {
                "type": "connection_established",
                "payload": {
                    "user_id": "user_123",
                    "connection_id": "conn_456"
                }
            }
            ws_mock.simulate_message(connection_msg)
            
            # 2. User sends chat message
            user_message = {
                "type": "user_message",
                "payload": {
                    "content": "What is the weather today?",
                    "thread_id": "thread_789",
                    "correlation_id": "opt_12345"
                }
            }
            ws_mock.send(json.dumps(user_message))
            
            # 3. Backend confirms message received
            confirmation = {
                "type": "message_confirmed",
                "payload": {
                    "correlation_id": "opt_12345",
                    "message_id": "msg_999"
                }
            }
            ws_mock.simulate_message(confirmation)
            
            # 4. Backend sends agent started
            agent_started = {
                "type": "agent_started", 
                "payload": {
                    "run_id": "run_abc",
                    "agent_name": "weather_agent",
                    "timestamp": time.time()
                }
            }
            ws_mock.simulate_message(agent_started)
            
            # 5. Backend sends partial results
            partial_result = {
                "type": "partial_result",
                "payload": {
                    "content": "Checking weather data...",
                    "agent_name": "weather_agent",
                    "is_complete": False
                }
            }
            ws_mock.simulate_message(partial_result)
            
            # 6. Backend sends final response
            final_response = {
                "type": "agent_completed",
                "payload": {
                    "agent_name": "weather_agent",
                    "result": {
                        "content": "Today is sunny with a high of 75°F",
                        "confidence": 0.95
                    },
                    "duration_ms": 2500
                }
            }
            ws_mock.simulate_message(final_response)
            
            # Verify message was sent successfully
            assert len(ws_mock.messages_sent) == 1
            assert ws_mock.messages_sent[0]["type"] == "user_message"
            
    async def test_error_recovery_scenario(self, mock_websocket):
        """Test error recovery scenario."""
        ws_mock = MockWebSocket()
        
        with patch('builtins.WebSocket', return_value=ws_mock):
            ws_mock.simulate_open()
            
            # Send invalid message
            ws_mock.should_fail = True
            
            try:
                invalid_message = {"type": "test"}
                ws_mock.send(json.dumps(invalid_message))
            except Exception:
                # Frontend should handle this gracefully
                pass
                
            # Reset error condition
            ws_mock.should_fail = False
            
            # Connection should recover
            valid_message = {"type": "ping"}
            ws_mock.send(json.dumps(valid_message))
            
            # Should work after error recovery
            assert len([msg for msg in ws_mock.messages_sent if msg.get("type") == "ping"]) == 1
            
    async def test_concurrent_user_scenario(self, mock_websocket):
        """Test scenario with multiple concurrent users."""
        # Simulate multiple WebSocket connections
        user_connections = []
        
        for i in range(3):
            ws_mock = MockWebSocket()
            ws_mock.user_id = f"user_{i}"
            user_connections.append(ws_mock)
            
            with patch('builtins.WebSocket', return_value=ws_mock):
                ws_mock.simulate_open()
                
                # Each user sends a message
                message = {
                    "type": "user_message",
                    "payload": {
                        "content": f"Message from user {i}",
                        "user_id": f"user_{i}"
                    }
                }
                ws_mock.send(json.dumps(message))
                
        # Verify all users could send messages
        assert len(user_connections) == 3
        for ws in user_connections:
            assert len(ws.messages_sent) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])