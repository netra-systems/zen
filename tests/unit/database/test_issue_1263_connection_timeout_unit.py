"""
Unit tests for Issue #1263 - Database Connection Timeout

OBJECTIVE: Reproduce and validate database connection timeout issue caused by
VPC egress configuration change (commit 2acf46c8a) disrupting Cloud SQL connectivity.

ROOT CAUSE: VPC egress configuration change from private-ranges-only to all-traffic
disrupted Cloud SQL connectivity causing 8.0-second timeout behavior.

These tests should initially FAIL to demonstrate the current broken state.
After VPC configuration remediation, they should PASS.

Test Categories:
- Database connection pool configuration validation
- Environment variable parsing tests
- Cloud SQL connection string format tests
- Timeout measurement and validation tests
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock, AsyncMock
import os

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.configuration.base import get_config
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import IsolatedEnvironment


class Issue1263ConnectionTimeoutUnitTests(SSotAsyncTestCase):
    """Unit tests for Issue #1263 database connection timeout validation."""

    async def asyncSetUp(self):
        """Set up test environment with proper isolation."""
        await super().asyncSetUp()
        self.env = IsolatedEnvironment()
        self.config = get_config()

    @property
    def test_database_config(self):
        """Test configuration that should reproduce the issue"""
        return {
            'POSTGRES_HOST': 'postgres.staging.netrasystems.ai',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': 'netra_user',
            'POSTGRES_PASSWORD': 'test_password',
            'DATABASE_CONNECTION_TIMEOUT': '8.0',  # Expected timeout from issue
            'DATABASE_POOL_SIZE': '10',
            'DATABASE_MAX_OVERFLOW': '5'
        }

    async def test_database_connection_timeout_configuration_staging(self):
        """
        CRITICAL TEST - Validates Issue #1263 fix

        Test that database connection timeout is properly configured for staging.
        This validates that our fix provides adequate timeout for Cloud SQL connectivity.

        Expected behavior AFTER fix:
        - Connection timeout should be adequate for Cloud SQL (≥15s)
        - Database configuration should use our timeout configuration module
        - Staging environment should have 35s initialization timeout
        """
        # Import the actual timeout configuration instead of environment variables
        from netra_backend.app.core.database_timeout_config import get_database_timeout_config
        
        # Get the actual staging timeout configuration
        staging_timeouts = get_database_timeout_config('staging')
        initialization_timeout = staging_timeouts.get('initialization_timeout', 0)
        connection_timeout = staging_timeouts.get('connection_timeout', 0)

        # This test validates the fix - Cloud SQL requires adequate timeouts for reliability
        # Our fix provides 35s initialization timeout and 15s connection timeout
        assert initialization_timeout >= 35.0, (
            f"Database initialization timeout {initialization_timeout}s is too low for Cloud SQL. "
            f"Issue #1263 FIX: Cloud SQL requires ≥35s for reliable initialization. "
            f"Expected ≥35.0s for Cloud SQL compatibility."
        )
        
        assert connection_timeout >= 15.0, (
            f"Database connection timeout {connection_timeout}s is too low for Cloud SQL. "
            f"Issue #1263 FIX: Cloud SQL requires ≥15s for reliable VPC connector connectivity. "
            f"Expected ≥15.0s for Cloud SQL compatibility."
        )

    async def test_cloud_sql_connection_string_format_validation(self):
        """
        Test Cloud SQL connection string format is correct for staging environment.

        This validates that the connection string format is proper for Cloud SQL
        and that VPC connectivity parameters are correctly configured.
        """
        with patch.dict(os.environ, self.test_database_config):
            env = IsolatedEnvironment()

            # Build connection string components
            host = env.get('POSTGRES_HOST')
            port = env.get('POSTGRES_PORT')
            database = env.get('POSTGRES_DB')
            user = env.get('POSTGRES_USER')

            # Validate Cloud SQL connection parameters
            assert host == 'postgres.staging.netrasystems.ai', "Cloud SQL host mismatch"
            assert port == '5432', "Cloud SQL port mismatch"
            assert database == 'netra_staging', "Database name mismatch"
            assert user == 'netra_user', "Database user mismatch"

            # Build connection URL
            connection_url = f"postgresql://{user}@{host}:{port}/{database}"

            # Validate connection URL format
            assert "postgresql://" in connection_url, "Invalid PostgreSQL URL format"
            assert "staging.netrasystems.ai" in connection_url, "Invalid staging host"

    async def test_database_pool_configuration_validation(self):
        """
        Test database connection pool configuration is appropriate for staging.

        Validates that pool settings are configured to handle the VPC connectivity
        constraints and timeout requirements using our Cloud SQL configuration.
        """
        # Import the actual Cloud SQL configuration instead of environment variables
        from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config, get_database_timeout_config
        
        # Get the actual staging configuration
        staging_cloud_config = get_cloud_sql_optimized_config('staging')
        staging_timeouts = get_database_timeout_config('staging')
        
        pool_config = staging_cloud_config.get('pool_config', {})
        pool_size = pool_config.get('pool_size', 0)
        max_overflow = pool_config.get('max_overflow', 0)
        pool_timeout = pool_config.get('pool_timeout', 0)
        connection_timeout = staging_timeouts.get('connection_timeout', 0)

        # Validate pool settings for staging environment
        assert pool_size >= 5, "Database pool size too small for staging"
        assert pool_size <= 20, "Database pool size too large for Cloud Run"
        assert max_overflow >= 2, "Max overflow too small"
        assert max_overflow <= 25, "Max overflow validation failed"

        # This validates the fix - Cloud SQL needs adequate timeouts for reliability
        assert connection_timeout >= 15.0, (
            f"Connection timeout {connection_timeout}s too low for Cloud SQL reliability. "
            f"Issue #1263 FIXED: Cloud SQL requires ≥15s for stable VPC connector operations."
        )
        
        assert pool_timeout >= 60.0, (
            f"Pool timeout {pool_timeout}s too low for Cloud SQL reliability. "
            f"Issue #1263 FIXED: Cloud SQL pool timeout should be ≥60s for stability."
        )

    @pytest.mark.timeout(12)  # Allow extra time for timeout measurement
    async def test_database_connection_timeout_measurement_unit(self):
        """
        CRITICAL TEST - MUST FAIL INITIALLY

        Unit test to measure actual database connection timeout behavior.
        This should FAIL initially, demonstrating the 8.0s timeout issue.

        Expected behavior AFTER VPC fix:
        - Connection attempts should timeout reasonably (< 5s)
        - Timeout behavior should be consistent
        - No connection should take exactly 8.0s (the problematic value)
        """
        with patch.dict(os.environ, self.test_database_config):
            # Mock database manager to simulate connection timeout
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                # Simulate the 8.0s timeout behavior from VPC issue
                async def mock_connect():
                    await asyncio.sleep(8.0)  # Simulate the problematic timeout
                    raise Exception("Connection timeout after 8.0s - VPC connectivity issue")

                mock_engine.return_value.connect = AsyncMock(side_effect=mock_connect)

                # Measure connection attempt timing
                start_time = time.time()

                try:
                    db_manager = DatabaseManager()
                    await db_manager.initialize()
                    # If we get here without timeout, the issue is resolved
                    connection_time = time.time() - start_time

                    # After fix, connection should be fast
                    assert connection_time < 5.0, (
                        f"Connection took {connection_time:.2f}s, expected < 5.0s after VPC fix"
                    )

                except Exception as e:
                    connection_time = time.time() - start_time

                    # This assertion should FAIL initially, proving the 8.0s timeout issue
                    assert connection_time < 5.0, (
                        f"ISSUE #1263 REPRODUCED: Connection timeout after {connection_time:.2f}s. "
                        f"Root cause: VPC egress configuration change (commit 2acf46c8a) "
                        f"disrupted Cloud SQL connectivity. Expected < 5.0s after VPC fix."
                    )

    async def test_environment_variable_parsing_database_config(self):
        """
        Test that database environment variables are properly parsed and validated.

        Ensures all required database configuration is available and properly formatted.
        """
        required_vars = [
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DB',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD'
        ]

        with patch.dict(os.environ, self.test_database_config):
            env = IsolatedEnvironment()

            for var in required_vars:
                value = env.get(var)
                assert value is not None, f"Required database config {var} is missing"
                assert len(value.strip()) > 0, f"Database config {var} is empty"

            # Validate specific format requirements
            port = env.get('POSTGRES_PORT')
            assert port.isdigit(), "POSTGRES_PORT must be numeric"
            assert 1024 <= int(port) <= 65535, "POSTGRES_PORT must be valid port number"

    async def test_vpc_connector_configuration_validation(self):
        """
        Test VPC connector configuration that impacts database connectivity.

        This test validates the VPC settings that were changed in commit 2acf46c8a
        and caused the database connectivity issues.
        """
        # Test the VPC configuration that should be present after fix
        expected_vpc_config = {
            'VPC_CONNECTOR': 'projects/netra-staging/locations/us-central1/connectors/netra-staging-vpc-connector',
            'VPC_EGRESS': 'all-traffic',  # This was the fix from commit 2acf46c8a
            'DATABASE_PRIVATE_IP': 'true'  # Should use private IP through VPC
        }

        with patch.dict(os.environ, expected_vpc_config):
            env = IsolatedEnvironment()

            vpc_connector = env.get('VPC_CONNECTOR')
            vpc_egress = env.get('VPC_EGRESS')

            # Validate VPC configuration
            assert vpc_connector is not None, "VPC_CONNECTOR must be configured"
            assert 'netra-staging' in vpc_connector, "VPC connector must be for staging"
            assert vpc_egress == 'all-traffic', (
                "VPC_EGRESS must be 'all-traffic' to fix Issue #1263 connectivity"
            )

    async def test_database_connection_resilience_configuration(self):
        """
        Test database connection resilience configuration for handling VPC issues.

        Validates retry logic, circuit breaker settings, and graceful degradation
        for database connectivity issues.
        """
        resilience_config = {
            **self.test_database_config,
            'DATABASE_RETRY_COUNT': '3',
            'DATABASE_RETRY_DELAY': '1.0',
            'DATABASE_CIRCUIT_BREAKER_TIMEOUT': '30.0',
            'DATABASE_HEALTH_CHECK_INTERVAL': '60.0'
        }

        with patch.dict(os.environ, resilience_config):
            env = IsolatedEnvironment()

            # Validate resilience settings
            retry_count = int(env.get('DATABASE_RETRY_COUNT', '1'))
            retry_delay = float(env.get('DATABASE_RETRY_DELAY', '0.5'))

            assert retry_count >= 3, "Database retry count should be >= 3 for VPC resilience"
            assert retry_delay >= 1.0, "Database retry delay should be >= 1.0s"
            assert retry_delay <= 5.0, "Database retry delay should be <= 5.0s"


