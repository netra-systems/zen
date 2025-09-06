"""
Comprehensive unit tests for corpus_admin operations_execution.

Business Value: Ensures reliable corpus operation execution with proper tool dispatcher
integration. These operations are critical for enterprise corpus management workflows
and must handle errors gracefully while maintaining data integrity.
"""

import pytest
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.corpus_admin.operations_execution import CorpusExecutionHelper
from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestCorpusExecutionHelper:
    """Test CorpusExecutionHelper initialization and basic functionality."""
    pass

    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock tool dispatcher for testing."""
    pass
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.execute_tool = AsyncNone  # TODO: Use real service instance
        return mock_dispatcher

    @pytest.fixture
    def execution_helper(self, mock_tool_dispatcher):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create CorpusExecutionHelper instance for testing."""
    pass
        return CorpusExecutionHelper(mock_tool_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create sample corpus metadata for testing."""
    pass
        return CorpusMetadata(
            corpus_name="test_corpus",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="Test knowledge base for execution testing",
            tags=["test", "execution"],
            access_level="private"
        )

    @pytest.fixture
    def sample_request(self, sample_metadata):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create sample corpus operation request."""
    pass
        return CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata,
            options={"index_immediately": True}
        )

    def test_initialization(self, mock_tool_dispatcher):
        """Test CorpusExecutionHelper initialization."""
        helper = CorpusExecutionHelper(mock_tool_dispatcher)
        
        assert helper is not None
        assert helper.tool_dispatcher == mock_tool_dispatcher

    def test_initialization_with_none_dispatcher(self):
        """Test initialization with None tool dispatcher."""
    pass
        # Should not raise exception during initialization
        helper = CorpusExecutionHelper(None)
        assert helper.tool_dispatcher is None


class TestExecuteViaToolDispatcher:
    """Test execute_via_tool_dispatcher method."""
    pass

    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.execute_tool = AsyncNone  # TODO: Use real service instance
        return mock_dispatcher

    @pytest.fixture
    def execution_helper(self, mock_tool_dispatcher):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusExecutionHelper(mock_tool_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusMetadata(
            corpus_name="tool_test_corpus",
            corpus_type=CorpusType.DOCUMENTATION,
            description="Test corpus for tool execution",
            access_level="public"
        )

    @pytest.fixture
    def sample_request(self, sample_metadata):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )

    @pytest.mark.asyncio
    async def test_successful_tool_execution(self, execution_helper, sample_request):
        """Test successful tool execution via dispatcher."""
        # Mock successful tool response
        mock_tool_result = {
            "success": True,
            "corpus_id": "created_corpus_123",
            "documents_indexed": 25
        }
        execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
        
        result = await execution_helper.execute_via_tool_dispatcher(
            tool_name="create_corpus",
            request=sample_request,
            run_id="test_run_123",
            result_key="corpus_id"
        )
        
        # Verify result
        assert isinstance(result, CorpusOperationResult)
        assert result.success is True
        assert result.operation == CorpusOperation.CREATE
        assert result.corpus_metadata.corpus_id == "created_corpus_123"
        assert result.affected_documents == 25
        assert result.metadata["corpus_id"] == "created_corpus_123"
        
        # Verify tool was called correctly
        execution_helper.tool_dispatcher.execute_tool.assert_called_once()
        call_args = execution_helper.tool_dispatcher.execute_tool.call_args
        assert call_args.kwargs["tool_name"] == "create_corpus"
        assert call_args.kwargs["run_id"] == "test_run_123"

    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, execution_helper, sample_request):
        """Test tool execution failure handling."""
    pass
        # Mock tool execution failure
        execution_helper.tool_dispatcher.execute_tool.side_effect = Exception("Tool execution failed")
        
        result = await execution_helper.execute_via_tool_dispatcher(
            tool_name="failing_tool",
            request=sample_request,
            run_id="error_run_456",
            result_key="result"
        )
        
        # Verify error result
        assert isinstance(result, CorpusOperationResult)
        assert result.success is False
        assert result.operation == sample_request.operation
        assert result.corpus_metadata == sample_request.corpus_metadata
        assert len(result.errors) == 1
        assert "Tool execution failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_tool_execution_with_different_result_keys(self, execution_helper, sample_request):
        """Test tool execution with different result keys."""
        test_cases = [
            ("corpus_id", "corpus_12345"),
            ("document_count", 100),
            ("status", "completed"),
            ("data", {"key": "value"})
        ]
        
        for result_key, result_value in test_cases:
            mock_tool_result = {
                "success": True,
                result_key: result_value,
                "documents_indexed": 10
            }
            execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
            
            result = await execution_helper.execute_via_tool_dispatcher(
                tool_name="test_tool",
                request=sample_request,
                run_id="key_test_run",
                result_key=result_key
            )
            
            assert result.success is True
            assert result.result_data == result_value
            assert result.metadata[result_key] == result_value

    @pytest.mark.asyncio
    async def test_tool_parameters_building(self, execution_helper, sample_request):
        """Test that tool parameters are built correctly."""
    pass
        mock_tool_result = {"success": True}
        execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
        
        await execution_helper.execute_via_tool_dispatcher(
            tool_name="param_test_tool",
            request=sample_request,
            run_id="param_test_run",
            result_key="result"
        )
        
        # Verify parameters were passed correctly
        call_args = execution_helper.tool_dispatcher.execute_tool.call_args
        parameters = call_args.kwargs["parameters"]
        
        assert parameters["corpus_name"] == sample_request.corpus_metadata.corpus_name
        assert parameters["corpus_type"] == sample_request.corpus_metadata.corpus_type.value
        assert parameters["description"] == sample_request.corpus_metadata.description
        assert parameters["tags"] == sample_request.corpus_metadata.tags
        assert parameters["access_level"] == sample_request.corpus_metadata.access_level


