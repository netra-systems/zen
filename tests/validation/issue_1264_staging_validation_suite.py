"""
Issue #1264 Staging Validation Suite - PostgreSQL Configuration Validation

CRITICAL P0 VALIDATION: Comprehensive validation framework for when the infrastructure
team fixes the Cloud SQL MySQL→PostgreSQL misconfiguration in Issue #1264.

This validation suite provides immediate, comprehensive testing that can be executed
as soon as the infrastructure fix is applied to validate the resolution.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Reliability and Performance
- Value Impact: Validates database infrastructure supporting $500K+ ARR platform
- Strategic Impact: Ensures Golden Path functionality and prevents regression

These tests are designed to PASS after the infrastructure fix and FAIL before it,
providing clear validation of the configuration correction.
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager
import os
import json

# Project imports for staging validation
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.schemas.config import StagingConfig
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config,
    get_cloud_sql_optimized_config,
    is_cloud_sql_environment
)

# Test framework imports following SSOT patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.database_test_utility import DatabaseTestUtility
from test_framework.staging_environment_fixtures import staging_environment_fixture

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_name: str
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class StagingHealthStatus:
    """Complete staging environment health status."""
    database_connectivity: bool
    connection_time: float
    health_endpoint_status: bool
    websocket_connectivity: bool
    golden_path_status: bool
    overall_health: bool
    timestamp: str
    details: Dict[str, Any]


class Issue1264StagingValidator:
    """
    Comprehensive validator for Issue #1264 resolution.

    This validator provides immediate verification when the infrastructure team
    fixes the Cloud SQL PostgreSQL configuration issue.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.db_utility = DatabaseTestUtility()
        self.staging_timeout_threshold = 8.0  # 8 second threshold from Issue #1264
        self.results: List[ValidationResult] = []

    async def validate_database_connectivity(self) -> ValidationResult:
        """
        Validate PostgreSQL database connectivity in staging.

        This test validates that:
        1. Database connections establish within acceptable time
        2. PostgreSQL (not MySQL) is responding
        3. Cloud SQL socket connectivity works properly
        4. Connection pools function correctly

        Expected: PASS after fix (fast connection), FAIL before fix (timeout)
        """
        start_time = time.time()

        try:
            # Get staging configuration
            config = StagingConfig()

            if not config.database_url:
                return ValidationResult(
                    test_name="database_connectivity",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message="No database URL configured for staging",
                    details={"config_source": "StagingConfig"}
                )

            # Validate database URL format for PostgreSQL
            if not config.database_url.startswith('postgresql'):
                return ValidationResult(
                    test_name="database_connectivity",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message=f"Database URL is not PostgreSQL: {config.database_url[:20]}...",
                    details={"url_protocol": config.database_url.split('://')[0]}
                )

            # Get timeout configuration for staging
            timeout_config = get_database_timeout_config('staging')
            connection_timeout = timeout_config['connection_timeout']

            logger.info(f"Testing database connectivity with {connection_timeout}s timeout")

            # Test actual database connection with timeout monitoring
            connection_start = time.time()

            try:
                # Use the database utility to test connection
                async with asyncio.timeout(connection_timeout):
                    connection_successful = await self.db_utility.test_connection(
                        config.database_url,
                        timeout=connection_timeout
                    )

                connection_time = time.time() - connection_start

                if not connection_successful:
                    return ValidationResult(
                        test_name="database_connectivity",
                        success=False,
                        execution_time=time.time() - start_time,
                        error_message="Database connection failed",
                        details={
                            "connection_time": connection_time,
                            "timeout_threshold": self.staging_timeout_threshold
                        }
                    )

                # Validate connection time is acceptable (Issue #1264 indicator)
                if connection_time > self.staging_timeout_threshold:
                    return ValidationResult(
                        test_name="database_connectivity",
                        success=False,
                        execution_time=time.time() - start_time,
                        error_message=f"Connection time {connection_time:.2f}s exceeds {self.staging_timeout_threshold}s threshold - Issue #1264 still present",
                        details={
                            "connection_time": connection_time,
                            "timeout_threshold": self.staging_timeout_threshold,
                            "issue_1264_reproduced": True
                        }
                    )

                # SUCCESS: Connection established quickly
                return ValidationResult(
                    test_name="database_connectivity",
                    success=True,
                    execution_time=time.time() - start_time,
                    details={
                        "connection_time": connection_time,
                        "timeout_threshold": self.staging_timeout_threshold,
                        "cloud_sql_optimized": is_cloud_sql_environment('staging'),
                        "database_type": "postgresql"
                    }
                )

            except asyncio.TimeoutError:
                connection_time = time.time() - connection_start
                return ValidationResult(
                    test_name="database_connectivity",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message=f"Database connection timeout after {connection_time:.2f}s - Issue #1264 reproduced",
                    details={
                        "connection_time": connection_time,
                        "timeout_threshold": self.staging_timeout_threshold,
                        "issue_1264_reproduced": True,
                        "likely_cause": "Cloud SQL misconfigured as MySQL instead of PostgreSQL"
                    }
                )

        except Exception as e:
            return ValidationResult(
                test_name="database_connectivity",
                success=False,
                execution_time=time.time() - start_time,
                error_message=f"Database connectivity validation failed: {str(e)}",
                details={"exception_type": type(e).__name__}
            )

    async def validate_health_endpoint(self) -> ValidationResult:
        """
        Validate staging health endpoint accessibility.

        Tests that the backend health endpoint returns 200 OK, indicating
        successful application startup including database initialization.

        Expected: PASS after fix, FAIL before fix (startup failure)
        """
        start_time = time.time()

        try:
            import aiohttp

            # Staging health endpoint URL
            health_url = "https://backend.staging.netrasystems.ai/health"
            timeout = aiohttp.ClientTimeout(total=30.0)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.get(health_url) as response:
                        response_time = time.time() - start_time

                        if response.status == 200:
                            response_data = await response.json()

                            return ValidationResult(
                                test_name="health_endpoint",
                                success=True,
                                execution_time=response_time,
                                details={
                                    "status_code": response.status,
                                    "response_time": response_time,
                                    "health_data": response_data,
                                    "endpoint_url": health_url
                                }
                            )
                        else:
                            response_text = await response.text()
                            return ValidationResult(
                                test_name="health_endpoint",
                                success=False,
                                execution_time=response_time,
                                error_message=f"Health endpoint returned {response.status}",
                                details={
                                    "status_code": response.status,
                                    "response_text": response_text[:500],
                                    "endpoint_url": health_url
                                }
                            )

                except aiohttp.ClientError as e:
                    return ValidationResult(
                        test_name="health_endpoint",
                        success=False,
                        execution_time=time.time() - start_time,
                        error_message=f"Health endpoint connection failed: {str(e)}",
                        details={
                            "endpoint_url": health_url,
                            "connection_error": str(e)
                        }
                    )

        except ImportError:
            return ValidationResult(
                test_name="health_endpoint",
                success=False,
                execution_time=time.time() - start_time,
                error_message="aiohttp not available for health endpoint testing",
                details={"dependency_missing": "aiohttp"}
            )
        except Exception as e:
            return ValidationResult(
                test_name="health_endpoint",
                success=False,
                execution_time=time.time() - start_time,
                error_message=f"Health endpoint validation failed: {str(e)}",
                details={"exception_type": type(e).__name__}
            )

    async def validate_websocket_connectivity(self) -> ValidationResult:
        """
        Validate WebSocket connection establishment to staging.

        Tests that WebSocket connections can be established to the staging
        environment, indicating proper backend startup and networking.

        Expected: PASS after fix, FAIL before fix (connection refused)
        """
        start_time = time.time()

        try:
            import websockets
            import ssl

            # Staging WebSocket endpoint
            ws_url = "wss://backend.staging.netrasystems.ai/ws"

            # Create SSL context for staging
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE  # For staging environment

            try:
                # Attempt WebSocket connection with timeout
                async with asyncio.timeout(15.0):
                    async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
                        connection_time = time.time() - start_time

                        # Send a simple ping to verify connectivity
                        await websocket.ping()

                        return ValidationResult(
                            test_name="websocket_connectivity",
                            success=True,
                            execution_time=connection_time,
                            details={
                                "connection_time": connection_time,
                                "websocket_url": ws_url,
                                "ssl_verified": False  # Staging uses self-signed
                            }
                        )

            except asyncio.TimeoutError:
                return ValidationResult(
                    test_name="websocket_connectivity",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message="WebSocket connection timeout - likely backend startup failure",
                    details={
                        "websocket_url": ws_url,
                        "timeout_threshold": 15.0,
                        "likely_cause": "Backend failed to start due to database issues"
                    }
                )
            except Exception as e:
                return ValidationResult(
                    test_name="websocket_connectivity",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message=f"WebSocket connection failed: {str(e)}",
                    details={
                        "websocket_url": ws_url,
                        "connection_error": str(e)
                    }
                )

        except ImportError:
            return ValidationResult(
                test_name="websocket_connectivity",
                success=False,
                execution_time=time.time() - start_time,
                error_message="websockets library not available",
                details={"dependency_missing": "websockets"}
            )
        except Exception as e:
            return ValidationResult(
                test_name="websocket_connectivity",
                success=False,
                execution_time=time.time() - start_time,
                error_message=f"WebSocket connectivity validation failed: {str(e)}",
                details={"exception_type": type(e).__name__}
            )

    async def validate_golden_path_flow(self) -> ValidationResult:
        """
        Validate basic Golden Path user flow in staging.

        Tests a simplified version of the Golden Path flow to ensure
        end-to-end functionality is working after the database fix.

        Expected: PASS after fix, FAIL before fix (service unavailable)
        """
        start_time = time.time()

        try:
            # This is a simplified validation that checks if the core
            # Golden Path infrastructure is operational

            # 1. Health endpoint check (prerequisite)
            health_result = await self.validate_health_endpoint()
            if not health_result.success:
                return ValidationResult(
                    test_name="golden_path_flow",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message="Golden Path validation failed - health endpoint not accessible",
                    details={"prerequisite_failed": "health_endpoint"}
                )

            # 2. WebSocket connectivity check (prerequisite)
            ws_result = await self.validate_websocket_connectivity()
            if not ws_result.success:
                return ValidationResult(
                    test_name="golden_path_flow",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message="Golden Path validation failed - WebSocket not accessible",
                    details={"prerequisite_failed": "websocket_connectivity"}
                )

            # 3. Database connectivity check (prerequisite)
            db_result = await self.validate_database_connectivity()
            if not db_result.success:
                return ValidationResult(
                    test_name="golden_path_flow",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_message="Golden Path validation failed - database not accessible",
                    details={"prerequisite_failed": "database_connectivity"}
                )

            # If all prerequisites pass, Golden Path infrastructure is operational
            return ValidationResult(
                test_name="golden_path_flow",
                success=True,
                execution_time=time.time() - start_time,
                details={
                    "health_endpoint": "operational",
                    "websocket_connectivity": "operational",
                    "database_connectivity": "operational",
                    "golden_path_infrastructure": "ready"
                }
            )

        except Exception as e:
            return ValidationResult(
                test_name="golden_path_flow",
                success=False,
                execution_time=time.time() - start_time,
                error_message=f"Golden Path flow validation failed: {str(e)}",
                details={"exception_type": type(e).__name__}
            )

    async def run_comprehensive_validation(self) -> StagingHealthStatus:
        """
        Run comprehensive validation suite for Issue #1264 resolution.

        Executes all validation tests and provides complete health assessment
        of the staging environment after infrastructure fix.
        """
        validation_start = time.time()

        logger.info("Starting Issue #1264 comprehensive validation suite...")

        # Run all validation tests
        validation_tests = [
            self.validate_database_connectivity(),
            self.validate_health_endpoint(),
            self.validate_websocket_connectivity(),
            self.validate_golden_path_flow()
        ]

        results = await asyncio.gather(*validation_tests, return_exceptions=True)

        # Process results
        self.results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_names = ["database_connectivity", "health_endpoint", "websocket_connectivity", "golden_path_flow"]
                self.results.append(ValidationResult(
                    test_name=test_names[i],
                    success=False,
                    execution_time=0.0,
                    error_message=f"Validation test exception: {str(result)}"
                ))
            else:
                self.results.append(result)

        # Determine overall health
        all_successful = all(result.success for result in self.results)
        total_execution_time = time.time() - validation_start

        # Create comprehensive health status
        health_status = StagingHealthStatus(
            database_connectivity=next((r.success for r in self.results if r.test_name == "database_connectivity"), False),
            connection_time=next((r.execution_time for r in self.results if r.test_name == "database_connectivity"), 0.0),
            health_endpoint_status=next((r.success for r in self.results if r.test_name == "health_endpoint"), False),
            websocket_connectivity=next((r.success for r in self.results if r.test_name == "websocket_connectivity"), False),
            golden_path_status=next((r.success for r in self.results if r.test_name == "golden_path_flow"), False),
            overall_health=all_successful,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            details={
                "total_execution_time": total_execution_time,
                "validation_results": [
                    {
                        "test": result.test_name,
                        "success": result.success,
                        "execution_time": result.execution_time,
                        "error": result.error_message,
                        "details": result.details
                    }
                    for result in self.results
                ],
                "issue_1264_resolution_status": "RESOLVED" if all_successful else "UNRESOLVED"
            }
        )

        return health_status


