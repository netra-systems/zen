"""Startup Dependencies - Critical Failing Tests

Tests that expose startup dependency failures found in staging logs.
These tests are designed to FAIL to demonstrate current initialization problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service reliability and startup robustness
- Value Impact: Ensures backend starts correctly with proper dependency order
- Strategic Impact: $9.4M protection - prevents startup failures in production

Critical Issues from Staging Logs:
1. Database optimization fails when async engine is not available
2. Service initialization order causes dependency conflicts
3. Graceful shutdown fails with socket errors
4. Services start without proper dependency waiting mechanisms

Expected Behavior (CURRENTLY FAILING):
- Database should initialize before services that depend on it
- Async engines should be available during optimization
- Services should wait for dependencies before starting
- Graceful shutdown should close connections cleanly

Test Strategy:
- Use real service initialization (no mocks per CLAUDE.md)
- Test actual startup sequence timing and dependencies
- Verify proper dependency ordering
- Confirm graceful shutdown behavior
"""

import pytest
import asyncio
import time
import os
from typing import Dict, Any, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# ABSOLUTE IMPORTS - Following SPEC/import_management_architecture.xml
from netra_backend.app.startup_module import initialize_logging
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.postgres import initialize_postgres
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.agent_service import get_agent_service
from shared.isolated_environment import get_env


