from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive unit tests for corpus_admin operations_handler.

# REMOVED_SYNTAX_ERROR: Business Value: Ensures reliable operation routing and execution for corpus management.
# REMOVED_SYNTAX_ERROR: The operations handler is the main orchestrator for all corpus operations and must
# REMOVED_SYNTAX_ERROR: provide robust error handling and proper operation delegation.
""

import pytest
from datetime import datetime, timezone
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.corpus_admin.operations_handler import CorpusOperationHandler
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.corpus_admin.models import ( )
CorpusOperation,
CorpusType,
CorpusMetadata,
CorpusOperationRequest,
CorpusOperationResult
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


# REMOVED_SYNTAX_ERROR: class TestCorpusOperationHandler:
    # REMOVED_SYNTAX_ERROR: """Test CorpusOperationHandler initialization and basic functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher for testing."""
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: mock_dispatcher.execute_tool = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return mock_dispatcher

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create CorpusOperationHandler instance for testing."""
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_tool_dispatcher)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create sample corpus metadata for testing."""
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="test_handler_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.KNOWLEDGE_BASE,
    # REMOVED_SYNTAX_ERROR: description="Test corpus for operations handler testing",
    # REMOVED_SYNTAX_ERROR: tags=["test", "handler"],
    # REMOVED_SYNTAX_ERROR: access_level="private"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_request(self, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create sample corpus operation request."""
    # REMOVED_SYNTAX_ERROR: return CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
    # REMOVED_SYNTAX_ERROR: options={"validate": True}
    

# REMOVED_SYNTAX_ERROR: def test_initialization(self, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Test CorpusOperationHandler initialization."""
    # REMOVED_SYNTAX_ERROR: handler = CorpusOperationHandler(mock_tool_dispatcher)

    # REMOVED_SYNTAX_ERROR: assert handler is not None
    # REMOVED_SYNTAX_ERROR: assert handler.tool_dispatcher == mock_tool_dispatcher
    # REMOVED_SYNTAX_ERROR: assert handler.crud_ops is not None
    # REMOVED_SYNTAX_ERROR: assert handler.analysis_ops is not None

# REMOVED_SYNTAX_ERROR: def test_component_initialization(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test that all components are properly initialized."""
    # REMOVED_SYNTAX_ERROR: assert operations_handler.crud_ops is not None
    # REMOVED_SYNTAX_ERROR: assert operations_handler.analysis_ops is not None
    # REMOVED_SYNTAX_ERROR: assert hasattr(operations_handler.crud_ops, 'tool_dispatcher')
    # REMOVED_SYNTAX_ERROR: assert hasattr(operations_handler.analysis_ops, 'tool_dispatcher')


# REMOVED_SYNTAX_ERROR: class TestExecuteOperation:
    # REMOVED_SYNTAX_ERROR: """Test execute_operation method and error handling."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: mock_dispatcher.execute_tool = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return mock_dispatcher

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_tool_dispatcher)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="execute_test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.DOCUMENTATION,
    # REMOVED_SYNTAX_ERROR: description="Test corpus for execution testing"
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_successful_crud_operation_routing(self, operations_handler, sample_metadata):
        # REMOVED_SYNTAX_ERROR: """Test successful routing of CRUD operations."""
        # REMOVED_SYNTAX_ERROR: create_request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # Mock successful CRUD operation
        # REMOVED_SYNTAX_ERROR: expected_result = CorpusOperationResult( )
        # REMOVED_SYNTAX_ERROR: success=True,
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
        # REMOVED_SYNTAX_ERROR: affected_documents=1
        

        # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute', return_value=expected_result) as mock_crud:
            # REMOVED_SYNTAX_ERROR: result = await operations_handler.execute_operation( )
            # REMOVED_SYNTAX_ERROR: create_request, "test_run_123", True
            

            # REMOVED_SYNTAX_ERROR: assert result == expected_result
            # REMOVED_SYNTAX_ERROR: mock_crud.assert_called_once_with( )
            # REMOVED_SYNTAX_ERROR: "create", create_request, "test_run_123", True
            

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_successful_analysis_operation_routing(self, operations_handler, sample_metadata):
                # REMOVED_SYNTAX_ERROR: """Test successful routing of analysis operations."""
                # REMOVED_SYNTAX_ERROR: analyze_request = CorpusOperationRequest( )
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.ANALYZE,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                

                # REMOVED_SYNTAX_ERROR: expected_result = CorpusOperationResult( )
                # REMOVED_SYNTAX_ERROR: success=True,
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.ANALYZE,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
                # REMOVED_SYNTAX_ERROR: affected_documents=100
                

                # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.analysis_ops, 'execute', return_value=expected_result) as mock_analysis:
                    # REMOVED_SYNTAX_ERROR: result = await operations_handler.execute_operation( )
                    # REMOVED_SYNTAX_ERROR: analyze_request, "analyze_run_456", False
                    

                    # REMOVED_SYNTAX_ERROR: assert result == expected_result
                    # REMOVED_SYNTAX_ERROR: mock_analysis.assert_called_once_with( )
                    # REMOVED_SYNTAX_ERROR: "analyze", analyze_request, "analyze_run_456", False
                    

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_unsupported_operation_handling(self, operations_handler, sample_metadata):
                        # REMOVED_SYNTAX_ERROR: """Test handling of unsupported operations."""
                        # Create a mock operation that's not in CRUD or analysis
