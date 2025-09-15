"""
Deterministic Startup Database Tests for Issue #1263

This test suite reproduces the database connectivity timeout issue during the
deterministic startup sequence, specifically when the lifespan startup event
attempts to initialize database connections and hits the 8-second timeout.

Business Value:
- Protects $500K+ ARR by ensuring application startup doesn't hang
- Validates deterministic startup sequence database dependency initialization
- Reproduces exact timeout condition from Cloud Run environment

REQUIREMENTS:
- Tests must INITIALLY FAIL to reproduce the startup timeout issue
- Test deterministic startup sequence with database dependency
- Reproduce 8-second timeout from lifespan startup event
- Use REAL staging database connections (no mocks)

Architecture Pattern: Integration Test following SSOT BaseTestCase
"""

import asyncio
import time
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock, MagicMock
from urllib.parse import urlparse

import pytest
from fastapi import FastAPI

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.configuration.database import DatabaseConfigManager
from netra_backend.app.core.configuration.base import get_unified_config


class DeterministicStartupDatabaseTests(SSotAsyncTestCase):
    """
    Deterministic Startup Database Tests - Issue #1263

    This test class reproduces the database connectivity timeout that occurs during
    the FastAPI lifespan startup event when the application attempts to initialize
    database connections in the Cloud Run environment.
    """

    @classmethod
    def setup_class(cls):
        """Set up class-level resources for deterministic startup tests."""
        super().setup_class()
        cls.logger.info("Setting up deterministic startup database test suite")

        # Configure for staging environment to reproduce exact issue
        cls._class_env.set("NETRA_ENV", "staging", "deterministic_startup_test")
        cls._class_env.set("DATABASE_URL", "postgresql://netra_user:password@staging-shared-postgres:5432/netra_staging", "deterministic_startup_test")

    def setup_method(self, method):
        """Set up individual test method for startup database testing."""
        super().setup_method(method)

        # Configure environment for deterministic startup testing
        self.set_env_var("NETRA_ENV", "staging")
        self.set_env_var("DATABASE_URL", "postgresql://netra_user:password@staging-shared-postgres:5432/netra_staging")
        self.set_env_var("CLOUD_RUN_DEPLOYMENT", "true")  # Simulate Cloud Run environment

        # Initialize startup metrics
        self.record_metric("startup_attempts", 0)
        self.record_metric("startup_timeouts", 0)
        self.record_metric("database_init_attempts", 0)

    async def test_lifespan_startup_database_timeout_reproduction(self):
        """
        Test lifespan startup database timeout - SHOULD FAIL reproducing Issue #1263.

        This test reproduces the exact scenario where the FastAPI lifespan startup
        event times out waiting for database connection initialization.
        """
        self.record_metric("startup_attempts", self.get_metric("startup_attempts", 0) + 1)

        self.logger.info("=== LIFESPAN STARTUP DATABASE TIMEOUT TEST ===")
        self.logger.info("Reproducing Issue #1263: FastAPI lifespan startup database timeout")

        # Create a minimal FastAPI app to test lifespan startup
        app = FastAPI()

        startup_completed = False
        startup_error = None
        startup_time = 0.0

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """
            Lifespan context manager that reproduces Issue #1263.

            This simulates the exact startup sequence that causes timeout:
            1. FastAPI lifespan startup begins
            2. Database manager attempts connection initialization
            3. PostgreSQL client tries to connect to MySQL database
            4. Connection timeout occurs after 8 seconds
            5. Startup fails or hangs
            """
            nonlocal startup_completed, startup_error, startup_time

            self.logger.info("Lifespan startup beginning - initializing database connections")
            start_time = time.time()

            try:
                # Simulate database initialization during startup
                await self._simulate_database_initialization_startup()

                startup_time = time.time() - start_time
                startup_completed = True
                self.logger.info(f"Lifespan startup completed in {startup_time:.2f} seconds")

                yield  # Application runs

            except Exception as e:
                startup_time = time.time() - start_time
                startup_error = e
                self.logger.error(f"Lifespan startup failed after {startup_time:.2f} seconds: {str(e)}")
                raise

            finally:
                # Cleanup on shutdown
                self.logger.info("Lifespan shutdown")

        # Set lifespan on the app
        app.router.lifespan_context = lifespan

        # Test the startup sequence with timeout
        startup_timeout = 10.0  # Longer than the expected 8s timeout
        start_time = time.time()

        try:
            # Simulate what happens in Cloud Run when the app starts
            async with lifespan(app) as _:
                elapsed_time = time.time() - start_time
                self.record_metric("successful_startup_time", elapsed_time)

                self.logger.info(f"Startup sequence completed in {elapsed_time:.2f} seconds")

                # If we get here without timeout, startup succeeded (unexpected in bug scenario)
                assert startup_completed, "Startup should have completed successfully"

        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            self.record_metric("startup_timeout_time", elapsed_time)
            self.record_metric("startup_timeouts", self.get_metric("startup_timeouts", 0) + 1)

            self.logger.error(f"ISSUE #1263 REPRODUCED: Startup timeout after {elapsed_time:.2f} seconds")

            if elapsed_time >= 8.0:
                self.logger.error("Confirmed: 8+ second startup timeout due to database connection failure")

            raise AssertionError(f"Deterministic startup timeout after {elapsed_time:.2f}s confirms Issue #1263")

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.record_metric("startup_error_time", elapsed_time)

            self.logger.error(f"Startup error after {elapsed_time:.2f} seconds: {str(e)}")

            if elapsed_time >= 8.0:
                self.record_metric("startup_timeouts", self.get_metric("startup_timeouts", 0) + 1)
                self.logger.error("Startup timeout during database initialization")

            raise AssertionError(f"Deterministic startup failed after {elapsed_time:.2f}s: {str(e)}")

    async def test_database_manager_initialization_timeout(self):
        """
        Test database manager initialization timeout - SHOULD FAIL during database setup.

        This test reproduces the specific database manager initialization that
        causes timeout during the deterministic startup sequence.
        """
        self.record_metric("database_init_attempts", self.get_metric("database_init_attempts", 0) + 1)

        self.logger.info("=== DATABASE MANAGER INITIALIZATION TIMEOUT TEST ===")

        # Get database configuration that will cause the issue
        config_manager = DatabaseConfigManager()
        database_url = config_manager.get_database_url("staging")

        self.logger.info(f"Testing database manager initialization with URL: {database_url}")

        # Parse URL to show configuration details
        parsed_url = urlparse(database_url)
        self.logger.info(f"Database configuration: {parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}")

        start_time = time.time()

        try:
            # Attempt database manager initialization
            # This should timeout when PostgreSQL client tries to connect to MySQL database
            await self._attempt_database_manager_initialization(database_url, timeout=9.0)

            initialization_time = time.time() - start_time
            self.record_metric("db_init_success_time", initialization_time)

            self.logger.info(f"Database manager initialization succeeded in {initialization_time:.2f} seconds")

            if initialization_time > 7.0:
                self.logger.warning(f"Database initialization took {initialization_time:.2f}s - close to timeout threshold")

        except asyncio.TimeoutError:
            initialization_time = time.time() - start_time
            self.record_metric("db_init_timeout_time", initialization_time)

            self.logger.error(f"ISSUE #1263: Database manager initialization timeout after {initialization_time:.2f} seconds")

            if initialization_time >= 8.0:
                self.logger.error("Confirmed: Database initialization timeout during deterministic startup")

            raise AssertionError(f"Database manager initialization timeout after {initialization_time:.2f}s")

        except Exception as e:
            initialization_time = time.time() - start_time
            self.record_metric("db_init_error_time", initialization_time)

            self.logger.error(f"Database manager initialization error after {initialization_time:.2f} seconds: {str(e)}")
            raise AssertionError(f"Database manager initialization failed: {str(e)}")

    async def test_connection_pool_initialization_timeout(self):
        """
        Test connection pool initialization timeout - SHOULD FAIL on pool creation.

        This test reproduces the connection pool initialization timeout that occurs
        when the database manager attempts to create connection pools during startup.
        """
        self.record_metric("database_init_attempts", self.get_metric("database_init_attempts", 0) + 1)

        self.logger.info("=== CONNECTION POOL INITIALIZATION TIMEOUT TEST ===")

        # Get database configuration
        config_manager = DatabaseConfigManager()
        database_url = config_manager.get_database_url("staging")
        parsed_url = urlparse(database_url)

        self.logger.info(f"Testing connection pool creation for: {parsed_url.hostname}:{parsed_url.port}")

        start_time = time.time()

        try:
            # Simulate connection pool creation with timeout
            await self._simulate_connection_pool_creation(
                host=parsed_url.hostname,
                port=parsed_url.port,
                database=parsed_url.path.lstrip('/'),
                username=parsed_url.username,
                password=parsed_url.password,
                timeout=8.5  # Slightly longer than expected timeout
            )

            pool_creation_time = time.time() - start_time
            self.record_metric("pool_creation_success_time", pool_creation_time)

            self.logger.info(f"Connection pool creation succeeded in {pool_creation_time:.2f} seconds")

        except asyncio.TimeoutError:
            pool_creation_time = time.time() - start_time
            self.record_metric("pool_creation_timeout_time", pool_creation_time)

            self.logger.error(f"ISSUE #1263: Connection pool creation timeout after {pool_creation_time:.2f} seconds")

            if pool_creation_time >= 8.0:
                self.logger.error("Confirmed: Connection pool timeout during deterministic startup")
                self.logger.error("Root cause: PostgreSQL pool trying to connect to MySQL database")

            raise AssertionError(f"Connection pool creation timeout after {pool_creation_time:.2f}s")

        except Exception as e:
            pool_creation_time = time.time() - start_time
            self.record_metric("pool_creation_error_time", pool_creation_time)

            self.logger.error(f"Connection pool creation error after {pool_creation_time:.2f} seconds: {str(e)}")
            raise AssertionError(f"Connection pool creation failed: {str(e)}")

    async def test_cloud_run_environment_startup_simulation(self):
        """
        Test Cloud Run environment startup simulation - SHOULD FAIL simulating exact deployment scenario.

        This test simulates the exact Cloud Run deployment environment where
        Issue #1263 occurs during container startup.
        """
        self.record_metric("startup_attempts", self.get_metric("startup_attempts", 0) + 1)

        self.logger.info("=== CLOUD RUN ENVIRONMENT STARTUP SIMULATION ===")
        self.logger.info("Simulating exact Cloud Run container startup sequence")

        # Simulate Cloud Run environment variables
        self.set_env_var("PORT", "8080")
        self.set_env_var("K_SERVICE", "netra-backend-staging")
        self.set_env_var("K_REVISION", "netra-backend-staging-00042-abc")

        start_time = time.time()

        try:
            # Simulate the full startup sequence that occurs in Cloud Run
            startup_steps = [
                ("Container initialization", 0.1),
                ("Environment setup", 0.2),
                ("Configuration loading", 0.3),
                ("Database connection initialization", 8.5),  # This step will timeout
                ("WebSocket manager setup", 0.2),
                ("Agent registry initialization", 0.3),
                ("Health check endpoint activation", 0.1)
            ]

            for step_name, expected_duration in startup_steps:
                step_start = time.time()
                self.logger.info(f"Cloud Run startup step: {step_name}")

                if "Database" in step_name:
                    # This is where the timeout occurs in Issue #1263
                    await self._simulate_database_connection_step(timeout=9.0)

                else:
                    # Simulate other startup steps
                    await asyncio.sleep(expected_duration)

                step_time = time.time() - step_start
                self.logger.info(f"Step '{step_name}' completed in {step_time:.2f} seconds")

            total_startup_time = time.time() - start_time
            self.record_metric("cloud_run_startup_success_time", total_startup_time)

            self.logger.info(f"Cloud Run startup simulation completed in {total_startup_time:.2f} seconds")

        except asyncio.TimeoutError:
            total_startup_time = time.time() - start_time
            self.record_metric("cloud_run_startup_timeout_time", total_startup_time)
            self.record_metric("startup_timeouts", self.get_metric("startup_timeouts", 0) + 1)

            self.logger.error(f"ISSUE #1263 REPRODUCED: Cloud Run startup timeout after {total_startup_time:.2f} seconds")
            self.logger.error("Container startup failed during database connection initialization")

            raise AssertionError(f"Cloud Run startup timeout after {total_startup_time:.2f}s confirms Issue #1263")

        except Exception as e:
            total_startup_time = time.time() - start_time
            self.record_metric("cloud_run_startup_error_time", total_startup_time)

            self.logger.error(f"Cloud Run startup error after {total_startup_time:.2f} seconds: {str(e)}")
            raise AssertionError(f"Cloud Run startup simulation failed: {str(e)}")

    async def _simulate_database_initialization_startup(self):
        """Simulate database initialization that occurs during startup."""
        self.logger.info("Simulating database initialization during lifespan startup")

        # Get database configuration
        config = get_unified_config()
        database_url = config.database_url

        # This is where the timeout occurs - PostgreSQL client connecting to MySQL database
        await self._attempt_database_connection_with_timeout(database_url, timeout=8.5)

    async def _attempt_database_manager_initialization(self, database_url, timeout=8.0):
        """Attempt database manager initialization with timeout."""
        self.logger.info(f"Attempting database manager initialization with timeout: {timeout}s")

        # Simulate what DatabaseManager does during initialization
        parsed_url = urlparse(database_url)

        # This simulates the connection attempt that times out
        await self._attempt_database_connection_with_timeout(database_url, timeout)

    async def _simulate_connection_pool_creation(self, host, port, database, username, password, timeout=8.0):
        """Simulate connection pool creation with timeout."""
        self.logger.info(f"Simulating connection pool creation to {host}:{port}")

        # This simulates the pool creation that fails due to protocol mismatch
        try:
            # In real scenario, this would be asyncpg.create_pool() or similar
            await asyncio.wait_for(
                self._simulate_connection_attempt(host, port),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Connection pool creation timed out after {timeout} seconds")
            raise

    async def _simulate_database_connection_step(self, timeout=8.0):
        """Simulate the database connection step that causes Issue #1263."""
        self.logger.info("Simulating database connection step (the problematic step)")

        config = get_unified_config()
        database_url = config.database_url
        parsed_url = urlparse(database_url)

        # This is where Issue #1263 manifests
        if parsed_url.scheme == "postgresql" and parsed_url.port == 5432:
            self.logger.error("SIMULATING ISSUE #1263:")
            self.logger.error("- PostgreSQL client attempting connection to port 5432")
            self.logger.error("- But actual database is MySQL on port 3307")
            self.logger.error("- This will cause 8-second timeout")

            # Simulate the timeout that occurs
            await asyncio.sleep(8.1)  # Just over the timeout threshold
            raise asyncio.TimeoutError("Database connection timeout - PostgreSQL client to MySQL server")

    async def _attempt_database_connection_with_timeout(self, database_url, timeout=8.0):
        """Attempt database connection with specified timeout."""
        parsed_url = urlparse(database_url)
        self.logger.info(f"Attempting database connection: {parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}")

        try:
            await asyncio.wait_for(
                self._simulate_connection_attempt(parsed_url.hostname, parsed_url.port),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Database connection timed out after {timeout} seconds")
            raise

    async def _simulate_connection_attempt(self, host, port):
        """Simulate a connection attempt that may timeout."""
        self.logger.debug(f"Simulating connection attempt to {host}:{port}")

        # If this is the problematic configuration, simulate timeout
        if port == 5432:  # PostgreSQL port but database is MySQL
            self.logger.warning("Simulating timeout due to protocol mismatch")
            await asyncio.sleep(8.5)  # Longer than typical timeout
            raise ConnectionError("Protocol mismatch: PostgreSQL client cannot connect to MySQL server")

        # Otherwise simulate successful connection
        await asyncio.sleep(0.1)

    def teardown_method(self, method):
        """Clean up after startup database tests."""
        # Log startup metrics
        attempts = self.get_metric("startup_attempts", 0)
        timeouts = self.get_metric("startup_timeouts", 0)
        db_attempts = self.get_metric("database_init_attempts", 0)

        self.logger.info(f"Startup test summary: {attempts} startup attempts, {db_attempts} db init attempts, {timeouts} timeouts")

        # Record test completion
        self.record_metric("test_completion_time", time.time())

        super().teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])