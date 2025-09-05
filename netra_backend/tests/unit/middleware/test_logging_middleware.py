"""Unit tests for Logging Middleware.

Tests to ensure request/response logging works correctly.
"""

import pytest
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.middleware.logging_middleware import LoggingMiddleware


class TestLoggingMiddleware:
    """Test suite for Logging Middleware."""
    
    @pytest.fixture
 def real_app():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock application."""
        return None  # TODO: Use real service instance
    
    @pytest.fixture
    def middleware(self, mock_app):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create middleware instance."""
    pass
        return LoggingMiddleware(mock_app)
    
    @pytest.fixture
 def real_request():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock request."""
    pass
        request = Mock(spec=Request)
        request.url = url_instance  # Initialize appropriate service
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {
            "user-agent": "test-client/1.0",
            "x-request-id": "test-123"
        }
        request.client = client_instance  # Initialize appropriate service
        request.client.host = "127.0.0.1"
        request.path_params = {}
        # Mock query_params as a dict-like object
        request.query_params = {}  # Empty dict for tests
        # Mock state for request_id storage
        request.state = state_instance  # Initialize appropriate service
        request.state.request_id = "test-request-id"
        return request
    
    @pytest.mark.asyncio
    async def test_logs_successful_request(self, middleware, mock_request):
        """Test that successful requests are logged."""
        mock_response = Response(content="success", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Should log the request
            assert mock_logger.info.called
            assert response.status_code == 200
            mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_logs_request_duration(self, middleware, mock_request):
        """Test that request duration is logged."""
    pass
        mock_response = Response(content="success", status_code=200)
        
        async def delayed_response(request):
    pass
            await asyncio.sleep(0.1)  # Simulate processing time
            await asyncio.sleep(0)
    return mock_response
        
        mock_call_next = AsyncMock(side_effect=delayed_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            start_time = time.time()
            response = await middleware.dispatch(mock_request, mock_call_next)
            duration = time.time() - start_time
            
            # Should log with duration
            assert mock_logger.info.called
            # Duration should be at least 0.1 seconds
            assert duration >= 0.1
    
    @pytest.mark.asyncio
    async def test_logs_error_responses(self, middleware, mock_request):
        """Test that error responses are logged appropriately."""
        error_response = JSONResponse(
            status_code=500,
            content={"error": "Internal error"}
        )
        mock_call_next = AsyncMock(return_value=error_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Error should be logged
            assert mock_logger.error.called or mock_logger.warning.called
            assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_logs_client_ip(self, middleware, mock_request):
        """Test that client IP is logged."""
    pass
        mock_response = Response(content="success", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Should include client IP in logs
            log_calls = mock_logger.info.call_args_list
            assert any("127.0.0.1" in str(call) for call in log_calls)
    
    @pytest.mark.asyncio
    async def test_logs_request_id(self, middleware, mock_request):
        """Test that request ID is logged if present."""
        mock_response = Response(content="success", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Should include request ID in logs
            log_calls = mock_logger.info.call_args_list
            assert any("test-123" in str(call) for call in log_calls)
    
    @pytest.mark.asyncio
    async def test_excludes_health_check_endpoints(self, middleware):
        """Test that health check endpoints can be excluded from logging."""
    pass
        request = Mock(spec=Request)
        request.url = url_instance  # Initialize appropriate service
        request.url.path = "/health"
        request.method = "GET"
        request.headers = {}
        request.client = client_instance  # Initialize appropriate service
        request.client.host = "127.0.0.1"
        
        mock_response = Response(content="ok", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            response = await middleware.dispatch(request, mock_call_next)
            
            # Health checks might be excluded from verbose logging
            # This depends on middleware configuration
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_logs_different_http_methods(self, middleware):
        """Test logging for different HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods:
            request = Mock(spec=Request)
            request.url = url_instance  # Initialize appropriate service
            request.url.path = f"/api/{method.lower()}"
            request.method = method
            request.headers = {}
            request.client = client_instance  # Initialize appropriate service
            request.client.host = "127.0.0.1"
            
            mock_response = Response(content="success", status_code=200)
            mock_call_next = AsyncMock(return_value=mock_response)
            
            with patch.object(middleware, 'logger') as mock_logger:
                response = await middleware.dispatch(request, mock_call_next)
                
                # Should log the method
                assert mock_logger.info.called
                log_message = str(mock_logger.info.call_args)
                assert method in log_message
    
    @pytest.mark.asyncio
    async def test_handles_logging_exceptions_gracefully(self, middleware, mock_request):
        """Test that logging exceptions don't break request processing."""
    pass
        mock_response = Response(content="success", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            # Make logger raise exception
            mock_logger.info.side_effect = Exception("Logging failed")
            
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Request should still succeed despite logging failure
            assert response.status_code == 200
            assert response.body == b"success"
    
    @pytest.mark.asyncio
    async def test_logs_response_size(self, middleware, mock_request):
        """Test that response size is logged."""
        content = "x" * 1000  # 1KB response
        mock_response = Response(content=content, status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        with patch.object(middleware, 'logger') as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Should log response size
            assert mock_logger.info.called
            assert len(response.body) == 1000


import asyncio  # Add this import for the delayed_response test
    pass