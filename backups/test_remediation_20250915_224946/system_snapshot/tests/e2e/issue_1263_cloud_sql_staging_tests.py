"""
E2E Tests for Issue #1263 - Cloud SQL Staging Connectivity

These E2E tests reproduce database connection timeout issues in the staging environment:
- Real Cloud SQL connectivity testing
- VPC connector and socket path validation
- Actual staging environment timeout reproduction
- End-to-end startup sequence with real services

The tests are designed to FAIL initially to reproduce the issue, then can be used
to validate fixes.

Following CLAUDE.md requirements:
- Uses real services only (no mocks in E2E tests)
- Tests against actual staging environment
- Uses SSOT test framework
- Reproduces production-like conditions
"""

import pytest
import asyncio
import unittest
from unittest.mock import patch
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Real service components for E2E testing
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.configuration.database import DatabaseConfigManager
from netra_backend.app.startup_checks.database_checks import perform_database_health_check
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config,
    get_cloud_sql_optimized_config,
    log_timeout_configuration
)

# Configuration and environment
from netra_backend.app.core.config import get_config
from shared.isolated_environment import IsolatedEnvironment

# Database URL construction
from shared.database_url_builder import DatabaseURLBuilder


class TestCloudSQLStagingConnectivity(SSotAsyncTestCase):
    """E2E tests for Cloud SQL staging connectivity and timeout issues."""

    def setUp(self):
        """Set up E2E test fixtures with staging configuration."""
        super().setUp()

        # Set up staging environment for E2E testing
        self.env = IsolatedEnvironment()
        self.env.set('ENVIRONMENT', 'staging', 'e2e_test')
        self.env.set('POSTGRES_HOST', '/cloudsql/netra-staging:us-central1:staging-shared-postgres', 'e2e_test')

        # Initialize logger for E2E test debugging
        self.logger = logging.getLogger(__name__)

        # Log test configuration for debugging
        log_timeout_configuration('staging')

    async def test_cloud_sql_staging_connection_timeout_reproduction(self):
        """
        E2E test to reproduce the "timeout after 8.0 seconds" issue in staging.

        This test should FAIL to demonstrate the actual timeout issue
        when connecting to Cloud SQL in the staging environment.
        """
        # Use actual staging configuration
        staging_config = get_database_timeout_config('staging')
        initialization_timeout = staging_config['initialization_timeout']  # 8.0 seconds

        self.logger.info(f"Testing Cloud SQL connection with {initialization_timeout}s timeout")

        # Create database manager with staging configuration
        database_manager = DatabaseManager()

        start_time = time.time()

        try:
            # Attempt real Cloud SQL connection with problematic timeout
            await asyncio.wait_for(
                database_manager.initialize_database(),
                timeout=initialization_timeout
            )

            connection_duration = time.time() - start_time

            # ASSERTION DESIGNED TO FAIL: Should timeout with 8.0 second configuration
            self.fail(
                f"Cloud SQL connection unexpectedly succeeded in {connection_duration:.2f}s "
                f"with {initialization_timeout}s timeout. Expected: 'timeout after 8.0 seconds' "
                f"error when connecting to staging Cloud SQL instance. "
                f"This indicates either: (1) the issue is resolved, or (2) test conditions "
                f"don't properly simulate the staging environment."
            )

        except asyncio.TimeoutError as e:
            # Expected failure - this reproduces the issue
            connection_duration = time.time() - start_time

            self.logger.error(
                f"REPRODUCED: Cloud SQL timeout after {connection_duration:.2f}s. "
                f"Configured timeout: {initialization_timeout}s. "
                f"This demonstrates the 'timeout after 8.0 seconds' issue."
            )

            # Verify this is the expected timeout duration
            self.assertAlmostEqual(
                connection_duration,
                initialization_timeout,
                delta=2.0,  # Allow 2 second tolerance
                msg=f"Timeout occurred at {connection_duration:.2f}s, expected ~{initialization_timeout}s"
            )

            # Document the reproduction for issue tracking
            self.fail(
                f"ISSUE #1263 REPRODUCED: Database connection timeout after {connection_duration:.2f}s "
                f"in staging environment. Configured timeout: {initialization_timeout}s. "
                f"This confirms the 'timeout after 8.0 seconds' issue in Cloud SQL connectivity."
            )

        except Exception as e:
            # Other errors may also indicate configuration issues
            connection_duration = time.time() - start_time

            error_message = str(e).lower()

            if 'timeout' in error_message:
                self.fail(
                    f"Cloud SQL connection timeout (not asyncio.TimeoutError): {e}. "
                    f"Duration: {connection_duration:.2f}s. This may be a lower-level "
                    f"timeout indicating VPC connector or socket connectivity issues."
                )
            elif 'permission' in error_message or 'authentication' in error_message:
                self.fail(
                    f"Cloud SQL authentication/permission error: {e}. "
                    f"This indicates IAM or database user configuration issues "
                    f"that prevent proper connectivity testing."
                )
            elif 'not found' in error_message or 'resolve' in error_message:
                self.fail(
                    f"Cloud SQL socket resolution error: {e}. "
                    f"This indicates VPC connector or socket path issues: "
                    f"POSTGRES_HOST={self.env.get('POSTGRES_HOST')}"
                )
            else:
                self.fail(
                    f"Cloud SQL connection failed with error: {e}. "
                    f"Duration: {connection_duration:.2f}s. "
                    f"This indicates configuration or connectivity issues."
                )

    async def test_staging_database_url_construction_with_cloud_sql(self):
        """
        E2E test for database URL construction with Cloud SQL socket paths.

        This should FAIL if URL construction doesn't properly handle
        Cloud SQL socket paths, which can cause connection issues.
        """
        # Get actual staging configuration
        config = get_config()
        database_url = config.database_url

        self.logger.info(f"Testing database URL construction: {database_url}")

        # Validate Cloud SQL socket path in URL
        expected_socket_path = '/cloudsql/netra-staging:us-central1:staging-shared-postgres'

        # ASSERTION DESIGNED TO FAIL: URL should properly include socket path
        self.assertIn(
            expected_socket_path,
            database_url,
            f"Database URL should include Cloud SQL socket path '{expected_socket_path}'. "
            f"Actual URL: {database_url}. Improper URL construction can cause connection timeouts."
        )

        # Validate URL format for Cloud SQL
        # Should not include port number for socket connections
        if expected_socket_path in database_url:
            self.assertNotIn(
                ':5432',
                database_url,
                f"Cloud SQL socket URL should not include port number. URL: {database_url}"
            )

        # Should use proper PostgreSQL scheme
        self.assertTrue(
            database_url.startswith('postgresql://'),
            f"Database URL should use postgresql:// scheme. URL: {database_url}"
        )

        # Test actual URL connectivity
        database_manager = DatabaseManager()
        url_builder = DatabaseURLBuilder(database_url)

        start_time = time.time()

        try:
            # Test connection with constructed URL
            connection_result = await database_manager.test_connection_url(
                url_builder.get_url(),
                timeout=10.0
            )

            connection_duration = time.time() - start_time

            # ASSERTION DESIGNED TO FAIL: Connection should fail due to timeout/config issues
            self.assertTrue(
                connection_result,
                f"Database URL connection unexpectedly succeeded in {connection_duration:.2f}s. "
                f"Expected: connection failure due to URL construction or connectivity issues."
            )

        except Exception as e:
            # Expected failure - demonstrates URL construction or connectivity issues
            connection_duration = time.time() - start_time

            self.fail(
                f"Database URL connection failed: {e}. Duration: {connection_duration:.2f}s. "
                f"URL: {database_url}. This indicates URL construction or connectivity issues "
                f"that can cause the 'timeout after 8.0 seconds' problem."
            )

    async def test_staging_health_check_timeout_e2e(self):
        """
        E2E test for database health check timeout in staging environment.

        This should FAIL to reproduce health check timeout issues
        with the actual staging Cloud SQL instance.
        """
        # Get staging health check timeout (3.0 seconds - very aggressive)
        staging_config = get_database_timeout_config('staging')
        health_check_timeout = staging_config['health_check_timeout']

        self.logger.info(f"Testing health check with {health_check_timeout}s timeout")

        start_time = time.time()

        try:
            # Perform actual health check against staging Cloud SQL
            health_result = await asyncio.wait_for(
                perform_database_health_check(),
                timeout=health_check_timeout
            )

            check_duration = time.time() - start_time

            # ASSERTION DESIGNED TO FAIL: Health check should timeout
            self.assertTrue(
                health_result,
                f"Database health check unexpectedly passed in {check_duration:.2f}s "
                f"with {health_check_timeout}s timeout. Expected: timeout due to "
                f"insufficient time for Cloud SQL health check operations."
            )

        except asyncio.TimeoutError:
            # Expected failure - demonstrates health check timeout issue
            check_duration = time.time() - start_time

            self.logger.error(
                f"REPRODUCED: Health check timeout after {check_duration:.2f}s. "
                f"Configured timeout: {health_check_timeout}s"
            )

            self.fail(
                f"ISSUE #1263 RELATED: Database health check timeout after {check_duration:.2f}s "
                f"in staging environment. Configured timeout: {health_check_timeout}s. "
                f"This demonstrates insufficient timeout for Cloud SQL health checks."
            )

        except Exception as e:
            # Other health check errors
            check_duration = time.time() - start_time

            self.fail(
                f"Database health check failed: {e}. Duration: {check_duration:.2f}s. "
                f"This indicates connectivity or configuration issues that prevent "
                f"proper health check execution in staging."
            )

    async def test_staging_vpc_connector_connectivity_e2e(self):
        """
        E2E test for VPC connector connectivity to Cloud SQL.

        This should FAIL if VPC connector is not properly configured
        or if there are network connectivity issues.
        """
        # Verify VPC connector environment configuration
        postgres_host = self.env.get('POSTGRES_HOST')
        expected_vpc_socket = '/cloudsql/netra-staging:us-central1:staging-shared-postgres'

        self.assertEqual(
            postgres_host,
            expected_vpc_socket,
            f"POSTGRES_HOST should be configured for VPC connector socket. "
            f"Expected: {expected_vpc_socket}, Got: {postgres_host}"
        )

        # Test network connectivity to Cloud SQL through VPC connector
        config_manager = DatabaseConfigManager()

        start_time = time.time()

        try:
            # Test VPC connector connectivity
            database_url = config_manager.get_database_url('staging')

            # Create database manager for VPC connectivity test
            database_manager = DatabaseManager()

            # Test connection through VPC connector
            connectivity_result = await database_manager.test_vpc_connectivity(
                socket_path=expected_vpc_socket,
                timeout=15.0  # Longer timeout for VPC connectivity test
            )

            connection_duration = time.time() - start_time

            # ASSERTION DESIGNED TO FAIL: VPC connectivity should fail
            self.assertTrue(
                connectivity_result,
                f"VPC connector connectivity unexpectedly succeeded in {connection_duration:.2f}s. "
                f"Expected: VPC connectivity failure due to network or configuration issues."
            )

        except Exception as e:
            # Expected failure - demonstrates VPC connectivity issues
            connection_duration = time.time() - start_time

            error_message = str(e).lower()

            if 'timeout' in error_message:
                self.fail(
                    f"VPC connector timeout: {e}. Duration: {connection_duration:.2f}s. "
                    f"This indicates network connectivity issues through VPC connector "
                    f"that can cause the 'timeout after 8.0 seconds' issue."
                )
            elif 'permission' in error_message or 'denied' in error_message:
                self.fail(
                    f"VPC connector permission error: {e}. "
                    f"This indicates IAM or network policy configuration issues."
                )
            elif 'not found' in error_message or 'resolve' in error_message:
                self.fail(
                    f"VPC connector socket resolution error: {e}. "
                    f"Socket: {expected_vpc_socket}. This indicates VPC connector "
                    f"configuration or Cloud SQL instance connectivity issues."
                )
            else:
                self.fail(
                    f"VPC connector connectivity error: {e}. Duration: {connection_duration:.2f}s. "
                    f"This indicates general VPC or Cloud SQL connectivity issues."
                )

    async def test_staging_full_startup_sequence_timeout_e2e(self):
        """
        E2E test for complete startup sequence with staging timeouts.

        This should FAIL to reproduce the complete startup timeout issue
        that affects the overall system initialization.
        """
        # Get complete staging timeout configuration
        staging_config = get_database_timeout_config('staging')
        total_expected_timeout = (
            staging_config['initialization_timeout'] +
            staging_config['table_setup_timeout'] +
            staging_config['health_check_timeout']
        )  # 8.0 + 5.0 + 3.0 = 16.0 seconds

        self.logger.info(
            f"Testing full startup sequence with total expected timeout: {total_expected_timeout}s"
        )

        # Components for full startup sequence
        config = get_config()
        database_manager = DatabaseManager()

        start_time = time.time()

        try:
            # Step 1: Database initialization
            await asyncio.wait_for(
                database_manager.initialize_database(),
                timeout=staging_config['initialization_timeout']
            )

            # Step 2: Table setup
            await asyncio.wait_for(
                database_manager.initialize_tables(),
                timeout=staging_config['table_setup_timeout']
            )

            # Step 3: Health check
            await asyncio.wait_for(
                perform_database_health_check(),
                timeout=staging_config['health_check_timeout']
            )

            startup_duration = time.time() - start_time

            # ASSERTION DESIGNED TO FAIL: Full startup should timeout
            self.fail(
                f"Full startup sequence unexpectedly completed in {startup_duration:.2f}s. "
                f"Expected: timeout during one of the startup phases due to "
                f"insufficient staging timeout configuration: {staging_config}"
            )

        except asyncio.TimeoutError as e:
            # Expected failure - demonstrates startup sequence timeout
            startup_duration = time.time() - start_time

            self.logger.error(
                f"REPRODUCED: Full startup sequence timeout after {startup_duration:.2f}s. "
                f"Staging config: {staging_config}"
            )

            self.fail(
                f"ISSUE #1263 REPRODUCED: Full startup sequence timeout after {startup_duration:.2f}s "
                f"in staging environment. This demonstrates the complete impact of insufficient "
                f"timeout configuration on system startup. Config: {staging_config}"
            )

        except Exception as e:
            # Other startup errors indicate configuration problems
            startup_duration = time.time() - start_time

            self.fail(
                f"Full startup sequence failed: {e}. Duration: {startup_duration:.2f}s. "
                f"This indicates database connectivity or configuration issues that prevent "
                f"successful system initialization in staging environment."
            )


