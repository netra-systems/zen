"""
Staging ClickHouse Connectivity Failures - Critical Infrastructure Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Infrastructure Stability, Analytics Reliability
- Value Impact: Prevents analytics system failures and deployment validation issues
- Strategic Impact: Ensures data pipeline operational readiness in staging

EXPECTED TO FAIL: These tests replicate critical ClickHouse connectivity issues found in staging:

1. **CRITICAL: ClickHouse Connection Timeout to Staging Host**
   - Connections to clickhouse.staging.netrasystems.ai:8123 timeout after 5+ seconds
   - Health check endpoint /health/ready returns 503 due to ClickHouse unavailability
   - Deployment validation fails preventing production releases

2. **CRITICAL: ClickHouse Service Provisioning Gap**
   - ClickHouse service not properly provisioned in staging environment
   - DNS resolution may work but service not listening on expected port
   - Network policies may be blocking ClickHouse traffic

3. **CRITICAL: ClickHouse Client Configuration Issues**
   - Application-level ClickHouse client fails to connect
   - Client timeout settings too aggressive for staging latency
   - Connection pool exhaustion due to failed connection attempts

Test-Driven Correction (TDC) Approach:
- Create failing tests that expose exact connectivity issues
- Validate configuration requirements and actual values
- Test both network-level and application-level connectivity
- Provide detailed error categorization for surgical fixes

Environment Requirements:
- Must run in staging environment (@pytest.mark.env("staging"))
- Requires CLICKHOUSE_HOST and CLICKHOUSE_PORT configuration
- Tests external service dependencies in staging infrastructure
"""

import asyncio
import json
import socket
import time
import pytest
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from unittest.mock import patch, AsyncMock

import httpx

# Core system imports using absolute paths
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from test_framework.environment_markers import env_requires, staging_only


@dataclass
class ClickHouseConnectivityResult:
    """Result container for ClickHouse connectivity test results."""
    test_type: str
    host: str
    port: int
    success: bool
    response_time_seconds: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    expected_behavior: str = "connection_success"
    actual_behavior: str = "unknown"
    business_impact: str = "unknown"


