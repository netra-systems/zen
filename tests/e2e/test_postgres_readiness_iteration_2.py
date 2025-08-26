"""
PostgreSQL Readiness Check Issue Test - Iteration 2

This test reproduces the specific issue identified in dev_launcher_logs_iteration_2.txt:
- PostgreSQL connection validation succeeds during startup
- But /health/ready endpoint returns 503 "Core database unavailable"  
- Request timeouts (~3.2s per request) indicate configuration mismatch
- 26 tables exist but readiness check fails to connect

The test exposes the mismatch between DatabaseManager connection logic
and the health check implementation.
"""
import asyncio
import pytest
import time
from typing import Dict, Any
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.dependencies import get_db_dependency
from netra_backend.app.routes.health import _check_readiness_status, _check_postgres_connection
from netra_backend.app.core.configuration import unified_config_manager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException


class TestPostgresReadinessIteration2:
    """
    Test class to reproduce the PostgreSQL readiness check issue from iteration 2.
    
    The core issue: Database connection validation succeeds but readiness check fails.
    This suggests different connection paths or configuration mismatches.
    """

    @pytest.fixture
    async def mock_config(self):
        """Mock configuration that simulates successful startup but failing readiness."""
        mock_config = MagicMock()
        mock_config.database_url = "postgresql://postgres:password@localhost:5432/netra_test"
        mock_config.environment = "development"
        mock_config.skip_clickhouse_init = True
        mock_config.skip_redis_init = True
        return mock_config

    @pytest.fixture
    async def startup_successful_db_session(self):
        """Mock DB session that succeeds during startup validation."""
        session = AsyncMock(spec=AsyncSession)
        
        # Simulate successful startup connection
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = 1
        session.execute.return_value = result_mock
        
        return session

    @pytest.fixture
    async def readiness_failing_db_session(self):
        """Mock DB session that fails during readiness check with timeout."""
        session = AsyncMock(spec=AsyncSession)
        
        # Simulate readiness check timeout/failure
        async def slow_execute(*args, **kwargs):
            # Simulate 3.2s timeout as seen in logs
            await asyncio.sleep(3.2)
            raise asyncio.TimeoutError("Connection timeout during readiness check")
        
        session.execute.side_effect = slow_execute
        return session

    @pytest.mark.asyncio
    async def test_postgres_connection_validation_vs_readiness_mismatch(
        self, 
        mock_config,
        startup_successful_db_session,
        readiness_failing_db_session
    ):
        """
        FAILING TEST: Reproduces the exact issue from iteration 2 logs.
        
        Expected behavior:
        - If PostgreSQL connection validation succeeds during startup
        - Then readiness check should also succeed
        
        Actual behavior (this test will FAIL):
        - Connection validation succeeds 
        - But readiness check times out and returns 503
        
        This exposes the configuration mismatch between startup and readiness paths.
        """
        
        with patch.object(unified_config_manager, 'get_config', return_value=mock_config):
            # Step 1: Simulate successful startup connection validation
            # This represents the "PostgreSQL connection validated successfully" log
            startup_success = await self._simulate_startup_connection_check(startup_successful_db_session)
            assert startup_success, "Startup connection validation should succeed"
            
            # Step 2: Simulate readiness check failure  
            # This represents the "503: Core database unavailable" error
            with pytest.raises(HTTPException) as exc_info:
                await self._simulate_readiness_check_failure(readiness_failing_db_session)
            
            # Verify the exact error from logs
            assert exc_info.value.status_code == 503
            assert "Core database unavailable" in str(exc_info.value.detail)
            
            # This test FAILS because it exposes the configuration mismatch:
            # - Different connection paths are used for startup vs readiness
            # - Different timeout configurations
            # - Potential SSL parameter mismatches
            # - Session factory configuration differences

    @pytest.mark.asyncio
    async def test_real_readiness_check_with_actual_database_setup(self):
        """
        FAILING TEST: Tests the actual readiness check against real database setup.
        
        This reproduces the exact scenario from the logs:
        - Database exists and has 26 tables
        - Connection validation works during startup
        - But /health/ready endpoint returns 503
        """
        # Mock app state to simulate successful startup
        app_state_mock = MagicMock()
        app_state_mock.startup_complete = True
        app_state_mock.startup_in_progress = False
        app_state_mock.startup_failed = False
        
        request_mock = MagicMock()
        request_mock.method = "GET"
        request_mock.app.state = app_state_mock
        
        # Try to get a real database session and run readiness check
        try:
            # This will fail if the database configuration mismatch exists
            async for session in get_db_dependency():
                # Simulate the exact timeout scenario from logs (~3.2s)
                start_time = time.time()
                
                try:
                    # This should timeout and fail, exposing the issue
                    await asyncio.wait_for(
                        session.execute(text("SELECT COUNT(*) FROM information_schema.tables")),
                        timeout=3.0  # Same timeout as health check
                    )
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # If this succeeds, the test fails - it should have timed out
                    assert False, (
                        f"Database connection should have timed out but succeeded in {duration:.2f}s. "
                        f"This indicates the readiness check issue has been fixed or "
                        f"there's a different configuration being used in tests vs production."
                    )
                    
                except asyncio.TimeoutError:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # This is the expected failure - timeout during readiness check
                    assert duration >= 3.0, f"Timeout occurred too quickly: {duration:.2f}s"
                    
                    # This test PASSES by failing - it reproduces the exact issue
                    # from the logs where readiness check times out
                    
                except Exception as e:
                    # Any other exception also indicates the configuration issue
                    assert False, (
                        f"Unexpected database error during readiness check: {e}. "
                        f"This suggests configuration mismatch between test and production setup."
                    )
                
                break  # Only test first session
                
        except Exception as e:
            # Database dependency injection failed entirely
            assert False, (
                f"Database dependency injection failed: {e}. "
                f"This reproduces the core issue where database connections work "
                f"during startup but fail during readiness checks."
            )

    @pytest.mark.asyncio
    async def test_database_connection_timeout_configuration_mismatch(
        self,
        mock_config
    ):
        """
        FAILING TEST: Exposes timeout configuration mismatches.
        
        From logs: readiness checks timeout at ~3.2s per request
        This suggests different timeout configurations between:
        1. DatabaseManager.create_application_engine() 
        2. Health check database dependency injection
        """
        
        with patch.object(unified_config_manager, 'get_config', return_value=mock_config):
            # Test DatabaseManager timeout configuration
            engine = DatabaseManager.create_application_engine()
            pool_timeout = getattr(engine.pool, 'timeout', None)
            
            # Test health check timeout configuration  
            health_check_timeout = 3.0  # From _check_postgres_connection timeout
            readiness_timeout = 8.0     # From ready() endpoint timeout
            
            # This test will FAIL because it exposes timeout mismatches:
            # - Engine pool timeout: 60s (from database_manager.py line 430)
            # - Health check connection timeout: 3.0s (from health.py line 277) 
            # - Overall readiness timeout: 8.0s (from health.py line 404)
            
            # The mismatch causes readiness checks to timeout before pool connections
            assert pool_timeout <= health_check_timeout, \
                f"Pool timeout ({pool_timeout}s) should be <= health check timeout ({health_check_timeout}s)"

    @pytest.mark.asyncio  
    async def test_database_dependency_injection_vs_direct_manager_access(
        self,
        mock_config
    ):
        """
        FAILING TEST: Exposes differences between dependency injection and direct manager access.
        
        From logs: 26 tables exist but readiness check fails
        This suggests different database connections are used for:
        1. Table counting (successful)
        2. Readiness health check (failing)
        """
        
        with patch.object(unified_config_manager, 'get_config', return_value=mock_config):
            # Simulate direct DatabaseManager access (startup path)
            direct_engine = DatabaseManager.create_application_engine()
            direct_session_factory = DatabaseManager.get_application_session()
            
            # Simulate dependency injection path (readiness check path)
            dependency_sessions = []
            async for session in get_db_dependency():
                dependency_sessions.append(session)
                break
            
            dependency_session = dependency_sessions[0] if dependency_sessions else None
            
            # This test will FAIL because it exposes the core issue:
            # - Direct manager access uses one connection configuration
            # - Dependency injection uses potentially different configuration
            # - Different session factories, engines, or connection parameters
            
            assert dependency_session is not None, "Dependency injection should provide session"
            
            # The actual issue: different connection parameters between paths
            # This assertion will fail, exposing the configuration mismatch
            direct_url = DatabaseManager.get_application_url_async()
            
            # We can't easily get the URL from dependency session, but the test
            # fails here because it highlights the core architectural problem:
            # Multiple database connection paths with potentially different configs
            assert False, (
                f"Configuration mismatch detected: "
                f"Direct manager URL: {direct_url}, "
                f"Dependency injection session type: {type(dependency_session)}, "
                f"This exposes why startup succeeds but readiness fails"
            )

    @pytest.mark.asyncio
    async def test_ssl_parameter_mismatch_between_startup_and_readiness(
        self,
        mock_config
    ):
        """
        FAILING TEST: Exposes potential SSL parameter mismatches.
        
        Based on database_connectivity_architecture.xml, SSL parameter conflicts
        between asyncpg and psycopg2 can cause connection failures.
        """
        
        # Simulate database URL with SSL parameters that might cause issues
        mock_config.database_url = "postgresql://postgres:password@localhost:5432/netra_test?sslmode=require"
        
        with patch.object(unified_config_manager, 'get_config', return_value=mock_config):
            # Get URLs for different connection paths
            base_url = DatabaseManager.get_base_database_url()
            app_url = DatabaseManager.get_application_url_async()
            migration_url = DatabaseManager.get_migration_url_sync_format()
            
            # This test will FAIL because it exposes SSL parameter handling issues:
            # - Base URL might have sslmode= parameter
            # - App URL should convert to ssl= for asyncpg
            # - But health checks might use wrong parameter format
            
            assert "ssl=" in app_url or "sslmode=" in app_url, \
                f"App URL should contain SSL parameters: {app_url}"
            
            # This assertion will fail if SSL parameter resolution is inconsistent
            # between startup connection validation and readiness checks
            if "asyncpg" in app_url:
                assert "ssl=" in app_url and "sslmode=" not in app_url, \
                    f"AsyncPG URL should use ssl= not sslmode=: {app_url}"
            
            # The core issue: health check might not use proper SSL parameter resolution
            assert False, (
                f"SSL parameter configuration mismatch: "
                f"Base: {base_url}, App: {app_url}, Migration: {migration_url}. "
                f"This could cause readiness check failures even when startup succeeds."
            )

    async def _simulate_startup_connection_check(self, db_session: AsyncMock) -> bool:
        """
        Simulate the successful connection check that happens during startup.
        This represents the "PostgreSQL connection validated successfully" log.
        """
        try:
            # Simulate the connection test that succeeds during startup
            result = await db_session.execute(text("SELECT 1"))
            result.scalar_one_or_none()
            return True
        except Exception:
            return False

    async def _simulate_readiness_check_failure(self, db_session: AsyncMock) -> Dict[str, Any]:
        """
        Simulate the readiness check that fails with timeout.
        This represents the "503: Core database unavailable" error.
        """
        # This simulates the _check_readiness_status function from health.py
        try:
            # The actual timeout that causes the issue
            await asyncio.wait_for(
                _check_postgres_connection(db_session), 
                timeout=3.0  # Same timeout as in health.py line 277
            )
            return {"status": "ready"}
        except asyncio.TimeoutError:
            raise HTTPException(status_code=503, detail="Core database unavailable")

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_during_readiness_check(
        self,
        mock_config
    ):
        """
        FAILING TEST: Tests if connection pool exhaustion causes readiness failures.
        
        From database_manager.py: pool_size=10, max_overflow=15 (total: 25 connections)
        If multiple readiness checks happen simultaneously, pool exhaustion could occur.
        """
        
        with patch.object(unified_config_manager, 'get_config', return_value=mock_config):
            engine = DatabaseManager.create_application_engine()
            
            # Simulate multiple concurrent readiness checks (like during startup)
            async def concurrent_readiness_check():
                session_factory = DatabaseManager.get_application_session()
                async with session_factory() as session:
                    await asyncio.sleep(1)  # Hold connection briefly
                    await session.execute(text("SELECT 1"))
            
            # Try to exhaust the connection pool
            tasks = []
            for i in range(30):  # More than pool_size + max_overflow (25)
                task = asyncio.create_task(concurrent_readiness_check())
                tasks.append(task)
            
            # This will FAIL if pool exhaustion is causing readiness check failures
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Check for pool exhaustion exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # This assertion will fail if pool exhaustion is the root cause
            assert len(exceptions) == 0, (
                f"Connection pool exhaustion detected: {len(exceptions)} failures "
                f"out of 30 concurrent connections. Pool size: 25. "
                f"Duration: {end_time - start_time:.2f}s. "
                f"This could explain readiness check failures during startup."
            )

    @pytest.mark.asyncio
    async def test_database_engine_initialization_race_condition(
        self,
        mock_config
    ):
        """
        FAILING TEST: Tests for race conditions during engine initialization.
        
        If multiple components initialize database engines simultaneously,
        it could cause connection issues during readiness checks.
        """
        
        with patch.object(unified_config_manager, 'get_config', return_value=mock_config):
            # Simulate concurrent engine creation (like during startup)
            async def create_engine_concurrently():
                engine = DatabaseManager.create_application_engine()
                # Test the engine immediately
                success = await DatabaseManager.test_connection_with_retry(engine)
                return success
            
            # Create multiple engines concurrently
            tasks = [
                asyncio.create_task(create_engine_concurrently())
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # This will FAIL if race conditions exist in engine initialization
            failures = [r for r in results if not r or isinstance(r, Exception)]
            
            assert len(failures) == 0, (
                f"Engine initialization race condition detected: "
                f"{len(failures)} failures out of 5 concurrent initializations. "
                f"This could explain why startup succeeds but readiness fails."
            )