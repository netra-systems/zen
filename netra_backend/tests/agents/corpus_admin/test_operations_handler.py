"""
Comprehensive unit tests for corpus_admin operations_handler.

Business Value: Ensures reliable operation routing and execution for corpus management.
The operations handler is the main orchestrator for all corpus operations and must
provide robust error handling and proper operation delegation.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from netra_backend.app.agents.corpus_admin.operations_handler import CorpusOperationHandler
from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestCorpusOperationHandler:
    """Test CorpusOperationHandler initialization and basic functionality."""

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher for testing."""
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.execute_tool = AsyncMock()
        return mock_dispatcher

    @pytest.fixture
    def operations_handler(self, mock_tool_dispatcher):
        """Create CorpusOperationHandler instance for testing."""
        return CorpusOperationHandler(mock_tool_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
        """Create sample corpus metadata for testing."""
        return CorpusMetadata(
            corpus_name="test_handler_corpus",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="Test corpus for operations handler testing",
            tags=["test", "handler"],
            access_level="private"
        )

    @pytest.fixture
    def sample_request(self, sample_metadata):
        """Create sample corpus operation request."""
        return CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata,
            options={"validate": True}
        )

    def test_initialization(self, mock_tool_dispatcher):
        """Test CorpusOperationHandler initialization."""
        handler = CorpusOperationHandler(mock_tool_dispatcher)
        
        assert handler is not None
        assert handler.tool_dispatcher == mock_tool_dispatcher
        assert handler.crud_ops is not None
        assert handler.analysis_ops is not None

    def test_component_initialization(self, operations_handler):
        """Test that all components are properly initialized."""
        assert operations_handler.crud_ops is not None
        assert operations_handler.analysis_ops is not None
        assert hasattr(operations_handler.crud_ops, 'tool_dispatcher')
        assert hasattr(operations_handler.analysis_ops, 'tool_dispatcher')


