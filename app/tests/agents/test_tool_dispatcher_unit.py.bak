"""Unit tests for ToolDispatcher with 70%+ coverage.
Tests all dispatcher methods, tool registration, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.agents.tool_dispatcher import (
    ToolDispatcher, 
    ToolDispatchRequest, 
    ToolDispatchResponse, 
    ToolExecuteResponse,
    ProductionTool
)
from app.agents.state import DeepAgentState
from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
from langchain_core.tools import BaseTool


class MockBaseTool:
    """Mock tool for testing."""
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
    
    async def arun(self, kwargs: Dict[str, Any]) -> Any:
        if self.should_fail:
            raise Exception(f"Tool {self.name} failed")
        return {"result": f"Tool {self.name} executed with {kwargs}"}


class TestToolDispatcherInitialization:
    """Test ToolDispatcher initialization and tool registration."""
    
    def test_init_empty(self):
        """Test initialization without tools."""
        dispatcher = ToolDispatcher()
        
        # Verify synthetic and corpus tools are registered
        assert "generate_synthetic_data_batch" in dispatcher.tools
        assert "create_corpus" in dispatcher.tools
        assert "search_corpus" in dispatcher.tools
        assert len(dispatcher.tools) > 0
    
    def test_init_with_tools(self):
        """Test initialization with provided tools."""
        tool1 = MockBaseTool("test_tool_1")
        tool2 = MockBaseTool("test_tool_2")
        tools = [tool1, tool2]
        
        dispatcher = ToolDispatcher(tools)
        
        # Verify provided tools are registered
        assert "test_tool_1" in dispatcher.tools
        assert "test_tool_2" in dispatcher.tools
        assert dispatcher.tools["test_tool_1"] == tool1
        assert dispatcher.tools["test_tool_2"] == tool2
    
    def test_register_synthetic_tools(self):
        """Test synthetic tools registration."""
        dispatcher = ToolDispatcher()
        
        synthetic_tools = [
            "generate_synthetic_data_batch",
            "validate_synthetic_data", 
            "store_synthetic_data"
        ]
        
        for tool_name in synthetic_tools:
            assert tool_name in dispatcher.tools
            assert isinstance(dispatcher.tools[tool_name], ProductionTool)
    
    def test_register_corpus_tools(self):
        """Test corpus tools registration."""
        dispatcher = ToolDispatcher()
        
        corpus_tools = [
            "create_corpus", "search_corpus", "update_corpus", "delete_corpus",
            "analyze_corpus", "export_corpus", "import_corpus", "validate_corpus"
        ]
        
        for tool_name in corpus_tools:
            assert tool_name in dispatcher.tools
            assert isinstance(dispatcher.tools[tool_name], ProductionTool)


class TestToolDispatcherCoreOperations:
    """Test core dispatcher operations."""
    
    def test_has_tool(self):
        """Test has_tool method."""
        dispatcher = ToolDispatcher()
        
        # Test existing tool
        assert dispatcher.has_tool("create_corpus") == True
        
        # Test non-existing tool
        assert dispatcher.has_tool("nonexistent_tool") == False
    
    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """Test successful tool dispatch."""
        tool = MockBaseTool("test_tool")
        dispatcher = ToolDispatcher([tool])
        
        result = await dispatcher.dispatch("test_tool", param1="value1", param2="value2")
        
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.tool_input.tool_name == "test_tool"
        assert result.tool_input.kwargs == {"param1": "value1", "param2": "value2"}
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found(self):
        """Test dispatch with non-existent tool."""
        dispatcher = ToolDispatcher()
        
        result = await dispatcher.dispatch("nonexistent_tool", param="value")
        
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert "Tool nonexistent_tool not found" in result.message
        assert result.tool_input.tool_name == "nonexistent_tool"
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_failure(self):
        """Test dispatch with failing tool."""
        failing_tool = MockBaseTool("failing_tool", should_fail=True)
        dispatcher = ToolDispatcher([failing_tool])
        
        result = await dispatcher.dispatch("failing_tool", param="value")
        
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert "Tool failing_tool failed" in result.message
    
    def test_create_error_result(self):
        """Test _create_error_result method."""
        dispatcher = ToolDispatcher()
        
        tool_input = ToolInput(tool_name="test_tool", kwargs={"param": "value"})
        error_message = "Test error message"
        
        result = dispatcher._create_error_result(tool_input, error_message)
        
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert result.message == error_message
        assert result.tool_input == tool_input
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test _execute_tool method with success."""
        dispatcher = ToolDispatcher()
        tool = MockBaseTool("test_tool")
        tool_input = ToolInput(tool_name="test_tool", kwargs={"param": "value"})
        kwargs = {"param": "value"}
        
        result = await dispatcher._execute_tool(tool_input, tool, kwargs)
        
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.payload is not None
        assert isinstance(result.payload, SimpleToolPayload)
    
    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """Test _execute_tool method with failure."""
        dispatcher = ToolDispatcher()
        failing_tool = MockBaseTool("failing_tool", should_fail=True)
        tool_input = ToolInput(tool_name="failing_tool", kwargs={})
        
        result = await dispatcher._execute_tool(tool_input, failing_tool, {})
        
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert "Tool failing_tool failed" in result.message


