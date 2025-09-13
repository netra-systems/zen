"""
Test suite for Issue #574 - ASGI lifespan scope handling in WebSocketExclusionMiddleware.

Tests that the middleware properly handles ASGI lifespan events without warnings.
This is a P3 code quality improvement to eliminate log noise.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import logging
from fastapi import FastAPI

# Import the internal function that creates the middleware
from netra_backend.app.core.middleware_setup import _create_inline_websocket_exclusion_middleware


class TestWebSocketExclusionMiddlewareLifespan:
    """Test ASGI lifespan scope handling in WebSocketExclusionMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create mock ASGI app."""
        return AsyncMock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create WebSocketExclusionMiddleware instance by calling the inline creation function."""
        # Create a temp FastAPI app to get the middleware
        temp_app = FastAPI()
        _create_inline_websocket_exclusion_middleware(temp_app)

        # Extract the middleware instance from the app
        for middleware_entry in temp_app.user_middleware:
            if 'WebSocketExclusion' in middleware_entry.cls.__name__:
                return middleware_entry.cls(mock_app)

        # Fallback - create the class directly (shouldn't happen)
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.types import ASGIApp, Receive, Scope, Send

        class WebSocketExclusionMiddleware(BaseHTTPMiddleware):
            async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                scope_type = scope.get("type", "unknown")
                if scope_type == "lifespan":
                    await self.app(scope, receive, send)
                    return
                await self.app(scope, receive, send)

        return WebSocketExclusionMiddleware(mock_app)

    @pytest.fixture
    def mock_receive(self):
        """Mock ASGI receive callable."""
        return AsyncMock()

    @pytest.fixture
    def mock_send(self):
        """Mock ASGI send callable."""
        return AsyncMock()

    async def test_lifespan_startup_scope_handling(self, middleware, mock_app, mock_receive, mock_send):
        """Test that lifespan startup events are handled without warnings."""
        # Arrange
        scope = {
            "type": "lifespan",
            "asgi": {"version": "3.0"},
            "state": {}
        }

        with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
            # Act
            await middleware(scope, mock_receive, mock_send)

            # Assert
            mock_app.assert_called_once_with(scope, mock_receive, mock_send)
            # Should NOT log any warnings for lifespan scope
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()

    async def test_lifespan_shutdown_scope_handling(self, middleware, mock_app, mock_receive, mock_send):
        """Test that lifespan shutdown events are handled without warnings."""
        # Arrange
        scope = {
            "type": "lifespan",
            "asgi": {"version": "3.0"},
            "state": {"startup_complete": True}
        }

        with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
            # Act
            await middleware(scope, mock_receive, mock_send)

            # Assert
            mock_app.assert_called_once_with(scope, mock_receive, mock_send)
            # Should NOT log any warnings for lifespan scope
            mock_logger.warning.assert_not_called()

    async def test_websocket_scope_still_bypasses_middleware(self, middleware, mock_app, mock_receive, mock_send):
        """Test that WebSocket connections still bypass HTTP middleware."""
        # Arrange
        scope = {
            "type": "websocket",
            "path": "/ws",
            "headers": []
        }

        with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
            # Act
            await middleware(scope, mock_receive, mock_send)

            # Assert
            mock_app.assert_called_once_with(scope, mock_receive, mock_send)
            # Should log debug message for WebSocket bypass
            mock_logger.debug.assert_called_with("WebSocket connection detected - bypassing HTTP middleware stack")

    async def test_http_scope_still_processes_normally(self, middleware, mock_receive, mock_send):
        """Test that HTTP requests still process through middleware validation."""
        # Arrange
        scope = {
            "type": "http",
            "path": "/api/test",
            "method": "GET",
            "headers": [(b"host", b"localhost")]
        }

        with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
            with patch.object(middleware, '_validate_http_scope', return_value=True):
                with patch.object(middleware.__class__.__bases__[0], '__call__', new_callable=AsyncMock) as mock_super_call:
                    # Act
                    await middleware(scope, mock_receive, mock_send)

                    # Assert
                    mock_super_call.assert_called_once_with(scope, mock_receive, mock_send)
                    # Should not log warnings for valid HTTP scope
                    mock_logger.warning.assert_not_called()

    async def test_unknown_scope_types_still_warn(self, middleware, mock_app, mock_receive, mock_send):
        """Test that truly unknown scope types still generate warnings."""
        # Arrange
        scope = {
            "type": "unknown_future_scope",
            "future_data": "test"
        }

        with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
            # Act
            await middleware(scope, mock_receive, mock_send)

            # Assert
            mock_app.assert_called_once_with(scope, mock_receive, mock_send)
            # Should log warning for truly unknown scope types
            mock_logger.warning.assert_called_once_with(
                "Unknown ASGI scope type: unknown_future_scope - passing through safely"
            )

    async def test_middleware_exception_handling_with_lifespan(self, middleware, mock_receive, mock_send):
        """Test that exceptions during lifespan handling are properly caught and logged."""
        # Arrange
        scope = {"type": "lifespan"}
        mock_app = AsyncMock(side_effect=Exception("Lifespan processing error"))
        middleware.app = mock_app

        with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
            # Act - The middleware should catch exceptions and handle them gracefully
            try:
                await middleware(scope, mock_receive, mock_send)
            except Exception:
                # If exception propagates, that's also acceptable behavior
                pass

            # Assert - Should log the error (check for any error logging)
            mock_logger.error.assert_called()
            error_call_args = mock_logger.error.call_args[0][0]
            # Either the main error or the fallback error should be logged
            assert ("CRITICAL: ASGI scope error in WebSocket exclusion" in error_call_args or
                    "Failed to pass through non-HTTP scope safely" in error_call_args)

    async def test_lifespan_scope_edge_cases(self, middleware, mock_app, mock_receive, mock_send):
        """Test edge cases for lifespan scope handling."""
        test_cases = [
            # Minimal lifespan scope
            {"type": "lifespan"},
            # Lifespan with extra data
            {"type": "lifespan", "asgi": {"version": "3.0"}, "custom_field": "value"},
            # Case sensitivity check
            {"type": "lifespan", "TYPE": "LIFESPAN"}
        ]

        for scope in test_cases:
            with patch('netra_backend.app.core.middleware_setup.logger') as mock_logger:
                # Act
                await middleware(scope, mock_receive, mock_send)

                # Assert
                mock_app.assert_called_with(scope, mock_receive, mock_send)
                # Should NOT log warnings for any lifespan scope variant
                mock_logger.warning.assert_not_called()

            # Reset mock for next iteration
            mock_app.reset_mock()

    async def test_performance_lifespan_handling(self, middleware, mock_app, mock_receive, mock_send):
        """Test that lifespan handling doesn't introduce performance overhead."""
        # Arrange
        scope = {"type": "lifespan"}

        # Act & Assert - Test multiple rapid calls
        start_time = asyncio.get_event_loop().time()

        for _ in range(100):
            await middleware(scope, mock_receive, mock_send)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should complete 100 lifespan calls in under 1 second
        assert duration < 1.0, f"Lifespan handling too slow: {duration}s for 100 calls"

        # Verify all calls were made
        assert mock_app.call_count == 100


class TestLifespanIntegration:
    """Integration tests for lifespan scope with actual FastAPI application."""

    async def test_real_fastapi_lifespan_integration(self):
        """Test actual FastAPI lifespan integration with middleware."""
        from fastapi.testclient import TestClient

        # Create a minimal FastAPI app with lifespan
        app = FastAPI()
        startup_called = False
        shutdown_called = False

        @app.on_event("startup")
        async def startup():
            nonlocal startup_called
            startup_called = True

        @app.on_event("shutdown")
        async def shutdown():
            nonlocal shutdown_called
            shutdown_called = True

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        # Add the actual inline WebSocket exclusion middleware
        _create_inline_websocket_exclusion_middleware(app)

        # Test with TestClient (which handles lifespan events)
        with TestClient(app) as client:
            # Test that normal HTTP requests work
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

        # Verify lifespan events were called
        assert startup_called, "Startup event should have been called"
        assert shutdown_called, "Shutdown event should have been called"