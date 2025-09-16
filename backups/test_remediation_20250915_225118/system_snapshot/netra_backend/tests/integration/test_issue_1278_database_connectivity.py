"""
Test Database Infrastructure Connectivity - Issue #1278

Integration tests for database connectivity that should FAIL when
infrastructure is unavailable, demonstrating Issue #1278.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Infrastructure Validation
- Value Impact: Ensure database infrastructure issues are detected
- Strategic Impact: Validate that tests properly detect infrastructure failures

CRITICAL: These tests are designed to FAIL when database infrastructure
is unavailable, which reproduces Issue #1278. Tests that pass indicate
proper database connectivity.
"""

import pytest
import asyncio
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Database imports
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
from netra_backend.app.core.configuration.database import DatabaseConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError


class TestDatabaseInfrastructureConnectivity(SSotAsyncTestCase):
    """
    Integration tests for database infrastructure connectivity.

    These tests attempt real database connections and should FAIL
    when infrastructure is unavailable (reproducing Issue #1278).
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Setup test environment for staging database
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("TESTING", "true")

        # These should point to staging infrastructure for Issue #1278 reproduction
        self.set_env_var("POSTGRES_HOST", "10.52.0.3")  # Internal GCP VPC IP
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_DB", "netra_staging")
        self.set_env_var("POSTGRES_USER", "netra_api")
        # Password would come from secrets in real staging

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_postgresql_connectivity_direct(self):
        """
        Test direct PostgreSQL connectivity to staging infrastructure.

        This should FAIL when VPC connectivity issues exist (Issue #1278).
        When it fails, it demonstrates the infrastructure connectivity problem.
        """
        config = DatabaseConfig()

        # Build connection URL for staging database
        from shared.database_url_builder import DatabaseURLBuilder
        builder = DatabaseURLBuilder(self.get_env().as_dict())

        try:
            # Get database URL
            database_url = builder.build_url()

            # Format for asyncpg driver
            database_url = builder.format_url_for_driver(database_url, 'asyncpg')

            self.record_metric("connection_url_built", True)

            # Create engine with realistic timeout for infrastructure testing
            engine = create_async_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    "command_timeout": 60,  # Issue #1278: Staging needs longer timeouts
                    "server_settings": {
                        "jit": "off",
                    },
                }
            )

            self.record_metric("engine_created", True)

            # Attempt actual connection with timeout
            async with engine.begin() as conn:
                # Simple query to validate connectivity
                result = await conn.execute(text("SELECT 1 as test_connection"))
                row = result.fetchone()

                self.assertEqual(row[0], 1)
                self.record_metric("database_query_successful", True)

            await engine.dispose()
            self.record_metric("connection_test", "PASSED")

        except (OperationalError, SQLTimeoutError, ConnectionError, OSError) as e:
            # These are EXPECTED failures for Issue #1278
            self.record_metric("infrastructure_failure", str(e))
            self.record_metric("connection_test", "FAILED_AS_EXPECTED")

            # Log the specific infrastructure error
            if "timeout" in str(e).lower():
                self.record_metric("failure_type", "timeout")
            elif "connection refused" in str(e).lower():
                self.record_metric("failure_type", "connection_refused")
            elif "host unreachable" in str(e).lower():
                self.record_metric("failure_type", "host_unreachable")
            else:
                self.record_metric("failure_type", "other_infrastructure")

            # Re-raise to make test fail (demonstrating Issue #1278)
            raise AssertionError(f"Database infrastructure connectivity failed: {e}")

        except Exception as e:
            self.record_metric("unexpected_error", str(e))
            raise

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_manager_initialization_with_infrastructure(self):
        """
        Test DatabaseManager initialization with real staging infrastructure.

        This should FAIL when VPC/infrastructure issues prevent connection.
        Demonstrates how application startup fails during Issue #1278.
        """
        try:
            # Get database manager (singleton)
            manager = get_database_manager()

            # Initialize manager (this should connect to real infrastructure)
            await manager.initialize()

            self.record_metric("manager_initialization", "successful")

            # Test engine access (this will fail if infrastructure unavailable)
            engine = manager.get_engine()
            self.assertIsNotNone(engine)

            self.record_metric("engine_access", "successful")

            # Test actual database session (critical test)
            user_context = self.create_test_user_execution_context()

            async with manager.get_session(user_context=user_context) as session:
                # Simple query to validate end-to-end connectivity
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()

                self.assertIsNotNone(version)
                self.record_metric("session_query_successful", True)
                self.record_metric("database_version", str(version)[:50])

            self.record_metric("database_manager_test", "PASSED")

        except (OperationalError, SQLTimeoutError, ConnectionError, OSError) as e:
            # These are EXPECTED failures for Issue #1278
            self.record_metric("manager_infrastructure_failure", str(e))
            self.record_metric("database_manager_test", "FAILED_AS_EXPECTED")

            # Categorize the failure type for Issue #1278 analysis
            error_str = str(e).lower()
            if "timeout" in error_str:
                self.record_metric("manager_failure_type", "timeout")
            elif "connection" in error_str and ("refused" in error_str or "reset" in error_str):
                self.record_metric("manager_failure_type", "connection_refused")
            elif "host" in error_str and "unreachable" in error_str:
                self.record_metric("manager_failure_type", "host_unreachable")
            elif "vpc" in error_str or "network" in error_str:
                self.record_metric("manager_failure_type", "network_infrastructure")
            else:
                self.record_metric("manager_failure_type", "other_database")

            # Re-raise to demonstrate Issue #1278 impact on application startup
            raise AssertionError(f"DatabaseManager failed to initialize due to infrastructure: {e}")

        except Exception as e:
            self.record_metric("manager_unexpected_error", str(e))
            raise

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_health_check_with_infrastructure(self):
        """
        Test database health check against real staging infrastructure.

        This should FAIL when infrastructure is unavailable, showing how
        health checks detect Issue #1278.
        """
        try:
            manager = get_database_manager()

            # Perform health check (this connects to real infrastructure)
            health_result = await manager.health_check()

            self.assertIsInstance(health_result, dict)
            self.record_metric("health_check_completed", True)

            # Check health status
            status = health_result.get('status', 'unknown')

            if status == 'healthy':
                self.record_metric("database_health", "healthy")
                self.record_metric("health_check_test", "PASSED")
            else:
                # Infrastructure is available but database is unhealthy
                self.record_metric("database_health", "unhealthy")
                self.record_metric("health_check_test", "FAILED_UNHEALTHY")
                self.fail(f"Database health check reported unhealthy: {health_result}")

        except (OperationalError, SQLTimeoutError, ConnectionError, OSError) as e:
            # These are EXPECTED failures for Issue #1278
            self.record_metric("health_check_infrastructure_failure", str(e))
            self.record_metric("health_check_test", "FAILED_AS_EXPECTED")

            # Re-raise to demonstrate Issue #1278 impact on health monitoring
            raise AssertionError(f"Health check failed due to infrastructure: {e}")

        except Exception as e:
            self.record_metric("health_check_unexpected_error", str(e))
            raise

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_connectivity_staging(self):
        """
        Test Redis connectivity to staging infrastructure.

        This should FAIL when VPC connectivity issues affect Redis access.
        Redis issues can compound database problems in Issue #1278.
        """
        # Set Redis staging configuration
        self.set_env_var("REDIS_HOST", "10.52.0.2")  # Internal GCP VPC IP
        self.set_env_var("REDIS_PORT", "6379")

        try:
            from netra_backend.app.services.enhanced_redis_manager import RedisManager

            # Initialize Redis manager
            redis_manager = RedisManager()
            await redis_manager.initialize()

            self.record_metric("redis_manager_initialized", True)

            # Test Redis connectivity
            await redis_manager.set("test_connectivity", "issue_1278_test", expire=60)
            value = await redis_manager.get("test_connectivity")

            self.assertEqual(value, "issue_1278_test")
            self.record_metric("redis_connectivity_test", "PASSED")

            # Cleanup test key
            await redis_manager.delete("test_connectivity")

        except (ConnectionError, OSError, TimeoutError) as e:
            # These are EXPECTED failures for Issue #1278 when VPC connectivity fails
            self.record_metric("redis_infrastructure_failure", str(e))
            self.record_metric("redis_connectivity_test", "FAILED_AS_EXPECTED")

            # Re-raise to demonstrate Redis component of Issue #1278
            raise AssertionError(f"Redis infrastructure connectivity failed: {e}")

        except Exception as e:
            self.record_metric("redis_unexpected_error", str(e))
            raise

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_combined_infrastructure_startup_sequence(self):
        """
        Test complete infrastructure startup sequence.

        This reproduces the complete Issue #1278 scenario by testing
        the full startup sequence that fails in staging.
        """
        startup_components = {}

        try:
            # Test 1: Database Manager initialization
            manager = get_database_manager()
            await manager.initialize()
            startup_components["database_manager"] = "SUCCESS"

            # Test 2: Redis initialization
            from netra_backend.app.services.enhanced_redis_manager import RedisManager
            redis_manager = RedisManager()
            await redis_manager.initialize()
            startup_components["redis_manager"] = "SUCCESS"

            # Test 3: Combined health check
            db_health = await manager.health_check()
            redis_health = await redis_manager.health_check() if hasattr(redis_manager, 'health_check') else {"status": "unknown"}

            startup_components["database_health"] = db_health.get('status', 'unknown')
            startup_components["redis_health"] = redis_health.get('status', 'unknown')

            # Test 4: Application-level functionality
            user_context = self.create_test_user_execution_context()
            async with manager.get_session(user_context=user_context) as session:
                # Test query that requires both database and potentially Redis
                result = await session.execute(text("SELECT current_timestamp"))
                timestamp = result.scalar()
                self.assertIsNotNone(timestamp)

            startup_components["application_functionality"] = "SUCCESS"

            # If we reach here, infrastructure is working
            self.record_metric("startup_sequence", "COMPLETE_SUCCESS")
            self.record_metric("startup_components", startup_components)

        except Exception as e:
            # Record which components failed for Issue #1278 analysis
            startup_components["failure_point"] = str(e)
            startup_components["failure_component"] = self._identify_failure_component(e)

            self.record_metric("startup_sequence", "FAILED_AS_EXPECTED")
            self.record_metric("startup_components", startup_components)

            # Re-raise to demonstrate Issue #1278 complete startup failure
            raise AssertionError(f"Complete infrastructure startup failed: {e}")

    def _identify_failure_component(self, exception):
        """Identify which infrastructure component caused the failure."""
        error_str = str(exception).lower()

        if "redis" in error_str:
            return "redis"
        elif any(term in error_str for term in ["postgres", "database", "sql"]):
            return "database"
        elif any(term in error_str for term in ["network", "timeout", "connection"]):
            return "network_infrastructure"
        elif "vpc" in error_str:
            return "vpc_connectivity"
        else:
            return "unknown"


class TestDatabaseTimeoutBehavior(SSotAsyncTestCase):
    """
    Test database timeout behavior under infrastructure stress.

    These tests validate timeout configuration and behavior when
    infrastructure is slow or unavailable.
    """

    def setup_method(self, method):
        """Setup for timeout testing."""
        super().setup_method(method)

        # Configure for staging with specific timeout settings
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("POSTGRES_CONNECT_TIMEOUT", "10")  # Short timeout for testing
        self.set_env_var("POSTGRES_COMMAND_TIMEOUT", "30")
        self.set_env_var("POSTGRES_HOST", "10.52.0.3")
        self.set_env_var("POSTGRES_PORT", "5432")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_timeout_behavior(self):
        """
        Test database connection timeout behavior.

        This should FAIL with timeout when infrastructure is slow/unavailable.
        """
        config = DatabaseConfig()

        try:
            from shared.database_url_builder import DatabaseURLBuilder
            builder = DatabaseURLBuilder(self.get_env().as_dict())
            database_url = builder.build_url()
            database_url = builder.format_url_for_driver(database_url, 'asyncpg')

            # Create engine with aggressive timeout for testing
            engine = create_async_engine(
                database_url,
                echo=False,
                connect_args={
                    "command_timeout": 10,  # Short timeout
                    "connect_timeout": 5,   # Very short connection timeout
                }
            )

            # This should timeout if infrastructure is slow/unavailable
            start_time = asyncio.get_event_loop().time()

            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT pg_sleep(1), 1"))
                row = result.fetchone()

            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            await engine.dispose()

            self.record_metric("connection_duration", duration)
            self.record_metric("timeout_test", "COMPLETED_SUCCESSFULLY")

        except (SQLTimeoutError, asyncio.TimeoutError) as e:
            # EXPECTED failure for Issue #1278
            self.record_metric("timeout_failure", str(e))
            self.record_metric("timeout_test", "FAILED_AS_EXPECTED_TIMEOUT")

            # Re-raise to demonstrate timeout component of Issue #1278
            raise AssertionError(f"Database timeout occurred as expected for Issue #1278: {e}")

        except (OperationalError, ConnectionError, OSError) as e:
            # Infrastructure connectivity failure
            self.record_metric("connectivity_failure", str(e))
            self.record_metric("timeout_test", "FAILED_AS_EXPECTED_CONNECTIVITY")

            raise AssertionError(f"Database connectivity failed during timeout test: {e}")

        except Exception as e:
            self.record_metric("unexpected_timeout_error", str(e))
            raise

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_query_timeout_under_load(self):
        """
        Test database query timeout behavior under simulated load.

        This should FAIL when infrastructure cannot handle load or is unavailable.
        """
        try:
            manager = get_database_manager()
            await manager.initialize()

            user_context = self.create_test_user_execution_context()

            # Test concurrent queries that might timeout under infrastructure stress
            async def long_query():
                async with manager.get_session(user_context=user_context) as session:
                    # Query that takes time and might timeout under infrastructure stress
                    result = await session.execute(text("""
                        SELECT
                            pg_sleep(2),
                            generate_series(1, 1000) as num,
                            current_timestamp
                    """))
                    return result.fetchall()

            # Run multiple concurrent queries to stress infrastructure
            start_time = asyncio.get_event_loop().time()

            tasks = [long_query() for _ in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            # Check if any queries failed
            failed_queries = [r for r in results if isinstance(r, Exception)]
            successful_queries = [r for r in results if not isinstance(r, Exception)]

            self.record_metric("query_duration", duration)
            self.record_metric("successful_queries", len(successful_queries))
            self.record_metric("failed_queries", len(failed_queries))

            if failed_queries:
                # Some queries failed under load - this might be expected for Issue #1278
                self.record_metric("load_test", "PARTIAL_FAILURE_UNDER_LOAD")
                first_failure = failed_queries[0]
                raise AssertionError(f"Queries failed under load (Issue #1278 symptom): {first_failure}")
            else:
                self.record_metric("load_test", "ALL_QUERIES_SUCCESSFUL")

        except (SQLTimeoutError, asyncio.TimeoutError) as e:
            self.record_metric("query_timeout_failure", str(e))
            self.record_metric("load_test", "FAILED_AS_EXPECTED_TIMEOUT")

            raise AssertionError(f"Query timeout under load (Issue #1278): {e}")

        except (OperationalError, ConnectionError, OSError) as e:
            self.record_metric("query_connectivity_failure", str(e))
            self.record_metric("load_test", "FAILED_AS_EXPECTED_CONNECTIVITY")

            raise AssertionError(f"Connectivity failed during load test: {e}")

        except Exception as e:
            self.record_metric("unexpected_load_error", str(e))
            raise