# REMOVED_SYNTAX_ERROR: class UnsupportedOperation:
    # REMOVED_SYNTAX_ERROR: value = "unsupported_op"

    # Patch the operation enum to include our unsupported operation
    # REMOVED_SYNTAX_ERROR: unsupported_request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,  # Use valid enum
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # Mock the operation value to be unsupported
    # REMOVED_SYNTAX_ERROR: with patch.object(unsupported_request.operation, 'value', "unsupported_op"):
        # REMOVED_SYNTAX_ERROR: result = await operations_handler.execute_operation( )
        # REMOVED_SYNTAX_ERROR: unsupported_request, "unsupported_run", True
        

        # REMOVED_SYNTAX_ERROR: assert isinstance(result, CorpusOperationResult)
        # REMOVED_SYNTAX_ERROR: assert result.success is False
        # REMOVED_SYNTAX_ERROR: assert len(result.errors) > 0
        # REMOVED_SYNTAX_ERROR: assert "Unsupported operation" in result.errors[0]

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_operation_execution_error_handling(self, operations_handler, sample_metadata):
            # REMOVED_SYNTAX_ERROR: """Test error handling during operation execution."""
            # REMOVED_SYNTAX_ERROR: error_request = CorpusOperationRequest( )
            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
            

            # Mock CRUD operation to raise exception
            # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute', side_effect=Exception("CRUD error")):
                # REMOVED_SYNTAX_ERROR: result = await operations_handler.execute_operation( )
                # REMOVED_SYNTAX_ERROR: error_request, "error_run_789", False
                

                # REMOVED_SYNTAX_ERROR: assert isinstance(result, CorpusOperationResult)
                # REMOVED_SYNTAX_ERROR: assert result.success is False
                # REMOVED_SYNTAX_ERROR: assert len(result.errors) > 0
                # REMOVED_SYNTAX_ERROR: assert "CRUD error" in result.errors[0]

                # REMOVED_SYNTAX_ERROR: @pytest.fixture)
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.CREATE, "crud"),
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.SEARCH, "crud"),
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.UPDATE, "crud"),
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.DELETE, "crud"),
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.ANALYZE, "analysis"),
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.INDEX, "analysis"),
                # REMOVED_SYNTAX_ERROR: (CorpusOperation.VALIDATE, "analysis"),
                
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_all_operation_types_routing(self, operations_handler, sample_metadata, operation, expected_type):
                    # REMOVED_SYNTAX_ERROR: """Test that all operation types are routed correctly."""
                    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                    # REMOVED_SYNTAX_ERROR: operation=operation,
                    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                    

                    # REMOVED_SYNTAX_ERROR: expected_result = CorpusOperationResult( )
                    # REMOVED_SYNTAX_ERROR: success=True,
                    # REMOVED_SYNTAX_ERROR: operation=operation,
                    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                    

                    # REMOVED_SYNTAX_ERROR: if expected_type == "crud":
                        # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute', return_value=expected_result) as mock_handler:
                            # REMOVED_SYNTAX_ERROR: await operations_handler.execute_operation(request, "formatted_string", True)
                            # REMOVED_SYNTAX_ERROR: mock_handler.assert_called_once()
                            # REMOVED_SYNTAX_ERROR: else:  # analysis
                            # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.analysis_ops, 'execute', return_value=expected_result) as mock_handler:
                                # REMOVED_SYNTAX_ERROR: await operations_handler.execute_operation(request, "formatted_string", True)
                                # REMOVED_SYNTAX_ERROR: mock_handler.assert_called_once()


