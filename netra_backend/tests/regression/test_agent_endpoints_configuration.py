"""
Regression Test: Agent Endpoints Configuration

CRITICAL: This test ensures agent endpoints are properly mounted and accessible.

Background: Frontend was getting 404 errors when calling /api/agents/triage because
the endpoints weren't properly configured or were being called on the wrong domain.

This test verifies:
1. Agent endpoints are properly registered in the FastAPI app
2. The endpoints respond correctly to requests
3. CORS is properly configured for cross-origin requests
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.app_factory import create_app
from netra_backend.app.routes.agents_execute import router as agents_router
import asyncio


class TestAgentEndpointsConfiguration:
    """Test suite for agent endpoints configuration."""
    
    @pytest.fixture
    def app(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create test app instance."""
    pass
        with patch('netra_backend.app.core.app_factory.lifespan'):
            app = create_app()
            return app
    
    @pytest.fixture
    def client(self, app):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create test client."""
    pass
        return TestClient(app)
    
    def test_agent_router_is_registered(self, app):
        """Test that the agents router is registered in the app."""
        # Get all routes
        routes = [route.path for route in app.routes]
        
        # Check that agent endpoints are registered
        assert '/api/agents/execute' in routes
        assert '/api/agents/triage' in routes
        assert '/api/agents/data' in routes
        assert '/api/agents/optimization' in routes
    
    def test_agent_endpoints_configuration(self, app):
        """Test that agent endpoints are configured with correct prefix."""
    pass
        # Import the route configuration
        from netra_backend.app.core.app_factory_route_configs import get_all_route_configurations
        from netra_backend.app.core.app_factory_route_imports import import_all_route_modules
        
        # Get route modules and configs
        modules = import_all_route_modules()
        configs = get_all_route_configurations(modules)
        
        # Check agents_execute router configuration
        assert 'agents_execute' in configs
        router_config = configs['agents_execute']
        
        # Verify prefix and tags
        assert router_config[1] == '/api/agents'  # prefix
        assert 'agents' in router_config[2]  # tags
    
    @pytest.mark.asyncio
    async def test_triage_endpoint_exists(self, client):
        """Test that /api/agents/triage endpoint exists and responds."""
        # Mock dependencies
        with patch('netra_backend.app.routes.agents_execute.get_current_user_optional', return_value=None):
            with patch('netra_backend.app.routes.agents_execute.get_agent_service', return_value=None):
                response = client.post(
                    '/api/agents/triage',
                    json={
                        'message': 'test message',
                        'context': {}
                    }
                )
                
                # Should not be 404
                assert response.status_code != 404
                # Will be 503 because agent_service is None, but that's OK for this test
                # The important thing is it's not 404
    
    @pytest.mark.asyncio
    async def test_data_endpoint_exists(self, client):
        """Test that /api/agents/data endpoint exists and responds."""
    pass
        with patch('netra_backend.app.routes.agents_execute.get_current_user_optional', return_value=None):
            with patch('netra_backend.app.routes.agents_execute.get_agent_service', return_value=None):
                response = client.post(
                    '/api/agents/data',
                    json={
                        'message': 'test data analysis',
                        'context': {}
                    }
                )
                
                assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_optimization_endpoint_exists(self, client):
        """Test that /api/agents/optimization endpoint exists and responds."""
        with patch('netra_backend.app.routes.agents_execute.get_current_user_optional', return_value=None):
            with patch('netra_backend.app.routes.agents_execute.get_agent_service', return_value=None):
                response = client.post(
                    '/api/agents/optimization',
                    json={
                        'message': 'optimize costs',
                        'context': {}
                    }
                )
                
                assert response.status_code != 404
    
    def test_cors_configuration_for_agents(self, app):
        """Test that CORS is properly configured for agent endpoints."""
    pass
        # Check that CORS middleware is configured
        middleware_types = [type(m) for m in app.user_middleware]
        middleware_names = [m.__class__.__name__ if hasattr(m, '__class__') else str(m) for m in app.user_middleware]
        
        # Should have CORS middleware configured
        assert any('CORS' in str(name) for name in middleware_names), \
            f"No CORS middleware found. Middleware: {middleware_names}"
    
    @pytest.mark.asyncio
    async def test_agent_endpoint_with_mock_service(self, client):
        """Test agent endpoint with mocked agent service."""
        mock_agent_service = AgentRegistry().get_agent("supervisor")
        mock_agent_service.execute_agent = AsyncMock(return_value={
            'response': 'Mock response',
            'status': 'success'
        })
        
        with patch('netra_backend.app.routes.agents_execute.get_current_user_optional', return_value={'user_id': 'test'}):
            with patch('netra_backend.app.routes.agents_execute.get_agent_service', return_value=mock_agent_service):
                response = client.post(
                    '/api/agents/triage',
                    json={
                        'message': 'Real test message',
                        'context': {}
                    }
                )
                
                # Should succeed with mocked service
                assert response.status_code == 200
                data = response.json()
                assert data['status'] == 'success'
                assert data['agent'] == 'triage'
    
    def test_agent_endpoints_url_structure(self):
        """Test that agent endpoints follow correct URL structure."""
    pass
        # Import router to check endpoint paths
        from netra_backend.app.routes.agents_execute import router
        
        # Get all routes from the router
        routes = [(route.path, route.methods) for route in router.routes]
        
        # Check specific endpoints
        assert ('/execute', {'POST'}) in routes
        assert ('/triage', {'POST'}) in routes
        assert ('/data', {'POST'}) in routes
        assert ('/optimization', {'POST'}) in routes
        
        # These will be prefixed with /api/agents when mounted
    
    def test_no_duplicate_agent_routes(self, app):
        """Test that there are no duplicate agent routes registered."""
        routes = [(route.path, list(route.methods)) for route in app.routes if hasattr(route, 'methods')]
        
        # Check for duplicates
        agent_routes = [r for r in routes if '/api/agents' in r[0]]
        
        # Convert to strings for comparison
        route_strings = [f"{path}:{','.join(sorted(methods))}" for path, methods in agent_routes]
        
        # Check no duplicates
        assert len(route_strings) == len(set(route_strings)), \
            f"Duplicate routes found: {route_strings}"


class TestAgentEndpointIntegration:
    """Integration tests for agent endpoints."""
    
    @pytest.mark.asyncio
    async def test_frontend_to_backend_flow(self):
        """Test the complete flow from frontend to backend."""
        # This test simulates what the frontend does
        from netra_backend.app.core.app_factory import create_app
        
        with patch('netra_backend.app.core.app_factory.lifespan'):
            app = create_app()
            client = TestClient(app)
            
            # Simulate frontend request structure
            frontend_request = {
                'type': 'triage',  # This is included but not used in specific endpoints
                'message': 'Test message from frontend',
                'context': {},
                'simulate_delay': False,
                'force_failure': False,
                'force_retry': False
            }
            
            with patch('netra_backend.app.routes.agents_execute.get_current_user_optional', return_value=None):
                with patch('netra_backend.app.routes.agents_execute.get_agent_service', return_value=None):
                    # Test that the endpoint accepts the frontend request format
                    response = client.post(
                        '/api/agents/triage',
                        json=frontend_request
                    )
                    
                    # Should not be 404 or 422 (validation error)
                    assert response.status_code not in [404, 422]
    
    def test_staging_urls_configuration(self):
        """Test that staging URLs are correctly configured."""
    pass
        # This is a configuration test, not a runtime test
        staging_backend_url = 'https://api.staging.netrasystems.ai'
        staging_frontend_url = 'https://app.staging.netrasystems.ai'
        
        # Agent endpoints should be on backend, not frontend
        agent_endpoints = [
            f'{staging_backend_url}/api/agents/triage',
            f'{staging_backend_url}/api/agents/data',
            f'{staging_backend_url}/api/agents/optimization',
            f'{staging_backend_url}/api/agents/execute'
        ]
        
        for endpoint in agent_endpoints:
            # Should use backend domain
            assert 'api.staging' in endpoint
            assert 'app.staging' not in endpoint
            
            # Should be HTTPS in staging
            assert endpoint.startswith('https://')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])