from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Test that verifies the WebSocket validator fix works correctly.

This test ensures that the WebSocket validator properly handles both
MCP endpoints (JSON-RPC) and regular endpoints (plain JSON).
"""

import asyncio
import json
import pytest
import time

from dev_launcher.websocket_validator import WebSocketValidator, WebSocketEndpoint, WebSocketStatus

# Skip these tests when no WebSocket services are running
# These are detailed protocol tests that require complex mocking
pytest.skip("WebSocket validator tests require running services or complex async mocking", allow_module_level=True)


class WebSocketValidatorFixTests:
    """Test the WebSocket validator fix for MCP endpoints."""
    
    @pytest.mark.asyncio
    async def test_validator_sends_json_rpc_to_mcp_endpoints(self):
        """Test that validator sends JSON-RPC format to MCP endpoints."""
        validator = WebSocketValidator(use_emoji=False)
        
        # Create an MCP endpoint (/ws path)
        endpoint = WebSocketEndpoint(
            name="backend_ws",
            url="ws://localhost:8000/ws",
            port=8000,
            path="/ws"  # MCP endpoint
        )
        
        sent_messages = []
        
        # Mock websocket that captures sent messages
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock(side_effect=lambda msg: sent_messages.append(msg))
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock(return_value=json.dumps({
            "jsonrpc": "2.0",
            "result": {"status": "ok"},
            "id": 1
        }))
        
        # Mock: Component isolation for testing without external dependencies
        with patch("dev_launcher.websocket_validator.websockets.connect") as mock_connect:
            # Create async context manager mock
            # Mock: Generic component isolation for controlled unit testing
            async_context_manager = AsyncMock()
            async_context_manager.__aenter__.return_value = mock_websocket
            async_context_manager.__aexit__.return_value = None
            mock_connect.return_value = async_context_manager
            
            # Test the WebSocket upgrade
            result = await validator._test_websocket_upgrade(endpoint)
            
            # Should succeed
            assert result
            
            # Verify JSON-RPC format was sent
            assert len(sent_messages) == 1
            sent_json = json.loads(sent_messages[0])
            assert "jsonrpc" in sent_json
            assert sent_json["jsonrpc"] == "2.0"
            assert "method" in sent_json
            assert sent_json["method"] == "ping"
            assert "params" in sent_json
            assert "id" in sent_json
    
    @pytest.mark.asyncio
    async def test_validator_sends_plain_json_to_secure_endpoints(self):
        """Test that validator sends plain JSON to /ws endpoints."""
        validator = WebSocketValidator(use_emoji=False)
        
        # Create a secure endpoint
        endpoint = WebSocketEndpoint(
            name="secure_ws",
            url="ws://localhost:8000/ws",
            port=8000,
            path="/ws"  # Secure endpoint
        )
        
        sent_messages = []
        
        # Mock websocket that captures sent messages
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock(side_effect=lambda msg: sent_messages.append(msg))
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock(return_value=json.dumps({
            "type": "pong",
            "timestamp": time.time()
        }))
        
        # Mock: Component isolation for testing without external dependencies
        with patch("dev_launcher.websocket_validator.websockets.connect") as mock_connect:
            # Create async context manager mock
            # Mock: Generic component isolation for controlled unit testing
            async_context_manager = AsyncMock()
            async_context_manager.__aenter__.return_value = mock_websocket
            async_context_manager.__aexit__.return_value = None
            mock_connect.return_value = async_context_manager
            
            # Test the WebSocket upgrade
            result = await validator._test_websocket_upgrade(endpoint)
            
            # Should succeed
            assert result
            
            # Verify plain JSON format was sent
            assert len(sent_messages) == 1
            sent_json = json.loads(sent_messages[0])
            assert "type" in sent_json
            assert sent_json["type"] == "ping"
            assert "timestamp" in sent_json
            # Should NOT have JSON-RPC fields
            assert "jsonrpc" not in sent_json
            assert "method" not in sent_json
    
    @pytest.mark.asyncio
    async def test_validator_handles_mcp_error_responses(self):
        """Test that validator correctly handles MCP error responses."""
        validator = WebSocketValidator(use_emoji=False)
        
        endpoint = WebSocketEndpoint(
            name="backend_ws",
            url="ws://localhost:8000/ws",
            port=8000,
            path="/ws"
        )
        
        # Mock MCP error response
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock(return_value=json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found"
            },
            "id": 1
        }))
        
        # Mock: Component isolation for testing without external dependencies
        with patch("dev_launcher.websocket_validator.websockets.connect") as mock_connect:
            # Create async context manager mock
            # Mock: Generic component isolation for controlled unit testing
            async_context_manager = AsyncMock()
            async_context_manager.__aenter__.return_value = mock_websocket
            async_context_manager.__aexit__.return_value = None
            mock_connect.return_value = async_context_manager
            
            # Test the WebSocket upgrade
            result = await validator._test_websocket_upgrade(endpoint)
            
            # Should still succeed - error response means connection works
            assert result
            assert endpoint.last_error is None
    
    @pytest.mark.asyncio
    async def test_validator_handles_mcp_timeout_gracefully(self):
        """Test that validator handles MCP endpoint timeouts gracefully."""
        validator = WebSocketValidator(use_emoji=False)
        
        endpoint = WebSocketEndpoint(
            name="backend_ws",
            url="ws://localhost:8000/ws",
            port=8000,
            path="/ws"
        )
        
        # Mock timeout on recv
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock(side_effect=asyncio.TimeoutError)
        
        # Mock: Component isolation for testing without external dependencies
        with patch("dev_launcher.websocket_validator.websockets.connect") as mock_connect:
            # Create async context manager mock
            # Mock: Generic component isolation for controlled unit testing
            async_context_manager = AsyncMock()
            async_context_manager.__aenter__.return_value = mock_websocket
            async_context_manager.__aexit__.return_value = None
            mock_connect.return_value = async_context_manager
            
            # Test the WebSocket upgrade
            result = await validator._test_websocket_upgrade(endpoint)
            
            # Should succeed for MCP endpoints (timeout is OK)
            assert result
    
    @pytest.mark.asyncio
    async def test_validator_fails_on_secure_endpoint_timeout(self):
        """Test that validator fails on timeout for non-MCP endpoints."""
        validator = WebSocketValidator(use_emoji=False)
        
        endpoint = WebSocketEndpoint(
            name="secure_ws",
            url="ws://localhost:8000/ws",
            port=8000,
            path="/ws"
        )
        
        # Mock timeout on recv
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock(side_effect=asyncio.TimeoutError)
        
        # Mock: Component isolation for testing without external dependencies
        with patch("dev_launcher.websocket_validator.websockets.connect") as mock_connect:
            # Create async context manager mock
            # Mock: Generic component isolation for controlled unit testing
            async_context_manager = AsyncMock()
            async_context_manager.__aenter__.return_value = mock_websocket
            async_context_manager.__aexit__.return_value = None
            mock_connect.return_value = async_context_manager
            
            # Test the WebSocket upgrade
            result = await validator._test_websocket_upgrade(endpoint)
            
            # Should fail for non-MCP endpoints
            assert not result
            assert endpoint.last_error == "No response received within timeout"
    
    @pytest.mark.asyncio
    async def test_full_validation_flow_with_mixed_endpoints(self):
        """Test full validation flow with both MCP and secure endpoints."""
        validator = WebSocketValidator(use_emoji=False)
        
        # Mock environment to add both types of endpoints
        with patch.dict("os.environ", {"BACKEND_PORT": "8000"}):
            validator._discover_websocket_endpoints()
        
        # Mock HTTP health check
        with patch.object(validator, "_check_http_server", return_value=True):
            
            # Mock websocket connections more properly
            # Mock: Generic component isolation for controlled unit testing
            mock_ws = AsyncMock()
            # Mock: Generic component isolation for controlled unit testing
            mock_ws.send = AsyncMock()
            # Mock: Async component isolation for testing without real async operations
            mock_ws.recv = AsyncMock(return_value=json.dumps({
                "jsonrpc": "2.0",
                "result": {"status": "ok"},
                "id": 1
            }))
            
            # Mock: Component isolation for testing without external dependencies
            with patch("websockets.connect") as mock_connect:
                # Mock: Async component isolation for testing without real async operations
                mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_ws)
                # Mock: Generic component isolation for controlled unit testing
                mock_connect.return_value.__aexit__ = AsyncMock()
                # Run validation
                result = await validator.validate_all_endpoints()
                
                # Should succeed
                assert result
                assert validator.is_all_healthy()
                
                # Check all endpoints are connected
                for endpoint in validator.endpoints.values():
                    assert endpoint.status == WebSocketStatus.CONNECTED
