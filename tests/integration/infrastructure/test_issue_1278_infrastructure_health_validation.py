"""
Infrastructure Health Tests for Issue #1278 - VPC Connector and Cloud SQL Validation

These tests validate VPC connector and Cloud SQL infrastructure health patterns
WITHOUT Docker, focusing on the specific infrastructure constraints identified
in Issue #1278.

Business Value Justification (BVJ):
- Segment: Platform/Production
- Business Goal: Infrastructure Reliability/Capacity Planning
- Value Impact: Ensure infrastructure components can support production load
- Strategic Impact: Validate $500K+ ARR infrastructure scaling requirements

CRITICAL: These tests are designed to FAIL when infrastructure capacity
constraints exist, demonstrating the VPC connector and Cloud SQL issues
that block Issue #1278 resolution.
"""

import asyncio
import pytest
import time
import socket
import subprocess
import platform
from typing import Dict, Any, Optional, List, Union
from unittest.mock import patch, MagicMock
import psutil
import concurrent.futures

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestIssue1278VPCConnectorHealthValidation(SSotAsyncTestCase):
    """
    Test VPC connector health validation for Issue #1278.

    These tests validate VPC connector capacity and connectivity patterns
    that are blocking Issue #1278 resolution.
    """

    def setup_method(self, method):
        """Setup for VPC connector health tests."""
        super().setup_method(method)

        # Configure for staging environment
        self.set_env_var("ENVIRONMENT", "staging", source="test")
        self.set_env_var("GCP_PROJECT", "netra-staging", source="test")

        # VPC connector configuration
        self.set_env_var("VPC_CONNECTOR", "staging-connector", source="test")
        self.set_env_var("VPC_CONNECTOR_REGION", "us-central1", source="test")

        # Internal VPC network addresses
        self.postgres_host = "10.52.0.3"
        self.postgres_port = 5432
        self.redis_host = "10.52.0.2"
        self.redis_port = 6379

        self.record_metric("test_category", "issue_1278_vpc_connector_health")
        self.record_metric("vpc_connector", "staging-connector")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_vpc_network_reachability_postgres(self):
        """
        Test VPC network reachability to PostgreSQL host.

        This should FAIL for Issue #1278 - VPC connector capacity constraints
        prevent reliable connectivity to internal network resources.
        """
        target_host = self.postgres_host
        target_port = self.postgres_port
        connection_timeout = 30

        start_time = time.time()
        connectivity_attempts = []

        # Test multiple connection attempts to detect capacity issues
        for attempt in range(3):
            attempt_start = time.time()

            try:
                # Attempt socket connection to PostgreSQL host
                sock = socket.create_connection(
                    (target_host, target_port),
                    timeout=connection_timeout
                )
                sock.close()

                attempt_time = time.time() - attempt_start
                connectivity_attempts.append({
                    "attempt": attempt + 1,
                    "status": "success",
                    "time": attempt_time,
                    "error": None
                })

                self.record_metric(f"vpc_postgres_attempt_{attempt + 1}_success", True)
                self.record_metric(f"vpc_postgres_attempt_{attempt + 1}_time", attempt_time)

            except (socket.timeout, socket.error, OSError) as e:
                attempt_time = time.time() - attempt_start
                connectivity_attempts.append({
                    "attempt": attempt + 1,
                    "status": "failed",
                    "time": attempt_time,
                    "error": str(e)
                })

                self.record_metric(f"vpc_postgres_attempt_{attempt + 1}_success", False)
                self.record_metric(f"vpc_postgres_attempt_{attempt + 1}_time", attempt_time)
                self.record_metric(f"vpc_postgres_attempt_{attempt + 1}_error", str(e))

            # Wait between attempts
            if attempt < 2:
                await asyncio.sleep(2)

        total_time = time.time() - start_time

        # Analyze connectivity results
        successful_attempts = sum(1 for attempt in connectivity_attempts if attempt["status"] == "success")
        failed_attempts = sum(1 for attempt in connectivity_attempts if attempt["status"] == "failed")
        total_attempts = len(connectivity_attempts)

        self.record_metric("vpc_postgres_connectivity_attempts", connectivity_attempts)
        self.record_metric("vpc_postgres_successful_attempts", successful_attempts)
        self.record_metric("vpc_postgres_failed_attempts", failed_attempts)
        self.record_metric("vpc_postgres_total_time", total_time)

        if failed_attempts > 0:
            # Expected failure for Issue #1278 - VPC connector capacity constraints
            failure_rate = failed_attempts / total_attempts
            self.record_metric("vpc_postgres_failure_rate", failure_rate)
            self.record_metric("vpc_postgres_test", "FAILED_AS_EXPECTED_VPC_CAPACITY")

            # Analyze error patterns
            error_patterns = []
            for attempt in connectivity_attempts:
                if attempt["status"] == "failed" and attempt["error"]:
                    error_str = attempt["error"].lower()
                    if "timeout" in error_str:
                        error_patterns.append("timeout")
                    elif "connection refused" in error_str:
                        error_patterns.append("connection_refused")
                    elif "network" in error_str:
                        error_patterns.append("network_error")
                    else:
                        error_patterns.append("other_error")

            self.record_metric("vpc_postgres_error_patterns", error_patterns)

            raise AssertionError(
                f"VPC connector PostgreSQL connectivity failed "
                f"(Issue #1278 - VPC connector capacity constraint): "
                f"{failed_attempts}/{total_attempts} attempts failed, "
                f"Failure rate: {failure_rate:.1%}, "
                f"Total time: {total_time:.2f}s, "
                f"Error patterns: {error_patterns}"
            )

        else:
            # Unexpected success for Issue #1278
            self.record_metric("vpc_postgres_test", "PASSED_UNEXPECTED")
            average_time = sum(attempt["time"] for attempt in connectivity_attempts) / total_attempts

            self.fail(
                f"VPC connector PostgreSQL connectivity succeeded unexpectedly "
                f"(Issue #1278 should cause VPC capacity failures): "
                f"All {total_attempts} attempts succeeded, "
                f"Average time: {average_time:.2f}s"
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_vpc_network_reachability_redis(self):
        """
        Test VPC network reachability to Redis host.

        This should FAIL for Issue #1278 - VPC connector affects all internal
        network connectivity, not just PostgreSQL.
        """
        target_host = self.redis_host
        target_port = self.redis_port
        connection_timeout = 30

        start_time = time.time()

        try:
            # Attempt socket connection to Redis host
            sock = socket.create_connection(
                (target_host, target_port),
                timeout=connection_timeout
            )
            sock.close()

            connection_time = time.time() - start_time

            self.record_metric("vpc_redis_connection_success", True)
            self.record_metric("vpc_redis_connection_time", connection_time)
            self.record_metric("vpc_redis_test", "PASSED_UNEXPECTED")

            # Unexpected success for Issue #1278
            self.fail(
                f"VPC connector Redis connectivity succeeded unexpectedly "
                f"(Issue #1278 should cause VPC capacity failures): "
                f"Connection time {connection_time:.2f}s"
            )

        except (socket.timeout, socket.error, OSError) as e:
            connection_time = time.time() - start_time

            self.record_metric("vpc_redis_connection_success", False)
            self.record_metric("vpc_redis_connection_time", connection_time)
            self.record_metric("vpc_redis_connection_error", str(e))

            # Expected failure for Issue #1278
            error_str = str(e).lower()
            vpc_error_patterns = {
                "timeout": "timeout" in error_str,
                "connection_refused": "connection refused" in error_str,
                "network_unreachable": "network" in error_str and "unreachable" in error_str,
                "host_unreachable": "host" in error_str and "unreachable" in error_str
            }

            found_patterns = [key for key, found in vpc_error_patterns.items() if found]
            self.record_metric("vpc_redis_error_patterns", found_patterns)
            self.record_metric("vpc_redis_test", "FAILED_AS_EXPECTED_VPC_CAPACITY")

            raise AssertionError(
                f"VPC connector Redis connectivity failed "
                f"(Issue #1278 - VPC connector capacity constraint): "
                f"Time {connection_time:.2f}s, "
                f"Error: {str(e)}, "
                f"Patterns: {found_patterns}"
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_vpc_concurrent_connection_stress(self):
        """
        Test VPC connector under concurrent connection stress.

        This should FAIL for Issue #1278 - concurrent connections expose
        VPC connector capacity limitations more clearly.
        """
        concurrent_connections = 10
        connection_timeout = 20
        targets = [
            (self.postgres_host, self.postgres_port, "PostgreSQL"),
            (self.redis_host, self.redis_port, "Redis")
        ]

        start_time = time.time()
        stress_results = []

        def attempt_connection(target_info: tuple, connection_id: int) -> Dict[str, Any]:
            """Attempt a single connection for stress testing."""
            host, port, service = target_info
            connection_start = time.time()

            try:
                sock = socket.create_connection((host, port), timeout=connection_timeout)
                sock.close()
                connection_time = time.time() - connection_start

                return {
                    "connection_id": connection_id,
                    "service": service,
                    "host": host,
                    "port": port,
                    "status": "success",
                    "time": connection_time,
                    "error": None
                }

            except Exception as e:
                connection_time = time.time() - connection_start

                return {
                    "connection_id": connection_id,
                    "service": service,
                    "host": host,
                    "port": port,
                    "status": "failed",
                    "time": connection_time,
                    "error": str(e)
                }

        # Run concurrent stress test
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_connections) as executor:
            # Create tasks for each target and connection
            tasks = []
            connection_id = 1

            for target in targets:
                for _ in range(concurrent_connections // len(targets)):
                    tasks.append(
                        executor.submit(attempt_connection, target, connection_id)
                    )
                    connection_id += 1

            # Wait for all connections to complete
            for future in concurrent.futures.as_completed(tasks, timeout=60):
                try:
                    result = future.result()
                    stress_results.append(result)
                except Exception as e:
                    stress_results.append({
                        "connection_id": connection_id,
                        "service": "unknown",
                        "status": "failed",
                        "time": None,
                        "error": str(e)
                    })
                    connection_id += 1

        total_time = time.time() - start_time

        # Analyze stress test results
        total_attempts = len(stress_results)
        successful_connections = sum(1 for result in stress_results if result["status"] == "success")
        failed_connections = sum(1 for result in stress_results if result["status"] == "failed")

        # Group by service
        service_results = {}
        for result in stress_results:
            service = result["service"]
            if service not in service_results:
                service_results[service] = {"success": 0, "failed": 0, "times": []}

            service_results[service][result["status"]] += 1
            if result["time"] is not None:
                service_results[service]["times"].append(result["time"])

        self.record_metric("vpc_stress_total_attempts", total_attempts)
        self.record_metric("vpc_stress_successful_connections", successful_connections)
        self.record_metric("vpc_stress_failed_connections", failed_connections)
        self.record_metric("vpc_stress_total_time", total_time)
        self.record_metric("vpc_stress_service_results", service_results)
        self.record_metric("vpc_stress_detailed_results", stress_results)

        if failed_connections > 0:
            # Expected failure for Issue #1278 - VPC connector stress failure
            failure_rate = failed_connections / total_attempts
            self.record_metric("vpc_stress_failure_rate", failure_rate)
            self.record_metric("vpc_stress_test", "FAILED_AS_EXPECTED_STRESS")

            # Analyze failure patterns by service
            failure_analysis = {}
            for result in stress_results:
                if result["status"] == "failed":
                    service = result["service"]
                    if service not in failure_analysis:
                        failure_analysis[service] = []
                    failure_analysis[service].append(result["error"])

            self.record_metric("vpc_stress_failure_analysis", failure_analysis)

            raise AssertionError(
                f"VPC connector stress test failed "
                f"(Issue #1278 - VPC capacity constraint under load): "
                f"{failed_connections}/{total_attempts} connections failed, "
                f"Failure rate: {failure_rate:.1%}, "
                f"Total time: {total_time:.2f}s, "
                f"Service results: {service_results}"
            )

        else:
            # Unexpected success for Issue #1278
            self.record_metric("vpc_stress_test", "PASSED_UNEXPECTED")
            average_time = sum(result["time"] for result in stress_results if result["time"]) / successful_connections

            self.fail(
                f"VPC connector stress test succeeded unexpectedly "
                f"(Issue #1278 should cause capacity failures under concurrent load): "
                f"All {total_attempts} connections succeeded, "
                f"Average time: {average_time:.2f}s"
            )


class TestIssue1278CloudSQLHealthValidation(SSotAsyncTestCase):
    """
    Test Cloud SQL health validation for Issue #1278.

    These tests validate Cloud SQL instance health and connection patterns
    that contribute to Issue #1278 database timeout failures.
    """

    def setup_method(self, method):
        """Setup for Cloud SQL health tests."""
        super().setup_method(method)

        # Configure for staging environment
        self.set_env_var("ENVIRONMENT", "staging", source="test")
        self.set_env_var("GCP_PROJECT", "netra-staging", source="test")

        # Cloud SQL configuration
        self.cloud_sql_instance = "netra-staging:us-central1:staging-shared-postgres"
        self.postgres_host = "10.52.0.3"  # Private IP through VPC
        self.postgres_port = 5432
        self.database_timeout = 90

        self.record_metric("test_category", "issue_1278_cloud_sql_health")
        self.record_metric("cloud_sql_instance", self.cloud_sql_instance)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cloud_sql_connection_establishment_timing(self):
        """
        Test Cloud SQL connection establishment timing patterns.

        This should FAIL for Issue #1278 - connection establishment
        exceeds timeout windows due to Cloud SQL instance constraints.
        """
        connection_attempts = 3
        max_connection_time = 30  # Reasonable connection time
        timing_results = []

        for attempt in range(connection_attempts):
            attempt_start = time.time()

            try:
                # Attempt TCP connection to Cloud SQL instance
                sock = socket.create_connection(
                    (self.postgres_host, self.postgres_port),
                    timeout=self.database_timeout
                )
                sock.close()

                connection_time = time.time() - attempt_start
                timing_results.append({
                    "attempt": attempt + 1,
                    "status": "success",
                    "time": connection_time,
                    "within_threshold": connection_time <= max_connection_time
                })

                self.record_metric(f"cloud_sql_attempt_{attempt + 1}_time", connection_time)
                self.record_metric(f"cloud_sql_attempt_{attempt + 1}_success", True)

            except Exception as e:
                connection_time = time.time() - attempt_start
                timing_results.append({
                    "attempt": attempt + 1,
                    "status": "failed",
                    "time": connection_time,
                    "error": str(e),
                    "within_threshold": False
                })

                self.record_metric(f"cloud_sql_attempt_{attempt + 1}_time", connection_time)
                self.record_metric(f"cloud_sql_attempt_{attempt + 1}_success", False)
                self.record_metric(f"cloud_sql_attempt_{attempt + 1}_error", str(e))

            # Wait between attempts
            if attempt < connection_attempts - 1:
                await asyncio.sleep(5)

        # Analyze timing results
        successful_attempts = sum(1 for result in timing_results if result["status"] == "success")
        failed_attempts = sum(1 for result in timing_results if result["status"] == "failed")
        slow_connections = sum(1 for result in timing_results if not result["within_threshold"])

        self.record_metric("cloud_sql_timing_results", timing_results)
        self.record_metric("cloud_sql_successful_attempts", successful_attempts)
        self.record_metric("cloud_sql_failed_attempts", failed_attempts)
        self.record_metric("cloud_sql_slow_connections", slow_connections)

        if failed_attempts > 0 or slow_connections > 0:
            # Expected for Issue #1278 - Cloud SQL performance issues
            if failed_attempts > 0:
                self.record_metric("cloud_sql_timing_test", "FAILED_AS_EXPECTED_CONNECTION_FAILURE")
                failure_errors = [result["error"] for result in timing_results if result["status"] == "failed"]

                raise AssertionError(
                    f"Cloud SQL connection establishment failed "
                    f"(Issue #1278 - Cloud SQL instance constraints): "
                    f"{failed_attempts}/{connection_attempts} attempts failed, "
                    f"Errors: {failure_errors}"
                )

            else:
                self.record_metric("cloud_sql_timing_test", "FAILED_AS_EXPECTED_SLOW_CONNECTIONS")
                slow_times = [result["time"] for result in timing_results if not result["within_threshold"]]

                raise AssertionError(
                    f"Cloud SQL connection establishment too slow "
                    f"(Issue #1278 - Cloud SQL performance constraint): "
                    f"{slow_connections}/{connection_attempts} attempts exceeded {max_connection_time}s threshold, "
                    f"Slow times: {slow_times}"
                )

        else:
            # Unexpected success for Issue #1278
            self.record_metric("cloud_sql_timing_test", "PASSED_UNEXPECTED")
            average_time = sum(result["time"] for result in timing_results) / len(timing_results)

            self.fail(
                f"Cloud SQL connection establishment succeeded unexpectedly "
                f"(Issue #1278 should cause timing/capacity issues): "
                f"All {connection_attempts} attempts within {max_connection_time}s threshold, "
                f"Average time: {average_time:.2f}s"
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cloud_sql_connection_pool_exhaustion(self):
        """
        Test Cloud SQL connection pool exhaustion patterns.

        This should FAIL for Issue #1278 - concurrent startup attempts
        exhaust Cloud SQL connection pool, causing subsequent failures.
        """
        concurrent_pool_tests = 8
        connection_timeout = 30

        start_time = time.time()
        pool_results = []

        def test_connection_pool(pool_id: int) -> Dict[str, Any]:
            """Test connection pool behavior."""
            pool_start = time.time()

            try:
                # Attempt connection that would use connection pool
                sock = socket.create_connection(
                    (self.postgres_host, self.postgres_port),
                    timeout=connection_timeout
                )

                # Hold connection briefly to stress pool
                time.sleep(2)
                sock.close()

                connection_time = time.time() - pool_start

                return {
                    "pool_id": pool_id,
                    "status": "success",
                    "time": connection_time,
                    "error": None
                }

            except Exception as e:
                connection_time = time.time() - pool_start

                return {
                    "pool_id": pool_id,
                    "status": "failed",
                    "time": connection_time,
                    "error": str(e)
                }

        # Run concurrent connection pool tests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_pool_tests) as executor:
            tasks = [
                executor.submit(test_connection_pool, i + 1)
                for i in range(concurrent_pool_tests)
            ]

            for future in concurrent.futures.as_completed(tasks, timeout=60):
                try:
                    result = future.result()
                    pool_results.append(result)
                except Exception as e:
                    pool_results.append({
                        "pool_id": 0,
                        "status": "failed",
                        "time": None,
                        "error": str(e)
                    })

        total_time = time.time() - start_time

        # Analyze connection pool results
        successful_pools = sum(1 for result in pool_results if result["status"] == "success")
        failed_pools = sum(1 for result in pool_results if result["status"] == "failed")

        self.record_metric("cloud_sql_pool_total_tests", concurrent_pool_tests)
        self.record_metric("cloud_sql_pool_successful", successful_pools)
        self.record_metric("cloud_sql_pool_failed", failed_pools)
        self.record_metric("cloud_sql_pool_total_time", total_time)
        self.record_metric("cloud_sql_pool_results", pool_results)

        if failed_pools > 0:
            # Expected failure for Issue #1278 - connection pool exhaustion
            failure_rate = failed_pools / concurrent_pool_tests
            self.record_metric("cloud_sql_pool_failure_rate", failure_rate)
            self.record_metric("cloud_sql_pool_test", "FAILED_AS_EXPECTED_POOL_EXHAUSTION")

            # Analyze pool failure patterns
            pool_errors = [result["error"] for result in pool_results if result["status"] == "failed"]
            self.record_metric("cloud_sql_pool_errors", pool_errors)

            raise AssertionError(
                f"Cloud SQL connection pool exhaustion detected "
                f"(Issue #1278 - concurrent startup pool constraint): "
                f"{failed_pools}/{concurrent_pool_tests} pool tests failed, "
                f"Failure rate: {failure_rate:.1%}, "
                f"Total time: {total_time:.2f}s"
            )

        else:
            # Unexpected success for Issue #1278
            self.record_metric("cloud_sql_pool_test", "PASSED_UNEXPECTED")
            average_time = sum(result["time"] for result in pool_results if result["time"]) / successful_pools

            self.fail(
                f"Cloud SQL connection pool tests succeeded unexpectedly "
                f"(Issue #1278 should cause pool exhaustion under concurrent load): "
                f"All {concurrent_pool_tests} pool tests succeeded, "
                f"Average time: {average_time:.2f}s"
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_infrastructure_combined_capacity_stress(self):
        """
        Test combined VPC connector + Cloud SQL capacity under stress.

        This should FAIL for Issue #1278 - combined infrastructure stress
        reproduces the exact conditions that cause SMD Phase 3 timeouts.
        """
        combined_stress_connections = 12
        stress_duration = 30  # seconds
        connection_timeout = 20

        start_time = time.time()
        stress_results = []

        def combined_stress_connection(stress_id: int) -> Dict[str, Any]:
            """Perform combined infrastructure stress test."""
            stress_start = time.time()

            try:
                # Sequential connection attempts to both services
                # This mimics SMD Phase 3 database initialization pattern

                # Step 1: Connect to PostgreSQL (database)
                postgres_start = time.time()
                postgres_sock = socket.create_connection(
                    (self.postgres_host, self.postgres_port),
                    timeout=connection_timeout
                )
                postgres_time = time.time() - postgres_start

                # Step 2: Connect to Redis (cache)
                redis_start = time.time()
                redis_sock = socket.create_connection(
                    (self.redis_host, self.redis_port),
                    timeout=connection_timeout
                )
                redis_time = time.time() - redis_start

                # Hold connections to stress infrastructure
                time.sleep(2)

                # Close connections
                postgres_sock.close()
                redis_sock.close()

                total_stress_time = time.time() - stress_start

                return {
                    "stress_id": stress_id,
                    "status": "success",
                    "total_time": total_stress_time,
                    "postgres_time": postgres_time,
                    "redis_time": redis_time,
                    "error": None
                }

            except Exception as e:
                total_stress_time = time.time() - stress_start

                return {
                    "stress_id": stress_id,
                    "status": "failed",
                    "total_time": total_stress_time,
                    "error": str(e)
                }

        # Run combined stress test
        with concurrent.futures.ThreadPoolExecutor(max_workers=combined_stress_connections) as executor:
            tasks = [
                executor.submit(combined_stress_connection, i + 1)
                for i in range(combined_stress_connections)
            ]

            for future in concurrent.futures.as_completed(tasks, timeout=stress_duration + 30):
                try:
                    result = future.result()
                    stress_results.append(result)
                except Exception as e:
                    stress_results.append({
                        "stress_id": 0,
                        "status": "failed",
                        "total_time": None,
                        "error": str(e)
                    })

        total_test_time = time.time() - start_time

        # Analyze combined stress results
        successful_stress = sum(1 for result in stress_results if result["status"] == "success")
        failed_stress = sum(1 for result in stress_results if result["status"] == "failed")

        self.record_metric("combined_stress_total_connections", combined_stress_connections)
        self.record_metric("combined_stress_successful", successful_stress)
        self.record_metric("combined_stress_failed", failed_stress)
        self.record_metric("combined_stress_total_time", total_test_time)
        self.record_metric("combined_stress_results", stress_results)

        if failed_stress > 0:
            # Expected failure for Issue #1278 - combined infrastructure stress
            failure_rate = failed_stress / combined_stress_connections
            self.record_metric("combined_stress_failure_rate", failure_rate)
            self.record_metric("combined_stress_test", "FAILED_AS_EXPECTED_INFRASTRUCTURE_STRESS")

            # Analyze stress failure patterns
            stress_errors = [result["error"] for result in stress_results if result["status"] == "failed"]
            self.record_metric("combined_stress_errors", stress_errors)

            raise AssertionError(
                f"Combined infrastructure stress test failed "
                f"(Issue #1278 - VPC connector + Cloud SQL capacity constraint): "
                f"{failed_stress}/{combined_stress_connections} stress connections failed, "
                f"Failure rate: {failure_rate:.1%}, "
                f"Total time: {total_test_time:.2f}s, "
                f"This reproduces SMD Phase 3 timeout conditions"
            )

        else:
            # Unexpected success for Issue #1278
            self.record_metric("combined_stress_test", "PASSED_UNEXPECTED")
            average_time = sum(result["total_time"] for result in stress_results if result["total_time"]) / successful_stress

            self.fail(
                f"Combined infrastructure stress test succeeded unexpectedly "
                f"(Issue #1278 should cause infrastructure capacity failures): "
                f"All {combined_stress_connections} stress connections succeeded, "
                f"Average time: {average_time:.2f}s"
            )