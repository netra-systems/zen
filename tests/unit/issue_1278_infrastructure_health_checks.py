"""
Level 1: Quick health checks for Issue #1278 infrastructure validation.
These tests should complete in under 10 minutes and require no Docker.

Following TEST_CREATION_GUIDE.md and CLAUDE.md best practices:
- Non-Docker tests as primary validation method
- Real service testing (no mocks for infrastructure validation)
- Business-focused validation ($500K+ ARR protection)
- Clear PASS/FAIL criteria for infrastructure status
"""
import pytest
import asyncio
import httpx
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime
import logging
import ssl
import socket
from urllib.parse import urlparse

# Configure logging for infrastructure validation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InfrastructureHealthValidator:
    """Quick health checks for Issue #1278 infrastructure components."""

    def __init__(self):
        self.staging_domains = {
            "backend": "https://staging.netrasystems.ai",
            "auth": "https://auth.staging.netrasystems.ai",
            "api": "https://api.staging.netrasystems.ai"
        }
        self.timeout_settings = {
            "connection_timeout": 10.0,
            "read_timeout": 30.0,
            "health_check_timeout": 15.0
        }

    def get_ssl_certificate_info(self, hostname: str, port: int = 443) -> Optional[Dict]:
        """Get SSL certificate information for validation."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    return {
                        "subject": cert.get("subject"),
                        "issuer": cert.get("issuer"),
                        "version": cert.get("version"),
                        "notAfter": cert.get("notAfter"),
                        "subjectAltName": cert.get("subjectAltName", [])
                    }
        except Exception as e:
            logger.error(f"SSL certificate check failed for {hostname}: {e}")
            return None

    def validate_domain_in_certificate(self, cert_info: Dict, expected_domain: str) -> bool:
        """Validate that domain is covered by SSL certificate."""
        if not cert_info:
            return False

        # Check subject alternative names
        san_list = cert_info.get("subjectAltName", [])
        for san_type, san_value in san_list:
            if san_type == "DNS":
                if san_value == expected_domain or san_value == f"*.{expected_domain.split('.', 1)[1]}":
                    return True

        return False


@pytest.mark.issue_1278
@pytest.mark.infrastructure
@pytest.mark.unit
class TestLevel1QuickHealthChecks:
    """Level 1: Quick infrastructure health validation for Issue #1278."""

    def test_staging_domain_ssl_certificates(self):
        """
        Validate SSL certificates for *.netrasystems.ai domains.

        Business Impact: SSL certificate issues cause complete service unavailability
        Issue #1278 Component: SSL Certificate validation under load
        """
        validator = InfrastructureHealthValidator()
        ssl_results = {}

        for service, url in validator.staging_domains.items():
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname

            logger.info(f"Testing SSL certificate for {service}: {hostname}")

            # Get SSL certificate information
            cert_info = validator.get_ssl_certificate_info(hostname)

            if cert_info is None:
                pytest.fail(f"❌ SSL Certificate FAILED for {service}: {hostname} - Cannot retrieve certificate")

            # Validate domain coverage
            domain_valid = validator.validate_domain_in_certificate(cert_info, hostname)

            ssl_results[service] = {
                "hostname": hostname,
                "certificate_valid": cert_info is not None,
                "domain_covered": domain_valid,
                "issuer": str(cert_info.get("issuer", "Unknown")) if cert_info else "Unknown"
            }

            # PASS criteria: SSL certificate exists and covers the domain
            assert cert_info is not None, f"❌ SSL Certificate missing for {service}: {hostname}"
            assert domain_valid, f"❌ SSL Certificate does not cover domain {hostname} for {service}"

            logger.info(f"✅ SSL Certificate OK for {service}: {hostname}")

        # Log summary of SSL validation
        logger.info("SSL Certificate Validation Summary:")
        for service, result in ssl_results.items():
            logger.info(f"  {service}: ✅ Valid SSL for {result['hostname']}")

    def test_basic_http_connectivity_no_503_errors(self):
        """
        Test basic HTTP connectivity without authentication.

        Business Impact: HTTP 503 errors block all user access ($500K+ ARR impact)
        Issue #1278 Component: VPC connector capacity and load balancer configuration
        """
        validator = InfrastructureHealthValidator()
        connectivity_results = {}

        for service, url in validator.staging_domains.items():
            logger.info(f"Testing HTTP connectivity for {service}: {url}")

            with httpx.Client(timeout=30.0, verify=True) as client:
                start_time = time.time()
                try:
                    # Test basic connectivity to health endpoint
                    response = client.get(f"{url}/health")
                    connection_time = time.time() - start_time

                    connectivity_results[service] = {
                        "url": url,
                        "status_code": response.status_code,
                        "response_time": connection_time,
                        "headers": dict(response.headers),
                        "no_503_error": response.status_code != 503
                    }

                    # CRITICAL: NOT HTTP 503 (any other response indicates infrastructure working)
                    assert response.status_code != 503, f"❌ HTTP 503 Service Unavailable for {service}: {url} - Issue #1278 infrastructure failure"

                    # Log successful connection
                    logger.info(f"✅ HTTP Response {response.status_code} for {service} in {connection_time:.2f}s")

                    # Warn on slow responses but don't fail (may be application issue)
                    if connection_time > 10.0:
                        logger.warning(f"⚠️ SLOW RESPONSE: {service} took {connection_time:.2f}s (may indicate VPC connector stress)")

                except httpx.TimeoutException:
                    connectivity_results[service] = {
                        "url": url,
                        "error": "timeout",
                        "response_time": 30.0,
                        "no_503_error": False
                    }
                    pytest.fail(f"❌ TIMEOUT: {service} health check exceeded 30s - VPC connector likely overwhelmed")

                except httpx.ConnectError as e:
                    connectivity_results[service] = {
                        "url": url,
                        "error": str(e),
                        "response_time": time.time() - start_time,
                        "no_503_error": False
                    }
                    pytest.fail(f"❌ CONNECTION ERROR: {service} - {e} - Infrastructure connectivity failure")

        # Log connectivity summary
        logger.info("HTTP Connectivity Validation Summary:")
        for service, result in connectivity_results.items():
            if result.get("no_503_error"):
                logger.info(f"  {service}: ✅ HTTP {result['status_code']} ({result['response_time']:.2f}s)")
            else:
                logger.error(f"  {service}: ❌ Connection failed")

    def test_load_balancer_consistency_validation(self):
        """
        Validate load balancer is properly routing requests consistently.

        Business Impact: Load balancer failures cause intermittent service access
        Issue #1278 Component: Load balancer health check configuration
        """
        validator = InfrastructureHealthValidator()
        load_balancer_results = {}

        for service, url in validator.staging_domains.items():
            logger.info(f"Testing load balancer consistency for {service}: {url}")

            response_codes = []
            response_times = []
            server_headers = []

            # Test multiple requests to check load balancer consistency
            for i in range(5):  # 5 quick requests to test consistency
                with httpx.Client(timeout=15.0, verify=True) as client:
                    start_time = time.time()
                    try:
                        response = client.get(f"{url}/health")
                        response_time = time.time() - start_time

                        response_codes.append(response.status_code)
                        response_times.append(response_time)

                        # Track server headers to detect load balancer routing
                        server_header = response.headers.get("server", "unknown")
                        server_headers.append(server_header)

                        logger.debug(f"Request {i+1}: HTTP {response.status_code} ({response_time:.2f}s)")

                    except httpx.TimeoutException:
                        response_codes.append(0)  # Timeout
                        response_times.append(15.0)
                        server_headers.append("timeout")
                        logger.warning(f"Request {i+1}: Timeout")

                    except Exception as e:
                        response_codes.append(0)  # Connection failure
                        response_times.append(15.0)
                        server_headers.append("error")
                        logger.warning(f"Request {i+1}: Error - {e}")

                # Small delay between requests
                time.sleep(0.5)

            # Analyze load balancer consistency
            load_balancer_results[service] = {
                "url": url,
                "response_codes": response_codes,
                "response_times": response_times,
                "server_headers": server_headers,
                "consistent_responses": len(set(response_codes)) <= 2,  # Allow some variation
                "avg_response_time": sum(response_times) / len(response_times)
            }

            # PASS criteria: Consistent responses (not all 503 or timeouts)
            non_503_responses = [code for code in response_codes if code != 503 and code != 0]
            assert len(non_503_responses) >= 3, f"❌ Load balancer failing for {service}: {response_codes} - Majority HTTP 503/timeout errors"

            # Validate response time consistency (no extreme outliers)
            avg_time = load_balancer_results[service]["avg_response_time"]
            max_time = max(response_times)
            assert max_time < (avg_time * 3), f"❌ Load balancer inconsistent for {service}: max {max_time:.2f}s vs avg {avg_time:.2f}s"

            logger.info(f"✅ Load balancer consistent for {service}: {response_codes}, avg {avg_time:.2f}s")

        # Log load balancer summary
        logger.info("Load Balancer Validation Summary:")
        for service, result in load_balancer_results.items():
            logger.info(f"  {service}: ✅ Consistent routing, avg {result['avg_response_time']:.2f}s")

    def test_vpc_connector_basic_capacity_validation(self):
        """
        Basic validation that VPC connector has sufficient capacity.

        Business Impact: VPC connector saturation causes widespread HTTP 503 errors
        Issue #1278 Component: VPC connector scaling (staging-connector capacity)
        """
        validator = InfrastructureHealthValidator()
        vpc_results = {
            "total_services": len(validator.staging_domains),
            "successful_connections": 0,
            "failed_connections": 0,
            "connection_times": [],
            "service_results": {}
        }

        logger.info("Testing VPC connector capacity for Issue #1278...")

        for service, url in validator.staging_domains.items():
            logger.info(f"Testing VPC connector capacity for {service}: {url}")

            try:
                with httpx.Client(timeout=20.0, verify=True) as client:
                    start_time = time.time()

                    # Test connection establishment (any response indicates VPC working)
                    response = client.get(f"{url}/health")
                    connection_time = time.time() - start_time

                    vpc_results["connection_times"].append(connection_time)
                    vpc_results["service_results"][service] = {
                        "status_code": response.status_code,
                        "connection_time": connection_time,
                        "success": True
                    }

                    # Any response (even error) means VPC connector allowing connections
                    if response.status_code in [200, 500, 404, 401, 403]:
                        vpc_results["successful_connections"] += 1
                        logger.info(f"✅ VPC connector allows connection to {service}: HTTP {response.status_code} ({connection_time:.2f}s)")
                    elif response.status_code == 503:
                        logger.warning(f"⚠️ Service unavailable for {service}: HTTP 503 (may indicate VPC capacity issues)")
                        vpc_results["failed_connections"] += 1

            except httpx.ConnectTimeout:
                vpc_results["failed_connections"] += 1
                vpc_results["service_results"][service] = {
                    "error": "timeout",
                    "success": False
                }
                logger.error(f"❌ Connection timeout for {service} (VPC connector likely saturated)")

            except httpx.ConnectError as e:
                vpc_results["failed_connections"] += 1
                vpc_results["service_results"][service] = {
                    "error": str(e),
                    "success": False
                }
                logger.error(f"❌ Connection error for {service}: {e} (VPC connector issue)")

        # Analyze VPC connector capacity
        total_services = vpc_results["total_services"]
        successful = vpc_results["successful_connections"]

        # PASS criteria: At least 66% of services responsive (VPC connector working)
        success_rate = successful / total_services
        assert success_rate >= 0.66, f"❌ VPC connector appears overwhelmed: {successful}/{total_services} connections successful ({success_rate:.1%})"

        # Validate connection times reasonable
        if vpc_results["connection_times"]:
            avg_connection_time = sum(vpc_results["connection_times"]) / len(vpc_results["connection_times"])
            assert avg_connection_time < 15.0, f"❌ VPC connector performance degraded: {avg_connection_time:.2f}s average connection time"

            logger.info(f"✅ VPC connector performance acceptable: {avg_connection_time:.2f}s average")

        # Log VPC connector summary
        if success_rate == 1.0:
            logger.info(f"✅ VPC connector fully operational: {successful}/{total_services} services accessible")
        else:
            logger.info(f"⚠️ VPC connector partially operational: {successful}/{total_services} services accessible ({success_rate:.1%})")

    @pytest.mark.asyncio
    async def test_concurrent_connection_basic_load(self):
        """
        Test basic concurrent connection handling (light load test).

        Business Impact: Infrastructure must handle multiple simultaneous users
        Issue #1278 Component: VPC connector concurrent capacity
        """
        validator = InfrastructureHealthValidator()

        # Light concurrent load (10 connections) to test basic capacity
        concurrent_requests = 10

        async def make_concurrent_request(session: httpx.AsyncClient, url: str, request_id: int) -> Dict:
            start_time = time.time()
            try:
                response = await session.get(f"{url}/health", timeout=20.0)
                connection_time = time.time() - start_time

                return {
                    "request_id": request_id,
                    "url": url,
                    "status_code": response.status_code,
                    "connection_time": connection_time,
                    "success": response.status_code != 503
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "url": url,
                    "status_code": 0,
                    "connection_time": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                }

        # Execute concurrent requests
        all_results = []

        async with httpx.AsyncClient(verify=True) as session:
            tasks = []

            # Create concurrent requests across all services
            for i in range(concurrent_requests):
                service_urls = list(validator.staging_domains.values())
                url = service_urls[i % len(service_urls)]
                task = make_concurrent_request(session, url, i)
                tasks.append(task)

            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results = [r for r in results if isinstance(r, dict)]

        # Analyze concurrent load results
        total_requests = len(all_results)
        successful_requests = len([r for r in all_results if r["success"]])
        http_503_errors = len([r for r in all_results if r["status_code"] == 503])

        logger.info(f"Concurrent connection test results:")
        logger.info(f"  Total requests: {total_requests}")
        logger.info(f"  Successful: {successful_requests}")
        logger.info(f"  HTTP 503 errors: {http_503_errors}")

        # PASS criteria: < 30% HTTP 503 errors under light concurrent load
        if total_requests > 0:
            failure_rate = http_503_errors / total_requests
            assert failure_rate < 0.30, f"❌ High HTTP 503 failure rate under light load: {failure_rate:.1%} - VPC connector likely overwhelmed"

            if failure_rate == 0:
                logger.info(f"✅ Zero HTTP 503 errors under concurrent load - VPC connector handling capacity well")
            else:
                logger.info(f"⚠️ Some HTTP 503 errors ({failure_rate:.1%}) but within acceptable range for light load")

        # Validate reasonable response times
        connection_times = [r["connection_time"] for r in all_results if r["success"]]
        if connection_times:
            avg_time = sum(connection_times) / len(connection_times)
            max_time = max(connection_times)

            assert avg_time < 10.0, f"❌ Poor performance under concurrent load: {avg_time:.2f}s average"
            assert max_time < 20.0, f"❌ Some requests very slow under concurrent load: {max_time:.2f}s maximum"

            logger.info(f"✅ Concurrent load performance acceptable: {avg_time:.2f}s avg, {max_time:.2f}s max")