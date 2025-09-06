# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Regression test for router double prefix pattern fix from commit 516e9e2f.

# REMOVED_SYNTAX_ERROR: This test ensures that API routes don"t have double prefixes and that
# REMOVED_SYNTAX_ERROR: route configuration is correct across all services.
# REMOVED_SYNTAX_ERROR: '''

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import List, Dict, Set
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.app_factory import create_app
from netra_backend.app.core.app_factory_route_configs import get_core_route_configs, get_business_route_configs


# REMOVED_SYNTAX_ERROR: class TestRouterPrefixRegression:
    # REMOVED_SYNTAX_ERROR: """Regression tests for router double prefix pattern issues."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def app(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a test FastAPI app instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.config.settings') as mock_settings:
        # REMOVED_SYNTAX_ERROR: mock_settings.DATABASE_URL = "sqlite:///test.db"
        # REMOVED_SYNTAX_ERROR: mock_settings.ENVIRONMENT = "test"
        # REMOVED_SYNTAX_ERROR: mock_settings.JWT_SECRET_KEY = "test-secret"
        # REMOVED_SYNTAX_ERROR: app = create_app()
        # REMOVED_SYNTAX_ERROR: return app

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def client(self, app):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a test client for the app."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return TestClient(app)

# REMOVED_SYNTAX_ERROR: def test_no_double_prefix_in_routes(self, app):
    # REMOVED_SYNTAX_ERROR: """Test that no routes have double prefixes like /api/api or /auth/auth."""
    # REMOVED_SYNTAX_ERROR: routes = []
    # REMOVED_SYNTAX_ERROR: for route in app.routes:
        # REMOVED_SYNTAX_ERROR: if hasattr(route, 'path'):
            # REMOVED_SYNTAX_ERROR: routes.append(route.path)

            # REMOVED_SYNTAX_ERROR: double_prefix_patterns = [ )
            # REMOVED_SYNTAX_ERROR: '/api/api',
            # REMOVED_SYNTAX_ERROR: '/auth/auth',
            # REMOVED_SYNTAX_ERROR: '/v1/v1',
            # REMOVED_SYNTAX_ERROR: '/corpus/corpus',
            # REMOVED_SYNTAX_ERROR: '/threads/threads',
            # REMOVED_SYNTAX_ERROR: '/messages/messages'
            

            # REMOVED_SYNTAX_ERROR: errors = []
            # REMOVED_SYNTAX_ERROR: for route in routes:
                # REMOVED_SYNTAX_ERROR: for pattern in double_prefix_patterns:
                    # REMOVED_SYNTAX_ERROR: if pattern in route:
                        # REMOVED_SYNTAX_ERROR: errors.append("formatted_string")

                        # REMOVED_SYNTAX_ERROR: assert len(errors) == 0, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_route_configs_have_unique_prefixes(self):
    # REMOVED_SYNTAX_ERROR: """Test that route configurations don't duplicate prefixes."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock modules for route config functions
    # REMOVED_SYNTAX_ERROR: mock_modules = {}
    # REMOVED_SYNTAX_ERROR: route_configs = {}

    # REMOVED_SYNTAX_ERROR: prefixes_seen = set()
    # REMOVED_SYNTAX_ERROR: duplicates = []

    # REMOVED_SYNTAX_ERROR: for config in route_configs:
        # REMOVED_SYNTAX_ERROR: if 'prefix' in config:
            # REMOVED_SYNTAX_ERROR: prefix = config['prefix']
            # REMOVED_SYNTAX_ERROR: if prefix in prefixes_seen:
                # REMOVED_SYNTAX_ERROR: duplicates.append(prefix)
                # REMOVED_SYNTAX_ERROR: prefixes_seen.add(prefix)

                # REMOVED_SYNTAX_ERROR: assert len(duplicates) == 0, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_auth_routes_correct_prefix(self, client):
    # REMOVED_SYNTAX_ERROR: """Test that auth routes have correct single prefix."""
    # These routes should exist with single prefix
    # REMOVED_SYNTAX_ERROR: expected_auth_routes = [ )
    # REMOVED_SYNTAX_ERROR: "/auth/config",
    # REMOVED_SYNTAX_ERROR: "/auth/login",
    # REMOVED_SYNTAX_ERROR: "/auth/register",
    # REMOVED_SYNTAX_ERROR: "/auth/refresh",
    # REMOVED_SYNTAX_ERROR: "/auth/logout"
    

    # Get all routes from the app
    # REMOVED_SYNTAX_ERROR: app_routes = []
    # REMOVED_SYNTAX_ERROR: for route in client.app.routes:
        # REMOVED_SYNTAX_ERROR: if hasattr(route, 'path'):
            # REMOVED_SYNTAX_ERROR: app_routes.append(route.path)

            # Check that auth routes don't have double prefix
            # REMOVED_SYNTAX_ERROR: for expected_route in expected_auth_routes:
                # The route should NOT be /auth/auth/login etc
                # REMOVED_SYNTAX_ERROR: double_prefix = expected_route.replace("/auth/", "/auth/auth/")
                # REMOVED_SYNTAX_ERROR: assert double_prefix not in app_routes, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_api_routes_correct_prefix(self, client):
    # REMOVED_SYNTAX_ERROR: """Test that API routes have correct single prefix."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test some key API endpoints
    # REMOVED_SYNTAX_ERROR: api_endpoints = [ )
    # REMOVED_SYNTAX_ERROR: "/api/threads",
    # REMOVED_SYNTAX_ERROR: "/api/messages",
    # REMOVED_SYNTAX_ERROR: "/api/corpus",
    # REMOVED_SYNTAX_ERROR: "/api/agents"
    

    # REMOVED_SYNTAX_ERROR: app_routes = []
    # REMOVED_SYNTAX_ERROR: for route in client.app.routes:
        # REMOVED_SYNTAX_ERROR: if hasattr(route, 'path'):
            # REMOVED_SYNTAX_ERROR: app_routes.append(route.path)

            # REMOVED_SYNTAX_ERROR: for endpoint in api_endpoints:
                # Check the route doesn't have double prefix
                # REMOVED_SYNTAX_ERROR: double_prefix = endpoint.replace("/api/", "/api/api/")
                # REMOVED_SYNTAX_ERROR: assert double_prefix not in app_routes, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_router_registration_without_double_prefix(self):
    # REMOVED_SYNTAX_ERROR: """Test that routers are registered without causing double prefixes."""
    # REMOVED_SYNTAX_ERROR: app = FastAPI()

    # Simulate router registration as done in app_factory
    # REMOVED_SYNTAX_ERROR: from fastapi import APIRouter

    # Create a test router with prefix
    # REMOVED_SYNTAX_ERROR: test_router = APIRouter(prefix="/test")
    # REMOVED_SYNTAX_ERROR: test_router.add_api_route("/endpoint", lambda x: None {"status": "ok"}, methods=["GET"])

    # Register router - should not double the prefix
    # REMOVED_SYNTAX_ERROR: app.include_router(test_router)

    # Check the resulting routes
    # REMOVED_SYNTAX_ERROR: routes = [item for item in []]

    # Should have /test/endpoint, not /test/test/endpoint
    # REMOVED_SYNTAX_ERROR: assert "/test/endpoint" in routes
    # REMOVED_SYNTAX_ERROR: assert "/test/test/endpoint" not in routes