@pytest.mark.e2e
class TestStagingClickHouseConnectivityFailures:
    """Test suite for ClickHouse connectivity failures in staging environment."""

    def setup_method(self):
        """Setup isolated test environment."""
        self.env = IsolatedEnvironment()
        self.env.enable_isolation_mode()
        self.start_time = time.time()
        
    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, 'env'):
            self.env.reset_to_original()

    @pytest.mark.env("staging")
    @pytest.mark.critical
    @pytest.mark.e2e
    def test_clickhouse_staging_host_network_connectivity_timeout(self):
        """
        EXPECTED TO FAIL - CRITICAL NETWORK CONNECTIVITY ISSUE
        
        Issue: Raw network connectivity to ClickHouse staging host times out
        Expected: Socket connection to clickhouse.staging.netrasystems.ai:8123 within 5 seconds
        Actual: Connection timeout indicating service provisioning or network issues
        
        Business Impact: Analytics system non-functional, deployment validation fails
        Root Causes: Service not provisioned, DNS issues, firewall blocking, port closed
        """
        # Configuration loading
        clickhouse_host = self.env.get("CLICKHOUSE_HOST", "clickhouse.staging.netrasystems.ai")
        clickhouse_port = int(self.env.get("CLICKHOUSE_PORT", "8123"))
        
        # Validate staging configuration
        assert "staging" in clickhouse_host, (
            f"ClickHouse host should be staging environment: {clickhouse_host}"
        )
        assert clickhouse_port == 8123, (
            f"ClickHouse should use standard port 8123, got: {clickhouse_port}"
        )
        
        # Test raw network connectivity
        connectivity_results = []
        
        # Test 1: Basic TCP connection
        start_time = time.time()
        try:
            sock = socket.create_connection((clickhouse_host, clickhouse_port), timeout=5.0)
            sock.close()
            connection_time = time.time() - start_time
            
            # Connection succeeded - unexpected but good
            connectivity_results.append(
                self._create_connectivity_result(
                    "raw_tcp", clickhouse_host, clickhouse_port, 
                    response_time_ms=int(connection_time * 1000)
                )
            )
            print(f"SUCCESS: Raw TCP connection to ClickHouse in {connection_time:.2f}s")
            
        except socket.timeout:
            connection_time = time.time() - start_time
            timeout_result = self._create_connectivity_result(
                "raw_tcp", clickhouse_host, clickhouse_port, 
                error=Exception(f"Connection timeout after {connection_time:.2f}s"),
                response_time_ms=int(connection_time * 1000)
            )
            timeout_result.actual_behavior = "connection_timeout"
            timeout_result.business_impact = "analytics_system_failure"
            connectivity_results.append(timeout_result)
            
            assert False, (
                f"CRITICAL CLICKHOUSE NETWORK TIMEOUT: Cannot connect to {clickhouse_host}:{clickhouse_port} "
                f"after {connection_time:.2f}s timeout. This indicates:\n"
                f"  1. ClickHouse service not provisioned in staging\n"
                f"  2. Network policies blocking ClickHouse traffic\n"
                f"  3. DNS resolution working but service unavailable\n"
                f"  4. Port 8123 not open on staging ClickHouse instance\n\n"
                f"Business Impact: Analytics system non-functional, deployment validation fails"
            )
            
        except socket.gaierror as e:
            dns_result = self._create_connectivity_result(
                "dns_resolution", clickhouse_host, clickhouse_port,
                error=e, response_time_ms=0
            )
            dns_result.actual_behavior = "dns_resolution_failure"
            dns_result.business_impact = "service_discovery_failure"
            connectivity_results.append(dns_result)
            
            assert False, (
                f"CRITICAL CLICKHOUSE DNS FAILURE: Cannot resolve {clickhouse_host}. "
                f"Error: {e}. Check DNS configuration and staging ClickHouse provisioning."
            )
            
        except ConnectionRefusedError:
            refused_result = self._create_connectivity_result(
                "service_availability", clickhouse_host, clickhouse_port,
                error=Exception("Connection refused"), response_time_ms=0
            )
            refused_result.actual_behavior = "service_unavailable"
            refused_result.business_impact = "service_not_provisioned"
            connectivity_results.append(refused_result)
            
            assert False, (
                f"CRITICAL CLICKHOUSE SERVICE DOWN: {clickhouse_host}:{clickhouse_port} "
                f"refused connection. ClickHouse service not provisioned or not listening on port 8123."
            )

    @pytest.mark.env("staging")
    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_clickhouse_application_client_connection_timeout_failure(self):
        """
        EXPECTED TO FAIL - CRITICAL APPLICATION CLIENT ISSUE
        
        Issue: ClickHouse application client connection attempts timeout
        Expected: ClickHouse client connects within 10 seconds for health validation
        Actual: Client connection timeout causing health check 503 responses
        
        This tests the actual application-level ClickHouse client used by the backend
        """
        # Test ClickHouse client import and instantiation
        try:
            from netra_backend.app.db.clickhouse import get_clickhouse_client
        except ImportError as e:
            assert False, (
                f"CLICKHOUSE CLIENT IMPORT FAILURE: Cannot import ClickHouseClient. "
                f"Error: {e}. This indicates missing dependencies or incorrect module structure."
            )
        
        # Test client connection with timeout enforcement
        start_time = time.time()
        try:
            # Use canonical ClickHouse client with context manager
            async with get_clickhouse_client() as client:
                # Use asyncio.wait_for to enforce strict timeout
                connection_result = await asyncio.wait_for(
                    client.test_connection(),
                    timeout=10.0
                )
            connection_time = time.time() - start_time
            
            # Connection succeeded
            assert connection_result is True, (
                "ClickHouse client connection should return True on success"
            )
            assert connection_time < 5.0, (
                f"ClickHouse client connection too slow: {connection_time:.2f}s. "
                f"Should connect within 5 seconds for health check requirements."
            )
            
            print(f"SUCCESS: ClickHouse client connected in {connection_time:.2f}s")
            
        except asyncio.TimeoutError:
            connection_time = time.time() - start_time
            assert False, (
                f"CRITICAL CLICKHOUSE CLIENT TIMEOUT: Client connection timed out after {connection_time:.2f}s. "
                f"This causes /health/ready endpoint to return 503 status, blocking deployment validation. "
                f"Health checks require ClickHouse connectivity for analytics system validation.\n\n"
                f"Impact Analysis:\n"
                f"  - Deployment validation fails (503 health response)\n"
                f"  - Analytics data collection broken\n"
                f"  - Monitoring dashboards show no data\n"
                f"  - Business intelligence reports unavailable\n\n"
                f"Root Cause Investigation Required:\n"
                f"  1. Check ClickHouse service provisioning in staging\n"
                f"  2. Verify network connectivity and firewall rules\n"
                f"  3. Validate ClickHouse authentication credentials\n"
                f"  4. Test DNS resolution and service discovery"
            )
            
        except Exception as e:
            connection_time = time.time() - start_time
            error_type = type(e).__name__
            error_message = str(e)
            
            # Categorize different types of connection failures
            if "timeout" in error_message.lower():
                failure_category = "TIMEOUT"
                impact = "health checks fail with 503"
            elif "refused" in error_message.lower():
                failure_category = "SERVICE_DOWN"
                impact = "ClickHouse service not provisioned"
            elif "auth" in error_message.lower():
                failure_category = "AUTHENTICATION"
                impact = "credentials invalid or missing"
            elif "network" in error_message.lower():
                failure_category = "NETWORK"
                impact = "firewall or routing issues"
            else:
                failure_category = "UNKNOWN"
                impact = "investigate error details"
            
            assert False, (
                f"CRITICAL CLICKHOUSE CLIENT FAILURE ({failure_category}): "
                f"Connection failed after {connection_time:.2f}s. "
                f"Error: {error_type} - {error_message}. "
                f"Business Impact: {impact}. "
                f"This prevents analytics functionality and deployment validation."
            )

    @pytest.mark.env("staging")
    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_clickhouse_health_check_endpoint_503_failure_analysis(self):
        """
        EXPECTED TO FAIL - CRITICAL HEALTH CHECK ISSUE
        
        Issue: Backend /health/ready returns 503 due to ClickHouse connectivity failure  
        Expected: Health endpoint returns 200 when all external dependencies accessible
        Actual: 503 response due to ClickHouse timeout blocking deployment validation
        
        Deployment Impact: GCP Cloud Run deployment validation fails, preventing releases
        """
        # Test backend health endpoint with ClickHouse dependency
        backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        health_ready_url = f"{backend_url}/health/ready"
        
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(health_ready_url)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # Unexpected success - health check passed
                    print(f"SUCCESS: Health check passed in {response_time:.2f}s")
                    
                    # Validate that ClickHouse is actually working
                    try:
                        health_data = response.json()
                        if "services" in health_data:
                            clickhouse_status = health_data["services"].get("clickhouse", {})
                            assert clickhouse_status.get("healthy", False), (
                                f"ClickHouse reported unhealthy in health response: {clickhouse_status}"
                            )
                    except Exception as parse_error:
                        assert False, f"Health response parsing failed: {parse_error}"
                        
                elif response.status_code == 503:
                    # Expected failure - health check failing due to external services
                    try:
                        error_data = response.json()
                        
                        # Analyze error details for ClickHouse-specific issues
                        clickhouse_error = None
                        if "services" in error_data:
                            clickhouse_status = error_data["services"].get("clickhouse", {})
                            if not clickhouse_status.get("healthy", False):
                                clickhouse_error = clickhouse_status.get("error", "Unknown ClickHouse error")
                        
                        error_summary = json.dumps(error_data, indent=2)
                        
                    except Exception:
                        error_summary = response.text
                        clickhouse_error = "Unable to parse error response"
                    
                    assert False, (
                        f"CRITICAL HEALTH CHECK FAILURE: /health/ready returned 503 after {response_time:.2f}s "
                        f"due to ClickHouse connectivity issues.\n\n"
                        f"ClickHouse Error: {clickhouse_error}\n\n"
                        f"Full Error Response:\n{error_summary}\n\n"
                        f"Business Impact:\n"
                        f"  - Deployment validation fails (503 health response)\n"
                        f"  - GCP Cloud Run marks service as unhealthy\n"
                        f"  - Analytics data collection completely broken\n"
                        f"  - Production release pipeline blocked\n\n"
                        f"Root Cause Investigation:\n"
                        f"  1. Verify ClickHouse service provisioning in staging\n"
                        f"  2. Check network connectivity to clickhouse.staging.netrasystems.ai:8123\n"
                        f"  3. Validate ClickHouse authentication and credentials\n"
                        f"  4. Review firewall rules and security groups"
                    )
                else:
                    # Unexpected status code
                    assert False, (
                        f"UNEXPECTED HEALTH CHECK STATUS: Expected 200 or 503, got {response.status_code} "
                        f"after {response_time:.2f}s. Response: {response.text[:200]}"
                    )
                    
        except httpx.TimeoutException:
            response_time = time.time() - start_time
            assert False, (
                f"CRITICAL HEALTH ENDPOINT TIMEOUT: /health/ready unreachable after {response_time:.2f}s. "
                f"This indicates backend service failure or complete network connectivity breakdown."
            )
            
        except httpx.ConnectError as e:
            assert False, (
                f"CRITICAL BACKEND SERVICE DOWN: Cannot connect to backend at {backend_url}. "
                f"Error: {e}. Check backend service deployment and availability."
            )

    @pytest.mark.env("staging")
    @pytest.mark.critical
    @pytest.mark.e2e
    def test_clickhouse_configuration_loading_missing_environment_variables(self):
        """
        EXPECTED TO FAIL - CRITICAL CONFIGURATION LOADING ISSUE
        
        Issue: ClickHouse configuration not properly loaded from staging environment
        Expected: CLICKHOUSE_HOST and CLICKHOUSE_PORT loaded from staging configuration
        Actual: Configuration missing or defaulting to localhost/development values
        
        Configuration Cascade: Missing config -> localhost fallback -> connection failure -> 503 health
        """
        # Test ClickHouse configuration environment variables
        clickhouse_config_vars = {
            'CLICKHOUSE_HOST': {
                'expected_pattern': 'staging',
                'forbidden_patterns': ['localhost', '127.0.0.1', 'local'],
                'description': 'Should point to staging ClickHouse host'
            },
            'CLICKHOUSE_PORT': {
                'expected_value': '8123',
                'description': 'Should use standard ClickHouse port 8123'
            },
            'CLICKHOUSE_URL': {
                'expected_pattern': 'staging',
                'forbidden_patterns': ['localhost', '127.0.0.1'],
                'description': 'Should contain staging ClickHouse URL if provided'
            },
            'CLICKHOUSE_USER': {
                'required': False,
                'description': 'ClickHouse username if authentication required'
            },
            'CLICKHOUSE_PASSWORD': {
                'required': False,
                'description': 'ClickHouse password if authentication required'
            }
        }
        
        configuration_failures = []
        
        for var_name, requirements in clickhouse_config_vars.items():
            value = self.env.get(var_name)
            
            # Check if required variable is missing
            if requirements.get('required', True) and value is None:
                configuration_failures.append(
                    f"{var_name}: MISSING - {requirements['description']}"
                )
                continue
            
            # Skip validation for optional missing variables
            if value is None:
                continue
                
            # Check expected patterns
            if 'expected_pattern' in requirements:
                expected_pattern = requirements['expected_pattern']
                if expected_pattern not in value:
                    configuration_failures.append(
                        f"{var_name}: INVALID PATTERN - Expected '{expected_pattern}' in '{value}'"
                    )
            
            # Check expected exact values
            if 'expected_value' in requirements:
                expected_value = requirements['expected_value']
                if value != expected_value:
                    configuration_failures.append(
                        f"{var_name}: WRONG VALUE - Expected '{expected_value}', got '{value}'"
                    )
            
            # Check forbidden patterns
            if 'forbidden_patterns' in requirements:
                for forbidden in requirements['forbidden_patterns']:
                    if forbidden in value:
                        configuration_failures.append(
                            f"{var_name}: FORBIDDEN PATTERN - Contains '{forbidden}' in '{value}'"
                        )
        
        # Report configuration failures
        if configuration_failures:
            failure_report = "\n".join(f"  - {failure}" for failure in configuration_failures)
            assert False, (
                f"CRITICAL CLICKHOUSE CONFIGURATION FAILURES:\n{failure_report}\n\n"
                f"These configuration issues prevent ClickHouse connectivity, causing:\n"
                f"  - Health check 503 responses\n"
                f"  - Deployment validation failures\n"
                f"  - Analytics system breakdown\n"
                f"  - Production release pipeline blocks\n\n"
                f"Fix by updating staging environment variables with correct ClickHouse configuration."
            )

    @pytest.mark.env("staging")
    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_clickhouse_service_provisioning_staging_infrastructure_gap(self):
        """
        EXPECTED TO FAIL - CRITICAL SERVICE PROVISIONING ISSUE
        
        Issue: ClickHouse service not properly provisioned in staging infrastructure
        Expected: ClickHouse service running and accessible in staging
        Actual: Service not provisioned or misconfigured in staging environment
        
        Infrastructure Gap: Staging != Production in ClickHouse availability
        """
        clickhouse_host = "clickhouse.staging.netrasystems.ai"
        clickhouse_port = 8123
        
        # Test progressive connectivity validation
        connectivity_tests = [
            ("dns_resolution", self._test_dns_resolution),
            ("tcp_connectivity", self._test_tcp_connectivity),
            ("http_connectivity", self._test_http_connectivity),
            ("clickhouse_ping", self._test_clickhouse_ping)
        ]
        
        test_results = []
        
        for test_name, test_func in connectivity_tests:
            try:
                result = await test_func(clickhouse_host, clickhouse_port)
                test_results.append({
                    'test': test_name,
                    'success': result.success,
                    'response_time': result.response_time_seconds,
                    'error': result.error_message
                })
                
                if not result.success:
                    # First failure point indicates root cause
                    assert False, (
                        f"CRITICAL CLICKHOUSE PROVISIONING FAILURE at {test_name.upper()}: "
                        f"{result.error_message} "
                        f"(Response time: {result.response_time_seconds:.2f}s)\n\n"
                        f"This indicates ClickHouse service provisioning gap in staging infrastructure. "
                        f"Progressive test results:\n" +
                        "\n".join(f"  {r['test']}: {'PASS' if r['success'] else 'FAIL'}" for r in test_results)
                    )
                    
            except Exception as e:
                test_results.append({
                    'test': test_name,
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                })
                
                assert False, (
                    f"CRITICAL CLICKHOUSE TEST FAILURE at {test_name.upper()}: {str(e)}"
                )
        
        # All tests passed - ClickHouse is properly provisioned
        print(f"SUCCESS: All ClickHouse connectivity tests passed")
        print(f"Test results: {json.dumps(test_results, indent=2)}")

    @pytest.mark.env("staging")
    @pytest.mark.critical
    @pytest.mark.e2e
    def test_clickhouse_timeout_configuration_too_aggressive_for_staging(self):
        """
        EXPECTED TO FAIL - CRITICAL TIMEOUT CONFIGURATION ISSUE
        
        Issue: ClickHouse timeout settings too aggressive for staging latency
        Expected: Timeout settings accommodate staging network latency (5-10s)
        Actual: Timeout too short causing premature connection failures
        
        Configuration Issue: Dev timeouts != Staging latency requirements
        """
        # Test ClickHouse timeout configuration
        timeout_config_vars = {
            'CLICKHOUSE_TIMEOUT': {
                'min_value': 10,  # Minimum 10 seconds for staging
                'description': 'Connection timeout in seconds'
            },
            'CLICKHOUSE_CONNECT_TIMEOUT': {
                'min_value': 5,
                'description': 'Initial connection timeout'
            },
            'CLICKHOUSE_READ_TIMEOUT': {
                'min_value': 30,
                'description': 'Query execution timeout'
            },
            'CLICKHOUSE_RETRIES': {
                'min_value': 2,
                'description': 'Number of retry attempts'
            }
        }
        
        timeout_failures = []
        
        for var_name, requirements in timeout_config_vars.items():
            value = self.env.get(var_name)
            
            if value is None:
                # Use default timeout values if not configured
                default_timeouts = {
                    'CLICKHOUSE_TIMEOUT': 30,
                    'CLICKHOUSE_CONNECT_TIMEOUT': 10,
                    'CLICKHOUSE_READ_TIMEOUT': 60,
                    'CLICKHOUSE_RETRIES': 3
                }
                value = str(default_timeouts.get(var_name, 30))
            
            try:
                timeout_value = int(value)
                min_required = requirements['min_value']
                
                if timeout_value < min_required:
                    timeout_failures.append(
                        f"{var_name}: TOO SHORT - {timeout_value}s < {min_required}s required for staging latency"
                    )
                    
            except ValueError:
                timeout_failures.append(
                    f"{var_name}: INVALID - '{value}' is not a valid integer timeout value"
                )
        
        # Report timeout configuration issues
        if timeout_failures:
            failure_report = "\n".join(f"  - {failure}" for failure in timeout_failures)
            assert False, (
                f"CRITICAL CLICKHOUSE TIMEOUT MISCONFIGURATION:\n{failure_report}\n\n"
                f"Aggressive timeout settings cause premature connection failures in staging. "
                f"Staging network latency requires more generous timeouts than development. "
                f"This creates false negatives where ClickHouse is available but timeouts are too short."
            )

    # ===================================================================
    # HELPER METHODS FOR PROGRESSIVE CONNECTIVITY TESTING
    # ===================================================================
    
    async def _test_dns_resolution(self, host: str, port: int) -> ClickHouseConnectivityResult:
        """Test DNS resolution for ClickHouse host."""
        start_time = time.time()
        try:
            socket.gethostbyname(host)
            response_time = time.time() - start_time
            return ClickHouseConnectivityResult(
                test_type="dns_resolution",
                host=host,
                port=port,
                success=True,
                response_time_seconds=response_time
            )
        except socket.gaierror as e:
            response_time = time.time() - start_time
            return ClickHouseConnectivityResult(
                test_type="dns_resolution",
                host=host,
                port=port,
                success=False,
                response_time_seconds=response_time,
                error_type="DNSResolutionError",
                error_message=f"Cannot resolve {host}: {e}"
            )
    
    async def _test_tcp_connectivity(self, host: str, port: int) -> ClickHouseConnectivityResult:
        """Test raw TCP connectivity to ClickHouse."""
        start_time = time.time()
        try:
            sock = socket.create_connection((host, port), timeout=5.0)
            sock.close()
            response_time = time.time() - start_time
            return ClickHouseConnectivityResult(
                test_type="tcp_connectivity",
                host=host,
                port=port,
                success=True,
                response_time_seconds=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ClickHouseConnectivityResult(
                test_type="tcp_connectivity",
                host=host,
                port=port,
                success=False,
                response_time_seconds=response_time,
                error_type=type(e).__name__,
                error_message=f"TCP connection failed: {e}"
            )
    
    async def _test_http_connectivity(self, host: str, port: int) -> ClickHouseConnectivityResult:
        """Test HTTP connectivity to ClickHouse."""
        start_time = time.time()
        try:
            url = f"http://{host}:{port}/ping"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response_time = time.time() - start_time
                
                return ClickHouseConnectivityResult(
                    test_type="http_connectivity",
                    host=host,
                    port=port,
                    success=response.status_code == 200,
                    response_time_seconds=response_time,
                    error_message=f"HTTP status: {response.status_code}" if response.status_code != 200 else None
                )
        except Exception as e:
            response_time = time.time() - start_time
            return ClickHouseConnectivityResult(
                test_type="http_connectivity",
                host=host,
                port=port,
                success=False,
                response_time_seconds=response_time,
                error_type=type(e).__name__,
                error_message=f"HTTP request failed: {e}"
            )
    
    async def _test_clickhouse_ping(self, host: str, port: int) -> ClickHouseConnectivityResult:
        """Test ClickHouse-specific ping endpoint."""
        start_time = time.time()
        try:
            # Test ClickHouse ping endpoint
            url = f"http://{host}:{port}/"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response_time = time.time() - start_time
                
                # ClickHouse ping should return "Ok."
                success = response.status_code == 200 and "Ok" in response.text
                
                return ClickHouseConnectivityResult(
                    test_type="clickhouse_ping",
                    host=host,
                    port=port,
                    success=success,
                    response_time_seconds=response_time,
                    error_message=f"Ping response: {response.text}" if not success else None
                )
        except Exception as e:
            response_time = time.time() - start_time
            return ClickHouseConnectivityResult(
                test_type="clickhouse_ping",
                host=host,
                port=port,
                success=False,
                response_time_seconds=response_time,
                error_type=type(e).__name__,
                error_message=f"ClickHouse ping failed: {e}"
            )

    def _create_connectivity_result(
        self, 
        test_type: str,
        host: str, 
        port: int, 
        error: Optional[Exception] = None,
        response_time_ms: int = 0
    ) -> ClickHouseConnectivityResult:
        """Create standardized connectivity test result."""
        if error:
            return ClickHouseConnectivityResult(
                test_type=test_type,
                host=host,
                port=port,
                success=False,
                response_time_seconds=response_time_ms / 1000.0,
                error_type=type(error).__name__,
                error_message=str(error),
                expected_behavior="connection_success",
                actual_behavior="connection_failure",
                business_impact="analytics_system_failure"
            )
        else:
            return ClickHouseConnectivityResult(
                test_type=test_type,
                host=host,
                port=port,
                success=True,
                response_time_seconds=response_time_ms / 1000.0,
                expected_behavior="connection_success", 
                actual_behavior="connection_success",
                business_impact="analytics_system_operational"
            )


# ===================================================================
# STANDALONE RAPID EXECUTION TESTS
# ===================================================================

@pytest.mark.env("staging")
@pytest.mark.critical
@pytest.mark.e2e
async def test_clickhouse_staging_connectivity_quick_validation():
    """
    STANDALONE CRITICAL TEST - ClickHouse Connectivity
    
    EXPECTED TO FAIL: Quick validation of ClickHouse connectivity issues
    Purpose: Rapid feedback on ClickHouse provisioning and connectivity
    """
    try:
        host = "clickhouse.staging.netrasystems.ai"
        port = 8123
        
        # Quick connectivity test
        start_time = time.time()
        sock = socket.create_connection((host, port), timeout=3.0)
        sock.close()
        print(f"SUCCESS: ClickHouse quick connectivity test passed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        assert False, f"CRITICAL: ClickHouse quick connectivity failed: {e}"


if __name__ == "__main__":
    """Direct execution for rapid testing during development."""
    print("Running ClickHouse connectivity failure tests...")
    
    # Environment validation
    env = IsolatedEnvironment()
    print(f"ClickHouse Host: {env.get('CLICKHOUSE_HOST', 'NOT_SET')}")
    print(f"ClickHouse Port: {env.get('CLICKHOUSE_PORT', 'NOT_SET')}")
    print(f"ClickHouse URL: {env.get('CLICKHOUSE_URL', 'NOT_SET')}")
    
    # Run quick connectivity test
    try:
        asyncio.run(test_clickhouse_staging_connectivity_quick_validation())
    except Exception as e:
        print(f"Quick connectivity test failed: {e}")
    
    print("ClickHouse connectivity failure tests completed.")