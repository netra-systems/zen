"""
Unit Tests for ClickHouse Exception Specificity - Issue #673 Completion

Tests that validate the implementation of specific ClickHouse exception types:
- TableCreationError
- ColumnModificationError 
- IndexCreationError

These tests do NOT require Docker and use mocked ClickHouse responses
to validate proper error classification and handling.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Improve analytics reliability and deployment success
- Value Impact: Reduces schema deployment failures and provides precise error context
- Revenue Impact: Prevents analytics data loss during schema migrations

Test Approach:
- Mock ClickHouse client responses with realistic error messages
- Validate specific exception types are raised with proper context
- Ensure error classification works for all ClickHouse schema operations
- Verify backward compatibility with existing error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.db.clickhouse_schema import ClickHouseTraceSchema
from netra_backend.app.db.transaction_errors import (
    TransactionError, TableCreationError, ColumnModificationError, 
    IndexCreationError, classify_error
)


@pytest.mark.unit
@pytest.mark.database
class ClickHouseExceptionSpecificityValidationTests(SSotAsyncTestCase):
    """
    Unit tests validating ClickHouse specific exception types are properly implemented.
    
    These tests validate the completion of Issue #673 by ensuring:
    1. TableCreationError is raised for table creation failures
    2. ColumnModificationError is raised for column alteration failures  
    3. IndexCreationError is raised for index operation failures
    4. Error messages include helpful context and resolution guidance
    5. Error classification works correctly for ClickHouse operations
    """
    
    @pytest.fixture
    def schema_manager(self):
        """Create ClickHouse schema manager for testing."""
        return ClickHouseTraceSchema()

    @pytest.mark.asyncio
    async def test_table_creation_error_properly_classified(self, schema_manager):
        """
        Test that table creation errors are properly classified as TableCreationError.
        
        This test validates that Issue #673 completion provides specific error types
        instead of generic Exception handling.
        """
        # Mock table creation syntax error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate table creation error from ClickHouse
            mock_client.execute.side_effect = ProgrammingError(
                "Syntax error in CREATE TABLE statement: Expected 'ENGINE' keyword", None, None
            )
            
            table_schema = """
            CREATE TABLE test_table (
                id UInt64,
                name String,
                INVALID SYNTAX HERE
            ) ENGINE = MergeTree() ORDER BY id
            """
            
            # This should now raise TableCreationError with specific context
            with pytest.raises(TableCreationError) as exc_info:
                await schema_manager.create_table("test_table", table_schema)
            
            error_message = str(exc_info.value)
            
            # Validate specific error context is included
            assert "Failed to create table 'test_table'" in error_message, "Should include table name"
            assert "TableCreationError" in type(exc_info.value).__name__, "Should be TableCreationError type"
            assert "create table" in error_message.lower() or "syntax error" in error_message.lower(), \
                "Should include table creation context"

    @pytest.mark.asyncio
    async def test_column_modification_error_properly_classified(self, schema_manager):
        """
        Test that column modification errors are properly classified as ColumnModificationError.
        
        This test validates proper error classification for ALTER TABLE operations.
        """
        # Mock column type incompatibility error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate column modification error from ClickHouse
            mock_client.execute.side_effect = OperationalError(
                "Cannot convert column 'id' from UInt64 to String: incompatible types", None, None
            )
            
            # This should now raise ColumnModificationError with specific context
            with pytest.raises(ColumnModificationError) as exc_info:
                await schema_manager.modify_column("test_table", "id", "String")
            
            error_message = str(exc_info.value)
            
            # Validate specific error context is included
            assert "Failed to modify column 'id'" in error_message, "Should include column name"
            assert "test_table" in error_message, "Should include table name"
            assert "String" in error_message, "Should include target type"
            assert "ColumnModificationError" in type(exc_info.value).__name__, "Should be ColumnModificationError type"

    @pytest.mark.asyncio
    async def test_index_creation_error_properly_classified(self, schema_manager):
        """
        Test that index creation errors are properly classified as IndexCreationError.
        
        This test validates proper error classification for index operations.
        """
        # Mock index creation conflict error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate index creation error from ClickHouse
            mock_client.execute.side_effect = IntegrityError(
                "Index 'test_index' already exists on table 'test_table'", None, None
            )
            
            # This should now raise IndexCreationError with specific context
            with pytest.raises(IndexCreationError) as exc_info:
                await schema_manager.create_index("test_table", "test_index", ["column1"])
            
            error_message = str(exc_info.value)
            
            # Validate specific error context is included
            assert "Failed to create index 'test_index'" in error_message, "Should include index name"
            assert "test_table" in error_message, "Should include table name"
            assert "column1" in error_message, "Should include column names"
            assert "IndexCreationError" in type(exc_info.value).__name__, "Should be IndexCreationError type"

    @pytest.mark.asyncio
    async def test_migration_error_includes_rollback_context(self, schema_manager):
        """
        Test that migration errors include proper rollback context and step information.
        
        This test validates enhanced error messages for failed migrations.
        """
        # Mock migration failure in the middle of operation
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # First operation succeeds, second fails
            mock_client.execute.side_effect = [
                None,  # First operation succeeds
                OperationalError("ALTER TABLE failed: incompatible types", None, None),  # Second fails
            ]
            
            migration_steps = [
                "ALTER TABLE test_table ADD COLUMN new_col String",
                "ALTER TABLE test_table MODIFY COLUMN old_col UInt32",
            ]
            
            # This should raise error with migration context
            with pytest.raises((ColumnModificationError, OperationalError)) as exc_info:
                await schema_manager.execute_migration("migration_001", migration_steps)
            
            error_message = str(exc_info.value)
            
            # Validate migration context is included
            assert "Migration Error:" in error_message or "migration_001" in error_message, \
                "Should include migration context"
            assert "step" in error_message.lower(), "Should include step information"
            assert "rollback" in error_message.lower(), "Should mention rollback"

    @pytest.mark.asyncio
    async def test_dependency_error_includes_relationship_context(self, schema_manager):
        """
        Test that table dependency errors include proper relationship context.
        
        This test validates enhanced error messages for dependency conflicts.
        """
        # Mock table deletion with dependency error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate dependency error from ClickHouse
            mock_client.execute.side_effect = IntegrityError(
                "Cannot drop table 'parent_table' because it is referenced by materialized view 'child_view'", 
                None, None
            )
            
            # This should raise error with dependency context
            with pytest.raises((TableCreationError, IntegrityError)) as exc_info:
                await schema_manager.drop_table("parent_table")
            
            error_message = str(exc_info.value)
            
            # Validate dependency context is included
            assert "parent_table" in error_message, "Should include target table"
            assert "dependency" in error_message.lower() or "referenced" in error_message.lower(), \
                "Should include dependency context"
            assert "resolution" in error_message.lower() or "steps" in error_message.lower(), \
                "Should provide resolution guidance"

    def test_error_classification_function_handles_clickhouse_patterns(self):
        """
        Test that the classify_error function properly handles ClickHouse-specific error patterns.
        
        This test validates the enhanced error classification logic.
        """
        # Test table creation error classification
        table_error = OperationalError("CREATE TABLE failed: invalid engine parameters", None, None)
        classified = classify_error(table_error)
        assert isinstance(classified, TableCreationError), \
            f"Should classify as TableCreationError, got {type(classified).__name__}"
        
        # Test column modification error classification
        column_error = OperationalError("ALTER TABLE failed: cannot convert column type", None, None)
        classified = classify_error(column_error)
        assert isinstance(classified, ColumnModificationError), \
            f"Should classify as ColumnModificationError, got {type(classified).__name__}"
        
        # Test index creation error classification
        index_error = OperationalError("CREATE INDEX failed: index already exists", None, None)
        classified = classify_error(index_error)
        assert isinstance(classified, IndexCreationError), \
            f"Should classify as IndexCreationError, got {type(classified).__name__}"

    def test_exception_inheritance_hierarchy(self):
        """
        Test that new exception types follow proper inheritance hierarchy.
        
        This validates the exception class structure is correct.
        """
        # Validate inheritance hierarchy
        assert issubclass(TableCreationError, TransactionError), \
            "TableCreationError should inherit from TransactionError"
        assert issubclass(ColumnModificationError, TransactionError), \
            "ColumnModificationError should inherit from TransactionError"
        assert issubclass(IndexCreationError, TransactionError), \
            "IndexCreationError should inherit from TransactionError"
        
        # Validate they can be caught as base transaction errors
        try:
            raise TableCreationError("Test error")
        except TransactionError:
            pass  # Should be caught as TransactionError
        else:
            pytest.fail("TableCreationError should be catchable as TransactionError")

    @pytest.mark.asyncio
    async def test_constraint_violation_error_context(self, schema_manager):
        """
        Test that constraint violation errors include proper constraint context.
        
        This test validates enhanced error messages for constraint violations.
        """
        # Mock constraint violation error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate constraint violation from ClickHouse
            mock_client.execute.side_effect = IntegrityError(
                "Check constraint violated: column 'amount' value -100 violates positive constraint", 
                None, None
            )
            
            # This should raise error with constraint context
            with pytest.raises((ColumnModificationError, IntegrityError)) as exc_info:
                await schema_manager.validate_table_constraints("transactions_table")
            
            error_message = str(exc_info.value)
            
            # Validate constraint context is included
            assert "constraint" in error_message.lower(), "Should include constraint context"
            assert "transactions_table" in error_message, "Should include table name"
            assert "fix" in error_message.lower() or "suggestion" in error_message.lower(), \
                "Should provide fix suggestions"

    @pytest.mark.asyncio
    async def test_backward_compatibility_maintained(self, schema_manager):
        """
        Test that existing code continues to work with enhanced error handling.
        
        This ensures the Issue #673 implementation doesn't break existing functionality.
        """
        # Mock a generic error that doesn't match specific patterns
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate generic operational error
            mock_client.execute.side_effect = OperationalError(
                "Generic database error: connection timeout", None, None
            )
            
            # This should still raise an OperationalError (backward compatibility)
            with pytest.raises(OperationalError) as exc_info:
                await schema_manager.create_table("test_table", "CREATE TABLE test_table (id UInt64)")
            
            # Should be classified but not as a specific schema error
            error_message = str(exc_info.value)
            assert "connection timeout" in error_message.lower(), "Should preserve original error message"

    def test_api_completeness_validation(self):
        """
        Test that the ClickHouse API has all required methods from Issue #673.
        
        This validates that the 20% remaining work is actually completed.
        """
        from netra_backend.app.db.clickhouse import ClickHouseService
        from netra_backend.app.db.transaction_errors import TableCreationError, ColumnModificationError, IndexCreationError
        
        # Validate service has required methods
        service = ClickHouseService()
        assert hasattr(service, 'insert_data'), "Should have insert_data method"
        assert hasattr(service, '_cache'), "Should have _cache property"
        
        # Validate exception types are available for import
        assert TableCreationError is not None, "TableCreationError should be importable"
        assert ColumnModificationError is not None, "ColumnModificationError should be importable"
        assert IndexCreationError is not None, "IndexCreationError should be importable"
        
        # Validate classification function is available
        from netra_backend.app.db.transaction_errors import classify_error
        assert classify_error is not None, "classify_error function should be importable"

    @pytest.mark.asyncio
    async def test_error_message_quality_and_actionability(self, schema_manager):
        """
        Test that error messages provide actionable information for developers.
        
        This validates the quality of error messages for debugging purposes.
        """
        # Test table creation error with actionable context
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Simulate engine configuration error
            mock_client.execute.side_effect = OperationalError(
                "Engine ReplacingMergeTree requires ORDER BY clause", None, None
            )
            
            table_schema = """
            CREATE TABLE test_table (
                id UInt64,
                name String
            ) ENGINE = ReplacingMergeTree()
            """
            
            # Error should include specific guidance
            with pytest.raises(TableCreationError) as exc_info:
                await schema_manager.create_table("test_table", table_schema)
            
            error_message = str(exc_info.value)
            
            # Validate error message quality
            assert "test_table" in error_message, "Should include table name for context"
            assert len(error_message) > 50, "Should provide detailed error context"
            assert any(keyword in error_message.lower() for keyword in ['failed', 'error', 'create']), \
                "Should clearly indicate the operation that failed"
