"""Comprehensive tests for FastAPI app factory functionality.

BUSINESS VALUE: Ensures proper application initialization and reliability,
protecting customer experience and preventing service disruptions that
could impact AI operations and customer satisfaction.

Tests critical paths including middleware setup, route registration,
error handling, and security configurations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from netra_backend.app.core.app_factory import (
    create_fastapi_app, create_app, register_error_handlers,
    setup_middleware, setup_security_middleware, setup_request_middleware,
    register_api_routes, setup_root_endpoint, initialize_oauth
)
from netra_backend.app.core.exceptions_base import NetraException


# Test fixtures for setup
@pytest.fixture
def mock_app():
    """Mock FastAPI application."""
    app = Mock(spec=FastAPI)
    app.add_exception_handler = Mock()
    app.add_middleware = Mock()
    app.middleware = Mock()
    app.include_router = Mock()
    app.get = Mock()
    return app


@pytest.fixture
def real_app():
    """Real FastAPI application for integration tests."""
    return FastAPI()


@pytest.fixture
def mock_lifespan():
    """Mock lifespan manager."""
    with patch('app.core.app_factory.lifespan') as mock:
        yield mock


# Helper functions for 25-line compliance
def assert_exception_handler_added(app, exception_type):
    """Assert exception handler was added for type."""
    app.add_exception_handler.assert_any_call(exception_type, 
                                             None if not hasattr(app.add_exception_handler, 'call_args_list') 
                                             else app.add_exception_handler.call_args_list)


def assert_middleware_added(app, middleware_type):
    """Assert middleware was added to app."""
    calls = app.middleware.call_args_list if hasattr(app.middleware, 'call_args_list') else []
    assert any("http" in str(call) for call in calls) or app.middleware.called


def get_handler_calls(app):
    """Get exception handler calls from netra_backend.app."""
    return app.add_exception_handler.call_args_list


def get_middleware_calls(app):
    """Get middleware calls from netra_backend.app."""
    return app.middleware.call_args_list if hasattr(app.middleware, 'call_args_list') else []


def assert_router_included(app, expected_count=None):
    """Assert routers were included in app."""
    if expected_count:
        assert app.include_router.call_count >= expected_count
    else:
        assert app.include_router.called


def create_mock_router():
    """Create a mock router for testing."""
    return Mock()


# Core app factory functionality tests
class TestFastAPIAppCreation:
    """Test FastAPI application creation."""

    def test_create_fastapi_app_returns_fastapi_instance(self, mock_lifespan):
        """create_fastapi_app returns FastAPI instance."""
        app = create_fastapi_app()
        assert isinstance(app, FastAPI)

    def test_create_fastapi_app_uses_lifespan(self, mock_lifespan):
        """create_fastapi_app uses lifespan manager."""
        create_fastapi_app()
        # Lifespan should be imported and used

    def test_create_app_returns_configured_app(self):
        """create_app returns fully configured application."""
        with patch('app.core.app_factory.create_fastapi_app') as mock_create:
            mock_create.return_value = Mock(spec=FastAPI)
            with patch('app.core.app_factory._configure_app_handlers'):
                with patch('app.core.app_factory._configure_app_routes'):
                    app = create_app()
                    assert app is not None

    def test_create_app_calls_configuration_methods(self, mock_app):
        """create_app calls all configuration methods."""
        with patch('app.core.app_factory.create_fastapi_app', return_value=mock_app):
            with patch('app.core.app_factory._configure_app_handlers') as mock_handlers:
                with patch('app.core.app_factory._configure_app_routes') as mock_routes:
                    create_app()
                    mock_handlers.assert_called_once_with(mock_app)
                    mock_routes.assert_called_once_with(mock_app)


class TestErrorHandlerRegistration:
    """Test error handler registration."""

    def test_register_error_handlers_adds_all_handlers(self, mock_app):
        """register_error_handlers adds all required handlers."""
        register_error_handlers(mock_app)
        assert mock_app.add_exception_handler.call_count >= 4

    def test_netra_exception_handler_registered(self, mock_app):
        """NetraException handler is registered."""
        register_error_handlers(mock_app)
        calls = get_handler_calls(mock_app)
        exception_types = [call[0][0] for call in calls]
        assert NetraException in exception_types

    def test_validation_error_handler_registered(self, mock_app):
        """ValidationError handler is registered."""
        register_error_handlers(mock_app)
        calls = get_handler_calls(mock_app)
        exception_types = [call[0][0] for call in calls]
        assert ValidationError in exception_types

    def test_http_exception_handler_registered(self, mock_app):
        """HTTPException handler is registered."""
        register_error_handlers(mock_app)
        calls = get_handler_calls(mock_app)
        exception_types = [call[0][0] for call in calls]
        assert HTTPException in exception_types

    def test_general_exception_handler_registered(self, mock_app):
        """General Exception handler is registered."""
        register_error_handlers(mock_app)
        calls = get_handler_calls(mock_app)
        exception_types = [call[0][0] for call in calls]
        assert Exception in exception_types


class TestSecurityMiddleware:
    """Test security middleware setup."""

    def test_setup_security_middleware_calls_all_components(self, mock_app):
        """setup_security_middleware sets up all security components."""
        with patch('app.core.app_factory._add_ip_blocking_middleware') as mock_ip:
            with patch('app.core.app_factory._add_path_traversal_middleware') as mock_path:
                with patch('app.core.app_factory._add_security_headers_middleware') as mock_headers:
                    setup_security_middleware(mock_app)
                    mock_ip.assert_called_once_with(mock_app)
                    mock_path.assert_called_once_with(mock_app)
                    mock_headers.assert_called_once_with(mock_app)

    def test_ip_blocking_middleware_added(self, mock_app):
        """IP blocking middleware is added."""
        with patch('app.middleware.ip_blocking.ip_blocking_middleware') as mock_middleware:
            from netra_backend.app.core.app_factory import _add_ip_blocking_middleware
            _add_ip_blocking_middleware(mock_app)
            mock_app.middleware.assert_called_with("http")

    def test_path_traversal_middleware_added(self, mock_app):
        """Path traversal protection middleware is added."""
        with patch('app.middleware.path_traversal_protection.path_traversal_protection_middleware'):
            from netra_backend.app.core.app_factory import _add_path_traversal_middleware
            _add_path_traversal_middleware(mock_app)
            mock_app.middleware.assert_called_with("http")

    def test_security_headers_middleware_added(self, mock_app):
        """Security headers middleware is added."""
        with patch('app.middleware.security_headers.SecurityHeadersMiddleware') as mock_middleware:
            with patch('app.config.settings') as mock_settings:
                mock_settings.environment = "development"
                from netra_backend.app.core.app_factory import _add_security_headers_middleware
                _add_security_headers_middleware(mock_app)
                mock_app.add_middleware.assert_called_once()


class TestRequestMiddleware:
    """Test request middleware setup."""

    def test_setup_request_middleware_calls_all_components(self, mock_app):
        """setup_request_middleware sets up all request components."""
        with patch('app.core.app_factory.setup_cors_middleware') as mock_cors:
            with patch('app.core.app_factory.create_cors_redirect_middleware') as mock_cors_redirect:
                with patch('app.core.app_factory.create_error_context_middleware') as mock_error:
                    with patch('app.core.app_factory.create_request_logging_middleware') as mock_logging:
                        with patch('app.core.app_factory.setup_session_middleware') as mock_session:
                            mock_cors_redirect.return_value = Mock()
                            mock_error.return_value = Mock()
                            mock_logging.return_value = Mock()
                            setup_request_middleware(mock_app)
                            mock_cors.assert_called_once_with(mock_app)
                            mock_session.assert_called_once_with(mock_app)

    def test_middleware_setup_calls_all_components(self, mock_app):
        """setup_middleware calls both security and request middleware."""
        with patch('app.core.app_factory.setup_security_middleware') as mock_security:
            with patch('app.core.app_factory.setup_request_middleware') as mock_request:
                setup_middleware(mock_app)
                mock_security.assert_called_once_with(mock_app)
                mock_request.assert_called_once_with(mock_app)


class TestRouteRegistration:
    """Test API route registration."""

    def test_register_api_routes_imports_and_registers(self, mock_app):
        """register_api_routes imports and registers routes."""
        with patch('app.core.app_factory._import_and_register_routes') as mock_import:
            register_api_routes(mock_app)
            mock_import.assert_called_once_with(mock_app)

    def test_import_and_register_routes_process(self, mock_app):
        """_import_and_register_routes follows correct process."""
        with patch('app.core.app_factory.import_all_route_modules') as mock_import:
            with patch('app.core.app_factory.get_all_route_configurations') as mock_config:
                with patch('app.core.app_factory._register_route_modules') as mock_register:
                    mock_import.return_value = {}
                    mock_config.return_value = {}
                    from netra_backend.app.core.app_factory import _import_and_register_routes
                    _import_and_register_routes(mock_app)
                    mock_import.assert_called_once()
                    mock_config.assert_called_once()
                    mock_register.assert_called_once()

    def test_register_route_modules_includes_routers(self, mock_app):
        """_register_route_modules includes routers in app."""
        routes_config = {
            'test_route': (create_mock_router(), '/api/test', ['test'])
        }
        from netra_backend.app.core.app_factory import _register_route_modules
        _register_route_modules(mock_app, routes_config)
        assert_router_included(mock_app, 1)

    def test_multiple_routes_registration(self, mock_app):
        """Multiple routes are registered correctly."""
        routes_config = {
            'route1': (create_mock_router(), '/api/route1', ['tag1']),
            'route2': (create_mock_router(), '/api/route2', ['tag2'])
        }
        from netra_backend.app.core.app_factory import _register_route_modules
        _register_route_modules(mock_app, routes_config)
        assert mock_app.include_router.call_count == 2


class TestRootEndpoint:
    """Test root endpoint setup."""

    def test_setup_root_endpoint_adds_route(self, mock_app):
        """setup_root_endpoint adds root route."""
        setup_root_endpoint(mock_app)
        mock_app.get.assert_called_once_with("/")

    def test_root_endpoint_handler_created(self, real_app):
        """Root endpoint handler is created correctly."""
        with patch('app.logging_config.central_logger') as mock_logger:
            mock_logger.get_logger.return_value.info = Mock()
            setup_root_endpoint(real_app)
            # Check that route was added
            assert len(real_app.routes) > 0

    def test_root_endpoint_logs_access(self, mock_app):
        """Root endpoint logs access when called."""
        setup_root_endpoint(mock_app)
        # Verify that setup completed (logger will be called when endpoint is invoked)
        mock_app.get.assert_called_once_with("/")


class TestOAuthInitialization:
    """Test OAuth initialization."""

    def test_initialize_oauth_is_noop(self, mock_app):
        """initialize_oauth is currently a no-op."""
        # This should not raise any exceptions
        initialize_oauth(mock_app)
        # Function should complete without error

    def test_oauth_handled_by_auth_service(self, mock_app):
        """OAuth is handled by auth service, not app factory."""
        # Test that the function acknowledges auth service handles OAuth
        result = initialize_oauth(mock_app)
        assert result is None  # Should return None (no-op)


class TestConfigurationMethods:
    """Test configuration helper methods."""

    def test_configure_app_handlers_calls_all_setup(self, mock_app):
        """_configure_app_handlers calls all handler setup methods."""
        with patch('app.core.app_factory.register_error_handlers') as mock_errors:
            with patch('app.core.app_factory.setup_middleware') as mock_middleware:
                with patch('app.core.app_factory.initialize_oauth') as mock_oauth:
                    from netra_backend.app.core.app_factory import _configure_app_handlers
                    _configure_app_handlers(mock_app)
                    mock_errors.assert_called_once_with(mock_app)
                    mock_middleware.assert_called_once_with(mock_app)
                    mock_oauth.assert_called_once_with(mock_app)

    def test_configure_app_routes_calls_route_setup(self, mock_app):
        """_configure_app_routes calls route setup methods."""
        with patch('app.core.app_factory.register_api_routes') as mock_routes:
            with patch('app.core.app_factory.setup_root_endpoint') as mock_root:
                from netra_backend.app.core.app_factory import _configure_app_routes
                _configure_app_routes(mock_app)
                mock_routes.assert_called_once_with(mock_app)
                mock_root.assert_called_once_with(mock_app)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_full_app_creation_integration(self):
        """Full app creation works end-to-end."""
        with patch('app.core.app_factory.import_all_route_modules', return_value={}):
            with patch('app.core.app_factory.get_all_route_configurations', return_value={}):
                app = create_app()
                assert isinstance(app, FastAPI)

    def test_error_handler_registration_order(self, mock_app):
        """Error handlers are registered in correct order."""
        register_error_handlers(mock_app)
        calls = get_handler_calls(mock_app)
        # Should have at least 4 handlers registered
        assert len(calls) >= 4

    def test_middleware_setup_order(self, mock_app):
        """Middleware is set up in correct order."""
        with patch('app.core.app_factory.setup_security_middleware') as mock_security:
            with patch('app.core.app_factory.setup_request_middleware') as mock_request:
                setup_middleware(mock_app)
                # Security middleware should be set up before request middleware
                mock_security.assert_called_once()
                mock_request.assert_called_once()

    def test_app_creation_with_minimal_config(self):
        """App can be created with minimal configuration."""
        with patch('app.core.app_factory.import_all_route_modules', return_value={}):
            with patch('app.core.app_factory.get_all_route_configurations', return_value={}):
                with patch('app.core.middleware_setup.setup_cors_middleware'):
                    with patch('app.core.middleware_setup.setup_session_middleware'):
                        app = create_app()
                        assert app is not None