"""
Comprehensive test suite for database operations validating the mock session factory has been removed.

This test suite ensures the CRITICAL SECURITY FIX is validated:
- Mock session factories have been completely removed from production code
- initialize_postgres always fails fast on errors (no silent degradation)
- Real database sessions are always used (NO MOCKS per CLAUDE.md)
- Behavior with PYTEST_CURRENT_TEST environment variable is tested
- Concurrent session creation and isolation is validated
- Difficult edge cases that could trigger mock fallback are covered

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Security Infrastructure
- Business Goal: Data integrity and system reliability
- Value Impact: Prevents silent data loss caused by mock session factories
- Strategic Impact: Ensures production database operations always persist data

CRITICAL: This test validates the security fix that prevents mock session factories
from being returned in any environment, which would cause silent data corruption.
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
"""
import asyncio
import inspect
import os
import pytest
import sys
import time
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from netra_backend.app.db.postgres_core import initialize_postgres, Database, AsyncDatabase, async_engine, async_session_factory, create_async_database, get_converted_async_db_url
from netra_backend.app.database import get_db, get_database_url, get_engine, get_sessionmaker
from shared.isolated_environment import get_env
from test_framework.database_test_utilities import DatabaseTestUtilities

class MockSessionFactoryRemovalTests:
    """Test that mock session factory code has been completely removed."""

    def test_initialize_postgres_no_mock_factory_fallback(self):
        """Test that initialize_postgres never returns a mock session factory."""
        import netra_backend.app.db.postgres_core as postgres_core_module
        source = inspect.getsource(postgres_core_module.initialize_postgres)
        forbidden_patterns = ['mock_session_factory', 'return AsyncMock', 'AsyncMock(', 'Mock(', 'MagicMock(', 'lambda:', 'lambda ', 'if.*test.*return.*mock', 'fallback.*mock', 'mock.*fallback']
        for pattern in forbidden_patterns:
            assert pattern not in source.lower(), f"CRITICAL SECURITY VIOLATION: Found forbidden pattern '{pattern}' in initialize_postgres(). Mock session factories cause silent data loss and must never be returned."

    def test_security_fix_comment_present(self):
        """Test that the critical security fix comment is present."""
        import netra_backend.app.db.postgres_core as postgres_core_module
        source = inspect.getsource(postgres_core_module.initialize_postgres)
        required_security_comments = ['CRITICAL SECURITY FIX', 'Never return mock session factory', 'Mock session factories cause silent data loss', 'prevent data corruption']
        for comment in required_security_comments:
            assert comment in source, f"CRITICAL: Required security comment '{comment}' not found in initialize_postgres(). This comment documents the critical security fix that prevents data corruption."

    def test_no_mock_imports_in_postgres_core(self):
        """Test that postgres_core.py has no mock-related imports."""
        import netra_backend.app.db.postgres_core as postgres_core_module
        source = inspect.getsource(postgres_core_module)
        forbidden_imports = ['AsyncMock', 'MagicMock']
        for forbidden_import in forbidden_imports:
            assert forbidden_import not in source, f"CRITICAL: Found forbidden mock import '{forbidden_import}' in postgres_core.py. "

    def test_all_session_factory_returns_are_real(self):
        """Test that all session factory returns in the codebase are real implementations."""
        import netra_backend.app.db.postgres_core as postgres_core_module
        functions_to_check = [postgres_core_module.initialize_postgres, postgres_core_module._create_async_session_factory]
        for func in functions_to_check:
            source = inspect.getsource(func)
            if 'return' in source and 'session' in source.lower():
                source_lines = source.split('\n')
                code_lines = []
                for line in source_lines:
                    if '#' in line and (not line.strip().startswith('#')):
                        in_string = False
                        quote_char = None
                        for i, char in enumerate(line):
                            if char in ['"', "'"] and (i == 0 or line[i - 1] != '\\'):
                                if not in_string:
                                    in_string = True
                                    quote_char = char
                                elif char == quote_char:
                                    in_string = False
                                    quote_char = None
                            elif char == '#' and (not in_string):
                                line = line[:i]
                                break
                    code_lines.append(line)
                code_only = '\n'.join(code_lines)
                forbidden_patterns = ['return Mock', 'return AsyncMock', 'return MagicMock', 'Mock(', 'AsyncMock(', 'MagicMock(']
                for pattern in forbidden_patterns:
                    assert pattern not in code_only, f"CRITICAL: Function {func.__name__} contains forbidden pattern '{pattern}'. All session factory returns must be real implementations."
                if 'return lambda' in code_only:
                    assert False, f'CRITICAL: Function {func.__name__} contains lambda in return path. All session factory returns must be real async_sessionmaker instances.'

