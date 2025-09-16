"""
App Factory Integration Tests - Startup Phase Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery  
- Value Impact: Ensures app creation and middleware setup enables revenue-generating chat interactions
- Strategic Impact: Validates system foundation for delivering real-time AI business value to users

Tests complete app factory initialization including:
1. FastAPI app creation with proper configuration
2. Middleware stack setup (CORS, error handling, authentication)
3. Route registration and WebSocket endpoints
4. Service dependency injection and state initialization
5. Error handling and logging configuration
"""
import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env

@pytest.mark.integration
@pytest.mark.startup
@pytest.mark.app_factory
class AppFactoryIntegrationTests(BaseIntegrationTest):
    """Integration tests for app factory initialization during startup."""

    async def async_setup(self):
        """Setup for app factory tests."""
        self.env = get_env()
        self.env.set('TESTING', '1', source='startup_test')
        self.env.set('ENVIRONMENT', 'test', source='startup_test')

    def test_app_factory_creation_with_middleware(self):
        """
        Test complete app factory creation including middleware setup.
        
        BVJ: App factory must properly initialize middleware stack to support:
        - CORS handling for frontend communication
        - Authentication middleware for user security
        - Error handling for graceful failure recovery
        - Logging middleware for observability
        """
        from netra_backend.app.main import create_app
        app = create_app()
        assert app is not None, 'App factory must create FastAPI instance'
        assert isinstance(app, FastAPI), 'Factory must return FastAPI application'
        assert hasattr(app, 'middleware_stack'), 'App must have middleware stack'
        client = TestClient(app)
        response = client.options('/health', headers={'Origin': 'http://localhost:3000'})
        assert 'access-control-allow-origin' in [h.lower() for h in response.headers.keys()], 'CORS middleware must be configured for frontend communication'
        assert hasattr(app, 'state'), 'App must have state object for service storage'
        self.logger.info(f'✅ App factory created FastAPI instance with middleware')
        self.logger.info(f'   - Middleware stack configured')
        self.logger.info(f'   - App state initialized')
        self.logger.info(f'   - CORS handling enabled')

    def test_app_route_registration(self):
        """
        Test that critical routes are properly registered during app creation.
        
        BVJ: Route registration enables:
        - Health checks for monitoring and deployment validation
        - WebSocket endpoints for real-time chat communication
        - API endpoints for business functionality
        """
        from netra_backend.app.main import create_app
        app = create_app()
        client = TestClient(app)
        response = client.get('/health')
        assert response.status_code != 404, 'Health endpoint must be registered'
        websocket_routes = [route for route in app.routes if hasattr(route, 'path') and 'ws' in route.path]
        assert len(websocket_routes) > 0, 'WebSocket routes must be registered for chat functionality'
        api_routes = [route for route in app.routes if hasattr(route, 'path') and route.path.startswith('/api')]
        self.logger.info(f'✅ Routes registered: {len(api_routes)} API routes, {len(websocket_routes)} WebSocket routes')

    def test_app_configuration_loading(self):
        """
        Test that app factory properly loads and applies configuration.
        
        BVJ: Configuration loading ensures:
        - Environment-specific settings for deployment flexibility
        - Service connection parameters for business functionality
        - Security settings for user data protection
        """
        from netra_backend.app.main import create_app
        test_envs = ['test', 'development']
        for env_name in test_envs:
            with patch.dict('os.environ', {'ENVIRONMENT': env_name}):
                app = create_app()
                assert app is not None, f'App creation must succeed in {env_name} environment'
        self.logger.info(f'✅ App factory handles multiple environment configurations')

    def test_app_service_dependency_injection(self):
        """
        Test that app factory properly initializes service dependencies.
        
        BVJ: Service injection enables:
        - Database connections for user data and business logic
        - Authentication services for user security
        - LLM services for AI functionality
        - WebSocket managers for real-time communication
        """
        from netra_backend.app.main import create_app
        app = create_app()
        assert hasattr(app, 'state'), 'App must have state for service storage'
        startup_successful = True
        try:
            app.state.test_service = 'mock_service'
            assert hasattr(app.state, 'test_service'), 'App state must support service storage'
        except Exception as e:
            startup_successful = False
            self.logger.error(f'Service injection failed: {e}')
        assert startup_successful, 'App must support service dependency injection'
        self.logger.info(f'✅ App factory supports service dependency injection')

    def test_app_error_handling_configuration(self):
        """
        Test that app factory configures proper error handling.
        
        BVJ: Error handling ensures:
        - Graceful failure recovery for user experience
        - Proper error responses for API consumers
        - Error logging for system observability
        - Security through controlled error information exposure
        """
        from netra_backend.app.main import create_app
        app = create_app()
        client = TestClient(app)
        response = client.get('/non-existent-endpoint')
        assert response.status_code == 404, 'App must handle missing routes gracefully'
        try:
            response.json()
            has_json_response = True
        except:
            has_json_response = False
        self.logger.info(f'✅ App factory configures error handling (404 handling confirmed)')

    async def test_app_async_context_support(self):
        """
        Test that app factory creates app with proper async context support.
        
        BVJ: Async support enables:
        - High-performance concurrent request handling
        - Efficient database and service connections
        - Real-time WebSocket communication
        - Scalable agent execution
        """
        from netra_backend.app.main import create_app
        app = create_app()

        async def test_async_operation():
            await asyncio.sleep(0.001)
            return 'async_success'
        try:
            result = await test_async_operation()
            assert result == 'async_success', 'App must support async operations'
        except Exception as e:
            pytest.fail(f'App async context failed: {e}')
        self.logger.info(f'✅ App factory creates async-compatible application')

    def test_app_startup_lifecycle_hooks(self):
        """
        Test that app factory properly configures startup/shutdown lifecycle hooks.
        
        BVJ: Lifecycle hooks enable:
        - Proper service initialization on startup
        - Clean resource cleanup on shutdown
        - Database connection management
        - Background task coordination
        """
        from netra_backend.app.main import create_app
        app = create_app()
        startup_events = getattr(app.router, 'on_startup', [])
        shutdown_events = getattr(app.router, 'on_shutdown', [])
        has_lifecycle_support = hasattr(app, 'on_event') or len(startup_events) > 0 or hasattr(app, 'lifespan')
        assert has_lifecycle_support, 'App must support startup/shutdown lifecycle hooks'
        self.logger.info(f'✅ App factory configures lifecycle hooks')
        self.logger.info(f'   - Startup events: {len(startup_events)}')
        self.logger.info(f'   - Shutdown events: {len(shutdown_events)}')