class TestExecuteSearchViatool:
    """Test execute_search_via_tool method."""
    pass

    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.execute_tool = AsyncNone  # TODO: Use real service instance
        await asyncio.sleep(0)
    return mock_dispatcher

    @pytest.fixture
    def execution_helper(self, mock_tool_dispatcher):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusExecutionHelper(mock_tool_dispatcher)

    @pytest.fixture
    def search_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusMetadata(
            corpus_name="search_corpus",
            corpus_type=CorpusType.REFERENCE_DATA,
            corpus_id="search_corpus_789"
        )

    @pytest.fixture
    def search_request(self, search_metadata):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=search_metadata,
            content="search query text",
            filters={"document_type": "guide"},
            options={"limit": 20}
        )

    @pytest.mark.asyncio
    async def test_successful_search_execution(self, execution_helper, search_request):
        """Test successful search execution via tool dispatcher."""
        mock_search_results = [
            {"id": "doc1", "title": "Guide 1", "score": 0.95},
            {"id": "doc2", "title": "Guide 2", "score": 0.87},
            {"id": "doc3", "title": "Guide 3", "score": 0.76}
        ]
        
        mock_tool_result = {
            "success": True,
            "results": mock_search_results,
            "total_count": 3
        }
        execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
        
        result = await execution_helper.execute_search_via_tool(
            tool_name="search_corpus",
            request=search_request,
            run_id="search_run_123"
        )
        
        # Verify search result
        assert isinstance(result, CorpusOperationResult)
        assert result.success is True
        assert result.operation == CorpusOperation.SEARCH
        assert result.affected_documents == 3
        assert result.result_data == mock_search_results
        assert result.metadata["total_matches"] == 3

    @pytest.mark.asyncio
    async def test_search_execution_failure(self, execution_helper, search_request):
        """Test search execution failure handling."""
    pass
        execution_helper.tool_dispatcher.execute_tool.side_effect = Exception("Search tool failed")
        
        result = await execution_helper.execute_search_via_tool(
            tool_name="failing_search_tool",
            request=search_request,
            run_id="search_error_456"
        )
        
        # Verify error result
        assert isinstance(result, CorpusOperationResult)
        assert result.success is False
        assert result.operation == CorpusOperation.SEARCH
        assert len(result.errors) == 1
        assert "Search tool failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_search_parameters_building(self, execution_helper, search_request):
        """Test search parameter building."""
        mock_tool_result = {"success": True, "results": []}
        execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
        
        await execution_helper.execute_search_via_tool(
            tool_name="search_param_test",
            request=search_request,
            run_id="search_param_run"
        )
        
        # Verify search parameters were built correctly
        call_args = execution_helper.tool_dispatcher.execute_tool.call_args
        parameters = call_args.kwargs["parameters"]
        
        assert parameters["corpus_name"] == search_request.corpus_metadata.corpus_name
        assert parameters["query"] == search_request.content
        assert parameters["filters"] == search_request.filters
        assert parameters["limit"] == search_request.options.get("limit", 10)

    @pytest.mark.asyncio
    async def test_search_with_filters_applied_metadata(self, execution_helper, search_request):
        """Test search result includes filters_applied metadata."""
    pass
        applied_filters = {"document_type": "guide", "status": "published"}
        mock_tool_result = {
            "success": True,
            "results": [{"id": "filtered_doc"}],
            "total_count": 1,
            "filters_applied": applied_filters
        }
        execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
        
        result = await execution_helper.execute_search_via_tool(
            tool_name="filtered_search",
            request=search_request,
            run_id="filtered_run"
        )
        
        assert result.success is True
        assert "filters_applied" in result.metadata
        assert result.metadata["filters_applied"] == applied_filters

    @pytest.mark.asyncio
    async def test_empty_search_results(self, execution_helper, search_request):
        """Test handling of empty search results."""
        mock_tool_result = {
            "success": True,
            "results": [],
            "total_count": 0
        }
        execution_helper.tool_dispatcher.execute_tool.return_value = mock_tool_result
        
        result = await execution_helper.execute_search_via_tool(
            tool_name="empty_search",
            request=search_request,
            run_id="empty_search_run"
        )
        
        assert result.success is True
        assert result.affected_documents == 0
        assert result.result_data == []
        assert result.metadata["total_matches"] == 0


