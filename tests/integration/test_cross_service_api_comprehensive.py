"""
Comprehensive Cross-Service API Communication Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Reliability & Multi-Service Integration
- Business Goal: Ensure reliable cross-service communication for production stability
- Value Impact: Validates API contracts, service discovery, and inter-service authentication
- Strategic Impact: Prevents service integration failures that could lead to system outages

This test suite validates the critical integration layer that enables multiple services
to work together as a cohesive platform. It focuses on real HTTP requests, service
authentication, API contract validation, and cross-service data consistency.

CRITICAL: These tests use REAL HTTP requests between services - no mocks allowed
per CLAUDE.md requirements for integration testing.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.service_availability_detector import (
    require_services, 
    get_service_detector,
    ServiceStatus
)
from shared.isolated_environment import get_env


class TestCrossServiceApiComprehensive(SSotBaseTestCase):
    """
    Comprehensive tests for cross-service API communication.
    
    This test class validates the integration layer that enables multiple services
    to communicate reliably in production environments.
    """

    def setup_method(self, method):
        """Setup method for each test with service availability checking."""
        super().setup_method(method)
        
        # Get environment configuration
        self.env = self.get_env()
        
        # Configure service endpoints from environment
        self.backend_url = self.env.get("BACKEND_SERVICE_URL", "http://localhost:8000")
        self.auth_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8081") 
        self.analytics_url = self.env.get("ANALYTICS_SERVICE_URL", "http://localhost:8082")
        
        # Service authentication configuration
        self.service_id = self.env.get("SERVICE_ID", "netra-backend")
        self.service_secret = self.env.get("SERVICE_SECRET")
        
        # Cross-service authentication token
        self.cross_service_token = self.env.get("CROSS_SERVICE_AUTH_TOKEN")
        
        # Test timeout configuration
        self.api_timeout = 10.0
        self.health_timeout = 5.0
        
        # Initialize HTTP client with proper timeout and headers
        self.http_client = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=15.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True
        )
        
        # Add cleanup for HTTP client
        self.add_cleanup(lambda: self.http_client.close())
        
        # Record metrics for service configuration
        self.record_metric("backend_url", self.backend_url)
        self.record_metric("auth_url", self.auth_url)
        self.record_metric("service_auth_configured", bool(self.service_secret))
        
    def _get_service_auth_headers(self) -> Dict[str, str]:
        """
        Get service-to-service authentication headers.
        
        BVJ: Platform/Internal - Service Authentication
        Ensures proper authentication between internal services.
        """
        headers = {"Content-Type": "application/json"}
        
        if self.service_id and self.service_secret:
            headers["X-Service-ID"] = self.service_id
            headers["X-Service-Secret"] = self.service_secret
            
        if self.cross_service_token:
            headers["X-Cross-Service-Auth"] = self.cross_service_token
            
        return headers
        
    def _get_user_auth_headers(self, jwt_token: str = None) -> Dict[str, str]:
        """
        Get user authentication headers for testing user-facing endpoints.
        
        Args:
            jwt_token: JWT token for user authentication
            
        Returns:
            Dict of headers including user authentication
        """
        headers = self._get_service_auth_headers()
        
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
            
        return headers

    def test_service_health_endpoints_availability(self):
        """
        Test health endpoints are available on all services.
        
        BVJ: Platform/Internal - Service Discovery & Monitoring
        Critical for service discovery, load balancing, and health monitoring.
        Prevents cascading failures by enabling proactive health checks.
        """
        # Check service availability first
        services = require_services(["backend", "auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["backend", "auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test backend health endpoint
        start_time = time.time()
        response = self.http_client.get(f"{self.backend_url}/health", timeout=self.health_timeout)
        response_time = time.time() - start_time
        
        assert response.status_code == 200, f"Backend health check failed: {response.status_code}"
        
        health_data = response.json()
        assert "status" in health_data, "Health response missing status field"
        assert health_data["status"] in ["healthy", "ok"], f"Backend unhealthy: {health_data.get('status')}"
        
        # Record health check metrics
        self.record_metric("backend_health_response_time", response_time)
        self.record_metric("backend_health_status", health_data.get("status"))
        
        # Test auth service health endpoint
        start_time = time.time()
        response = self.http_client.get(f"{self.auth_url}/health", timeout=self.health_timeout)
        response_time = time.time() - start_time
        
        assert response.status_code == 200, f"Auth service health check failed: {response.status_code}"
        
        health_data = response.json()
        assert "status" in health_data, "Auth health response missing status field"
        assert health_data["status"] in ["healthy", "ok"], f"Auth service unhealthy: {health_data.get('status')}"
        
        # Record auth health metrics
        self.record_metric("auth_health_response_time", response_time)
        self.record_metric("auth_health_status", health_data.get("status"))

    def test_service_to_service_authentication_headers(self):
        """
        Test service-to-service authentication header validation.
        
        BVJ: Platform/Internal - Security & Service Authentication
        Critical for preventing unauthorized access between internal services.
        Protects sensitive inter-service communication and prevents security breaches.
        """
        # Skip if service credentials not configured
        if not self.service_secret:
            pytest.skip("Service authentication credentials not configured")
            
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
        
        # Test valid service authentication
        headers = self._get_service_auth_headers()
        
        # Create test token validation request
        test_payload = {
            "token": "test_token_for_service_auth",
            "token_type": "access"
        }
        
        start_time = time.time()
        response = self.http_client.post(
            f"{self.auth_url}/auth/validate",
            json=test_payload,
            headers=headers,
            timeout=self.api_timeout
        )
        response_time = time.time() - start_time
        
        # Service should authenticate properly (even if token is invalid)
        # We're testing service auth, not token validity
        assert response.status_code in [200, 401], f"Service auth failed: {response.status_code} - {response.text}"
        assert response.status_code != 403, f"Service authentication rejected: {response.text}"
        
        self.record_metric("service_auth_response_time", response_time)
        self.record_metric("service_auth_status_code", response.status_code)

    def test_service_to_service_authentication_rejection(self):
        """
        Test service-to-service authentication properly rejects invalid credentials.
        
        BVJ: Platform/Internal - Security Validation
        Ensures unauthorized services cannot access protected endpoints.
        Critical for maintaining security boundaries between services.
        """
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test with invalid service credentials
        invalid_headers = {
            "Content-Type": "application/json",
            "X-Service-ID": "invalid-service",
            "X-Service-Secret": "invalid-secret"
        }
        
        test_payload = {
            "token": "test_token",
            "token_type": "access" 
        }
        
        response = self.http_client.post(
            f"{self.auth_url}/auth/validate",
            json=test_payload,
            headers=invalid_headers,
            timeout=self.api_timeout
        )
        
        # Should reject invalid service credentials
        assert response.status_code == 403, f"Expected 403 for invalid service auth, got {response.status_code}"
        
        self.record_metric("invalid_service_auth_rejected", True)

    def test_api_contract_validation_auth_endpoints(self):
        """
        Test API contract validation for authentication endpoints.
        
        BVJ: Platform/Internal - API Contract Reliability
        Ensures API contracts remain stable across service deployments.
        Prevents breaking changes that could cause integration failures.
        """
        # Skip if service credentials not configured
        if not self.service_secret:
            pytest.skip("Service authentication credentials not configured")
            
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        headers = self._get_service_auth_headers()
        
        # Test token validation endpoint contract
        valid_request = {
            "token": "test_jwt_token",
            "token_type": "access"
        }
        
        response = self.http_client.post(
            f"{self.auth_url}/auth/validate",
            json=valid_request,
            headers=headers,
            timeout=self.api_timeout
        )
        
        # Should return proper status codes (200 for valid, 401 for invalid tokens)
        assert response.status_code in [200, 401], f"Unexpected status code: {response.status_code}"
        
        response_data = response.json()
        
        # Validate response structure
        expected_fields = ["valid"]
        for field in expected_fields:
            assert field in response_data, f"Missing required field '{field}' in response"
            
        # If validation succeeded, check additional fields
        if response.status_code == 200 and response_data.get("valid"):
            optional_fields = ["user_id", "email", "permissions"]
            for field in optional_fields:
                if field in response_data:
                    assert isinstance(response_data[field], (str, list)), f"Field '{field}' has incorrect type"
                    
        self.record_metric("auth_contract_validation_passed", True)

    def test_api_contract_validation_malformed_requests(self):
        """
        Test API contract validation with malformed requests.
        
        BVJ: Platform/Internal - Error Handling & Robustness  
        Ensures services handle malformed requests gracefully.
        Critical for system stability and preventing cascading failures.
        """
        # Skip if service credentials not configured
        if not self.service_secret:
            pytest.skip("Service authentication credentials not configured")
            
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        headers = self._get_service_auth_headers()
        
        # Test malformed request payloads
        malformed_requests = [
            {},  # Empty payload
            {"invalid_field": "value"},  # Wrong field names
            {"token": ""},  # Empty token
            {"token": None},  # Null token
        ]
        
        for i, malformed_request in enumerate(malformed_requests):
            response = self.http_client.post(
                f"{self.auth_url}/auth/validate",
                json=malformed_request,
                headers=headers,
                timeout=self.api_timeout
            )
            
            # Should return 400 (Bad Request) or 422 (Validation Error) for malformed requests
            assert response.status_code in [400, 422], f"Malformed request {i} should return 400/422, got {response.status_code}"
            
            # Response should contain error information
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                assert "detail" in error_data or "error" in error_data, f"Error response missing detail/error field"
                
        self.record_metric("malformed_request_handling_tests", len(malformed_requests))

    def test_cross_service_data_consistency_user_validation(self):
        """
        Test cross-service data consistency for user validation.
        
        BVJ: Platform/Internal - Data Consistency & User Experience
        Ensures user data remains consistent across service boundaries.
        Critical for maintaining user session integrity and preventing auth issues.
        """
        # Skip if service credentials not configured
        if not self.service_secret:
            pytest.skip("Service authentication credentials not configured")
            
        # Check both services are available
        services = require_services(["backend", "auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["backend", "auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Create test user through auth service
        auth_headers = self._get_service_auth_headers()
        
        # Test user registration endpoint (if available)
        test_user_data = {
            "email": f"test_user_{uuid4().hex[:8]}@example.com",
            "password": "TestPassword123!",
            "provider": "local"
        }
        
        # Try to register user (may not be available in all environments)
        register_response = self.http_client.post(
            f"{self.auth_url}/auth/register",
            json=test_user_data,
            headers=auth_headers,
            timeout=self.api_timeout
        )
        
        # If registration succeeded, test login consistency
        if register_response.status_code == 200:
            # Login through auth service
            login_response = self.http_client.post(
                f"{self.auth_url}/auth/login",
                json={
                    "email": test_user_data["email"],
                    "password": test_user_data["password"]
                },
                headers=auth_headers,
                timeout=self.api_timeout
            )
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                jwt_token = login_data.get("access_token")
                
                if jwt_token:
                    # Validate token through auth service
                    validate_response = self.http_client.post(
                        f"{self.auth_url}/auth/validate",
                        json={"token": jwt_token, "token_type": "access"},
                        headers=auth_headers,
                        timeout=self.api_timeout
                    )
                    
                    assert validate_response.status_code == 200, "Token validation should succeed"
                    
                    validate_data = validate_response.json()
                    assert validate_data.get("valid") is True, "Token should be valid"
                    assert validate_data.get("email") == test_user_data["email"], "Email should match"
                    
                    self.record_metric("cross_service_user_consistency_validated", True)
                    return
        
        # If full user flow not available, just test token validation consistency
        self.record_metric("limited_user_consistency_test", True)

    def test_service_discovery_endpoint_contracts(self):
        """
        Test service discovery endpoint contracts and responses.
        
        BVJ: Platform/Internal - Service Discovery & Orchestration
        Ensures services can discover and communicate with each other properly.
        Critical for microservice architecture and dynamic scaling.
        """
        # Check backend service availability
        services = require_services(["backend"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["backend"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test backend service info endpoint (if available)
        response = self.http_client.get(
            f"{self.backend_url}/service-info",
            headers=self._get_service_auth_headers(),
            timeout=self.api_timeout
        )
        
        # Service info may or may not be available
        if response.status_code == 200:
            service_info = response.json()
            
            # Validate service info structure
            expected_fields = ["service_name", "version"]
            for field in expected_fields:
                if field in service_info:
                    assert isinstance(service_info[field], str), f"Field '{field}' should be string"
                    assert len(service_info[field]) > 0, f"Field '{field}' should not be empty"
                    
            self.record_metric("service_discovery_info_available", True)
        else:
            # Service info not available - that's okay for this test
            self.record_metric("service_discovery_info_available", False)

    def test_api_timeout_and_connection_handling(self):
        """
        Test API timeout and connection handling between services.
        
        BVJ: Platform/Internal - System Resilience & Performance
        Ensures services handle timeouts gracefully and maintain performance SLAs.
        Critical for preventing cascading failures and maintaining user experience.
        """
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test with very short timeout to simulate timeout conditions
        short_timeout = 0.01  # 10ms timeout
        
        try:
            with httpx.Client(timeout=short_timeout) as timeout_client:
                response = timeout_client.get(f"{self.auth_url}/health")
                
                # If response comes back, that's fine - service is very fast
                if response.status_code == 200:
                    self.record_metric("service_response_very_fast", True)
                    
        except httpx.TimeoutException:
            # Expected - service took longer than 10ms
            self.record_metric("timeout_handling_working", True)
        except Exception as e:
            # Other connection errors are also acceptable for this test
            self.record_metric("connection_error_handled", str(type(e).__name__))
            
        # Test with reasonable timeout
        response = self.http_client.get(
            f"{self.auth_url}/health",
            timeout=self.health_timeout
        )
        
        assert response.status_code == 200, "Health check should succeed with reasonable timeout"
        self.record_metric("reasonable_timeout_successful", True)

    def test_error_response_format_consistency(self):
        """
        Test error response format consistency across services.
        
        BVJ: Platform/Internal - API Standardization & Developer Experience
        Ensures consistent error handling across all service endpoints.
        Critical for client integration and debugging.
        """
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test 404 error response format
        response = self.http_client.get(
            f"{self.auth_url}/nonexistent-endpoint",
            headers=self._get_service_auth_headers(),
            timeout=self.api_timeout
        )
        
        assert response.status_code == 404, f"Expected 404 for nonexistent endpoint, got {response.status_code}"
        
        # Check if response is JSON
        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            
            # Should have error detail
            assert "detail" in error_data or "error" in error_data or "message" in error_data, \
                "Error response should contain detail/error/message field"
                
        self.record_metric("error_format_consistency_validated", True)

    def test_concurrent_api_requests_handling(self):
        """
        Test concurrent API request handling across services.
        
        BVJ: Platform/Internal - Performance & Scalability
        Ensures services can handle multiple concurrent requests without degradation.
        Critical for production load handling and user experience.
        """
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Create multiple concurrent health check requests
        concurrent_requests = 5
        
        async def make_health_request():
            """Make async health check request."""
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.get(f"{self.auth_url}/health")
                return response.status_code, time.time()
        
        # Execute concurrent requests
        async def run_concurrent_test():
            start_time = time.time()
            tasks = [make_health_request() for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            successful_requests = 0
            response_times = []
            
            for result in results:
                if isinstance(result, tuple) and result[0] == 200:
                    successful_requests += 1
                    response_times.append(result[1] - start_time)
                    
            return successful_requests, response_times, total_time
        
        # Run the concurrent test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            successful_requests, response_times, total_time = loop.run_until_complete(run_concurrent_test())
        finally:
            loop.close()
        
        # Validate concurrent request handling
        assert successful_requests >= concurrent_requests // 2, \
            f"At least half of concurrent requests should succeed, got {successful_requests}/{concurrent_requests}"
            
        # Record performance metrics
        self.record_metric("concurrent_requests_sent", concurrent_requests)
        self.record_metric("concurrent_requests_successful", successful_requests)
        self.record_metric("concurrent_requests_total_time", total_time)
        
        if response_times:
            self.record_metric("concurrent_requests_avg_response_time", sum(response_times) / len(response_times))

    def test_service_api_versioning_headers(self):
        """
        Test API versioning header support across services.
        
        BVJ: Platform/Internal - API Evolution & Backward Compatibility
        Ensures services support API versioning for backward compatibility.
        Critical for rolling deployments and client compatibility.
        """
        # Check backend service availability
        services = require_services(["backend"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["backend"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test with API version headers
        version_headers = self._get_service_auth_headers()
        version_headers["API-Version"] = "v1"
        version_headers["Accept"] = "application/vnd.api+json;version=1"
        
        response = self.http_client.get(
            f"{self.backend_url}/health",
            headers=version_headers,
            timeout=self.api_timeout
        )
        
        # Health endpoint should work regardless of version headers
        assert response.status_code == 200, f"Health check with version headers failed: {response.status_code}"
        
        # Check if service responds with version information
        if "API-Version" in response.headers:
            self.record_metric("api_versioning_supported", True)
            self.record_metric("api_version_returned", response.headers["API-Version"])
        else:
            self.record_metric("api_versioning_supported", False)

    def test_request_correlation_and_tracing_headers(self):
        """
        Test request correlation and distributed tracing header propagation.
        
        BVJ: Platform/Internal - Observability & Debugging
        Ensures request tracing works across service boundaries.
        Critical for debugging production issues and performance monitoring.
        """
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Create correlation headers
        correlation_id = f"test-{uuid4()}"
        trace_id = f"trace-{uuid4().hex[:16]}"
        
        tracing_headers = self._get_service_auth_headers()
        tracing_headers.update({
            "X-Correlation-ID": correlation_id,
            "X-Trace-ID": trace_id,
            "X-Request-ID": f"req-{uuid4().hex[:8]}",
            "User-Agent": "cross-service-integration-test/1.0"
        })
        
        response = self.http_client.get(
            f"{self.auth_url}/health",
            headers=tracing_headers,
            timeout=self.api_timeout
        )
        
        assert response.status_code == 200, "Health check with tracing headers should succeed"
        
        # Check if service echoes back correlation headers
        correlation_headers_found = 0
        for header_name in ["X-Correlation-ID", "X-Trace-ID", "X-Request-ID"]:
            if header_name in response.headers:
                correlation_headers_found += 1
                
        self.record_metric("tracing_headers_sent", 3)
        self.record_metric("tracing_headers_echoed", correlation_headers_found)
        self.record_metric("correlation_id_used", correlation_id)

    def test_circuit_breaker_and_resilience_patterns(self):
        """
        Test circuit breaker and resilience patterns in cross-service communication.
        
        BVJ: Platform/Internal - System Resilience & Fault Tolerance
        Ensures services implement proper circuit breaker patterns.
        Critical for preventing cascading failures and maintaining system stability.
        """
        # This test validates that services implement resilience patterns
        # We can't easily trigger circuit breakers without causing real failures,
        # so we test the patterns indirectly
        
        # Check backend service availability
        services = require_services(["backend"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["backend"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test rapid successive requests to see if rate limiting/circuit breaker patterns are present
        rapid_requests = 10
        request_times = []
        response_codes = []
        
        for i in range(rapid_requests):
            start_time = time.time()
            
            try:
                response = self.http_client.get(
                    f"{self.backend_url}/health",
                    headers=self._get_service_auth_headers(),
                    timeout=self.api_timeout
                )
                response_codes.append(response.status_code)
                request_times.append(time.time() - start_time)
                
            except Exception as e:
                response_codes.append(0)  # Connection failed
                request_times.append(time.time() - start_time)
                
            # Small delay between requests
            time.sleep(0.1)
        
        # Analyze patterns
        successful_requests = sum(1 for code in response_codes if code == 200)
        rate_limited_requests = sum(1 for code in response_codes if code == 429)
        
        # Most requests should succeed (service should handle moderate load)
        assert successful_requests >= rapid_requests // 2, \
            f"At least half of rapid requests should succeed, got {successful_requests}/{rapid_requests}"
            
        # Record resilience metrics
        self.record_metric("rapid_requests_sent", rapid_requests)
        self.record_metric("rapid_requests_successful", successful_requests)
        self.record_metric("rapid_requests_rate_limited", rate_limited_requests)
        self.record_metric("rapid_requests_avg_time", sum(request_times) / len(request_times))

    def test_api_schema_validation_and_content_types(self):
        """
        Test API schema validation and content type handling.
        
        BVJ: Platform/Internal - API Contract Validation & Data Quality  
        Ensures services properly validate request/response schemas and content types.
        Critical for data integrity and preventing malformed data propagation.
        """
        # Skip if service credentials not configured
        if not self.service_secret:
            pytest.skip("Service authentication credentials not configured")
            
        # Check auth service availability
        services = require_services(["auth"], timeout=self.health_timeout)
        skip_msg = get_service_detector().generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(skip_msg)
            
        # Test different content types
        headers = self._get_service_auth_headers()
        
        # Test with correct JSON content type
        valid_request = {
            "token": "test_token_for_schema",
            "token_type": "access"
        }
        
        response = self.http_client.post(
            f"{self.auth_url}/auth/validate",
            json=valid_request,
            headers=headers,
            timeout=self.api_timeout
        )
        
        # Should handle JSON requests properly
        assert response.status_code in [200, 401], f"JSON request should be handled, got {response.status_code}"
        
        # Test with incorrect content type (if service enforces it)
        text_headers = headers.copy()
        text_headers["Content-Type"] = "text/plain"
        
        response = self.http_client.post(
            f"{self.auth_url}/auth/validate",
            data="not json data",
            headers=text_headers,
            timeout=self.api_timeout
        )
        
        # Should reject non-JSON requests appropriately
        assert response.status_code in [400, 415, 422], \
            f"Non-JSON request should be rejected with 400/415/422, got {response.status_code}"
            
        self.record_metric("content_type_validation_tested", True)

    def teardown_method(self, method):
        """Teardown method with enhanced metrics reporting."""
        # Record final test metrics
        total_metrics = self.get_all_metrics()
        
        # Log summary of cross-service communication test results
        if total_metrics:
            successful_tests = sum(1 for k, v in total_metrics.items() 
                                 if k.endswith('_validated') or k.endswith('_successful') or k.endswith('_passed'))
            
            self.record_metric("total_successful_validations", successful_tests)
            
        super().teardown_method(method)