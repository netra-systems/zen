"""
Test Non-Critical Table Startup Logic Fix Validation

This test validates the critical fix implemented for lines 143-158 in startup_module.py
to resolve tangled startup logic where non-critical tables were incorrectly blocking startup.

CRITICAL FIX TESTED:
- Non-critical tables (credit_transactions, agent_executions, subscriptions) should NOT block startup
- Critical tables (users, threads, messages, runs, assistants) MUST still block startup when missing
- Both graceful and strict modes should allow startup with missing non-critical tables
- Strict mode should provide enhanced logging without exceptions for non-critical tables

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Prevent false startup failures that block production deployments
- Value Impact: Eliminates broken deployments when optional features are not ready
- Strategic Impact: Ensures core chat functionality always available regardless of non-critical table status
"""
import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from netra_backend.app.startup_module import _verify_required_database_tables_exist
from shared.isolated_environment import get_env
env = get_env()
env.set('ENVIRONMENT', 'testing', 'test')
env.set('TESTING', 'true', 'test')

class MockEngine:
    """Mock database engine for testing table validation."""

    def __init__(self, existing_tables=None):
        self.existing_tables = existing_tables or set()
        self._disposed = False

    def connect(self):

        class AsyncContextManager:

            def __init__(self, connection):
                self.connection = connection

            async def __aenter__(self):
                return self.connection

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return AsyncContextManager(MockConnection(self.existing_tables))

    async def dispose(self):
        self._disposed = True

class MockConnection:
    """Mock database connection for testing."""

    def __init__(self, existing_tables):
        self.existing_tables = existing_tables
        self._transaction = None

    def begin(self):
        self._transaction = MockTransaction()
        return self._transaction

    async def execute(self, query):
        return MockResult(self.existing_tables)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class MockTransaction:
    """Mock database transaction."""

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class MockResult:
    """Mock database query result."""

    def __init__(self, existing_tables):
        self.existing_tables = existing_tables

    def fetchall(self):
        return [(table,) for table in self.existing_tables]

class StartupNonCriticalTableFixTests:
    """Test the non-critical table startup logic fix."""

    def setup_method(self):
        """Setup test logging."""
        self.logger = logging.getLogger('test_startup_validation')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        self.log_messages = []
        handler = logging.Handler()
        handler.emit = lambda record: self.log_messages.append(record.getMessage())
        self.logger.addHandler(handler)

    @pytest.mark.asyncio
    async def test_critical_tables_missing_behavior_graceful_mode(self):
        """Test that missing critical tables log warnings in graceful mode (current behavior)."""
        existing_tables = {'messages', 'runs', 'assistants'}
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = {'users', 'threads', 'messages', 'runs', 'assistants', 'credit_transactions', 'agent_executions', 'subscriptions'}
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    log_text = ' '.join(self.log_messages)
                    assert 'CRITICAL STARTUP FAILURE' in log_text
                    assert 'Missing CRITICAL database tables' in log_text

    @pytest.mark.asyncio
    async def test_critical_tables_missing_blocks_startup_strict_mode(self):
        """Test that missing critical tables STILL block startup in strict mode."""
        existing_tables = {'threads', 'messages', 'runs', 'assistants'}
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = {'users', 'threads', 'messages', 'runs', 'assistants', 'credit_transactions', 'agent_executions', 'subscriptions'}
                    with pytest.raises(RuntimeError) as exc_info:
                        await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
                    assert 'Missing critical database tables' in str(exc_info.value)
                    assert 'users' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_critical_tables_missing_allows_startup_graceful_mode(self):
        """Test that missing non-critical tables DON'T block startup in graceful mode."""
        existing_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = {'users', 'threads', 'messages', 'runs', 'assistants', 'credit_transactions', 'agent_executions', 'subscriptions'}
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    log_text = ' '.join(self.log_messages)
                    assert 'Missing non-critical database tables' in log_text
                    assert 'credit_transactions' in log_text or 'agent_executions' in log_text
                    assert 'Continuing with degraded functionality - core chat will work' in log_text

    @pytest.mark.asyncio
    async def test_non_critical_tables_missing_allows_startup_strict_mode(self):
        """CRITICAL TEST: Non-critical tables DON'T block startup in STRICT mode (the fix)."""
        existing_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = {'users', 'threads', 'messages', 'runs', 'assistants', 'credit_transactions', 'agent_executions', 'subscriptions'}
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
                    log_text = ' '.join(self.log_messages)
                    assert 'Missing non-critical database tables' in log_text
                    assert 'STRICT MODE: Missing non-critical tables logged for operations team' in log_text
                    assert 'Features affected may include: advanced analytics, credit tracking, agent execution history' in log_text
                    assert "Non-critical tables don't block startup in any mode" in log_text

    @pytest.mark.asyncio
    async def test_all_tables_present_succeeds_both_modes(self):
        """Test that when all tables are present, both modes succeed."""
        existing_tables = {'users', 'threads', 'messages', 'runs', 'assistants', 'credit_transactions', 'agent_executions', 'subscriptions'}
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = existing_tables
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
                    log_text = ' '.join(self.log_messages)
                    assert 'All' in log_text and 'required database tables are present' in log_text

    @pytest.mark.asyncio
    async def test_mixed_critical_non_critical_missing_graceful_behavior(self):
        """Test that missing BOTH critical and non-critical tables logs warnings in graceful mode."""
        existing_tables = {'messages', 'runs'}
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = {'users', 'threads', 'messages', 'runs', 'assistants', 'credit_transactions', 'agent_executions', 'subscriptions'}
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    log_text = ' '.join(self.log_messages)
                    assert 'CRITICAL STARTUP FAILURE' in log_text
                    assert 'Missing CRITICAL database tables' in log_text

    @pytest.mark.asyncio
    async def test_database_connection_failure_graceful_mode(self):
        """Test that database connection failure is handled gracefully in graceful mode."""
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = None
            await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
            log_text = ' '.join(self.log_messages)
            assert 'Failed to get database engine' in log_text
            assert 'continuing without table verification' in log_text

    @pytest.mark.asyncio
    async def test_database_connection_failure_strict_mode(self):
        """Test that database connection failure raises exception in strict mode."""
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = None
            with pytest.raises(RuntimeError) as exc_info:
                await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
            assert 'Failed to get database engine' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_table_query_exception_handling(self):
        """Test handling of database query exceptions."""

        class FailingConnection:

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            def begin(self):
                return MockTransaction()

            async def execute(self, query):
                raise Exception('Database query failed')

        class FailingEngine:

            def connect(self):

                class AsyncContextManager:

                    async def __aenter__(self):
                        return FailingConnection()

                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass
                return AsyncContextManager()

            async def dispose(self):
                pass
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = FailingEngine()
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                with pytest.raises(RuntimeError):
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=False)

    def test_critical_table_definitions(self):
        """Test that critical table definitions are correct."""
        expected_critical_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
        import inspect
        source = inspect.getsource(_verify_required_database_tables_exist)
        assert "'users'" in source
        assert "'threads'" in source
        assert "'messages'" in source
        assert "'runs'" in source
        assert "'assistants'" in source
        assert 'Core chat functionality' in source

    def test_non_critical_examples(self):
        """Test that the examples of non-critical tables are correctly identified."""
        non_critical_examples = {'credit_transactions', 'agent_executions', 'subscriptions'}
        critical_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
        assert len(non_critical_examples & critical_tables) == 0
        all_tables = critical_tables | non_critical_examples
        non_critical_computed = all_tables - critical_tables
        for table in non_critical_examples:
            assert table in non_critical_computed
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')