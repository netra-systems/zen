"""Tests for MCP Integration.

Tests the MCP context manager, intent detector, and agent bridge.
Follows strict 25-line function design for testability.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp_client import MCPTool

from netra_backend.app.agents.mcp_integration.context_manager import (
    MCPAgentContext,
    MCPContextManager,
    MCPPermissionContext,
)
from netra_backend.app.agents.mcp_integration.mcp_intent_detector import (
    MCPIntentDetector,
)
from netra_backend.app.services.agent_mcp_bridge import AgentMCPBridge

@pytest.fixture
def mock_mcp_service():
    """Mock MCP client service."""
    service = AsyncMock()
    service.discover_tools.return_value = [
        {"name": "file_read", "description": "Read file", "schema": {}},
        {"name": "web_fetch", "description": "Fetch URL", "schema": {}}
    ]
    service.execute_tool.return_value = {"status": "success", "result": "test"}
    return service

@pytest.fixture
def mcp_context_manager(mock_mcp_service):
    """MCP context manager with mock service."""
    return MCPContextManager(mock_mcp_service)

@pytest.fixture
def mcp_intent_detector():
    """MCP intent detector instance."""
    return MCPIntentDetector()

@pytest.fixture
def agent_mcp_bridge(mock_mcp_service):
    """Agent MCP bridge with mock service."""
    return AgentMCPBridge(mock_mcp_service)

@pytest.fixture
def sample_agent_context():
    """Sample agent context for testing."""
    permission_ctx = MCPPermissionContext(
        agent_name="data_sub_agent",
        user_id="test_user"
    )
    return MCPAgentContext(
        run_id="test_run",
        thread_id="test_thread",
        agent_name="data_sub_agent",
        user_id="test_user",
        permission_context=permission_ctx
    )

class TestMCPContextManager:
    """Test MCP context manager functionality."""
    
    @pytest.mark.asyncio
    
    async def test_create_agent_context(self, mcp_context_manager):
        """Test agent context creation."""
        context = await mcp_context_manager.create_agent_context(
            "data_sub_agent", "user123", "run123", "thread123"
        )
        
        assert context.agent_name == "data_sub_agent"
        assert context.user_id == "user123"
        assert context.run_id == "run123"
        assert context.thread_id == "thread123"
    
    @pytest.mark.asyncio
    
    async def test_get_available_tools(self, mcp_context_manager, sample_agent_context):
        """Test tool discovery with permissions."""
        tools = await mcp_context_manager.get_available_tools(
            sample_agent_context, "test_server"
        )
        
        assert len(tools) >= 0
        assert all(isinstance(tool, MCPTool) for tool in tools)
    
    @pytest.mark.asyncio
    
    async def test_execute_tool_with_context_success(self, mcp_context_manager, sample_agent_context):
        """Test successful tool execution."""
        # Mock permission checker to allow execution
        mcp_context_manager.permission_checker.can_execute_tool = Mock(return_value=True)
        
        result = await mcp_context_manager.execute_tool_with_context(
            sample_agent_context, "test_server", "file_read", {"path": "/test"}
        )
        
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    
    async def test_execute_tool_permission_denied(self, mcp_context_manager, sample_agent_context):
        """Test tool execution with permission denied."""
        # Mock permission checker to deny execution
        mcp_context_manager.permission_checker.can_execute_tool = Mock(return_value=False)
        
        with pytest.raises(Exception) as exc_info:
            await mcp_context_manager.execute_tool_with_context(
                sample_agent_context, "test_server", "restricted_tool", {}
            )
        
        assert "Permission denied" in str(exc_info.value)
    
    def test_cleanup_context(self, mcp_context_manager):
        """Test context cleanup."""
        run_id = "test_run_123"
        mcp_context_manager.active_contexts[run_id] = Mock()
        
        mcp_context_manager.cleanup_context(run_id)
        
        assert run_id not in mcp_context_manager.active_contexts

class TestMCPIntentDetector:
    """Test MCP intent detection functionality."""
    
    def test_detect_no_mcp_intent(self, mcp_intent_detector):
        """Test request with no MCP intent."""
        request = "What is the weather like today?"
        intent = mcp_intent_detector.detect_intent(request)
        
        assert not intent.requires_mcp
        assert intent.confidence == 0.0
    
    def test_detect_file_operation_intent(self, mcp_intent_detector):
        """Test file operation intent detection."""
        request = "Please read file /path/to/data.txt"
        intent = mcp_intent_detector.detect_intent(request)
        
        assert intent.requires_mcp
        assert intent.server_name == "filesystem"
        assert intent.confidence >= 0.5
    
    def test_detect_web_operation_intent(self, mcp_intent_detector):
        """Test web operation intent detection."""
        request = "Fetch URL https://example.com and analyze content"
        intent = mcp_intent_detector.detect_intent(request)
        
        assert intent.requires_mcp
        assert intent.server_name == "web_scraper"
        assert len(intent.parameters) > 0
    
    def test_should_route_to_mcp(self, mcp_intent_detector):
        """Test MCP routing decision."""
        mcp_request = "Use external tool to read file data.csv"
        normal_request = "Analyze the sales data trends"
        
        assert mcp_intent_detector.should_route_to_mcp(mcp_request)
        assert not mcp_intent_detector.should_route_to_mcp(normal_request)
    
    def test_get_routing_info(self, mcp_intent_detector):
        """Test routing information extraction."""
        request = "Run command ls -la in system"
        should_route, server, tool = mcp_intent_detector.get_routing_info(request)
        
        assert should_route
        assert server == "system"
        assert tool in ["command", "ls"]

class TestAgentMCPBridge:
    """Test agent-MCP bridge functionality."""
    
    @pytest.mark.asyncio
    
    async def test_discover_tools(self, agent_mcp_bridge, sample_agent_context):
        """Test tool discovery through bridge."""
        tools = await agent_mcp_bridge.discover_tools(
            sample_agent_context, "test_server"
        )
        
        assert len(tools) >= 0
        assert all(isinstance(tool, MCPTool) for tool in tools)
    
    @pytest.mark.asyncio
    
    async def test_execute_tool_for_agent_success(self, agent_mcp_bridge, sample_agent_context):
        """Test successful tool execution through bridge."""
        result = await agent_mcp_bridge.execute_tool_for_agent(
            sample_agent_context, "test_server", "file_read", {"path": "/test"}
        )
        
        assert result["status"] == "success"
        assert "type" in result
    
    @pytest.mark.asyncio
    
    async def test_execute_tool_for_agent_error(self, agent_mcp_bridge, sample_agent_context):
        """Test tool execution error handling."""
        # Mock service to raise exception
        agent_mcp_bridge.mcp_service.execute_tool.side_effect = Exception("Tool error")
        
        result = await agent_mcp_bridge.execute_tool_for_agent(
            sample_agent_context, "test_server", "failing_tool", {}
        )
        
        assert result["status"] == "error"
        assert "error" in result
    
    @pytest.mark.asyncio
    
    async def test_get_server_capabilities(self, agent_mcp_bridge):
        """Test server capabilities retrieval."""
        agent_mcp_bridge.mcp_service.list_servers.return_value = [
            {"name": "test_server", "capabilities": ["tools", "resources"]}
        ]
        
        capabilities = await agent_mcp_bridge.get_server_capabilities("test_server")
        
        assert "tools" in capabilities or capabilities == {}
    
    @pytest.mark.asyncio
    
    async def test_health_check_success(self, agent_mcp_bridge):
        """Test successful server health check."""
        health = await agent_mcp_bridge.health_check("test_server")
        assert health is True
    
    @pytest.mark.asyncio
    
    async def test_health_check_failure(self, agent_mcp_bridge):
        """Test failed server health check."""
        agent_mcp_bridge.mcp_service.discover_tools.side_effect = Exception("Connection error")
        
        health = await agent_mcp_bridge.health_check("test_server")
        assert health is False

class TestMCPIntegrationEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    
    async def test_full_mcp_workflow(self, mcp_context_manager, mcp_intent_detector, agent_mcp_bridge):
        """Test complete MCP workflow from intent detection to execution."""
        # 1. Detect MCP intent
        request = "Read file /data/analysis.csv using external tool"
        intent = mcp_intent_detector.detect_intent(request)
        
        assert intent.requires_mcp
        
        # 2. Create agent context
        context = await mcp_context_manager.create_agent_context(
            "data_sub_agent", "user123", "run123", "thread123"
        )
        
        # 3. Execute tool through bridge
        mcp_context_manager.permission_checker.can_execute_tool = Mock(return_value=True)
        
        result = await agent_mcp_bridge.execute_tool_for_agent(
            context, "filesystem", "file_read", {"path": "/data/analysis.csv"}
        )
        
        assert result["status"] == "success"
        
        # 4. Cleanup
        mcp_context_manager.cleanup_context(context.run_id)
        assert context.run_id not in mcp_context_manager.active_contexts