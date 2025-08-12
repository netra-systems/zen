"""
Tests for MCP Server Core

Comprehensive test suite for the MCP server implementation.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid

from app.mcp.server import MCPServer, MCPServerConfig, MCPSession
from app.core.exceptions import NetraException


class TestMCPServerConfig:
    """Test MCP server configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = MCPServerConfig()
        assert config.protocol_version == "1.0.0"
        assert config.server_name == "Netra MCP Server"
        assert config.max_sessions == 1000
        assert config.session_timeout == 3600
        assert config.rate_limit == 100
        assert config.enable_sampling == True
        assert config.enable_tools == True
        assert config.enable_resources == True
        assert config.enable_prompts == True
        
    def test_custom_config(self):
        """Test custom configuration"""
        config = MCPServerConfig(
            max_sessions=500,
            session_timeout=7200,
            rate_limit=50,
            enable_sampling=False
        )
        assert config.max_sessions == 500
        assert config.session_timeout == 7200
        assert config.rate_limit == 50
        assert config.enable_sampling == False
        
    def test_config_validation(self):
        """Test configuration validation"""
        with pytest.raises(ValueError):
            MCPServerConfig(max_sessions=0)
        with pytest.raises(ValueError):
            MCPServerConfig(session_timeout=30)
        with pytest.raises(ValueError):
            MCPServerConfig(rate_limit=0)


class TestMCPSession:
    """Test MCP session model"""
    
    def test_session_creation(self):
        """Test session creation with defaults"""
        session = MCPSession(
            transport="websocket",
            protocol_version="1.0.0",
            capabilities={"tools": True}
        )
        assert session.id != None
        assert session.transport == "websocket"
        assert session.protocol_version == "1.0.0"
        assert session.capabilities == {"tools": True}
        assert session.state == {}
        assert session.request_count == 0
        assert session.last_request_at == None
        
    def test_session_expiry(self):
        """Test session expiry calculation"""
        session = MCPSession(
            transport="http",
            protocol_version="1.0.0",
            capabilities={}
        )
        assert session.expires_at > session.created_at
        assert (session.expires_at - session.created_at).seconds == 3600