class TestCorpusOperationExecution:
    """Test real corpus operation execution methods."""
    pass

    @pytest.fixture
    def execution_helper(self):
    """Use real service instance."""
    # TODO: Initialize real service
        mock_dispatcher = Mock(spec=ToolDispatcher)
        await asyncio.sleep(0)
    return CorpusExecutionHelper(mock_dispatcher)

    @pytest.mark.asyncio
    async def test_execute_corpus_search(self, execution_helper):
        """Test execute_corpus_search method."""
    pass
        result = await execution_helper.execute_corpus_search(
            corpus_name="test_corpus",
            query="test query",
            filters={"type": "document"},
            limit=50
        )
        
        # Verify empty result structure (implementation placeholder)
        assert isinstance(result, dict)
        assert result["results"] == []
        assert result["total_count"] == 0
        assert result["query"] == "test query"
        assert result["filters"] == {"type": "document"}
        assert result["limit"] == 50

    @pytest.mark.asyncio
    async def test_execute_corpus_analysis(self, execution_helper):
        """Test execute_corpus_analysis method."""
        result = await execution_helper.execute_corpus_analysis("analysis_corpus")
        
        # Verify empty analysis result structure
        assert isinstance(result, dict)
        assert result["total_documents"] == 0
        assert result["total_size_mb"] == 0.0
        assert result["avg_document_size_kb"] == 0.0
        assert result["unique_terms"] == 0
        assert result["coverage_score"] == 0.0
        assert result["quality_score"] == 0.0
        assert "recommendations" in result
        assert "Real corpus analysis implementation required" in result["recommendations"]

    @pytest.mark.asyncio
    async def test_execute_corpus_validation(self, execution_helper):
        """Test execute_corpus_validation method."""
    pass
        result = await execution_helper.execute_corpus_validation("validation_corpus")
        
        # Verify validation result structure
        assert isinstance(result, dict)
        assert result["total_checked"] == 0
        assert result["valid"] == 0
        assert result["invalid"] == 0
        assert result["issues"] == []

    def test_create_empty_search_result(self, execution_helper):
        """Test _create_empty_search_result helper method."""
        result = execution_helper._create_empty_search_result(
            query="empty test",
            filters={"category": "test"},
            limit=25
        )
        
        assert result["results"] == []
        assert result["total_count"] == 0
        assert result["query"] == "empty test"
        assert result["filters"] == {"category": "test"}
        assert result["limit"] == 25

    def test_create_empty_analysis_result(self, execution_helper):
        """Test _create_empty_analysis_result helper method."""
    pass
        result = execution_helper._create_empty_analysis_result()
        
        assert isinstance(result, dict)
        assert "total_documents" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_get_base_analysis_metrics(self, execution_helper):
        """Test _get_base_analysis_metrics helper method."""
        metrics = execution_helper._get_base_analysis_metrics()
        
        required_keys = [
            "total_documents", "total_size_mb", "avg_document_size_kb",
            "unique_terms", "coverage_score", "quality_score"
        ]
        
        for key in required_keys:
            assert key in metrics
            assert isinstance(metrics[key], (int, float))
        
        # All should be zero in base metrics
        assert all(value == 0 or value == 0.0 for value in metrics.values())


