"""
Validation tests for WebSocket mock utilities module.
Ensures all patterns work correctly and comply with architecture requirements.
"""

import pytest
import asyncio
from unittest.mock import patch

from app.tests.test_utilities.websocket_mocks import (
    create_mock_websocket,
    create_mock_websockets,
    WebSocketBuilder,
    MessageSimulator,
    websocket_test_context,
    simulate_connection_lifecycle,
    MockWebSocket,
    MockWebSocketState
)


class TestWebSocketMockUtilities:
    """Test suite for WebSocket mock utilities framework."""
    
    def test_create_mock_websocket_basic(self):
        """Test basic WebSocket creation (≤8 lines)."""
        ws = create_mock_websocket("test_user")
        assert ws.user_id == "test_user"
        assert ws.state == MockWebSocketState.CONNECTED
        assert ws.is_authenticated is True
        assert len(ws.sent_messages) == 0
    
    def test_create_multiple_websockets(self):
        """Test multiple WebSocket creation (≤8 lines)."""
        websockets = create_mock_websockets(3, "user")
        assert len(websockets) == 3
        assert "user_1" in websockets
        assert "user_3" in websockets
        assert all(ws.user_id.startswith("user_") for ws in websockets.values())
    
    def test_websocket_builder_pattern(self):
        """Test fluent builder pattern (≤8 lines)."""
        ws = (WebSocketBuilder()
              .with_user_id("builder_test")
              .with_authentication("custom_token", ["admin", "read"])
              .with_rate_limiting(50, 30)
              .build())
        assert ws.user_id == "builder_test"
        assert ws.auth_token == "custom_token"
        assert ws.permissions == ["admin", "read"]
        assert ws.rate_limit_max == 50
    
    @pytest.mark.asyncio
    async def test_websocket_send_operations(self):
        """Test WebSocket send operations (≤8 lines)."""
        ws = create_mock_websocket("send_test")
        await ws.send_text("test message")
        await ws.send_json({"type": "test", "data": "json"})
        assert len(ws.sent_messages) == 2
        assert ws.sent_messages[0]["type"] == "text"
        assert ws.sent_messages[1]["type"] == "json"
    
    @pytest.mark.asyncio
    async def test_websocket_failure_simulation(self):
        """Test failure simulation features (≤8 lines)."""
        ws = (WebSocketBuilder()
              .with_user_id("fail_test")
              .with_failure_simulation(send_fail=True)
              .build())
        with pytest.raises(ConnectionError):
            await ws.send_text("should fail")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_simulation(self):
        """Test rate limiting simulation (≤8 lines)."""
        ws = (WebSocketBuilder()
              .with_user_id("rate_test")
              .with_rate_limiting(max_requests=2)
              .build())
        await ws.send_text("message 1")
        await ws.send_text("message 2")
        with pytest.raises(ConnectionError, match="Rate limit exceeded"):
            await ws.send_text("message 3")
    
    @pytest.mark.asyncio
    async def test_message_simulator(self):
        """Test message simulation patterns (≤8 lines)."""
        simulator = MessageSimulator()
        ws = create_mock_websocket("sim_test")
        messages = [
            {"type": "test1", "data": "data1"},
            {"type": "test2", "data": "data2"}
        ]
        results = await simulator.simulate_bidirectional_flow(ws, messages)
        assert len(results) == 2
        assert all("response" in result["type"] for result in results)
    
    @pytest.mark.asyncio
    async def test_websocket_context_manager(self):
        """Test async context manager pattern (≤8 lines)."""
        async with websocket_test_context(user_count=3) as websockets:
            assert len(websockets) == 3
            assert "user_1" in websockets
            assert "user_3" in websockets
            # Verify all are connected
            for ws in websockets.values():
                assert ws.state == MockWebSocketState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """Test complete connection lifecycle (≤8 lines)."""
        ws = create_mock_websocket("lifecycle_test")
        result = await simulate_connection_lifecycle(ws)
        assert result["connected"] is True
        assert result["messages_sent"] == 1
        assert result["final_state"] == MockWebSocketState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_broadcast_simulation(self):
        """Test broadcast message simulation (≤8 lines)."""
        simulator = MessageSimulator()
        websockets = [create_mock_websocket(f"user_{i}") for i in range(3)]
        broadcast_msg = {"type": "broadcast", "data": "test"}
        result = await simulator.simulate_broadcast(websockets, broadcast_msg)
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["total"] == 3


class TestWebSocketMockArchitectureCompliance:
    """Test architecture compliance for WebSocket mock utilities."""
    
    def test_mock_websocket_line_count(self):
        """Verify MockWebSocket class doesn't exceed limits (≤8 lines)."""
        # This is a meta-test to ensure our module follows architecture rules
        import inspect
        from app.tests.test_utilities.websocket_mocks import MockWebSocket
        
        # Get all methods and check they don't exceed 8 lines
        methods = inspect.getmembers(MockWebSocket, predicate=inspect.isfunction)
        for name, method in methods:
            source_lines = inspect.getsourcelines(method)[0]
            # Filter out docstrings and empty lines
            code_lines = [line for line in source_lines 
                         if line.strip() and not line.strip().startswith('"""')]
            assert len(code_lines) <= 8, f"Method {name} has {len(code_lines)} lines"
    
    def test_builder_pattern_compliance(self):
        """Verify WebSocketBuilder follows architecture rules (≤8 lines)."""
        import inspect
        from app.tests.test_utilities.websocket_mocks import WebSocketBuilder
        
        methods = inspect.getmembers(WebSocketBuilder, predicate=inspect.isfunction)
        for name, method in methods:
            source_lines = inspect.getsourcelines(method)[0]
            code_lines = [line for line in source_lines 
                         if line.strip() and not line.strip().startswith('"""')]
            assert len(code_lines) <= 8, f"Builder method {name} has {len(code_lines)} lines"
    
    def test_module_total_line_count(self):
        """Verify total module doesn't exceed 300 lines (≤8 lines)."""
        import inspect
        from app.tests.test_utilities import websocket_mocks
        
        source_lines = inspect.getsourcelines(websocket_mocks)[0]
        # Filter out empty lines and comments
        code_lines = [line for line in source_lines 
                     if line.strip() and not line.strip().startswith('#')]
        assert len(code_lines) <= 300, f"Module has {len(code_lines)} lines, exceeds 300 limit"


@pytest.mark.asyncio
async def test_comprehensive_websocket_workflow():
    """Test comprehensive WebSocket workflow using all utilities (≤8 lines)."""
    async with websocket_test_context(user_count=2) as websockets:
        # Test authentication and rate limiting
        ws1 = websockets["user_1"]
        ws2 = websockets["user_2"]
        
        # Send messages and verify
        await ws1.send_json({"type": "user_message", "text": "Hello"})
        await ws2.send_json({"type": "ping", "data": {}})
        
        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 1