"""Health Endpoint HTTP Methods - Critical Failing Tests

Tests that expose health endpoint method failures found in staging logs.
These tests are designed to FAIL to demonstrate current HTTP method handling problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service reliability and monitoring compatibility  
- Value Impact: Ensures health endpoints work with all monitoring systems
- Strategic Impact: $9.4M protection - prevents monitoring failures in production

Critical Issues from Staging Logs:
1. Health endpoints return 405 (Method Not Allowed) for HEAD requests
2. Load balancers and monitoring systems expect HEAD method support
3. OPTIONS method may not be properly handled for CORS preflight
4. Inconsistent HTTP method support across health endpoints

Expected Behavior (CURRENTLY FAILING):
- GET /health should return 200 with health status
- HEAD /health should return 200 with same headers but no body
- OPTIONS /health should return 200 with allowed methods
- All methods should have consistent status codes and headers

Test Strategy:
- Use real HTTP requests (no mocks per CLAUDE.md)
- Test actual FastAPI endpoint method handling
- Verify HTTP specification compliance
- Confirm monitoring system compatibility
"""

import pytest
import asyncio
from typing import Dict, Any
import json
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment

# ABSOLUTE IMPORTS - Following SPEC/import_management_architecture.xml
from fastapi.testclient import TestClient
from fastapi import FastAPI
from netra_backend.app.routes.health_check import router, readiness_probe, liveness_probe, startup_probe
from shared.isolated_environment import get_env


# Create test FastAPI app for endpoint testing
def create_test_app() -> FastAPI:
    """Create test FastAPI application with health routes."""
    app = FastAPI()
    app.include_router(router, prefix="/health", tags=["health"])
    return app