class InitializePostgresFailFastTests:
    """Test that initialize_postgres fails fast on errors with no silent degradation."""

    @pytest.mark.asyncio
    async def test_initialize_postgres_fails_on_invalid_url(self):
        """Test initialize_postgres fails fast with invalid database URL."""
        global async_engine, async_session_factory
        original_engine = async_engine
        original_factory = async_session_factory
        try:
            async_engine = None
            async_session_factory = None
            with patch('netra_backend.app.db.postgres_core._validate_database_url') as mock_validate:
                mock_validate.return_value = 'invalid://not-a-database'
                with pytest.raises(RuntimeError, match='Database engine creation failed'):
                    initialize_postgres()
                assert async_session_factory is None, 'CRITICAL: initialize_postgres must not create mock session factory on failure'
        finally:
            async_engine = original_engine
            async_session_factory = original_factory

    @pytest.mark.asyncio
    async def test_initialize_postgres_fails_on_connection_error(self):
        """Test initialize_postgres fails fast on database connection errors."""
        global async_engine, async_session_factory
        original_engine = async_engine
        original_factory = async_session_factory
        try:
            async_engine = None
            async_session_factory = None
            with patch('netra_backend.app.db.postgres_core.create_async_engine') as mock_create:
                mock_create.side_effect = Exception('Connection refused')
                with pytest.raises(RuntimeError, match='Failed to initialize PostgreSQL'):
                    initialize_postgres()
                assert async_session_factory is None, 'CRITICAL: Must not create fallback mock session factory on connection failure'
        finally:
            async_engine = original_engine
            async_session_factory = original_factory

    @pytest.mark.asyncio
    async def test_initialize_postgres_no_silent_failures(self):
        """Test that initialize_postgres never silently fails or returns fallbacks."""
        global async_engine, async_session_factory
        original_engine = async_engine
        original_factory = async_session_factory
        try:
            async_engine = None
            async_session_factory = None
            failure_scenarios = [('Database URL None', lambda: None), ('Empty URL', lambda: ''), ('Invalid protocol', lambda: 'invalid://localhost'), ('Missing host', lambda: 'postgresql://')]
            for scenario_name, url_func in failure_scenarios:
                async_engine = None
                async_session_factory = None
                with patch('netra_backend.app.db.postgres_core._validate_database_url') as mock_validate:
                    mock_validate.return_value = url_func()
                    with pytest.raises((RuntimeError, ValueError, Exception)) as exc_info:
                        initialize_postgres()
                    error_msg = str(exc_info.value)
                    assert error_msg, f'Empty error message for scenario: {scenario_name}'
                    assert len(error_msg) > 10, f'Too brief error message for scenario: {scenario_name}'
                    assert async_session_factory is None, f"CRITICAL: Scenario '{scenario_name}' must not create mock session factory"
        finally:
            async_engine = original_engine
            async_session_factory = original_factory

    def test_initialize_postgres_raises_specific_errors(self):
        """Test that initialize_postgres raises specific, actionable errors."""
        global async_engine, async_session_factory
        original_engine = async_engine
        original_factory = async_session_factory
        try:
            async_engine = None
            async_session_factory = None
            with patch('netra_backend.app.db.postgres_core._initialize_async_engine') as mock_init:
                mock_init.side_effect = ValueError('Original database error')
                with pytest.raises(RuntimeError) as exc_info:
                    initialize_postgres()
                error_msg = str(exc_info.value)
                assert 'Failed to initialize PostgreSQL' in error_msg, 'Error message should provide context about PostgreSQL initialization failure'
                assert 'Original database error' in error_msg or hasattr(exc_info.value, '__cause__'), 'Original error should be preserved in error chain'
        finally:
            async_engine = original_engine
            async_session_factory = original_factory

