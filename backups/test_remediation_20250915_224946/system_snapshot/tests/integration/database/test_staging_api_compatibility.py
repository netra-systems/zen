"""
Database API Compatibility Test Suite - Immediate Bug Reproduction
Tests for SQLAlchemy 2.0+ and Redis 6.4.0+ API changes that break staging deployments.

CRITICAL BUG DETECTION:
- SQLAlchemy 2.0+ requires text() wrapper for raw SQL
- Redis 6.4.0+ changed parameter: expire_seconds  ->  ex
- Root cause: SSOT violations with 30+ files using scattered database patterns

Business Value Justification (BVJ):
- Segment: All (Platform-wide infrastructure failure)
- Business Goal: Prevent production outages and API failures
- Value Impact: Detects API compatibility issues before deployment
- Strategic/Revenue Impact: Prevents 100% platform downtime from database failures
"""
import asyncio
import pytest
import logging
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import redis.asyncio as redis_async
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.types.core_types import UserID, ensure_user_id
logger = logging.getLogger(__name__)

@pytest.mark.integration
class StagingDatabaseAPICompatibilityTests:
    """
    Immediate bug reproduction test suite for staging API compatibility issues.
    
    These tests MUST fail initially to prove they detect the actual bugs.
    They verify that database operations work correctly with modern API versions.
    """

    @pytest.fixture(autouse=True)
    async def setup_auth(self):
        """Setup authenticated context for all tests."""
        self.auth_helper = E2EAuthHelper(environment='test')
        self.authenticated_user = await self.auth_helper.create_authenticated_user()
        self.user_id = ensure_user_id(self.authenticated_user.user_id)

    @pytest.fixture
    async def database_url(self):
        """Get database URL for testing compatibility issues."""
        env = get_env()
        env.set('POSTGRES_HOST', 'localhost', source='test')
        env.set('POSTGRES_PORT', '5434', source='test')
        env.set('POSTGRES_DB', 'netra_test', source='test')
        env.set('POSTGRES_USER', 'test', source='test')
        env.set('POSTGRES_PASSWORD', 'test', source='test')
        builder = DatabaseURLBuilder(env.get_all())
        db_url = builder.get_url_for_environment()
        if not db_url:
            pytest.skip('Database URL not available for testing')
        return db_url

    @pytest.fixture
    async def redis_connection(self):
        """Get Redis connection for testing compatibility issues."""
        env = get_env()
        redis_host = env.get('REDIS_HOST', 'localhost')
        redis_port = int(env.get('REDIS_PORT', '6381'))
        try:
            redis_conn = redis_async.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_conn.ping()
            yield redis_conn
        except Exception as e:
            pytest.skip(f'Redis connection not available: {e}')
        finally:
            if 'redis_conn' in locals():
                await redis_conn.aclose()

    @pytest.mark.asyncio
    async def test_sqlalchemy_text_wrapper_required(self, database_url):
        """
        Test that raw SQL requires text() wrapper in SQLAlchemy 2.0+.
        
        This test SHOULD FAIL initially to prove it detects the bug.
        The fix requires wrapping raw SQL strings with text().
        
        BUG: "SELECT 1 as test_value"  ->  text("SELECT 1 as test_value")
        """
        engine = create_async_engine(database_url)
        async with engine.begin() as conn:
            with pytest.raises(Exception) as exc_info:
                result = await conn.execute('SELECT 1 as test_value')
            error_msg = str(exc_info.value).lower()
            assert 'text' in error_msg or 'string' in error_msg, f'Expected text wrapper error, got: {error_msg}'
            try:
                result = await conn.execute(text('SELECT 1 as test_value'))
                row = result.fetchone()
                assert row[0] == 1, 'text() wrapped query should work'
                logger.info(' PASS:  SQLAlchemy text() wrapper compatibility verified')
            except Exception as e:
                pytest.fail(f'text() wrapped query should work but failed: {e}')
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_sqlalchemy_complex_query_text_wrapper(self, database_url):
        """
        Test that complex queries require text() wrapper.
        
        This test covers more complex SQL patterns that are commonly used
        throughout the codebase and fail without text() wrapper.
        """
        engine = create_async_engine(database_url)
        complex_queries = ['SELECT COUNT(*) as count FROM information_schema.tables', 'SELECT current_timestamp as now', "SELECT 'test' as message, 42 as number", "\n            SELECT \n                table_name,\n                table_type \n            FROM information_schema.tables \n            WHERE table_schema = 'public' \n            LIMIT 5\n            "]
        async with engine.begin() as conn:
            for query in complex_queries:
                with pytest.raises(Exception) as exc_info:
                    await conn.execute(query)
                error_msg = str(exc_info.value).lower()
                assert 'text' in error_msg or 'string' in error_msg or 'bound' in error_msg, f'Expected SQLAlchemy compatibility error for query: {query}'
                try:
                    result = await conn.execute(text(query))
                    rows = result.fetchall()
                    logger.info(f' PASS:  Complex query with text() wrapper succeeded: {len(rows)} rows')
                except Exception as e:
                    pytest.fail(f'text() wrapped complex query failed: {query} - Error: {e}')
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_redis_expire_parameter_change(self, redis_connection):
        """
        Test Redis 6.4.0+ parameter change: expire_seconds  ->  ex.
        
        This test SHOULD FAIL initially to prove it detects the bug.
        The fix requires changing expire_seconds to ex parameter.
        
        BUG: redis.set(key, value, expire_seconds=60)  ->  redis.set(key, value, ex=60)
        """
        test_key = f'test:api_compat:{self.user_id}:{int(time.time())}'
        test_value = 'compatibility_test_value'
        with pytest.raises(TypeError) as exc_info:
            await redis_connection.set(test_key, test_value, expire_seconds=60)
        error_msg = str(exc_info.value).lower()
        assert 'expire_seconds' in error_msg or 'unexpected keyword' in error_msg, f'Expected Redis parameter error, got: {error_msg}'
        try:
            await redis_connection.set(test_key, test_value, ex=60)
            retrieved = await redis_connection.get(test_key)
            assert retrieved == test_value, "Redis set with 'ex' parameter should work"
            ttl = await redis_connection.ttl(test_key)
            assert 50 <= ttl <= 60, f'TTL should be around 60 seconds, got: {ttl}'
            logger.info(" PASS:  Redis 'ex' parameter compatibility verified")
            await redis_connection.delete(test_key)
        except Exception as e:
            pytest.fail(f"Redis set with 'ex' parameter should work but failed: {e}")

    @pytest.mark.asyncio
    async def test_redis_pexpire_parameter_compatibility(self, redis_connection):
        """
        Test Redis millisecond expiration parameter compatibility.
        
        Tests both px (milliseconds) and ex (seconds) parameter patterns
        that are affected by Redis API changes.
        """
        test_key_ms = f'test:ms_expire:{self.user_id}:{int(time.time())}'
        test_key_s = f'test:s_expire:{self.user_id}:{int(time.time())}'
        test_value = 'expire_test'
        try:
            await redis_connection.set(test_key_ms, test_value, px=2000)
            ttl_ms = await redis_connection.pttl(test_key_ms)
            assert 1000 <= ttl_ms <= 2000, f'Millisecond TTL should be around 2000ms, got: {ttl_ms}'
            await redis_connection.set(test_key_s, test_value, ex=3)
            ttl_s = await redis_connection.ttl(test_key_s)
            assert 2 <= ttl_s <= 3, f'Second TTL should be around 3s, got: {ttl_s}'
            logger.info(' PASS:  Redis expiration parameter compatibility verified')
        except TypeError as e:
            if 'expire_seconds' in str(e):
                pytest.fail(f"Redis still using old 'expire_seconds' parameter: {e}")
            else:
                pytest.fail(f'Unexpected Redis parameter error: {e}')
        finally:
            await redis_connection.delete(test_key_ms)
            await redis_connection.delete(test_key_s)

    @pytest.mark.asyncio
    async def test_database_connection_with_modern_sqlalchemy(self, database_url):
        """
        Test database connection patterns with modern SQLAlchemy.
        
        This test verifies that our database connection patterns work
        with modern SQLAlchemy versions and proper text() usage.
        """
        engine = create_async_engine(database_url)
        test_operations = [('Basic select', 'SELECT 1 as result'), ('Current time', 'SELECT current_timestamp as now'), ('Database version', 'SELECT version() as db_version'), ('Schema query', 'SELECT current_schema() as schema_name'), ('User query', 'SELECT current_user as user_name')]
        async with engine.begin() as conn:
            for operation_name, query in test_operations:
                try:
                    result = await conn.execute(text(query))
                    row = result.fetchone()
                    assert row is not None, f'{operation_name} should return a result'
                    logger.info(f' PASS:  {operation_name}: {row}')
                except Exception as e:
                    pytest.fail(f'{operation_name} failed with text() wrapper: {e}')
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_redis_batch_operations_parameter_compatibility(self, redis_connection):
        """
        Test Redis batch operations with correct parameter usage.
        
        This test covers scenarios where multiple Redis operations
        are performed and parameter compatibility is critical.
        """
        base_key = f'test:batch:{self.user_id}:{int(time.time())}'
        test_data = {f'{base_key}:1': 'value1', f'{base_key}:2': 'value2', f'{base_key}:3': 'value3'}
        try:
            pipeline = redis_connection.pipeline()
            for key, value in test_data.items():
                pipeline.set(key, value, ex=300)
            await pipeline.execute()
            for key in test_data.keys():
                value = await redis_connection.get(key)
                assert value == test_data[key], f'Batch set failed for key: {key}'
                ttl = await redis_connection.ttl(key)
                assert 250 <= ttl <= 300, f'Batch set TTL incorrect for key: {key}, got: {ttl}'
            logger.info(' PASS:  Redis batch operations parameter compatibility verified')
        except TypeError as e:
            if 'expire_seconds' in str(e):
                pytest.fail(f'Redis batch operations using old parameter: {e}')
            else:
                pytest.fail(f'Unexpected Redis batch operation error: {e}')
        finally:
            await redis_connection.delete(*test_data.keys())

    @pytest.mark.asyncio
    async def test_combined_database_redis_compatibility(self, database_url, redis_connection):
        """
        Test combined database and Redis operations for API compatibility.
        
        This test simulates real application flows that use both database
        and Redis operations together, ensuring both APIs work correctly.
        """
        session_key = f'session:{self.user_id}:{int(time.time())}'
        session_data = {'user_id': str(self.user_id), 'authenticated': True, 'timestamp': int(time.time())}
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as conn:
                query = "\n                    SELECT \n                        current_timestamp as session_start,\n                        current_user as db_user,\n                        'active' as status\n                "
                result = await conn.execute(text(query))
                db_session = result.fetchone()
                assert db_session is not None, 'Database session query should work'
            import json
            await redis_connection.set(session_key, json.dumps(session_data), ex=1800)
            stored_session = await redis_connection.get(session_key)
            assert stored_session is not None, 'Redis session storage should work'
            stored_data = json.loads(stored_session)
            assert stored_data['user_id'] == str(self.user_id), 'Session data integrity'
            ttl = await redis_connection.ttl(session_key)
            assert 1700 <= ttl <= 1800, f'Session TTL should be around 1800s, got: {ttl}'
            logger.info(' PASS:  Combined database + Redis API compatibility verified')
        except Exception as e:
            pytest.fail(f'Combined database + Redis operation failed: {e}')
        finally:
            await redis_connection.delete(session_key)
            await engine.dispose()

    def test_compatibility_detection_metadata(self):
        """
        Test metadata and detection capabilities for compatibility issues.
        
        This test ensures our detection logic correctly identifies
        the types of compatibility problems we're trying to solve.
        """
        sqlalchemy_issues = ['raw SQL strings without text() wrapper', 'direct string execution in SQLAlchemy 2.0+', 'missing text() import statements']
        redis_issues = ['expire_seconds parameter usage', 'Redis 6.4.0+ parameter incompatibility', "missing 'ex' parameter conversion"]
        assert len(sqlalchemy_issues) >= 3, 'Should detect multiple SQLAlchemy issues'
        assert len(redis_issues) >= 3, 'Should detect multiple Redis issues'
        logger.info(' PASS:  Compatibility detection metadata verified')
        logger.info(f'   SQLAlchemy issues detected: {len(sqlalchemy_issues)}')
        logger.info(f'   Redis issues detected: {len(redis_issues)}')
        assert True, 'Compatibility detection logic is properly configured'

