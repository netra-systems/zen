"""
Unit tests for database initializer exception specificity.

MISSION: Validate that DatabaseInitializer raises specific exception types instead of broad Exception handling.
Tests will FAIL initially to demonstrate current broad exception handling problems.

Issue #374: Database Exception Handling Remediation
"""
import pytest
import asyncio
import asyncpg
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError, ProgrammingError
from netra_backend.app.db.database_initializer import DatabaseInitializer
from netra_backend.app.db.transaction_errors import DeadlockError, ConnectionError, TimeoutError, PermissionError, SchemaError, classify_error

class TestDatabaseInitializerExceptionSpecificity:
    """Test suite for database initializer exception specificity validation."""

    @pytest.mark.unit
    async def test_database_creation_connection_failure_specificity(self):
        """FAILING TEST: Should raise ConnectionError for database creation failures."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncpg.ConnectionFailureError('Connection to database failed')
            with pytest.raises(ConnectionError, match='Connection to database failed'):
                result = initializer._create_postgresql_database('test_db')
                assert result is False

    @pytest.mark.unit
    async def test_schema_initialization_failure_specificity(self):
        """FAILING TEST: Should raise SchemaError for schema initialization failures."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_connection.execute.side_effect = asyncpg.PostgresError("relation 'test_table' does not exist")
            mock_connect.return_value.__aenter__.return_value = mock_connection
            with pytest.raises(SchemaError, match='relation.*does not exist'):
                await initializer._initialize_postgresql_schema()

    @pytest.mark.unit
    async def test_permission_denied_during_initialization_specificity(self):
        """FAILING TEST: Should raise PermissionError for permission issues."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncpg.InsufficientPrivilegeError('permission denied for database')
            with pytest.raises(PermissionError, match='permission denied'):
                result = initializer._create_postgresql_database('test_db')

    @pytest.mark.unit
    async def test_database_already_exists_error_specificity(self):
        """FAILING TEST: Should handle 'database already exists' as specific case."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_connection.execute.side_effect = asyncpg.PostgresError('database "test_db" already exists')
            mock_connect.return_value.__aenter__.return_value = mock_connection
            result = initializer._create_postgresql_database('test_db')
            assert result is True, "Should handle 'already exists' gracefully"

    @pytest.mark.unit
    async def test_connection_timeout_during_initialization_specificity(self):
        """FAILING TEST: Should raise TimeoutError for connection timeouts."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncpg.TooManyConnectionsError('Connection timeout')
            with pytest.raises(TimeoutError, match='Connection timeout'):
                result = initializer._create_postgresql_database('test_db')

    @pytest.mark.unit
    async def test_circuit_breaker_functionality_with_specific_errors(self):
        """Test that circuit breaker trips on specific error types."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncpg.ConnectionError('Database server down')
            with pytest.raises(ConnectionError):
                await initializer._initialize_postgresql_schema()
            with pytest.raises(Exception) as exc_info:
                await initializer._initialize_postgresql_schema()
            error_message = str(exc_info.value)
            assert 'circuit' in error_message.lower() or 'breaker' in error_message.lower()

    @pytest.mark.unit
    def test_database_initializer_not_importing_transaction_errors(self):
        """FAILING TEST: DatabaseInitializer should import and use transaction_errors."""
        import netra_backend.app.db.database_initializer as db_init_module
        assert hasattr(db_init_module, 'classify_error'), 'DatabaseInitializer should import classify_error from transaction_errors'
        assert hasattr(db_init_module, 'ConnectionError'), 'DatabaseInitializer should import ConnectionError'
        assert hasattr(db_init_module, 'SchemaError'), 'DatabaseInitializer should import SchemaError'
        assert hasattr(db_init_module, 'PermissionError'), 'DatabaseInitializer should import PermissionError'
        assert hasattr(db_init_module, 'TimeoutError'), 'DatabaseInitializer should import TimeoutError'

class TestDatabaseInitializerErrorClassification:
    """Test suite for database initializer error classification patterns."""

    @pytest.mark.unit
    def test_postgresql_error_classification(self):
        """Test that PostgreSQL errors are properly classified."""
        permission_error = asyncpg.PostgresError('permission denied for database test_db')
        classified = classify_error(permission_error)
        assert isinstance(classified, PermissionError), 'Permission denied should be classified as PermissionError'
        schema_error = asyncpg.PostgresError("relation 'test_table' does not exist")
        classified = classify_error(schema_error)
        assert isinstance(classified, SchemaError), 'Relation not found should be classified as SchemaError'
        connection_error = asyncpg.ConnectionError('connection to server failed')
        classified = classify_error(connection_error)
        assert isinstance(classified, ConnectionError), 'Connection failure should be classified as ConnectionError'

    @pytest.mark.unit
    async def test_error_recovery_strategies(self):
        """Test that initializer has appropriate recovery strategies for different errors."""
        initializer = DatabaseInitializer()
        with patch.object(initializer, '_trip_circuit_breaker') as mock_trip_breaker:
            with patch('asyncpg.connect') as mock_connect:
                mock_connect.side_effect = asyncpg.ConnectionError('Server down')
                result = initializer._create_postgresql_database('test_db')
                assert mock_trip_breaker.called, 'Circuit breaker should be tripped for ConnectionError'

    @pytest.mark.unit
    async def test_initialization_error_context_enhancement(self):
        """FAILING TEST: Initialization errors should include enhanced context."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncpg.PostgresError("database 'test_db' does not exist")
            with pytest.raises(SchemaError) as exc_info:
                result = initializer._create_postgresql_database('test_db')
            error_message = str(exc_info.value)
            assert 'test_db' in error_message, 'Error should include database name context'
            assert any((word in error_message.lower() for word in ['initialization', 'setup', 'create'])), 'Error should include operation context'

class TestDatabaseInitializerIntegrationPatterns:
    """Test suite for database initializer integration and dependency patterns."""

    @pytest.mark.unit
    async def test_multiple_database_type_error_handling(self):
        """Test error handling across different database types (PostgreSQL, ClickHouse)."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_pg_connect:
            mock_pg_connect.side_effect = asyncpg.PostgresError('PostgreSQL-specific error')
            with pytest.raises((SchemaError, ConnectionError, PermissionError)):
                await initializer._initialize_postgresql_schema()
        if hasattr(initializer, '_initialize_clickhouse_schema'):
            with patch('clickhouse_driver.Client') as mock_ch_client:
                mock_ch_client.side_effect = Exception('ClickHouse connection failed')
                with pytest.raises((ConnectionError, SchemaError)):
                    await initializer._initialize_clickhouse_schema()

    @pytest.mark.unit
    async def test_migration_error_specificity(self):
        """Test that database migration errors are classified specifically."""
        initializer = DatabaseInitializer()
        with patch('asyncpg.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_connection.execute.side_effect = asyncpg.PostgresError("column 'new_column' already exists")
            mock_connect.return_value.__aenter__.return_value = mock_connection
            with pytest.raises((SchemaError, Exception)) as exc_info:
                await initializer._initialize_postgresql_schema()
            error_message = str(exc_info.value)
            assert 'column' in error_message.lower() or 'already exists' in error_message.lower()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')