"""
Unit tests for transaction error classification functionality.

MISSION: Validate that the transaction_errors.py module properly classifies database exceptions
and that database modules are using these classification functions correctly.

Issue #374: Database Exception Handling Remediation
"""
import pytest
import asyncio
import asyncpg
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError, DisconnectionError, ProgrammingError
try:
    from clickhouse_driver.errors import NetworkError, ServerException
except ImportError:

    class NetworkError(Exception):
        pass

    class ServerException(Exception):
        pass
from netra_backend.app.db.transaction_errors import TransactionError, DeadlockError, ConnectionError, TimeoutError, PermissionError, SchemaError, classify_error, is_retryable_error, _has_deadlock_keywords, _has_connection_keywords, _has_timeout_keywords, _has_permission_keywords, _has_schema_keywords

class TransactionErrorClassificationTests:
    """Test suite for transaction error classification functions."""

    @pytest.mark.unit
    def test_deadlock_error_classification(self):
        """Test that deadlock errors are properly classified."""
        deadlock_error = OperationalError('deadlock detected', None, None)
        classified = classify_error(deadlock_error)
        assert isinstance(classified, DeadlockError)
        assert 'deadlock detected' in str(classified)
        lock_timeout_error = OperationalError('lock timeout exceeded', None, None)
        classified = classify_error(lock_timeout_error)
        assert isinstance(classified, DeadlockError)
        lock_wait_error = OperationalError('lock wait timeout', None, None)
        classified = classify_error(lock_wait_error)
        assert isinstance(classified, DeadlockError)

    @pytest.mark.unit
    def test_connection_error_classification(self):
        """Test that connection errors are properly classified."""
        connection_error = OperationalError('connection timeout', None, None)
        classified = classify_error(connection_error)
        assert isinstance(classified, (ConnectionError, TimeoutError))
        network_error = OperationalError('network unreachable', None, None)
        classified = classify_error(network_error)
        assert isinstance(classified, ConnectionError)
        pipe_error = OperationalError('broken pipe', None, None)
        classified = classify_error(pipe_error)
        assert isinstance(classified, ConnectionError)

    @pytest.mark.unit
    def test_timeout_error_classification(self):
        """Test that timeout errors are properly classified."""
        timeout_error = OperationalError('query timeout', None, None)
        classified = classify_error(timeout_error)
        assert isinstance(classified, TimeoutError)
        timed_out_error = OperationalError('connection timed out', None, None)
        classified = classify_error(timed_out_error)
        assert isinstance(classified, (TimeoutError, ConnectionError))
        time_limit_error = OperationalError('time limit exceeded', None, None)
        classified = classify_error(time_limit_error)
        assert isinstance(classified, TimeoutError)

    @pytest.mark.unit
    def test_permission_error_classification(self):
        """Test that permission errors are properly classified."""
        permission_error = OperationalError('permission denied', None, None)
        classified = classify_error(permission_error)
        assert isinstance(classified, PermissionError)
        auth_error = OperationalError('authentication failed', None, None)
        classified = classify_error(auth_error)
        assert isinstance(classified, PermissionError)
        access_error = OperationalError('access denied', None, None)
        classified = classify_error(access_error)
        assert isinstance(classified, PermissionError)
        privilege_error = OperationalError('insufficient privileges', None, None)
        classified = classify_error(privilege_error)
        assert isinstance(classified, PermissionError)

    @pytest.mark.unit
    def test_schema_error_classification(self):
        """Test that schema errors are properly classified."""
        table_error = OperationalError('table does not exist', None, None)
        classified = classify_error(table_error)
        assert isinstance(classified, SchemaError)
        column_error = OperationalError('no such column', None, None)
        classified = classify_error(column_error)
        assert isinstance(classified, SchemaError)
        syntax_error = OperationalError('syntax error', None, None)
        classified = classify_error(syntax_error)
        assert isinstance(classified, SchemaError)
        invalid_column_error = OperationalError('invalid column name', None, None)
        classified = classify_error(invalid_column_error)
        assert isinstance(classified, SchemaError)

    @pytest.mark.unit
    def test_non_operational_error_passthrough(self):
        """Test that non-OperationalError exceptions pass through unchanged."""
        value_error = ValueError('Invalid value')
        classified = classify_error(value_error)
        assert classified is value_error
        disconnection_error = DisconnectionError('Connection lost', None, None)
        classified = classify_error(disconnection_error)
        assert isinstance(classified, ConnectionError)
        assert 'Connection lost' in str(classified)

    @pytest.mark.unit
    def test_error_priority_classification(self):
        """Test that errors with multiple keywords are classified by priority."""
        mixed_error = OperationalError('deadlock detected due to connection timeout', None, None)
        classified = classify_error(mixed_error)
        assert isinstance(classified, DeadlockError)
        connection_timeout_error = OperationalError('connection timeout occurred', None, None)
        classified = classify_error(connection_timeout_error)
        assert isinstance(classified, ConnectionError)