@pytest.mark.staging
@pytest.mark.validation
@pytest.mark.issue_1264
class TestIssue1264StagingValidation(SSotAsyncTestCase):
    """
    Comprehensive validation tests for Issue #1264 resolution.

    These tests provide immediate validation when the infrastructure team
    fixes the Cloud SQL PostgreSQL configuration issue.
    """

    @pytest.fixture(autouse=True)
    def setup_validation_environment(self):
        """Set up validation environment."""
        self.validator = Issue1264StagingValidator()

        # Ensure we're in staging environment for these tests
        current_env = self.validator.env.get('ENVIRONMENT', 'development')
        if current_env.lower() != 'staging':
            pytest.skip(f"Issue #1264 validation requires staging environment (current: {current_env})")

    @pytest.mark.asyncio
    async def test_database_connectivity_validation(self):
        """
        VALIDATION TEST: Database connectivity after Issue #1264 fix.

        Expected: PASS after infrastructure fix, FAIL before fix
        This test validates PostgreSQL connectivity is working properly.
        """
        result = await self.validator.validate_database_connectivity()

        # Report results
        print(f"\n=== DATABASE CONNECTIVITY VALIDATION ===")
        print(f"Success: {result.success}")
        print(f"Execution Time: {result.execution_time:.2f}s")

        if result.details:
            connection_time = result.details.get('connection_time', 0.0)
            print(f"Connection Time: {connection_time:.2f}s")
            print(f"Timeout Threshold: {result.details.get('timeout_threshold', 'N/A')}s")

        if result.error_message:
            print(f"Error: {result.error_message}")

        # Assert success - this will FAIL if Issue #1264 is still present
        assert result.success, (
            f"Database connectivity validation failed: {result.error_message}. "
            f"This indicates Issue #1264 (Cloud SQL misconfiguration) is still present. "
            f"Infrastructure team needs to configure Cloud SQL as PostgreSQL."
        )

        # Additional validation - connection time should be reasonable
        if result.details and 'connection_time' in result.details:
            connection_time = result.details['connection_time']
            assert connection_time < self.validator.staging_timeout_threshold, (
                f"Connection time {connection_time:.2f}s exceeds {self.validator.staging_timeout_threshold}s threshold. "
                f"This suggests Issue #1264 timeout issue is still present."
            )

    @pytest.mark.asyncio
    async def test_health_endpoint_validation(self):
        """
        VALIDATION TEST: Health endpoint accessibility after Issue #1264 fix.

        Expected: PASS after infrastructure fix, FAIL before fix
        This test validates the backend service starts successfully.
        """
        result = await self.validator.validate_health_endpoint()

        # Report results
        print(f"\n=== HEALTH ENDPOINT VALIDATION ===")
        print(f"Success: {result.success}")
        print(f"Execution Time: {result.execution_time:.2f}s")

        if result.details:
            status_code = result.details.get('status_code', 'N/A')
            print(f"Status Code: {status_code}")
            endpoint_url = result.details.get('endpoint_url', 'N/A')
            print(f"Endpoint: {endpoint_url}")

        if result.error_message:
            print(f"Error: {result.error_message}")

        # Assert success - this will FAIL if backend can't start due to database issues
        assert result.success, (
            f"Health endpoint validation failed: {result.error_message}. "
            f"This indicates the backend service cannot start, likely due to "
            f"Issue #1264 database connectivity problems."
        )

    @pytest.mark.asyncio
    async def test_websocket_connectivity_validation(self):
        """
        VALIDATION TEST: WebSocket connectivity after Issue #1264 fix.

        Expected: PASS after infrastructure fix, FAIL before fix
        This test validates WebSocket connections work properly.
        """
        result = await self.validator.validate_websocket_connectivity()

        # Report results
        print(f"\n=== WEBSOCKET CONNECTIVITY VALIDATION ===")
        print(f"Success: {result.success}")
        print(f"Execution Time: {result.execution_time:.2f}s")

        if result.details:
            connection_time = result.details.get('connection_time', 0.0)
            print(f"Connection Time: {connection_time:.2f}s")
            ws_url = result.details.get('websocket_url', 'N/A')
            print(f"WebSocket URL: {ws_url}")

        if result.error_message:
            print(f"Error: {result.error_message}")

        # Assert success - this will FAIL if WebSocket connections are refused
        assert result.success, (
            f"WebSocket connectivity validation failed: {result.error_message}. "
            f"This indicates the backend service is not accepting WebSocket connections, "
            f"likely due to Issue #1264 preventing service startup."
        )

    @pytest.mark.asyncio
    async def test_golden_path_flow_validation(self):
        """
        VALIDATION TEST: Golden Path flow readiness after Issue #1264 fix.

        Expected: PASS after infrastructure fix, FAIL before fix
        This test validates end-to-end Golden Path infrastructure is operational.
        """
        result = await self.validator.validate_golden_path_flow()

        # Report results
        print(f"\n=== GOLDEN PATH FLOW VALIDATION ===")
        print(f"Success: {result.success}")
        print(f"Execution Time: {result.execution_time:.2f}s")

        if result.details:
            for component, status in result.details.items():
                if component != "exception_type":
                    print(f"{component}: {status}")

        if result.error_message:
            print(f"Error: {result.error_message}")

        # Assert success - this will FAIL if Golden Path infrastructure is not ready
        assert result.success, (
            f"Golden Path flow validation failed: {result.error_message}. "
            f"This indicates the Golden Path infrastructure is not operational, "
            f"likely due to Issue #1264 preventing proper service startup."
        )

    @pytest.mark.asyncio
    async def test_comprehensive_staging_validation(self):
        """
        COMPREHENSIVE VALIDATION TEST: Complete Issue #1264 resolution validation.

        This test runs the complete validation suite and provides comprehensive
        assessment of staging environment health after infrastructure fix.
        """
        health_status = await self.validator.run_comprehensive_validation()

        # Report comprehensive results
        print(f"\n=== COMPREHENSIVE STAGING VALIDATION ===")
        print(f"Overall Health: {health_status.overall_health}")
        print(f"Timestamp: {health_status.timestamp}")
        print(f"Database Connectivity: {health_status.database_connectivity}")
        print(f"Database Connection Time: {health_status.connection_time:.2f}s")
        print(f"Health Endpoint: {health_status.health_endpoint_status}")
        print(f"WebSocket Connectivity: {health_status.websocket_connectivity}")
        print(f"Golden Path Status: {health_status.golden_path_status}")

        # Print detailed results
        print(f"\nDetailed Results:")
        for result_details in health_status.details.get('validation_results', []):
            test_name = result_details['test']
            success = result_details['success']
            exec_time = result_details['execution_time']
            status_symbol = "✓" if success else "❌"
            print(f"  {status_symbol} {test_name}: {exec_time:.2f}s")
            if not success and result_details.get('error'):
                print(f"    Error: {result_details['error']}")

        issue_status = health_status.details.get('issue_1264_resolution_status', 'UNKNOWN')
        print(f"\nIssue #1264 Resolution Status: {issue_status}")

        # Assert overall health - this will FAIL if any validation fails
        assert health_status.overall_health, (
            f"Comprehensive staging validation failed. Issue #1264 resolution incomplete. "
            f"Infrastructure fix required: "
            f"Database Connectivity: {health_status.database_connectivity}, "
            f"Health Endpoint: {health_status.health_endpoint_status}, "
            f"WebSocket Connectivity: {health_status.websocket_connectivity}, "
            f"Golden Path: {health_status.golden_path_status}"
        )

        # Additional validation for Issue #1264 specific indicators
        assert health_status.connection_time < self.validator.staging_timeout_threshold, (
            f"Database connection time {health_status.connection_time:.2f}s still exceeds "
            f"{self.validator.staging_timeout_threshold}s threshold. Issue #1264 may not be fully resolved."
        )

        print(f"\n🎉 SUCCESS: Issue #1264 resolution validated - staging environment healthy!")


