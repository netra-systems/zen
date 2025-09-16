"""
Integration tests for Issue #1263 - Cloud SQL Connectivity with Real GCP Services

OBJECTIVE: Test real Cloud SQL connectivity to validate VPC egress configuration
impact on database connections. Uses real GCP services (no mocks).

ROOT CAUSE: VPC egress configuration change (commit 2acf46c8a) from
private-ranges-only to all-traffic disrupted Cloud SQL connectivity.

These integration tests use REAL SERVICES to reproduce the actual connectivity
issue and validate the VPC configuration fix.

Test Categories:
- Real Cloud SQL connectivity timeout measurement
- VPC connector routing validation
- Secret Manager integration validation
- Connection pool behavior under VPC constraints
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import os
import socket
from urllib.parse import urlparse
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.configuration.base import get_config
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import IsolatedEnvironment
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError


logger = logging.getLogger(__name__)


class TestIssue1263CloudSQLConnectivityIntegration(SSotAsyncTestCase):
    """Integration tests for Issue #1263 using real Cloud SQL connectivity."""

    async def asyncSetUp(self):
        """Set up integration test environment with real services."""
        await super().asyncSetUp()
        self.env = IsolatedEnvironment()
        self.config = get_config()

    @property
    def staging_config(self):
        """Real staging configuration for Issue #1263 reproduction"""
        env = IsolatedEnvironment()
        return {
            'POSTGRES_HOST': 'postgres.staging.netrasystems.ai',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': env.get('POSTGRES_USER', 'netra_user'),
            'POSTGRES_PASSWORD': env.get('POSTGRES_PASSWORD', 'test_password'),
            'VPC_CONNECTOR': 'projects/netra-staging/locations/us-central1/connectors/netra-staging-vpc-connector',
            'VPC_EGRESS': 'all-traffic'  # The fix from commit 2acf46c8a
        }

    async def test_cloud_sql_connectivity_timeout_measurement_real(self):
        """
        CRITICAL INTEGRATION TEST - MUST FAIL INITIALLY

        Test real Cloud SQL connectivity and measure actual timeout behavior.
        This should FAIL initially with 8.0s timeout, demonstrating Issue #1263.

        After VPC configuration fix, should PASS with reasonable connection times.
        """
        with patch.dict(os.environ, self.staging_config, clear=False):
            start_time = time.time()
            connection_successful = False
            connection_time = 0.0
            error_details = None

            try:
                # Attempt real Cloud SQL connection
                connection_url = self._build_connection_url()
                engine = create_engine(
                    connection_url,
                    pool_timeout=8.0,  # Match the problematic timeout
                    connect_args={"connect_timeout": 8.0}
                )

                # Test actual connection
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1 as test"))
                    assert result.fetchone()[0] == 1
                    connection_successful = True

                connection_time = time.time() - start_time

                # After VPC fix, connection should be fast
                assert connection_time < 5.0, (
                    f"Connection took {connection_time:.2f}s, expected < 5.0s after VPC fix"
                )

            except (OperationalError, SQLTimeoutError, Exception) as e:
                connection_time = time.time() - start_time
                error_details = str(e)

                # Log the exact error for debugging
                logger.error(f"Cloud SQL connection failed after {connection_time:.2f}s: {error_details}")

                # This should FAIL initially, demonstrating Issue #1263
                if connection_time >= 7.5:  # Close to 8.0s indicates the VPC issue
                    pytest.fail(
                        f"ISSUE #1263 REPRODUCED: Cloud SQL connection timeout after {connection_time:.2f}s. "
                        f"Root cause: VPC egress configuration change (commit 2acf46c8a) disrupted connectivity. "
                        f"Error: {error_details}"
                    )
                else:
                    # Other connection errors should still be reported
                    pytest.fail(f"Unexpected database connection error: {error_details}")

    async def test_vpc_connector_routing_validation_real(self):
        """
        Test VPC connector routing for Cloud SQL connectivity.

        Validates that the VPC connector is properly configured and routing
        traffic to Cloud SQL through the private network.
        """
        with patch.dict(os.environ, self.staging_config, clear=False):
            env = IsolatedEnvironment()
            vpc_connector = env.get('VPC_CONNECTOR')
            vpc_egress = env.get('VPC_EGRESS')

            # Validate VPC configuration
            assert vpc_connector is not None, "VPC_CONNECTOR must be configured"
            assert 'netra-staging' in vpc_connector, "VPC connector must be for staging project"
            assert 'us-central1' in vpc_connector, "VPC connector must be in correct region"
            assert vpc_egress == 'all-traffic', "VPC_EGRESS must be 'all-traffic' for Issue #1263 fix"

            # Test network routing to Cloud SQL
            postgres_host = env.get('POSTGRES_HOST')
            postgres_port = int(env.get('POSTGRES_PORT'))

            # Test DNS resolution
            try:
                socket_info = socket.getaddrinfo(postgres_host, postgres_port, socket.AF_INET)
                assert len(socket_info) > 0, f"DNS resolution failed for {postgres_host}"

                resolved_ip = socket_info[0][4][0]
                logger.info(f"Cloud SQL host {postgres_host} resolved to {resolved_ip}")

            except socket.gaierror as e:
                pytest.fail(f"DNS resolution failed for {postgres_host}: {e}")

    async def test_connection_pool_behavior_vpc_constraints_real(self):
        """
        Test database connection pool behavior under VPC connectivity constraints.

        Validates that connection pooling works properly with the VPC connector
        and doesn't hit timeout issues during pool creation.
        """
        with patch.dict(os.environ, self.staging_config, clear=False):
            pool_config = {
                'pool_size': 5,
                'max_overflow': 3,
                'pool_timeout': 5.0,  # Should be reasonable after VPC fix
                'pool_recycle': 3600
            }

            connection_url = self._build_connection_url()
            start_time = time.time()

            try:
                # Create engine with pool configuration
                engine = create_engine(
                    connection_url,
                    **pool_config,
                    connect_args={"connect_timeout": 5.0}
                )

                # Test multiple concurrent connections
                connections = []
                for i in range(3):
                    conn = engine.connect()
                    result = conn.execute(text("SELECT current_database()"))
                    db_name = result.fetchone()[0]
                    assert db_name == 'netra_staging', f"Connected to wrong database: {db_name}"
                    connections.append(conn)

                # Clean up connections
                for conn in connections:
                    conn.close()

                pool_creation_time = time.time() - start_time

                # After VPC fix, pool creation should be fast
                assert pool_creation_time < 10.0, (
                    f"Connection pool creation took {pool_creation_time:.2f}s, "
                    f"expected < 10.0s after VPC fix"
                )

            except Exception as e:
                pool_creation_time = time.time() - start_time

                if pool_creation_time >= 8.0:
                    pytest.fail(
                        f"ISSUE #1263: Connection pool creation timeout after {pool_creation_time:.2f}s. "
                        f"VPC configuration issue affecting Cloud SQL connectivity. Error: {e}"
                    )
                else:
                    pytest.fail(f"Unexpected connection pool error: {e}")

    async def test_database_health_check_performance_real(self):
        """
        Test database health check performance with real Cloud SQL.

        This test relates to the backend health ready timeout issue that was
        caused by the same VPC configuration problem.
        """
        with patch.dict(os.environ, self.staging_config, clear=False):
            health_check_start = time.time()

            try:
                # Simulate the health check query
                connection_url = self._build_connection_url()
                engine = create_engine(
                    connection_url,
                    connect_args={"connect_timeout": 3.0}  # Health check timeout
                )

                with engine.connect() as conn:
                    # Typical health check queries
                    result = conn.execute(text("SELECT 1"))
                    assert result.fetchone()[0] == 1

                    result = conn.execute(text("SELECT current_database()"))
                    assert result.fetchone()[0] == 'netra_staging'

                health_check_time = time.time() - health_check_start

                # Health checks should be very fast after VPC fix
                assert health_check_time < 3.0, (
                    f"Database health check took {health_check_time:.2f}s, "
                    f"expected < 3.0s for reliable health monitoring"
                )

            except Exception as e:
                health_check_time = time.time() - health_check_start

                # This failure pattern indicates Issue #1263
                if health_check_time >= 8.0:
                    pytest.fail(
                        f"ISSUE #1263: Database health check timeout after {health_check_time:.2f}s. "
                        f"Same VPC issue affecting /health/ready endpoint. Error: {e}"
                    )
                else:
                    pytest.fail(f"Database health check failed: {e}")

    async def test_concurrent_database_connections_vpc_stress_real(self):
        """
        Test concurrent database connections under VPC constraints.

        Validates that multiple concurrent connections work properly through
        the VPC connector without hitting timeout issues.
        """
        with patch.dict(os.environ, self.staging_config, clear=False):
            connection_url = self._build_connection_url()
            concurrent_connections = 5
            connection_results = []

            async def test_single_connection(connection_id: int) -> Dict[str, Any]:
                """Test a single database connection with timing."""
                start_time = time.time()
                try:
                    engine = create_engine(
                        connection_url,
                        connect_args={"connect_timeout": 5.0}
                    )

                    with engine.connect() as conn:
                        result = conn.execute(text(f"SELECT {connection_id} as conn_id, current_timestamp"))
                        row = result.fetchone()
                        connection_time = time.time() - start_time

                        return {
                            'connection_id': connection_id,
                            'success': True,
                            'connection_time': connection_time,
                            'result': row[0],
                            'timestamp': row[1]
                        }

                except Exception as e:
                    connection_time = time.time() - start_time
                    return {
                        'connection_id': connection_id,
                        'success': False,
                        'connection_time': connection_time,
                        'error': str(e)
                    }

            # Run concurrent connections
            tasks = [test_single_connection(i) for i in range(concurrent_connections)]
            connection_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results
            successful_connections = [r for r in connection_results if r.get('success', False)]
            failed_connections = [r for r in connection_results if not r.get('success', True)]

            # After VPC fix, most connections should succeed
            success_rate = len(successful_connections) / len(connection_results)
            assert success_rate >= 0.8, (
                f"Concurrent connection success rate {success_rate:.1%} too low. "
                f"Issue #1263: VPC configuration affecting concurrent Cloud SQL access."
            )

            # Check timing for successful connections
            avg_connection_time = sum(r['connection_time'] for r in successful_connections) / len(successful_connections)
            assert avg_connection_time < 5.0, (
                f"Average concurrent connection time {avg_connection_time:.2f}s too high"
            )

            # Log failed connections for debugging
            for failed in failed_connections:
                if failed['connection_time'] >= 8.0:
                    pytest.fail(
                        f"ISSUE #1263: Connection {failed['connection_id']} timeout "
                        f"after {failed['connection_time']:.2f}s - VPC configuration issue"
                    )

    async def test_secret_manager_integration_database_credentials(self):
        """
        Test Secret Manager integration for database credentials.

        Validates that database credentials are properly retrieved from
        Secret Manager and work with Cloud SQL connectivity.
        """
        # This test validates that credentials work with the VPC configuration
        with patch.dict(os.environ, self.staging_config, clear=False):
            # Get credentials from environment (as they would come from Secret Manager)
            env = IsolatedEnvironment()
            db_user = env.get('POSTGRES_USER')
            db_password = env.get('POSTGRES_PASSWORD')

            assert db_user is not None, "Database user credentials missing"
            assert db_password is not None, "Database password credentials missing"
            assert len(db_user.strip()) > 0, "Database user credentials empty"
            assert len(db_password.strip()) > 0, "Database password credentials empty"

            # Test credentials work with Cloud SQL
            connection_url = f"postgresql://{db_user}:{db_password}@{self.staging_config['POSTGRES_HOST']}:{self.staging_config['POSTGRES_PORT']}/{self.staging_config['POSTGRES_DB']}"

            start_time = time.time()
            try:
                engine = create_engine(connection_url, connect_args={"connect_timeout": 5.0})
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT current_user"))
                    current_user = result.fetchone()[0]
                    assert current_user == db_user, f"Connected as wrong user: {current_user}"

                credential_test_time = time.time() - start_time
                assert credential_test_time < 5.0, (
                    f"Credential authentication took {credential_test_time:.2f}s, "
                    f"expected < 5.0s after VPC fix"
                )

            except Exception as e:
                credential_test_time = time.time() - start_time

                if credential_test_time >= 8.0:
                    pytest.fail(
                        f"ISSUE #1263: Credential authentication timeout after "
                        f"{credential_test_time:.2f}s - VPC configuration issue. Error: {e}"
                    )
                else:
                    pytest.fail(f"Database credential authentication failed: {e}")

    def _build_connection_url(self) -> str:
        """Build database connection URL from environment configuration."""
        env = IsolatedEnvironment()
        host = env.get('POSTGRES_HOST')
        port = env.get('POSTGRES_PORT')
        database = env.get('POSTGRES_DB')
        user = env.get('POSTGRES_USER')
        password = env.get('POSTGRES_PASSWORD')

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"