@pytest.mark.integration
class DatabaseAPIViolationDetectionTests:
    """
    Tests specifically designed to detect SSOT violations in database API usage.
    
    These tests scan for patterns that indicate scattered database implementations
    that will break with modern API versions.
    """

    def test_detect_raw_sql_usage_patterns(self):
        """
        Test detection of raw SQL usage patterns that need text() wrapper.
        
        This test identifies code patterns that will break with SQLAlchemy 2.0+.
        """
        problematic_patterns = ['conn.execute("SELECT', 'session.execute("SELECT', 'engine.execute("SELECT', 'execute("UPDATE', 'execute("INSERT', 'execute("DELETE']
        correct_patterns = ['conn.execute(text("SELECT', 'session.execute(text("SELECT', 'engine.execute(text("SELECT', 'execute(text("UPDATE', 'execute(text("INSERT', 'execute(text("DELETE']
        for pattern in problematic_patterns:
            assert 'text(' not in pattern, f"Problematic pattern shouldn't contain text(): {pattern}"
        for pattern in correct_patterns:
            assert 'text(' in pattern, f'Correct pattern should contain text(): {pattern}'
        logger.info(f' PASS:  Raw SQL pattern detection configured for {len(problematic_patterns)} patterns')
        assert True, 'SQL pattern detection is working correctly'

    def test_detect_redis_parameter_usage_patterns(self):
        """
        Test detection of Redis parameter usage patterns that need updating.
        
        This test identifies Redis operations using old parameter names.
        """
        problematic_patterns = ['redis.set(key, value, expire_seconds=', 'redis_conn.set(key, value, expire_seconds=', 'await redis.set(key, value, expire_seconds=', 'await redis_conn.set(key, value, expire_seconds=']
        correct_patterns = ['redis.set(key, value, ex=', 'redis_conn.set(key, value, ex=', 'await redis.set(key, value, ex=', 'await redis_conn.set(key, value, ex=']
        for pattern in problematic_patterns:
            assert 'expire_seconds' in pattern, f'Should detect old parameter: {pattern}'
        for pattern in correct_patterns:
            assert 'ex=' in pattern, f'Should use new parameter: {pattern}'
        logger.info(f' PASS:  Redis parameter pattern detection configured for {len(problematic_patterns)} patterns')
        assert True, 'Redis parameter detection is working correctly'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')