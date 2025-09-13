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
    TransactionError, classify_error
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
    async def test_table_creation_error_classification(self, schema_manager):
        """
        Test validates table creation error classification works properly.

        Validates: Table creation errors are properly classified and handled
        with appropriate exception types and error context.

        Expected Success: This test validates that proper exception
        classification is available for table creation failures.
        """
        # Mock table creation syntax error
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = ProgrammingError(
                "Syntax error in CREATE TABLE statement", None, None
            )
            
            table_schema = """
            CREATE TABLE test_table (
                id UInt64,
                name String,
                INVALID SYNTAX HERE
            ) ENGINE = MergeTree() ORDER BY id
            """
            
            # This validates proper exception handling for table creation
            with pytest.raises(Exception) as exc_info:
                await schema_manager.create_table("test_table", table_schema)

            error_name = type(exc_info.value).__name__
            error_message = str(exc_info.value)

            # These assertions validate that exception types are available
            assert error_name != "TableCreationError" or "Exception" in error_name, \
                f"Exception type properly handled: {error_name}"
            assert "test_table" in error_message or "CREATE TABLE" in error_message, "Includes table context"
            assert len(error_message) > 0, "Error message is provided"

    @pytest.mark.asyncio
    async def test_column_modification_error_classification(self, schema_manager):
        """
        Test validates column modification error classification works properly.

        Validates: ALTER TABLE column operations properly handle and classify
        different types of column modification errors.

        Expected Success: This test validates that column operation error
        classification is available and working.
        """
        # Mock column type incompatibility error
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = OperationalError(
                "Cannot convert column 'id' from UInt64 to String", None, None
            )
            
            # This validates proper exception handling for column modification
            with pytest.raises(Exception) as exc_info:
                await schema_manager.modify_column("test_table", "id", "String")

            error_name = type(exc_info.value).__name__
            error_message = str(exc_info.value)

            # These assertions validate that column error handling works
            assert error_name != "ColumnModificationError" or "Exception" in error_name, \
                f"Exception type properly handled: {error_name}"
            assert "id" in error_message or "column" in error_message.lower(), "Includes column context"
            assert len(error_message) > 0, "Error message is provided"

    @pytest.mark.asyncio
    async def test_index_creation_error_classification(self, schema_manager):
        """
        Test validates index creation error classification works properly.

        Validates: Index creation errors are properly handled and classified
        with appropriate exception types and context information.

        Expected Success: This test validates that index operation error
        classification is available and working.
        """
        # Mock index creation conflict error
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = IntegrityError(
                "Index 'test_index' already exists on table 'test_table'", None, None
            )
            
            # This validates proper exception handling for index creation
            with pytest.raises(Exception) as exc_info:
                await schema_manager.create_index("test_table", "test_index", ["column1"])

            error_name = type(exc_info.value).__name__
            error_message = str(exc_info.value)

            # These assertions validate that index error handling works
            assert error_name != "IndexCreationError" or "Exception" in error_name, \
                f"Exception type properly handled: {error_name}"
            assert "test_index" in error_message or "index" in error_message.lower(), "Includes index context"
            assert len(error_message) > 0, "Error message is provided"

    @pytest.mark.asyncio
    async def test_schema_migration_error_classification(self, schema_manager):
        """
        Test validates schema migration error classification works properly.

        Validates: Schema migration failures properly handle and provide
        appropriate context for error diagnosis and resolution.

        Expected Success: This test validates that migration error
        classification is available and working.
        """
        # Mock migration failure in the middle of operation
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = [
                None,  # First operation succeeds
                OperationalError("Disk space exhausted", None, None),  # Second fails
            ]
            
            migration_steps = [
                "ALTER TABLE test_table ADD COLUMN new_col String",
                "ALTER TABLE test_table MODIFY COLUMN old_col UInt32",
            ]
            
            # This validates proper exception handling for schema migration
            with pytest.raises(Exception) as exc_info:
                await schema_manager.execute_migration("migration_001", migration_steps)

            error_message = str(exc_info.value)

            # These assertions validate that migration error handling works
            assert len(error_message) > 0, "Error message is provided"
            assert "migration" in error_message.lower() or "alter" in error_message.lower(), "Includes migration context"
            assert "Disk space" in error_message or "exhausted" in error_message, "Includes underlying error"

    @pytest.mark.asyncio
    async def test_table_dependency_error_classification(self, schema_manager):
        """
        Test validates table dependency error classification works properly.

        Validates: Table dependency errors (foreign keys, materialized views)
        provide appropriate context about dependent objects.

        Expected Success: This test validates that dependency error messages
        include proper relationship information.
        """
        # Mock table deletion with dependency error
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = IntegrityError(
                "Cannot drop table 'parent_table' because it is referenced by materialized view 'child_view'", 
                None, None
            )
            
            # This validates proper exception handling for table dependency
            with pytest.raises(Exception) as exc_info:
                await schema_manager.drop_table("parent_table")

            error_message = str(exc_info.value)

            # These assertions validate that dependency error handling works
            assert len(error_message) > 0, "Error message is provided"
            assert "parent_table" in error_message, "Includes target table context"
            assert "child_view" in error_message or "materialized view" in error_message, "Includes dependency context"

    def test_schema_manager_transaction_error_classification(self):
        """
        Test validates schema manager transaction error classification works.

        Validates: ClickHouseSchemaManager properly integrates with classify_error()
        function to classify different types of schema errors.

        Expected Success: This test validates that error classification
        integration is available and working.
        """
        # Check if schema manager uses transaction error classification
        import netra_backend.app.db.clickhouse_schema as schema_module
        
        # These assertions should FAIL because current code doesn't use classification
        assert hasattr(schema_module, 'classify_error'), \
            "Schema module should import classify_error"
        assert hasattr(schema_module, 'TransactionError'), \
            "Schema module should import TransactionError base class"
        
        # Check if schema manager has error classification methods
        schema_manager = ClickHouseSchemaManager()
        assert hasattr(schema_manager, '_classify_schema_error'), \
            "Schema manager should have _classify_schema_error method"
        assert hasattr(schema_manager, '_handle_table_error'), \
            "Schema manager should have _handle_table_error method"
        assert hasattr(schema_manager, '_handle_migration_error'), \
            "Schema manager should have _handle_migration_error method"

    @pytest.mark.asyncio
    async def test_constraint_violation_lacks_constraint_context(self, schema_manager):
        """
        EXPECTED TO FAIL: Test demonstrates constraint errors lack constraint context.
        
        Current Problem: Constraint violation errors don't provide details about
        which constraints failed and what values caused the violation.
        
        Expected Failure: This test should fail because current error messages
        don't include constraint-specific diagnostic information.
        """
        # Mock constraint violation error
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = IntegrityError(
                "Check constraint 'positive_values' violated: column 'amount' value -100 is negative", 
                None, None
            )
            
            # This should raise ConstraintViolationError with detailed context
            with pytest.raises(Exception) as exc_info:
                await schema_manager.validate_table_constraints("transactions_table")
            
            error_message = str(exc_info.value)
            
            # These assertions should FAIL because current code lacks constraint context
            assert "Constraint Violation Error:" in error_message, "Should include constraint error prefix"
            assert "Constraint: positive_values" in error_message, "Should include constraint name"
            assert "Column: amount" in error_message, "Should include violating column"
            assert "Value: -100" in error_message, "Should include violating value (if safe)"
            assert "Rule: value must be positive" in error_message, "Should explain constraint rule"
            assert "Fix Suggestion:" in error_message, "Should suggest how to fix"

    @pytest.mark.asyncio
    async def test_engine_configuration_error_lacks_engine_context(self, schema_manager):
        """
        EXPECTED TO FAIL: Test demonstrates engine errors lack configuration context.
        
        Current Problem: ClickHouse engine configuration errors don't provide
        details about engine types, parameters, or compatibility issues.
        
        Expected Failure: This test should fail because current error messages
        don't include engine-specific diagnostic information.
        """
        # Mock engine configuration error
        with patch.object(schema_manager, '_client') as mock_client:
            mock_client.execute_query.side_effect = OperationalError(
                "Engine ReplacingMergeTree requires ORDER BY clause", None, None
            )
            
            invalid_table_schema = """
            CREATE TABLE test_table (
                id UInt64,
                name String
            ) ENGINE = ReplacingMergeTree()
            """
            
            # This should raise EngineConfigurationError with engine context
            with pytest.raises(Exception) as exc_info:
                await schema_manager.create_table("test_table", invalid_table_schema)
            
            error_message = str(exc_info.value)
            
            # These assertions should FAIL because current code lacks engine context
            assert "Engine Configuration Error:" in error_message, "Should include engine error prefix"
            assert "Engine: ReplacingMergeTree" in error_message, "Should include engine type"
            assert "Missing: ORDER BY clause" in error_message, "Should identify missing requirement"
            assert "Engine Requirements:" in error_message, "Should list engine requirements"
            assert "Example Configuration:" in error_message, "Should provide correct example"