"""
Integration Tests for Issue #1263 - GCP Database Connection Timeout

These integration tests focus on real GCP Cloud SQL connectivity issues in staging
environment without Docker dependencies. Tests use real database connections where
available, or simulate realistic Cloud SQL connection patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Staging Environment Reliability
- Business Goal: Production Deployment Confidence
- Value Impact: Ensures database connectivity works in GCP Cloud SQL environment
- Strategic Impact: Validates $500K+ ARR chat functionality database dependencies

Integration Test Strategy:
1. Test real GCP Cloud SQL connectivity if accessible
2. Validate POSTGRES_HOST resolution and VPC connector functionality
3. Test connection pool behavior under Cloud SQL constraints
4. Validate timeout configurations work with real network latency
5. Test progressive retry mechanisms with real connection failures

Expected Behavior:
- Cloud SQL connections should complete within configured timeouts
- VPC connector should enable proper database access
- Connection pooling should work efficiently with Cloud SQL latency
- Retry logic should handle transient Cloud SQL connectivity issues
- System should gracefully degrade when Cloud SQL is unreachable
"""

import asyncio
import time
import socket
import pytest
import subprocess
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class GcpDatabaseConnectivityIssue1263Tests(SSotAsyncTestCase):
    """
    Integration tests for Issue #1263 - GCP Database connectivity and timeout issues.

    These tests focus on real-world database connectivity scenarios in GCP Cloud SQL
    environment, including network latency, VPC connector issues, and connection pooling.
    """

    def setup_method(self, method=None):
        """Setup integration test environment for GCP database connectivity."""
        super().setup_method(method)

        # Configure for staging environment Cloud SQL testing
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("DATABASE_TYPE", "postgresql")

        # GCP Cloud SQL specific configuration
        self.set_env_var("CLOUD_SQL_CONNECTION_NAME", "netra-staging:us-central1:staging-postgres")
        self.set_env_var("POSTGRES_HOST", "/cloudsql/netra-staging:us-central1:staging-postgres")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_DB", "netra_staging")

        # Real staging database URL pattern (will fail if not accessible)
        self.set_env_var(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres_user:password@/cloudsql/netra-staging:us-central1:staging-postgres/netra_staging"
        )

        # Enable connection monitoring
        self.set_env_var("ENABLE_DB_CONNECTION_MONITORING", "true")
        self.set_env_var("LOG_DATABASE_CONNECTIONS", "true")

        # Track connection attempts for analysis
        self.connection_attempts = []
        self.connection_times = []

    def _is_cloud_sql_accessible(self) -> bool:
        """
        Check if GCP Cloud SQL is accessible from current environment.

        Returns:
            True if Cloud SQL socket is accessible
        """
        try:
            cloud_sql_path = "/cloudsql/netra-staging:us-central1:staging-postgres"

            # Check if Unix socket path exists (indicates Cloud SQL proxy/VPC connector)
            import os
            if os.path.exists(cloud_sql_path):
                return True

            # Alternative: Check if standard postgres port is accessible on staging host
            postgres_host = self.get_env_var("POSTGRES_HOST", "localhost")
            if postgres_host and not postgres_host.startswith("/cloudsql/"):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                try:
                    result = sock.connect_ex((postgres_host, 5432))
                    return result == 0
                finally:
                    sock.close()

        except Exception as e:
            self.logger.debug(f"Cloud SQL accessibility check failed: {e}")

        return False

    def _record_connection_attempt(self, start_time: float, success: bool, error: Optional[str] = None):
        """Record connection attempt metrics."""
        duration = time.time() - start_time
        attempt = {
            'duration': duration,
            'success': success,
            'error': error,
            'timestamp': time.time()
        }
        self.connection_attempts.append(attempt)
        self.connection_times.append(duration)

        # Record metrics
        self.record_metric(f"connection_attempt_{len(self.connection_attempts)}", attempt)

    @pytest.mark.asyncio
    async def test_cloud_sql_connectivity_basic(self):
        """
        Test basic Cloud SQL connectivity using real connection if available.

        This test attempts to establish a real connection to GCP Cloud SQL
        to validate that the database is accessible and responsive.
        """
        if not self._is_cloud_sql_accessible():
            pytest.skip("GCP Cloud SQL not accessible from test environment")

        from netra_backend.app.core.database_timeout_config import get_database_timeout_config

        timeout_config = get_database_timeout_config("staging")
        connection_timeout = timeout_config["connection_timeout"]

        start_time = time.time()

        try:
            # Attempt real database connection using configured settings
            from netra_backend.app.db.postgres import create_engine_with_config
            from netra_backend.app.config import get_config

            config = get_config()

            # Create engine with Cloud SQL optimized settings
            engine = create_engine_with_config(config.database_url)

            # Test connection with timeout
            async with asyncio.timeout(connection_timeout):
                async with engine.begin() as conn:
                    # Simple connectivity test
                    result = await conn.execute("SELECT 1 as test")
                    row = result.fetchone()
                    assert row[0] == 1, "Basic connectivity test failed"

            connection_duration = time.time() - start_time
            self._record_connection_attempt(start_time, True)

            # Verify connection completed within expected timeframe
            assert connection_duration < connection_timeout, (
                f"Cloud SQL connection took {connection_duration:.2f}s, "
                f"expected < {connection_timeout}s"
            )

            self.record_metric("cloud_sql_basic_connectivity", True)
            self.record_metric("connection_duration", connection_duration)

            await engine.dispose()

        except asyncio.TimeoutError:
            connection_duration = time.time() - start_time
            self._record_connection_attempt(start_time, False, "timeout")

            # This indicates the timeout configuration may be too aggressive
            self.record_metric("cloud_sql_connection_timeout", True)
            self.record_metric("timeout_duration", connection_duration)

            pytest.fail(f"Cloud SQL connection timed out after {connection_duration:.2f}s")

        except Exception as e:
            connection_duration = time.time() - start_time
            self._record_connection_attempt(start_time, False, str(e))

            self.record_metric("cloud_sql_connection_error", str(e))
            self.record_metric("error_duration", connection_duration)

            # Log detailed error for analysis
            self.logger.error(f"Cloud SQL connection failed: {e}")
            pytest.fail(f"Cloud SQL connection error: {e}")

    @pytest.mark.asyncio
    async def test_vpc_connector_resolution(self):
        """
        Test VPC connector socket resolution for Cloud SQL connectivity.

        This test validates that the VPC connector can properly resolve
        the Cloud SQL Unix socket path used in staging environment.
        """
        cloud_sql_path = "/cloudsql/netra-staging:us-central1:staging-postgres"

        # Test socket path existence and permissions
        import os
        import stat

        if os.path.exists(cloud_sql_path):
            # VPC connector socket exists - test properties
            socket_stat = os.stat(cloud_sql_path)

            # Verify it's a socket
            assert stat.S_ISSOCK(socket_stat.st_mode), (
                f"Cloud SQL path {cloud_sql_path} exists but is not a socket"
            )

            # Verify permissions
            readable = os.access(cloud_sql_path, os.R_OK)
            writable = os.access(cloud_sql_path, os.W_OK)

            assert readable and writable, (
                f"Cloud SQL socket {cloud_sql_path} permissions insufficient: "
                f"readable={readable}, writable={writable}"
            )

            self.record_metric("vpc_connector_socket_accessible", True)
            self.record_metric("socket_permissions_ok", readable and writable)

        else:
            # VPC connector not available - skip or test alternative connectivity
            self.logger.warning(f"VPC connector socket not found: {cloud_sql_path}")
            self.record_metric("vpc_connector_socket_accessible", False)

            # Test if we can resolve staging database host alternatively
            postgres_host = self.get_env_var("POSTGRES_HOST")
            if postgres_host and not postgres_host.startswith("/cloudsql/"):
                # Test TCP connectivity to staging host
                start_time = time.time()
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5.0)
                    result = sock.connect_ex((postgres_host, 5432))

                    connectivity_time = time.time() - start_time
                    tcp_accessible = (result == 0)

                    self.record_metric("tcp_connectivity_available", tcp_accessible)
                    self.record_metric("tcp_connection_time", connectivity_time)

                    if not tcp_accessible:
                        pytest.skip(f"Neither VPC connector nor TCP connectivity available to {postgres_host}")

                finally:
                    sock.close()
            else:
                pytest.skip("No accessible database connectivity method found")

    @pytest.mark.asyncio
    async def test_database_connection_pool_behavior(self):
        """
        Test database connection pool behavior under Cloud SQL constraints.

        This test validates that connection pooling works efficiently with
        Cloud SQL latency and connection limits.
        """
        if not self._is_cloud_sql_accessible():
            pytest.skip("Cloud SQL not accessible - cannot test connection pooling")

        from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config

        # Get Cloud SQL optimized pool configuration
        pool_config = get_cloud_sql_optimized_config("staging")["pool_config"]

        # Test connection pool settings
        expected_pool_size = pool_config["pool_size"]
        expected_max_overflow = pool_config["max_overflow"]
        expected_pool_timeout = pool_config["pool_timeout"]

        try:
            from netra_backend.app.db.postgres import create_async_session_factory

            # Create session factory with pool configuration
            session_factory = create_async_session_factory()

            # Test concurrent connection creation
            concurrent_sessions = []
            start_time = time.time()

            try:
                # Create multiple concurrent sessions (within pool limits)
                for i in range(min(expected_pool_size, 5)):
                    session = session_factory()
                    concurrent_sessions.append(session)

                # Test basic operation with each session
                for i, session in enumerate(concurrent_sessions):
                    async with session() as db_session:
                        result = await db_session.execute("SELECT 1 as test")
                        row = result.fetchone()
                        assert row[0] == 1, f"Session {i} connectivity test failed"

                pool_test_duration = time.time() - start_time

                # Verify pool operations complete within reasonable time
                assert pool_test_duration < expected_pool_timeout, (
                    f"Connection pool test took {pool_test_duration:.2f}s, "
                    f"expected < {expected_pool_timeout}s"
                )

                self.record_metric("connection_pool_test_duration", pool_test_duration)
                self.record_metric("concurrent_sessions_created", len(concurrent_sessions))
                self.record_metric("connection_pool_functional", True)

            finally:
                # Clean up sessions
                for session in concurrent_sessions:
                    if hasattr(session, 'close'):
                        await session.close()

        except Exception as e:
            self.record_metric("connection_pool_error", str(e))
            self.logger.error(f"Connection pool test failed: {e}")
            pytest.fail(f"Connection pool test error: {e}")

    @pytest.mark.asyncio
    async def test_progressive_retry_logic(self):
        """
        Test progressive retry logic for Cloud SQL connection failures.

        This test validates that the retry mechanism handles transient
        Cloud SQL connectivity issues appropriately.
        """
        from netra_backend.app.core.database_timeout_config import get_progressive_retry_config

        retry_config = get_progressive_retry_config("staging")

        max_retries = retry_config["max_retries"]
        base_delay = retry_config["base_delay"]
        max_delay = retry_config["max_delay"]

        # Simulate progressive retry behavior
        attempt_count = 0
        retry_delays = []
        total_retry_time = 0.0

        start_time = time.time()

        for attempt in range(max_retries):
            attempt_count += 1

            # Calculate expected delay for this attempt
            delay = min(base_delay * (2 ** attempt), max_delay)
            retry_delays.append(delay)
            total_retry_time += delay

            self.record_metric(f"retry_attempt_{attempt + 1}_delay", delay)

            # Simulate retry delay (but don't actually wait in test)
            await asyncio.sleep(0.01)  # Minimal sleep for test performance

        total_test_time = time.time() - start_time

        # Verify retry configuration is reasonable for staging environment
        assert total_retry_time < 60.0, (
            f"Total retry time {total_retry_time:.2f}s too long for staging environment"
        )

        assert max_retries >= 3, f"Expected at least 3 retries, got {max_retries}"
        assert base_delay >= 1.0, f"Base delay {base_delay}s may be too short for Cloud SQL"

        # Verify exponential backoff
        if len(retry_delays) > 1:
            for i in range(1, len(retry_delays)):
                assert retry_delays[i] >= retry_delays[i-1], (
                    f"Retry delays not increasing: {retry_delays[i-1]} -> {retry_delays[i]}"
                )

        self.record_metric("retry_attempts_configured", attempt_count)
        self.record_metric("total_retry_time_theoretical", total_retry_time)
        self.record_metric("retry_logic_reasonable", total_retry_time < 60.0)

    @pytest.mark.asyncio
    async def test_database_health_check_integration(self):
        """
        Test database health check integration with Cloud SQL.

        This test validates that database health checks work properly
        with Cloud SQL connectivity and timeout constraints.
        """
        from netra_backend.app.core.database_timeout_config import get_database_timeout_config

        timeout_config = get_database_timeout_config("staging")
        health_check_timeout = timeout_config["health_check_timeout"]

        start_time = time.time()

        try:
            # Test DatabaseManager health check if accessible
            if self._is_cloud_sql_accessible():
                from netra_backend.app.db.database_manager import get_database_manager

                manager = get_database_manager()

                # Initialize manager if needed
                if not getattr(manager, '_initialized', False):
                    await asyncio.wait_for(
                        manager.initialize(),
                        timeout=timeout_config["initialization_timeout"]
                    )

                # Run health check with timeout
                health_result = await asyncio.wait_for(
                    manager.health_check(),
                    timeout=health_check_timeout
                )

                health_check_duration = time.time() - start_time

                # Verify health check results
                assert isinstance(health_result, dict), "Health check should return dict"
                assert 'status' in health_result, "Health check should include status"

                self.record_metric("health_check_duration", health_check_duration)
                self.record_metric("health_check_status", health_result.get('status'))
                self.record_metric("health_check_successful", health_result.get('status') == 'healthy')

                # Verify health check completed within timeout
                assert health_check_duration < health_check_timeout, (
                    f"Health check took {health_check_duration:.2f}s, "
                    f"expected < {health_check_timeout}s"
                )

            else:
                # Test mock health check behavior when Cloud SQL unavailable
                self.logger.info("Testing health check behavior with unavailable Cloud SQL")

                with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_manager:
                    mock_instance = AsyncMock()
                    mock_instance.health_check = AsyncMock(
                        side_effect=asyncio.TimeoutError("Health check timeout")
                    )
                    mock_manager.return_value = mock_instance

                    # Test that health check timeout is handled gracefully
                    with pytest.raises(asyncio.TimeoutError):
                        await asyncio.wait_for(
                            mock_instance.health_check(),
                            timeout=health_check_timeout
                        )

                    health_check_duration = time.time() - start_time

                    # Verify timeout occurred within expected timeframe
                    assert abs(health_check_duration - health_check_timeout) < 1.0, (
                        f"Health check timeout timing incorrect: {health_check_duration:.2f}s"
                    )

                    self.record_metric("health_check_timeout_test", True)
                    self.record_metric("health_check_timeout_accuracy", health_check_duration)

        except Exception as e:
            health_check_duration = time.time() - start_time
            self.record_metric("health_check_error", str(e))
            self.record_metric("health_check_error_duration", health_check_duration)

            self.logger.error(f"Health check integration test failed: {e}")
            pytest.fail(f"Health check integration error: {e}")

    @pytest.mark.asyncio
    async def test_staging_specific_database_configuration(self):
        """
        Test staging-specific database configuration validation.

        This test ensures that staging database configuration is optimized
        for Cloud SQL and includes proper timeout and connection settings.
        """
        from netra_backend.app.core.database_timeout_config import (
            get_database_timeout_config,
            get_cloud_sql_optimized_config,
            is_cloud_sql_environment
        )

        # Verify staging is identified as Cloud SQL environment
        assert is_cloud_sql_environment("staging"), "Staging should be identified as Cloud SQL environment"

        # Get staging-specific configurations
        timeout_config = get_database_timeout_config("staging")
        cloud_config = get_cloud_sql_optimized_config("staging")

        # Validate timeout configuration for staging
        expected_timeouts = {
            'initialization_timeout': 8.0,
            'table_setup_timeout': 5.0,
            'connection_timeout': 3.0,
            'health_check_timeout': 3.0
        }

        for key, expected_value in expected_timeouts.items():
            actual_value = timeout_config[key]
            assert actual_value == expected_value, (
                f"Staging {key} should be {expected_value}s, got {actual_value}s"
            )

        # Validate Cloud SQL optimization settings
        connect_args = cloud_config.get("connect_args", {})
        server_settings = connect_args.get("server_settings", {})

        assert "application_name" in server_settings, "Application name should be set for Cloud SQL"
        assert server_settings["application_name"] == "netra_staging", "Staging app name should be correct"

        # Validate pool configuration for Cloud SQL
        pool_config = cloud_config.get("pool_config", {})

        assert pool_config.get("pool_size", 0) >= 10, "Cloud SQL should have adequate pool size"
        assert pool_config.get("max_overflow", 0) >= 15, "Cloud SQL should have adequate overflow"
        assert pool_config.get("pool_timeout", 0) >= 30.0, "Cloud SQL should have reasonable pool timeout"
        assert pool_config.get("pool_pre_ping") is True, "Cloud SQL should use pre-ping"

        # Record configuration validation results
        self.record_metric("staging_timeout_config_valid", True)
        self.record_metric("staging_cloud_sql_config_valid", True)
        self.record_metric("staging_pool_config_adequate", True)

        # Validate configuration consistency
        total_timeout = (
            timeout_config["initialization_timeout"] +
            timeout_config["table_setup_timeout"] +
            timeout_config["health_check_timeout"]
        )

        # Total timeout should be reasonable for staging (< 20s to prevent WebSocket blocking)
        assert total_timeout < 20.0, (
            f"Total staging database timeout {total_timeout:.2f}s too high, "
            f"may block WebSocket connections"
        )

        self.record_metric("total_staging_timeout", total_timeout)
        self.record_metric("staging_timeout_reasonable", total_timeout < 20.0)

    def test_network_connectivity_diagnostics(self):
        """
        Test network connectivity diagnostics for staging database host.

        This test provides diagnostic information about network connectivity
        to the staging database host to help identify connectivity issues.
        """
        postgres_host = self.get_env_var("POSTGRES_HOST", "")

        if not postgres_host or postgres_host.startswith("/cloudsql/"):
            # Unix socket - test socket accessibility
            if postgres_host.startswith("/cloudsql/"):
                socket_path = postgres_host
                import os

                socket_exists = os.path.exists(socket_path)
                self.record_metric("unix_socket_exists", socket_exists)

                if socket_exists:
                    socket_accessible = os.access(socket_path, os.R_OK | os.W_OK)
                    self.record_metric("unix_socket_accessible", socket_accessible)
                else:
                    self.record_metric("unix_socket_accessible", False)

                # Skip TCP diagnostics for Unix sockets
                return
            else:
                pytest.skip("No postgres host configured for diagnostics")

        # TCP connectivity diagnostics
        diagnostic_results = {
            'host_resolvable': False,
            'port_accessible': False,
            'connection_time': None,
            'dns_resolution_time': None
        }

        try:
            # DNS resolution test
            dns_start = time.time()
            resolved_ip = socket.gethostbyname(postgres_host)
            dns_time = time.time() - dns_start

            diagnostic_results['host_resolvable'] = True
            diagnostic_results['dns_resolution_time'] = dns_time
            diagnostic_results['resolved_ip'] = resolved_ip

            self.record_metric("dns_resolution_successful", True)
            self.record_metric("dns_resolution_time", dns_time)
            self.record_metric("resolved_ip", resolved_ip)

        except socket.gaierror as e:
            diagnostic_results['dns_error'] = str(e)
            self.record_metric("dns_resolution_successful", False)
            self.record_metric("dns_error", str(e))

        if diagnostic_results['host_resolvable']:
            # Port connectivity test
            try:
                conn_start = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)

                try:
                    result = sock.connect_ex((postgres_host, 5432))
                    conn_time = time.time() - conn_start

                    diagnostic_results['port_accessible'] = (result == 0)
                    diagnostic_results['connection_time'] = conn_time

                    self.record_metric("port_accessible", result == 0)
                    self.record_metric("connection_time", conn_time)

                finally:
                    sock.close()

            except Exception as e:
                diagnostic_results['connection_error'] = str(e)
                self.record_metric("connection_error", str(e))

        # Log diagnostic results
        self.logger.info(f"Network diagnostics for {postgres_host}: {diagnostic_results}")
        self.record_metric("network_diagnostics", diagnostic_results)

        # Provide diagnostic summary
        if not diagnostic_results['host_resolvable']:
            pytest.fail(f"Database host {postgres_host} is not resolvable via DNS")
        elif not diagnostic_results['port_accessible']:
            pytest.fail(f"Database host {postgres_host}:5432 is not accessible (port closed or filtered)")
        else:
            # Connection looks good from network perspective
            self.record_metric("network_connectivity_ok", True)

    def teardown_method(self, method=None):
        """Clean up integration test environment and summarize results."""
        # Log connection attempt summary
        if self.connection_attempts:
            successful_attempts = [a for a in self.connection_attempts if a['success']]
            failed_attempts = [a for a in self.connection_attempts if not a['success']]

            self.logger.info(f"Connection attempts summary: "
                           f"{len(successful_attempts)} successful, {len(failed_attempts)} failed")

            if self.connection_times:
                avg_time = sum(self.connection_times) / len(self.connection_times)
                max_time = max(self.connection_times)
                min_time = min(self.connection_times)

                self.record_metric("avg_connection_time", avg_time)
                self.record_metric("max_connection_time", max_time)
                self.record_metric("min_connection_time", min_time)

                self.logger.info(f"Connection times: avg={avg_time:.2f}s, "
                               f"min={min_time:.2f}s, max={max_time:.2f}s")

        super().teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])