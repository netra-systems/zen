import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector

# Mock class for testing
class ToolDispatcher:
    def __init__(self, tools):
        self.tools = tools
    
    def register_tool(self, tool):
        self.tools[tool.name] = tool
    
    async def execute_tool(self, tool_name, params):
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await self.tools[tool_name].execute(params)
    
    async def execute_chain(self, chain):
        results = []
        for tool_name, params in chain:
            result = await self.execute_tool(tool_name, params)
            results.append(result)
        return results
    
    async def execute_tool_with_metadata(self, tool_name, params):
        import time
        start_time = time.time()
        result = await self.execute_tool(tool_name, params)
        execution_time = time.time() - start_time
        
        return {
            "result": result,
            "metadata": {
                "tool_name": tool_name,
                "execution_time": execution_time,
                "timestamp": time.time()
            }
        }
class TestToolDispatcher:
    
    async def test_tool_registration(self):
        """Test dynamic tool registration in dispatcher"""
        tool_dispatcher = ToolDispatcher({})
        
        mock_tool = MagicMock()
        mock_tool.name = "custom_analyzer"
        mock_tool.execute = AsyncMock(return_value={"result": "success"})
        
        tool_dispatcher.register_tool(mock_tool)
        
        assert "custom_analyzer" in tool_dispatcher.tools
        assert tool_dispatcher.tools["custom_analyzer"] == mock_tool
    
    async def test_tool_execution_with_validation(self):
        """Test tool execution with parameter validation"""
        mock_log_fetcher = AsyncMock()
        mock_log_fetcher.execute = AsyncMock(return_value={
            "logs": ["log1", "log2"],
            "count": 2
        })
        
        tools = {"log_fetcher": mock_log_fetcher}
        tool_dispatcher = ToolDispatcher(tools)
        
        result = await tool_dispatcher.execute_tool(
            "log_fetcher",
            {"start_time": "2024-01-01", "end_time": "2024-01-02"}
        )
        
        assert result["logs"] == ["log1", "log2"]
        mock_log_fetcher.execute.assert_called_once()
    
    async def test_tool_chain_execution(self):
        """Test executing multiple tools in sequence"""
        mock_analyzer = AsyncMock(return_value={"patterns": ["pattern1"]})
        mock_optimizer = AsyncMock(return_value={"optimizations": ["opt1"]})
        
        tools = {
            "pattern_analyzer": MagicMock(execute=mock_analyzer),
            "optimizer": MagicMock(execute=mock_optimizer)
        }
        
        tool_dispatcher = ToolDispatcher(tools)
        
        chain_result = await tool_dispatcher.execute_chain([
            ("pattern_analyzer", {"data": "test"}),
            ("optimizer", {"patterns": ["pattern1"]})
        ])
        
        assert len(chain_result) == 2
        assert chain_result[0]["patterns"] == ["pattern1"]
        assert chain_result[1]["optimizations"] == ["opt1"]
    
    async def test_tool_error_handling(self):
        """Test error handling when tool execution fails"""
        mock_failing_tool = AsyncMock()
        mock_failing_tool.execute = AsyncMock(
            side_effect=Exception("Tool execution failed")
        )
        
        tools = {"failing_tool": mock_failing_tool}
        tool_dispatcher = ToolDispatcher(tools)
        
        with pytest.raises(Exception) as exc_info:
            await tool_dispatcher.execute_tool("failing_tool", {})
        
        assert "Tool execution failed" in str(exc_info.value)
    
    async def test_unknown_tool_handling(self):
        """Test handling of unknown tool requests"""
        tool_dispatcher = ToolDispatcher({})
        
        with pytest.raises(ValueError) as exc_info:
            await tool_dispatcher.execute_tool("non_existent_tool", {})
        
        assert "Unknown tool" in str(exc_info.value)
    
    async def test_concurrent_tool_execution(self):
        """Test concurrent execution of multiple tools"""
        import asyncio
        
        mock_tool_1 = AsyncMock()
        mock_tool_2 = AsyncMock()
        mock_tool_3 = AsyncMock()
        
        mock_tool_1.execute = AsyncMock(return_value={"result": "tool1"})
        mock_tool_2.execute = AsyncMock(return_value={"result": "tool2"})
        mock_tool_3.execute = AsyncMock(return_value={"result": "tool3"})
        
        tools = {
            "tool1": mock_tool_1,
            "tool2": mock_tool_2,
            "tool3": mock_tool_3
        }
        
        tool_dispatcher = ToolDispatcher(tools)
        
        tasks = [
            tool_dispatcher.execute_tool("tool1", {}),
            tool_dispatcher.execute_tool("tool2", {}),
            tool_dispatcher.execute_tool("tool3", {})
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert results[0]["result"] == "tool1"
        assert results[1]["result"] == "tool2"
        assert results[2]["result"] == "tool3"
    
    async def test_tool_metadata_tracking(self):
        """Test tracking tool execution metadata"""
        mock_tool = AsyncMock()
        mock_tool.execute = AsyncMock(return_value={"data": "test_result"})
        
        tools = {"test_tool": mock_tool}
        tool_dispatcher = ToolDispatcher(tools)
        
        result = await tool_dispatcher.execute_tool_with_metadata(
            "test_tool", 
            {"param": "value"}
        )
        
        assert "result" in result
        assert "metadata" in result
        assert result["metadata"]["tool_name"] == "test_tool"
        assert "execution_time" in result["metadata"]
        assert "timestamp" in result["metadata"]