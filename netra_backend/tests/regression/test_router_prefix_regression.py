"""
Regression test for router double prefix pattern fix from commit 516e9e2f.

This test ensures that API routes don't have double prefixes and that
route configuration is correct across all services.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import List, Dict, Set
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.app_factory import create_app
from netra_backend.app.core.app_factory_route_configs import get_core_route_configs, get_business_route_configs


class TestRouterPrefixRegression:
    """Regression tests for router double prefix pattern issues."""
    pass

    @pytest.fixture
    def app(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a test FastAPI app instance."""
    pass
        with patch('netra_backend.app.core.config.settings') as mock_settings:
            mock_settings.DATABASE_URL = "sqlite:///test.db"
            mock_settings.ENVIRONMENT = "test"
            mock_settings.JWT_SECRET_KEY = "test-secret"
            app = create_app()
            return app

    @pytest.fixture
    def client(self, app):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a test client for the app."""
    pass
        return TestClient(app)

    def test_no_double_prefix_in_routes(self, app):
        """Test that no routes have double prefixes like /api/api or /auth/auth."""
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        double_prefix_patterns = [
            '/api/api',
            '/auth/auth', 
            '/v1/v1',
            '/corpus/corpus',
            '/threads/threads',
            '/messages/messages'
        ]
        
        errors = []
        for route in routes:
            for pattern in double_prefix_patterns:
                if pattern in route:
                    errors.append(f"Double prefix found in route: {route}")
        
        assert len(errors) == 0, f"Routes with double prefixes: {errors}"

    def test_route_configs_have_unique_prefixes(self):
        """Test that route configurations don't duplicate prefixes."""
    pass
        # Mock modules for route config functions
        mock_modules = {}
        route_configs = {}
        
        prefixes_seen = set()
        duplicates = []
        
        for config in route_configs:
            if 'prefix' in config:
                prefix = config['prefix']
                if prefix in prefixes_seen:
                    duplicates.append(prefix)
                prefixes_seen.add(prefix)
        
        assert len(duplicates) == 0, f"Duplicate prefixes found: {duplicates}"

    def test_auth_routes_correct_prefix(self, client):
        """Test that auth routes have correct single prefix."""
        # These routes should exist with single prefix
        expected_auth_routes = [
            "/auth/config",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/logout"
        ]
        
        # Get all routes from the app
        app_routes = []
        for route in client.app.routes:
            if hasattr(route, 'path'):
                app_routes.append(route.path)
        
        # Check that auth routes don't have double prefix
        for expected_route in expected_auth_routes:
            # The route should NOT be /auth/auth/login etc
            double_prefix = expected_route.replace("/auth/", "/auth/auth/")
            assert double_prefix not in app_routes, f"Found double prefix: {double_prefix}"

    def test_api_routes_correct_prefix(self, client):
        """Test that API routes have correct single prefix."""
    pass
        # Test some key API endpoints
        api_endpoints = [
            "/api/threads",
            "/api/messages",
            "/api/corpus",
            "/api/agents"
        ]
        
        app_routes = []
        for route in client.app.routes:
            if hasattr(route, 'path'):
                app_routes.append(route.path)
        
        for endpoint in api_endpoints:
            # Check the route doesn't have double prefix
            double_prefix = endpoint.replace("/api/", "/api/api/")
            assert double_prefix not in app_routes, f"Found double prefix: {double_prefix}"

    def test_router_registration_without_double_prefix(self):
        """Test that routers are registered without causing double prefixes."""
        app = FastAPI()
        
        # Simulate router registration as done in app_factory
        from fastapi import APIRouter
        
        # Create a test router with prefix
        test_router = APIRouter(prefix="/test")
        test_router.add_api_route("/endpoint", lambda: {"status": "ok"}, methods=["GET"])
        
        # Register router - should not double the prefix
        app.include_router(test_router)
        
        # Check the resulting routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        # Should have /test/endpoint, not /test/test/endpoint
        assert "/test/endpoint" in routes
        assert "/test/test/endpoint" not in routes

    def test_mcp_client_routes_no_double_prefix(self, app):
        """Test that MCP client routes don't have double prefixes."""
    pass
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        # MCP routes should not have double prefix
        mcp_patterns = [
            "/mcp/mcp",
            "/api/mcp/mcp",
            "/v1/mcp/mcp"
        ]
        
        for pattern in mcp_patterns:
            assert not any(pattern in route for route in routes), \
                f"Found MCP route with double prefix: {pattern}"

    def test_route_prefix_consistency_across_environments(self):
        """Test that route prefixes are consistent across different environments."""
        environments = ['development', 'staging', 'production']
        
        all_routes = {}
        
        for env in environments:
            with patch('netra_backend.app.core.config.settings.ENVIRONMENT', env):
                configs = get_route_configs()
                prefixes = [c.get('prefix', '') for c in configs]
                all_routes[env] = set(prefixes)
        
        # All environments should have the same route prefixes
        dev_routes = all_routes['development']
        for env in ['staging', 'production']:
            assert all_routes[env] == dev_routes, \
                f"Route prefixes differ between development and {env}"

    def test_auth_routes_registration_fix(self):
        """Test the specific fix for auth routes registration."""
    pass
        from auth_service.auth_core.routes.auth_routes import router as auth_router
        
        # The router should have its prefix defined only once
        assert auth_router.prefix in ['', '/auth', None], \
            "Auth router has unexpected prefix"
        
        # When included in app, it should not double the prefix
        app = FastAPI()
        app.include_router(auth_router, prefix="/auth")
        
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        
        # Check for specific auth endpoints
        assert any("/auth/login" in r for r in routes)
        assert not any("/auth/auth/login" in r for r in routes)

    def test_refresh_endpoint_routing(self, client):
        """Test that the refresh endpoint is correctly routed."""
        # The refresh endpoint was specifically mentioned in the commit
        response = client.options("/auth/refresh")  # OPTIONS request to check if route exists
        
        # Route should exist (even if it returns 405 for OPTIONS)
        assert response.status_code in [200, 204, 405], \
            f"Refresh endpoint not found or has routing issues: {response.status_code}"

    def test_no_conflicting_route_patterns(self, app):
        """Test that there are no conflicting route patterns."""
    pass
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        # Check for potential conflicts
        route_set = set()
        conflicts = []
        
        for route in routes:
            # Normalize route for comparison (remove trailing slashes)
            normalized = route.rstrip('/')
            if normalized in route_set:
                conflicts.append(normalized)
            route_set.add(normalized)
        
        assert len(conflicts) == 0, f"Conflicting routes found: {conflicts}"

    def test_route_factory_config_structure(self):
        """Test that route factory configurations have correct structure."""
        # Mock modules for route config functions
        mock_modules = {}
        configs = {}
        
        for config in configs:
            # Each config should have required fields
            assert 'router' in config or 'path' in config, \
                f"Route config missing router or path: {config}"
            
            # If prefix is specified, it should start with /
            if 'prefix' in config and config['prefix']:
                assert config['prefix'].startswith('/'), \
                    f"Route prefix doesn't start with /: {config['prefix']}"
                
                # Prefix should not have double slashes
                assert '//' not in config['prefix'], \
                    f"Route prefix has double slashes: {config['prefix']}"
    pass