# REMOVED_SYNTAX_ERROR: def test_mcp_client_routes_no_double_prefix(self, app):
    # REMOVED_SYNTAX_ERROR: """Test that MCP client routes don't have double prefixes."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: routes = [item for item in []]

    # MCP routes should not have double prefix
    # REMOVED_SYNTAX_ERROR: mcp_patterns = [ )
    # REMOVED_SYNTAX_ERROR: "/mcp/mcp",
    # REMOVED_SYNTAX_ERROR: "/api/mcp/mcp",
    # REMOVED_SYNTAX_ERROR: "/v1/mcp/mcp"
    

    # REMOVED_SYNTAX_ERROR: for pattern in mcp_patterns:
        # REMOVED_SYNTAX_ERROR: assert not any(pattern in route for route in routes), \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_route_prefix_consistency_across_environments(self):
    # REMOVED_SYNTAX_ERROR: """Test that route prefixes are consistent across different environments."""
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: all_routes = {}

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.config.settings.ENVIRONMENT', env):
            # REMOVED_SYNTAX_ERROR: configs = get_route_configs()
            # REMOVED_SYNTAX_ERROR: prefixes = [c.get('prefix', '') for c in configs]
            # REMOVED_SYNTAX_ERROR: all_routes[env] = set(prefixes)

            # All environments should have the same route prefixes
            # REMOVED_SYNTAX_ERROR: dev_routes = all_routes['development']
            # REMOVED_SYNTAX_ERROR: for env in ['staging', 'production']:
                # REMOVED_SYNTAX_ERROR: assert all_routes[env] == dev_routes, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_auth_routes_registration_fix(self):
    # REMOVED_SYNTAX_ERROR: """Test the specific fix for auth routes registration."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.routes.auth_routes import router as auth_router

    # The router should have its prefix defined only once
    # REMOVED_SYNTAX_ERROR: assert auth_router.prefix in ['', '/auth', None], \
    # REMOVED_SYNTAX_ERROR: "Auth router has unexpected prefix"

    # When included in app, it should not double the prefix
    # REMOVED_SYNTAX_ERROR: app = FastAPI()
    # REMOVED_SYNTAX_ERROR: app.include_router(auth_router, prefix="/auth")

    # REMOVED_SYNTAX_ERROR: routes = [item for item in []]

    # Check for specific auth endpoints
    # REMOVED_SYNTAX_ERROR: assert any("/auth/login" in r for r in routes)
    # REMOVED_SYNTAX_ERROR: assert not any("/auth/auth/login" in r for r in routes)