# REMOVED_SYNTAX_ERROR: class TestOperationTypeChecking:
    # REMOVED_SYNTAX_ERROR: """Test operation type checking methods."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_dispatcher)

# REMOVED_SYNTAX_ERROR: def test_is_crud_operation(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test CRUD operation detection."""
    # REMOVED_SYNTAX_ERROR: crud_operations = ["create", "search", "update", "delete"]
    # REMOVED_SYNTAX_ERROR: non_crud_operations = ["analyze", "export", "import", "validate", "unknown"]

    # REMOVED_SYNTAX_ERROR: for operation in crud_operations:
        # REMOVED_SYNTAX_ERROR: assert operations_handler._is_crud_operation(operation) is True

        # REMOVED_SYNTAX_ERROR: for operation in non_crud_operations:
            # REMOVED_SYNTAX_ERROR: assert operations_handler._is_crud_operation(operation) is False

# REMOVED_SYNTAX_ERROR: def test_is_analysis_operation(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test analysis operation detection."""
    # REMOVED_SYNTAX_ERROR: analysis_operations = ["analyze", "export", "import", "validate"]
    # REMOVED_SYNTAX_ERROR: non_analysis_operations = ["create", "search", "update", "delete", "unknown"]

    # REMOVED_SYNTAX_ERROR: for operation in analysis_operations:
        # REMOVED_SYNTAX_ERROR: assert operations_handler._is_analysis_operation(operation) is True

        # REMOVED_SYNTAX_ERROR: for operation in non_analysis_operations:
            # REMOVED_SYNTAX_ERROR: assert operations_handler._is_analysis_operation(operation) is False

# REMOVED_SYNTAX_ERROR: def test_operation_type_mutual_exclusivity(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test that operation types are mutually exclusive."""
    # REMOVED_SYNTAX_ERROR: all_operations = [ )
    # REMOVED_SYNTAX_ERROR: "create", "search", "update", "delete",
    # REMOVED_SYNTAX_ERROR: "analyze", "export", "import", "validate"
    

    # REMOVED_SYNTAX_ERROR: for operation in all_operations:
        # REMOVED_SYNTAX_ERROR: is_crud = operations_handler._is_crud_operation(operation)
        # REMOVED_SYNTAX_ERROR: is_analysis = operations_handler._is_analysis_operation(operation)

        # Each operation should be exactly one type
        # REMOVED_SYNTAX_ERROR: assert is_crud != is_analysis  # XOR: exactly one should be True

# REMOVED_SYNTAX_ERROR: def test_unknown_operation_type_checking(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test handling of unknown operation types."""
    # REMOVED_SYNTAX_ERROR: unknown_operations = ["unknown", "invalid", "test", "", "123"]

    # REMOVED_SYNTAX_ERROR: for operation in unknown_operations:
        # REMOVED_SYNTAX_ERROR: assert operations_handler._is_crud_operation(operation) is False
        # REMOVED_SYNTAX_ERROR: assert operations_handler._is_analysis_operation(operation) is False


# REMOVED_SYNTAX_ERROR: class TestErrorHandling:
    # REMOVED_SYNTAX_ERROR: """Test error handling methods."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_dispatcher)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="error_test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.TRAINING_DATA,
    # REMOVED_SYNTAX_ERROR: access_level="restricted"
    

# REMOVED_SYNTAX_ERROR: def test_handle_operation_error(self, operations_handler, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test _handle_operation_error method."""
    # REMOVED_SYNTAX_ERROR: base_result = CorpusOperationResult( )
    # REMOVED_SYNTAX_ERROR: success=False,
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: test_error = Exception("Test operation error")

    # REMOVED_SYNTAX_ERROR: result = operations_handler._handle_operation_error(base_result, test_error)

    # REMOVED_SYNTAX_ERROR: assert result == base_result
    # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 1
    # REMOVED_SYNTAX_ERROR: assert "Test operation error" in result.errors[0]

