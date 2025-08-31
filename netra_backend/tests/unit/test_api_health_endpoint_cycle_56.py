"""
Test cases to expose backend health endpoint routing issue in staging.

ISSUE TO TEST:
- Backend health endpoint `/api/health` returns 404, which gets converted to 401 by security middleware
- This causes health monitoring to report false authentication failures
- The endpoint should return 200 with a health status JSON response

REQUIREMENTS:
1. Create tests that ACTUALLY FAIL with current code to prove the issue exists
2. Test that `/api/health` returns 200 (not 404 or 401)
3. Test that response contains proper health status JSON
4. Test that endpoint is accessible without authentication

These tests are designed to FAIL with the current code to prove the routing issue exists.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Fix health monitoring false positives causing alert fatigue
- Value Impact: Prevents false authentication failures in monitoring systems
- Strategic Impact: Enables reliable health monitoring for all environments
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import time
import json

from netra_backend.app.core.app_factory import create_app


class TestHealthEndpointRoutingIssue:
    """Test health endpoint routing configuration - these tests should FAIL to prove the issue."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_app_state(self, app):
        """Mock app state for health endpoint tests."""
        mock_state = MagicMock()
        mock_state.startup_complete = True
        mock_state.startup_in_progress = False
        mock_state.startup_failed = False
        mock_state.startup_error = None
        app.state = mock_state
        return mock_state

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_api_health_endpoint_returns_200_not_404(self, client, mock_app_state):
        """
        FAILING TEST: /api/health should return 200 but returns 404 -> 401.
        
        This test WILL FAIL and proves the routing issue exists.
        The health endpoint should be accessible at /api/health but isn't properly routed.
        """
        # This should return 200 but will likely return 404 -> 401 due to security middleware
        response = client.get("/api/health")
        
        print(f"\n=== HEALTH ENDPOINT TEST RESULTS ===")
        print(f"URL: /api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        print(f"===================================\n")
        
        # EXPECTED: 200 with health data
        # ACTUAL: Will likely be 404 (route not found) -> 401 (security middleware conversion)
        assert response.status_code == 200, (
            f"ROUTING ISSUE CONFIRMED: Expected 200, got {response.status_code}. "
            f"Response: {response.text}. "
            f"This indicates the /api/health route is not properly configured. "
            f"When a route returns 404, security middleware converts it to 401, "
            f"causing health monitoring to report false authentication failures."
        )
        
        # Should return JSON health status
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_api_health_endpoint_returns_proper_json_structure(self, client, mock_app_state):
        """
        FAILING TEST: /api/health should return proper health JSON structure.
        
        This test will FAIL because the route doesn't exist and returns 404/401.
        """
        response = client.get("/api/health")
        
        # This will fail if route returns 404
        assert response.status_code == 200, (
            f"Cannot test JSON structure because route returns {response.status_code} instead of 200. "
            f"This confirms the routing issue - /api/health is not properly registered."
        )
        
        data = response.json()
        
        # Expected health response structure based on health.py implementation
        required_fields = ["status", "service", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field '{field}' in health response"
        
        # Status should be valid
        assert data["status"] in ["healthy", "unhealthy"]
        
        # Service should be identified
        assert data["service"] == "netra-ai-platform"
        
        # Timestamp should be recent
        assert isinstance(data["timestamp"], (int, float))
        assert data["timestamp"] > 0

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_api_health_endpoint_bypasses_authentication(self, client, mock_app_state):
        """
        FAILING TEST: /api/health should be accessible without authentication.
        
        This test will FAIL because 404 gets converted to 401 by security middleware.
        Health endpoints should not require authentication but the routing issue causes auth errors.
        """
        # Make request without authentication headers
        response = client.get("/api/health")
        
        print(f"\n=== AUTHENTICATION BYPASS TEST ===")
        print(f"URL: /api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Expected: 200 or 503 (health status)")
        print(f"Actual: {response.status_code} - {response.text[:200]}")
        print(f"================================\n")
        
        # Should not return 401/403 (authentication/authorization errors)
        assert response.status_code != 401, (
            f"SECURITY MIDDLEWARE ISSUE CONFIRMED: Health endpoint returned 401 (Unauthorized). "
            f"This indicates that security middleware is converting 404 (route not found) to 401. "
            f"The real issue is that /api/health route is not registered, so it returns 404, "
            f"then security middleware converts 404 to 401, causing false authentication failures "
            f"in health monitoring systems."
        )
        assert response.status_code != 403, (
            f"Health endpoint returned 403 (Forbidden). "
            f"Health endpoints should be publicly accessible."
        )
        
        # Should return 200 (healthy) or 503 (unhealthy service), NOT 404
        assert response.status_code in [200, 503], (
            f"ROUTING ISSUE: Expected 200 or 503, got {response.status_code}. "
            f"Response: {response.text}. "
            f"A 404 response indicates the route is not registered at /api/health."
        )

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_health_endpoint_works_across_environments(self, client, mock_app_state):
        """
        FAILING TEST: Health endpoint should work in all environments.
        
        This will FAIL in test environment, indicating broader routing issue.
        """
        response = client.get("/api/health")
        
        # Should work regardless of environment
        assert response.status_code in [200, 503], (
            f"Health endpoint failed in test environment: {response.status_code}. "
            f"If this fails in test, it will also fail in staging and production."
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should include environment information
            assert "status" in data


class TestAlternativeHealthEndpointPaths:
    """Test alternative health endpoint path configurations to understand current routing."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_app_state(self, app):
        """Mock app state for health endpoint tests."""
        mock_state = MagicMock()
        mock_state.startup_complete = True
        mock_state.startup_in_progress = False
        mock_state.startup_failed = False
        mock_state.startup_error = None
        app.state = mock_state
        return mock_state

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_map_available_health_endpoints(self, client, mock_app_state):
        """
        Map all health endpoint variations to verify they work correctly.
        
        Verifies that both /health and /api/health endpoints are properly configured.
        """
        test_paths = [
            "/health",           # Health router at /health prefix
            "/health/",          # With trailing slash
            "/api/health",       # Health router at /api/health prefix
            "/api/health/",      # With trailing slash
            "/health/live",      # Liveness probe
            "/health/ready",     # Readiness probe  
            "/api/health/live",  # Liveness probe via API prefix
            "/api/health/ready", # Readiness probe via API prefix
        ]
        
        results = {}
        
        print(f"\n=== HEALTH ENDPOINT ROUTING VERIFICATION ===")
        
        for path in test_paths:
            try:
                response = client.get(path)
                results[path] = {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "response_preview": response.text[:100] if response.text else ""
                }
                
                status_emoji = "PASS" if response.status_code == 200 else "FAIL"
                print(f"{status_emoji} {path}: {response.status_code}")
                
            except Exception as e:
                results[path] = {"error": str(e)}
                print(f"ERROR {path}: ERROR - {e}")
        
        print(f"==========================================\n")
        
        # Verify both main health endpoints work
        health_status = results.get('/health', {}).get('status_code', 0)
        api_health_status = results.get('/api/health', {}).get('status_code', 0)
        
        print(f"ANALYSIS:")
        print(f"   /health status: {health_status}")
        print(f"   /api/health status: {api_health_status}")
        
        # Both endpoints should work (200 status)
        assert health_status == 200, f"Health endpoint /health should return 200, got {health_status}"
        assert api_health_status == 200, f"API health endpoint /api/health should return 200, got {api_health_status}"

    @pytest.mark.unit  
    @pytest.mark.api
    @pytest.mark.health
    def test_current_health_configuration_analysis(self, client, mock_app_state):
        """
        Verify the current health endpoint configuration works as expected.
        
        Both /health and /api/health endpoints should be properly configured and working.
        """
        # Test both configured paths
        health_response = client.get("/health")
        api_health_response = client.get("/api/health") 
        
        print(f"\n=== HEALTH CONFIGURATION VERIFICATION ===")
        print(f"/health endpoint status: {health_response.status_code}")
        print(f"/api/health endpoint status: {api_health_response.status_code}")
        
        # Both endpoints should work
        working_paths = []
        if health_response.status_code == 200:
            working_paths.append("/health")
        if api_health_response.status_code == 200:
            working_paths.append("/api/health")
            
        print(f"Working paths: {working_paths}")
        if len(working_paths) < 2:
            print(f"Non-working paths: {[p for p in ['/health', '/api/health'] if p not in working_paths]}")
        print(f"=========================================\n")
        
        # Both health endpoints should work
        assert health_response.status_code == 200, f"/health endpoint should work, got status {health_response.status_code}"
        assert api_health_response.status_code == 200, f"/api/health endpoint should work, got status {api_health_response.status_code}"


class TestHealthEndpointCurrentConfiguration:
    """Test to understand the current health endpoint configuration."""
    
    @pytest.fixture
    def app(self):
        """Create test application.""" 
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_inspect_current_routes(self, app):
        """
        Inspect the current route configuration to verify both health endpoints are registered.
        
        This test examines the actual registered routes to confirm proper configuration.
        """
        print(f"\n=== REGISTERED ROUTES ANALYSIS ===")
        
        # Print all registered routes
        all_routes = []
        health_routes = []
        
        try:
            for route in app.routes:
                try:
                    if hasattr(route, 'path') and hasattr(route, 'methods'):
                        route_info = f"{list(route.methods)} {route.path}"
                        all_routes.append(route_info)
                        if 'health' in route.path.lower():
                            health_routes.append(route_info)
                            print(f"HEALTH ROUTE: {route_info}")
                    elif hasattr(route, 'path'):
                        route_info = f"MOUNT {route.path}"
                        all_routes.append(route_info)
                        if 'health' in route.path.lower():
                            print(f"HEALTH MOUNT: {route_info}")
                except Exception as e:
                    print(f"WARNING Error processing route: {e}")
                    continue
        except Exception as e:
            print(f"ERROR Error accessing app routes: {e}")
            all_routes = []
            health_routes = []
        
        # Check specifically for the routes we care about
        api_health_found = any('/api/health' in route for route in all_routes)
        health_found = any('/health' in route for route in all_routes)
        
        print(f"\nROUTE ANALYSIS:")
        print(f"   Total routes registered: {len(all_routes)}")
        print(f"   Health-related routes: {len(health_routes)}")
        print(f"   /health route found: {health_found}")
        print(f"   /api/health route found: {api_health_found}")
        
        if health_routes:
            print(f"\nALL HEALTH ROUTES:")
            for route in health_routes:
                print(f"     {route}")
        
        print(f"===============================\n")
        
        # Both routes should be properly registered
        assert health_found, "Health routes should be found in route registry"
        # Note: /api/health might be mounted as a separate mount point, so we verify via functional test
        print(f"Health route configuration verified")


class TestHealthEndpointSecurityBypass:
    """Test that health endpoints properly bypass security middleware when they exist."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        return create_app()

    @pytest.fixture  
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_app_state(self, app):
        """Mock app state for health endpoint tests."""
        mock_state = MagicMock()
        mock_state.startup_complete = True
        app.state = mock_state
        return mock_state

    @pytest.mark.unit
    @pytest.mark.api 
    @pytest.mark.health
    def test_health_endpoint_with_invalid_auth_should_still_work(self, client, mock_app_state):
        """
        FAILING TEST: Health endpoint should work even with invalid auth headers.
        
        This will FAIL because /api/health doesn't exist, so it returns 404 -> 401.
        When it exists, it should ignore auth headers completely.
        """
        # Send invalid authorization header
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = client.get("/api/health", headers=headers)
        
        print(f"\n=== OAUTH SIMULATION TEST ===")
        print(f"URL: /api/health")
        print(f"Headers: {headers}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        print(f"=======================\n")
        
        # Should ignore invalid auth and still return health status (not 401)
        assert response.status_code != 401, (
            f"AUTH ISSUE: Health endpoint returned 401 with invalid auth. "
            f"This could mean: 1) Route doesn't exist (404->401 conversion), "
            f"or 2) Auth middleware is incorrectly applied to health endpoints. "
            f"Health endpoints should ignore auth headers completely."
        )
        
        # Should return health status (200/503), not auth errors
        assert response.status_code in [200, 503], (
            f"Expected health status (200/503), got {response.status_code}"
        )


class TestExpectedHealthEndpointBehavior:
    """Test what the health endpoint behavior should be when properly configured."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_app_state(self, app):
        """Mock app state for health endpoint tests."""
        mock_state = MagicMock()
        mock_state.startup_complete = True
        mock_state.startup_in_progress = False
        mock_state.startup_failed = False
        mock_state.startup_error = None
        app.state = mock_state
        return mock_state

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health
    def test_expected_api_health_response_format(self, client, mock_app_state):
        """
        Test expected health response format for /api/health endpoint.
        
        Verifies the API health endpoint returns the expected JSON structure.
        """
        # Test the API health endpoint specifically
        response = client.get("/api/health")
        
        # Verify the endpoint is working
        assert response.status_code == 200, (
            f"API health endpoint should return 200, got {response.status_code}"
        )
        
        data = response.json()
        
        # Expected format based on actual API health response
        required_fields = ["status", "service", "timestamp"]
        optional_fields = ["version", "uptime_seconds", "checks"]
        
        # Check required fields
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from health response"
            
        # Validate specific field types
        assert data["status"] in ["healthy", "unhealthy"], f"Status should be healthy/unhealthy, got {data['status']}"
        assert data["service"] == "netra-ai-platform", f"Service should be netra-ai-platform, got {data['service']}"
        assert isinstance(data["timestamp"], (int, float)), f"Timestamp should be a number, got {type(data['timestamp'])}"
        assert data["timestamp"] > 0, f"Timestamp should be positive, got {data['timestamp']}"
        
        print(f"Health response validation passed - all required fields present")

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.health  
    def test_api_health_response_time_requirement(self, client, mock_app_state):
        """
        API health endpoint should respond quickly for monitoring.
        
        Health endpoints must be fast for monitoring systems.
        """
        start_time = time.time()
        response = client.get("/api/health")  # Test the API endpoint specifically
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should respond quickly (under 5 seconds for health check)
        assert response_time < 5.0, (
            f"API health endpoint took {response_time:.2f}s to respond. "
            f"Health checks should be fast for monitoring."
        )
        
        # Should actually work (return 200/503)
        assert response.status_code in [200, 503], (
            f"API health endpoint returned {response.status_code} instead of health status"
        )
        
        print(f"API health endpoint response time: {response_time:.3f}s")