class TestToolDispatcherAdvancedOperations:
    """Test advanced dispatcher operations."""
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_success(self):
        """Test dispatch_tool method with success."""
        tool = MockBaseTool("test_tool")
        dispatcher = ToolDispatcher([tool])
        state = DeepAgentState(user_request="test")
        
        result = await dispatcher.dispatch_tool(
            "test_tool", 
            {"param": "value"}, 
            state, 
            "run_123"
        )
        
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == True
        assert result.result is not None
        assert result.error is None
        assert result.metadata["tool_name"] == "test_tool"
        assert result.metadata["run_id"] == "run_123"
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found(self):
        """Test dispatch_tool with non-existent tool."""
        dispatcher = ToolDispatcher()
        state = DeepAgentState(user_request="test")
        
        result = await dispatcher.dispatch_tool(
            "nonexistent_tool",
            {"param": "value"},
            state,
            "run_123"
        )
        
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == False
        assert result.error == "Tool nonexistent_tool not found"
        assert result.result is None
    
    def test_create_tool_not_found_response(self):
        """Test _create_tool_not_found_response method."""
        dispatcher = ToolDispatcher()
        
        response = dispatcher._create_tool_not_found_response("missing_tool", "run_123")
        
        assert isinstance(response, ToolDispatchResponse)
        assert response.success == False
        assert response.error == "Tool missing_tool not found"
        assert response.result is None
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_error_handling_success(self):
        """Test _execute_tool_with_error_handling with success."""
        tool = MockBaseTool("test_tool")
        dispatcher = ToolDispatcher([tool])
        state = DeepAgentState(user_request="test")
        
        response = await dispatcher._execute_tool_with_error_handling(
            tool, "test_tool", {"param": "value"}, state, "run_123"
        )
        
        assert isinstance(response, ToolDispatchResponse)
        assert response.success == True
        assert response.error is None
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_error_handling_failure(self):
        """Test _execute_tool_with_error_handling with failure."""
        failing_tool = MockBaseTool("failing_tool", should_fail=True)
        dispatcher = ToolDispatcher([failing_tool])
        state = DeepAgentState(user_request="test")
        
        response = await dispatcher._execute_tool_with_error_handling(
            failing_tool, "failing_tool", {"param": "value"}, state, "run_123"
        )
        
        assert isinstance(response, ToolDispatchResponse)
        assert response.success == False
        assert "Tool failing_tool failed" in response.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_by_type_production_tool(self):
        """Test _execute_tool_by_type with ProductionTool."""
        dispatcher = ToolDispatcher()
        production_tool = dispatcher.tools["create_corpus"]
        state = DeepAgentState(user_request="test")
        
        # Mock the execute method
        production_tool.execute = AsyncMock(return_value={"success": True})
        
        result = await dispatcher._execute_tool_by_type(
            production_tool, {"param": "value"}, state, "run_123"
        )
        
        assert result == {"success": True}
        production_tool.execute.assert_called_once_with(
            {"param": "value"}, state, "run_123"
        )
    
    @pytest.mark.asyncio
    async def test_execute_tool_by_type_async_tool(self):
        """Test _execute_tool_by_type with async tool."""
        dispatcher = ToolDispatcher()
        async_tool = MockBaseTool("async_tool")
        
        result = await dispatcher._execute_tool_by_type(
            async_tool, {"param": "value"}, None, "run_123"
        )
        
        assert "result" in result
        assert "async_tool" in str(result)
    
    @pytest.mark.asyncio
    async def test_execute_tool_by_type_sync_tool(self):
        """Test _execute_tool_by_type with sync tool."""
        dispatcher = ToolDispatcher()
        
        # Create sync tool mock
        sync_tool = Mock()
        sync_tool.return_value = {"sync": "result"}
        
        # Execute the method
        result = await dispatcher._execute_tool_by_type(sync_tool, {"param": "value"}, None, "run_123")
        
        assert result == {"sync": "result"}
        sync_tool.assert_called_once_with({"param": "value"})
    
    def test_create_success_response(self):
        """Test _create_success_response method."""
        dispatcher = ToolDispatcher()
        
        response = dispatcher._create_success_response(
            {"data": "test"}, "test_tool", "run_123"
        )
        
        assert isinstance(response, ToolDispatchResponse)
        assert response.success == True
        assert response.result == {"data": "test"}
        assert response.error is None
        assert response.metadata["tool_name"] == "test_tool"
        assert response.metadata["run_id"] == "run_123"
    
    def test_create_error_response(self):
        """Test _create_error_response method."""
        dispatcher = ToolDispatcher()
        error = Exception("Test error")
        
        response = dispatcher._create_error_response(error, "test_tool", "run_123")
        
        assert isinstance(response, ToolDispatchResponse)
        assert response.success == False
        assert response.result is None
        assert response.error == "Test error"
        assert response.metadata["tool_name"] == "test_tool"
        assert response.metadata["run_id"] == "run_123"