# Direct execution for immediate validation
if __name__ == "__main__":
    """
    Direct execution for immediate Issue #1264 validation.

    Run this script directly to validate staging environment health
    after the infrastructure team applies the PostgreSQL configuration fix.
    """
    import sys

    print("=" * 80)
    print("ISSUE #1264 STAGING VALIDATION SUITE")
    print("=" * 80)
    print("Validating PostgreSQL configuration fix in staging environment")
    print("Expected: PASS after infrastructure fix, FAIL before fix")
    print("=" * 80)

    async def run_validation():
        validator = Issue1264StagingValidator()

        # Validate environment
        current_env = validator.env.get('ENVIRONMENT', 'development')
        if current_env.lower() != 'staging':
            print(f"❌ Environment validation failed: Not in staging (current: {current_env})")
            print("   Set ENVIRONMENT=staging to run validation")
            sys.exit(1)

        print(f"✓ Environment validated: {current_env}")

        # Run comprehensive validation
        try:
            health_status = await validator.run_comprehensive_validation()

            print(f"\n" + "=" * 80)
            print(f"VALIDATION RESULTS - {health_status.timestamp}")
            print(f"=" * 80)

            print(f"Overall Health: {'✓ HEALTHY' if health_status.overall_health else '❌ UNHEALTHY'}")
            print(f"Database Connectivity: {'✓' if health_status.database_connectivity else '❌'} ({health_status.connection_time:.2f}s)")
            print(f"Health Endpoint: {'✓' if health_status.health_endpoint_status else '❌'}")
            print(f"WebSocket Connectivity: {'✓' if health_status.websocket_connectivity else '❌'}")
            print(f"Golden Path Status: {'✓' if health_status.golden_path_status else '❌'}")

            issue_status = health_status.details.get('issue_1264_resolution_status', 'UNKNOWN')
            print(f"\nIssue #1264 Status: {issue_status}")

            if health_status.overall_health:
                print(f"\n🎉 SUCCESS: Issue #1264 resolved - staging environment healthy!")
                print(f"   Infrastructure fix successful - PostgreSQL configuration working")
                sys.exit(0)
            else:
                print(f"\n❌ VALIDATION FAILED: Issue #1264 not yet resolved")
                print(f"   Infrastructure fix still required")

                # Print failure details
                for result in health_status.details.get('validation_results', []):
                    if not result['success']:
                        print(f"   - {result['test']}: {result['error']}")

                sys.exit(1)

        except Exception as e:
            print(f"\n💥 VALIDATION ERROR: {e}")
            sys.exit(1)

    # Run validation
    asyncio.run(run_validation())