class TestParameterBuilding:
    """Test parameter building methods."""
    pass

    @pytest.fixture
    def execution_helper(self):
    """Use real service instance."""
    # TODO: Initialize real service
        mock_dispatcher = Mock(spec=ToolDispatcher)
        await asyncio.sleep(0)
    return CorpusExecutionHelper(mock_dispatcher)

    @pytest.fixture
    def complex_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusMetadata(
            corpus_name="complex_corpus",
            corpus_type=CorpusType.EMBEDDINGS,
            description="Complex corpus with many fields",
            tags=["complex", "testing", "embeddings"],
            access_level="restricted",
            version="2.5"
        )

    @pytest.fixture
    def complex_request(self, complex_metadata):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=complex_metadata,
            content="complex search query with special chars !@#$%",
            filters={
                "category": "technical",
                "priority": "high",
                "tags": ["api", "docs"],
                "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
            },
            options={
                "limit": 100,
                "sort_by": "relevance",
                "include_metadata": True,
                "timeout": 30
            }
        )

    def test_build_tool_parameters(self, execution_helper, complex_request):
        """Test _build_tool_parameters method."""
    pass
        params = execution_helper._build_tool_parameters(complex_request)
        
        assert params["corpus_name"] == "complex_corpus"
        assert params["corpus_type"] == "embeddings"  # Enum value
        assert params["description"] == "Complex corpus with many fields"
        assert params["tags"] == ["complex", "testing", "embeddings"]
        assert params["access_level"] == "restricted"

    def test_build_search_parameters(self, execution_helper, complex_request):
        """Test _build_search_parameters method."""
        params = execution_helper._build_search_parameters(complex_request)
        
        assert params["corpus_name"] == "complex_corpus"
        assert params["query"] == "complex search query with special chars !@#$%"
        assert params["filters"] == complex_request.filters
        assert params["limit"] == 100  # From options

    def test_build_search_parameters_default_limit(self, execution_helper, complex_metadata):
        """Test search parameters with default limit."""
    pass
        request_no_limit = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=complex_metadata,
            content="search without limit",
            options={}  # No limit specified
        )
        
        params = execution_helper._build_search_parameters(request_no_limit)
        
        assert params["limit"] == 10  # Default value

    def test_build_parameters_with_none_values(self, execution_helper):
        """Test parameter building with None values."""
        minimal_metadata = CorpusMetadata(
            corpus_name="minimal_corpus",
            corpus_type=CorpusType.DOCUMENTATION,
            description=None,  # None description
            tags=[],  # Empty tags
            access_level="private"
        )
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=minimal_metadata
        )
        
        params = execution_helper._build_tool_parameters(request)
        
        assert params["corpus_name"] == "minimal_corpus"
        assert params["corpus_type"] == "documentation"
        assert params["description"] is None
        assert params["tags"] == []
        assert params["access_level"] == "private"