class TestProductionTool:
    """Test ProductionTool class."""
    
    def test_production_tool_initialization(self):
        """Test ProductionTool initialization."""
        tool = ProductionTool("test_tool")
        
        assert tool.name == "test_tool"
        assert hasattr(tool, 'reliability')
    
    @pytest.mark.asyncio
    async def test_arun_success(self):
        """Test ProductionTool arun method with success."""
        tool = ProductionTool("test_tool")
        
        # Mock the execute method
        mock_response = {"success": True, "data": "test_result"}
        tool.execute = AsyncMock(return_value=mock_response)
        
        # Mock the reliability wrapper
        with patch.object(tool, 'reliability') as mock_reliability:
            mock_reliability.execute = AsyncMock(return_value=ToolExecuteResponse(
                success=True, data="test_result"
            ))
            
            result = await tool.arun({"param": "value"})
            
            assert isinstance(result, ToolExecuteResponse)
            assert result.success == True
            assert result.data == "test_result"
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test ProductionTool execute method with success."""
        tool = ProductionTool("test_tool")
        
        # Mock internal execution
        mock_result = {"success": True, "data": "result"}
        tool._execute_with_reliability = AsyncMock(return_value=mock_result)
        
        result = await tool.execute({"param": "value"}, None, "run_123")
        
        assert result == mock_result
        tool._execute_with_reliability.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test ProductionTool execute method with failure."""
        tool = ProductionTool("test_tool")
        
        # Mock failure
        tool._execute_with_reliability = AsyncMock(side_effect=Exception("Tool failed"))
        
        result = await tool.execute({"param": "value"}, None, "run_123")
        
        assert result["success"] == False
        assert "Tool failed" in result["error"]
        assert result["metadata"]["tool"] == "test_tool"
        assert result["metadata"]["run_id"] == "run_123"
    
    def test_create_execution_error_response(self):
        """Test _create_execution_error_response method."""
        tool = ProductionTool("test_tool")
        error = Exception("Test error")
        
        response = tool._create_execution_error_response(error, "run_123")
        
        assert response["success"] == False
        assert response["error"] == "Test error"
        assert response["metadata"]["tool"] == "test_tool"
        assert response["metadata"]["run_id"] == "run_123"