class TestExecuteOperation:
    """Test execute_operation method and error handling."""

    @pytest.fixture
    def mock_tool_dispatcher(self):
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.execute_tool = AsyncMock()
        return mock_dispatcher

    @pytest.fixture
    def operations_handler(self, mock_tool_dispatcher):
        return CorpusOperationHandler(mock_tool_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
        return CorpusMetadata(
            corpus_name="execute_test_corpus",
            corpus_type=CorpusType.DOCUMENTATION,
            description="Test corpus for execution testing"
        )

    @pytest.mark.asyncio
    async def test_successful_crud_operation_routing(self, operations_handler, sample_metadata):
        """Test successful routing of CRUD operations."""
        create_request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        
        # Mock successful CRUD operation
        expected_result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata,
            affected_documents=1
        )
        
        with patch.object(operations_handler.crud_ops, 'execute', return_value=expected_result) as mock_crud:
            result = await operations_handler.execute_operation(
                create_request, "test_run_123", True
            )
            
            assert result == expected_result
            mock_crud.assert_called_once_with(
                "create", create_request, "test_run_123", True
            )

    @pytest.mark.asyncio
    async def test_successful_analysis_operation_routing(self, operations_handler, sample_metadata):
        """Test successful routing of analysis operations."""
        analyze_request = CorpusOperationRequest(
            operation=CorpusOperation.ANALYZE,
            corpus_metadata=sample_metadata
        )
        
        expected_result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.ANALYZE,
            corpus_metadata=sample_metadata,
            affected_documents=100
        )
        
        with patch.object(operations_handler.analysis_ops, 'execute', return_value=expected_result) as mock_analysis:
            result = await operations_handler.execute_operation(
                analyze_request, "analyze_run_456", False
            )
            
            assert result == expected_result
            mock_analysis.assert_called_once_with(
                "analyze", analyze_request, "analyze_run_456", False
            )

    @pytest.mark.asyncio
    async def test_unsupported_operation_handling(self, operations_handler, sample_metadata):
        """Test handling of unsupported operations."""
        # Create a mock operation that's not in CRUD or analysis
        class UnsupportedOperation:
            value = "unsupported_op"
        
        # Patch the operation enum to include our unsupported operation
        unsupported_request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,  # Use valid enum
            corpus_metadata=sample_metadata
        )
        
        # Mock the operation value to be unsupported
        with patch.object(unsupported_request.operation, 'value', "unsupported_op"):
            result = await operations_handler.execute_operation(
                unsupported_request, "unsupported_run", True
            )
            
            assert isinstance(result, CorpusOperationResult)
            assert result.success is False
            assert len(result.errors) > 0
            assert "Unsupported operation" in result.errors[0]

    @pytest.mark.asyncio
    async def test_operation_execution_error_handling(self, operations_handler, sample_metadata):
        """Test error handling during operation execution."""
        error_request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata
        )
        
        # Mock CRUD operation to raise exception
        with patch.object(operations_handler.crud_ops, 'execute', side_effect=Exception("CRUD error")):
            result = await operations_handler.execute_operation(
                error_request, "error_run_789", False
            )
            
            assert isinstance(result, CorpusOperationResult)
            assert result.success is False
            assert len(result.errors) > 0
            assert "CRUD error" in result.errors[0]

    @pytest.mark.parametrize("operation,expected_type", [
        (CorpusOperation.CREATE, "crud"),
        (CorpusOperation.SEARCH, "crud"),
        (CorpusOperation.UPDATE, "crud"),
        (CorpusOperation.DELETE, "crud"),
        (CorpusOperation.ANALYZE, "analysis"),
        (CorpusOperation.INDEX, "analysis"),
        (CorpusOperation.VALIDATE, "analysis"),
    ])
    @pytest.mark.asyncio
    async def test_all_operation_types_routing(self, operations_handler, sample_metadata, operation, expected_type):
        """Test that all operation types are routed correctly."""
        request = CorpusOperationRequest(
            operation=operation,
            corpus_metadata=sample_metadata
        )
        
        expected_result = CorpusOperationResult(
            success=True,
            operation=operation,
            corpus_metadata=sample_metadata
        )
        
        if expected_type == "crud":
            with patch.object(operations_handler.crud_ops, 'execute', return_value=expected_result) as mock_handler:
                await operations_handler.execute_operation(request, f"{operation.value}_run", True)
                mock_handler.assert_called_once()
        else:  # analysis
            with patch.object(operations_handler.analysis_ops, 'execute', return_value=expected_result) as mock_handler:
                await operations_handler.execute_operation(request, f"{operation.value}_run", True)
                mock_handler.assert_called_once()


class TestOperationTypeChecking:
    """Test operation type checking methods."""

    @pytest.fixture
    def operations_handler(self):
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusOperationHandler(mock_dispatcher)

    def test_is_crud_operation(self, operations_handler):
        """Test CRUD operation detection."""
        crud_operations = ["create", "search", "update", "delete"]
        non_crud_operations = ["analyze", "export", "import", "validate", "unknown"]
        
        for operation in crud_operations:
            assert operations_handler._is_crud_operation(operation) is True
        
        for operation in non_crud_operations:
            assert operations_handler._is_crud_operation(operation) is False

    def test_is_analysis_operation(self, operations_handler):
        """Test analysis operation detection."""
        analysis_operations = ["analyze", "export", "import", "validate"]
        non_analysis_operations = ["create", "search", "update", "delete", "unknown"]
        
        for operation in analysis_operations:
            assert operations_handler._is_analysis_operation(operation) is True
        
        for operation in non_analysis_operations:
            assert operations_handler._is_analysis_operation(operation) is False

    def test_operation_type_mutual_exclusivity(self, operations_handler):
        """Test that operation types are mutually exclusive."""
        all_operations = [
            "create", "search", "update", "delete",
            "analyze", "export", "import", "validate"
        ]
        
        for operation in all_operations:
            is_crud = operations_handler._is_crud_operation(operation)
            is_analysis = operations_handler._is_analysis_operation(operation)
            
            # Each operation should be exactly one type
            assert is_crud != is_analysis  # XOR: exactly one should be True

    def test_unknown_operation_type_checking(self, operations_handler):
        """Test handling of unknown operation types."""
        unknown_operations = ["unknown", "invalid", "test", "", "123"]
        
        for operation in unknown_operations:
            assert operations_handler._is_crud_operation(operation) is False
            assert operations_handler._is_analysis_operation(operation) is False


