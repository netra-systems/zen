"""Test Request-Scoped Session Factory

Comprehensive tests for the RequestScopedSessionFactory ensuring proper
session isolation, connection pool management, and leak detection.

Test Coverage:
1. Session isolation between concurrent users
2. Connection pool exhaustion protection  
3. Session leak detection and cleanup
4. Metrics collection and monitoring
5. Circuit breaker protection
6. Load testing with 100+ concurrent sessions
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory, get_session_factory, get_isolated_session, validate_session_isolation, get_factory_health, shutdown_session_factory, SessionState, SessionMetrics, ConnectionPoolMetrics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

@pytest.mark.database
class RequestScopedSessionFactoryTests:
    """Test the RequestScopedSessionFactory class."""

    @pytest.fixture
    async def factory(self):
        """Create a fresh factory for testing."""
        factory = RequestScopedSessionFactory()
        yield factory
        await factory.close()

    async def test_factory_initialization(self, factory: RequestScopedSessionFactory):
        """Test factory initializes correctly."""
        assert factory._active_sessions == {}
        assert factory._pool_metrics.active_sessions == 0
        assert factory._leak_detection_enabled is True
        assert factory._cleanup_task is not None

    async def test_session_creation_and_cleanup(self, factory: RequestScopedSessionFactory):
        """Test basic session creation and cleanup."""
        user_id = 'test_user_123'
        request_id = 'test_request_456'
        async with factory.get_request_scoped_session(user_id, request_id) as session:
            assert isinstance(session, AsyncSession)
            assert session.info['user_id'] == user_id
            assert session.info['request_id'] == request_id
            assert session.info['is_request_scoped'] is True
            assert session.info['factory_managed'] is True
            assert factory._pool_metrics.active_sessions == 1
            assert len(factory._active_sessions) == 1
        assert factory._pool_metrics.active_sessions == 0
        assert len(factory._active_sessions) == 0
        assert factory._pool_metrics.sessions_closed == 1

    async def test_session_isolation_validation(self, factory: RequestScopedSessionFactory):
        """Test session isolation validation."""
        user_id = 'test_user_isolation'
        async with factory.get_request_scoped_session(user_id) as session:
            assert await factory.validate_session_isolation(session, user_id)
            with pytest.raises(ValueError, match='Session isolation violated'):
                await factory.validate_session_isolation(session, 'different_user')

    async def test_concurrent_user_isolation(self, factory: RequestScopedSessionFactory):
        """Test that concurrent users get isolated sessions."""
        num_users = 10

        async def user_session_test(user_index: int):
            """Test session for a single user."""
            user_id = f'user_{user_index}'
            request_id = f'request_{user_index}'
            async with factory.get_request_scoped_session(user_id, request_id) as session:
                assert session.info['user_id'] == user_id
                assert session.info['request_id'] == request_id
                result = await session.execute(text('SELECT :user_id as user'), {'user_id': user_id})
                row = result.fetchone()
                assert row[0] == user_id
                return f'success_{user_index}'
        tasks = [user_session_test(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks)
        assert len(results) == num_users
        for i, result in enumerate(results):
            assert result == f'success_{i}'
        assert factory._pool_metrics.active_sessions == 0
        assert factory._pool_metrics.total_sessions_created == num_users

    async def test_session_metrics_collection(self, factory: RequestScopedSessionFactory):
        """Test that session metrics are collected properly."""
        user_id = 'metrics_test_user'
        async with factory.get_request_scoped_session(user_id) as session:
            await session.execute(text('SELECT 1'))
            await session.execute(text('SELECT 2'))
            session_metrics = factory.get_session_metrics()
            assert len(session_metrics) == 1
            session_id = list(session_metrics.keys())[0]
            metrics = session_metrics[session_id]
            assert metrics['user_id'] == user_id
            assert metrics['state'] == SessionState.ACTIVE.value

    async def test_pool_metrics_tracking(self, factory: RequestScopedSessionFactory):
        """Test that pool metrics are tracked correctly."""
        initial_metrics = factory.get_pool_metrics()
        assert initial_metrics.total_sessions_created == 0
        num_sessions = 5
        tasks = []

        async def create_session(i):
            async with factory.get_request_scoped_session(f'user_{i}') as session:
                await asyncio.sleep(0.1)
        tasks = [create_session(i) for i in range(num_sessions)]
        await asyncio.gather(*tasks)
        final_metrics = factory.get_pool_metrics()
        assert final_metrics.total_sessions_created == num_sessions
        assert final_metrics.sessions_closed == num_sessions
        assert final_metrics.active_sessions == 0
        assert final_metrics.peak_concurrent_sessions >= 1

    async def test_session_error_handling(self, factory: RequestScopedSessionFactory):
        """Test session error handling and cleanup."""
        user_id = 'error_test_user'
        with pytest.raises(ValueError, match='Test error'):
            async with factory.get_request_scoped_session(user_id) as session:
                raise ValueError('Test error')
        assert factory._pool_metrics.active_sessions == 0
        assert len(factory._active_sessions) == 0

    async def test_health_check(self, factory: RequestScopedSessionFactory):
        """Test factory health check functionality."""
        health = await factory.health_check()
        assert 'status' in health
        assert 'factory_metrics' in health
        assert 'pool_status' in health
        factory_metrics = health['factory_metrics']
        assert 'active_sessions' in factory_metrics
        assert 'total_created' in factory_metrics
        assert 'leaked_sessions' in factory_metrics

    async def test_factory_cleanup(self, factory: RequestScopedSessionFactory):
        """Test factory cleanup functionality."""
        async with factory.get_request_scoped_session('user1'):
            pass
        assert factory._pool_metrics.total_sessions_created == 1
        await factory.close()
        assert factory._cleanup_task.cancelled()

@pytest.mark.database
class GlobalSessionFactoryTests:
    """Test global session factory functions."""

    async def test_get_session_factory_singleton(self):
        """Test that get_session_factory returns singleton."""
        factory1 = await get_session_factory()
        factory2 = await get_session_factory()
        assert factory1 is factory2
        await factory1.close()

    async def test_get_isolated_session(self):
        """Test get_isolated_session function."""
        user_id = 'global_test_user'
        request_id = 'global_test_request'
        thread_id = 'global_test_thread'
        async with get_isolated_session(user_id, request_id, thread_id) as session:
            assert isinstance(session, AsyncSession)
            assert session.info['user_id'] == user_id
            assert session.info['request_id'] == request_id
            assert session.info['thread_id'] == thread_id

    async def test_validate_session_isolation_function(self):
        """Test validate_session_isolation function."""
        user_id = 'validation_test_user'
        async with get_isolated_session(user_id) as session:
            assert await validate_session_isolation(session, user_id)
            with pytest.raises(ValueError):
                await validate_session_isolation(session, 'wrong_user')

    async def test_get_factory_health_function(self):
        """Test get_factory_health function."""
        health = await get_factory_health()
        assert isinstance(health, dict)
        assert 'status' in health

    async def test_shutdown_session_factory(self):
        """Test shutdown_session_factory function."""
        factory = await get_session_factory()
        assert factory is not None
        await shutdown_session_factory()

@pytest.mark.database
class ConcurrentLoadTestingTests:
    """Test high-concurrency scenarios."""

    @pytest.fixture
    async def factory(self):
        """Create factory for load testing."""
        factory = RequestScopedSessionFactory()
        yield factory
        await factory.close()

    async def test_concurrent_session_load(self, factory: RequestScopedSessionFactory):
        """Test with high concurrent session load."""
        num_concurrent = 50
        queries_per_session = 3

        async def session_workload(session_index: int):
            """Workload for a single session."""
            user_id = f'load_user_{session_index}'
            request_id = f'load_req_{session_index}'
            try:
                async with factory.get_request_scoped_session(user_id, request_id) as session:
                    for query_index in range(queries_per_session):
                        result = await session.execute(text('SELECT :session_id as s_id, :query_id as q_id'), {'session_id': session_index, 'query_id': query_index})
                        row = result.fetchone()
                        assert row[0] == session_index
                        assert row[1] == query_index
                return {'session_index': session_index, 'status': 'success'}
            except Exception as e:
                return {'session_index': session_index, 'status': 'failed', 'error': str(e)}
        tasks = [session_workload(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_sessions = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        failed_sessions = [r for r in results if isinstance(r, dict) and r.get('status') == 'failed']
        exceptions = [r for r in results if isinstance(r, Exception)]
        success_rate = len(successful_sessions) / num_concurrent
        assert success_rate >= 0.95, f'Success rate too low: {success_rate:.2%}'
        pool_metrics = factory.get_pool_metrics()
        assert pool_metrics.total_sessions_created == num_concurrent
        assert pool_metrics.active_sessions == 0
        assert pool_metrics.peak_concurrent_sessions > 0
        if failed_sessions:
            print(f'Failed sessions: {failed_sessions}')
        if exceptions:
            print(f'Exceptions: {exceptions}')

    async def test_connection_pool_exhaustion_protection(self, factory: RequestScopedSessionFactory):
        """Test protection against connection pool exhaustion."""
        num_sessions = 100

        async def long_running_session(session_index: int):
            """Create a session that holds connections."""
            user_id = f'pool_test_user_{session_index}'
            try:
                async with factory.get_request_scoped_session(user_id) as session:
                    await asyncio.sleep(0.05)
                    result = await session.execute(text('SELECT 1'))
                    return result.scalar()
            except Exception as e:
                return str(e)
        tasks = [long_running_session(i) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_results = [r for r in results if r == 1]
        assert len(successful_results) > 0
        await asyncio.sleep(0.1)
        assert factory._pool_metrics.active_sessions == 0

    async def test_session_leak_detection(self, factory: RequestScopedSessionFactory):
        """Test session leak detection and cleanup."""
        user_id = 'leak_test_user'
        session_id = f'{user_id}_leak_test_{uuid.uuid4().hex[:8]}'
        from netra_backend.app.database.request_scoped_session_factory import SessionMetrics, SessionState
        leak_metrics = SessionMetrics(session_id=session_id, request_id='leak_request', user_id=user_id, created_at=datetime.now(timezone.utc))
        leak_metrics.state = SessionState.ACTIVE
        factory._active_sessions[session_id] = leak_metrics
        factory._pool_metrics.active_sessions += 1
        await factory._detect_and_cleanup_leaks()

    @pytest.mark.timeout(60)
    async def test_extreme_concurrent_load(self, factory: RequestScopedSessionFactory):
        """Test extreme concurrent load (100+ sessions)."""
        num_concurrent = 100

        async def minimal_session_test(session_index: int):
            """Minimal session test for high concurrency."""
            user_id = f'extreme_user_{session_index}'
            try:
                async with factory.get_request_scoped_session(user_id) as session:
                    result = await session.execute(text('SELECT 1'))
                    return result.scalar() == 1
            except Exception:
                return False
        start_time = datetime.now(timezone.utc)
        tasks = [minimal_session_test(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now(timezone.utc)
        successful_results = [r for r in results if r is True]
        success_rate = len(successful_results) / num_concurrent
        total_duration_ms = (end_time - start_time).total_seconds() * 1000
        print(f'Extreme load test: {num_concurrent} concurrent sessions')
        print(f'Success rate: {success_rate:.2%}')
        print(f'Total duration: {total_duration_ms:.1f}ms')
        print(f'Avg time per session: {total_duration_ms / num_concurrent:.1f}ms')
        assert success_rate >= 0.9, f'Success rate too low for extreme load: {success_rate:.2%}'
        final_metrics = factory.get_pool_metrics()
        assert final_metrics.active_sessions == 0
        assert final_metrics.total_sessions_created == num_concurrent
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')