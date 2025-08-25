"""
HTTP method monitoring compatibility tests for auth service.

These tests target the 405 Method Not Allowed errors seen in staging logs
when monitoring systems use HEAD requests on health endpoints. Monitoring
systems commonly use HEAD requests to check endpoint availability without
downloading response bodies.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from auth_service.main import app
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_service,
    pytest.mark.http_methods,
    pytest.mark.monitoring
]

class TestHealthEndpointHeadSupport:
    """Test HEAD method support for health check endpoints."""
    
    def setup_method(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    def test_root_health_endpoint_head_method(self):
        """
        Test HEAD method support on /health endpoint.
        
        EXPECTED FAILURE: Currently returns 405 Method Not Allowed.
        Staging logs show monitoring systems failing with HEAD requests.
        """
        # First verify GET works
        get_response = self.client.get("/health")
        assert get_response.status_code == 200, "GET /health should work"
        
        # Now test HEAD method - this is currently failing
        head_response = self.client.head("/health")
        
        # This assertion will fail - HEAD method is not currently supported
        assert head_response.status_code == 200, \
            f"HEAD /health should return 200 (monitoring compatibility), got {head_response.status_code}"
        
        # HEAD response should have same headers as GET but empty body
        assert len(head_response.content) == 0, "HEAD response should have empty body"
        
        # Content-Type should match GET response
        get_content_type = get_response.headers.get("content-type", "").lower()
        head_content_type = head_response.headers.get("content-type", "").lower()
        assert "json" in head_content_type or head_content_type == get_content_type, \
            f"HEAD Content-Type should indicate JSON: {head_content_type}"
    
    def test_auth_health_endpoint_head_method(self):
        """
        Test HEAD method support on /auth/health endpoint.
        
        EXPECTED FAILURE: Currently returns 405 Method Not Allowed.
        """
        # First verify GET works
        get_response = self.client.get("/auth/health")
        assert get_response.status_code == 200, "GET /auth/health should work"
        
        # Test HEAD method
        head_response = self.client.head("/auth/health")
        
        # This will fail - HEAD not supported
        assert head_response.status_code == 200, \
            f"HEAD /auth/health should return 200, got {head_response.status_code}"
        
        assert len(head_response.content) == 0, "HEAD response should have empty body"
    
    def test_readiness_endpoint_head_method(self):
        """
        Test HEAD method support on readiness endpoints.
        
        EXPECTED FAILURE: Readiness endpoints likely don't support HEAD.
        """
        readiness_endpoints = ["/readiness", "/health/ready"]
        
        for endpoint in readiness_endpoints:
            # Verify GET works first
            get_response = self.client.get(endpoint)
            if get_response.status_code not in [200, 503]:
                pytest.skip(f"GET {endpoint} returned unexpected status {get_response.status_code}")
            
            # Test HEAD method
            head_response = self.client.head(endpoint)
            
            # Should return same status as GET, not 405
            assert head_response.status_code != 405, \
                f"HEAD {endpoint} should not return 405 Method Not Allowed"
            
            # Should return same status as GET  
            assert head_response.status_code == get_response.status_code, \
                f"HEAD {endpoint} status {head_response.status_code} should match GET status {get_response.status_code}"

class TestDocumentationEndpointHeadSupport:
    """Test HEAD method support for documentation endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_openapi_json_head_method(self):
        """
        Test HEAD method on /openapi.json endpoint.
        
        EXPECTED FAILURE: Documentation endpoints may not support HEAD.
        Monitoring systems often check API documentation availability.
        """
        # Verify GET works
        get_response = self.client.get("/openapi.json")
        if get_response.status_code != 200:
            pytest.skip(f"GET /openapi.json not available: {get_response.status_code}")
        
        # Test HEAD method
        head_response = self.client.head("/openapi.json")
        
        # Should support HEAD for monitoring
        assert head_response.status_code == 200, \
            f"HEAD /openapi.json should return 200, got {head_response.status_code}"
        
        assert len(head_response.content) == 0, "HEAD response should have empty body"
        
        # Should indicate JSON content
        content_type = head_response.headers.get("content-type", "")
        assert "json" in content_type.lower(), \
            f"HEAD /openapi.json should have JSON Content-Type: {content_type}"
    
    def test_docs_endpoint_head_method(self):
        """
        Test HEAD method on /docs endpoint.
        
        EXPECTED FAILURE: Docs endpoint likely doesn't support HEAD.
        """
        # Verify GET works (docs endpoint)
        get_response = self.client.get("/docs")
        if get_response.status_code != 200:
            pytest.skip(f"GET /docs not available: {get_response.status_code}")
        
        # Test HEAD method
        head_response = self.client.head("/docs")
        
        # Should support HEAD for availability checking
        assert head_response.status_code == 200, \
            f"HEAD /docs should return 200, got {head_response.status_code}"
        
        assert len(head_response.content) == 0, "HEAD response should have empty body"