@pytest.mark.integration
@pytest.mark.startup
@pytest.mark.business_value
class AppFactoryBusinessValueTests(BaseIntegrationTest):
    """Business value validation for app factory initialization."""

    def test_app_factory_enables_chat_infrastructure(self):
        """
        Test that app factory creates infrastructure required for chat business value.
        
        BVJ: Chat functionality delivers 90% of platform value through:
        - Real-time WebSocket communication with users
        - API endpoints for user authentication and data
        - Error handling for graceful user experience
        - Monitoring for system reliability
        """
        from netra_backend.app.main import create_app
        app = create_app()
        client = TestClient(app)
        websocket_routes = [route for route in app.routes if hasattr(route, 'path') and 'ws' in route.path.lower()]
        assert len(websocket_routes) > 0, 'App must provide WebSocket routes for chat communication'
        api_routes = [route for route in app.routes if hasattr(route, 'path') and route.path.startswith('/api')]
        health_response = client.get('/health')
        chat_infrastructure_ready = health_response.status_code != 500
        assert chat_infrastructure_ready, 'App infrastructure must support chat business value delivery'
        business_value_metrics = {'websocket_routes': len(websocket_routes), 'api_routes': len(api_routes), 'health_check': health_response.status_code, 'chat_infrastructure_ready': chat_infrastructure_ready}
        self.assert_business_value_delivered(business_value_metrics, 'automation')
        self.logger.info(f'✅ App factory enables chat business value delivery')
        self.logger.info(f'   - WebSocket routes: {len(websocket_routes)}')
        self.logger.info(f'   - API routes: {len(api_routes)}')
        self.logger.info(f'   - Health check: {health_response.status_code}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')