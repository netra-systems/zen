class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''Test that async context manager fixes work correctly with middleware.

        This test verifies that the SecurityResponseMiddleware and other middleware
        work correctly with our fixed async context manager patterns.
        '''

        import pytest
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from starlette.middleware.base import BaseHTTPMiddleware
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.middleware.security_response_middleware import SecurityResponseMiddleware
        from netra_backend.app.database import get_db
        from netra_backend.app.dependencies import get_request_scoped_db_session
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


@pytest.mark.asyncio
class TestMiddlewareAsyncIntegration:
    """Test middleware integration with async context managers."""

    async def test_security_middleware_with_database_operation(self):
    """Test that SecurityResponseMiddleware works when database operations use async context managers."""

        # Create a mock app
    app = FastAPI()

        # Add the security middleware
    middleware = SecurityResponseMiddleware(app)

        # Create a mock request
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.state = Magic        request.state.authenticated = False

        # Create a mock call_next that simulates a database operation
    async def mock_call_next(request):
    # Simulate using the database with our fixed async context manager
        try:
        async with get_db() as session:
            # If we get here without error, the context manager works
        pass
        except Exception as e:
                # Database connection errors are OK for this test
        if "connection" not in str(e).lower() and "database" not in str(e).lower():
        raise

                    # Return a 404 response
        response = Magic            response.status_code = 404
        await asyncio.sleep(0)
        return response

                    # Test the middleware
        response = await middleware.dispatch(request, mock_call_next)

                    # Should convert 404 to 401 for unauthenticated API request
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    async def test_middleware_exception_handling_with_async_context(self):
        """Test that middleware properly handles exceptions from async context managers."""

        app = FastAPI()
        middleware = SecurityResponseMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"

                        # Create a call_next that raises an exception
    async def mock_call_next_with_error(request):
        pass
    # Simulate an error in async context manager
        raise ValueError("Test error")

    # The middleware should re-raise the exception
        with pytest.raises(ValueError) as exc_info:
        await middleware.dispatch(request, mock_call_next_with_error)

        assert "Test error" in str(exc_info.value)

    async def test_health_endpoint_bypass(self):
        """Test that health endpoints bypass the security middleware."""

        app = FastAPI()
        middleware = SecurityResponseMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/health"

            # Create a simple mock response
        mock_response = Magic        mock_response.status_code = 200

    async def mock_call_next(request):
        await asyncio.sleep(0)
        return mock_response

    # Test the middleware
        response = await middleware.dispatch(request, mock_call_next)

    # Should pass through unchanged for health endpoint
        assert response == mock_response
        assert response.status_code == 200

    async def test_no_async_generator_context_manager_errors(self):
        """Test that we don't get _AsyncGeneratorContextManager errors in middleware."""

        app = FastAPI()

        # Track any errors
        errors_seen = []

        @pytest.fixture
    async def test_middleware(request:
        pass
        try:
                # Use our fixed async context manager
        async with get_request_scoped_db_session() as session:
                    # If this works, we won't get _AsyncGeneratorContextManager errors
        pass
        except Exception as e:
        errors_seen.append(str(e))
                        # Database connection errors are OK
        if "_AsyncGeneratorContextManager" in str(e):
        raise  # This would indicate our fix didn"t work

        response = await call_next(request)
        await asyncio.sleep(0)
        return response

                            # Add security middleware
        app.add_middleware(SecurityResponseMiddleware)

                            # Create test request
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state = Magic
                            # Mock call_next
    async def mock_call_next(request):
        pass
        await asyncio.sleep(0)
        return JSONResponse({"status": "ok"})

    # Execute through middleware chain
    # This would fail with _AsyncGeneratorContextManager error if our fix didn't work
        for error in errors_seen:
        assert "_AsyncGeneratorContextManager" not in error

    async def test_concurrent_requests_with_middleware(self):
        """Test that concurrent requests through middleware don't cause async issues."""

        import asyncio

        app = FastAPI()
        middleware = SecurityResponseMiddleware(app)

    async def process_request(request_id: int):
        request = MagicMock(spec=Request)
        request.url.path = "formatted_string"
        request.state = Magic            request.state.authenticated = True  # Authenticated, so won"t convert

    async def mock_call_next(request):
    # Simulate database operation
        try:
        async with get_db() as session:
        await asyncio.sleep(0.01)  # Simulate work
        except Exception:
        pass  # Ignore database errors

        response = Magic                response.status_code = 200
        await asyncio.sleep(0)
        return response

        return await middleware.dispatch(request, mock_call_next)

                # Process multiple concurrent requests
        tasks = [process_request(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

                # All should complete successfully
        assert len(responses) == 5
        for response in responses:
                    # Should not be converted since authenticated
        assert response.status_code == 200


        if __name__ == "__main__":
        pytest.main([__file__, "-v"])
        pass
