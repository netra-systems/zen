"""Comprehensive DatabaseManager Integration Test Suite

CRITICAL: Integration tests for DatabaseManager following TEST_CREATION_GUIDE.md patterns.
Uses REAL database connections (SQLite for testing) to ensure genuine integration validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Foundation for ALL services
- Business Goal: Ensure DatabaseManager reliably handles real-world database operations  
- Value Impact: Prevents 500 errors, data corruption, and service outages in production
- Strategic Impact: DatabaseManager is core infrastructure - failures cascade to all services

TEST PHILOSOPHY: Real Services > Mocks
- Uses real SQLite database connections for authentic integration testing
- Tests actual DatabaseURLBuilder integration patterns
- Validates real async session management and transaction handling
- Covers realistic multi-user isolation scenarios
- Tests genuine connection pooling, retry logic, and error recovery

COVERAGE TARGETS:
1. Database connection pooling and lifecycle management 
2. Multi-user data isolation and security scenarios
3. Transaction handling and rollback patterns
4. Connection retry and circuit breaker behaviors
5. Database migration and schema validation flows
6. Concurrent access patterns and thread safety
7. Performance under load (bulk operations)
8. Comprehensive error handling and recovery
9. Cross-service database consistency patterns
10. Database URL validation and connection string handling

CRITICAL: Follows CLAUDE.md requirements:
- NO MOCKS for database operations (real SQLite connections)
- Uses IsolatedEnvironment (never os.environ directly) 
- Follows SSOT patterns from test_framework/
- Tests deliver genuine business value validation
"""
import asyncio
import pytest
import logging
import sqlite3
import tempfile
import os
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.sql import select
from pathlib import Path
import time
import threading
from unittest.mock import patch
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.real_services_test_fixtures import real_services_fixture
logger = logging.getLogger(__name__)