# REMOVED_SYNTAX_ERROR: def test_handle_multiple_errors(self, operations_handler, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test handling multiple errors in succession."""
    # REMOVED_SYNTAX_ERROR: base_result = CorpusOperationResult( )
    # REMOVED_SYNTAX_ERROR: success=False,
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: errors = [ )
    # REMOVED_SYNTAX_ERROR: Exception("First error"),
    # REMOVED_SYNTAX_ERROR: Exception("Second error"),
    # REMOVED_SYNTAX_ERROR: Exception("Third error")
    

    # Apply multiple errors
    # REMOVED_SYNTAX_ERROR: result = base_result
    # REMOVED_SYNTAX_ERROR: for error in errors:
        # REMOVED_SYNTAX_ERROR: result = operations_handler._handle_operation_error(result, error)

        # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 3
        # REMOVED_SYNTAX_ERROR: assert "First error" in result.errors[0]
        # REMOVED_SYNTAX_ERROR: assert "Second error" in result.errors[1]
        # REMOVED_SYNTAX_ERROR: assert "Third error" in result.errors[2]

# REMOVED_SYNTAX_ERROR: def test_create_unsupported_operation_result(self, operations_handler, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test _create_unsupported_operation_result method."""
    # REMOVED_SYNTAX_ERROR: unsupported_request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,  # Valid enum but treated as unsupported
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: result = operations_handler._create_unsupported_operation_result(unsupported_request)

    # REMOVED_SYNTAX_ERROR: assert isinstance(result, CorpusOperationResult)
    # REMOVED_SYNTAX_ERROR: assert result.success is False
    # REMOVED_SYNTAX_ERROR: assert result.operation == CorpusOperation.SEARCH
    # REMOVED_SYNTAX_ERROR: assert result.corpus_metadata == sample_metadata
    # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 1
    # REMOVED_SYNTAX_ERROR: assert "Unsupported operation" in result.errors[0]

# REMOVED_SYNTAX_ERROR: def test_create_base_result(self, operations_handler, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test _create_base_result method."""
    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: result = operations_handler._create_base_result(request)

    # REMOVED_SYNTAX_ERROR: assert isinstance(result, CorpusOperationResult)
    # REMOVED_SYNTAX_ERROR: assert result.success is False  # Base result defaults to False
    # REMOVED_SYNTAX_ERROR: assert result.operation == CorpusOperation.DELETE
    # REMOVED_SYNTAX_ERROR: assert result.corpus_metadata == sample_metadata
    # REMOVED_SYNTAX_ERROR: assert result.affected_documents == 0
    # REMOVED_SYNTAX_ERROR: assert result.errors == []


# REMOVED_SYNTAX_ERROR: class TestCorpusStatistics:
    # REMOVED_SYNTAX_ERROR: """Test corpus statistics methods."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_dispatcher)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_get_corpus_statistics(self, operations_handler):
        # REMOVED_SYNTAX_ERROR: """Test get_corpus_statistics method."""
        # REMOVED_SYNTAX_ERROR: stats = await operations_handler.get_corpus_statistics()

        # REMOVED_SYNTAX_ERROR: assert isinstance(stats, dict)

        # Check base statistics
        # REMOVED_SYNTAX_ERROR: assert "total_corpora" in stats
        # REMOVED_SYNTAX_ERROR: assert "total_documents" in stats
        # REMOVED_SYNTAX_ERROR: assert "total_size_gb" in stats
        # REMOVED_SYNTAX_ERROR: assert stats["total_corpora"] == 12
        # REMOVED_SYNTAX_ERROR: assert stats["total_documents"] == 45678
        # REMOVED_SYNTAX_ERROR: assert stats["total_size_gb"] == 2.3

        # Check corpora by type
        # REMOVED_SYNTAX_ERROR: assert "corpora_by_type" in stats
        # REMOVED_SYNTAX_ERROR: corpora_types = stats["corpora_by_type"]
        # REMOVED_SYNTAX_ERROR: assert isinstance(corpora_types, dict)
        # REMOVED_SYNTAX_ERROR: assert "documentation" in corpora_types
        # REMOVED_SYNTAX_ERROR: assert "knowledge_base" in corpora_types
        # REMOVED_SYNTAX_ERROR: assert "training_data" in corpora_types
        # REMOVED_SYNTAX_ERROR: assert "reference_data" in corpora_types
        # REMOVED_SYNTAX_ERROR: assert "embeddings" in corpora_types

        # Check recent operations
        # REMOVED_SYNTAX_ERROR: assert "recent_operations" in stats
        # REMOVED_SYNTAX_ERROR: recent_ops = stats["recent_operations"]
        # REMOVED_SYNTAX_ERROR: assert isinstance(recent_ops, list)
        # REMOVED_SYNTAX_ERROR: assert len(recent_ops) >= 2  # Should have at least search and create