class TestMCPServer:
    """Test MCP server core functionality"""
    
    @pytest.fixture
    def server(self):
        """Create MCP server instance"""
        return MCPServer()
        
    @pytest.fixture
    def mock_session(self):
        """Create mock session"""
        return MCPSession(
            id="test-session",
            transport="test",
            protocol_version="1.0.0",
            capabilities={}
        )
        
    def test_server_initialization(self, server):
        """Test server initialization"""
        assert server.config != None
        assert server.sessions == {}
        assert server.request_handlers != {}
        assert server.tool_registry != None
        assert server.resource_manager != None
        assert server.prompt_manager != None
        
    def test_method_registration(self, server):
        """Test method handler registration"""
        handler = Mock()
        server.register_method("test.method", handler)
        assert "test.method" in server.request_handlers
        assert server.request_handlers["test.method"] == handler
        
    @pytest.mark.asyncio
    async def test_handle_request_invalid_jsonrpc(self, server):
        """Test handling request with invalid JSON-RPC version"""
        request = {"method": "test", "params": {}}
        response = await server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32600
        assert "Invalid Request" in response["error"]["message"]
        
    @pytest.mark.asyncio
    async def test_handle_request_missing_method(self, server):
        """Test handling request with missing method"""
        request = {"jsonrpc": "2.0", "params": {}, "id": 1}
        response = await server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32600
        assert "missing method" in response["error"]["message"]
        
    @pytest.mark.asyncio
    async def test_handle_request_method_not_found(self, server):
        """Test handling request with unknown method"""
        request = {"jsonrpc": "2.0", "method": "unknown.method", "id": 1}
        response = await server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]
        
    @pytest.mark.asyncio
    async def test_handle_request_success(self, server):
        """Test successful request handling"""
        async def test_handler(params, session_id):
            return {"result": "success", "params": params}
            
        server.register_method("test.method", test_handler)
        request = {
            "jsonrpc": "2.0",
            "method": "test.method",
            "params": {"test": "value"},
            "id": 1
        }
        response = await server.handle_request(request)
        assert "result" in response
        assert response["result"]["result"] == "success"
        assert response["result"]["params"] == {"test": "value"}
        assert response["id"] == 1
        
    @pytest.mark.asyncio
    async def test_handle_initialize(self, server):
        """Test initialization handling"""
        params = {
            "protocolVersion": "1.0.0",
            "capabilities": {"experimental": True},
            "clientInfo": {"name": "test-client"}
        }
        result = await server.handle_initialize(params)
        
        assert result["protocolVersion"] == "1.0.0"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "Netra MCP Server"
        
    @pytest.mark.asyncio
    async def test_handle_ping(self, server):
        """Test ping handling"""
        result = await server.handle_ping({})
        assert result["pong"] == True
        assert "timestamp" in result
        
    @pytest.mark.asyncio
    async def test_handle_tools_list(self, server):
        """Test tools list handling"""
        server.tool_registry = AsyncMock()
        server.tool_registry.list_tools.return_value = [
            {"name": "tool1", "description": "Test tool"}
        ]
        
        result = await server.handle_tools_list({})
        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "tool1"
        
    @pytest.mark.asyncio
    async def test_handle_tools_call(self, server):
        """Test tool execution handling"""
        server.tool_registry = AsyncMock()
        server.tool_registry.execute_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        params = {"name": "test_tool", "arguments": {"arg": "value"}}
        result = await server.handle_tools_call(params)
        
        assert "content" in result
        assert "isError" in result
        assert result["isError"] == False
        server.tool_registry.execute_tool.assert_called_once_with(
            "test_tool", {"arg": "value"}, None
        )
        
    @pytest.mark.asyncio
    async def test_handle_tools_call_missing_name(self, server):
        """Test tool execution with missing name"""
        server.tool_registry = Mock()
        
        with pytest.raises(NetraException) as exc_info:
            await server.handle_tools_call({"arguments": {}})
        assert "Tool name is required" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_handle_resources_list(self, server):
        """Test resources list handling"""
        server.resource_manager = AsyncMock()
        server.resource_manager.list_resources.return_value = [
            {"uri": "netra://test", "name": "Test Resource"}
        ]
        
        result = await server.handle_resources_list({})
        assert "resources" in result
        assert len(result["resources"]) == 1
        assert result["resources"][0]["uri"] == "netra://test"
        
    @pytest.mark.asyncio
    async def test_handle_resources_read(self, server):
        """Test resource reading"""
        server.resource_manager = AsyncMock()
        server.resource_manager.read_resource.return_value = [
            {"type": "text", "text": "Resource content"}
        ]
        
        params = {"uri": "netra://test"}
        result = await server.handle_resources_read(params)
        
        assert "contents" in result
        assert result["contents"][0]["text"] == "Resource content"
        
    @pytest.mark.asyncio
    async def test_handle_prompts_list(self, server):
        """Test prompts list handling"""
        server.prompt_manager = AsyncMock()
        server.prompt_manager.list_prompts.return_value = [
            {"name": "test_prompt", "description": "Test prompt"}
        ]
        
        result = await server.handle_prompts_list({})
        assert "prompts" in result
        assert len(result["prompts"]) == 1
        
    @pytest.mark.asyncio
    async def test_handle_prompts_get(self, server):
        """Test prompt retrieval"""
        server.prompt_manager = AsyncMock()
        server.prompt_manager.get_prompt.return_value = [
            {"role": "system", "content": "Test prompt"}
        ]
        
        params = {"name": "test_prompt", "arguments": {}}
        result = await server.handle_prompts_get(params)
        
        assert "messages" in result
        assert result["messages"][0]["role"] == "system"
        
    @pytest.mark.asyncio
    async def test_rate_limiting(self, server, mock_session):
        """Test rate limiting functionality"""
        # Add session with high request count
        mock_session.request_count = 200
        mock_session.last_request_at = datetime.now(UTC)
        server.sessions["test-session"] = mock_session
        
        request = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        }
        
        response = await server.handle_request(request, "test-session")
        assert "error" in response
        assert response["error"]["code"] == -32004
        assert "Rate limit exceeded" in response["error"]["message"]
        
    @pytest.mark.asyncio
    async def test_session_activity_tracking(self, server, mock_session):
        """Test session activity tracking"""
        server.sessions["test-session"] = mock_session
        server.register_method("test", AsyncMock(return_value={"result": "ok"}))
        
        initial_count = mock_session.request_count
        
        request = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        }
        
        await server.handle_request(request, "test-session")
        
        assert mock_session.request_count == initial_count + 1
        assert mock_session.last_request_at != None
        
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, server):
        """Test expired session cleanup"""
        # Add expired session
        expired_session = MCPSession(
            id="expired",
            transport="test",
            protocol_version="1.0.0",
            capabilities={}
        )
        expired_session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        server.sessions["expired"] = expired_session
        
        # Add active session
        active_session = MCPSession(
            id="active",
            transport="test",
            protocol_version="1.0.0",
            capabilities={}
        )
        server.sessions["active"] = active_session
        
        await server.cleanup_expired_sessions()
        
        assert "expired" not in server.sessions
        assert "active" in server.sessions
        
    @pytest.mark.asyncio
    async def test_shutdown(self, server):
        """Test server shutdown"""
        server.sessions["test"] = Mock()
        server.tool_registry = AsyncMock()
        server.resource_manager = AsyncMock()
        
        await server.shutdown()
        
        assert len(server.sessions) == 0
        server.tool_registry.shutdown.assert_called_once()
        server.resource_manager.shutdown.assert_called_once()
        
    def test_success_response_format(self, server):
        """Test success response formatting"""
        response = server._success_response({"data": "test"}, 123)
        
        assert response["jsonrpc"] == "2.0"
        assert response["result"] == {"data": "test"}
        assert response["id"] == 123
        
    def test_error_response_format(self, server):
        """Test error response formatting"""
        response = server._error_response(
            -32601,
            "Method not found",
            456,
            {"details": "additional info"}
        )
        
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Method not found"
        assert response["error"]["data"] == {"details": "additional info"}
        assert response["id"] == 456
        
    def test_notification_handling(self, server):
        """Test notification (no id) handling"""
        response = server._success_response({"data": "test"})
        assert "id" not in response
        
        response = server._error_response(-32601, "Error")
        assert "id" not in response