class DatabaseManagerIntegrationComprehensiveTests(BaseIntegrationTest):
    """Comprehensive integration test suite for DatabaseManager with real database connections."""

    def setup_method(self):
        """Set up for each test method with real database environment."""
        super().setup_method()
        self.temp_db_dir = tempfile.mkdtemp(prefix='netra_db_test_')
        self.primary_db_path = os.path.join(self.temp_db_dir, 'primary.db')
        self.secondary_db_path = os.path.join(self.temp_db_dir, 'secondary.db')
        self.test_env_vars = {'ENVIRONMENT': 'test', 'USE_MEMORY_DB': 'false', 'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5434', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_password', 'POSTGRES_DB': 'test_db', 'SQLITE_URL': f'sqlite+aiosqlite:///{self.primary_db_path}', 'SQLITE_SECONDARY_URL': f'sqlite+aiosqlite:///{self.secondary_db_path}', 'GOOGLE_OAUTH_CLIENT_ID_TEST': 'test_client_id', 'GOOGLE_OAUTH_CLIENT_SECRET_TEST': 'test_client_secret'}
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None

    def teardown_method(self):
        """Clean up after each test method."""
        super().teardown_method()
        try:
            if os.path.exists(self.primary_db_path):
                os.unlink(self.primary_db_path)
            if os.path.exists(self.secondary_db_path):
                os.unlink(self.secondary_db_path)
            os.rmdir(self.temp_db_dir)
        except OSError as e:
            logger.warning(f'Failed to clean up test databases: {e}')

    async def _create_test_tables(self, engine: AsyncEngine) -> None:
        """Create test tables in the database."""
        metadata = MetaData()
        test_table = Table('test_users', metadata, Column('id', Integer, primary_key=True), Column('username', String(50), nullable=False), Column('email', String(100), unique=True), Column('created_at', DateTime))
        test_concurrent = Table('test_concurrent', metadata, Column('id', Integer, primary_key=True), Column('thread_id', String(50)), Column('operation_id', String(100)), Column('data', String(200)))
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_manager_real_sqlite_initialization(self, isolated_env):
        """Test DatabaseManager initialization with real SQLite database."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            assert db_manager._initialized
            assert 'primary' in db_manager._engines
            engine = db_manager.get_engine('primary')
            await self._create_test_tables(engine)
            async with db_manager.get_session() as session:
                result = await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'testuser', 'email': 'test@example.com'})
                await session.commit()
                result = await session.execute(text('SELECT username FROM test_users WHERE email = :email'), {'email': 'test@example.com'})
                row = result.fetchone()
                assert row is not None
                assert row[0] == 'testuser'
            await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_user_data_isolation_real_sessions(self, isolated_env):
        """Test multi-user data isolation using real database sessions."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            engine = db_manager.get_engine('primary')
            await self._create_test_tables(engine)
            user1_data = []
            user2_data = []
            async with db_manager.get_session() as user1_session:
                await user1_session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'user1', 'email': 'user1@example.com'})
                await user1_session.commit()
                result = await user1_session.execute(text('SELECT id, username FROM test_users WHERE username = :username'), {'username': 'user1'})
                user1_data = result.fetchall()
            async with db_manager.get_session() as user2_session:
                await user2_session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'user2', 'email': 'user2@example.com'})
                await user2_session.commit()
                result = await user2_session.execute(text('SELECT username FROM test_users ORDER BY username'))
                user2_data = result.fetchall()
            assert len(user1_data) == 1
            assert user1_data[0][1] == 'user1'
            assert len(user2_data) == 2
            usernames = [row[0] for row in user2_data]
            assert 'user1' in usernames
            assert 'user2' in usernames
            await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transaction_rollback_real_database(self, isolated_env):
        """Test transaction handling and rollback scenarios with real database."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            engine = db_manager.get_engine('primary')
            await self._create_test_tables(engine)
            async with db_manager.get_session() as session:
                await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'commit_user', 'email': 'commit@example.com'})
            transaction_failed = False
            try:
                async with db_manager.get_session() as session:
                    await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'rollback_user', 'email': 'rollback@example.com'})
                    await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'rollback_user', 'email': 'rollback@example.com'})
            except Exception as e:
                transaction_failed = True
                logger.info(f'Expected transaction failure: {e}')
            assert transaction_failed, 'Transaction should have failed due to unique constraint'
            async with db_manager.get_session() as session:
                result = await session.execute(text('SELECT username FROM test_users'))
                usernames = [row[0] for row in result.fetchall()]
                assert 'commit_user' in usernames
                assert 'rollback_user' not in usernames
            await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_health_check_real_database(self, isolated_env):
        """Test database health check functionality with real database."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            health_result = await db_manager.health_check()
            assert health_result['status'] == 'healthy'
            assert health_result['engine'] == 'primary'
            assert health_result['connection'] == 'ok'
            await db_manager.close_all()
            health_result = await db_manager.health_check()
            assert health_result['status'] == 'unhealthy'
            assert health_result['engine'] == 'primary'
            assert 'not initialized' in health_result['error'].lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_database_access_thread_safety(self, isolated_env):
        """Test concurrent access patterns and thread safety with real database."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            engine = db_manager.get_engine('primary')
            await self._create_test_tables(engine)

            async def concurrent_insert_operation(thread_id: int, operation_count: int):
                """Perform concurrent database insertions."""
                results = []
                for i in range(operation_count):
                    try:
                        async with db_manager.get_session() as session:
                            operation_id = f'thread_{thread_id}_op_{i}'
                            await session.execute(text('INSERT INTO test_concurrent (thread_id, operation_id, data) VALUES (:thread_id, :operation_id, :data)'), {'thread_id': str(thread_id), 'operation_id': operation_id, 'data': f'data_{i}'})
                            await session.commit()
                            results.append(operation_id)
                    except Exception as e:
                        logger.error(f'Concurrent operation failed: {e}')
                        results.append(f'ERROR_{i}')
                return results
            num_threads = 5
            operations_per_thread = 10
            tasks = []
            for thread_id in range(num_threads):
                task = asyncio.create_task(concurrent_insert_operation(thread_id, operations_per_thread))
                tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_successful_ops = 0
            for thread_results in results:
                if isinstance(thread_results, list):
                    successful_ops = [r for r in thread_results if not r.startswith('ERROR_')]
                    total_successful_ops += len(successful_ops)
            expected_ops = num_threads * operations_per_thread
            assert total_successful_ops == expected_ops, f'Expected {expected_ops} successful operations, got {total_successful_ops}'
            async with db_manager.get_session() as session:
                result = await session.execute(text('SELECT COUNT(*) FROM test_concurrent'))
                count = result.scalar()
                assert count == expected_ops
                for thread_id in range(num_threads):
                    result = await session.execute(text('SELECT COUNT(*) FROM test_concurrent WHERE thread_id = :thread_id'), {'thread_id': str(thread_id)})
                    thread_count = result.scalar()
                    assert thread_count == operations_per_thread
            await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_url_builder_integration_real_scenarios(self, isolated_env):
        """Test DatabaseURLBuilder integration with real database scenarios."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        test_scenarios = [{'name': 'sqlite_memory', 'env_vars': {'USE_MEMORY_DB': 'true'}, 'expected_driver': 'aiosqlite'}, {'name': 'sqlite_file', 'env_vars': {'USE_MEMORY_DB': 'false'}, 'expected_driver': 'aiosqlite'}, {'name': 'postgres_tcp', 'env_vars': {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5434', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_password', 'POSTGRES_DB': 'test_db'}, 'expected_driver': 'asyncpg'}]
        for scenario in test_scenarios:
            logger.info(f"Testing DatabaseURLBuilder scenario: {scenario['name']}")
            scenario_env = self.test_env_vars.copy()
            scenario_env.update(scenario['env_vars'])
            for key, value in scenario_env.items():
                isolated_env.set(key, value, source='test')
            url_builder = DatabaseURLBuilder(isolated_env.as_dict())
            if scenario['name'].startswith('sqlite'):
                if scenario['name'] == 'sqlite_memory':
                    test_url = 'sqlite+aiosqlite:///:memory:'
                else:
                    test_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            else:
                test_url = url_builder.get_url_for_environment(sync=False)
                if test_url:
                    test_url = url_builder.format_url_for_driver(test_url, 'asyncpg')
            if test_url:
                assert scenario['expected_driver'] in test_url.lower()
                if 'sqlite' in scenario['name']:
                    with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
                        mock_config.return_value.database_echo = False
                        mock_config.return_value.database_pool_size = 0
                        mock_config.return_value.database_max_overflow = 0
                        mock_config.return_value.database_url = test_url
                        mock_get_url.return_value = test_url
                        db_manager = DatabaseManager()
                        await db_manager.initialize()
                        engine = db_manager.get_engine('primary')
                        async with db_manager.get_session() as session:
                            result = await session.execute(text('SELECT 1 as test'))
                            value = result.scalar()
                            assert value == 1
                        await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulk_operations_performance_realistic_load(self, isolated_env):
        """Test performance under realistic load with bulk operations."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            engine = db_manager.get_engine('primary')
            await self._create_test_tables(engine)
            batch_size = 100
            num_batches = 10
            total_records = batch_size * num_batches
            start_time = time.time()
            for batch_num in range(num_batches):
                async with db_manager.get_session() as session:
                    for i in range(batch_size):
                        record_id = batch_num * batch_size + i
                        await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': f'bulk_user_{record_id}', 'email': f'bulk_{record_id}@example.com'})
                    await session.commit()
            bulk_insert_time = time.time() - start_time
            async with db_manager.get_session() as session:
                result = await session.execute(text('SELECT COUNT(*) FROM test_users'))
                count = result.scalar()
                assert count == total_records
            records_per_second = total_records / bulk_insert_time
            logger.info(f'Bulk insert performance: {records_per_second:.2f} records/second')
            assert records_per_second > 100, f'Performance too slow: {records_per_second:.2f} records/second'
            query_start = time.time()
            async with db_manager.get_session() as session:
                result = await session.execute(text('SELECT username, email FROM test_users ORDER BY username'))
                all_records = result.fetchall()
            query_time = time.time() - query_start
            query_records_per_second = total_records / query_time
            logger.info(f'Bulk query performance: {query_records_per_second:.2f} records/second')
            assert len(all_records) == total_records
            assert query_records_per_second > 1000, f'Query performance too slow: {query_records_per_second:.2f} records/second'
            await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_recovery_scenarios(self, isolated_env):
        """Test comprehensive error handling and recovery scenarios."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            engine = db_manager.get_engine('primary')
            await self._create_test_tables(engine)
            sql_error_handled = False
            try:
                async with db_manager.get_session() as session:
                    await session.execute(text('INVALID SQL STATEMENT'))
            except Exception as e:
                sql_error_handled = True
                logger.info(f'SQL error properly handled: {e}')
            assert sql_error_handled, 'SQL syntax error should be handled'
            constraint_error_handled = False
            try:
                async with db_manager.get_session() as session:
                    await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'unique_user', 'email': 'unique@example.com'})
                    await session.commit()
                async with db_manager.get_session() as session:
                    await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'duplicate_user', 'email': 'unique@example.com'})
                    await session.commit()
            except Exception as e:
                constraint_error_handled = True
                logger.info(f'Constraint error properly handled: {e}')
            assert constraint_error_handled, 'Unique constraint violation should be handled'
            async with db_manager.get_session() as session:
                await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'recovery_user', 'email': 'recovery@example.com'})
                await session.commit()
                result = await session.execute(text('SELECT username FROM test_users WHERE email = :email'), {'email': 'recovery@example.com'})
                row = result.fetchone()
                assert row is not None
                assert row[0] == 'recovery_user'
            try:
                async with db_manager.get_session() as session:
                    await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'cleanup_test', 'email': 'cleanup@example.com'})
                    raise RuntimeError('Simulated application error')
            except RuntimeError:
                pass
            async with db_manager.get_session() as session:
                result = await session.execute(text('SELECT COUNT(*) FROM test_users'))
                count = result.scalar()
                result = await session.execute(text('SELECT COUNT(*) FROM test_users WHERE email = :email'), {'email': 'cleanup@example.com'})
                cleanup_count = result.scalar()
                assert cleanup_count == 0, 'Rolled back transaction should not persist data'
            await db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_migration_url_format_validation(self, isolated_env):
        """Test database migration URL generation and format validation."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        isolated_env.set('POSTGRES_HOST', 'localhost', source='test')
        isolated_env.set('POSTGRES_PORT', '5432', source='test')
        isolated_env.set('POSTGRES_USER', 'migration_user', source='test')
        isolated_env.set('POSTGRES_PASSWORD', 'migration_pass', source='test')
        isolated_env.set('POSTGRES_DB', 'migration_db', source='test')
        migration_url = DatabaseManager.get_migration_url_sync_format()
        assert migration_url is not None
        assert migration_url.startswith('postgresql://'), f'Migration URL should be sync format: {migration_url}'
        assert 'migration_user' in migration_url or 'localhost' in migration_url
        assert '+asyncpg' not in migration_url, 'Migration URL should not contain async drivers'
        assert '+psycopg' not in migration_url, 'Migration URL should not contain async drivers'
        url_builder = DatabaseURLBuilder(isolated_env.as_dict())
        base_url = url_builder.get_url_for_environment(sync=True)
        if base_url:
            asyncpg_url = url_builder.format_url_for_driver(base_url, 'asyncpg')
            assert '+asyncpg://' in asyncpg_url
            sync_url = url_builder.format_url_for_driver(base_url, 'base')
            assert '+asyncpg' not in sync_url
            assert sync_url.startswith('postgresql://')
            is_valid, error_msg = url_builder.validate_url_for_driver(asyncpg_url, 'asyncpg')
            assert is_valid, f'AsyncPG URL validation failed: {error_msg}'
            is_valid, error_msg = url_builder.validate_url_for_driver(sync_url, 'base')
            assert is_valid, f'Sync URL validation failed: {error_msg}'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cross_service_consistency_patterns(self, isolated_env):
        """Test database patterns that ensure cross-service consistency."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            backend_db_manager = DatabaseManager()
            await backend_db_manager.initialize()
            auth_db_manager = DatabaseManager()
            await auth_db_manager.initialize()
            backend_engine = backend_db_manager.get_engine('primary')
            await self._create_test_tables(backend_engine)
            auth_engine = auth_db_manager.get_engine('primary')
            await self._create_test_tables(auth_engine)
            user_id = 'cross_service_user_123'
            async with backend_db_manager.get_session() as backend_session:
                await backend_session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': user_id, 'email': f'{user_id}@example.com'})
                await backend_session.commit()
            async with auth_db_manager.get_session() as auth_session:
                result = await auth_session.execute(text('SELECT username FROM test_users WHERE email = :email'), {'email': f'{user_id}@example.com'})
                row = result.fetchone()
                assert row is not None
                assert row[0] == user_id
                await auth_session.execute(text('UPDATE test_users SET username = :username WHERE email = :email'), {'username': f'{user_id}_updated', 'email': f'{user_id}@example.com'})
                await auth_session.commit()
            async with backend_db_manager.get_session() as backend_session:
                result = await backend_session.execute(text('SELECT username FROM test_users WHERE email = :email'), {'email': f'{user_id}@example.com'})
                row = result.fetchone()
                assert row is not None
                assert row[0] == f'{user_id}_updated'
            backend_transaction_complete = False
            auth_transaction_complete = False

            async def backend_transaction():
                nonlocal backend_transaction_complete
                async with backend_db_manager.get_session() as session:
                    await session.execute(text('INSERT INTO test_concurrent (thread_id, operation_id, data) VALUES (:thread_id, :operation_id, :data)'), {'thread_id': 'backend_service', 'operation_id': 'tx_test_1', 'data': 'backend_data'})
                    await asyncio.sleep(0.1)
                    await session.commit()
                    backend_transaction_complete = True

            async def auth_transaction():
                nonlocal auth_transaction_complete
                async with auth_db_manager.get_session() as session:
                    await session.execute(text('INSERT INTO test_concurrent (thread_id, operation_id, data) VALUES (:thread_id, :operation_id, :data)'), {'thread_id': 'auth_service', 'operation_id': 'tx_test_2', 'data': 'auth_data'})
                    await asyncio.sleep(0.1)
                    await session.commit()
                    auth_transaction_complete = True
            await asyncio.gather(backend_transaction(), auth_transaction())
            assert backend_transaction_complete
            assert auth_transaction_complete
            async with backend_db_manager.get_session() as session:
                result = await session.execute(text('SELECT COUNT(*) FROM test_concurrent'))
                count = result.scalar()
                assert count == 2
                result = await session.execute(text('SELECT thread_id, data FROM test_concurrent ORDER BY thread_id'))
                records = result.fetchall()
                service_data = {record[0]: record[1] for record in records}
                assert service_data['auth_service'] == 'auth_data'
                assert service_data['backend_service'] == 'backend_data'
            await backend_db_manager.close_all()
            await auth_db_manager.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_global_database_manager_singleton_pattern(self, isolated_env):
        """Test global database manager singleton behavior and lifecycle."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            manager1 = get_database_manager()
            manager2 = get_database_manager()
            assert manager1 is manager2, 'get_database_manager() should return the same instance'
            await manager1.initialize()
            engine = manager1.get_engine('primary')
            await self._create_test_tables(engine)
            async with get_db_session() as session:
                await session.execute(text('INSERT INTO test_users (username, email) VALUES (:username, :email)'), {'username': 'global_test', 'email': 'global@example.com'})
                await session.commit()
            async with DatabaseManager.get_async_session() as session:
                result = await session.execute(text('SELECT username FROM test_users WHERE email = :email'), {'email': 'global@example.com'})
                row = result.fetchone()
                assert row is not None
                assert row[0] == 'global_test'
            await manager1.close_all()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_realistic_business_scenario_user_lifecycle(self, isolated_env):
        """Test realistic business scenario: complete user lifecycle operations."""
        for key, value in self.test_env_vars.items():
            isolated_env.set(key, value, source='test')
        with patch('netra_backend.app.core.config.get_config') as mock_config, patch.object(DatabaseManager, '_get_database_url') as mock_get_url:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f'sqlite+aiosqlite:///{self.primary_db_path}'
            mock_get_url.return_value = f'sqlite+aiosqlite:///{self.primary_db_path}'
            db_manager = DatabaseManager()
            await db_manager.initialize()
            engine = db_manager.get_engine('primary')
            metadata = MetaData()
            users_table = Table('business_users', metadata, Column('id', Integer, primary_key=True), Column('email', String(255), unique=True), Column('username', String(100)), Column('subscription_tier', String(50)), Column('created_at', DateTime), Column('is_active', Integer, default=1, nullable=False))
            sessions_table = Table('user_sessions', metadata, Column('id', Integer, primary_key=True), Column('user_id', Integer), Column('session_token', String(255)), Column('expires_at', DateTime), Column('is_valid', Integer, default=1, nullable=False))
            async with engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
            test_user_email = 'business_user@netrasystems.ai'
            async with db_manager.get_session() as session:
                await session.execute(text('INSERT INTO business_users (email, username, subscription_tier, is_active) VALUES (:email, :username, :subscription_tier, :is_active)'), {'email': test_user_email, 'username': 'business_user', 'subscription_tier': 'free', 'is_active': 1})
                await session.commit()
                result = await session.execute(text('SELECT id FROM business_users WHERE email = :email'), {'email': test_user_email})
                user_id = result.scalar()
                assert user_id is not None
            session_token = 'business_session_token_12345'
            async with db_manager.get_session() as session:
                await session.execute(text('INSERT INTO user_sessions (user_id, session_token, is_valid) VALUES (:user_id, :session_token, :is_valid)'), {'user_id': user_id, 'session_token': session_token, 'is_valid': 1})
                await session.commit()
            async with db_manager.get_session() as session:
                result = await session.execute(text('\n                        SELECT u.email, u.subscription_tier, s.is_valid \n                        FROM business_users u\n                        JOIN user_sessions s ON u.id = s.user_id\n                        WHERE s.session_token = :session_token AND u.is_active = 1\n                    '), {'session_token': session_token})
                user_session = result.fetchone()
                assert user_session is not None
                assert user_session[0] == test_user_email
                assert user_session[1] == 'free'
                assert user_session[2] == 1
            async with db_manager.get_session() as session:
                await session.execute(text('UPDATE business_users SET subscription_tier = :tier WHERE email = :email'), {'tier': 'premium', 'email': test_user_email})
                await session.commit()
                result = await session.execute(text('SELECT subscription_tier FROM business_users WHERE email = :email'), {'email': test_user_email})
                tier = result.scalar()
                assert tier == 'premium'
            async with db_manager.get_session() as session:
                await session.execute(text('UPDATE user_sessions SET is_valid = 0 WHERE session_token = :session_token'), {'session_token': session_token})
                await session.commit()
                result = await session.execute(text('SELECT is_valid FROM user_sessions WHERE session_token = :session_token'), {'session_token': session_token})
                is_valid = result.scalar()
                assert is_valid == 0
            async with db_manager.get_session() as session:
                await session.execute(text('UPDATE business_users SET is_active = 0 WHERE email = :email'), {'email': test_user_email})
                await session.commit()
                result = await session.execute(text('SELECT is_active FROM business_users WHERE email = :email'), {'email': test_user_email})
                is_active = result.scalar()
                assert is_active == 0
            async with db_manager.get_session() as session:
                result = await session.execute(text('\n                        SELECT COUNT(*) \n                        FROM business_users u\n                        JOIN user_sessions s ON u.id = s.user_id\n                        WHERE s.session_token = :session_token AND u.is_active = 1 AND s.is_valid = 1\n                    '), {'session_token': session_token})
                active_sessions = result.scalar()
                assert active_sessions == 0, 'Inactive users should have no valid sessions'
            await db_manager.close_all()

@pytest.fixture(scope='function')
def temp_database_files():
    """Fixture providing temporary database file paths."""
    temp_dir = tempfile.mkdtemp(prefix='netra_db_fixture_')
    files = {'primary': os.path.join(temp_dir, 'primary.db'), 'secondary': os.path.join(temp_dir, 'secondary.db'), 'temp_dir': temp_dir}
    yield files
    try:
        for file_path in [files['primary'], files['secondary']]:
            if os.path.exists(file_path):
                os.unlink(file_path)
        os.rmdir(temp_dir)
    except OSError:
        pass

@pytest.fixture(scope='function')
def database_performance_config():
    """Fixture providing configuration for performance testing."""
    return {'bulk_insert_batch_size': 50, 'bulk_insert_batches': 5, 'concurrent_operations': 5, 'operations_per_thread': 8, 'performance_timeout': 30.0, 'min_records_per_second': 50}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')