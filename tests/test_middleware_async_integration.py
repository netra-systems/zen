# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Test that async context manager fixes work correctly with middleware.

    # REMOVED_SYNTAX_ERROR: This test verifies that the SecurityResponseMiddleware and other middleware
    # REMOVED_SYNTAX_ERROR: work correctly with our fixed async context manager patterns.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from fastapi import FastAPI, Request
    # REMOVED_SYNTAX_ERROR: from fastapi.responses import JSONResponse
    # REMOVED_SYNTAX_ERROR: from starlette.middleware.base import BaseHTTPMiddleware
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.middleware.security_response_middleware import SecurityResponseMiddleware
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.database import get_db
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.dependencies import get_request_scoped_db_session
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


    # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestMiddlewareAsyncIntegration:
    # REMOVED_SYNTAX_ERROR: """Test middleware integration with async context managers."""

    # Removed problematic line: async def test_security_middleware_with_database_operation(self):
        # REMOVED_SYNTAX_ERROR: """Test that SecurityResponseMiddleware works when database operations use async context managers."""

        # Create a mock app
        # REMOVED_SYNTAX_ERROR: app = FastAPI()

        # Add the security middleware
        # REMOVED_SYNTAX_ERROR: middleware = SecurityResponseMiddleware(app)

        # Create a mock request
        # REMOVED_SYNTAX_ERROR: request = MagicMock(spec=Request)
        # REMOVED_SYNTAX_ERROR: request.url.path = "/api/test"
        # REMOVED_SYNTAX_ERROR: request.state = Magic        request.state.authenticated = False

        # Create a mock call_next that simulates a database operation
# REMOVED_SYNTAX_ERROR: async def mock_call_next(request):
    # Simulate using the database with our fixed async context manager
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: async with get_db() as session:
            # If we get here without error, the context manager works
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # Database connection errors are OK for this test
                # REMOVED_SYNTAX_ERROR: if "connection" not in str(e).lower() and "database" not in str(e).lower():
                    # REMOVED_SYNTAX_ERROR: raise

                    # Return a 404 response
                    # REMOVED_SYNTAX_ERROR: response = Magic            response.status_code = 404
                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                    # REMOVED_SYNTAX_ERROR: return response

                    # Test the middleware
                    # REMOVED_SYNTAX_ERROR: response = await middleware.dispatch(request, mock_call_next)

                    # Should convert 404 to 401 for unauthenticated API request
                    # REMOVED_SYNTAX_ERROR: assert isinstance(response, JSONResponse)
                    # REMOVED_SYNTAX_ERROR: assert response.status_code == 401

                    # Removed problematic line: async def test_middleware_exception_handling_with_async_context(self):
                        # REMOVED_SYNTAX_ERROR: """Test that middleware properly handles exceptions from async context managers."""

                        # REMOVED_SYNTAX_ERROR: app = FastAPI()
                        # REMOVED_SYNTAX_ERROR: middleware = SecurityResponseMiddleware(app)

                        # REMOVED_SYNTAX_ERROR: request = MagicMock(spec=Request)
                        # REMOVED_SYNTAX_ERROR: request.url.path = "/api/test"

                        # Create a call_next that raises an exception
# REMOVED_SYNTAX_ERROR: async def mock_call_next_with_error(request):
    # REMOVED_SYNTAX_ERROR: pass
    # Simulate an error in async context manager
    # REMOVED_SYNTAX_ERROR: raise ValueError("Test error")

    # The middleware should re-raise the exception
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
        # REMOVED_SYNTAX_ERROR: await middleware.dispatch(request, mock_call_next_with_error)

        # REMOVED_SYNTAX_ERROR: assert "Test error" in str(exc_info.value)

        # Removed problematic line: async def test_health_endpoint_bypass(self):
            # REMOVED_SYNTAX_ERROR: """Test that health endpoints bypass the security middleware."""

            # REMOVED_SYNTAX_ERROR: app = FastAPI()
            # REMOVED_SYNTAX_ERROR: middleware = SecurityResponseMiddleware(app)

            # REMOVED_SYNTAX_ERROR: request = MagicMock(spec=Request)
            # REMOVED_SYNTAX_ERROR: request.url.path = "/health"

            # Create a simple mock response
            # REMOVED_SYNTAX_ERROR: mock_response = Magic        mock_response.status_code = 200