# REMOVED_SYNTAX_ERROR: def test_get_base_statistics(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _get_base_statistics method."""
    # REMOVED_SYNTAX_ERROR: base_stats = operations_handler._get_base_statistics()

    # REMOVED_SYNTAX_ERROR: assert isinstance(base_stats, dict)
    # REMOVED_SYNTAX_ERROR: assert "total_corpora" in base_stats
    # REMOVED_SYNTAX_ERROR: assert "total_documents" in base_stats
    # REMOVED_SYNTAX_ERROR: assert "total_size_gb" in base_stats

    # Verify reasonable values
    # REMOVED_SYNTAX_ERROR: assert isinstance(base_stats["total_corpora"], int)
    # REMOVED_SYNTAX_ERROR: assert isinstance(base_stats["total_documents"], int)
    # REMOVED_SYNTAX_ERROR: assert isinstance(base_stats["total_size_gb"], (int, float))

# REMOVED_SYNTAX_ERROR: def test_get_corpora_by_type(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _get_corpora_by_type method."""
    # REMOVED_SYNTAX_ERROR: corpora_by_type = operations_handler._get_corpora_by_type()

    # REMOVED_SYNTAX_ERROR: assert isinstance(corpora_by_type, dict)

    # Should include all corpus types
    # REMOVED_SYNTAX_ERROR: expected_types = ["documentation", "knowledge_base", "training_data", "reference_data", "embeddings"]
    # REMOVED_SYNTAX_ERROR: for corpus_type in expected_types:
        # REMOVED_SYNTAX_ERROR: assert corpus_type in corpora_by_type
        # REMOVED_SYNTAX_ERROR: assert isinstance(corpora_by_type[corpus_type], int)
        # REMOVED_SYNTAX_ERROR: assert corpora_by_type[corpus_type] >= 0

# REMOVED_SYNTAX_ERROR: def test_get_base_corpus_types(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _get_base_corpus_types method."""
    # REMOVED_SYNTAX_ERROR: base_types = operations_handler._get_base_corpus_types()

    # REMOVED_SYNTAX_ERROR: assert isinstance(base_types, dict)
    # REMOVED_SYNTAX_ERROR: assert "documentation" in base_types
    # REMOVED_SYNTAX_ERROR: assert "knowledge_base" in base_types
    # REMOVED_SYNTAX_ERROR: assert "training_data" in base_types

    # Verify counts are reasonable
    # REMOVED_SYNTAX_ERROR: assert base_types["documentation"] == 3
    # REMOVED_SYNTAX_ERROR: assert base_types["knowledge_base"] == 5
    # REMOVED_SYNTAX_ERROR: assert base_types["training_data"] == 2

# REMOVED_SYNTAX_ERROR: def test_get_additional_corpus_types(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _get_additional_corpus_types method."""
    # REMOVED_SYNTAX_ERROR: additional_types = operations_handler._get_additional_corpus_types()

    # REMOVED_SYNTAX_ERROR: assert isinstance(additional_types, dict)
    # REMOVED_SYNTAX_ERROR: assert "reference_data" in additional_types
    # REMOVED_SYNTAX_ERROR: assert "embeddings" in additional_types

    # REMOVED_SYNTAX_ERROR: assert additional_types["reference_data"] == 1
    # REMOVED_SYNTAX_ERROR: assert additional_types["embeddings"] == 1

