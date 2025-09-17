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

        '''
        Test to verify CORS middleware fix for AsyncGeneratorContextManager bug.

        This test ensures that the middleware correctly handles call_next as a simple
        callable without attempting to treat it as a context manager.
        '''

        import pytest
        from fastapi import Request, Response
        from fastapi.responses import JSONResponse
        from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from shared.isolated_environment import IsolatedEnvironment
        import asyncio


@pytest.mark.asyncio
    async def test_cors_middleware_direct_call_next():
"""Test that middleware directly calls call_next without context manager handling."""
        # Create mock app and middleware
app = Magic    middleware = CORSFixMiddleware(app, environment="development")

        # Create mock request with valid origin
request = MagicMock(spec=Request)
request.headers = {"origin": "http://localhost:3000"}
request.url.path = "/api/test"

        # Create mock response
expected_response = Response(content="test", status_code=200)

        # Create mock call_next that returns response
call_next = AsyncMock(return_value=expected_response)

        # Execute middleware
response = await middleware.dispatch(request, call_next)

        # Verify call_next was called directly with request
call_next.assert_called_once_with(request)

        # Verify response is correct
assert response.status_code == 200

        # Verify CORS headers were added
assert "Access-Control-Allow-Origin" in response.headers
assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
assert response.headers["Access-Control-Allow-Credentials"] == "true"


@pytest.mark.asyncio
    async def test_cors_middleware_error_handling():
"""Test that middleware properly handles errors from call_next."""
pass
            # Create mock app and middleware
app = Magic    middleware = CORSFixMiddleware(app, environment="development")

            # Create mock request with valid origin
request = MagicMock(spec=Request)
request.headers = {"origin": "http://localhost:3000"}
request.url.path = "/api/test"

            # Create mock call_next that raises an error
error_message = "Test error from downstream"
call_next = AsyncMock(side_effect=Exception(error_message))

            # Execute middleware - should handle error gracefully
response = await middleware.dispatch(request, call_next)

            # Verify call_next was called
call_next.assert_called_once_with(request)

            # Verify error response is created
assert response.status_code == 500
assert isinstance(response, JSONResponse)

            # Verify CORS headers are added even on error
assert "Access-Control-Allow-Origin" in response.headers
assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


@pytest.mark.asyncio
    async def test_cors_middleware_no_origin():
"""Test middleware behavior when no origin header is present."""
                # Create mock app and middleware
app = Magic    middleware = CORSFixMiddleware(app, environment="development")

                # Create request without origin header
request = MagicMock(spec=Request)
request.headers = {}
request.url.path = "/api/test"

                # Create mock response
expected_response = Response(content="test", status_code=200)
call_next = AsyncMock(return_value=expected_response)

                # Execute middleware
response = await middleware.dispatch(request, call_next)

                # Verify call_next was called
call_next.assert_called_once_with(request)

                # Verify response but no CORS headers added (no origin)
assert response.status_code == 200
assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
    async def test_cors_middleware_invalid_origin():
"""Test middleware behavior with invalid origin."""
pass
                    # Create mock app and middleware
app = Magic    middleware = CORSFixMiddleware(app, environment="development")

                    # Create request with invalid origin
request = MagicMock(spec=Request)
request.headers = {"origin": "http://malicious.com"}
request.url.path = "/api/test"

                    # Create mock response
expected_response = Response(content="test", status_code=200)
call_next = AsyncMock(return_value=expected_response)

                    # Execute middleware
response = await middleware.dispatch(request, call_next)

                    # Verify call_next was called
call_next.assert_called_once_with(request)

                    # Verify response but no CORS headers for invalid origin
assert response.status_code == 200
assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
    async def test_cors_middleware_preflight_request():
"""Test middleware handles OPTIONS preflight requests."""
                        # Create mock app and middleware
app = Magic    middleware = CORSFixMiddleware(app, environment="development")

                        # Create OPTIONS request with origin
request = MagicMock(spec=Request)
request.method = "OPTIONS"
request.headers = { )
"origin": "http://localhost:3000",
"access-control-request-method": "POST"
                        
request.url.path = "/api/test"

                        # Create mock response for OPTIONS
expected_response = Response(status_code=200)
call_next = AsyncMock(return_value=expected_response)

                        # Execute middleware
response = await middleware.dispatch(request, call_next)

                        # Verify call_next was called
call_next.assert_called_once_with(request)

                        # Verify CORS headers are present for preflight
assert "Access-Control-Allow-Origin" in response.headers
assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
assert "Access-Control-Allow-Methods" in response.headers
assert "Access-Control-Allow-Headers" in response.headers
pass
