"""
ClickHouse Schema Exception Types Tests - Issue #374

Tests that validate proper exception type classification for ClickHouse schema operations.
These tests validate the working exception handling system.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Improve analytics schema reliability and deployment success
- Value Impact: Reduces schema deployment failures and rollback time
- Revenue Impact: Prevents analytics data loss during schema migrations

Test Purpose:
- Validate specific schema error type classification in ClickHouse operations
- Confirm proper exception types are available for schema operations
- Verify table creation, migration, and index error specificity
- Test proper schema-specific exception handling implementation

Expected Behavior:
- Tests validate working exception classification system
- Tests confirm specific schema error types are available
- Clear validation of proper schema exception handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.db.clickhouse_schema import ClickHouseTraceSchema
from netra_backend.app.db.transaction_errors import (
    TransactionError, classify_error, TableCreationError, ColumnModificationError, 
    IndexCreationError, MigrationError, TableDependencyError, ConstraintViolationError,
    EngineConfigurationError
)


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseSchemaExceptionTypes(SSotAsyncTestCase):
    """
    Tests validating proper exception type classification in ClickHouse schema operations.

    These tests validate the working system where:
    1. Table creation errors use specific exception classification
    2. Column modification errors have proper type handling
    3. Index creation/deletion errors provide adequate context
    4. Schema migration errors use proper classification
    """
    
    @pytest.fixture
    def schema_manager(self):
        """Create ClickHouse schema manager for testing."""
        return ClickHouseTraceSchema()

    @pytest.mark.asyncio
    async def test_table_creation_uses_specific_error_types(self, schema_manager):
        """
        Test verifies table creation errors use specific TableCreationError types.
        
        Verifies that table creation errors are properly classified as
        TableCreationError instead of generic Exception types.
        """
        # Mock table creation syntax error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock executor to raise ProgrammingError
            async def mock_executor(func, *args):
                raise ProgrammingError(
                    "Syntax error in CREATE TABLE statement", None, None
                )
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                table_schema = """
                CREATE TABLE test_table (
                    id UInt64,
                    name String
                ) ENGINE = MergeTree() ORDER BY id
                """
                
                # Should raise TableCreationError (specific type)
                with pytest.raises(TableCreationError) as exc_info:
                    await schema_manager.create_table("test_table", table_schema)
                
                error_name = type(exc_info.value).__name__
                error_message = str(exc_info.value)
                
                # Verify specific error type and context
                assert error_name == "TableCreationError", \
                    f"Should be TableCreationError, got {error_name}"
                assert "test_table" in error_message, "Should include table name"
                assert "Failed to create table" in error_message, "Should include operation context"

    @pytest.mark.asyncio
    async def test_column_modification_uses_specific_error_types(self, schema_manager):
        """
        Test verifies column modification errors use specific ColumnModificationError types.
        
        Verifies that column modification errors are properly classified as
        ColumnModificationError instead of generic Exception types.
        """
        # Mock column type incompatibility error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock executor to raise OperationalError
            async def mock_executor(func, *args):
                raise OperationalError(
                    "Cannot convert column 'id' from UInt64 to String", None, None
                )
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                # Should raise ColumnModificationError (specific type)
                with pytest.raises(ColumnModificationError) as exc_info:
                    await schema_manager.modify_column("test_table", "id", "String")
                
                error_name = type(exc_info.value).__name__
                error_message = str(exc_info.value)
                
                # Verify specific error type and context
                assert error_name == "ColumnModificationError", \
                    f"Should be ColumnModificationError, got {error_name}"
                assert "id" in error_message, "Should include column name"
                assert "test_table" in error_message, "Should include table name"
                assert "String" in error_message, "Should include target type"

    @pytest.mark.asyncio
    async def test_index_creation_uses_specific_error_types(self, schema_manager):
        """
        Test verifies index creation errors use specific IndexCreationError types.
        
        Verifies that index creation errors are properly classified as
        IndexCreationError instead of generic Exception types.
        """
        # Mock index creation conflict error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock executor to raise IntegrityError
            async def mock_executor(func, *args):
                raise IntegrityError(
                    "Index 'test_index' already exists on table 'test_table'", None, None
                )
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                # Should raise IndexCreationError (specific type)
                with pytest.raises(IndexCreationError) as exc_info:
                    await schema_manager.create_index("test_table", "test_index", ["column1"])
                
                error_name = type(exc_info.value).__name__
                error_message = str(exc_info.value)
                
                # Verify specific error type and context
                assert error_name == "IndexCreationError", \
                    f"Should be IndexCreationError, got {error_name}"
                assert "test_index" in error_message, "Should include index name"
                assert "test_table" in error_message, "Should include table name"

    @pytest.mark.asyncio
    async def test_schema_migration_provides_rollback_error_context(self, schema_manager):
        """
        Test verifies migration errors provide proper rollback context.
        
        Verifies that schema migration failures include sufficient
        context for rollback operations and partial migration state.
        """
        # Mock migration failure in the middle of operation
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            call_count = 0
            async def mock_executor(func, *args):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return None  # First operation succeeds
                else:
                    raise OperationalError("Cannot modify column old_col: type conversion failed", None, None)  # Second fails
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                migration_steps = [
                    "ALTER TABLE test_table ADD COLUMN new_col String",
                    "ALTER TABLE test_table MODIFY COLUMN old_col UInt32",
                ]
                
                # Should raise ColumnModificationError with migration context
                with pytest.raises(ColumnModificationError) as exc_info:
                    await schema_manager.execute_migration("migration_001", migration_steps)
                
                error_message = str(exc_info.value)
                
                # Verify migration context is included
                assert "Migration Error:" in error_message, "Should include migration error prefix"
                assert "migration_001" in error_message, "Should include migration name"
                assert "step 2" in error_message, "Should include failed step number"
                assert "Completed Steps:" in error_message, "Should list completed steps"
                assert "Rollback Required:" in error_message, "Should indicate rollback need"

    @pytest.mark.asyncio
    async def test_table_dependency_error_provides_relationship_context(self, schema_manager):
        """
        Test verifies dependency errors provide proper relationship context.
        
        Verifies that table dependency errors include sufficient
        context about dependent objects and resolution steps.
        """
        # Mock table deletion with dependency error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock executor to raise IntegrityError with dependency context
            async def mock_executor(func, *args):
                raise IntegrityError(
                    "Cannot drop table 'parent_table' because it is referenced by materialized view 'child_view'", 
                    None, None
                )
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                # Should raise TableCreationError with dependency context
                with pytest.raises(TableCreationError) as exc_info:
                    await schema_manager.drop_table("parent_table")
                
                error_message = str(exc_info.value)
                
                # Verify dependency context is included
                assert "Table Dependency Error:" in error_message, "Should include dependency error prefix"
                assert "parent_table" in error_message, "Should include target table"
                assert "Resolution Steps:" in error_message, "Should provide resolution steps"

    def test_schema_manager_uses_transaction_error_classification(self):
        """
        Test verifies schema manager properly uses error classification.
        
        Verifies that ClickHouseTraceSchema integrates with the
        transaction error classification system.
        """
        # Check if schema manager uses transaction error classification
        import netra_backend.app.db.clickhouse_schema as schema_module
        
        # Verify imports are available
        assert hasattr(schema_module, 'classify_error'), \
            "Schema module should import classify_error"
        assert hasattr(schema_module, 'TableCreationError'), \
            "Schema module should import TableCreationError"
        assert hasattr(schema_module, 'ColumnModificationError'), \
            "Schema module should import ColumnModificationError" 
        assert hasattr(schema_module, 'IndexCreationError'), \
            "Schema module should import IndexCreationError"
        
        # Verify schema manager instance has the required methods
        schema_manager = ClickHouseTraceSchema()
        assert hasattr(schema_manager, 'create_table'), \
            "Schema manager should have create_table method"
        assert hasattr(schema_manager, 'modify_column'), \
            "Schema manager should have modify_column method"
        assert hasattr(schema_manager, 'create_index'), \
            "Schema manager should have create_index method"
        assert hasattr(schema_manager, 'execute_migration'), \
            "Schema manager should have execute_migration method"

    @pytest.mark.asyncio
    async def test_constraint_violation_provides_constraint_context(self, schema_manager):
        """
        Test verifies constraint errors provide proper constraint context.
        
        Verifies that constraint violation errors include details about
        which constraints failed and suggested fixes.
        """
        # Mock constraint violation error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock executor to raise IntegrityError with constraint context
            async def mock_executor(func, *args):
                raise IntegrityError(
                    "Check constraint 'positive_values' violated: column 'amount' value -100 is negative", 
                    None, None
                )
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                # Should raise ColumnModificationError with constraint context
                with pytest.raises(ColumnModificationError) as exc_info:
                    await schema_manager.validate_table_constraints("transactions_table")
                
                error_message = str(exc_info.value)
                
                # Verify constraint context is included
                assert "Constraint Violation Error:" in error_message, "Should include constraint error prefix"
                assert "transactions_table" in error_message, "Should include table name"
                assert "Fix Suggestion:" in error_message, "Should suggest how to fix"

    @pytest.mark.asyncio
    async def test_engine_configuration_error_provides_engine_context(self, schema_manager):
        """
        Test verifies engine errors provide proper configuration context.
        
        Verifies that ClickHouse engine configuration errors include
        details about engine requirements and configuration issues.
        """
        # Mock engine configuration error
        with patch.object(schema_manager, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock executor to raise OperationalError with engine context
            async def mock_executor(func, *args):
                raise OperationalError(
                    "Engine ReplacingMergeTree requires ORDER BY clause", None, None
                )
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_executor
                
                invalid_table_schema = """
                CREATE TABLE test_table (
                    id UInt64,
                    name String
                ) ENGINE = ReplacingMergeTree()
                """
                
                # Should raise EngineConfigurationError with engine context
                with pytest.raises(EngineConfigurationError) as exc_info:
                    await schema_manager.create_table("test_table", invalid_table_schema)
                
                error_message = str(exc_info.value)
                
                # Verify engine configuration context is included
                assert "Engine configuration issue" in error_message, "Should include engine configuration error context"
                assert "ReplacingMergeTree requires ORDER BY clause" in error_message, "Should include specific engine error details"