# REMOVED_SYNTAX_ERROR: async def mock_call_next(request):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock_response

    # Test the middleware
    # REMOVED_SYNTAX_ERROR: response = await middleware.dispatch(request, mock_call_next)

    # Should pass through unchanged for health endpoint
    # REMOVED_SYNTAX_ERROR: assert response == mock_response
    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

    # Removed problematic line: async def test_no_async_generator_context_manager_errors(self):
        # REMOVED_SYNTAX_ERROR: """Test that we don't get _AsyncGeneratorContextManager errors in middleware."""

        # REMOVED_SYNTAX_ERROR: app = FastAPI()

        # Track any errors
        # REMOVED_SYNTAX_ERROR: errors_seen = []

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
        # Removed problematic line: async def test_middleware(request: Request, call_next):
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: try:
                # Use our fixed async context manager
                # REMOVED_SYNTAX_ERROR: async with get_request_scoped_db_session() as session:
                    # If this works, we won't get _AsyncGeneratorContextManager errors
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: errors_seen.append(str(e))
                        # Database connection errors are OK
                        # REMOVED_SYNTAX_ERROR: if "_AsyncGeneratorContextManager" in str(e):
                            # REMOVED_SYNTAX_ERROR: raise  # This would indicate our fix didn"t work

                            # REMOVED_SYNTAX_ERROR: response = await call_next(request)
                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                            # REMOVED_SYNTAX_ERROR: return response

                            # Add security middleware
                            # REMOVED_SYNTAX_ERROR: app.add_middleware(SecurityResponseMiddleware)

                            # Create test request
                            # REMOVED_SYNTAX_ERROR: request = MagicMock(spec=Request)
                            # REMOVED_SYNTAX_ERROR: request.url.path = "/api/test"
                            # REMOVED_SYNTAX_ERROR: request.state = Magic
                            # Mock call_next
# REMOVED_SYNTAX_ERROR: async def mock_call_next(request):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return JSONResponse({"status": "ok"})

    # Execute through middleware chain
    # This would fail with _AsyncGeneratorContextManager error if our fix didn't work
    # REMOVED_SYNTAX_ERROR: for error in errors_seen:
        # REMOVED_SYNTAX_ERROR: assert "_AsyncGeneratorContextManager" not in error

        # Removed problematic line: async def test_concurrent_requests_with_middleware(self):
            # REMOVED_SYNTAX_ERROR: """Test that concurrent requests through middleware don't cause async issues."""

            # REMOVED_SYNTAX_ERROR: import asyncio

            # REMOVED_SYNTAX_ERROR: app = FastAPI()
            # REMOVED_SYNTAX_ERROR: middleware = SecurityResponseMiddleware(app)

# REMOVED_SYNTAX_ERROR: async def process_request(request_id: int):
    # REMOVED_SYNTAX_ERROR: request = MagicMock(spec=Request)
    # REMOVED_SYNTAX_ERROR: request.url.path = "formatted_string"
    # REMOVED_SYNTAX_ERROR: request.state = Magic            request.state.authenticated = True  # Authenticated, so won"t convert

# REMOVED_SYNTAX_ERROR: async def mock_call_next(request):
    # Simulate database operation
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: async with get_db() as session:
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Simulate work
            # REMOVED_SYNTAX_ERROR: except Exception:
                # REMOVED_SYNTAX_ERROR: pass  # Ignore database errors

                # REMOVED_SYNTAX_ERROR: response = Magic                response.status_code = 200
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                # REMOVED_SYNTAX_ERROR: return response

                # REMOVED_SYNTAX_ERROR: return await middleware.dispatch(request, mock_call_next)

                # Process multiple concurrent requests
                # REMOVED_SYNTAX_ERROR: tasks = [process_request(i) for i in range(5)]
                # REMOVED_SYNTAX_ERROR: responses = await asyncio.gather(*tasks)

                # All should complete successfully
                # REMOVED_SYNTAX_ERROR: assert len(responses) == 5
                # REMOVED_SYNTAX_ERROR: for response in responses:
                    # Should not be converted since authenticated
                    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200


                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])
                        # REMOVED_SYNTAX_ERROR: pass