class TestHealthEndpointMethods:
    """Test health endpoint HTTP method support that currently fails."""
    
    def setup_method(self):
        """Setup test client for each test."""
        self.app = create_test_app()
        self.client = TestClient(self.app)
    
    def test_health_ready_get_method_should_work(self):
        """Test GET method on /health/ready endpoint.
        
        BASELINE TEST: This should work to establish baseline behavior.
        If this fails, there are deeper issues with the health endpoint.
        """
        try:
            response = self.client.get("/health/ready")
            
            # Should return success or service unavailable (both are acceptable)
            assert response.status_code in [200, 503], \
                f"GET /health/ready should return 200 or 503, got: {response.status_code}"
            
            # Should have JSON content
            assert response.headers.get("content-type") == "application/json", \
                "Health endpoint should return JSON content-type"
            
            # Should be valid JSON
            try:
                health_data = response.json()
                assert "status" in health_data, "Health response should include status field"
            except Exception as e:
                pytest.fail(f"Health response should be valid JSON: {e}")
                
        except Exception as e:
            pytest.fail(f"Basic GET /health/ready should work: {e}")
    
    def test_health_ready_head_method_should_work_but_currently_fails(self):
        """Test HEAD method on /health/ready endpoint.
        
        CURRENTLY FAILS: Returns 405 Method Not Allowed for HEAD requests.
        Load balancers and monitoring systems expect HEAD method support.
        
        Expected: Should return same status as GET but with no response body.
        """
        try:
            # First get the GET response for comparison
            get_response = self.client.get("/health/ready")
            
            # HEAD should return same status code as GET
            head_response = self.client.head("/health/ready")
            
            # This will currently fail with 405 Method Not Allowed
            assert head_response.status_code == get_response.status_code, \
                f"HEAD should return same status as GET. GET: {get_response.status_code}, HEAD: {head_response.status_code}"
            
            # HEAD should have same headers as GET
            assert head_response.headers.get("content-type") == get_response.headers.get("content-type"), \
                "HEAD should have same content-type header as GET"
            
            # HEAD should have empty body
            assert head_response.content == b"", \
                f"HEAD response should have empty body, got: {head_response.content}"
            
            # Should have content-length header
            if "content-length" in get_response.headers:
                assert "content-length" in head_response.headers, \
                    "HEAD should include content-length header if GET does"
                    
        except Exception as e:
            pytest.fail(f"HEAD /health/ready should work like GET but without body: {e}")
    
    def test_health_ready_options_method_should_work_but_currently_fails(self):
        """Test OPTIONS method on /health/ready endpoint.
        
        CURRENTLY FAILS: May return 405 Method Not Allowed for OPTIONS requests.
        CORS preflight requests and API discovery tools expect OPTIONS support.
        
        Expected: Should return 200 with allowed methods in Allow header.
        """
        try:
            response = self.client.options("/health/ready")
            
            # OPTIONS should return 200 or 204
            assert response.status_code in [200, 204], \
                f"OPTIONS should return 200 or 204, got: {response.status_code}"
            
            # Should include Allow header with supported methods
            allow_header = response.headers.get("allow")
            assert allow_header is not None, "OPTIONS should return Allow header"
            
            # Should include GET and HEAD methods
            allowed_methods = [method.strip().upper() for method in allow_header.split(",")]
            assert "GET" in allowed_methods, f"Allow header should include GET, got: {allow_header}"
            assert "HEAD" in allowed_methods, f"Allow header should include HEAD, got: {allow_header}"
            assert "OPTIONS" in allowed_methods, f"Allow header should include OPTIONS, got: {allow_header}"
            
        except Exception as e:
            pytest.fail(f"OPTIONS /health/ready should return allowed methods: {e}")
    
    def test_health_live_head_method_should_work_but_currently_fails(self):
        """Test HEAD method on /health/live endpoint.
        
        CURRENTLY FAILS: Returns 405 Method Not Allowed for HEAD requests.
        Kubernetes liveness probes may use HEAD method for efficiency.
        
        Expected: Should return same status as GET but with no response body.
        """
        try:
            # Get baseline GET response
            get_response = self.client.get("/health/live")
            
            # HEAD should work the same
            head_response = self.client.head("/health/live")
            
            # Should have same status code
            assert head_response.status_code == get_response.status_code, \
                f"HEAD /health/live should match GET status. GET: {get_response.status_code}, HEAD: {head_response.status_code}"
            
            # Should have same content-type
            assert head_response.headers.get("content-type") == get_response.headers.get("content-type"), \
                "HEAD /health/live should have same content-type as GET"
            
            # Should have empty body
            assert head_response.content == b"", \
                "HEAD /health/live should have empty body"
                
        except Exception as e:
            pytest.fail(f"HEAD /health/live should work: {e}")
    
    def test_health_startup_head_method_should_work_but_currently_fails(self):
        """Test HEAD method on /health/startup endpoint.
        
        CURRENTLY FAILS: Returns 405 Method Not Allowed for HEAD requests.
        Kubernetes startup probes may use HEAD method for efficiency.
        
        Expected: Should return same status as GET but with no response body.
        """
        try:
            # Get baseline GET response
            get_response = self.client.get("/health/startup")
            
            # HEAD should work the same  
            head_response = self.client.head("/health/startup")
            
            # Should have same status code
            assert head_response.status_code == get_response.status_code, \
                f"HEAD /health/startup should match GET status. GET: {get_response.status_code}, HEAD: {head_response.status_code}"
            
            # Should have same content-type
            assert head_response.headers.get("content-type") == get_response.headers.get("content-type"), \
                "HEAD /health/startup should have same content-type as GET"
            
            # Should have empty body
            assert head_response.content == b"", \
                "HEAD /health/startup should have empty body"
                
        except Exception as e:
            pytest.fail(f"HEAD /health/startup should work: {e}")
    
    def test_health_endpoints_cors_options_handling(self):
        """Test CORS OPTIONS handling for health endpoints.
        
        CURRENTLY FAILS: Health endpoints may not properly handle CORS preflight
        requests, causing browser-based monitoring dashboards to fail.
        
        Expected: Should handle CORS OPTIONS with appropriate headers.
        """
        endpoints = ["/health/ready", "/health/live", "/health/startup"]
        
        for endpoint in endpoints:
            try:
                response = self.client.options(
                    endpoint,
                    headers={
                        "Origin": "https://monitoring.example.com",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Content-Type"
                    }
                )
                
                # Should not return 405 Method Not Allowed
                assert response.status_code != 405, \
                    f"CORS OPTIONS {endpoint} should not return 405 Method Not Allowed"
                
                # Should return successful status
                assert response.status_code in [200, 204], \
                    f"CORS OPTIONS {endpoint} should return 200 or 204, got: {response.status_code}"
                
                # Should include Allow header
                allow_header = response.headers.get("allow")
                assert allow_header is not None, \
                    f"CORS OPTIONS {endpoint} should include Allow header"
                
            except Exception as e:
                pytest.fail(f"CORS OPTIONS handling failed for {endpoint}: {e}")
    
    def test_health_endpoints_method_consistency(self):
        """Test that all health endpoints have consistent method support.
        
        CURRENTLY FAILS: Health endpoints may have inconsistent HTTP method support,
        causing confusion for monitoring system configuration.
        
        Expected: All health endpoints should support the same HTTP methods.
        """
        endpoints = ["/health/ready", "/health/live", "/health/startup"]
        methods = ["GET", "HEAD", "OPTIONS"]
        
        # Track which methods work for each endpoint
        endpoint_methods = {}
        
        for endpoint in endpoints:
            endpoint_methods[endpoint] = {}
            
            for method in methods:
                try:
                    if method == "GET":
                        response = self.client.get(endpoint)
                    elif method == "HEAD":
                        response = self.client.head(endpoint)
                    elif method == "OPTIONS":
                        response = self.client.options(endpoint)
                    
                    # Record if method is supported (not 405)
                    endpoint_methods[endpoint][method] = response.status_code != 405
                    
                except Exception as e:
                    endpoint_methods[endpoint][method] = False
        
        # All endpoints should support the same methods
        first_endpoint = endpoints[0]
        reference_methods = endpoint_methods[first_endpoint]
        
        for endpoint in endpoints[1:]:
            for method in methods:
                reference_support = reference_methods[method]
                current_support = endpoint_methods[endpoint][method]
                
                assert reference_support == current_support, \
                    f"Method support inconsistency: {first_endpoint} {method}={reference_support}, {endpoint} {method}={current_support}"
        
        # At minimum, all endpoints should support GET and HEAD
        for endpoint in endpoints:
            assert endpoint_methods[endpoint]["GET"], \
                f"{endpoint} should support GET method"
            # This will currently fail for HEAD and OPTIONS
            assert endpoint_methods[endpoint]["HEAD"], \
                f"{endpoint} should support HEAD method"
            assert endpoint_methods[endpoint]["OPTIONS"], \
                f"{endpoint} should support OPTIONS method"
    
    def test_health_endpoint_http_spec_compliance(self):
        """Test health endpoints comply with HTTP specification.
        
        CURRENTLY FAILS: Health endpoints may not be fully HTTP spec compliant,
        particularly around HEAD method implementation and status code consistency.
        
        Expected: Should follow HTTP/1.1 specification for method handling.
        """
        try:
            # GET request baseline
            get_response = self.client.get("/health/ready")
            
            # HEAD should return identical headers to GET
            head_response = self.client.head("/health/ready")
            
            # Status codes should match
            assert head_response.status_code == get_response.status_code, \
                "HEAD should return same status code as GET (HTTP spec requirement)"
            
            # Critical headers should match
            critical_headers = ["content-type", "content-length", "cache-control"]
            for header in critical_headers:
                if header in get_response.headers:
                    assert get_response.headers[header] == head_response.headers.get(header), \
                        f"HEAD should return same {header} header as GET"
            
            # HEAD should have no body (HTTP spec requirement)
            assert head_response.content == b"", \
                "HEAD method must not return message body (HTTP/1.1 spec)"
            
            # OPTIONS should indicate allowed methods
            options_response = self.client.options("/health/ready")
            assert "allow" in options_response.headers, \
                "OPTIONS should return Allow header (HTTP spec requirement)"
                
        except Exception as e:
            pytest.fail(f"Health endpoints should comply with HTTP specification: {e}")


if __name__ == "__main__":
    # Run specific failing tests to demonstrate issues
    pytest.main([__file__, "-v", "--tb=short"])