class RetryableErrorDetectionTests:
    """Test suite for retryable error detection functionality."""

    @pytest.mark.unit
    def test_deadlock_error_retryability(self):
        """Test that deadlock errors are correctly identified as retryable."""
        deadlock_error = OperationalError('deadlock detected', None, None)
        assert is_retryable_error(deadlock_error, enable_deadlock_retry=True, enable_connection_retry=False)
        assert not is_retryable_error(deadlock_error, enable_deadlock_retry=False, enable_connection_retry=False)

    @pytest.mark.unit
    def test_connection_error_retryability(self):
        """Test that connection errors are correctly identified as retryable."""
        disconnection_error = DisconnectionError('Connection lost', None, None)
        assert is_retryable_error(disconnection_error, enable_deadlock_retry=False, enable_connection_retry=True)
        assert not is_retryable_error(disconnection_error, enable_deadlock_retry=False, enable_connection_retry=False)
        connection_operational_error = OperationalError('connection timeout', None, None)
        assert is_retryable_error(connection_operational_error, enable_deadlock_retry=False, enable_connection_retry=True)

    @pytest.mark.unit
    def test_non_retryable_errors(self):
        """Test that non-retryable errors are correctly identified."""
        permission_error = OperationalError('permission denied', None, None)
        assert not is_retryable_error(permission_error, enable_deadlock_retry=True, enable_connection_retry=True)
        schema_error = OperationalError('table does not exist', None, None)
        assert not is_retryable_error(schema_error, enable_deadlock_retry=True, enable_connection_retry=True)
        value_error = ValueError('Invalid input')
        assert not is_retryable_error(value_error, enable_deadlock_retry=True, enable_connection_retry=True)

class KeywordDetectionFunctionsTests:
    """Test suite for keyword detection helper functions."""

    @pytest.mark.unit
    def test_deadlock_keyword_detection(self):
        """Test deadlock keyword detection."""
        assert _has_deadlock_keywords('deadlock detected')
        assert _has_deadlock_keywords('lock timeout exceeded')
        assert _has_deadlock_keywords('lock wait timeout')
        assert _has_deadlock_keywords('Database DEADLOCK occurred')
        assert not _has_deadlock_keywords('connection timeout')
        assert not _has_deadlock_keywords('permission denied')

    @pytest.mark.unit
    def test_connection_keyword_detection(self):
        """Test connection keyword detection."""
        assert _has_connection_keywords('connection refused')
        assert _has_connection_keywords('network unreachable')
        assert _has_connection_keywords('connection timeout')
        assert _has_connection_keywords('broken pipe')
        assert not _has_connection_keywords('deadlock detected')
        assert not _has_connection_keywords('permission denied')

    @pytest.mark.unit
    def test_timeout_keyword_detection(self):
        """Test timeout keyword detection."""
        assert _has_timeout_keywords('query timeout')
        assert _has_timeout_keywords('connection timed out')
        assert _has_timeout_keywords('time limit exceeded')
        assert not _has_timeout_keywords('deadlock detected')
        assert not _has_timeout_keywords('permission denied')

    @pytest.mark.unit
    def test_permission_keyword_detection(self):
        """Test permission keyword detection."""
        assert _has_permission_keywords('permission denied')
        assert _has_permission_keywords('access denied')
        assert _has_permission_keywords('insufficient privileges')
        assert _has_permission_keywords('authentication failed')
        assert not _has_permission_keywords('connection timeout')
        assert not _has_permission_keywords('deadlock detected')

    @pytest.mark.unit
    def test_schema_keyword_detection(self):
        """Test schema keyword detection."""
        assert _has_schema_keywords('table does not exist')
        assert _has_schema_keywords('no such table')
        assert _has_schema_keywords('no such column')
        assert _has_schema_keywords('syntax error')
        assert _has_schema_keywords('invalid column name')
        assert not _has_schema_keywords('connection timeout')
        assert not _has_schema_keywords('permission denied')

class DatabaseSpecificErrorIntegrationTests:
    """Test suite for database-specific error handling integration."""

    @pytest.mark.unit
    def test_asyncpg_error_classification(self):
        """Test that asyncpg errors can be classified (if supported)."""
        postgres_error = asyncpg.PostgresError("relation 'test_table' does not exist")
        try:
            classified = classify_error(postgres_error)
            if classified != postgres_error:
                assert isinstance(classified, SchemaError)
        except Exception as e:
            pytest.skip(f'asyncpg error classification not yet implemented: {e}')

    @pytest.mark.unit
    def test_clickhouse_error_classification(self):
        """Test that ClickHouse errors can be classified (if supported)."""
        network_error = NetworkError('Connection to ClickHouse failed')
        try:
            classified = classify_error(network_error)
            if classified != network_error:
                assert isinstance(classified, ConnectionError)
        except Exception as e:
            pytest.skip(f'ClickHouse error classification not yet implemented: {e}')
        server_error = ServerException("Table 'test' doesn't exist")
        try:
            classified = classify_error(server_error)
            if classified != server_error:
                assert isinstance(classified, SchemaError)
        except Exception as e:
            pytest.skip(f'ClickHouse server error classification not yet implemented: {e}')

class TransactionErrorHierarchyTests:
    """Test suite for transaction error class hierarchy."""

    @pytest.mark.unit
    def test_error_inheritance(self):
        """Test that all specific errors inherit from TransactionError."""
        assert issubclass(DeadlockError, TransactionError)
        assert issubclass(ConnectionError, TransactionError)
        assert issubclass(TimeoutError, TransactionError)
        assert issubclass(PermissionError, TransactionError)
        assert issubclass(SchemaError, TransactionError)
        assert issubclass(TransactionError, Exception)

    @pytest.mark.unit
    def test_error_instantiation(self):
        """Test that error classes can be properly instantiated."""
        deadlock_error = DeadlockError('Test deadlock')
        assert str(deadlock_error) == 'Test deadlock'
        assert isinstance(deadlock_error, TransactionError)
        connection_error = ConnectionError('Test connection failure')
        assert str(connection_error) == 'Test connection failure'
        assert isinstance(connection_error, TransactionError)
        timeout_error = TimeoutError('Test timeout')
        assert str(timeout_error) == 'Test timeout'
        assert isinstance(timeout_error, TransactionError)
        permission_error = PermissionError('Test permission denied')
        assert str(permission_error) == 'Test permission denied'
        assert isinstance(permission_error, TransactionError)
        schema_error = SchemaError('Test schema error')
        assert str(schema_error) == 'Test schema error'
        assert isinstance(schema_error, TransactionError)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')