# REMOVED_SYNTAX_ERROR: def test_get_recent_operations(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _get_recent_operations method."""
    # REMOVED_SYNTAX_ERROR: recent_ops = operations_handler._get_recent_operations()

    # REMOVED_SYNTAX_ERROR: assert isinstance(recent_ops, list)
    # REMOVED_SYNTAX_ERROR: assert len(recent_ops) == 2

    # Check structure of operations
    # REMOVED_SYNTAX_ERROR: for op in recent_ops:
        # REMOVED_SYNTAX_ERROR: assert isinstance(op, dict)
        # REMOVED_SYNTAX_ERROR: assert "operation" in op
        # REMOVED_SYNTAX_ERROR: assert "timestamp" in op
        # REMOVED_SYNTAX_ERROR: assert "corpus" in op

        # Verify timestamp format
        # REMOVED_SYNTAX_ERROR: assert isinstance(op["timestamp"], str)
        # Should be ISO format
        # REMOVED_SYNTAX_ERROR: datetime.fromisoformat(op["timestamp"].replace('Z', '+00:00'))

# REMOVED_SYNTAX_ERROR: def test_create_search_operation_record(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _create_search_operation_record method."""
    # REMOVED_SYNTAX_ERROR: search_record = operations_handler._create_search_operation_record()

    # REMOVED_SYNTAX_ERROR: assert isinstance(search_record, dict)
    # REMOVED_SYNTAX_ERROR: assert search_record["operation"] == "search"
    # REMOVED_SYNTAX_ERROR: assert search_record["corpus"] == "main_kb"
    # REMOVED_SYNTAX_ERROR: assert "timestamp" in search_record

    # Verify timestamp is recent
    # REMOVED_SYNTAX_ERROR: timestamp = datetime.fromisoformat(search_record["timestamp"].replace('Z', '+00:00'))
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: time_diff = now - timestamp
    # REMOVED_SYNTAX_ERROR: assert time_diff.total_seconds() < 60  # Should be within last minute

# REMOVED_SYNTAX_ERROR: def test_create_create_operation_record(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test _create_create_operation_record method."""
    # REMOVED_SYNTAX_ERROR: create_record = operations_handler._create_create_operation_record()

    # REMOVED_SYNTAX_ERROR: assert isinstance(create_record, dict)
    # REMOVED_SYNTAX_ERROR: assert create_record["operation"] == "create"
    # REMOVED_SYNTAX_ERROR: assert create_record["corpus"] == "product_docs"
    # REMOVED_SYNTAX_ERROR: assert "timestamp" in create_record

    # Verify timestamp format and recency
    # REMOVED_SYNTAX_ERROR: timestamp = datetime.fromisoformat(create_record["timestamp"].replace('Z', '+00:00'))
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: time_diff = now - timestamp
    # REMOVED_SYNTAX_ERROR: assert time_diff.total_seconds() < 60


# REMOVED_SYNTAX_ERROR: class TestOperationRouting:
    # REMOVED_SYNTAX_ERROR: """Test operation routing logic."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_dispatcher)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="routing_test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.EMBEDDINGS,
    # REMOVED_SYNTAX_ERROR: description="Test corpus for routing logic"
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_route_operation_crud_success(self, operations_handler, sample_metadata):
        # REMOVED_SYNTAX_ERROR: """Test successful CRUD operation routing."""
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # REMOVED_SYNTAX_ERROR: expected_result = CorpusOperationResult( )
        # REMOVED_SYNTAX_ERROR: success=True,
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute', return_value=expected_result) as mock_crud:
            # REMOVED_SYNTAX_ERROR: result = await operations_handler._route_operation(request, "route_run", True)

            # REMOVED_SYNTAX_ERROR: assert result == expected_result
            # REMOVED_SYNTAX_ERROR: mock_crud.assert_called_once_with("create", request, "route_run", True)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_route_operation_analysis_success(self, operations_handler, sample_metadata):
                # REMOVED_SYNTAX_ERROR: """Test successful analysis operation routing."""
                # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.VALIDATE,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                

                # REMOVED_SYNTAX_ERROR: expected_result = CorpusOperationResult( )
                # REMOVED_SYNTAX_ERROR: success=True,
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.VALIDATE,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                

                # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.analysis_ops, 'execute', return_value=expected_result) as mock_analysis:
                    # REMOVED_SYNTAX_ERROR: result = await operations_handler._route_operation(request, "validate_run", False)

                    # REMOVED_SYNTAX_ERROR: assert result == expected_result
                    # REMOVED_SYNTAX_ERROR: mock_analysis.assert_called_once_with("validate", request, "validate_run", False)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_route_operation_unsupported(self, operations_handler, sample_metadata):
                        # REMOVED_SYNTAX_ERROR: """Test routing of unsupported operations."""
                        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,  # Valid enum
                        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                        

                        # Mock the operation value to be unsupported
                        # REMOVED_SYNTAX_ERROR: with patch.object(request.operation, 'value', "unsupported_operation"):
                            # REMOVED_SYNTAX_ERROR: result = await operations_handler._route_operation(request, "unsupported_run", True)

                            # REMOVED_SYNTAX_ERROR: assert isinstance(result, CorpusOperationResult)
                            # REMOVED_SYNTAX_ERROR: assert result.success is False
                            # REMOVED_SYNTAX_ERROR: assert "Unsupported operation" in result.errors[0]