class TestProductionToolInternalExecution:
    """Test ProductionTool internal execution methods."""
    
    @pytest.mark.asyncio
    async def test_execute_internal_synthetic_tools(self):
        """Test _execute_internal with synthetic tools."""
        tool = ProductionTool("generate_synthetic_data_batch")
        
        # Mock synthetic tool execution
        mock_result = {"success": True, "data": "synthetic_data"}
        tool._try_synthetic_tools = AsyncMock(return_value=mock_result)
        
        result = await tool._execute_internal({}, None, "run_123")
        
        assert result == mock_result
        tool._try_synthetic_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_internal_corpus_tools(self):
        """Test _execute_internal with corpus tools."""
        tool = ProductionTool("create_corpus")
        
        # Mock corpus tool execution
        mock_result = {"success": True, "data": "corpus_created"}
        tool._try_synthetic_tools = AsyncMock(return_value=None)
        tool._try_corpus_tools = AsyncMock(return_value=mock_result)
        
        result = await tool._execute_internal({}, None, "run_123")
        
        assert result == mock_result
        tool._try_corpus_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_internal_default(self):
        """Test _execute_internal with default fallback."""
        tool = ProductionTool("unknown_tool")
        
        # Mock all specific tool methods return None
        tool._try_synthetic_tools = AsyncMock(return_value=None)
        tool._try_corpus_tools = AsyncMock(return_value=None)
        
        result = await tool._execute_internal({}, None, "run_123")
        
        assert result["success"] == False
        assert "not implemented" in result["error"]
        assert result["metadata"]["tool"] == "unknown_tool"
    
    @pytest.mark.asyncio
    async def test_try_synthetic_tools_batch_generation(self):
        """Test _try_synthetic_tools with batch generation."""
        tool = ProductionTool("generate_synthetic_data_batch")
        
        # Mock the specific execution method
        mock_result = {"success": True, "batch_size": 100}
        tool._execute_synthetic_data_batch = AsyncMock(return_value=mock_result)
        
        result = await tool._try_synthetic_tools({"batch_size": 100})
        
        assert result == mock_result
        tool._execute_synthetic_data_batch.assert_called_once_with({"batch_size": 100})
    
    @pytest.mark.asyncio
    async def test_try_synthetic_tools_validation(self):
        """Test _try_synthetic_tools with validation."""
        tool = ProductionTool("validate_synthetic_data")
        
        mock_result = {"success": True, "valid": True}
        tool._execute_validate_synthetic_data = AsyncMock(return_value=mock_result)
        
        result = await tool._try_synthetic_tools({"data": "test_data"})
        
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_try_synthetic_tools_storage(self):
        """Test _try_synthetic_tools with storage."""
        tool = ProductionTool("store_synthetic_data")
        
        mock_result = {"success": True, "stored": True}
        tool._execute_store_synthetic_data = AsyncMock(return_value=mock_result)
        
        result = await tool._try_synthetic_tools({"data": "test_data"})
        
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_try_corpus_tools_create(self):
        """Test _try_corpus_tools with create operation."""
        tool = ProductionTool("create_corpus")
        
        mock_result = {"success": True, "corpus_id": "123"}
        tool._execute_create_corpus = AsyncMock(return_value=mock_result)
        
        result = await tool._try_corpus_tools({"name": "test_corpus"})
        
        assert result == mock_result
        tool._execute_create_corpus.assert_called_once_with({"name": "test_corpus"})
    
    @pytest.mark.asyncio
    async def test_try_corpus_tools_search(self):
        """Test _try_corpus_tools with search operation."""
        tool = ProductionTool("search_corpus")
        
        mock_result = {"success": True, "results": []}
        tool._execute_search_corpus = AsyncMock(return_value=mock_result)
        
        result = await tool._try_corpus_tools({"query": "test"})
        
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_try_corpus_tools_unknown(self):
        """Test _try_corpus_tools with unknown corpus operation."""
        tool = ProductionTool("unknown_corpus_tool")
        
        result = await tool._try_corpus_tools({})
        
        assert result is None