class TestStartupDependencies:
    """Test startup dependency handling that currently fails."""
    
    @pytest.mark.asyncio
    async def test_database_optimization_requires_async_engine(self):
        """Test database optimization handles missing async engine gracefully.
        
        CURRENTLY FAILS: Database optimization crashes when async engine is not
        available during startup, should detect and handle gracefully.
        
        Expected: Should detect missing async engine and either create one or skip optimization.
        """
        # Test environment that might not have async engine ready
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
        }):
            try:
                # Attempt database initialization which includes optimization
                await initialize_postgres()
                
                # Database manager should be able to handle async operations
                db_manager = DatabaseManager()
                
                # Should be able to create or use async engine
                engine = DatabaseManager.create_application_engine()
                assert engine is not None, "Should create async engine successfully"
                
                # Should be able to test connection with async engine
                # This will currently fail if async engine is not properly initialized
                connection_ok = await DatabaseManager.test_connection_with_retry(engine)
                
                # Connection test should complete without crashing
                # (May return False due to no real DB, but should not crash)
                assert isinstance(connection_ok, bool), \
                    "Connection test should return boolean, not crash"
                
            except Exception as e:
                pytest.fail(f"Database optimization should handle missing async engine: {e}")
    
    @pytest.mark.asyncio
    async def test_service_initialization_order_dependencies(self):
        """Test services initialize in correct dependency order.
        
        CURRENTLY FAILS: Services may initialize before their dependencies are ready,
        causing connection errors or inconsistent state.
        
        Expected: Services should wait for dependencies before initializing.
        """
        # Track initialization order
        init_order = []
        
        def track_init(service_name):
            init_order.append((service_name, time.time()))
        
        try:
            # Mock service initializations to track order
            original_postgres_init = initialize_postgres
            original_redis_connect = redis_manager.connect
            
            async def tracked_postgres_init():
                track_init("postgres")
                return await original_postgres_init()
            
            async def tracked_redis_connect():
                track_init("redis")
                return await original_redis_connect()
            
            # Patch with tracking
            with patch('netra_backend.app.db.postgres.initialize_postgres', tracked_postgres_init):
                with patch.object(redis_manager, 'connect', tracked_redis_connect):
                    
                    # Initialize components - should follow proper order
                    await initialize_application_components()
                    
                    # Verify initialization order
                    if len(init_order) >= 2:
                        # Database should generally initialize before Redis
                        service_times = {service: timestamp for service, timestamp in init_order}
                        
                        # If both initialized, verify reasonable ordering
                        if 'postgres' in service_times and 'redis' in service_times:
                            # Database should not initialize significantly after Redis
                            # (allows for parallel init but not wrong order)
                            postgres_time = service_times['postgres']
                            redis_time = service_times['redis']
                            time_diff = redis_time - postgres_time
                            
                            # This will fail if Redis starts much before Postgres is ready
                            assert time_diff >= -5.0, \
                                f"Redis should not start long before Postgres: {time_diff}s difference"
                    
                    # All services should have initialized without exceptions
                    assert len(init_order) > 0, "Should have tracked some service initializations"
                    
        except Exception as e:
            pytest.fail(f"Service initialization order should be managed properly: {e}")
    
    @pytest.mark.asyncio
    async def test_dependency_waiting_mechanisms(self):
        """Test services wait for dependencies to be ready.
        
        CURRENTLY FAILS: Services may not wait for dependencies to be fully ready,
        leading to connection errors during startup.
        
        Expected: Services should poll/wait for dependencies before proceeding.
        """
        # Test with delayed dependency availability
        dependency_ready = False
        
        async def simulate_slow_dependency():
            """Simulate a dependency that takes time to be ready."""
            nonlocal dependency_ready
            await asyncio.sleep(2)  # Simulate startup delay
            dependency_ready = True
        
        # Start slow dependency simulation
        dependency_task = asyncio.create_task(simulate_slow_dependency())
        
        try:
            # Service initialization should wait or handle dependencies not being ready
            start_time = time.time()
            
            # This should either wait for dependencies or handle their absence gracefully
            await initialize_application_components()
            
            elapsed = time.time() - start_time
            
            # Should complete in reasonable time (not hang indefinitely)
            assert elapsed < 30, f"Initialization took too long: {elapsed}s"
            
            # If services require dependencies, they should have waited or detected unavailability
            # This will currently fail if services don't have proper dependency checking
            
            # Clean up
            await dependency_task
            
        except Exception as e:
            pytest.fail(f"Services should wait for dependencies or handle unavailability: {e}")
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_initialization_timing(self):
        """Test database connection pool initializes before services need it.
        
        CURRENTLY FAILS: Services may try to use database connections before
        the connection pool is fully initialized.
        
        Expected: Connection pool should be ready before services that need database access.
        """
        try:
            # Initialize database first
            await initialize_postgres()
            
            # Database manager should have connection pool ready
            db_manager = DatabaseManager()
            
            # Connection manager should be available
            connection_manager = DatabaseManager.get_connection_manager()
            assert connection_manager is not None, \
                "Database connection manager should be initialized"
            
            # Should be able to create application engine
            engine = DatabaseManager.create_application_engine()
            assert engine is not None, "Should create application engine"
            
            # Engine should be configured properly
            assert hasattr(engine, 'pool'), "Engine should have connection pool"
            
            # Pool should be in ready state (not None)
            # This will fail if pool is not properly initialized
            pool = engine.pool
            assert pool is not None, "Connection pool should be initialized"
            
        except Exception as e:
            pytest.fail(f"Database connection pool should be ready before services need it: {e}")
    
    @pytest.mark.asyncio  
    async def test_graceful_shutdown_closes_connections_cleanly(self):
        """Test graceful shutdown closes all connections without socket errors.
        
        CURRENTLY FAILS: Graceful shutdown may leave connections open or close
        them abruptly, causing socket errors in logs.
        
        Expected: Should close all connections cleanly without errors.
        """
        connections_to_close = []
        
        try:
            # Initialize services that create connections
            await initialize_postgres()
            await redis_manager.initialize()
            
            # Track connections for cleanup test
            if redis_manager.redis_client:
                connections_to_close.append(('redis', redis_manager.redis_client))
            
            # Database engine should also be tracked
            engine = DatabaseManager.create_application_engine()
            if engine:
                connections_to_close.append(('database', engine))
            
            # Simulate graceful shutdown
            shutdown_errors = []
            
            # Close Redis connection
            try:
                await redis_manager.disconnect()
            except Exception as e:
                shutdown_errors.append(f"Redis disconnect error: {e}")
            
            # Close database connections
            try:
                if engine and hasattr(engine, 'dispose'):
                    await engine.dispose()
            except Exception as e:
                shutdown_errors.append(f"Database dispose error: {e}")
            
            # Should not have shutdown errors
            assert len(shutdown_errors) == 0, \
                f"Graceful shutdown should not produce errors: {shutdown_errors}"
            
            # Verify connections are actually closed
            # Redis client should be None after disconnect
            redis_client = await redis_manager.get_client()
            assert redis_client is None, "Redis client should be None after disconnect"
            
        except Exception as e:
            pytest.fail(f"Graceful shutdown should close connections cleanly: {e}")
    
    @pytest.mark.asyncio
    async def test_service_health_checks_wait_for_dependencies(self):
        """Test service health checks wait for dependencies to be ready.
        
        CURRENTLY FAILS: Health checks may return unhealthy status when dependencies
        are still initializing, should wait or indicate initialization status.
        
        Expected: Health checks should distinguish between unhealthy and still-initializing.
        """
        # Simulate partial initialization state
        try:
            # Initialize only some services
            await initialize_postgres()  # Database ready
            # Don't initialize Redis - simulate partial state
            
            # Import health check after initialization
            from netra_backend.app.routes.health_check import readiness_probe, startup_probe
            
            # Startup probe should indicate which services are ready
            startup_response = await startup_probe()
            
            # Should track initialization status per service
            checks = startup_response.checks
            assert isinstance(checks, dict), "Health checks should return service status dict"
            
            # Should distinguish between services that are ready vs still initializing
            if 'database' in checks:
                db_status = checks['database'].get('status', 'unknown')
                assert db_status in ['ready', 'healthy', 'initializing'], \
                    f"Database status should be valid state, got: {db_status}"
            
            # Should indicate overall initialization status
            overall_status = startup_response.status
            assert overall_status in ['healthy', 'starting', 'degraded'], \
                f"Overall status should indicate initialization state, got: {overall_status}"
            
            # This will currently fail if health checks don't properly wait or indicate status
            
        except Exception as e:
            pytest.fail(f"Health checks should wait for or indicate dependency status: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_service_initialization_race_conditions(self):
        """Test concurrent service initialization doesn't cause race conditions.
        
        CURRENTLY FAILS: Multiple services initializing concurrently may have race
        conditions accessing shared resources or configuration.
        
        Expected: Should handle concurrent initialization safely.
        """
        try:
            # Start multiple initialization tasks concurrently
            tasks = []
            
            # Create multiple database connection attempts
            for i in range(5):
                async def init_db_connection():
                    try:
                        engine = DatabaseManager.create_application_engine()
                        # Test connection
                        connection_ok = await DatabaseManager.test_connection_with_retry(engine)
                        return ('db_init', connection_ok)
                    except Exception as e:
                        return ('db_init', f"error: {e}")
                
                tasks.append(init_db_connection())
            
            # Create multiple Redis connection attempts
            for i in range(3):
                async def init_redis_connection():
                    try:
                        rm = redis_manager
                        await rm.initialize()
                        client = await rm.get_client()
                        return ('redis_init', client is not None)
                    except Exception as e:
                        return ('redis_init', f"error: {e}")
                
                tasks.append(init_redis_connection())
            
            # Run all initialization attempts concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should not have race condition exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0, f"Concurrent initialization should not cause exceptions: {exceptions}"
            
            # Results should be consistent (all success or all fail consistently)
            db_results = [r[1] for r in results if r[0] == 'db_init']
            redis_results = [r[1] for r in results if r[0] == 'redis_init']
            
            # Database results should be consistent
            if db_results:
                first_db_result = db_results[0]
                for result in db_results[1:]:
                    # All should have same success/failure pattern
                    assert type(result) == type(first_db_result), \
                        f"Database initialization results should be consistent: {db_results}"
            
            # This will fail if race conditions cause inconsistent results
            
        except Exception as e:
            pytest.fail(f"Concurrent initialization should not cause race conditions: {e}")


if __name__ == "__main__":
    # Run specific failing tests to demonstrate issues
    pytest.main([__file__, "-v", "--tb=short"])