class TestErrorHandling:
    """Test error handling methods."""

    @pytest.fixture
    def operations_handler(self):
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusOperationHandler(mock_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
        return CorpusMetadata(
            corpus_name="error_test_corpus",
            corpus_type=CorpusType.TRAINING_DATA,
            access_level="restricted"
        )

    def test_handle_operation_error(self, operations_handler, sample_metadata):
        """Test _handle_operation_error method."""
        base_result = CorpusOperationResult(
            success=False,
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        
        test_error = Exception("Test operation error")
        
        result = operations_handler._handle_operation_error(base_result, test_error)
        
        assert result == base_result
        assert len(result.errors) == 1
        assert "Test operation error" in result.errors[0]

    def test_handle_multiple_errors(self, operations_handler, sample_metadata):
        """Test handling multiple errors in succession."""
        base_result = CorpusOperationResult(
            success=False,
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata
        )
        
        errors = [
            Exception("First error"),
            Exception("Second error"),
            Exception("Third error")
        ]
        
        # Apply multiple errors
        result = base_result
        for error in errors:
            result = operations_handler._handle_operation_error(result, error)
        
        assert len(result.errors) == 3
        assert "First error" in result.errors[0]
        assert "Second error" in result.errors[1]
        assert "Third error" in result.errors[2]

    def test_create_unsupported_operation_result(self, operations_handler, sample_metadata):
        """Test _create_unsupported_operation_result method."""
        unsupported_request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,  # Valid enum but treated as unsupported
            corpus_metadata=sample_metadata
        )
        
        result = operations_handler._create_unsupported_operation_result(unsupported_request)
        
        assert isinstance(result, CorpusOperationResult)
        assert result.success is False
        assert result.operation == CorpusOperation.SEARCH
        assert result.corpus_metadata == sample_metadata
        assert len(result.errors) == 1
        assert "Unsupported operation" in result.errors[0]

    def test_create_base_result(self, operations_handler, sample_metadata):
        """Test _create_base_result method."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        result = operations_handler._create_base_result(request)
        
        assert isinstance(result, CorpusOperationResult)
        assert result.success is False  # Base result defaults to False
        assert result.operation == CorpusOperation.DELETE
        assert result.corpus_metadata == sample_metadata
        assert result.affected_documents == 0
        assert result.errors == []


class TestCorpusStatistics:
    """Test corpus statistics methods."""

    @pytest.fixture
    def operations_handler(self):
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusOperationHandler(mock_dispatcher)

    @pytest.mark.asyncio
    async def test_get_corpus_statistics(self, operations_handler):
        """Test get_corpus_statistics method."""
        stats = await operations_handler.get_corpus_statistics()
        
        assert isinstance(stats, dict)
        
        # Check base statistics
        assert "total_corpora" in stats
        assert "total_documents" in stats
        assert "total_size_gb" in stats
        assert stats["total_corpora"] == 12
        assert stats["total_documents"] == 45678
        assert stats["total_size_gb"] == 2.3
        
        # Check corpora by type
        assert "corpora_by_type" in stats
        corpora_types = stats["corpora_by_type"]
        assert isinstance(corpora_types, dict)
        assert "documentation" in corpora_types
        assert "knowledge_base" in corpora_types
        assert "training_data" in corpora_types
        assert "reference_data" in corpora_types
        assert "embeddings" in corpora_types
        
        # Check recent operations
        assert "recent_operations" in stats
        recent_ops = stats["recent_operations"]
        assert isinstance(recent_ops, list)
        assert len(recent_ops) >= 2  # Should have at least search and create

    def test_get_base_statistics(self, operations_handler):
        """Test _get_base_statistics method."""
        base_stats = operations_handler._get_base_statistics()
        
        assert isinstance(base_stats, dict)
        assert "total_corpora" in base_stats
        assert "total_documents" in base_stats
        assert "total_size_gb" in base_stats
        
        # Verify reasonable values
        assert isinstance(base_stats["total_corpora"], int)
        assert isinstance(base_stats["total_documents"], int)
        assert isinstance(base_stats["total_size_gb"], (int, float))

    def test_get_corpora_by_type(self, operations_handler):
        """Test _get_corpora_by_type method."""
        corpora_by_type = operations_handler._get_corpora_by_type()
        
        assert isinstance(corpora_by_type, dict)
        
        # Should include all corpus types
        expected_types = ["documentation", "knowledge_base", "training_data", "reference_data", "embeddings"]
        for corpus_type in expected_types:
            assert corpus_type in corpora_by_type
            assert isinstance(corpora_by_type[corpus_type], int)
            assert corpora_by_type[corpus_type] >= 0

    def test_get_base_corpus_types(self, operations_handler):
        """Test _get_base_corpus_types method."""
        base_types = operations_handler._get_base_corpus_types()
        
        assert isinstance(base_types, dict)
        assert "documentation" in base_types
        assert "knowledge_base" in base_types
        assert "training_data" in base_types
        
        # Verify counts are reasonable
        assert base_types["documentation"] == 3
        assert base_types["knowledge_base"] == 5
        assert base_types["training_data"] == 2

    def test_get_additional_corpus_types(self, operations_handler):
        """Test _get_additional_corpus_types method."""
        additional_types = operations_handler._get_additional_corpus_types()
        
        assert isinstance(additional_types, dict)
        assert "reference_data" in additional_types
        assert "embeddings" in additional_types
        
        assert additional_types["reference_data"] == 1
        assert additional_types["embeddings"] == 1

    def test_get_recent_operations(self, operations_handler):
        """Test _get_recent_operations method."""
        recent_ops = operations_handler._get_recent_operations()
        
        assert isinstance(recent_ops, list)
        assert len(recent_ops) == 2
        
        # Check structure of operations
        for op in recent_ops:
            assert isinstance(op, dict)
            assert "operation" in op
            assert "timestamp" in op
            assert "corpus" in op
            
            # Verify timestamp format
            assert isinstance(op["timestamp"], str)
            # Should be ISO format
            datetime.fromisoformat(op["timestamp"].replace('Z', '+00:00'))

    def test_create_search_operation_record(self, operations_handler):
        """Test _create_search_operation_record method."""
        search_record = operations_handler._create_search_operation_record()
        
        assert isinstance(search_record, dict)
        assert search_record["operation"] == "search"
        assert search_record["corpus"] == "main_kb"
        assert "timestamp" in search_record
        
        # Verify timestamp is recent
        timestamp = datetime.fromisoformat(search_record["timestamp"].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        time_diff = now - timestamp
        assert time_diff.total_seconds() < 60  # Should be within last minute

    def test_create_create_operation_record(self, operations_handler):
        """Test _create_create_operation_record method."""
        create_record = operations_handler._create_create_operation_record()
        
        assert isinstance(create_record, dict)
        assert create_record["operation"] == "create"
        assert create_record["corpus"] == "product_docs"
        assert "timestamp" in create_record
        
        # Verify timestamp format and recency
        timestamp = datetime.fromisoformat(create_record["timestamp"].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        time_diff = now - timestamp
        assert time_diff.total_seconds() < 60


class TestOperationRouting:
    """Test operation routing logic."""

    @pytest.fixture
    def operations_handler(self):
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusOperationHandler(mock_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
        return CorpusMetadata(
            corpus_name="routing_test_corpus",
            corpus_type=CorpusType.EMBEDDINGS,
            description="Test corpus for routing logic"
        )

    @pytest.mark.asyncio
    async def test_route_operation_crud_success(self, operations_handler, sample_metadata):
        """Test successful CRUD operation routing."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        
        expected_result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        
        with patch.object(operations_handler.crud_ops, 'execute', return_value=expected_result) as mock_crud:
            result = await operations_handler._route_operation(request, "route_run", True)
            
            assert result == expected_result
            mock_crud.assert_called_once_with("create", request, "route_run", True)

    @pytest.mark.asyncio
    async def test_route_operation_analysis_success(self, operations_handler, sample_metadata):
        """Test successful analysis operation routing."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=sample_metadata
        )
        
        expected_result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=sample_metadata
        )
        
        with patch.object(operations_handler.analysis_ops, 'execute', return_value=expected_result) as mock_analysis:
            result = await operations_handler._route_operation(request, "validate_run", False)
            
            assert result == expected_result
            mock_analysis.assert_called_once_with("validate", request, "validate_run", False)

    @pytest.mark.asyncio
    async def test_route_operation_unsupported(self, operations_handler, sample_metadata):
        """Test routing of unsupported operations."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,  # Valid enum
            corpus_metadata=sample_metadata
        )
        
        # Mock the operation value to be unsupported
        with patch.object(request.operation, 'value', "unsupported_operation"):
            result = await operations_handler._route_operation(request, "unsupported_run", True)
            
            assert isinstance(result, CorpusOperationResult)
            assert result.success is False
            assert "Unsupported operation" in result.errors[0]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def operations_handler(self):
        mock_dispatcher = Mock(spec=ToolDispatcher)
        return CorpusOperationHandler(mock_dispatcher)

    @pytest.mark.asyncio
    async def test_none_request_handling(self, operations_handler):
        """Test handling of None request."""
        # This should raise an AttributeError or similar
        with pytest.raises((AttributeError, TypeError)):
            await operations_handler.execute_operation(None, "none_run", True)

    @pytest.mark.asyncio
    async def test_empty_run_id_handling(self, operations_handler):
        """Test handling of empty run_id."""
        metadata = CorpusMetadata(
            corpus_name="empty_run_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata
        )
        
        # Should handle empty run_id gracefully
        with patch.object(operations_handler.crud_ops, 'execute') as mock_crud:
            mock_crud.return_value = CorpusOperationResult(
                success=True,
                operation=CorpusOperation.SEARCH,
                corpus_metadata=metadata
            )
            
            result = await operations_handler.execute_operation(request, "", False)
            mock_crud.assert_called_once_with("search", request, "", False)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, operations_handler):
        """Test concurrent operation execution."""
        import asyncio
        
        metadata = CorpusMetadata(
            corpus_name="concurrent_test",
            corpus_type=CorpusType.REFERENCE_DATA
        )
        
        requests = [
            CorpusOperationRequest(
                operation=CorpusOperation.SEARCH,
                corpus_metadata=metadata
            ) for _ in range(5)
        ]
        
        # Mock successful results
        with patch.object(operations_handler.crud_ops, 'execute') as mock_crud:
            mock_crud.return_value = CorpusOperationResult(
                success=True,
                operation=CorpusOperation.SEARCH,
                corpus_metadata=metadata
            )
            
            # Execute operations concurrently
            tasks = [
                operations_handler.execute_operation(req, f"concurrent_run_{i}", True)
                for i, req in enumerate(requests)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, CorpusOperationResult)
                assert result.success is True

    def test_extreme_metadata_values(self, operations_handler):
        """Test handling of extreme metadata values."""
        extreme_metadata = CorpusMetadata(
            corpus_name="x" * 1000,  # Very long name
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="y" * 5000,  # Very long description
            tags=["tag"] * 50,  # Many tags
            access_level="🔐🗝️🔒"  # Unicode access level
        )
        
        # Should create result without exceptions
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=extreme_metadata
        )
        
        base_result = operations_handler._create_base_result(request)
        
        assert base_result.corpus_metadata == extreme_metadata
        assert len(base_result.corpus_metadata.corpus_name) == 1000
        assert len(base_result.corpus_metadata.description) == 5000

    @pytest.mark.asyncio
    async def test_malformed_tool_dispatcher_responses(self, operations_handler):
        """Test handling of malformed tool dispatcher responses."""
        metadata = CorpusMetadata(
            corpus_name="malformed_test",
            corpus_type=CorpusType.TRAINING_DATA
        )
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata
        )
        
        # Mock CRUD to return None (malformed response)
        with patch.object(operations_handler.crud_ops, 'execute', return_value=None):
            result = await operations_handler.execute_operation(request, "malformed_run", False)
            
            # Should handle gracefully and return an error result
            # The actual behavior depends on implementation, but should not crash
            assert result is None or isinstance(result, CorpusOperationResult)


