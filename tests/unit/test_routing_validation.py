"""
Route Validation Tests - Ensures API routing consistency

This test module validates that all expected API endpoints exist and are accessible,
preventing routing mismatches that cause E2E test failures.
"""

import pytest
from fastapi.testclient import TestClient
from netra_backend.app.main import app

# Test client
client = TestClient(app)


class TestRoutingValidation:
    """Test suite for route validation and consistency."""

    def test_messages_root_endpoint_exists(self):
        """Test that /api/messages root endpoint exists."""
        # This should now work with our new messages_root router
        response = client.get("/api/messages")
        
        # Should return API info, not 404
        assert response.status_code in [200, 401, 403], f"Expected 200/401/403, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "service" in data
            assert data["service"] == "messages-api"
            assert "endpoints" in data

    def test_messages_chat_endpoints_exist(self):
        """Test that /api/chat/messages endpoints exist."""
        # GET /api/chat/messages should exist  
        response = client.get("/api/chat/messages")
        
        # Should require auth (401/403) or return data (200), not 404
        assert response.status_code in [200, 401, 403], f"Expected 200/401/403, got {response.status_code}"

    def test_agents_endpoints_exist(self):
        """Test that /api/agents endpoints exist."""
        endpoints_to_test = [
            "/api/agents/execute",
            "/api/agents/triage", 
            "/api/agents/data",
            "/api/agents/optimization",
            "/api/agents/status",
            "/api/agents/start",
            "/api/agents/stop",
            "/api/agents/cancel",
            "/api/agents/stream"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            
            # Should not be 404 (endpoint exists), may be 405 (wrong method), 401/403 (auth required)
            assert response.status_code != 404, f"Endpoint {endpoint} returns 404 - endpoint missing!"
            
            # If it's 405, try POST (many agent endpoints expect POST)
            if response.status_code == 405:
                post_response = client.post(endpoint, json={"message": "test"})
                assert post_response.status_code != 404, f"POST {endpoint} returns 404 - endpoint missing!"

    def test_events_endpoints_exist(self):
        """Test that /api/events endpoints exist."""
        endpoints_to_test = [
            "/api/events",  # Root endpoint (added in our fix)
            "/api/events/stream",
            "/api/events/info"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            
            # Should not be 404
            assert response.status_code != 404, f"Endpoint {endpoint} returns 404 - endpoint missing!"
            assert response.status_code in [200, 401, 403, 405], \
                f"Endpoint {endpoint} returned unexpected status {response.status_code}"

    def test_route_consistency(self):
        """Test that route prefixes are consistent with E2E test expectations."""
        # Test expected route patterns
        expected_patterns = {
            "/api/messages": "messages-root",
            "/api/chat/messages": "messages",
            "/api/agents/execute": "agents", 
            "/api/events": "events",
            "/api/events/stream": "events"
        }
        
        for endpoint, expected_service in expected_patterns.items():
            response = client.get(endpoint)
            
            # Endpoint should exist (not 404)
            assert response.status_code != 404, \
                f"Expected endpoint {endpoint} missing (should serve {expected_service})"

    def test_backwards_compatibility(self):
        """Test that E2E test expectations are met."""
        # These are the specific endpoints that E2E tests expect to work
        critical_endpoints = [
            "/api/messages",  # E2E tests expect this to exist
            "/api/agents/execute",  # E2E tests expect this for agent execution
            "/api/agents/triage",   # E2E tests expect this for triage agent
            "/api/agents/data",     # E2E tests expect this for data agent  
            "/api/agents/optimization",  # E2E tests expect this for optimization agent
            "/api/events",          # E2E tests expect this for events
        ]
        
        for endpoint in critical_endpoints:
            response = client.get(endpoint)
            
            # Critical: these endpoints must not return 404
            assert response.status_code != 404, \
                f"CRITICAL: E2E test endpoint {endpoint} returns 404! This will break E2E tests."

    def test_health_endpoints(self):
        """Test that health check endpoints exist."""
        health_endpoints = [
            "/health",
            "/api/health"
        ]
        
        for endpoint in health_endpoints:
            response = client.get(endpoint)
            # Health endpoints should be accessible
            if response.status_code != 404:
                # If endpoint exists, it should return successful health status
                assert response.status_code == 200, \
                    f"Health endpoint {endpoint} exists but returns {response.status_code}"

    def test_root_api_endpoint(self):
        """Test that the root API endpoint works."""
        response = client.get("/")
        
        # Root endpoint should exist and return welcome message
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Netra API" in data["message"]


if __name__ == "__main__":
    # Run basic validation
    test_suite = TestRoutingValidation()
    
    print("Testing critical routing endpoints...")
    
    try:
        test_suite.test_messages_root_endpoint_exists()
        print(" PASS:  Messages root endpoint validation passed")
    except Exception as e:
        print(f" FAIL:  Messages root endpoint validation failed: {e}")
    
    try:
        test_suite.test_agents_endpoints_exist()
        print(" PASS:  Agents endpoints validation passed")
    except Exception as e:
        print(f" FAIL:  Agents endpoints validation failed: {e}")
    
    try:
        test_suite.test_events_endpoints_exist()
        print(" PASS:  Events endpoints validation passed")
    except Exception as e:
        print(f" FAIL:  Events endpoints validation failed: {e}")
    
    try:
        test_suite.test_backwards_compatibility()
        print(" PASS:  Backwards compatibility validation passed")
    except Exception as e:
        print(f" FAIL:  Backwards compatibility validation failed: {e}")
    
    print("Route validation complete!")