"""Comprehensive tests for FastAPI app factory functionality.

BUSINESS VALUE: Ensures proper application initialization and reliability,
protecting customer experience and preventing service disruptions that
could impact AI operations and customer satisfaction.

Tests critical paths including middleware setup, route registration,
error handling, and security configurations.

MOCK JUSTIFICATION: L1 Unit Tests - Mocking FastAPI app components to isolate
app factory logic. Real application initialization tested in L3 integration tests.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.app_factory import (
    create_app,
    create_fastapi_app,
    initialize_oauth,
    register_api_routes,
    register_error_handlers,
    setup_middleware,
    setup_request_middleware,
    setup_root_endpoint,
    setup_security_middleware
)
from netra_backend.app.core.exceptions_base import NetraException


class TestFastAPIAppCreation:
    """Test FastAPI application creation."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        app = Mock(spec=FastAPI)
        app.add_exception_handler = Mock()
        app.add_middleware = Mock()
        app.middleware = Mock()
        app.include_router = Mock()
        app.get = Mock()
        return app

    @pytest.fixture
    def minimal_app(self):
        """Real minimal FastAPI app for lifecycle testing."""
        return FastAPI()

    def test_create_fastapi_app_returns_fastapi_instance(self):
        """create_fastapi_app returns FastAPI instance."""
        with patch('netra_backend.app.core.app_factory.lifespan'):
            app = create_fastapi_app()
            assert isinstance(app, FastAPI)

    def test_create_app_returns_configured_app(self):
        """create_app returns fully configured application."""
        with patch('netra_backend.app.core.app_factory.create_fastapi_app') as mock_create:
            mock_create.return_value = Mock(spec=FastAPI)
            with patch('netra_backend.app.core.app_factory._configure_app_handlers'):
                with patch('netra_backend.app.core.app_factory._configure_app_routes'):
                    app = create_app()
                    assert app is not None


class TestErrorHandlerRegistration:
    """Test error handler registration."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        app = Mock(spec=FastAPI)
        app.add_exception_handler = Mock()
        return app

    def test_register_error_handlers_adds_all_handlers(self, mock_app):
        """register_error_handlers adds all required handlers."""
        register_error_handlers(mock_app)
        assert mock_app.add_exception_handler.call_count >= 4

    def test_netra_exception_handler_registered(self, mock_app):
        """NetraException handler is registered."""
        register_error_handlers(mock_app)
        calls = mock_app.add_exception_handler.call_args_list
        exception_types = [call[0][0] for call in calls]
        assert NetraException in exception_types

    def test_validation_error_handler_registered(self, mock_app):
        """ValidationError handler is registered."""
        register_error_handlers(mock_app)
        calls = mock_app.add_exception_handler.call_args_list
        exception_types = [call[0][0] for call in calls]
        assert ValidationError in exception_types

    def test_http_exception_handler_registered(self, mock_app):
        """HTTPException handler is registered."""
        register_error_handlers(mock_app)
        calls = mock_app.add_exception_handler.call_args_list
        exception_types = [call[0][0] for call in calls]
        assert HTTPException in exception_types


class TestSecurityMiddleware:
    """Test security middleware setup."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        app = Mock(spec=FastAPI)
        app.add_middleware = Mock()
        app.middleware = Mock()
        return app

    def test_setup_security_middleware_calls_all_components(self, mock_app):
        """setup_security_middleware sets up all security components."""
        with patch('netra_backend.app.core.app_factory._add_path_traversal_middleware') as mock_path:
            with patch('netra_backend.app.core.app_factory._add_security_headers_middleware') as mock_headers:
                setup_security_middleware(mock_app)
                mock_path.assert_called_once_with(mock_app)
                mock_headers.assert_called_once_with(mock_app)


class TestRequestMiddleware:
    """Test request middleware setup."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        app = Mock(spec=FastAPI)
        app.add_middleware = Mock()
        app.middleware = Mock()
        return app

    def test_setup_request_middleware_calls_all_components(self, mock_app):
        """setup_request_middleware sets up all request components."""
        with patch('netra_backend.app.core.app_factory.setup_cors_middleware') as mock_cors:
            with patch('netra_backend.app.core.app_factory.create_cors_redirect_middleware') as mock_cors_redirect:
                with patch('netra_backend.app.core.app_factory.create_error_context_middleware') as mock_error:
                    with patch('netra_backend.app.core.app_factory.create_request_logging_middleware') as mock_logging:
                        with patch('netra_backend.app.core.app_factory.setup_session_middleware') as mock_session:
                            mock_cors_redirect.return_value = Mock()
                            mock_error.return_value = Mock()
                            mock_logging.return_value = Mock()
                            setup_request_middleware(mock_app)
                            mock_cors.assert_called_once_with(mock_app)
                            mock_session.assert_called_once_with(mock_app)

    def test_middleware_setup_calls_all_components(self, mock_app):
        """setup_middleware calls both security and request middleware."""
        with patch('netra_backend.app.core.app_factory.setup_security_middleware') as mock_security:
            with patch('netra_backend.app.core.app_factory.setup_request_middleware') as mock_request:
                setup_middleware(mock_app)
                mock_security.assert_called_once_with(mock_app)
                mock_request.assert_called_once_with(mock_app)


class TestRouteRegistration:
    """Test API route registration."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        app = Mock(spec=FastAPI)
        app.include_router = Mock()
        return app

    def test_register_api_routes_imports_and_registers(self, mock_app):
        """register_api_routes imports and registers routes."""
        with patch('netra_backend.app.core.app_factory._import_and_register_routes') as mock_import:
            register_api_routes(mock_app)
            mock_import.assert_called_once_with(mock_app)


class TestRootEndpoint:
    """Test root endpoint setup."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        app = Mock(spec=FastAPI)
        app.get = Mock()
        return app

    def test_setup_root_endpoint_adds_route(self, mock_app):
        """setup_root_endpoint adds root route."""
        setup_root_endpoint(mock_app)
        mock_app.get.assert_called_once_with("/")


class TestOAuthInitialization:
    """Test OAuth initialization."""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        return Mock(spec=FastAPI)

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


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_full_app_creation_integration(self):
        """Full app creation works end-to-end."""
        with patch('netra_backend.app.core.app_factory.import_all_route_modules', return_value={}):
            with patch('netra_backend.app.core.app_factory.get_all_route_configurations', return_value={}):
                app = create_app()
                assert isinstance(app, FastAPI)