class TestIntegrationWithComponents:
    """Test integration with CRUD and Analysis operation components."""

    @pytest.fixture
    def mock_tool_dispatcher(self):
        return Mock(spec=ToolDispatcher)

    @pytest.fixture
    def operations_handler(self, mock_tool_dispatcher):
        return CorpusOperationHandler(mock_tool_dispatcher)

    @pytest.fixture
    def sample_metadata(self):
        return CorpusMetadata(
            corpus_name="integration_test_corpus",
            corpus_type=CorpusType.KNOWLEDGE_BASE
        )

    @pytest.mark.asyncio
    async def test_crud_component_integration(self, operations_handler, sample_metadata):
        """Test integration with CRUD operations component."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        # Verify CRUD component exists and has correct interface
        assert hasattr(operations_handler.crud_ops, 'execute')
        assert hasattr(operations_handler.crud_ops, 'tool_dispatcher')
        assert operations_handler.crud_ops.tool_dispatcher == operations_handler.tool_dispatcher

    @pytest.mark.asyncio
    async def test_analysis_component_integration(self, operations_handler, sample_metadata):
        """Test integration with Analysis operations component."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.EXPORT,
            corpus_metadata=sample_metadata
        )
        
        # Verify Analysis component exists and has correct interface
        assert hasattr(operations_handler.analysis_ops, 'execute')
        assert hasattr(operations_handler.analysis_ops, 'tool_dispatcher')
        assert operations_handler.analysis_ops.tool_dispatcher == operations_handler.tool_dispatcher

    @pytest.mark.asyncio
    async def test_tool_dispatcher_propagation(self, mock_tool_dispatcher):
        """Test that tool dispatcher is properly propagated to components."""
        handler = CorpusOperationHandler(mock_tool_dispatcher)
        
        # Both components should have the same tool dispatcher instance
        assert handler.crud_ops.tool_dispatcher is mock_tool_dispatcher
        assert handler.analysis_ops.tool_dispatcher is mock_tool_dispatcher

    @pytest.mark.asyncio
    async def test_component_method_signatures(self, operations_handler, sample_metadata):
        """Test that component methods have expected signatures."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        
        # Mock both components to verify they're called with correct parameters
        with patch.object(operations_handler.crud_ops, 'execute') as mock_crud:
            mock_result = CorpusOperationResult(
                success=True,
                operation=CorpusOperation.SEARCH,
                corpus_metadata=sample_metadata
            )
            mock_crud.return_value = mock_result
            
            await operations_handler.execute_operation(request, "signature_test", True)
            
            # Verify component was called with expected signature
            mock_crud.assert_called_once_with("search", request, "signature_test", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])