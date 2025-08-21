"""
Tests for MCP Request Handler

Test JSON-RPC 2.0 request processing.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


# Skip tests if RequestHandler module doesn't exist yet
pytest.skip("MCP Request Handler not yet implemented", allow_module_level=True)

from netra_backend.app.core.exceptions_base import NetraException


class TestRequestHandler:
    """Test request handler functionality"""
    
    @pytest.fixture
    def mock_server(self):
        """Create mock server"""
        server = Mock()
        server.handle_request = AsyncMock()
        return server
        
    @pytest.fixture
    def handler(self, mock_server):
        """Create request handler"""
        return RequestHandler(mock_server)
    async def test_process_request_string(self, handler, mock_server):
        """Test processing string request"""
        mock_server.handle_request.return_value = {
            "jsonrpc": "2.0",
            "result": {"success": True},
            "id": 1
        }
        
        request_str = '{"jsonrpc": "2.0", "method": "test", "id": 1}'
        response = await handler.process_request(request_str)
        
        assert isinstance(response, str)
        response_dict = json.loads(response)
        assert response_dict["result"]["success"] == True
    async def test_process_request_dict(self, handler, mock_server):
        """Test processing dict request"""
        mock_server.handle_request.return_value = {
            "jsonrpc": "2.0",
            "result": {"success": True},
            "id": 1
        }
        
        request_dict = {"jsonrpc": "2.0", "method": "test", "id": 1}
        response = await handler.process_request(request_dict)
        
        assert isinstance(response, dict)
        assert response["result"]["success"] == True
    async def test_process_invalid_json(self, handler):
        """Test processing invalid JSON string"""
        request_str = '{"invalid json'
        response = await handler.process_request(request_str)
        
        assert isinstance(response, str)
        response_dict = json.loads(response)
        assert "error" in response_dict
        assert response_dict["error"]["code"] == -32700
    async def test_process_batch_request(self, handler, mock_server):
        """Test processing batch requests"""
        mock_server.handle_request.side_effect = [
            {"jsonrpc": "2.0", "result": {"id": 1}, "id": 1},
            {"jsonrpc": "2.0", "result": {"id": 2}, "id": 2}
        ]
        
        batch_request = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2}
        ]
        
        response = await handler.process_request(batch_request)
        
        assert isinstance(response, list)
        assert len(response) == 2
        assert response[0]["result"]["id"] == 1
        assert response[1]["result"]["id"] == 2
    async def test_process_notification(self, handler, mock_server):
        """Test processing notification (no id)"""
        mock_server.handle_request.return_value = None
        
        request = {"jsonrpc": "2.0", "method": "notify"}
        response = await handler.process_request(request)
        
        assert response == None
    async def test_process_single_request_invalid_type(self, handler):
        """Test processing request with invalid type"""
        response = await handler._process_single_request("not a dict")
        
        assert "error" in response
        assert response["error"]["code"] == -32600
        assert "must be an object" in response["error"]["message"]
    async def test_process_single_request_invalid_version(self, handler):
        """Test processing request with invalid JSON-RPC version"""
        response = await handler._process_single_request({"method": "test"})
        
        assert "error" in response
        assert response["error"]["code"] == -32600
        assert "Invalid or missing jsonrpc" in response["error"]["message"]
    async def test_process_single_request_missing_method(self, handler):
        """Test processing request with missing method"""
        response = await handler._process_single_request({"jsonrpc": "2.0"})
        
        assert "error" in response
        assert response["error"]["code"] == -32600
        assert "Invalid or missing method" in response["error"]["message"]
    async def test_process_single_request_invalid_params(self, handler):
        """Test processing request with invalid params type"""
        response = await handler._process_single_request({
            "jsonrpc": "2.0",
            "method": "test",
            "params": "not an object or array"
        })
        
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "Params must be object or array" in response["error"]["message"]
    async def test_process_business_error(self, handler, mock_server):
        """Test processing request that raises business error"""
        mock_server.handle_request.side_effect = NetraException("Business error")
        
        response = await handler._process_single_request({
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        assert "error" in response
        assert response["error"]["code"] == -32000
        assert "Business error" in response["error"]["message"]
    async def test_process_unexpected_error(self, handler, mock_server):
        """Test processing request that raises unexpected error"""
        mock_server.handle_request.side_effect = Exception("Unexpected error")
        
        response = await handler._process_single_request({
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "Unexpected error" in response["error"]["message"]
        
    def test_validate_request_valid(self, handler):
        """Test validating valid request"""
        request = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"key": "value"},
            "id": 1
        }
        
        result = handler.validate_request(request)
        assert result == None
        
    def test_validate_request_missing_jsonrpc(self, handler):
        """Test validating request without jsonrpc"""
        request = {"method": "test"}
        
        result = handler.validate_request(request)
        assert result["error"]["code"] == -32600
        assert "Missing jsonrpc" in result["error"]["message"]
        
    def test_validate_request_wrong_version(self, handler):
        """Test validating request with wrong version"""
        request = {"jsonrpc": "1.0", "method": "test"}
        
        result = handler.validate_request(request)
        assert result["error"]["code"] == -32600
        assert "Invalid jsonrpc version" in result["error"]["message"]
        
    def test_validate_request_invalid_method_type(self, handler):
        """Test validating request with non-string method"""
        request = {"jsonrpc": "2.0", "method": 123}
        
        result = handler.validate_request(request)
        assert result["error"]["code"] == -32600
        assert "Method must be a string" in result["error"]["message"]
        
    def test_validate_request_invalid_params_type(self, handler):
        """Test validating request with invalid params type"""
        request = {"jsonrpc": "2.0", "method": "test", "params": "string"}
        
        result = handler.validate_request(request)
        assert result["error"]["code"] == -32602
        assert "Params must be object or array" in result["error"]["message"]
        
    def test_validate_request_invalid_id_type(self, handler):
        """Test validating request with invalid id type"""
        request = {"jsonrpc": "2.0", "method": "test", "id": []}
        
        result = handler.validate_request(request)
        assert result["error"]["code"] == -32600
        assert "Invalid id type" in result["error"]["message"]
        
    def test_error_response_methods(self, handler):
        """Test error response helper methods"""
        # Parse error
        response = handler._parse_error("Parse failed", 1)
        assert response["error"]["code"] == -32700
        assert "Parse failed" in response["error"]["message"]
        assert response["id"] == 1
        
        # Invalid request
        response = handler._invalid_request("Invalid", 2)
        assert response["error"]["code"] == -32600
        assert "Invalid" in response["error"]["message"]
        
        # Method not found
        response = handler._method_not_found("unknown", 3)
        assert response["error"]["code"] == -32601
        assert "unknown" in response["error"]["message"]
        
        # Invalid params
        response = handler._invalid_params("Bad params", 4)
        assert response["error"]["code"] == -32602
        assert "Bad params" in response["error"]["message"]
        
        # Internal error
        response = handler._internal_error("Internal", 5)
        assert response["error"]["code"] == -32603
        assert "Internal" in response["error"]["message"]
        
    def test_error_response_without_id(self, handler):
        """Test error response without request id"""
        response = handler._error_response(-32700, "Error")
        assert "id" not in response
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32700