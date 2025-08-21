"""Unit tests for ProductionTool class and internal execution."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import AsyncMock, patch

# Add project root to path

from netra_backend.app.agents.production_tool import ProductionTool, ToolExecuteResponse
from netra_backend.tests.helpers.tool_dispatcher_assertions import (

# Add project root to path
    assert_production_tool_initialized,
    assert_tool_execute_response_success,
    assert_tool_execute_response_error,
    assert_execution_error_response,
    assert_not_implemented_error
)


class TestProductionTool:
    """Test ProductionTool class."""
    
    def test_production_tool_initialization(self):
        """Test ProductionTool initialization."""
        tool = ProductionTool("test_tool")
        assert_production_tool_initialized(tool, "test_tool")
    async def test_arun_success(self):
        """Test ProductionTool arun method with success."""
        tool = self._setup_arun_success_test()
        result = await self._execute_arun_with_mocks(tool)
        self._verify_arun_success(result)
    async def test_execute_success(self):
        """Test ProductionTool execute method with success."""
        tool = self._setup_execute_success_test()
        result = await tool.execute({"param": "value"}, None, "run_123")
        self._verify_execute_success(result, tool)
    async def test_execute_failure(self):
        """Test ProductionTool execute method with failure."""
        tool = self._setup_execute_failure_test()
        result = await tool.execute({"param": "value"}, None, "run_123")
        self._verify_execute_failure(result)
    
    def test_create_execution_error_response(self):
        """Test _create_execution_error_response method."""
        tool = ProductionTool("test_tool")
        error = Exception("Test error")
        response = tool._create_execution_error_response(error, "run_123")
        assert_execution_error_response(response, "Test error", "test_tool")
    
    def _setup_arun_success_test(self) -> ProductionTool:
        """Setup arun success test."""
        tool = ProductionTool("test_tool")
        tool.execute = AsyncMock(return_value={"success": True, "data": "test_result"})
        return tool
    
    async def _execute_arun_with_mocks(self, tool: ProductionTool):
        """Execute arun with reliability mocks."""
        with patch.object(tool, 'reliability') as mock_reliability:
            mock_reliability.execute_safely = AsyncMock(return_value=ToolExecuteResponse(success=True, data="test_result"))
            return await tool.arun({"param": "value"})
    
    def _verify_arun_success(self, result: ToolExecuteResponse) -> None:
        """Verify arun success result."""
        assert isinstance(result, ToolExecuteResponse)
        assert result.success is True
        assert result.data == "test_result"
    
    def _setup_execute_success_test(self) -> ProductionTool:
        """Setup execute success test."""
        tool = ProductionTool("test_tool")
        tool._execute_with_reliability_wrapper = AsyncMock(return_value={"success": True, "data": "result"})
        return tool
    
    def _verify_execute_success(self, result, tool: ProductionTool) -> None:
        """Verify execute success result."""
        assert result == {"success": True, "data": "result"}
        tool._execute_with_reliability_wrapper.assert_called_once()
    
    def _setup_execute_failure_test(self) -> ProductionTool:
        """Setup execute failure test."""
        tool = ProductionTool("test_tool")
        tool._execute_with_reliability_wrapper = AsyncMock(side_effect=Exception("Tool failed"))
        return tool
    
    def _verify_execute_failure(self, result) -> None:
        """Verify execute failure result."""
        assert_tool_execute_response_error(result, "Tool failed")
        assert result["metadata"]["tool"] == "test_tool"
        assert result["metadata"]["run_id"] == "run_123"


class TestProductionToolInternalExecution:
    """Test ProductionTool internal execution methods."""
    async def test_execute_internal_synthetic_tools(self):
        """Test _execute_internal with synthetic tools."""
        tool = self._setup_synthetic_tool_test()
        result = await tool._execute_internal({}, None, "run_123")
        self._verify_synthetic_tool_result(result, tool)
    async def test_execute_internal_corpus_tools(self):
        """Test _execute_internal with corpus tools."""
        tool = self._setup_corpus_tool_test()
        result = await tool._execute_internal({}, None, "run_123")
        self._verify_corpus_tool_result(result, tool)
    async def test_execute_internal_default(self):
        """Test _execute_internal with default fallback."""
        tool = self._setup_default_tool_test()
        result = await tool._execute_internal({}, None, "run_123")
        assert_not_implemented_error(result, "unknown_tool")
    async def test_try_synthetic_tools_batch_generation(self):
        """Test _try_synthetic_tools with batch generation."""
        tool = self._setup_batch_generation_test()
        with patch('app.services.synthetic_data.synthetic_data_service.generate_batch') as mock_service:
            mock_service.return_value = [{"data": "item1"}, {"data": "item2"}]
            result = await tool._try_synthetic_tools({"batch_size": 100})
            self._verify_batch_generation_result_real(result)
    async def test_try_synthetic_tools_validation(self):
        """Test _try_synthetic_tools with validation."""
        tool = self._setup_validation_test()
        result = await tool._try_synthetic_tools({"data": "test_data"})
        assert_tool_execute_response_success(result)
    async def test_try_synthetic_tools_storage(self):
        """Test _try_synthetic_tools with storage."""
        tool = self._setup_storage_test()
        result = await tool._try_synthetic_tools({"data": "test_data"})
        assert_tool_execute_response_success(result)
    async def test_try_corpus_tools_create(self):
        """Test _try_corpus_tools with create operation."""
        tool = self._setup_corpus_create_test()
        with patch('app.services.corpus.corpus_service.create_corpus') as mock_service:
            from unittest.mock import Mock
            mock_corpus = Mock()
            mock_corpus.id = "test_corpus_123"
            mock_corpus.name = "test_corpus"
            mock_service.return_value = mock_corpus
            result = await tool._try_corpus_tools({"name": "test_corpus", "description": "test"})
            self._verify_corpus_create_result_real(result)
    async def test_try_corpus_tools_search(self):
        """Test _try_corpus_tools with search operation."""
        tool = self._setup_corpus_search_test()
        with patch('app.services.corpus.corpus_service.search_corpus_content') as mock_service:
            mock_service.return_value = {"results": ["doc1", "doc2"], "total": 2}
            result = await tool._try_corpus_tools({"corpus_id": "123", "query": "test"})
            assert_tool_execute_response_success(result)
    async def test_try_corpus_tools_unknown(self):
        """Test _try_corpus_tools with unknown corpus operation."""
        tool = ProductionTool("unknown_corpus_tool")
        result = await tool._try_corpus_tools({})
        assert result is None
    
    def _setup_synthetic_tool_test(self) -> ProductionTool:
        """Setup synthetic tool test."""
        tool = ProductionTool("generate_synthetic_data_batch")
        tool._try_synthetic_tools = AsyncMock(return_value={"success": True, "data": "synthetic_data"})
        return tool
    
    def _verify_synthetic_tool_result(self, result, tool: ProductionTool) -> None:
        """Verify synthetic tool execution result."""
        assert result == {"success": True, "data": "synthetic_data"}
        tool._try_synthetic_tools.assert_called_once()
    
    def _setup_corpus_tool_test(self) -> ProductionTool:
        """Setup corpus tool test."""
        tool = ProductionTool("create_corpus")
        tool._try_synthetic_tools = AsyncMock(return_value=None)
        tool._try_corpus_tools = AsyncMock(return_value={"success": True, "data": "corpus_created"})
        return tool
    
    def _verify_corpus_tool_result(self, result, tool: ProductionTool) -> None:
        """Verify corpus tool execution result."""
        assert result == {"success": True, "data": "corpus_created"}
        tool._try_corpus_tools.assert_called_once()
    
    def _setup_default_tool_test(self) -> ProductionTool:
        """Setup default tool test."""
        tool = ProductionTool("unknown_tool")
        tool._try_synthetic_tools = AsyncMock(return_value=None)
        tool._try_corpus_tools = AsyncMock(return_value=None)
        return tool
    
    def _setup_batch_generation_test(self) -> ProductionTool:
        """Setup batch generation test."""
        tool = ProductionTool("generate_synthetic_data_batch")
        tool._execute_synthetic_data_batch = AsyncMock(return_value={"success": True, "batch_size": 100})
        return tool
    
    def _verify_batch_generation_result_real(self, result) -> None:
        """Verify batch generation result with real service response."""
        assert result["success"] is True
        assert "data" in result
        assert result["metadata"]["tool"] == "generate_synthetic_data_batch"
    
    def _setup_validation_test(self) -> ProductionTool:
        """Setup validation test."""
        tool = ProductionTool("validate_synthetic_data")
        tool._execute_validate_synthetic_data = AsyncMock(return_value={"success": True, "valid": True})
        return tool
    
    def _setup_storage_test(self) -> ProductionTool:
        """Setup storage test."""
        tool = ProductionTool("store_synthetic_data")
        tool._execute_store_synthetic_data = AsyncMock(return_value={"success": True, "stored": True})
        return tool
    
    def _setup_corpus_create_test(self) -> ProductionTool:
        """Setup corpus create test."""
        tool = ProductionTool("create_corpus")
        tool._execute_create_corpus = AsyncMock(return_value={"success": True, "corpus_id": "123"})
        return tool
    
    def _verify_corpus_create_result_real(self, result) -> None:
        """Verify corpus create result with real service response."""
        assert result["success"] is True
        assert result["data"]["corpus_id"] == "test_corpus_123"
        assert result["data"]["name"] == "test_corpus"
    
    def _setup_corpus_search_test(self) -> ProductionTool:
        """Setup corpus search test."""
        tool = ProductionTool("search_corpus")
        tool._execute_search_corpus = AsyncMock(return_value={"success": True, "results": []})
        return tool