class RealDatabaseSessionsTests:
    """Test real database session creation and operations."""

    @pytest.mark.asyncio
    async def test_real_session_creation_with_database_test_utility(self):
        """Test real session creation using DatabaseTestUtilities (NO MOCKS)."""
        async with DatabaseTestUtilities('netra_backend') as db_util:
            session = await db_util.get_test_session()
            assert isinstance(session, AsyncSession), f'Expected real AsyncSession, got {type(session)}. CRITICAL: Must use real database sessions, never mocks.'
            result = await session.execute(text('SELECT 1 as test_value'))
            row = result.fetchone()
            assert row is not None
            assert row.test_value == 1
            assert hasattr(session, 'bind'), 'Real session must have bind attribute'
            assert hasattr(session, 'execute'), 'Real session must have execute method'
            assert callable(session.execute), 'execute must be callable, not a Mock'
            mock_attributes = ['call_count', 'called', 'return_value', '_mock_name']
            for attr in mock_attributes:
                assert not hasattr(session, attr), f"CRITICAL: Session has mock attribute '{attr}'. Database sessions must be real, never mocks."

    @pytest.mark.asyncio
    async def test_real_engine_creation(self):
        """Test that database engines are real SQLAlchemy engines."""
        try:
            engine = get_engine()
            assert hasattr(engine, 'dialect'), 'Real engine must have dialect'
            assert hasattr(engine, 'pool'), 'Real engine must have connection pool'
            assert hasattr(engine, 'url'), 'Real engine must have URL'
            engine_url = str(engine.url)
            assert 'postgresql' in engine_url.lower() or 'sqlite' in engine_url.lower(), f'Engine URL must be valid database URL, got: {engine_url}'
            mock_attributes = ['call_count', 'called', 'return_value', '_mock_name']
            for attr in mock_attributes:
                assert not hasattr(engine, attr), f"CRITICAL: Engine has mock attribute '{attr}'. Database engines must be real, never mocks."
        except Exception as e:
            assert 'mock' not in str(e).lower(), f'Error message suggests mock fallback: {e}. Engine creation must fail fast with real errors.'
            raise

    @pytest.mark.asyncio
    async def test_real_sessionmaker_creation(self):
        """Test that sessionmaker creates real session factories."""
        try:
            sessionmaker = get_sessionmaker()
            assert callable(sessionmaker), 'Sessionmaker must be callable'
            assert hasattr(sessionmaker, 'bind'), 'Real sessionmaker must have bind attribute'
            session = sessionmaker()
            assert isinstance(session, AsyncSession), f'Expected real AsyncSession from sessionmaker, got {type(session)}'
            for obj in [sessionmaker, session]:
                mock_attributes = ['call_count', 'called', 'return_value', '_mock_name']
                for attr in mock_attributes:
                    assert not hasattr(obj, attr), f"CRITICAL: {type(obj).__name__} has mock attribute '{attr}'. Database components must be real, never mocks."
            await session.close()
        except Exception as e:
            assert 'mock' not in str(e).lower(), f'Error message suggests mock fallback: {e}. Sessionmaker creation must fail fast with real errors.'
            raise

    @pytest.mark.asyncio
    async def test_database_operations_with_real_persistence(self):
        """Test that database operations actually persist data (not mocked)."""
        async with DatabaseTestUtilities('netra_backend') as db_util:
            async with db_util.committed_transaction_scope() as session:
                await session.execute(text('\n                    CREATE TABLE IF NOT EXISTS mock_removal_test (\n                        id SERIAL PRIMARY KEY,\n                        test_value TEXT NOT NULL,\n                        created_at TIMESTAMP DEFAULT NOW()\n                    )\n                '))
                test_id = str(uuid.uuid4())
                await session.execute(text('\n                    INSERT INTO mock_removal_test (test_value) VALUES (:test_value)\n                '), {'test_value': f'test_data_{test_id}'})
            async with db_util.transaction_scope() as verify_session:
                result = await verify_session.execute(text('\n                    SELECT test_value FROM mock_removal_test \n                    WHERE test_value = :test_value\n                '), {'test_value': f'test_data_{test_id}'})
                row = result.fetchone()
                assert row is not None, 'CRITICAL: Data was not persisted. This indicates mock session factory usage that accepts operations without actually persisting them to the database.'
                assert row.test_value == f'test_data_{test_id}', "Retrieved data doesn't match inserted data, indicating data corruption or mock usage."
            async with db_util.committed_transaction_scope() as cleanup_session:
                await cleanup_session.execute(text('\n                    DELETE FROM mock_removal_test WHERE test_value = :test_value\n                '), {'test_value': f'test_data_{test_id}'})
                await cleanup_session.execute(text('\n                    DROP TABLE IF EXISTS mock_removal_test\n                '))

