"""
Tests for MCP Tool Registry

Test tool registration, discovery, and execution.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.mcp.tools.tool_registry import ToolRegistry, Tool, ToolExecution
from app.core.exceptions import NetraException


class TestTool:
    """Test Tool model"""
    
    def test_tool_creation(self):
        """Test tool creation"""
        tool = Tool(
            name="test_tool",
            description="Test tool",
            inputSchema={"type": "object"},
            outputSchema={"type": "object"},
            requires_auth=True,
            permissions=["read", "write"],
            category="testing",
            version="2.0.0"
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.inputSchema == {"type": "object"}
        assert tool.outputSchema == {"type": "object"}
        assert tool.requires_auth is True
        assert tool.permissions == ["read", "write"]
        assert tool.category == "testing"
        assert tool.version == "2.0.0"
        
    def test_tool_defaults(self):
        """Test tool default values"""
        tool = Tool(
            name="test",
            description="Test",
            inputSchema={}
        )
        
        assert tool.handler is None
        assert tool.requires_auth is True
        assert tool.permissions == []
        assert tool.category is None
        assert tool.version == "1.0.0"


class TestToolExecution:
    """Test ToolExecution model"""
    
    def test_execution_creation(self):
        """Test execution record creation"""
        execution = ToolExecution(
            tool_name="test_tool",
            session_id="session123",
            input_params={"key": "value"},
            output_result={"result": "success"},
            execution_time_ms=100,
            status="success"
        )
        
        assert execution.tool_name == "test_tool"
        assert execution.session_id == "session123"
        assert execution.input_params == {"key": "value"}
        assert execution.output_result == {"result": "success"}
        assert execution.execution_time_ms == 100
        assert execution.status == "success"
        assert execution.error is None
        assert isinstance(execution.created_at, datetime)


class TestToolRegistry:
    """Test tool registry functionality"""
    
    @pytest.fixture
    def registry(self):
        """Create tool registry"""
        return ToolRegistry()
        
    def test_registry_initialization(self, registry):
        """Test registry initialization with built-in tools"""
        assert len(registry.tools) > 0
        assert "run_agent" in registry.tools
        assert "get_agent_status" in registry.tools
        assert "list_agents" in registry.tools
        assert "analyze_workload" in registry.tools
        assert "optimize_prompt" in registry.tools
        assert "query_corpus" in registry.tools
        assert "generate_synthetic_data" in registry.tools
        assert "create_thread" in registry.tools
        assert "get_thread_history" in registry.tools
        
    def test_register_tool(self, registry):
        """Test registering a new tool"""
        tool = Tool(
            name="custom_tool",
            description="Custom tool",
            inputSchema={"type": "object"}
        )
        
        registry.register_tool(tool)
        
        assert "custom_tool" in registry.tools
        assert registry.tools["custom_tool"] == tool
        
    def test_register_tool_overwrite(self, registry, caplog):
        """Test overwriting existing tool"""
        tool1 = Tool(name="test", description="First", inputSchema={})
        tool2 = Tool(name="test", description="Second", inputSchema={})
        
        registry.register_tool(tool1)
        registry.register_tool(tool2)
        
        assert registry.tools["test"].description == "Second"
        assert "Overwriting existing tool" in caplog.text
        
    def test_unregister_tool(self, registry):
        """Test unregistering a tool"""
        tool = Tool(name="temp_tool", description="Temp", inputSchema={})
        registry.register_tool(tool)
        
        assert "temp_tool" in registry.tools
        
        registry.unregister_tool("temp_tool")
        
        assert "temp_tool" not in registry.tools
        
    @pytest.mark.asyncio
    async def test_list_tools(self, registry):
        """Test listing available tools"""
        tools = await registry.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool format
        tool = tools[0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        
    @pytest.mark.asyncio
    async def test_list_tools_with_category(self, registry):
        """Test listing tools includes category"""
        tools = await registry.list_tools()
        
        agent_tools = [t for t in tools if t.get("category") == "Agent Operations"]
        assert len(agent_tools) > 0
        
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, registry):
        """Test successful tool execution"""
        async def test_handler(arguments, session_id):
            return {"result": "success", "args": arguments}
            
        tool = Tool(
            name="test_exec",
            description="Test",
            inputSchema={},
            handler=test_handler
        )
        registry.register_tool(tool)
        
        result = await registry.execute_tool(
            "test_exec",
            {"arg1": "value1"},
            "session123"
        )
        
        assert result["isError"] is False
        assert len(result["content"]) == 1
        assert result["content"][0]["args"]["arg1"] == "value1"
        
        # Check execution was recorded
        assert len(registry.executions) == 1
        execution = registry.executions[0]
        assert execution.tool_name == "test_exec"
        assert execution.status == "success"
        
    @pytest.mark.asyncio
    async def test_execute_tool_sync_handler(self, registry):
        """Test executing tool with synchronous handler"""
        def sync_handler(arguments, session_id):
            return {"sync": True, "args": arguments}
            
        tool = Tool(
            name="sync_tool",
            description="Sync tool",
            inputSchema={},
            handler=sync_handler
        )
        registry.register_tool(tool)
        
        result = await registry.execute_tool("sync_tool", {}, None)
        
        assert result["isError"] is False
        assert result["content"][0]["sync"] is True
        
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, registry):
        """Test executing non-existent tool"""
        result = await registry.execute_tool("nonexistent", {}, None)
        
        assert result["isError"] is True
        assert "Tool not found" in result["content"][0]["text"]
        
        # Check error was recorded
        assert len(registry.executions) == 1
        assert registry.executions[0].status == "error"
        
    @pytest.mark.asyncio
    async def test_execute_tool_no_handler(self, registry):
        """Test executing tool without handler"""
        tool = Tool(
            name="no_handler",
            description="No handler",
            inputSchema={}
        )
        registry.register_tool(tool)
        
        result = await registry.execute_tool("no_handler", {}, None)
        
        assert result["isError"] is True
        assert "has no handler" in result["content"][0]["text"]
        
    @pytest.mark.asyncio
    async def test_execute_tool_handler_error(self, registry):
        """Test tool execution with handler error"""
        async def error_handler(arguments, session_id):
            raise ValueError("Handler error")
            
        tool = Tool(
            name="error_tool",
            description="Error tool",
            inputSchema={},
            handler=error_handler
        )
        registry.register_tool(tool)
        
        result = await registry.execute_tool("error_tool", {}, None)
        
        assert result["isError"] is True
        assert "Handler error" in result["content"][0]["text"]
        
        # Check error was recorded
        execution = registry.executions[0]
        assert execution.status == "error"
        assert "Handler error" in execution.error
        
    @pytest.mark.asyncio
    async def test_execute_tool_list_content(self, registry):
        """Test tool returning list content"""
        async def list_handler(arguments, session_id):
            return [
                {"type": "text", "text": "Item 1"},
                {"type": "text", "text": "Item 2"}
            ]
            
        tool = Tool(
            name="list_tool",
            description="List tool",
            inputSchema={},
            handler=list_handler
        )
        registry.register_tool(tool)
        
        result = await registry.execute_tool("list_tool", {}, None)
        
        assert result["isError"] is False
        assert len(result["content"]) == 2
        assert result["content"][0]["text"] == "Item 1"
        assert result["content"][1]["text"] == "Item 2"
        
    @pytest.mark.asyncio
    async def test_builtin_handlers_placeholder(self, registry):
        """Test built-in tool handlers (placeholder implementations)"""
        # Test run_agent handler
        result = await registry.execute_tool(
            "run_agent",
            {"agent_name": "TestAgent", "input_data": {}},
            None
        )
        assert result["isError"] is False
        assert "run_id" in result["content"][0]
        
        # Test get_agent_status handler
        result = await registry.execute_tool(
            "get_agent_status",
            {"run_id": "test123"},
            None
        )
        assert result["isError"] is False
        
        # Test list_agents handler
        result = await registry.execute_tool(
            "list_agents",
            {},
            None
        )
        assert result["isError"] is False
        agents = json.loads(result["content"][0]["text"])
        assert isinstance(agents, list)
        
        # Test analyze_workload handler
        result = await registry.execute_tool(
            "analyze_workload",
            {"workload_data": {}},
            None
        )
        assert result["isError"] is False
        
        # Test optimize_prompt handler
        result = await registry.execute_tool(
            "optimize_prompt",
            {"prompt": "Test prompt"},
            None
        )
        assert result["isError"] is False
        
        # Test query_corpus handler
        result = await registry.execute_tool(
            "query_corpus",
            {"query": "test query"},
            None
        )
        assert result["isError"] is False
        
        # Test generate_synthetic_data handler
        result = await registry.execute_tool(
            "generate_synthetic_data",
            {"schema": {}},
            None
        )
        assert result["isError"] is False
        
        # Test create_thread handler
        result = await registry.execute_tool(
            "create_thread",
            {},
            None
        )
        assert result["isError"] is False
        assert "thread_id" in result["content"][0]
        
        # Test get_thread_history handler
        result = await registry.execute_tool(
            "get_thread_history",
            {"thread_id": "test123"},
            None
        )
        assert result["isError"] is False
        
    @pytest.mark.asyncio
    async def test_shutdown(self, registry):
        """Test registry shutdown"""
        registry.register_tool(Tool(name="test", description="Test", inputSchema={}))
        registry.executions.append(ToolExecution(
            tool_name="test",
            session_id="session",
            input_params={}
        ))
        
        await registry.shutdown()
        
        assert len(registry.tools) == 0
        assert len(registry.executions) == 0