class TestRootEndpointHeadSupport:
    """Test HEAD method support for root and service info endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_root_endpoint_head_method(self):
        """
        Test HEAD method on root endpoint (/).
        
        EXPECTED FAILURE: Root endpoint may not support HEAD method.
        """
        # Verify GET works
        get_response = self.client.get("/")
        assert get_response.status_code == 200, "GET / should work"
        
        # Test HEAD method
        head_response = self.client.head("/")
        
        # Should support HEAD for service availability checks
        assert head_response.status_code == 200, \
            f"HEAD / should return 200, got {head_response.status_code}"
        
        assert len(head_response.content) == 0, "HEAD response should have empty body"
        
        # Should have JSON content type
        content_type = head_response.headers.get("content-type", "")
        assert "json" in content_type.lower(), \
            f"HEAD / should indicate JSON content: {content_type}"

class TestHttpMethodCompatibilityComprehensive:
    """Comprehensive HTTP method compatibility tests."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @pytest.mark.parametrize("endpoint", [
        "/",
        "/health",
        "/readiness", 
        "/health/ready",
        "/auth/health",
        "/openapi.json"
    ])
    def test_head_method_comprehensive(self, endpoint):
        """
        Comprehensive HEAD method test across critical endpoints.
        
        EXPECTED FAILURE: Most endpoints will return 405 for HEAD requests.
        """
        # Get the GET response for reference
        get_response = self.client.get(endpoint)
        
        if get_response.status_code not in [200, 503]:
            pytest.skip(f"GET {endpoint} returned {get_response.status_code}, not testing HEAD")
        
        # Test HEAD method
        head_response = self.client.head(endpoint)
        
        # Critical assertion - HEAD should not return 405
        assert head_response.status_code != 405, \
            f"HEAD {endpoint} returned 405 Method Not Allowed - monitoring systems need HEAD support"
        
        # HEAD should return same status as GET for monitoring compatibility
        assert head_response.status_code == get_response.status_code, \
            f"HEAD {endpoint} status {head_response.status_code} != GET status {get_response.status_code}"
        
        # HEAD must have empty body per HTTP spec
        assert len(head_response.content) == 0, \
            f"HEAD {endpoint} must have empty body, got {len(head_response.content)} bytes"
        
        # Content-Type should be present and match GET if GET has it
        if get_response.headers.get("content-type"):
            assert head_response.headers.get("content-type"), \
                f"HEAD {endpoint} missing Content-Type header"
    
    def test_options_method_cors_preflight(self):
        """
        Test OPTIONS method support for CORS preflight requests.
        
        May fail if CORS preflight is not properly configured.
        """
        cors_endpoints = [
            "/auth/login",
            "/auth/callback/google", 
            "/auth/verify",
            "/auth/config"
        ]
        
        for endpoint in cors_endpoints:
            response = self.client.options(endpoint)
            
            # OPTIONS should not return 405 for CORS endpoints
            assert response.status_code != 405, \
                f"OPTIONS {endpoint} returned 405 - CORS preflight requires OPTIONS support"
            
            # Should return 200 or 204 for successful preflight
            assert response.status_code in [200, 204], \
                f"OPTIONS {endpoint} should return 200 or 204, got {response.status_code}"
    
    def test_method_not_allowed_includes_allow_header(self):
        """
        Test that 405 responses include Allow header with supported methods.
        
        May fail if Allow header is not set properly.
        """
        # Try an unsupported method on a known endpoint
        response = self.client.request("PATCH", "/health")
        
        if response.status_code == 405:
            # 405 responses should include Allow header per HTTP spec
            allow_header = response.headers.get("allow") or response.headers.get("Allow")
            assert allow_header, "405 responses should include Allow header with supported methods"
            
            # Should include GET and HEAD methods for health endpoint
            allow_methods = [method.strip().upper() for method in allow_header.split(",")]
            assert "GET" in allow_methods, f"Health endpoint should allow GET method: {allow_methods}"
            assert "HEAD" in allow_methods, f"Health endpoint should allow HEAD method: {allow_methods}"

class TestMonitoringSystemCompatibility:
    """Test compatibility with common monitoring system patterns."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_check_with_monitoring_user_agent(self):
        """
        Test health check with common monitoring system user agents.
        
        Should handle monitoring system requests properly.
        """
        monitoring_user_agents = [
            "Kubernetes/1.21 (linux/amd64) kubernetes/1c4c40c",
            "GoogleHC/1.0",
            "AWS-Application-Load-Balancer-Health-Check", 
            "Consul Health Check",
            "nagios-plugins/2.3.3",
            "Datadog Agent/7.40.1"
        ]
        
        for user_agent in monitoring_user_agents:
            # Test both GET and HEAD with monitoring user agents
            get_response = self.client.get("/health", headers={"User-Agent": user_agent})
            assert get_response.status_code == 200, f"Health check failed for {user_agent}"
            
            head_response = self.client.head("/health", headers={"User-Agent": user_agent})
            # This will fail until HEAD support is implemented
            assert head_response.status_code == 200, \
                f"HEAD health check failed for monitoring system {user_agent}: {head_response.status_code}"
    
    def test_rapid_health_checks(self):
        """
        Test rapid sequential health checks as monitoring systems do.
        
        Should handle burst requests efficiently.
        """
        import time
        
        start_time = time.time()
        
        # Simulate monitoring system making rapid requests
        for i in range(20):
            response = self.client.head("/health")  # Will fail until HEAD is supported
            assert response.status_code in [200, 405], \
                f"Health check #{i} failed with status {response.status_code}"
        
        elapsed = time.time() - start_time
        
        # Should handle rapid requests efficiently (under 2 seconds for 20 requests)
        assert elapsed < 2.0, f"Rapid health checks took too long: {elapsed:.2f}s"
    
    def test_health_check_timeout_handling(self):
        """
        Test health check with short timeout as monitoring systems use.
        
        Should respond quickly enough for typical monitoring timeouts.
        """
        import time
        
        # Test with very short timeout similar to monitoring systems
        start_time = time.time()
        response = self.client.get("/health")
        elapsed = time.time() - start_time
        
        # Should respond within monitoring system timeout (typically 5-10 seconds, we test for 1)
        assert elapsed < 1.0, f"Health check took too long for monitoring systems: {elapsed:.2f}s"
        assert response.status_code == 200, "Health check should succeed quickly"