class TestProductionToolSpecificOperations:
    """Test specific tool operations."""
    
    @pytest.mark.asyncio
    async def test_execute_synthetic_data_batch_success(self):
        """Test synthetic data batch generation success."""
        tool = ProductionTool("generate_synthetic_data_batch")
        
        with patch('app.services.synthetic_data.synthetic_data_service') as mock_service:
            mock_service.generate_batch = AsyncMock(return_value=["data1", "data2"])
            
            result = await tool._execute_synthetic_data_batch({"batch_size": 2})
            
            assert result["success"] == True
            assert result["data"] == ["data1", "data2"]
            assert result["metadata"]["batch_size"] == 2
    
    @pytest.mark.asyncio
    async def test_execute_synthetic_data_batch_failure(self):
        """Test synthetic data batch generation failure."""
        tool = ProductionTool("generate_synthetic_data_batch")
        
        with patch('app.services.synthetic_data.synthetic_data_service') as mock_service:
            mock_service.generate_batch = AsyncMock(side_effect=Exception("Service error"))
            
            result = await tool._execute_synthetic_data_batch({"batch_size": 2})
            
            assert result["success"] == False
            assert "Failed to generate synthetic data" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_create_corpus_success(self):
        """Test corpus creation success."""
        tool = ProductionTool("create_corpus")
        
        with patch('app.services.corpus.corpus_service') as mock_service:
            mock_corpus = Mock()
            mock_corpus.id = "corpus_123"
            mock_corpus.name = "test_corpus"
            mock_service.create_corpus = AsyncMock(return_value=mock_corpus)
            
            result = await tool._execute_create_corpus({
                "corpus_name": "test_corpus",
                "description": "Test description"
            })
            
            assert result["success"] == True
            assert result["data"]["corpus_id"] == "corpus_123"
            assert result["data"]["name"] == "test_corpus"
    
    @pytest.mark.asyncio
    async def test_execute_create_corpus_failure(self):
        """Test corpus creation failure."""
        tool = ProductionTool("create_corpus")
        
        with patch('app.services.corpus.corpus_service') as mock_service:
            mock_service.create_corpus = AsyncMock(side_effect=Exception("Database error"))
            
            result = await tool._execute_create_corpus({"corpus_name": "test"})
            
            assert result["success"] == False
            assert "Failed to create corpus" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_search_corpus_success(self):
        """Test corpus search success."""
        tool = ProductionTool("search_corpus")
        
        with patch('app.services.corpus.corpus_service') as mock_service:
            mock_results = {"results": ["doc1", "doc2"], "total": 2}
            mock_service.search_corpus_content = AsyncMock(return_value=mock_results)
            
            result = await tool._execute_search_corpus({
                "corpus_id": "123",
                "query": "test",
                "limit": 10
            })
            
            assert result["success"] == True
            assert len(result["data"]["results"]) == 2
            assert result["data"]["total_matches"] == 2
    
    @pytest.mark.asyncio
    async def test_execute_search_corpus_missing_id(self):
        """Test corpus search with missing corpus_id."""
        tool = ProductionTool("search_corpus")
        
        result = await tool._execute_search_corpus({"query": "test"})
        
        assert result["success"] == False
        assert "corpus_id parameter is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_validate_synthetic_data(self):
        """Test synthetic data validation."""
        tool = ProductionTool("validate_synthetic_data")
        
        with patch('app.services.synthetic_data.validate_data') as mock_validate:
            mock_validate.return_value = {"valid": True, "errors": []}
            
            result = await tool._execute_validate_synthetic_data({"data": ["item1", "item2"]})
            
            assert result["success"] == True
            assert result["data"]["valid"] == True
    
    @pytest.mark.asyncio
    async def test_execute_store_synthetic_data(self):
        """Test synthetic data storage."""
        tool = ProductionTool("store_synthetic_data")
        
        with patch('app.services.synthetic_data.synthetic_data_service') as mock_service:
            mock_service.ingest_batch = AsyncMock(return_value={"stored": 10})
            
            result = await tool._execute_store_synthetic_data({
                "data": ["item1", "item2"],
                "table_name": "test_table"
            })
            
            assert result["success"] == True
            assert result["data"]["stored"] == 10
    
    @pytest.mark.asyncio
    async def test_execute_default(self):
        """Test default execution method."""
        tool = ProductionTool("unknown_tool")
        
        result = await tool._execute_default()
        
        assert result["success"] == False
        assert "not implemented" in result["error"]
        assert result["metadata"]["tool"] == "unknown_tool"
        assert result["metadata"]["status"] == "not_implemented"


class TestToolDispatcherEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_dispatch_with_none_parameters(self):
        """Test dispatch with None parameters."""
        dispatcher = ToolDispatcher()
        
        result = await dispatcher.dispatch("create_corpus")
        
        # Should not crash and handle empty parameters
        assert isinstance(result, ToolResult)
    
    @pytest.mark.asyncio
    async def test_dispatch_tool_with_empty_state(self):
        """Test dispatch_tool with minimal state."""
        tool = MockBaseTool("test_tool")
        dispatcher = ToolDispatcher([tool])
        
        # Create minimal state
        state = DeepAgentState(user_request="")
        
        result = await dispatcher.dispatch_tool(
            "test_tool", {}, state, "run_123"
        )
        
        assert result.success == True
    
    def test_register_tool_batch_with_existing_tools(self):
        """Test _register_tool_batch with some existing tools."""
        dispatcher = ToolDispatcher()
        
        # Some tools already exist
        existing_count = len(dispatcher.tools)
        
        # Try to register mix of new and existing
        tool_names = ["create_corpus", "new_tool_1", "new_tool_2"]
        dispatcher._register_tool_batch(tool_names)
        
        # Should have added only the new ones
        assert "new_tool_1" in dispatcher.tools
        assert "new_tool_2" in dispatcher.tools
        assert len(dispatcher.tools) >= existing_count + 2