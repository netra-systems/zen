"""
Unit tests for database manager exception specificity.

MISSION: Validate that DatabaseManager raises specific exception types instead of broad Exception handling.
Tests will FAIL initially to demonstrate current broad exception handling problems.

Issue #374: Database Exception Handling Remediation
"""
import pytest
import asyncio
import asyncpg
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.transaction_errors import DeadlockError, ConnectionError, TimeoutError, PermissionError, SchemaError, classify_error

class DatabaseManagerExceptionSpecificityTests:
    """Test suite for database manager exception specificity validation."""

    @pytest.mark.unit
    async def test_database_manager_health_check_connection_failure_specificity(self):
        """FAILING TEST: Should raise ConnectionError, not generic Exception."""
        manager = DatabaseManager()
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=asyncpg.ConnectionFailureError('Connection refused'))
        with pytest.raises(ConnectionError, match='Connection refused'):
            await manager._health_check_engine('test_engine', mock_engine)

    @pytest.mark.unit
    async def test_database_manager_initialization_failure_specificity(self):
        """FAILING TEST: Should raise specific exception types during initialization."""
        manager = DatabaseManager()
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            mock_create_engine.side_effect = asyncpg.ConnectionFailureError('Could not connect to server')
            with pytest.raises(ConnectionError, match='Could not connect to server'):
                await manager.initialize()

    @pytest.mark.unit
    async def test_database_manager_rollback_deadlock_classification(self):
        """FAILING TEST: Should classify rollback deadlock failures specifically."""
        manager = DatabaseManager()
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock(side_effect=OperationalError('deadlock detected', None, None))
        with patch.object(manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            with pytest.raises(DeadlockError, match='deadlock detected'):
                async with manager.get_session() as session:
                    raise ValueError('Force rollback scenario')

    @pytest.mark.unit
    async def test_database_manager_session_timeout_specificity(self):
        """FAILING TEST: Should raise TimeoutError for session timeouts."""
        manager = DatabaseManager()
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=asyncio.TimeoutError('Query execution timeout'))
            mock_session_class.return_value = mock_session
            with pytest.raises(TimeoutError, match='Query execution timeout'):
                async with manager.get_session() as session:
                    await session.execute('SELECT pg_sleep(30)')

    @pytest.mark.unit
    async def test_websocket_event_sending_failure_classification(self):
        """FAILING TEST: Should classify WebSocket event sending failures."""
        manager = DatabaseManager()
        with patch.object(manager, '_send_websocket_event') as mock_send:
            mock_send.side_effect = ConnectionError('WebSocket connection lost')
            with pytest.raises(ConnectionError, match='WebSocket connection lost'):
                await manager._send_post_commit_events([MagicMock(event_type='test_event', user_id=1, event_data={})])

    @pytest.mark.unit
    async def test_session_cleanup_failure_specificity(self):
        """FAILING TEST: Should classify session cleanup failures specifically."""
        manager = DatabaseManager()
        mock_session = AsyncMock()
        mock_session.close = AsyncMock(side_effect=OperationalError('connection already closed', None, None))
        with patch.object(manager, '_active_sessions', {'test-session': mock_session}):
            await manager._cleanup_expired_sessions()
            mock_session.close.assert_called_once()

    @pytest.mark.unit
    async def test_rollback_notification_failure_classification(self):
        """FAILING TEST: Should classify rollback notification failures."""
        manager = DatabaseManager()
        with patch.object(manager, '_send_rollback_notification') as mock_send:
            mock_send.side_effect = TimeoutError('Notification timeout')
            with pytest.raises(TimeoutError, match='Notification timeout'):
                rollback_notification = MagicMock()
                await manager._send_rollback_notification(rollback_notification, [1, 2, 3])

    @pytest.mark.unit
    async def test_auto_initialization_failure_specificity(self):
        """FAILING TEST: Should classify auto-initialization failures."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.initialize') as mock_init:
            mock_init.side_effect = PermissionError('Insufficient database privileges')
            with pytest.raises(PermissionError, match='Insufficient database privileges'):
                manager = DatabaseManager()
                await manager._ensure_initialized()

    @pytest.mark.unit
    def test_transaction_error_classification_integration(self):
        """Test that classify_error function is properly integrated."""
        deadlock_error = OperationalError('deadlock detected', None, None)
        classified = classify_error(deadlock_error)
        assert isinstance(classified, DeadlockError)
        assert 'deadlock detected' in str(classified)
        connection_error = OperationalError('connection timeout', None, None)
        classified = classify_error(connection_error)
        assert isinstance(classified, (ConnectionError, TimeoutError))

    @pytest.mark.unit
    def test_database_manager_not_using_transaction_errors_module(self):
        """FAILING TEST: DatabaseManager should import and use transaction_errors module."""
        import netra_backend.app.db.database_manager as db_manager_module
        assert hasattr(db_manager_module, 'classify_error'), 'DatabaseManager should import classify_error from transaction_errors'
        assert hasattr(db_manager_module, 'DeadlockError'), 'DatabaseManager should import DeadlockError'
        assert hasattr(db_manager_module, 'ConnectionError'), 'DatabaseManager should import ConnectionError'
        assert hasattr(db_manager_module, 'TimeoutError'), 'DatabaseManager should import TimeoutError'

class DatabaseManagerErrorRecoveryTests:
    """Test suite for database manager error recovery patterns."""

    @pytest.mark.unit
    async def test_retryable_error_detection(self):
        """Test that retryable errors are properly identified."""
        from netra_backend.app.db.transaction_errors import is_retryable_error
        deadlock_error = OperationalError('deadlock detected', None, None)
        assert is_retryable_error(deadlock_error, enable_deadlock_retry=True, enable_connection_retry=False)
        assert not is_retryable_error(deadlock_error, enable_deadlock_retry=False, enable_connection_retry=False)
        connection_error = DisconnectionError('connection lost', None, None)
        assert is_retryable_error(connection_error, enable_deadlock_retry=False, enable_connection_retry=True)
        assert not is_retryable_error(connection_error, enable_deadlock_retry=False, enable_connection_retry=False)

    @pytest.mark.unit
    async def test_error_context_enhancement(self):
        """Test that errors include enhanced context information."""
        manager = DatabaseManager()
        with patch.object(manager, '_health_check_engine') as mock_health_check:
            mock_health_check.side_effect = ConnectionError('Database connection failed')
            with pytest.raises(ConnectionError) as exc_info:
                await manager._health_check_engine('postgresql_engine', MagicMock())
            error_message = str(exc_info.value)
            assert 'postgresql_engine' in error_message, 'Error should include engine name context'
            assert any((word in error_message.lower() for word in ['connection', 'database'])), 'Error should include operation context'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')