@pytest.mark.e2e
@pytest.mark.staging
class TestStagingCloudSQLConnectivityPytest(SSotAsyncTestCase):
    """Pytest-compatible E2E tests for staging Cloud SQL connectivity."""

    @pytest.mark.asyncio
    async def test_reproduce_8_second_timeout_issue(self):
        """Pytest version of the timeout reproduction test."""
        # Set staging environment
        env = IsolatedEnvironment()
        env.set('ENVIRONMENT', 'staging', 'pytest_e2e')
        env.set('POSTGRES_HOST', '/cloudsql/netra-staging:us-central1:staging-shared-postgres', 'pytest_e2e')

        # Get problematic timeout configuration
        staging_config = get_database_timeout_config('staging')
        timeout = staging_config['initialization_timeout']  # 8.0 seconds

        # Attempt database connection
        database_manager = DatabaseManager()

        with pytest.raises((asyncio.TimeoutError, Exception)) as exc_info:
            await asyncio.wait_for(
                database_manager.initialize_database(),
                timeout=timeout
            )

        # Document the failure for issue tracking
        error = exc_info.value
        assert "timeout" in str(error).lower() or isinstance(error, asyncio.TimeoutError), \
            f"Expected timeout error, got: {error}"

        # Log reproduction confirmation
        logging.getLogger(__name__).error(
            f"ISSUE #1263 REPRODUCED: {error}. Timeout: {timeout}s"
        )


if __name__ == '__main__':
    unittest.main()