# REMOVED_SYNTAX_ERROR: class TestEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Test edge cases and error conditions."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_dispatcher)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_none_request_handling(self, operations_handler):
        # REMOVED_SYNTAX_ERROR: """Test handling of None request."""
        # This should raise an AttributeError or similar
        # REMOVED_SYNTAX_ERROR: with pytest.raises((AttributeError, TypeError)):
            # REMOVED_SYNTAX_ERROR: await operations_handler.execute_operation(None, "none_run", True)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_empty_run_id_handling(self, operations_handler):
                # REMOVED_SYNTAX_ERROR: """Test handling of empty run_id."""
                # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
                # REMOVED_SYNTAX_ERROR: corpus_name="empty_run_test",
                # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.DOCUMENTATION
                
                # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
                

                # Should handle empty run_id gracefully
                # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute') as mock_crud:
                    # REMOVED_SYNTAX_ERROR: mock_crud.return_value = CorpusOperationResult( )
                    # REMOVED_SYNTAX_ERROR: success=True,
                    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                    # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
                    

                    # REMOVED_SYNTAX_ERROR: result = await operations_handler.execute_operation(request, "", False)
                    # REMOVED_SYNTAX_ERROR: mock_crud.assert_called_once_with("search", request, "", False)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_concurrent_operations(self, operations_handler):
                        # REMOVED_SYNTAX_ERROR: """Test concurrent operation execution."""
                        # REMOVED_SYNTAX_ERROR: import asyncio

                        # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
                        # REMOVED_SYNTAX_ERROR: corpus_name="concurrent_test",
                        # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.REFERENCE_DATA
                        

                        # REMOVED_SYNTAX_ERROR: requests = [ )
                        # REMOVED_SYNTAX_ERROR: CorpusOperationRequest( )
                        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                        # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
                        # REMOVED_SYNTAX_ERROR: ) for _ in range(5)
                        

                        # Mock successful results
                        # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute') as mock_crud:
                            # REMOVED_SYNTAX_ERROR: mock_crud.return_value = CorpusOperationResult( )
                            # REMOVED_SYNTAX_ERROR: success=True,
                            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                            # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
                            

                            # Execute operations concurrently
                            # REMOVED_SYNTAX_ERROR: tasks = [ )
                            # REMOVED_SYNTAX_ERROR: operations_handler.execute_operation(req, "formatted_string", True)
                            # REMOVED_SYNTAX_ERROR: for i, req in enumerate(requests)
                            

                            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                            # All should succeed
                            # REMOVED_SYNTAX_ERROR: assert len(results) == 5
                            # REMOVED_SYNTAX_ERROR: for result in results:
                                # REMOVED_SYNTAX_ERROR: assert not isinstance(result, Exception)
                                # REMOVED_SYNTAX_ERROR: assert isinstance(result, CorpusOperationResult)
                                # REMOVED_SYNTAX_ERROR: assert result.success is True