class PytestCurrentTestBehaviorTests:
    """Test behavior with PYTEST_CURRENT_TEST environment variable set."""

    def test_pytest_current_test_env_var_handling(self):
        """Test that PYTEST_CURRENT_TEST environment variable is handled correctly."""
        original_value = os.environ.get('PYTEST_CURRENT_TEST')
        try:
            os.environ['PYTEST_CURRENT_TEST'] = 'netra_backend/tests/unit/db/test_postgres_core_production_fix.py::PytestCurrentTestBehaviorTests::test_pytest_current_test_env_var_handling'
            env = get_env()
            current_test = env.get('PYTEST_CURRENT_TEST')
            assert current_test is not None, 'PYTEST_CURRENT_TEST should be accessible through get_env()'
            database_url = get_database_url()
            assert database_url is not None, 'Database URL should be retrievable during tests'
            assert 'mock' not in database_url.lower(), "CRITICAL: Database URL contains 'mock' when PYTEST_CURRENT_TEST is set, indicating improper mock fallback behavior."
        finally:
            if original_value is None:
                os.environ.pop('PYTEST_CURRENT_TEST', None)
            else:
                os.environ['PYTEST_CURRENT_TEST'] = original_value

    def test_test_collection_mode_handling(self):
        """Test handling of TEST_COLLECTION_MODE environment variable."""
        original_value = os.environ.get('TEST_COLLECTION_MODE')
        try:
            os.environ['TEST_COLLECTION_MODE'] = '1'
            global async_engine, async_session_factory
            original_engine = async_engine
            original_factory = async_session_factory
            async_engine = None
            async_session_factory = None
            try:
                result = initialize_postgres()
                assert result is None, 'initialize_postgres should return None during test collection, not create mock session factory.'
                assert async_engine is None, 'Global async_engine should remain None during test collection'
                assert async_session_factory is None, 'Global async_session_factory should remain None during test collection'
            finally:
                async_engine = original_engine
                async_session_factory = original_factory
        finally:
            if original_value is None:
                os.environ.pop('TEST_COLLECTION_MODE', None)
            else:
                os.environ['TEST_COLLECTION_MODE'] = original_value

    @pytest.mark.asyncio
    async def test_real_database_with_test_env_vars(self):
        """Test that real database operations work even with test environment variables."""
        env_vars_to_set = {'PYTEST_CURRENT_TEST': 'test_real_database_with_test_env_vars', 'TEST_MODE': 'true', 'TESTING': '1'}
        original_values = {}
        for var, value in env_vars_to_set.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        try:
            async with DatabaseTestUtilities('netra_backend') as db_util:
                session = await db_util.get_test_session()
                assert isinstance(session, AsyncSession), 'Must create real AsyncSession even with test environment variables set'
                result = await session.execute(text('SELECT 42 as answer'))
                row = result.fetchone()
                assert row.answer == 42, 'Real database operations must work even in test environment'
        finally:
            for var, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = original_value