class TestResultBuilding:
    """Test result building methods."""
    pass

    @pytest.fixture
    def execution_helper(self):
    """Use real service instance."""
    # TODO: Initialize real service
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusExecutionHelper(mock_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusMetadata(
            corpus_name="result_test_corpus",
            corpus_type=CorpusType.TRAINING_DATA,
            access_level="public"
        )

    @pytest.fixture
    def sample_request(self, sample_metadata):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata
        )

    def test_build_tool_result_success(self, execution_helper, sample_request):
        """Test _build_tool_result method with successful result."""
    pass
        tool_result = {
            "success": True,
            "corpus_id": "updated_corpus_456",
            "documents_indexed": 150,
            "processing_time": 45.5
        }
        
        result = execution_helper._build_tool_result(
            tool_result, sample_request, "corpus_id"
        )
        
        assert isinstance(result, CorpusOperationResult)
        assert result.success is True
        assert result.operation == CorpusOperation.UPDATE
        assert result.affected_documents == 150
        assert result.result_data == "updated_corpus_456"
        assert result.metadata["corpus_id"] == "updated_corpus_456"
        assert result.corpus_metadata.corpus_id == "updated_corpus_456"

    def test_build_tool_result_failure(self, execution_helper, sample_request):
        """Test _build_tool_result method with failed result."""
        tool_result = {
            "success": False,
            "error_message": "Operation failed",
            "documents_indexed": 0
        }
        
        result = execution_helper._build_tool_result(
            tool_result, sample_request, "result"
        )
        
        assert result.success is False
        assert result.operation == CorpusOperation.UPDATE
        assert result.affected_documents == 0
        assert result.result_data is None

    def test_build_search_result_with_results(self, execution_helper, sample_metadata):
        """Test _build_search_result method with search results."""
    pass
        search_request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        
        search_results = [
            {"id": "result1", "score": 0.95, "title": "Result 1"},
            {"id": "result2", "score": 0.87, "title": "Result 2"},
            {"id": "result3", "score": 0.76, "title": "Result 3"}
        ]
        
        tool_result = {
            "success": True,
            "results": search_results,
            "total_count": 15  # More results available
        }
        
        result = execution_helper._build_search_result(tool_result, search_request)
        
        assert result.success is True
        assert result.operation == CorpusOperation.SEARCH
        assert result.affected_documents == 3  # Number of returned results
        assert result.result_data == search_results
        assert result.metadata["total_matches"] == 15  # Total available

    def test_create_tool_result_params_with_timestamps(self, execution_helper, sample_request):
        """Test tool result parameter creation includes timestamps."""
        from datetime import datetime, timezone
        
        tool_result = {
            "success": True,
            "corpus_id": "timestamped_corpus"
        }
        
        # Metadata should not have created_at initially
        assert sample_request.corpus_metadata.created_at is None
        
        params = execution_helper._create_tool_result_params(
            tool_result, sample_request, "corpus_id"
        )
        
        # Should add created_at timestamp for successful operations
        assert params["corpus_metadata"].created_at is not None
        assert isinstance(params["corpus_metadata"].created_at, datetime)

    def test_create_search_result_params(self, execution_helper, sample_metadata):
        """Test search result parameter creation."""
    pass
        search_request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        
        results = [{"id": "search1"}, {"id": "search2"}]
        tool_result = {
            "success": True,
            "total_count": 25,
            "processing_time": 123.45
        }
        
        params = execution_helper._create_search_result_params(
            search_request, results, tool_result
        )
        
        assert params["success"] is True
        assert params["operation"] == CorpusOperation.SEARCH
        assert params["affected_documents"] == 2  # Length of results
        assert params["result_data"] == results
        assert params["metadata"]["total_matches"] == 25