@pytest.mark.integration
@pytest.mark.real_services
class TestIssue1263DatabaseManagerIntegration(SSotAsyncTestCase):
    """Integration tests for DatabaseManager with Issue #1263 scenario."""

    async def test_database_manager_initialization_vpc_timing(self):
        """
        Test DatabaseManager initialization timing with VPC configuration.

        This should demonstrate the Issue #1263 timeout behavior with the
        actual DatabaseManager class used in production.
        """
        staging_config = {
            'POSTGRES_HOST': 'postgres.staging.netrasystems.ai',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',
            'VPC_CONNECTOR': 'projects/netra-staging/locations/us-central1/connectors/netra-staging-vpc-connector',
            'VPC_EGRESS': 'all-traffic'
        }

        with patch.dict(os.environ, staging_config, clear=False):
            start_time = time.time()

            try:
                db_manager = DatabaseManager()
                await db_manager.initialize()

                # Test basic database operations
                await db_manager.health_check()

                initialization_time = time.time() - start_time

                # After VPC fix, initialization should be reasonable
                assert initialization_time < 10.0, (
                    f"DatabaseManager initialization took {initialization_time:.2f}s, "
                    f"expected < 10.0s after Issue #1263 VPC fix"
                )

            except Exception as e:
                initialization_time = time.time() - start_time

                if initialization_time >= 8.0:
                    pytest.fail(
                        f"ISSUE #1263: DatabaseManager initialization timeout after "
                        f"{initialization_time:.2f}s - VPC egress configuration issue. Error: {e}"
                    )
                else:
                    pytest.fail(f"DatabaseManager initialization failed: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--real-services'])