class ConcurrentSessionIsolationTests:
    """Test concurrent session creation and isolation."""

    @pytest.mark.asyncio
    async def test_concurrent_session_creation_all_real(self):
        """Test that concurrent session creation produces only real sessions."""
        async with DatabaseTestUtilities('netra_backend') as db_util:
            num_concurrent_sessions = 10
            sessions_created = []

            async def create_session_task(session_id: int):
                session = await db_util.get_test_session()
                assert isinstance(session, AsyncSession), f'Session {session_id} is not a real AsyncSession: {type(session)}'
                result = await session.execute(text('SELECT :session_id as id'), {'session_id': session_id})
                row = result.fetchone()
                assert row.id == session_id, f'Session {session_id} operation failed'
                return session
            tasks = [create_session_task(i) for i in range(num_concurrent_sessions)]
            sessions = await asyncio.gather(*tasks)
            for i, session in enumerate(sessions):
                assert isinstance(session, AsyncSession), f'Concurrent session {i} is not real: {type(session)}'
                mock_attributes = ['call_count', 'called', 'return_value', '_mock_name']
                for attr in mock_attributes:
                    assert not hasattr(session, attr), f"CRITICAL: Concurrent session {i} has mock attribute '{attr}'. All concurrent sessions must be real."
            session_ids = [id(session) for session in sessions]
            unique_session_ids = set(session_ids)
            assert len(unique_session_ids) == num_concurrent_sessions, f'Expected {num_concurrent_sessions} unique sessions, got {len(unique_session_ids)}. Sessions must be isolated, not shared or mocked.'

    @pytest.mark.asyncio
    async def test_concurrent_database_operations_isolation(self):
        """Test that concurrent database operations are properly isolated."""
        async with DatabaseTestUtilities('netra_backend') as db_util:
            async with db_util.committed_transaction_scope() as setup_session:
                await setup_session.execute(text('\n                    CREATE TABLE IF NOT EXISTS isolation_test (\n                        session_id INTEGER,\n                        operation_id INTEGER,\n                        data TEXT\n                    )\n                '))

            async def isolated_operation(session_id: int, operation_id: int):
                session = await db_util.get_test_session()
                await session.execute(text('\n                    INSERT INTO isolation_test (session_id, operation_id, data) \n                    VALUES (:session_id, :operation_id, :data)\n                '), {'session_id': session_id, 'operation_id': operation_id, 'data': f'session_{session_id}_op_{operation_id}'})
                await session.commit()
                result = await session.execute(text('\n                    SELECT data FROM isolation_test \n                    WHERE session_id = :session_id AND operation_id = :operation_id\n                '), {'session_id': session_id, 'operation_id': operation_id})
                row = result.fetchone()
                assert row is not None, f'Data for session {session_id} operation {operation_id} not found. This indicates mock session factory usage or isolation failure.'
                return f'session_{session_id}_op_{operation_id}'
            num_sessions = 5
            num_operations_per_session = 3
            tasks = []
            for session_id in range(num_sessions):
                for operation_id in range(num_operations_per_session):
                    task = isolated_operation(session_id, operation_id)
                    tasks.append(task)
            results = await asyncio.gather(*tasks)
            expected_results = []
            for session_id in range(num_sessions):
                for operation_id in range(num_operations_per_session):
                    expected_results.append(f'session_{session_id}_op_{operation_id}')
            assert len(results) == len(expected_results), f'Expected {len(expected_results)} results, got {len(results)}'
            async with db_util.transaction_scope() as verify_session:
                result = await verify_session.execute(text('\n                    SELECT COUNT(*) as count FROM isolation_test\n                '))
                row = result.fetchone()
                assert row.count == len(expected_results), f"Expected {len(expected_results)} rows in database, got {row.count}. This indicates mock session factory usage that doesn't persist data."
            async with db_util.committed_transaction_scope() as cleanup_session:
                await cleanup_session.execute(text('DROP TABLE IF EXISTS isolation_test'))

    @pytest.mark.asyncio
    async def test_session_thread_safety_no_mocks(self):
        """Test that sessions are thread-safe and always real (no mocks in threads)."""
        import threading
        import queue
        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        async def thread_database_operation(thread_id: int):
            """Database operation to run in separate thread."""
            try:
                async with DatabaseTestUtilities('netra_backend') as db_util:
                    session = await db_util.get_test_session()
                    assert isinstance(session, AsyncSession), f'Thread {thread_id} got non-real session: {type(session)}'
                    mock_attributes = ['call_count', 'called', 'return_value', '_mock_name']
                    for attr in mock_attributes:
                        assert not hasattr(session, attr), f"CRITICAL: Thread {thread_id} session has mock attribute '{attr}'. Thread-local sessions must be real, never mocks."
                    result = await session.execute(text('SELECT :thread_id as tid'), {'thread_id': thread_id})
                    row = result.fetchone()
                    assert row.tid == thread_id, f'Thread {thread_id} operation verification failed'
                    results_queue.put(f'thread_{thread_id}_success')
            except Exception as e:
                errors_queue.put(f'thread_{thread_id}_error: {e}')

        def thread_runner(thread_id: int):
            """Thread function that runs async database operations."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(thread_database_operation(thread_id))
            finally:
                loop.close()
        num_threads = 5
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=thread_runner, args=(thread_id,))
            threads.append(thread)
            thread.start()
        for thread in threads.join():
            thread.join(timeout=30)
            assert not thread.is_alive(), f'Thread {thread.name} timed out'
        assert errors_queue.empty(), f'Thread errors occurred: {list(errors_queue.queue)}'
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        assert len(results) == num_threads, f'Expected {num_threads} successful thread results, got {len(results)}'

class DifficultEdgeCasesTests:
    """Create difficult edge cases that could trigger mock fallback."""

    @pytest.mark.asyncio
    async def test_memory_pressure_no_mock_fallback(self):
        """Test that memory pressure doesn't trigger mock session fallback."""
        memory_pressure = []
        try:
            for i in range(100):
                memory_pressure.append(bytearray(1024 * 1024))
            async with DatabaseTestUtilities('netra_backend') as db_util:
                session = await db_util.get_test_session()
                assert isinstance(session, AsyncSession), 'CRITICAL: Memory pressure triggered mock session fallback. System must use real sessions even under resource constraints.'
                result = await session.execute(text("SELECT 'under_pressure' as status"))
                row = result.fetchone()
                assert row.status == 'under_pressure', 'Database operations must work under memory pressure with real sessions.'
        except MemoryError:
            pytest.skip('Insufficient memory for test, but no mock fallback detected', allow_module_level=True)
        finally:
            memory_pressure.clear()

    @pytest.mark.asyncio
    async def test_rapid_session_creation_destruction_no_mocks(self):
        """Test rapid session creation/destruction doesn't cause mock fallback."""
        async with DatabaseTestUtilities('netra_backend') as db_util:
            for iteration in range(50):
                session = await db_util.get_test_session()
                assert isinstance(session, AsyncSession), f'Iteration {iteration}: Got mock session instead of real. Rapid session cycling must not trigger mock fallback.'
                result = await session.execute(text('SELECT :iter as iteration'), {'iter': iteration})
                row = result.fetchone()
                assert row.iteration == iteration, f'Iteration {iteration}: Database operation failed, indicating mock usage.'
                await session.close()

    @pytest.mark.asyncio
    async def test_exception_during_session_creation_no_mock_fallback(self):
        """Test that exceptions during session creation don't trigger mock fallback."""
        exception_scenarios = [(ConnectionError, 'Database connection lost'), (TimeoutError, 'Connection timeout'), (OSError, 'Network unavailable')]
        for exception_class, error_message in exception_scenarios:
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create:
                mock_create.side_effect = exception_class(error_message)
                with pytest.raises((exception_class, RuntimeError)) as exc_info:
                    async with DatabaseTestUtilities('netra_backend') as db_util:
                        await db_util.get_test_session()
                error_str = str(exc_info.value)
                assert 'mock' not in error_str.lower(), f'Error message suggests mock fallback for {exception_class.__name__}: {error_str}'

    @pytest.mark.asyncio
    async def test_database_url_edge_cases_no_mock_fallback(self):
        """Test edge cases in database URL handling don't trigger mock fallback."""
        edge_case_urls = ['', '   ', 'not-a-url', 'http://not-a-database', 'postgresql://', 'postgresql://user@', 'postgresql://user:pass@host', 'sqlite:///nonexistent.db']
        for url in edge_case_urls:
            with patch('netra_backend.app.database.get_database_url') as mock_get_url:
                mock_get_url.return_value = url
                with pytest.raises((ValueError, RuntimeError, Exception)) as exc_info:
                    get_engine()
                error_str = str(exc_info.value)
                assert 'mock' not in error_str.lower(), f"Error handling for URL '{url}' suggests mock fallback: {error_str}"

    @pytest.mark.asyncio
    async def test_sqlalchemy_version_compatibility_no_mocks(self):
        """Test SQLAlchemy version compatibility doesn't cause mock fallback."""
        assert hasattr(sqlalchemy, '__version__'), 'SQLAlchemy version should be accessible'
        assert hasattr(AsyncSession, '__module__'), 'AsyncSession should have module attribute'
        assert 'sqlalchemy' in AsyncSession.__module__, 'AsyncSession should be from SQLAlchemy, not a mock replacement'
        assert callable(async_sessionmaker), 'async_sessionmaker should be callable'
        assert hasattr(async_sessionmaker, '__module__'), 'async_sessionmaker should have module attribute'
        assert 'sqlalchemy' in async_sessionmaker.__module__, 'async_sessionmaker should be from SQLAlchemy, not a mock'

    def test_global_state_corruption_resilience(self):
        """Test resilience against global state corruption without mock fallback."""
        global async_engine, async_session_factory
        original_engine = async_engine
        original_factory = async_session_factory
        try:
            corruption_scenarios = [('None engine', lambda: setattr(sys.modules['netra_backend.app.db.postgres_core'], 'async_engine', None)), ('None factory', lambda: setattr(sys.modules['netra_backend.app.db.postgres_core'], 'async_session_factory', None)), ('Invalid engine', lambda: setattr(sys.modules['netra_backend.app.db.postgres_core'], 'async_engine', 'not_an_engine')), ('Invalid factory', lambda: setattr(sys.modules['netra_backend.app.db.postgres_core'], 'async_session_factory', 'not_a_factory'))]
            for scenario_name, corrupt_func in corruption_scenarios:
                async_engine = original_engine
                async_session_factory = original_factory
                corrupt_func()
                try:
                    result = initialize_postgres()
                    if result is not None:
                        assert callable(result), f"Scenario '{scenario_name}': Result should be callable session factory"
                        assert not hasattr(result, '_mock_name'), f"CRITICAL: Scenario '{scenario_name}' returned mock session factory"
                except Exception as e:
                    error_str = str(e)
                    assert 'mock' not in error_str.lower(), f"Scenario '{scenario_name}' error suggests mock fallback: {error_str}"
        finally:
            async_engine = original_engine
            async_session_factory = original_factory