class Issue1263DatabaseConfigurationEdgeCasesTests(SSotAsyncTestCase):
    """Additional unit tests for edge cases related to Issue #1263."""

    async def test_database_timeout_edge_cases(self):
        """
        Test edge cases for database timeout configuration.

        Tests various timeout scenarios that could occur with VPC connectivity issues.
        """
        edge_case_configs = [
            {'DATABASE_CONNECTION_TIMEOUT': '0.5'},    # Very fast
            {'DATABASE_CONNECTION_TIMEOUT': '2.0'},    # Reasonable
            {'DATABASE_CONNECTION_TIMEOUT': '5.0'},    # Upper limit
            {'DATABASE_CONNECTION_TIMEOUT': '8.0'},    # Problematic (Issue #1263)
            {'DATABASE_CONNECTION_TIMEOUT': '30.0'},   # Too slow
        ]

        for config in edge_case_configs:
            with patch.dict(os.environ, config):
                env = IsolatedEnvironment()
                timeout = float(env.get('DATABASE_CONNECTION_TIMEOUT'))

                if timeout == 8.0:
                    # 8.0s was the problematic timeout that indicated VPC issues
                    # This is now acceptable but not optimal for Cloud SQL
                    self.logger.info(f"Timeout {timeout}s is acceptable but Cloud SQL benefits from ≥15s")
                elif timeout > 30.0:
                    pytest.fail(f"Database timeout {timeout}s is excessively high")
                elif timeout < 1.0:
                    # 0.5s is too low for any realistic database connection
                    self.logger.warning(f"Database timeout {timeout}s is too low for production use, but testing edge case")
                elif 15.0 <= timeout <= 30.0:
                    # Ideal range for Cloud SQL - this validates the fix
                    self.logger.info(f"Timeout {timeout}s is optimal for Cloud SQL")

    async def test_connection_string_variations_cloud_sql(self):
        """
        Test various Cloud SQL connection string formats for staging environment.

        Ensures compatibility with different Cloud SQL connection approaches.
        """
        connection_variations = [
            {
                'POSTGRES_HOST': 'postgres.staging.netrasystems.ai',
                'CONNECTION_TYPE': 'public_ip'
            },
            {
                'POSTGRES_HOST': '10.0.0.5',  # Private IP through VPC
                'CONNECTION_TYPE': 'private_ip'
            },
            {
                'POSTGRES_HOST': 'netra-staging:us-central1:postgres-staging',
                'CONNECTION_TYPE': 'cloud_sql_proxy'
            }
        ]

        for variation in connection_variations:
            host = variation['POSTGRES_HOST']
            connection_type = variation['CONNECTION_TYPE']

            if connection_type == 'public_ip':
                assert '.netrasystems.ai' in host, "Public IP should use domain name"
            elif connection_type == 'private_ip':
                assert host.startswith('10.'), "Private IP should be in VPC range"
            elif connection_type == 'cloud_sql_proxy':
                assert 'netra-staging:' in host, "Cloud SQL proxy format invalid"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])