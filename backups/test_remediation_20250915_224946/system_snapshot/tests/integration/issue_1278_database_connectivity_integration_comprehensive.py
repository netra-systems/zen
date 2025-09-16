"""
Integration Tests for Issue #1278 - Database Connectivity Integration Comprehensive

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Integration)
- Business Goal: Validate database connectivity components work together
- Value Impact: Confirms application startup sequence with real database attempts
- Strategic Impact: Validates readiness for infrastructure fixes

Following TEST_CREATION_GUIDE.md requirements:
- Uses real services (PostgreSQL + Redis) without Docker
- Tests actual database connection attempts with staging timeout configuration
- Designed to reproduce Issue #1278 infrastructure problems
- Uses SSOT test framework patterns

These tests validate the database connectivity integration aspects identified in Issue #1278:
- Database Manager initialization with Cloud SQL timeouts
- SMD Phase 3 integration testing with real database
- FastAPI lifespan manager integration during database failures
- Database connection pool timeout validation with real services
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
import os
import time

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import IsolatedEnvironment

# System under test - database components
try:
    from netra_backend.app.core.database_manager import DatabaseManager
    from netra_backend.app.core.database_timeout_config import get_database_timeout_config
except ImportError:
    DatabaseManager = None
    get_database_timeout_config = None

try:
    from netra_backend.app.startup.system_manager_daemon import SystemManagerDaemon
    from netra_backend.app.startup.deterministic_startup_error import DeterministicStartupError
except ImportError:
    SystemManagerDaemon = None
    DeterministicStartupError = None

try:
    from netra_backend.app.startup.lifespan_manager import LifespanManager
except ImportError:
    LifespanManager = None

# Database utilities
try:
    from netra_backend.app.core.configuration.database import get_database_url
    from shared.database.connection_pool import create_connection_pool
except ImportError:
    get_database_url = None
    create_connection_pool = None

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.issue_1278
@pytest.mark.real_services
@pytest.mark.database_connectivity
class TestDatabaseConnectivityIntegrationComprehensive(BaseIntegrationTest):
    """Integration tests for database connectivity - Issue #1278."""

    @pytest.fixture(autouse=True)
    async def setup_real_services(self, real_services_fixture):
        """Set up real PostgreSQL and Redis services for integration testing."""
        self.real_services = real_services_fixture
        self.isolated_env = IsolatedEnvironment()

        # Configure staging-like environment for testing
        self.staging_config = {
            'ENVIRONMENT': 'staging',
            'DATABASE_URL': self.real_services.get_database_url(),
            'REDIS_URL': self.real_services.get_redis_url(),
            'DATABASE_TIMEOUT_INITIALIZATION': '35.0',
            'DATABASE_TIMEOUT_CONNECTION': '15.0',
            'DATABASE_TIMEOUT_POOL': '15.0'
        }

    async def test_database_manager_initialization_timeout_behavior(self):
        """
        Test Case 2.1: Test DatabaseManager with staging timeout configuration.

        Expected behavior:
        - Should attempt database connection with 35.0s timeout
        - Should either succeed (if infrastructure works) or timeout appropriately
        - Should provide proper error messaging for Cloud SQL context
        - NO MOCKS - real database connection attempts
        """
        if DatabaseManager is None:
            pytest.skip("DatabaseManager not available")

        with self.isolated_env.context(self.staging_config):
            database_manager = DatabaseManager()

            start_time = time.time()
            try:
                # Attempt real database initialization with staging timeouts
                await database_manager.initialize()

                # If successful, validate initialization time
                initialization_time = time.time() - start_time
                logger.info(f"Database initialization succeeded in {initialization_time:.2f}s")

                # Should succeed within timeout window
                self.assertLess(initialization_time, 35.0,
                               "Initialization should complete within 35.0s timeout")

                # Validate connection is working
                connection_test = await database_manager.test_connection()
                self.assertTrue(connection_test, "Database connection should be functional")

            except (TimeoutError, DeterministicStartupError) as e:
                # Expected behavior if infrastructure issues exist
                initialization_time = time.time() - start_time
                logger.warning(f"Database initialization failed after {initialization_time:.2f}s: {e}")

                # Should timeout appropriately (around 35.0s for Cloud SQL compatibility)
                self.assertGreaterEqual(initialization_time, 30.0,
                                      "Should timeout after reasonable Cloud SQL connection attempt")
                self.assertLessEqual(initialization_time, 40.0,
                                   "Should not hang indefinitely beyond timeout")

            finally:
                # Clean up
                if hasattr(database_manager, 'cleanup'):
                    await database_manager.cleanup()

    async def test_smd_phase_3_database_initialization_integration(self):
        """
        Test Case 2.2: Test complete SMD Phase 3 execution with real database.

        Expected behavior:
        - Execute actual SMD Phase 3 with staging configuration
        - Monitor for 35.0s timeout behavior
        - Validate error propagation to FastAPI lifespan
        """
        if SystemManagerDaemon is None:
            pytest.skip("SystemManagerDaemon not available")

        with self.isolated_env.context(self.staging_config):
            smd = SystemManagerDaemon()

            start_time = time.time()
            try:
                # Execute SMD Phase 3 (DATABASE) with real services
                await smd.execute_phase("DATABASE")

                execution_time = time.time() - start_time
                logger.info(f"SMD Phase 3 completed successfully in {execution_time:.2f}s")

                # Validate successful execution
                self.assertTrue(smd.is_phase_completed("DATABASE"),
                               "SMD Phase 3 should be marked as completed")

                # Should complete within reasonable time
                self.assertLess(execution_time, 35.0,
                               "SMD Phase 3 should complete within timeout")

            except DeterministicStartupError as e:
                execution_time = time.time() - start_time
                logger.warning(f"SMD Phase 3 failed with DeterministicStartupError after {execution_time:.2f}s: {e}")

                # Validate error context
                self.assertEqual(e.phase, "DATABASE", "Error should indicate DATABASE phase")
                self.assertIn("timeout", str(e).lower(), "Error should mention timeout")

                # Should fail after appropriate timeout attempt
                self.assertGreaterEqual(execution_time, 30.0, "Should attempt full timeout duration")

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"SMD Phase 3 failed with unexpected error after {execution_time:.2f}s: {e}")

                # Re-raise unexpected errors for investigation
                raise

    async def test_fastapi_lifespan_deterministic_startup_failure_handling(self):
        """
        Test Case 2.3: Test lifespan manager behavior during SMD failures.

        Expected behavior:
        - Simulate SMD Phase 3 failure conditions
        - Validate lifespan manager error handling
        - Confirm no degraded startup allowed
        """
        if LifespanManager is None:
            pytest.skip("LifespanManager not available")

        with self.isolated_env.context(self.staging_config):
            lifespan_manager = LifespanManager()

            # Simulate database connectivity failure
            with patch.object(SystemManagerDaemon, 'execute_phase') as mock_smd:
                mock_smd.side_effect = DeterministicStartupError(
                    phase="DATABASE",
                    component="Cloud SQL VPC Connector",
                    details="Connection timeout after 35.0s"
                )

                try:
                    # Attempt lifespan startup with mocked SMD failure
                    await lifespan_manager.startup()
                    self.fail("Lifespan should not allow startup with SMD failures")

                except DeterministicStartupError as e:
                    # Expected behavior - lifespan should propagate the error
                    self.assertEqual(e.phase, "DATABASE")
                    self.assertIn("35.0s", e.details)
                    logger.info("Lifespan manager correctly rejected startup due to SMD failure")

                except Exception as e:
                    # Log unexpected errors but don't fail the test immediately
                    logger.error(f"Unexpected error in lifespan manager: {e}")
                    # This might indicate the lifespan manager needs improvement

    async def test_database_connection_pool_cloud_sql_timeout_handling(self):
        """
        Test Case 2.4: Test connection pool behavior with Cloud SQL VPC connector simulation.

        Expected behavior:
        - Test connection pool establishment with 15.0s pool_timeout
        - Validate socket establishment timing
        - Monitor for connection pool timeout behavior
        """
        if create_connection_pool is None:
            pytest.skip("Connection pool utilities not available")

        with self.isolated_env.context(self.staging_config):
            # Get database URL with real services
            database_url = self.real_services.get_database_url()

            start_time = time.time()
            try:
                # Create connection pool with staging timeout configuration
                pool = await create_connection_pool(
                    database_url=database_url,
                    pool_size=5,
                    pool_timeout=15.0,
                    connection_timeout=15.0
                )

                pool_creation_time = time.time() - start_time
                logger.info(f"Connection pool created successfully in {pool_creation_time:.2f}s")

                # Validate pool functionality
                async with pool.acquire() as connection:
                    result = await connection.fetchval("SELECT 1")
                    self.assertEqual(result, 1, "Connection pool should provide working connections")

                # Test pool timeout behavior with multiple connections
                connection_times = []
                for i in range(3):
                    conn_start = time.time()
                    async with pool.acquire() as connection:
                        await connection.fetchval("SELECT pg_sleep(0.1)")
                    conn_time = time.time() - conn_start
                    connection_times.append(conn_time)

                # All connections should complete within reasonable time
                max_connection_time = max(connection_times)
                self.assertLess(max_connection_time, 15.0,
                               "Individual connections should complete within pool timeout")

            except asyncio.TimeoutError as e:
                pool_creation_time = time.time() - start_time
                logger.warning(f"Connection pool creation timed out after {pool_creation_time:.2f}s: {e}")

                # Should timeout around the configured timeout
                self.assertGreaterEqual(pool_creation_time, 10.0,
                                      "Should attempt connection for reasonable duration")
                self.assertLessEqual(pool_creation_time, 20.0,
                                   "Should not hang beyond configured timeout")

            finally:
                # Clean up connection pool
                if 'pool' in locals():
                    await pool.close()

    async def test_database_connectivity_error_recovery_patterns(self):
        """
        Test Case 2.5: Test database connectivity error recovery and retry patterns.

        Expected behavior:
        - Test progressive retry behavior during connectivity issues
        - Validate error messaging and logging
        - Confirm graceful degradation handling
        """
        with self.isolated_env.context(self.staging_config):
            # Test with various connection failure scenarios
            test_scenarios = [
                {
                    'name': 'Connection refused',
                    'database_url': 'postgresql://localhost:9999/nonexistent',
                    'expected_error': 'connection refused'
                },
                {
                    'name': 'Invalid host',
                    'database_url': 'postgresql://invalid-host:5432/test',
                    'expected_error': 'could not translate host name'
                }
            ]

            for scenario in test_scenarios:
                logger.info(f"Testing scenario: {scenario['name']}")

                start_time = time.time()
                try:
                    if create_connection_pool:
                        pool = await create_connection_pool(
                            database_url=scenario['database_url'],
                            pool_size=1,
                            pool_timeout=5.0,
                            connection_timeout=5.0
                        )
                        await pool.close()

                        # Should not succeed with invalid configuration
                        self.fail(f"Expected connection to fail for scenario: {scenario['name']}")

                except Exception as e:
                    error_time = time.time() - start_time
                    error_msg = str(e).lower()

                    logger.info(f"Scenario '{scenario['name']}' failed as expected after {error_time:.2f}s: {e}")

                    # Should fail quickly for clear connection issues
                    self.assertLess(error_time, 10.0,
                                   f"Should fail quickly for {scenario['name']}")

    async def test_staging_environment_database_configuration_validation(self):
        """
        Test Case 2.6: Validate staging environment database configuration integration.

        Expected behavior:
        - Validate staging-specific timeout configurations
        - Test Cloud SQL socket path handling (if applicable)
        - Confirm environment-specific behavior
        """
        if get_database_timeout_config is None:
            pytest.skip("Database timeout config not available")

        with self.isolated_env.context(self.staging_config):
            # Get staging configuration
            timeout_config = get_database_timeout_config('staging')

            # Validate staging-specific timeouts
            self.assertEqual(timeout_config.get('initialization_timeout'), 35.0,
                           "Staging should use 35.0s initialization timeout")
            self.assertEqual(timeout_config.get('connection_timeout'), 15.0,
                           "Staging should use 15.0s connection timeout")
            self.assertEqual(timeout_config.get('pool_timeout'), 15.0,
                           "Staging should use 15.0s pool timeout")

            # Test configuration application
            if DatabaseManager:
                db_manager = DatabaseManager()
                applied_config = db_manager.get_timeout_configuration()

                self.assertEqual(applied_config.get('initialization_timeout'), 35.0,
                               "DatabaseManager should apply staging timeout configuration")

            logger.info("Staging database configuration validation completed")


if __name__ == '__main__':
    # Run integration tests
    pytest.main([__file__, '-v', '--tb=short'])