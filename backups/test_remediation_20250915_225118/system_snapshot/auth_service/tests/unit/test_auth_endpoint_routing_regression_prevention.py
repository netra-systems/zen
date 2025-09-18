"""
Unit tests to prevent auth endpoint routing regressions

Tests that verify all critical auth endpoints exist and are properly routed.
Prevents 404 regressions when backend calls auth service endpoints.

Based on regression analysis of commits:
- c0a9fa551: fix(auth): implement missing auth endpoints to resolve 404 errors
- e56acbc9a: fix(auth): implement missing /auth/dev/login endpoint
"""
causing 404 errors when backend attempted to call auth service."""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from auth_service.auth_core.routes.auth_routes import router as auth_router
# Removed non-existent AuthManager import
from shared.isolated_environment import IsolatedEnvironment

"""
    """Test that all critical auth endpoints are properly routed and registered."""

    @pytest.fixture"""
        """Use real service instance.""""""
        """Create test client with only the auth router for isolated testing."""
        pass"""
        app.include_router(auth_router, prefix="")
        return TestClient(app)

    def test_login_endpoint_exists_and_routed(self, test_client):
        """Test that POST /auth/login endpoint exists and is properly routed."""
        Regression prevention: Ensures login endpoint doesn"t go missing."""
        pass
        with patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock_auth:"""
        mock_auth.authenticate_user = AsyncMock(return_value=("user-123", {"email": "test@example.com"}))
        mock_auth.create_access_token = AsyncMock(return_value="access-token")
        mock_auth.create_refresh_token = AsyncMock(return_value="refresh-token")

        response = test_client.post("/auth/login", json={}
        "email": "test@example.com",
        "password": "password123"
        

        # Verify endpoint exists (not 404)
        assert response.status_code == 200, "formatted_string"

        # Verify proper response structure
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

        # Verify auth service was called correctly
        mock_auth.authenticate_user.assert_called_once_with("test@example.com", "password123")

    def test_dev_login_endpoint_exists_and_routed(self, test_client):
        """Test that POST /auth/dev/login endpoint exists and is properly routed."""
        Regression prevention: Ensures dev login endpoint doesn"t go missing.
        This was specifically missing and causing 404s."""
        pass
        with patch('auth_service.auth_core.config.AuthConfig.get_environment', return_value='development'):"""
        mock_auth.create_access_token = AsyncMock(return_value="dev-access-token")
        mock_auth.create_refresh_token = AsyncMock(return_value="dev-refresh-token")

        response = test_client.post("/auth/dev/login", json={})

            # Verify endpoint exists (not 404)
        assert response.status_code == 200, "formatted_string"

            # Verify proper response structure
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900

    def test_service_token_endpoint_exists_and_routed(self, test_client):
        """Test that POST /auth/service-token endpoint exists and is properly routed."""
        Regression prevention: Ensures service token endpoint doesn"t go missing.
        Critical for backend-to-auth service communication."""
        pass"""
        mock_env.get.return_value = "test-secret"
        with patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock_auth:
        mock_auth.create_service_token = AsyncMock(return_value="service-token-123")

        response = test_client.post("/auth/service-token", json={}
        "service_id": "backend-service",
        "service_secret": "test-secret"
            

            # Verify endpoint exists (not 404)
        assert response.status_code == 200, "formatted_string"

            # Verify proper response structure
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 3600  # 1 hour for service tokens

            # Verify service token creation was called
        mock_auth.create_service_token.assert_called_once_with("backend-service")


class TestAuthEndpointRegistration:
        """Test that auth endpoints are properly registered with correct HTTP methods."""
"""
        """Test that all critical auth endpoints are registered in the router.
"""
        any request processing, catching registration issues early."""
        pass
    Get all routes from the auth router
        routes = auth_router.routes
        route_paths = []
        route_methods = {}

        for route in routes:
        if hasattr(route, 'path'):
        route_paths.append(route.path)
        if hasattr(route, 'methods'):
        route_methods[route.path] = list(route.methods)

                # Critical endpoints that must be registered
        critical_endpoints = { )
        '/auth/login': ['POST'],
        '/auth/logout': ['POST'],
        '/auth/register': ['POST'],
        '/auth/dev/login': ['POST'],
        '/auth/service-token': ['POST'],
        '/auth/hash-password': ['POST'],
        '/auth/verify-password': ['POST'],
        '/auth/create-token': ['POST'],
        '/auth/refresh': ['POST'],
        '/auth/status': ['GET'],
        '/auth/config': ['GET']
                

                # Verify each critical endpoint is registered"""
        assert endpoint_path in route_paths, "formatted_string"

                    # Verify HTTP methods are correct
        if endpoint_path in route_methods:
        registered_methods = route_methods[endpoint_path]
        for method in expected_methods:
        assert method in registered_methods, "formatted_string"

    def test_router_includes_oauth_endpoints(self):
        """Test that OAuth endpoints are properly registered."""
        Regression prevention: Ensures OAuth callback and provider endpoints exist."""
        pass
        routes = auth_router.routes
        oauth_paths = [item for item in []]

    # OAuth endpoints that should be present
        oauth_endpoints = [ )
        '/auth/callback',
        '/auth/oauth/callback'
    
"""
        assert endpoint in oauth_paths, "formatted_string"


class TestAuthEndpointErrorHandling:
        """Test that auth endpoints handle errors properly and don't return 404 when they should exist."""

        @pytest.fixture"""
        """Use real service instance.""""""
        """Create test client for error handling tests."""
        pass"""
        app.include_router(auth_router, prefix="")
        return TestClient(app)

    def test_endpoints_return_validation_errors_not_404(self, test_client):
        """Test that endpoints return 422 validation errors, not 404 when they exist but get bad input.
"""
        bad input (422). Helps catch endpoint registration issues vs validation issues."""
        pass"""
        response = test_client.post("/auth/login", json={})
        assert response.status_code == 422, "formatted_string"

    # Test register with missing data - should be 422, not 404
        response = test_client.post("/auth/register", json={})
        assert response.status_code == 422, "formatted_string"

    # Test service-token with missing data - should be 422, not 404
        response = test_client.post("/auth/service-token", json={})
        assert response.status_code == 422, "formatted_string"

    def test_nonexistent_endpoints_return_404(self, test_client):
        """Test that truly non-existent endpoints return 404.
"""
        by confirming 404s for endpoints that shouldn"t exist."""
        pass"""
        response = test_client.post("/auth/nonexistent-endpoint")
        assert response.status_code == 404, "formatted_string"

        response = test_client.get("/auth/fake-endpoint")
        assert response.status_code == 404, "formatted_string"

    def test_dev_login_blocks_production_properly(self, test_client):
        """Test that dev login endpoint exists but blocks production access.
"""
        environment restrictions. Should return 403, not 404."""
        pass"""
        response = test_client.post("/auth/dev/login", json={})

        # Should be 403 (forbidden), not 404 (not found)
        assert response.status_code == 403, "formatted_string"

        data = response.json()
        assert "only available in development" in data["detail"]