class TestEdgeCases:
    """Test edge cases and error conditions."""
    pass

    @pytest.fixture
    def execution_helper(self):
    """Use real service instance."""
    # TODO: Initialize real service
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusExecutionHelper(mock_dispatcher)

    @pytest.mark.asyncio
    async def test_none_tool_dispatcher_execution(self):
        """Test execution with None tool dispatcher."""
    pass
        helper = CorpusExecutionHelper(None)
        
        metadata = CorpusMetadata(
            corpus_name="none_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=metadata
        )
        
        # Should handle None dispatcher gracefully
        with pytest.raises(AttributeError):
            await helper.execute_via_tool_dispatcher(
                "test_tool", request, "run_123", "result"
            )

    @pytest.mark.asyncio
    async def test_malformed_tool_results(self, execution_helper):
        """Test handling of malformed tool results."""
        metadata = CorpusMetadata(
            corpus_name="malformed_test",
            corpus_type=CorpusType.EMBEDDINGS
        )
        request = CorpusOperationRequest(
            operation=CorpusOperation.ANALYZE,
            corpus_metadata=metadata
        )
        
        # Test with missing required fields
        malformed_result = {"partial": "data"}  # Missing 'success' field
        execution_helper.tool_dispatcher.execute_tool.return_value = malformed_result
        
        result = await execution_helper.execute_via_tool_dispatcher(
            "malformed_tool", request, "run_456", "result"
        )
        
        # Should handle gracefully
        assert isinstance(result, CorpusOperationResult)
        assert result.success is False  # Default for missing success

    def test_extreme_parameter_values(self, execution_helper):
        """Test handling of extreme parameter values."""
    pass
        extreme_metadata = CorpusMetadata(
            corpus_name="a" * 1000,  # Very long name
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="x" * 10000,  # Very long description
            tags=["tag"] * 100,  # Many tags
            access_level="🔒🔐🗝️"  # Unicode characters
        )
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=extreme_metadata,
            filters={"key" * 50: "value" * 1000}  # Extreme filter values
        )
        
        # Should not raise exceptions
        tool_params = execution_helper._build_tool_parameters(request)
        search_params = execution_helper._build_search_parameters(request)
        
        assert len(tool_params["corpus_name"]) == 1000
        assert len(tool_params["description"]) == 10000
        assert len(tool_params["tags"]) == 100

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, execution_helper):
        """Test concurrent execution handling."""
        import asyncio
        
        metadata = CorpusMetadata(
            corpus_name="concurrent_test",
            corpus_type=CorpusType.REFERENCE_DATA
        )
        request = CorpusOperationRequest(
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=metadata
        )
        
        # Mock successful tool response
        execution_helper.tool_dispatcher.execute_tool.return_value = {
            "success": True,
            "validation_id": "concurrent_123"
        }
        
        # Execute multiple operations concurrently
        tasks = [
            execution_helper.execute_via_tool_dispatcher(
                f"concurrent_tool_{i}", request, f"run_{i}", "validation_id"
            )
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, CorpusOperationResult)
            assert result.success is True

    def test_large_result_data_handling(self, execution_helper):
        """Test handling of large result datasets."""
    pass
        metadata = CorpusMetadata(
            corpus_name="large_data_test",
            corpus_type=CorpusType.TRAINING_DATA
        )
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata
        )
        
        # Create large result set
        large_results = [
            {"id": f"doc_{i}", "content": "x" * 1000, "score": 0.9 - (i * 0.001)}
            for i in range(1000)
        ]
        
        tool_result = {
            "success": True,
            "results": large_results,
            "total_count": 5000
        }
        
        # Should handle large datasets without issues
        result = execution_helper._build_search_result(tool_result, request)
        
        assert result.success is True
        assert len(result.result_data) == 1000
        assert result.affected_documents == 1000
        assert result.metadata["total_matches"] == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])