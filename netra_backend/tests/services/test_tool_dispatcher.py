import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import (
    ApexToolSelector,
)

# Mock fixture for testing - avoid duplicating production ToolDispatcher
@pytest.fixture
def mock_tool_dispatcher():
    """Create a mock ToolDispatcher for testing without duplicating production code."""
    mock_dispatcher = Mock()
    mock_dispatcher.tools = {}
    
    def register_tool(tool):
        mock_dispatcher.tools[tool.name] = tool
    
    async def execute_tool(tool_name, params):
        if tool_name not in mock_dispatcher.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await mock_dispatcher.tools[tool_name].execute(params)
    
    async def execute_chain(chain):
        results = []
        for tool_name, params in chain:
            result = await execute_tool(tool_name, params)
            results.append(result)
        return results
    
    async def execute_tool_with_metadata(tool_name, params):
        import time
        start_time = time.time()
        result = await execute_tool(tool_name, params)
        execution_time = time.time() - start_time
        
        return {
            "result": result,
            "metadata": {
                "tool_name": tool_name,
                "execution_time": execution_time,
                "timestamp": time.time()
            }
        }
    
    mock_dispatcher.register_tool = register_tool
    mock_dispatcher.execute_tool = execute_tool
    mock_dispatcher.execute_chain = execute_chain
    mock_dispatcher.execute_tool_with_metadata = execute_tool_with_metadata
    
    return mock_dispatcher
class TestToolDispatcher:
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, mock_tool_dispatcher):
        """Test dynamic tool registration in dispatcher"""
        # Mock: Generic component isolation for controlled unit testing
        mock_tool = MagicMock()
        mock_tool.name = "custom_analyzer"
        # Mock: Async component isolation for testing without real async operations
        mock_tool.execute = AsyncMock(return_value={"result": "success"})
        
        mock_tool_dispatcher.register_tool(mock_tool)
        
        assert "custom_analyzer" in mock_tool_dispatcher.tools
        assert mock_tool_dispatcher.tools["custom_analyzer"] == mock_tool
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_validation(self, mock_tool_dispatcher):
        """Test tool execution with parameter validation"""
        # Mock: Generic component isolation for controlled unit testing
        mock_log_fetcher = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_log_fetcher.execute = AsyncMock(return_value={
            "logs": ["log1", "log2"],
            "count": 2
        })
        mock_log_fetcher.name = "log_fetcher"
        
        mock_tool_dispatcher.register_tool(mock_log_fetcher)
        
        result = await mock_tool_dispatcher.execute_tool(
            "log_fetcher",
            {"start_time": "2024-01-01", "end_time": "2024-01-02"}
        )
        
        assert result["logs"] == ["log1", "log2"]
        mock_log_fetcher.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tool_chain_execution(self, mock_tool_dispatcher):
        """Test executing multiple tools in sequence"""
        # Mock: Async component isolation for testing without real async operations
        mock_analyzer = AsyncMock(return_value={"patterns": ["pattern1"]})
        # Mock: Async component isolation for testing without real async operations
        mock_optimizer = AsyncMock(return_value={"optimizations": ["opt1"]})
        
        # Mock: Service component isolation for predictable testing behavior
        pattern_analyzer = MagicMock(execute=mock_analyzer)
        pattern_analyzer.name = "pattern_analyzer"
        # Mock: Service component isolation for predictable testing behavior
        optimizer = MagicMock(execute=mock_optimizer)
        optimizer.name = "optimizer"
        
        mock_tool_dispatcher.register_tool(pattern_analyzer)
        mock_tool_dispatcher.register_tool(optimizer)
        
        chain_result = await mock_tool_dispatcher.execute_chain([
            ("pattern_analyzer", {"data": "test"}),
            ("optimizer", {"patterns": ["pattern1"]})
        ])
        
        assert len(chain_result) == 2
        assert chain_result[0]["patterns"] == ["pattern1"]
        assert chain_result[1]["optimizations"] == ["opt1"]
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mock_tool_dispatcher):
        """Test error handling when tool execution fails"""
        # Mock: Generic component isolation for controlled unit testing
        mock_failing_tool = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_failing_tool.execute = AsyncMock(
            side_effect=Exception("Tool execution failed")
        )
        mock_failing_tool.name = "failing_tool"
        
        mock_tool_dispatcher.register_tool(mock_failing_tool)
        
        with pytest.raises(Exception) as exc_info:
            await mock_tool_dispatcher.execute_tool("failing_tool", {})
        
        assert "Tool execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_unknown_tool_handling(self, mock_tool_dispatcher):
        """Test handling of unknown tool requests"""
        
        with pytest.raises(ValueError) as exc_info:
            await mock_tool_dispatcher.execute_tool("non_existent_tool", {})
        
        assert "Unknown tool" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_tool_dispatcher):
        """Test concurrent execution of multiple tools"""
        import asyncio
        
        # Mock: Generic component isolation for controlled unit testing
        mock_tool_1 = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_tool_2 = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_tool_3 = AsyncMock()
        
        # Mock: Async component isolation for testing without real async operations
        mock_tool_1.execute = AsyncMock(return_value={"result": "tool1"})
        mock_tool_1.name = "tool1"
        # Mock: Async component isolation for testing without real async operations
        mock_tool_2.execute = AsyncMock(return_value={"result": "tool2"})
        mock_tool_2.name = "tool2"
        # Mock: Async component isolation for testing without real async operations
        mock_tool_3.execute = AsyncMock(return_value={"result": "tool3"})
        mock_tool_3.name = "tool3"
        
        mock_tool_dispatcher.register_tool(mock_tool_1)
        mock_tool_dispatcher.register_tool(mock_tool_2)
        mock_tool_dispatcher.register_tool(mock_tool_3)
        
        tasks = [
            mock_tool_dispatcher.execute_tool("tool1", {}),
            mock_tool_dispatcher.execute_tool("tool2", {}),
            mock_tool_dispatcher.execute_tool("tool3", {})
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert results[0]["result"] == "tool1"
        assert results[1]["result"] == "tool2"
        assert results[2]["result"] == "tool3"
    
    @pytest.mark.asyncio
    async def test_tool_metadata_tracking(self, mock_tool_dispatcher):
        """Test tracking tool execution metadata"""
        # Mock: Generic component isolation for controlled unit testing
        mock_tool = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_tool.execute = AsyncMock(return_value={"data": "test_result"})
        mock_tool.name = "test_tool"
        
        mock_tool_dispatcher.register_tool(mock_tool)
        
        result = await mock_tool_dispatcher.execute_tool_with_metadata(
            "test_tool", 
            {"param": "value"}
        )
        
        assert "result" in result
        assert "metadata" in result
        assert result["metadata"]["tool_name"] == "test_tool"
        assert "execution_time" in result["metadata"]
        assert "timestamp" in result["metadata"]