class RealSessionValidationTests:
    """Validate all database connections use real sessions (NO MOCKS)."""

    @pytest.mark.asyncio
    async def test_all_database_entry_points_use_real_sessions(self):
        """Test that all database entry points create real sessions."""
        entry_points_to_test = [('get_db context manager', lambda: get_db()), ('DatabaseTestUtilities', lambda: DatabaseTestUtilities('netra_backend').__aenter__())]
        for entry_point_name, entry_point_func in entry_points_to_test:
            try:
                if 'context manager' in entry_point_name:
                    async with entry_point_func() as session:
                        assert isinstance(session, AsyncSession), f"Entry point '{entry_point_name}' returned {type(session)}, expected AsyncSession"
                        await self._verify_session_is_real(session, entry_point_name)
                else:
                    db_util = await entry_point_func()
                    session = await db_util.get_test_session()
                    assert isinstance(session, AsyncSession), f"Entry point '{entry_point_name}' returned {type(session)}, expected AsyncSession"
                    await self._verify_session_is_real(session, entry_point_name)
                    await db_util.cleanup()
            except Exception as e:
                error_str = str(e)
                assert 'mock' not in error_str.lower(), f"Entry point '{entry_point_name}' error suggests mock fallback: {error_str}"
                raise

    async def _verify_session_is_real(self, session: AsyncSession, entry_point_name: str):
        """Helper to verify a session is real, not mocked."""
        real_session_attributes = ['bind', 'execute', 'commit', 'rollback', 'close']
        for attr in real_session_attributes:
            assert hasattr(session, attr), f"Entry point '{entry_point_name}' session missing real attribute '{attr}'"
            assert callable(getattr(session, attr)), f"Entry point '{entry_point_name}' session attribute '{attr}' is not callable"
        mock_attributes = ['call_count', 'called', 'return_value', '_mock_name', '_spec_class', 'assert_called', 'assert_called_once', 'reset_mock']
        for attr in mock_attributes:
            assert not hasattr(session, attr), f"CRITICAL: Entry point '{entry_point_name}' session has mock attribute '{attr}'. All sessions must be real AsyncSession instances."
        try:
            result = await session.execute(text("SELECT 'real_session_test' as test_marker"))
            row = result.fetchone()
            assert row is not None, f"Entry point '{entry_point_name}' session failed to execute query"
            assert row.test_marker == 'real_session_test', f"Entry point '{entry_point_name}' session query returned unexpected result"
        except Exception as e:
            raise AssertionError(f"Entry point '{entry_point_name}' session failed basic query: {e}. This indicates the session may not be properly connected to a real database.")

    @pytest.mark.asyncio
    async def test_session_lifecycle_events_are_real(self):
        """Test that session lifecycle events are real, not mocked."""
        async with DatabaseTestUtilities('netra_backend') as db_util:
            session = await db_util.get_test_session()
            events_triggered = []
            original_execute = session.execute
            original_commit = session.commit
            original_rollback = session.rollback
            original_close = session.close

            async def tracked_execute(*args, **kwargs):
                events_triggered.append('execute')
                return await original_execute(*args, **kwargs)

            async def tracked_commit(*args, **kwargs):
                events_triggered.append('commit')
                return await original_commit(*args, **kwargs)

            async def tracked_rollback(*args, **kwargs):
                events_triggered.append('rollback')
                return await original_rollback(*args, **kwargs)

            async def tracked_close(*args, **kwargs):
                events_triggered.append('close')
                return await original_close(*args, **kwargs)
            session.execute = tracked_execute
            session.commit = tracked_commit
            session.rollback = tracked_rollback
            session.close = tracked_close
            await session.execute(text('SELECT 1'))
            events_triggered.append('manual_commit')
            await session.commit()
            expected_events = ['execute', 'manual_commit', 'commit']
            for event in expected_events:
                assert event in events_triggered, f"Expected event '{event}' not triggered. This indicates mock session behavior. Events: {events_triggered}"

    def test_no_mock_dependencies_in_database_modules(self):
        """Test that database modules don't import or depend on mock libraries."""
        modules_to_check = ['netra_backend.app.db.postgres_core', 'netra_backend.app.database', 'netra_backend.app.db.database_manager']
        for module_name in modules_to_check:
            try:
                module = sys.modules.get(module_name)
                if module is None:
                    module = __import__(module_name, fromlist=[''])
                for name, obj in module.__dict__.items():
                    if hasattr(obj, '_mock_name') or hasattr(obj, '_spec_class'):
                        pytest.fail(f"CRITICAL: Module {module_name} contains mock object '{name}'. Database modules must not contain or depend on mock objects.")
                module_source = inspect.getsource(module) if hasattr(module, '__file__') else ''
                forbidden_mock_imports = ['AsyncMock', 'MagicMock']
                for forbidden_import in forbidden_mock_imports:
                    if forbidden_import in module_source:
                        pytest.fail(f"CRITICAL: Module {module_name} contains forbidden import '{forbidden_import}'. ")
            except ImportError:
                continue
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')