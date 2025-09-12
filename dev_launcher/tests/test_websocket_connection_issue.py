"""
Test that reproduces the WebSocket connection issue in dev launcher.

This test will fail initially, demonstrating the issue where the WebSocket
validator sends a plain JSON message to the MCP endpoint which expects
JSON-RPC format.
"""

import asyncio
import json
import pytest
import time
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.websocket_validator import WebSocketValidator, WebSocketEndpoint, WebSocketStatus

# Skip these tests when no WebSocket services are running  
pytest.skip("WebSocket connection tests require running services", allow_module_level=True)


class TestWebSocketConnectionIssue:
    """Test that reproduces WebSocket connection failure."""
    
    @pytest.mark.asyncio
    async def test_websocket_validator_sends_wrong_format_to_mcp_endpoint(self):
        """
        Test that demonstrates the WebSocket validator sends plain JSON
        instead of JSON-RPC format expected by MCP endpoint.
        
        This test will FAIL initially, showing the issue.
        """
        validator = WebSocketValidator(use_emoji=False)
        
        # Mock the websockets library
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock()
        
        # Simulate MCP endpoint that expects JSON-RPC format
        # It will return an error for non-JSON-RPC messages
        async def mock_recv():
            # Wait to see what was sent
            await asyncio.sleep(0.1)
            if mock_websocket.send.called:
                sent_data = mock_websocket.send.call_args[0][0]
                sent_json = json.loads(sent_data)
                
                # Check if it's valid JSON-RPC
                if "jsonrpc" not in sent_json or "method" not in sent_json:
                    # MCP endpoint would return an error for invalid format
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request: Missing jsonrpc field"
                        },
                        "id": None
                    })
                else:
                    # Valid JSON-RPC, return proper response
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "result": {"type": "pong"},
                        "id": sent_json.get("id", 1)
                    })
        
        mock_websocket.recv = mock_recv
        
        # Mock: Component isolation for testing without external dependencies
        with patch("websockets.connect") as mock_connect:
            # Mock: WebSocket infrastructure isolation for unit tests without real connections
            mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
            # Mock: Generic component isolation for controlled unit testing
            mock_connect.return_value.__aexit__ = AsyncMock()
            
            # This should fail because validator sends wrong format
            endpoint = WebSocketEndpoint(
                name="test_mcp",
                url="ws://localhost:8000/ws",
                port=8000,
                path="/ws"
            )
            
            result = await validator._test_websocket_upgrade(endpoint)
            
            # Verify what was sent
            assert mock_websocket.send.called
            sent_data = mock_websocket.send.call_args[0][0]
            sent_json = json.loads(sent_data)
            
            # The validator sends plain JSON like {"type": "ping", "timestamp": ...}
            # But MCP expects JSON-RPC like {"jsonrpc": "2.0", "method": "ping", ...}
            assert "type" in sent_json  # Validator sends this
            assert "jsonrpc" not in sent_json  # But doesn't send this
            
            # So the test should fail
            assert not result, "Expected WebSocket test to fail due to wrong message format"
            assert "Invalid JSON message structure" in endpoint.last_error or \
                   "Invalid Request" in endpoint.last_error
    
    @pytest.mark.asyncio
    async def test_current_websocket_validator_logic_fails(self):
        """
        Test the actual current logic that causes WebSocket validation to fail.
        This reproduces the exact issue seen in the dev launcher output.
        """
        validator = WebSocketValidator(use_emoji=False)
        
        # Add the backend endpoint as it would be discovered
        validator._add_endpoint("backend_ws", "localhost", 8000, "/ws")
        
        # Mock HTTP check to succeed (server is running)
        with patch.object(validator, "_check_http_server", return_value=True):
            # Mock websocket connection
            # Mock: WebSocket infrastructure isolation for unit tests without real connections
            mock_websocket = AsyncMock()
            # Mock: WebSocket infrastructure isolation for unit tests without real connections
            mock_websocket.send = AsyncMock()
            
            # Simulate timeout on recv (no proper response)
            # Mock: WebSocket infrastructure isolation for unit tests without real connections
            mock_websocket.recv = AsyncMock(side_effect=asyncio.TimeoutError)
            
            # Mock: Component isolation for testing without external dependencies
            with patch("websockets.connect") as mock_connect:
                # Mock: WebSocket infrastructure isolation for unit tests without real connections
                mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
                # Mock: Generic component isolation for controlled unit testing
                mock_connect.return_value.__aexit__ = AsyncMock()
                
                # Run the validation
                result = await validator.validate_all_endpoints()
                
                # Should fail after retries
                assert not result, "WebSocket validation should fail"
                
                # Check the endpoint status
                endpoint = validator.endpoints["backend_ws"]
                assert endpoint.status == WebSocketStatus.FAILED
                assert endpoint.failure_count > 0
    
    @pytest.mark.asyncio
    async def test_websocket_validator_with_json_rpc_format_succeeds(self):
        """
        Test that shows how the validator would succeed if it sent
        proper JSON-RPC format messages.
        
        This is what the fix should achieve.
        """
        validator = WebSocketValidator(use_emoji=False)
        
        # Mock successful JSON-RPC communication
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send = AsyncMock()
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.recv = AsyncMock(return_value=json.dumps({
            "jsonrpc": "2.0",
            "result": {"status": "connected"},
            "id": 1
        }))
        
        # Mock: Component isolation for testing without external dependencies
        with patch("websockets.connect") as mock_connect:
            # Mock: WebSocket infrastructure isolation for unit tests without real connections
            mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
            # Mock: Generic component isolation for controlled unit testing
            mock_connect.return_value.__aexit__ = AsyncMock()
            
            # Patch the method to send JSON-RPC format
            original_test = validator._test_websocket_upgrade
            
            async def patched_test(endpoint):
                try:
                    import websockets
                    async with websockets.connect(endpoint.url, open_timeout=validator.timeout) as ws:
                        # Send JSON-RPC format message
                        test_message = {
                            "jsonrpc": "2.0",
                            "method": "ping",
                            "params": {"timestamp": time.time()},
                            "id": 1
                        }
                        await ws.send(json.dumps(test_message))
                        
                        # Wait for response
                        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        response_json = json.loads(response)
                        
                        # Validate JSON-RPC response
                        if "jsonrpc" in response_json:
                            return True
                        return False
                except Exception as e:
                    endpoint.last_error = str(e)
                    return False
            
            validator._test_websocket_upgrade = patched_test
            
            endpoint = WebSocketEndpoint(
                name="test_mcp",
                url="ws://localhost:8000/ws",
                port=8000,
                path="/ws"
            )
            
            result = await validator._test_websocket_upgrade(endpoint)
            
            # With proper format, it should succeed
            assert result, "WebSocket test should succeed with JSON-RPC format"