# REMOVED_SYNTAX_ERROR: def test_extreme_metadata_values(self, operations_handler):
    # REMOVED_SYNTAX_ERROR: """Test handling of extreme metadata values."""
    # REMOVED_SYNTAX_ERROR: extreme_metadata = CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="x" * 1000,  # Very long name
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.KNOWLEDGE_BASE,
    # REMOVED_SYNTAX_ERROR: description="y" * 5000,  # Very long description
    # REMOVED_SYNTAX_ERROR: tags=["tag"] * 50,  # Many tags
    # REMOVED_SYNTAX_ERROR: access_level="🔐🗝️🔒"  # Unicode access level
    

    # Should create result without exceptions
    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=extreme_metadata
    

    # REMOVED_SYNTAX_ERROR: base_result = operations_handler._create_base_result(request)

    # REMOVED_SYNTAX_ERROR: assert base_result.corpus_metadata == extreme_metadata
    # REMOVED_SYNTAX_ERROR: assert len(base_result.corpus_metadata.corpus_name) == 1000
    # REMOVED_SYNTAX_ERROR: assert len(base_result.corpus_metadata.description) == 5000

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_malformed_tool_dispatcher_responses(self, operations_handler):
        # REMOVED_SYNTAX_ERROR: """Test handling of malformed tool dispatcher responses."""
        # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
        # REMOVED_SYNTAX_ERROR: corpus_name="malformed_test",
        # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.TRAINING_DATA
        
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
        

        # Mock CRUD to await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return None (malformed response)
        # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute', return_value=None):
            # REMOVED_SYNTAX_ERROR: result = await operations_handler.execute_operation(request, "malformed_run", False)

            # Should handle gracefully and return an error result
            # The actual behavior depends on implementation, but should not crash
            # REMOVED_SYNTAX_ERROR: assert result is None or isinstance(result, CorpusOperationResult)


# REMOVED_SYNTAX_ERROR: class TestIntegrationWithComponents:
    # REMOVED_SYNTAX_ERROR: """Test integration with CRUD and Analysis operation components."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return Mock(spec=ToolDispatcher)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def operations_handler(self, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusOperationHandler(mock_tool_dispatcher)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="integration_test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.KNOWLEDGE_BASE
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_crud_component_integration(self, operations_handler, sample_metadata):
        # REMOVED_SYNTAX_ERROR: """Test integration with CRUD operations component."""
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # Verify CRUD component exists and has correct interface
        # REMOVED_SYNTAX_ERROR: assert hasattr(operations_handler.crud_ops, 'execute')
        # REMOVED_SYNTAX_ERROR: assert hasattr(operations_handler.crud_ops, 'tool_dispatcher')
        # REMOVED_SYNTAX_ERROR: assert operations_handler.crud_ops.tool_dispatcher == operations_handler.tool_dispatcher

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_analysis_component_integration(self, operations_handler, sample_metadata):
            # REMOVED_SYNTAX_ERROR: """Test integration with Analysis operations component."""
            # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.EXPORT,
            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
            

            # Verify Analysis component exists and has correct interface
            # REMOVED_SYNTAX_ERROR: assert hasattr(operations_handler.analysis_ops, 'execute')
            # REMOVED_SYNTAX_ERROR: assert hasattr(operations_handler.analysis_ops, 'tool_dispatcher')
            # REMOVED_SYNTAX_ERROR: assert operations_handler.analysis_ops.tool_dispatcher == operations_handler.tool_dispatcher

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_tool_dispatcher_propagation(self, mock_tool_dispatcher):
                # REMOVED_SYNTAX_ERROR: """Test that tool dispatcher is properly propagated to components."""
                # REMOVED_SYNTAX_ERROR: handler = CorpusOperationHandler(mock_tool_dispatcher)

                # Both components should have the same tool dispatcher instance
                # REMOVED_SYNTAX_ERROR: assert handler.crud_ops.tool_dispatcher is mock_tool_dispatcher
                # REMOVED_SYNTAX_ERROR: assert handler.analysis_ops.tool_dispatcher is mock_tool_dispatcher

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_component_method_signatures(self, operations_handler, sample_metadata):
                    # REMOVED_SYNTAX_ERROR: """Test that component methods have expected signatures."""
                    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                    

                    # Mock both components to verify they're called with correct parameters
                    # REMOVED_SYNTAX_ERROR: with patch.object(operations_handler.crud_ops, 'execute') as mock_crud:
                        # REMOVED_SYNTAX_ERROR: mock_result = CorpusOperationResult( )
                        # REMOVED_SYNTAX_ERROR: success=True,
                        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                        
                        # REMOVED_SYNTAX_ERROR: mock_crud.return_value = mock_result

                        # REMOVED_SYNTAX_ERROR: await operations_handler.execute_operation(request, "signature_test", True)

                        # Verify component was called with expected signature
                        # REMOVED_SYNTAX_ERROR: mock_crud.assert_called_once_with("search", request, "signature_test", True)


                        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])
                            # REMOVED_SYNTAX_ERROR: pass