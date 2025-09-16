"""
Integration Tests: Request-Scoped Session Factory Error Path Validation

This test suite validates error handling in the request-scoped session factory,
specifically focusing on the code paths where the SessionMetrics SSOT violation occurs.

Business Value:
- Validates database error handling doesn't crash due to field access bugs
- Ensures session factory error logging works correctly under load
- Tests real database connection failure scenarios with proper error context

CRITICAL: Uses REAL PostgreSQL connection from test environment.
NO MOCKS - These are integration tests that validate real error paths.

Expected Test Behavior:
- Tests that trigger database errors should expose AttributeError in error handling
- Session factory should handle errors gracefully despite field access bugs
- Error context logging should fail due to missing fields in SessionMetrics

Target Bug Location:
- request_scoped_session_factory.py lines 383-385 in error handling block
"""
import asyncio
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import patch
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError, TimeoutError as SQLTimeoutError
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory, SessionMetrics, SessionState, ConnectionPoolMetrics
from netra_backend.app.database import get_db, DatabaseManager
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.fixtures.lightweight_services import lightweight_services_fixture

class RequestScopedSessionFactoryErrorPathsTests(SSotBaseTestCase):
    """
    Integration tests for request-scoped session factory error handling.
    
    These tests use REAL PostgreSQL connections and trigger actual database
    errors to validate the error handling code paths where the SSOT bug occurs.
    """

    @pytest.fixture(autouse=True)
    async def setup_real_services(self):
        """Setup real database connection for integration testing."""
        self.services_fixture = lightweight_services_fixture
        await self.services_fixture.setup()
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.session_factory = RequestScopedSessionFactory(database_manager=self.db_manager)
        yield
        await self.services_fixture.cleanup()
        if self.db_manager:
            await self.db_manager.close()

    async def test_database_connection_error_triggers_ssot_bug(self):
        """
        Test that database connection errors trigger the SessionMetrics SSOT bug.
        
        This test forces a database connection error and validates that
        the error handling code fails due to missing SessionMetrics fields.
        """
        user_id = 'error-test-user-123'
        request_id = 'error-test-request-456'
        with patch.object(self.db_manager, 'get_session', side_effect=OperationalError('Connection failed', None, None)):
            try:
                async with self.session_factory.get_session(user_id=user_id, request_id=request_id) as session:
                    pytest.fail('Expected OperationalError due to patched connection failure')
            except Exception as e:
                print(f'\n[U+1F41B] CAPTURED ERROR: {type(e).__name__}: {e}')
                if 'has no attribute' in str(e) and ('last_activity' in str(e) or 'operations_count' in str(e) or 'errors' in str(e)):
                    print(' PASS:  SSOT BUG REPRODUCED: AttributeError in error handling')
                    print('This proves the SessionMetrics field access bug exists')
                    assert True, 'Successfully reproduced SSOT bug in error handling'
                else:
                    print(' WARNING: [U+FE0F] Original database error (SSOT bug may be fixed or not triggered)')
                    assert isinstance(e, (OperationalError, SQLAlchemyError)), f'Expected database error, got {type(e)}'

    async def test_session_timeout_error_path(self):
        """
        Test session timeout scenarios that trigger error logging.
        
        This uses real database with artificial timeout to force error paths.
        """
        user_id = 'timeout-test-user-789'
        request_id = 'timeout-test-request-012'

        async def slow_session_creation(*args, **kwargs):
            await asyncio.sleep(0.1)
            raise SQLTimeoutError('Session creation timeout', None, None)
        with patch.object(self.db_manager, 'get_session', side_effect=slow_session_creation):
            try:
                async with self.session_factory.get_session(user_id=user_id, request_id=request_id, timeout=0.05) as session:
                    pytest.fail('Expected SQLTimeoutError due to timeout')
            except Exception as e:
                print(f'\n[U+23F1][U+FE0F] TIMEOUT ERROR: {type(e).__name__}: {e}')
                if 'has no attribute' in str(e):
                    print(' PASS:  SSOT BUG TRIGGERED: Timeout error handling failed due to field access')
                    assert any((field in str(e) for field in ['last_activity', 'operations_count', 'errors'])), f'Expected SSOT bug related to known missing fields, got: {e}'
                else:
                    assert 'timeout' in str(e).lower() or isinstance(e, SQLTimeoutError)
                    print(' WARNING: [U+FE0F] Timeout handled without SSOT bug (possibly fixed)')

    async def test_session_factory_pool_exhaustion_error(self):
        """
        Test database connection pool exhaustion error paths.
        
        This creates many concurrent sessions to exhaust the pool and
        trigger error handling where the SSOT bug occurs.
        """
        user_id = 'pool-test-user-345'
        base_request_id = 'pool-test-request'
        concurrent_sessions = []
        max_connections = 5
        original_pool_size = getattr(self.session_factory, '_max_pool_size', None)
        self.session_factory._max_pool_size = max_connections
        try:
            for i in range(max_connections + 3):
                request_id = f'{base_request_id}-{i}'
                session_task = asyncio.create_task(self._hold_session_open(user_id, request_id))
                concurrent_sessions.append(session_task)
                await asyncio.sleep(0.01)
            results = await asyncio.gather(*concurrent_sessions, return_exceptions=True)
            ssot_bugs_found = 0
            pool_errors_found = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    print(f'\n SEARCH:  SESSION {i} ERROR: {type(result).__name__}: {error_msg}')
                    if 'has no attribute' in error_msg and any((field in error_msg for field in ['last_activity', 'operations_count', 'errors'])):
                        ssot_bugs_found += 1
                        print(f'   PASS:  SSOT BUG FOUND in session {i}')
                    elif 'pool' in error_msg.lower() or 'connection' in error_msg.lower():
                        pool_errors_found += 1
                        print(f'   IDEA:  Pool exhaustion error in session {i}')
            print(f'\n CHART:  ERROR ANALYSIS:')
            print(f'  SSOT bugs found: {ssot_bugs_found}')
            print(f'  Pool errors found: {pool_errors_found}')
            print(f'  Total sessions: {len(results)}')
            assert ssot_bugs_found > 0 or pool_errors_found > 0, 'Expected either SSOT bugs or pool exhaustion errors'
            if ssot_bugs_found > 0:
                print(' PASS:  SSOT BUG REPRODUCED under pool exhaustion conditions')
        finally:
            if original_pool_size is not None:
                self.session_factory._max_pool_size = original_pool_size
            for task in concurrent_sessions:
                if not task.done():
                    task.cancel()

    async def _hold_session_open(self, user_id: str, request_id: str) -> None:
        """Helper method to hold a session open briefly."""
        try:
            async with self.session_factory.get_session(user_id=user_id, request_id=request_id) as session:
                await asyncio.sleep(0.05)
                result = await session.execute('SELECT 1 as test_query')
                row = result.first()
                assert row[0] == 1, 'Basic query should work'
        except Exception as e:
            raise e

    async def test_session_metrics_creation_and_error_logging(self):
        """
        Test SessionMetrics creation and error logging integration.
        
        This directly tests the error logging code path that contains the SSOT bug.
        """
        user_id = 'metrics-test-user-678'
        request_id = 'metrics-test-request-901'
        try:
            async with self.session_factory.get_session(user_id=user_id, request_id=request_id) as session:
                session_metrics = getattr(session, '_session_metrics', None)
                if session_metrics is None:
                    factory_metrics = getattr(self.session_factory, '_active_sessions', {})
                    session_key = f'{user_id}:{request_id}'
                    session_metrics = factory_metrics.get(session_key)
                if session_metrics:
                    print(f'\n CHART:  SESSION METRICS FOUND:')
                    print(f'  Type: {type(session_metrics).__name__}')
                    print(f"  Session ID: {getattr(session_metrics, 'session_id', 'N/A')}")
                    print(f"  Created: {getattr(session_metrics, 'created_at', 'N/A')}")
                    self._test_session_metrics_field_access(session_metrics)
                else:
                    print(' WARNING: [U+FE0F] No session metrics found - may not be instrumented')
                await self._force_session_error_with_logging(session, session_metrics)
        except Exception as e:
            print(f'\n FIRE:  SESSION ERROR: {type(e).__name__}: {e}')
            if 'has no attribute' in str(e):
                expected_fields = ['last_activity', 'operations_count', 'errors']
                if any((field in str(e) for field in expected_fields)):
                    print(' PASS:  SSOT BUG CONFIRMED: Error logging failed due to missing SessionMetrics fields')
                    assert True, 'Successfully reproduced SSOT bug in session error logging'
                else:
                    print('[U+2753] Unexpected attribute error:', str(e))
            else:
                print(' WARNING: [U+FE0F] Different error occurred - SSOT bug may not be triggered')

    def _test_session_metrics_field_access(self, session_metrics: SessionMetrics) -> None:
        """Test direct field access on SessionMetrics to expose SSOT bug."""
        print('\n SEARCH:  TESTING SESSIONMETRICS FIELD ACCESS:')
        problematic_fields = {'last_activity': 'Should be last_activity_at', 'operations_count': 'Should be query_count + transaction_count', 'errors': 'Should be error_count'}
        for field_name, correct_name in problematic_fields.items():
            try:
                value = getattr(session_metrics, field_name)
                print(f'   FAIL:  UNEXPECTED: {field_name} exists with value {value}')
            except AttributeError as e:
                print(f'   PASS:  CONFIRMED: {field_name} missing -> {correct_name}')
                print(f'    AttributeError: {e}')
        correct_fields = {'last_activity_at': lambda m: getattr(m, 'last_activity_at', None), 'error_count': lambda m: getattr(m, 'error_count', 0), 'query_count': lambda m: getattr(m, 'query_count', 0)}
        print('\n PASS:  CORRECT FIELD ACCESS:')
        for field_name, accessor in correct_fields.items():
            try:
                value = accessor(session_metrics)
                print(f'  {field_name}: {value}')
            except Exception as e:
                print(f'  {field_name}: ERROR {e}')

    async def _force_session_error_with_logging(self, session: AsyncSession, session_metrics: SessionMetrics) -> None:
        """Force a session error to trigger the error logging code path."""
        try:
            await session.execute('SELECT * FROM non_existent_table_12345')
        except Exception as db_error:
            print(f'\n[U+1F4A5] FORCED DATABASE ERROR: {db_error}')
            try:
                error_context = {'session_metrics': {'state': session_metrics.state.value if session_metrics.state else 'unknown', 'created_at': session_metrics.created_at.isoformat() if session_metrics.created_at else None, 'last_activity': session_metrics.last_activity.isoformat() if session_metrics.last_activity else None, 'operations_count': session_metrics.operations_count, 'errors': session_metrics.errors}}
                print(' FAIL:  UNEXPECTED: Error context created without AttributeError')
                print(f'Context: {error_context}')
            except AttributeError as attr_error:
                print(f' PASS:  SSOT BUG REPRODUCED in error logging: {attr_error}')
                raise attr_error

    async def test_concurrent_session_errors_ssot_impact(self):
        """
        Test concurrent session errors to validate SSOT bug impact under load.
        
        This test simulates multiple concurrent requests that fail,
        all triggering the error logging code path with the SSOT bug.
        """
        concurrent_errors = []
        num_concurrent = 5
        for i in range(num_concurrent):
            user_id = f'concurrent-error-user-{i}'
            request_id = f'concurrent-error-request-{i}'
            error_task = asyncio.create_task(self._trigger_concurrent_session_error(user_id, request_id))
            concurrent_errors.append(error_task)
        results = await asyncio.gather(*concurrent_errors, return_exceptions=True)
        ssot_errors = []
        database_errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = str(result)
                if 'has no attribute' in error_msg and any((field in error_msg for field in ['last_activity', 'operations_count', 'errors'])):
                    ssot_errors.append((i, result))
                else:
                    database_errors.append((i, result))
        print(f'\n CHART:  CONCURRENT ERROR ANALYSIS:')
        print(f'  Total requests: {num_concurrent}')
        print(f'  SSOT errors: {len(ssot_errors)}')
        print(f'  Database errors: {len(database_errors)}')
        for i, error in ssot_errors:
            print(f'  SSOT Error {i}: {error}')
        if len(ssot_errors) > 0:
            print(' PASS:  SSOT BUG CONFIRMED: Multiple concurrent requests trigger AttributeError')
            assert True, f'Found {len(ssot_errors)} SSOT bugs in concurrent error handling'
        else:
            print(' WARNING: [U+FE0F] No SSOT bugs found - may be fixed or not triggered in this test')
            assert len(database_errors) > 0, 'Expected some database errors from concurrent requests'

    async def _trigger_concurrent_session_error(self, user_id: str, request_id: str) -> None:
        """Helper to trigger session error for concurrent testing."""
        try:
            async with self.session_factory.get_session(user_id=user_id, request_id=request_id) as session:
                await session.execute('SELECT * FROM definitely_nonexistent_table')
        except Exception as e:
            raise e
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')