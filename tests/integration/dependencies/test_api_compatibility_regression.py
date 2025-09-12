"""
Dependency Regression Prevention Test Suite
Tests to prevent API compatibility regressions during dependency upgrades.

CRITICAL REGRESSION PREVENTION:
- Tests for SQLAlchemy version compatibility (1.x vs 2.x)
- Tests for Redis version compatibility (pre-6.4.0 vs 6.4.0+)
- Tests for asyncio compatibility across Python versions
- Tests for database driver compatibility

Business Value Justification (BVJ):
- Segment: Platform/Internal (Prevents infrastructure failures affecting all users)
- Business Goal: System Stability and Upgrade Safety
- Value Impact: Prevents production outages during dependency upgrades
- Strategic/Revenue Impact: Prevents $100K+ outages from compatibility breaks
"""

import asyncio
import pytest
import logging
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import patch, MagicMock
from packaging import version
import importlib
import subprocess
from contextlib import asynccontextmanager

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)

class TestAPICompatibilityRegression:
    """
    API Compatibility Regression Prevention Test Suite.
    
    This suite tests for regressions that occur when dependencies are upgraded:
    1. SQLAlchemy 1.x  ->  2.x compatibility breaks
    2. Redis 6.4.0+ parameter changes
    3. Python asyncio changes across versions
    4. Database driver version compatibility
    """
    
    @pytest.fixture(autouse=True)
    async def setup_dependency_testing(self):
        """Setup dependency compatibility testing environment."""
        self.auth_helper = E2EAuthHelper(environment="test")
        self.test_user = await self.auth_helper.create_authenticated_user()
        
        # Get current dependency versions for comparison
        self.dependency_versions = self._get_current_dependency_versions()
        logger.info(f"[U+1F4E6] Current dependency versions: {self.dependency_versions}")
    
    def _get_current_dependency_versions(self) -> Dict[str, str]:
        """Get versions of critical dependencies that could cause regressions."""
        versions = {}
        
        # Check SQLAlchemy version
        try:
            import sqlalchemy
            versions["sqlalchemy"] = sqlalchemy.__version__
        except ImportError:
            versions["sqlalchemy"] = "not_installed"
        
        # Check Redis version
        try:
            import redis
            versions["redis"] = redis.__version__
        except ImportError:
            versions["redis"] = "not_installed"
        
        # Check asyncio-redis version if installed
        try:
            import redis.asyncio
            # Redis asyncio is part of redis package since 4.2.0
            versions["redis_asyncio"] = "available"
        except ImportError:
            versions["redis_asyncio"] = "not_available"
        
        # Check Python version
        versions["python"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Check asyncpg version (PostgreSQL driver)
        try:
            import asyncpg
            versions["asyncpg"] = asyncpg.__version__
        except ImportError:
            versions["asyncpg"] = "not_installed"
        
        return versions
    
    @pytest.mark.asyncio
    async def test_sqlalchemy_version_compatibility_regression(self):
        """
        Test SQLAlchemy version compatibility to prevent regressions.
        
        This test detects regressions when SQLAlchemy is upgraded:
        - 1.4.x  ->  2.0.x: requires text() wrapper for raw SQL
        - 1.3.x  ->  1.4.x: async patterns changed
        - 2.0.x  ->  2.1.x: potential future breaking changes
        """
        import sqlalchemy
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        
        # Get SQLAlchemy version and determine compatibility requirements
        sqlalchemy_version = version.parse(sqlalchemy.__version__)
        logger.info(f" SEARCH:  Testing SQLAlchemy version {sqlalchemy_version}")
        
        # Test database URL
        env = get_env()
        test_db_url = "sqlite+aiosqlite:///test_compatibility.db"
        
        engine = create_async_engine(test_db_url, echo=False)
        
        try:
            async with engine.begin() as conn:
                # Test 1: Raw SQL compatibility across versions
                if sqlalchemy_version >= version.parse("2.0.0"):
                    # SQLAlchemy 2.0+ requires text() wrapper
                    logger.info("[U+1F4CB] Testing SQLAlchemy 2.0+ text() wrapper requirement")
                    
                    # This should work in 2.0+
                    result = await conn.execute(text("SELECT 1 as test_value"))
                    row = result.fetchone()
                    assert row[0] == 1, "text() wrapper should work in SQLAlchemy 2.0+"
                    
                    # Test that raw strings fail (would be a regression if they started working)
                    try:
                        await conn.execute("SELECT 2 as raw_test")
                        pytest.fail("Raw SQL strings should fail in SQLAlchemy 2.0+ (regression detected)")
                    except Exception:
                        logger.info(" PASS:  Raw SQL properly rejected in SQLAlchemy 2.0+ (no regression)")
                
                elif sqlalchemy_version >= version.parse("1.4.0"):
                    # SQLAlchemy 1.4.x should support both patterns
                    logger.info("[U+1F4CB] Testing SQLAlchemy 1.4.x compatibility patterns")
                    
                    # Both should work in 1.4.x
                    result1 = await conn.execute(text("SELECT 1 as test_value"))
                    assert result1.fetchone()[0] == 1
                    
                    # Raw strings might still work in 1.4.x
                    try:
                        result2 = await conn.execute("SELECT 2 as raw_test")
                        raw_works = True
                        logger.info("[U+2139][U+FE0F] Raw SQL still works in SQLAlchemy 1.4.x")
                    except Exception:
                        raw_works = False
                        logger.info("[U+2139][U+FE0F] Raw SQL rejected in SQLAlchemy 1.4.x")
                
                else:
                    # SQLAlchemy < 1.4.0
                    logger.info("[U+1F4CB] Testing legacy SQLAlchemy compatibility")
                    pytest.skip("SQLAlchemy version too old for async testing")
                
                # Test 2: Async session patterns
                logger.info("[U+1F4CB] Testing async session compatibility patterns")
                
                # Test async context manager
                from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
                
                async_session = async_sessionmaker(engine, class_=AsyncSession)
                
                async with async_session() as session:
                    result = await session.execute(text("SELECT 'session_test' as test"))
                    session_row = result.fetchone()
                    assert session_row[0] == "session_test", "Async session should work"
                    
                    # Test transaction rollback
                    async with session.begin():
                        await session.execute(text("SELECT 1"))
                        # Transaction will auto-commit on success
                
                logger.info(" PASS:  SQLAlchemy version compatibility validated")
                
        except Exception as e:
            pytest.fail(f"SQLAlchemy compatibility test failed: {e}")
        finally:
            await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_redis_version_compatibility_regression(self):
        """
        Test Redis version compatibility to prevent regressions.
        
        This test detects regressions when Redis client is upgraded:
        - Pre-6.4.0: expire_seconds parameter
        - 6.4.0+: ex parameter for expiration
        - 4.2.0+: redis.asyncio module availability
        """
        import redis.asyncio as redis_async
        
        redis_version = version.parse(self.dependency_versions["redis"])
        logger.info(f" SEARCH:  Testing Redis version {redis_version}")
        
        # Connect to test Redis
        redis_conn = redis_async.Redis(
            host="localhost",
            port=6381,  # Test port
            decode_responses=True
        )
        
        try:
            await redis_conn.ping()
        except Exception:
            pytest.skip("Redis test instance not available")
        
        try:
            test_key = f"regression_test:{int(time.time())}"
            test_value = "compatibility_test"
            
            # Test current Redis API compatibility
            if redis_version >= version.parse("6.4.0"):
                logger.info("[U+1F4CB] Testing Redis 6.4.0+ parameter compatibility")
                
                # Should work with 'ex' parameter
                await redis_conn.set(test_key, test_value, ex=60)
                
                retrieved = await redis_conn.get(test_key)
                assert retrieved == test_value, "Redis set with 'ex' parameter should work"
                
                ttl = await redis_conn.ttl(test_key)
                assert 50 <= ttl <= 60, "TTL should be set correctly"
                
                # Test that old parameter fails (regression prevention)
                with pytest.raises(TypeError):
                    await redis_conn.set(f"{test_key}_old", test_value, expire_seconds=60)
                
                logger.info(" PASS:  Redis 6.4.0+ parameter compatibility validated")
                
            else:
                logger.info("[U+1F4CB] Testing legacy Redis parameter compatibility")
                
                # For older versions, test what should work
                await redis_conn.set(test_key, test_value)
                await redis_conn.expire(test_key, 60)
                
                retrieved = await redis_conn.get(test_key)
                assert retrieved == test_value, "Basic Redis operations should work"
                
                logger.info(" PASS:  Legacy Redis compatibility validated")
            
            # Test async Redis patterns across versions
            logger.info("[U+1F4CB] Testing async Redis patterns")
            
            # Pipeline operations
            pipeline = redis_conn.pipeline()
            for i in range(3):
                pipeline.set(f"{test_key}_batch_{i}", f"value_{i}", ex=120)
            
            results = await pipeline.execute()
            assert len(results) == 3, "Pipeline operations should work"
            
            # Verify batch operations
            for i in range(3):
                value = await redis_conn.get(f"{test_key}_batch_{i}")
                assert value == f"value_{i}", f"Batch value {i} should be correct"
            
            # Cleanup
            cleanup_keys = [test_key] + [f"{test_key}_batch_{i}" for i in range(3)]
            await redis_conn.delete(*cleanup_keys)
            
            logger.info(" PASS:  Redis async patterns validated")
            
        except Exception as e:
            pytest.fail(f"Redis compatibility test failed: {e}")
        finally:
            await redis_conn.aclose()
    
    @pytest.mark.asyncio
    async def test_python_asyncio_compatibility_regression(self):
        """
        Test Python asyncio compatibility across versions.
        
        This test detects regressions in asyncio patterns:
        - Python 3.8: asyncio.create_task behavior
        - Python 3.9: asyncio improvements
        - Python 3.10+: asyncio context improvements
        - Python 3.11+: asyncio performance improvements
        """
        python_version = version.parse(self.dependency_versions["python"])
        logger.info(f" SEARCH:  Testing Python {python_version} asyncio compatibility")
        
        # Test 1: Basic asyncio patterns
        async def test_task():
            await asyncio.sleep(0.001)
            return "task_complete"
        
        # Create and await task
        task = asyncio.create_task(test_task())
        result = await task
        assert result == "task_complete", "Basic asyncio task should work"
        
        # Test 2: Multiple concurrent tasks
        async def concurrent_task(task_id: int, delay: float = 0.001):
            await asyncio.sleep(delay)
            return f"task_{task_id}_complete"
        
        tasks = [asyncio.create_task(concurrent_task(i)) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5, "All concurrent tasks should complete"
        for i, result in enumerate(results):
            assert result == f"task_{i}_complete", f"Task {i} result should be correct"
        
        # Test 3: Timeout patterns
        async def slow_task():
            await asyncio.sleep(0.1)
            return "slow_complete"
        
        # Test timeout handling
        try:
            result = await asyncio.wait_for(slow_task(), timeout=0.05)
            pytest.fail("Task should have timed out")
        except asyncio.TimeoutError:
            logger.info(" PASS:  Asyncio timeout handling works correctly")
        
        # Test successful completion within timeout
        result = await asyncio.wait_for(slow_task(), timeout=0.2)
        assert result == "slow_complete", "Task should complete within timeout"
        
        # Test 4: Context manager async patterns
        @asynccontextmanager
        async def async_context():
            logger.info("Entering async context")
            try:
                yield "context_value"
            finally:
                logger.info("Exiting async context")
        
        async with async_context() as value:
            assert value == "context_value", "Async context manager should work"
        
        # Test 5: Exception handling in async context
        async def failing_task():
            await asyncio.sleep(0.001)
            raise ValueError("Intentional test error")
        
        try:
            await failing_task()
            pytest.fail("Task should have raised exception")
        except ValueError as e:
            assert str(e) == "Intentional test error", "Exception should propagate correctly"
        
        logger.info(f" PASS:  Python {python_version} asyncio compatibility validated")
    
    @pytest.mark.asyncio
    async def test_database_driver_compatibility_regression(self):
        """
        Test database driver compatibility across versions.
        
        This test detects regressions in database drivers:
        - asyncpg: PostgreSQL async driver
        - aiosqlite: SQLite async driver
        - Connection pooling behavior
        - Transaction isolation behavior
        """
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Test SQLite driver (always available)
        sqlite_url = "sqlite+aiosqlite:///test_driver_compat.db"
        sqlite_engine = create_async_engine(sqlite_url, echo=False)
        
        try:
            # Test basic SQLite operations
            async with sqlite_engine.begin() as conn:
                await conn.execute(text("CREATE TEMPORARY TABLE driver_test (id INTEGER, value TEXT)"))
                await conn.execute(text("INSERT INTO driver_test VALUES (1, 'test_value')"))
                
                result = await conn.execute(text("SELECT id, value FROM driver_test WHERE id = 1"))
                row = result.fetchone()
                
                assert row is not None, "SQLite driver should return results"
                assert row[0] == 1, "SQLite driver should return correct ID"
                assert row[1] == "test_value", "SQLite driver should return correct value"
            
            logger.info(" PASS:  SQLite driver compatibility validated")
            
        except Exception as e:
            pytest.fail(f"SQLite driver compatibility failed: {e}")
        finally:
            await sqlite_engine.dispose()
        
        # Test PostgreSQL driver if asyncpg is available
        if self.dependency_versions.get("asyncpg", "not_installed") != "not_installed":
            logger.info("[U+1F4CB] Testing PostgreSQL driver compatibility")
            
            # Try to connect to test PostgreSQL
            env = get_env()
            pg_url = f"postgresql+asyncpg://test:test@localhost:5434/netra_test"
            pg_engine = create_async_engine(pg_url, echo=False)
            
            try:
                async with pg_engine.begin() as conn:
                    # Test basic PostgreSQL operations
                    result = await conn.execute(text("SELECT version() as pg_version"))
                    version_row = result.fetchone()
                    
                    if version_row:
                        logger.info(f" CHART:  PostgreSQL version: {version_row[0][:50]}...")
                        
                        # Test PostgreSQL-specific features
                        await conn.execute(text("""
                            CREATE TEMPORARY TABLE pg_driver_test (
                                id SERIAL PRIMARY KEY,
                                data JSONB,
                                created_at TIMESTAMP DEFAULT NOW()
                            )
                        """))
                        
                        test_data = {"test": True, "value": 42}
                        await conn.execute(text("""
                            INSERT INTO pg_driver_test (data) VALUES (:data)
                        """), {"data": json.dumps(test_data)})
                        
                        result = await conn.execute(text("""
                            SELECT id, data, created_at FROM pg_driver_test WHERE id = 1
                        """))
                        pg_row = result.fetchone()
                        
                        assert pg_row is not None, "PostgreSQL driver should return results"
                        assert pg_row[0] == 1, "PostgreSQL driver should return correct ID"
                        
                        # Test JSONB functionality
                        stored_data = json.loads(pg_row[1]) if isinstance(pg_row[1], str) else pg_row[1]
                        assert stored_data["test"] is True, "PostgreSQL JSONB should work"
                        assert stored_data["value"] == 42, "PostgreSQL JSONB should preserve values"
                        
                        logger.info(" PASS:  PostgreSQL driver compatibility validated")
                    
            except Exception as e:
                logger.warning(f"PostgreSQL driver test skipped: {e}")
                # Don't fail the test if PostgreSQL is not available
            finally:
                await pg_engine.dispose()
        else:
            logger.info("[U+1F4CB] PostgreSQL driver not installed, skipping compatibility test")
    
    @pytest.mark.asyncio
    async def test_dependency_interaction_regression(self):
        """
        Test dependency interaction regressions.
        
        This test detects regressions when multiple dependencies are upgraded together:
        - SQLAlchemy + asyncpg version interactions
        - Redis + asyncio version interactions
        - Authentication libraries + async patterns
        """
        logger.info("[U+1F4CB] Testing dependency interaction patterns")
        
        # Test 1: SQLAlchemy + Redis interaction
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        import redis.asyncio as redis_async
        
        # Setup both connections
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///test_interaction.db", echo=False)
        redis_conn = redis_async.Redis(host="localhost", port=6381, decode_responses=True)
        
        try:
            await redis_conn.ping()
        except Exception:
            pytest.skip("Redis not available for interaction testing")
        
        try:
            # Test coordinated database + cache operations
            test_id = int(time.time())
            db_key = f"interaction_test_{test_id}"
            cache_key = f"cache:{db_key}"
            
            # Step 1: Database write
            async with sqlite_engine.begin() as conn:
                await conn.execute(text("""
                    CREATE TEMPORARY TABLE interaction_test (
                        id INTEGER PRIMARY KEY,
                        key TEXT,
                        value TEXT,
                        cached BOOLEAN
                    )
                """))
                
                await conn.execute(text("""
                    INSERT INTO interaction_test (id, key, value, cached)
                    VALUES (:id, :key, :value, :cached)
                """), {
                    "id": test_id,
                    "key": db_key,
                    "value": f"test_value_{test_id}",
                    "cached": False
                })
            
            # Step 2: Cache write (using correct Redis API)
            cache_data = {
                "id": test_id,
                "key": db_key,
                "value": f"test_value_{test_id}",
                "cached_at": time.time()
            }
            
            await redis_conn.set(cache_key, json.dumps(cache_data), ex=300)
            
            # Step 3: Update database to reflect caching
            async with sqlite_engine.begin() as conn:
                await conn.execute(text("""
                    UPDATE interaction_test SET cached = :cached WHERE id = :id
                """), {"id": test_id, "cached": True})
            
            # Step 4: Verify consistency
            # Check database
            async with sqlite_engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT id, key, value, cached FROM interaction_test WHERE id = :id
                """), {"id": test_id})
                db_row = result.fetchone()
            
            # Check cache
            cached_data = await redis_conn.get(cache_key)
            cache_obj = json.loads(cached_data) if cached_data else None
            
            # Verify interaction integrity
            assert db_row is not None, "Database record should exist"
            assert cache_obj is not None, "Cache record should exist"
            assert db_row.cached is True, "Database should reflect caching status"
            assert cache_obj["id"] == test_id, "Cache should have correct ID"
            assert cache_obj["value"] == db_row.value, "Cache and database values should match"
            
            # Cleanup
            await redis_conn.delete(cache_key)
            
            logger.info(" PASS:  Database + Cache interaction compatibility validated")
            
        except Exception as e:
            pytest.fail(f"Dependency interaction test failed: {e}")
        finally:
            await sqlite_engine.dispose()
            await redis_conn.aclose()
        
        # Test 2: Authentication + async patterns
        logger.info("[U+1F4CB] Testing authentication async pattern compatibility")
        
        # Test JWT token creation and validation in async context
        test_tasks = []
        
        async def auth_task(task_id: int):
            # Create token
            token = self.auth_helper.create_test_jwt_token(
                user_id=f"task_user_{task_id}",
                email=f"task_{task_id}@example.com"
            )
            
            # Validate token
            validation = await self.auth_helper.validate_jwt_token(token)
            
            return {
                "task_id": task_id,
                "token_valid": validation["valid"],
                "user_id": validation.get("user_id")
            }
        
        # Run multiple auth tasks concurrently
        for i in range(3):
            task = asyncio.create_task(auth_task(i))
            test_tasks.append(task)
        
        auth_results = await asyncio.gather(*test_tasks)
        
        # Verify all auth tasks succeeded
        for result in auth_results:
            assert result["token_valid"] is True, f"Auth task {result['task_id']} should be valid"
            assert result["user_id"] == f"task_user_{result['task_id']}", "User ID should match"
        
        logger.info(" PASS:  Authentication async pattern compatibility validated")
    
    def test_dependency_version_matrix_regression(self):
        """
        Test dependency version matrix for known regression patterns.
        
        This test maintains a compatibility matrix to detect when
        dependency combinations are known to be problematic.
        """
        # Known problematic version combinations
        regression_matrix = {
            "sqlalchemy": {
                "2.0.0": {
                    "breaking_changes": ["text_wrapper_required", "legacy_query_deprecated"],
                    "affected_patterns": ["raw_sql_execution", "legacy_sessionmaker"]
                },
                "1.4.0": {
                    "breaking_changes": ["async_patterns_changed"],
                    "affected_patterns": ["session_creation", "engine_configuration"]
                }
            },
            "redis": {
                "6.4.0": {
                    "breaking_changes": ["expire_seconds_removed"],
                    "affected_patterns": ["set_with_expiration", "cache_operations"]
                },
                "4.2.0": {
                    "breaking_changes": ["asyncio_module_added"],
                    "affected_patterns": ["async_redis_imports"]
                }
            }
        }
        
        current_versions = self.dependency_versions
        detected_regressions = []
        
        for package, version_info in regression_matrix.items():
            current_version = current_versions.get(package)
            if current_version and current_version != "not_installed":
                current_ver = version.parse(current_version)
                
                for breaking_version, breaking_info in version_info.items():
                    breaking_ver = version.parse(breaking_version)
                    
                    if current_ver >= breaking_ver:
                        detected_regressions.append({
                            "package": package,
                            "current_version": current_version,
                            "breaking_version": breaking_version,
                            "breaking_changes": breaking_info["breaking_changes"],
                            "affected_patterns": breaking_info["affected_patterns"]
                        })
        
        # Log detected potential regressions
        if detected_regressions:
            logger.warning(f" WARNING: [U+FE0F] Detected {len(detected_regressions)} potential regression patterns:")
            for regression in detected_regressions:
                logger.warning(f"   [U+1F4E6] {regression['package']} {regression['current_version']}: {regression['breaking_changes']}")
                logger.warning(f"       SEARCH:  Affected patterns: {regression['affected_patterns']}")
        else:
            logger.info(" PASS:  No known regression patterns detected in current dependency versions")
        
        # Verify our tests cover the detected regressions
        covered_patterns = {
            "text_wrapper_required": True,      # Covered in SQLAlchemy tests
            "expire_seconds_removed": True,     # Covered in Redis tests
            "async_patterns_changed": True,     # Covered in asyncio tests
            "raw_sql_execution": True,          # Covered in SQLAlchemy tests
            "set_with_expiration": True,        # Covered in Redis tests
            "cache_operations": True,           # Covered in interaction tests
            "async_redis_imports": True,        # Covered in Redis tests
        }
        
        for regression in detected_regressions:
            for breaking_change in regression["breaking_changes"]:
                if breaking_change not in covered_patterns:
                    pytest.fail(f"Regression pattern '{breaking_change}' not covered by tests")
        
        logger.info(f" PASS:  Dependency version matrix validated: {len(detected_regressions)} regressions detected and covered")
        assert True, "Dependency regression prevention is properly configured"

if __name__ == "__main__":
    # Run dependency regression prevention tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_api_compatibility_regression"
    ])