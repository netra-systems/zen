"""
Domain Configuration Validation Tests for Issue #1278

This test suite validates domain configuration issues specific to Issue #1278:
- *.netrasystems.ai vs *.staging.netrasystems.ai domain usage
- SSL certificate validation for correct domains
- Load balancer configuration for staging domains
- CORS configuration for staging domains

These tests SHOULD FAIL to demonstrate domain configuration problems.
"""

import asyncio
import ssl
import socket
import aiohttp
import dns.resolver
from typing import Dict, List, Optional, Tuple
import pytest
from urllib.parse import urlparse

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment


class TestDomainConfiguration1278(SSotAsyncTestCase):
    """Test domain configuration issues for Issue #1278"""

    def setUp(self):
        super().setUp()
        self.env = IsolatedEnvironment()

    async def test_staging_domain_ssl_certificate_validation(self):
        """
        Test SSL certificate validation for staging domains.

        Issue #1278 mentions SSL certificate failures for *.staging.netrasystems.ai
        This test validates SSL certificates for the correct staging domains.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Domain configurations from Issue #1278
        correct_staging_domains = [
            "staging.netrasystems.ai",      # Backend/Auth
            "staging.netrasystems.ai",      # Frontend
            "api-staging.netrasystems.ai"   # WebSocket
        ]

        # Deprecated domains that cause SSL failures
        deprecated_domains = [
            "backend.staging.netrasystems.ai",
            "auth.staging.netrasystems.ai",
            "frontend.staging.netrasystems.ai",
            "api.staging.netrasystems.ai"
        ]

        ssl_validation_results = {}

        # Test correct staging domains
        for domain in correct_staging_domains:
            try:
                # Test SSL certificate validity
                context = ssl.create_default_context()

                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()

                        ssl_validation_results[domain] = {
                            "ssl_valid": True,
                            "cert_subject": cert.get('subject', []),
                            "cert_issuer": cert.get('issuer', []),
                            "cert_version": cert.get('version', 'unknown')
                        }

            except Exception as e:
                ssl_validation_results[domain] = {
                    "ssl_valid": False,
                    "error": str(e)
                }

        # Test deprecated domains (should fail)
        for domain in deprecated_domains:
            try:
                context = ssl.create_default_context()

                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()

                        ssl_validation_results[domain] = {
                            "ssl_valid": True,
                            "cert_subject": cert.get('subject', []),
                            "deprecated": True
                        }

            except Exception as e:
                ssl_validation_results[domain] = {
                    "ssl_valid": False,
                    "error": str(e),
                    "deprecated": True
                }

        print(f"SSL Certificate Validation Results:")
        for domain, result in ssl_validation_results.items():
            is_deprecated = result.get("deprecated", False)
            status = "VALID" if result["ssl_valid"] else "INVALID"
            deprecated_note = " (DEPRECATED)" if is_deprecated else ""

            print(f"  {domain}: {status}{deprecated_note}")

            if not result["ssl_valid"]:
                print(f"    Error: {result.get('error', 'Unknown')}")

        # Validate that correct domains have valid SSL
        correct_domain_failures = []
        for domain in correct_staging_domains:
            if domain in ssl_validation_results and not ssl_validation_results[domain]["ssl_valid"]:
                correct_domain_failures.append(domain)

        # This assertion SHOULD FAIL if correct staging domains have SSL issues
        self.assertEqual(len(correct_domain_failures), 0,
                        f"SSL certificate failures for correct staging domains: {correct_domain_failures}")

    async def test_staging_domain_dns_resolution(self):
        """
        Test DNS resolution for staging domains.

        Issue #1278 may involve DNS resolution issues for staging domains.
        This test validates DNS configuration.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Test DNS resolution for staging domains
        staging_domains = [
            "staging.netrasystems.ai",
            "api-staging.netrasystems.ai"
        ]

        dns_results = {}

        for domain in staging_domains:
            try:
                # Test A record resolution
                a_records = dns.resolver.resolve(domain, 'A')
                a_ips = [str(record) for record in a_records]

                # Test CNAME records if any
                cname_records = []
                try:
                    cnames = dns.resolver.resolve(domain, 'CNAME')
                    cname_records = [str(record) for record in cnames]
                except:
                    pass  # No CNAME records

                dns_results[domain] = {
                    "resolved": True,
                    "a_records": a_ips,
                    "cname_records": cname_records
                }

            except Exception as e:
                dns_results[domain] = {
                    "resolved": False,
                    "error": str(e)
                }

        print(f"DNS Resolution Results:")
        for domain, result in dns_results.items():
            status = "RESOLVED" if result["resolved"] else "FAILED"
            print(f"  {domain}: {status}")

            if result["resolved"]:
                print(f"    A records: {result['a_records']}")
                if result['cname_records']:
                    print(f"    CNAME records: {result['cname_records']}")
            else:
                print(f"    Error: {result.get('error', 'Unknown')}")

        # Validate that all staging domains resolve
        failed_domains = [domain for domain, result in dns_results.items() if not result["resolved"]]

        # This assertion SHOULD FAIL if staging domains don't resolve
        self.assertEqual(len(failed_domains), 0,
                        f"DNS resolution failures for staging domains: {failed_domains}")

    async def test_staging_domain_http_connectivity(self):
        """
        Test HTTP connectivity to staging domains.

        Issue #1278 involves 503 Service Unavailable errors.
        This test validates HTTP connectivity to staging domains.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Test HTTP connectivity to staging endpoints
        staging_endpoints = {
            "backend": "https://staging.netrasystems.ai/health",
            "api": "https://api-staging.netrasystems.ai/health",
            "frontend": "https://staging.netrasystems.ai/"
        }

        http_results = {}

        async with aiohttp.ClientSession() as session:
            for endpoint_name, url in staging_endpoints.items():
                try:
                    async with session.get(url, timeout=30) as response:
                        http_results[endpoint_name] = {
                            "success": True,
                            "status_code": response.status,
                            "url": url,
                            "headers": dict(response.headers)
                        }

                except Exception as e:
                    http_results[endpoint_name] = {
                        "success": False,
                        "error": str(e),
                        "url": url
                    }

        print(f"HTTP Connectivity Results:")
        for endpoint_name, result in http_results.items():
            status = "SUCCESS" if result["success"] else "FAILED"
            url = result["url"]

            print(f"  {endpoint_name} ({url}): {status}")

            if result["success"]:
                print(f"    Status code: {result['status_code']}")
            else:
                print(f"    Error: {result.get('error', 'Unknown')}")

        # Check for 503 Service Unavailable errors mentioned in Issue #1278
        service_unavailable_errors = []
        for endpoint_name, result in http_results.items():
            if result["success"] and result["status_code"] == 503:
                service_unavailable_errors.append(endpoint_name)

        if service_unavailable_errors:
            print(f"503 Service Unavailable errors detected: {service_unavailable_errors}")

        # This assertion SHOULD FAIL if there are connectivity issues
        failed_endpoints = [name for name, result in http_results.items() if not result["success"]]
        self.assertEqual(len(failed_endpoints), 0,
                        f"HTTP connectivity failures: {failed_endpoints}")

    def test_current_domain_configuration_validation(self):
        """
        Test current domain configuration against Issue #1278 requirements.

        This test validates that the application is configured to use the
        correct staging domains as specified in Issue #1278.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Get current domain configuration
        current_config = {
            "API_BASE_URL": self.env.get_string("API_BASE_URL", ""),
            "FRONTEND_URL": self.env.get_string("FRONTEND_URL", ""),
            "WEBSOCKET_URL": self.env.get_string("WEBSOCKET_URL", ""),
            "BACKEND_URL": self.env.get_string("BACKEND_URL", ""),
            "AUTH_SERVICE_URL": self.env.get_string("AUTH_SERVICE_URL", "")
        }

        print(f"Current Domain Configuration:")
        for key, value in current_config.items():
            print(f"  {key}: {value}")

        # Validate against correct domain patterns from Issue #1278
        domain_validation_issues = []

        # Backend/Auth should use staging.netrasystems.ai
        backend_urls = ["API_BASE_URL", "BACKEND_URL", "AUTH_SERVICE_URL"]
        for url_key in backend_urls:
            url = current_config.get(url_key, "")
            if url and "staging.netrasystems.ai" not in url:
                if ".staging.netrasystems.ai" in url:
                    domain_validation_issues.append(
                        f"{url_key}: Uses deprecated .staging.netrasystems.ai pattern: {url}"
                    )
                elif url:  # Not empty but doesn't contain staging domain
                    domain_validation_issues.append(
                        f"{url_key}: Should use staging.netrasystems.ai domain: {url}"
                    )

        # Frontend should use staging.netrasystems.ai
        frontend_url = current_config.get("FRONTEND_URL", "")
        if frontend_url and "staging.netrasystems.ai" not in frontend_url:
            if ".staging.netrasystems.ai" in frontend_url:
                domain_validation_issues.append(
                    f"FRONTEND_URL: Uses deprecated .staging.netrasystems.ai pattern: {frontend_url}"
                )
            elif frontend_url:
                domain_validation_issues.append(
                    f"FRONTEND_URL: Should use staging.netrasystems.ai domain: {frontend_url}"
                )

        # WebSocket should use api-staging.netrasystems.ai
        websocket_url = current_config.get("WEBSOCKET_URL", "")
        if websocket_url and "api-staging.netrasystems.ai" not in websocket_url:
            domain_validation_issues.append(
                f"WEBSOCKET_URL: Should use api-staging.netrasystems.ai domain: {websocket_url}"
            )

        if domain_validation_issues:
            print(f"Domain configuration issues:")
            for issue in domain_validation_issues:
                print(f"  - {issue}")

        # This assertion SHOULD FAIL if domain configuration is incorrect
        self.assertEqual(len(domain_validation_issues), 0,
                        f"Domain configuration issues: {domain_validation_issues}")

    async def test_cors_configuration_for_staging_domains(self):
        """
        Test CORS configuration for staging domains.

        Issue #1278 may involve CORS configuration issues between
        frontend and backend on staging domains.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Test CORS configuration
        frontend_url = self.env.get_string("FRONTEND_URL", "https://staging.netrasystems.ai")
        backend_url = self.env.get_string("API_BASE_URL", "https://staging.netrasystems.ai")

        cors_test_results = {}

        async with aiohttp.ClientSession() as session:
            # Test CORS preflight request
            try:
                headers = {
                    "Origin": frontend_url,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }

                async with session.options(f"{backend_url}/api/test", headers=headers, timeout=15) as response:
                    cors_headers = {
                        "access-control-allow-origin": response.headers.get("Access-Control-Allow-Origin"),
                        "access-control-allow-methods": response.headers.get("Access-Control-Allow-Methods"),
                        "access-control-allow-headers": response.headers.get("Access-Control-Allow-Headers"),
                        "access-control-allow-credentials": response.headers.get("Access-Control-Allow-Credentials")
                    }

                    cors_test_results["preflight"] = {
                        "success": True,
                        "status_code": response.status,
                        "cors_headers": cors_headers
                    }

            except Exception as e:
                cors_test_results["preflight"] = {
                    "success": False,
                    "error": str(e)
                }

        print(f"CORS Configuration Test Results:")
        for test_name, result in cors_test_results.items():
            status = "SUCCESS" if result["success"] else "FAILED"
            print(f"  {test_name}: {status}")

            if result["success"]:
                print(f"    Status code: {result['status_code']}")
                print(f"    CORS headers:")
                for header, value in result.get("cors_headers", {}).items():
                    print(f"      {header}: {value}")
            else:
                print(f"    Error: {result.get('error', 'Unknown')}")

        # Validate CORS configuration
        cors_issues = []
        if "preflight" in cors_test_results and cors_test_results["preflight"]["success"]:
            cors_headers = cors_test_results["preflight"]["cors_headers"]

            # Check if frontend origin is allowed
            allowed_origin = cors_headers.get("access-control-allow-origin")
            if allowed_origin != frontend_url and allowed_origin != "*":
                cors_issues.append(f"Frontend origin not allowed: {allowed_origin}")

        # This assertion might FAIL if CORS is misconfigured
        self.assertEqual(len(cors_issues), 0,
                        f"CORS configuration issues: {cors_issues}")


if __name__ == "__main__":
    # Run these tests to validate domain configuration for Issue #1278
    pytest.main([__file__, "-v", "--tb=short"])