# REMOVED_SYNTAX_ERROR: def test_refresh_endpoint_routing(self, client):
    # REMOVED_SYNTAX_ERROR: """Test that the refresh endpoint is correctly routed."""
    # The refresh endpoint was specifically mentioned in the commit
    # REMOVED_SYNTAX_ERROR: response = client.options("/auth/refresh")  # OPTIONS request to check if route exists

    # Route should exist (even if it returns 405 for OPTIONS)
    # REMOVED_SYNTAX_ERROR: assert response.status_code in [200, 204, 405], \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_no_conflicting_route_patterns(self, app):
    # REMOVED_SYNTAX_ERROR: """Test that there are no conflicting route patterns."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: routes = []
    # REMOVED_SYNTAX_ERROR: for route in app.routes:
        # REMOVED_SYNTAX_ERROR: if hasattr(route, 'path'):
            # REMOVED_SYNTAX_ERROR: routes.append(route.path)

            # Check for potential conflicts
            # REMOVED_SYNTAX_ERROR: route_set = set()
            # REMOVED_SYNTAX_ERROR: conflicts = []

            # REMOVED_SYNTAX_ERROR: for route in routes:
                # Normalize route for comparison (remove trailing slashes)
                # REMOVED_SYNTAX_ERROR: normalized = route.rstrip('/')
                # REMOVED_SYNTAX_ERROR: if normalized in route_set:
                    # REMOVED_SYNTAX_ERROR: conflicts.append(normalized)
                    # REMOVED_SYNTAX_ERROR: route_set.add(normalized)

                    # REMOVED_SYNTAX_ERROR: assert len(conflicts) == 0, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_route_factory_config_structure(self):
    # REMOVED_SYNTAX_ERROR: """Test that route factory configurations have correct structure."""
    # Mock modules for route config functions
    # REMOVED_SYNTAX_ERROR: mock_modules = {}
    # REMOVED_SYNTAX_ERROR: configs = {}

    # REMOVED_SYNTAX_ERROR: for config in configs:
        # Each config should have required fields
        # REMOVED_SYNTAX_ERROR: assert 'router' in config or 'path' in config, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # If prefix is specified, it should start with /
        # REMOVED_SYNTAX_ERROR: if 'prefix' in config and config['prefix']:
            # REMOVED_SYNTAX_ERROR: assert config['prefix'].startswith('/'), \
            # REMOVED_SYNTAX_ERROR: f"Route prefix doesn"t start with /: {config["prefix"]}"

            # Prefix should not have double slashes
            # REMOVED_SYNTAX_ERROR: assert '//' not in config['prefix'], \
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: pass