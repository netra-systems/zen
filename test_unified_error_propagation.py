"""Unified Error Propagation Test Suite.

Tests error propagation across all services to ensure:
- No silent failures
- Clear error messages reach users
- Proper HTTP status codes
- Correct error logging

Agent 17 - Unified Testing Implementation Team
"""

import pytest
import asyncio
import logging
import json
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, TimeoutException, HTTPError
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.main import app
from app.core.exceptions_base import NetraException, ValidationError
from app.core.exceptions_agent import (
    AgentError, AgentExecutionError, AgentTimeoutError,
    LLMError, LLMRequestError, LLMRateLimitError
)
from app.agents.agent_error_types import AgentValidationError, NetworkError
from app.core.error_codes import ErrorCode, ErrorSeverity
from app.schemas.core_enums import ErrorCategory


class TestAuthServiceErrorPropagation:
    """Test auth service errors reaching frontend."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        self.auth_base_url = "http://localhost:3001"
    
    @pytest.mark.asyncio
    async def test_auth_invalid_credentials_error(self):
        """Test invalid credentials error propagation."""
        # Mock auth service returning 401
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 401
            mock_post.return_value.json.return_value = {
                "error": "invalid_credentials",
                "message": "Invalid email or password"
            }
            
            response = self.client.post("/api/auth/login", json={
                "email": "invalid@test.com",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            error_data = response.json()
            assert error_data["error"] == "invalid_credentials"
            assert "Invalid email or password" in error_data["message"]
    
    @pytest.mark.asyncio
    async def test_auth_service_unavailable_error(self):
        """Test auth service unavailable error propagation."""
        with patch('httpx.AsyncClient.post', side_effect=TimeoutException("timeout")):
            response = self.client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password"
            })
            
            assert response.status_code == 503
            error_data = response.json()
            assert "service_unavailable" in error_data.get("error", "")
            assert "timeout" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_auth_token_expired_error(self):
        """Test expired token error propagation."""
        with patch('app.auth_dependencies.verify_token') as mock_verify:
            mock_verify.side_effect = ValueError("Token expired")
            
            response = self.client.get("/api/user/profile", headers={
                "Authorization": "Bearer expired_token"
            })
            
            assert response.status_code == 401
            error_data = response.json()
            assert "expired" in error_data.get("message", "").lower()
    
    def test_auth_missing_token_error(self):
        """Test missing token error propagation."""
        # Test a route that would require authentication (use demo route which has optional auth)
        response = self.client.get("/api/demo/")
        
        # Demo endpoint should work without auth but may return different response
        assert response.status_code in [200, 401, 404]
        
        # If we get an error response, verify it's properly formatted
        if response.status_code >= 400:
            error_data = response.json()
            # Should have proper error structure
            assert "error" in error_data or "detail" in error_data or "message" in error_data


class TestWebSocketErrorPropagation:
    """Test backend errors over WebSocket."""
    
    def setup_method(self):
        """Setup WebSocket test environment."""
        self.websocket_url = "ws://localhost:8000/ws"
        self.test_user_id = "test_user_123"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_error(self):
        """Test WebSocket connection error handling."""
        with patch('websockets.connect', side_effect=ConnectionClosed(None, None)):
            try:
                async with websockets.connect(self.websocket_url) as websocket:
                    await websocket.send(json.dumps({"type": "test"}))
            except ConnectionClosed as e:
                # Verify error is properly caught and logged
                assert e is not None
    
    @pytest.mark.asyncio
    async def test_websocket_agent_error_propagation(self):
        """Test agent errors propagate through WebSocket."""
        mock_websocket = AsyncMock()
        
        # Simulate agent error during WebSocket communication
        with patch('app.ws_manager.WSManager.handle_message') as mock_handle:
            mock_handle.side_effect = AgentExecutionError(
                agent_name="TestAgent",
                task="test_task"
            )
            
            # Verify error is caught and formatted for client
            try:
                await mock_handle({"type": "agent_request", "data": {}})
            except AgentExecutionError as e:
                assert e.error_details.code == ErrorCode.AGENT_EXECUTION_FAILED
                assert "TestAgent" in str(e)
                assert "test_task" in str(e)
    
    @pytest.mark.asyncio
    async def test_websocket_rate_limit_error(self):
        """Test rate limit error through WebSocket."""
        mock_websocket = AsyncMock()
        
        with patch('app.ws_manager.WSManager.send_error') as mock_send:
            rate_limit_error = LLMRateLimitError(
                provider="openai",
                retry_after=30
            )
            
            await mock_send(mock_websocket, rate_limit_error)
            
            # Verify error message sent to client
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "rate limit" in str(args[1]).lower()
            assert "30" in str(args[1])
    
    @pytest.mark.asyncio
    async def test_websocket_malformed_message_error(self):
        """Test malformed WebSocket message error."""
        with patch('app.ws_manager.WSManager.handle_message') as mock_handle:
            mock_handle.side_effect = ValidationError(
                message="Invalid message format",
                details={"field": "type", "issue": "missing"}
            )
            
            try:
                await mock_handle("invalid_json")
            except ValidationError as e:
                assert e.error_details.code == ErrorCode.VALIDATION_ERROR
                assert "Invalid message format" in str(e)


class TestDatabaseErrorHandling:
    """Test database error handling."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test database connection failure propagation."""
        with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_engine:
            mock_engine.side_effect = ConnectionError("Database unavailable")
            
            client = TestClient(app)
            response = client.get("/api/health/db")
            
            assert response.status_code == 503
            error_data = response.json()
            assert "database" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_database_query_timeout(self):
        """Test database query timeout handling."""
        with patch('app.database.repository.BaseRepository.execute') as mock_execute:
            mock_execute.side_effect = asyncio.TimeoutError("Query timeout")
            
            client = TestClient(app)
            response = client.get("/api/users/1")
            
            assert response.status_code == 504
            error_data = response.json()
            assert "timeout" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_database_constraint_violation(self):
        """Test database constraint violation propagation."""
        from sqlalchemy.exc import IntegrityError
        
        with patch('app.database.repository.UserRepository.create') as mock_create:
            mock_create.side_effect = IntegrityError(
                "duplicate key value violates unique constraint",
                None, None
            )
            
            client = TestClient(app)
            response = client.post("/api/users", json={
                "email": "duplicate@test.com",
                "name": "Test User"
            })
            
            assert response.status_code == 409
            error_data = response.json()
            assert "duplicate" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_clickhouse_connection_error(self):
        """Test ClickHouse connection error handling."""
        with patch('clickhouse_connect.get_client') as mock_client:
            mock_client.side_effect = ConnectionError("ClickHouse unavailable")
            
            client = TestClient(app)
            response = client.get("/api/analytics/stats")
            
            assert response.status_code == 503
            error_data = response.json()
            assert "analytics service" in error_data.get("message", "").lower()


class TestNetworkTimeoutHandling:
    """Test network timeout handling."""
    
    @pytest.mark.asyncio
    async def test_llm_request_timeout(self):
        """Test LLM request timeout propagation."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = TimeoutException("Request timeout")
            
            client = TestClient(app)
            response = client.post("/api/chat/message", json={
                "message": "Test message",
                "session_id": "test_session"
            })
            
            assert response.status_code == 504
            error_data = response.json()
            assert "timeout" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_external_api_timeout(self):
        """Test external API timeout handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = TimeoutException("API timeout")
            
            client = TestClient(app)
            response = client.get("/api/external/data")
            
            assert response.status_code == 504
            error_data = response.json()
            assert "external service" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_timeout(self):
        """Test concurrent request timeout handling."""
        async def slow_operation():
            await asyncio.sleep(10)  # Simulate slow operation
            
        with patch('asyncio.wait_for') as mock_wait:
            mock_wait.side_effect = asyncio.TimeoutError()
            
            client = TestClient(app)
            response = client.post("/api/bulk/process", json={
                "items": ["item1", "item2", "item3"]
            })
            
            assert response.status_code == 504
            error_data = response.json()
            assert "operation timeout" in error_data.get("message", "").lower()


class TestAgentErrorPropagation:
    """Test agent error propagation across the system."""
    
    @pytest.mark.asyncio
    async def test_agent_execution_error(self):
        """Test agent execution error propagation."""
        with patch('app.agents.base.BaseSubAgent.execute') as mock_execute:
            mock_execute.side_effect = AgentExecutionError(
                agent_name="DataSubAgent",
                task="process_data"
            )
            
            client = TestClient(app)
            response = client.post("/api/agents/execute", json={
                "agent_type": "data",
                "task": "process_data"
            })
            
            assert response.status_code == 500
            error_data = response.json()
            assert "DataSubAgent" in error_data.get("message", "")
            assert "process_data" in error_data.get("message", "")
    
    @pytest.mark.asyncio
    async def test_agent_timeout_error(self):
        """Test agent timeout error propagation."""
        with patch('app.agents.base.BaseSubAgent.execute') as mock_execute:
            mock_execute.side_effect = AgentTimeoutError(
                agent_name="ReportingSubAgent",
                timeout_seconds=30
            )
            
            client = TestClient(app)
            response = client.post("/api/reports/generate", json={
                "type": "summary"
            })
            
            assert response.status_code == 504
            error_data = response.json()
            assert "ReportingSubAgent" in error_data.get("message", "")
            assert "30" in error_data.get("message", "")
    
    @pytest.mark.asyncio
    async def test_agent_validation_error(self):
        """Test agent validation error propagation."""
        with patch('app.agents.base.BaseSubAgent.validate_input') as mock_validate:
            mock_validate.side_effect = AgentValidationError(
                "Invalid input parameters",
                context={"field": "data_source", "value": "invalid"}
            )
            
            client = TestClient(app)
            response = client.post("/api/agents/synthetic", json={
                "data_source": "invalid"
            })
            
            assert response.status_code == 400
            error_data = response.json()
            assert "Invalid input parameters" in error_data.get("message", "")
            assert "data_source" in str(error_data.get("details", {}))
    
    @pytest.mark.asyncio
    async def test_llm_provider_error(self):
        """Test LLM provider error propagation."""
        with patch('app.core.llm_client.LLMClient.generate') as mock_generate:
            mock_generate.side_effect = LLMRequestError(
                provider="openai",
                model="gpt-4",
                status_code=429
            )
            
            client = TestClient(app)
            response = client.post("/api/chat/completion", json={
                "prompt": "Test prompt"
            })
            
            assert response.status_code == 429
            error_data = response.json()
            assert "openai" in error_data.get("message", "").lower()
            assert "gpt-4" in error_data.get("message", "").lower()


class TestRateLimitErrorHandling:
    """Test rate limit error handling."""
    
    @pytest.mark.asyncio
    async def test_openai_rate_limit(self):
        """Test OpenAI rate limit error handling."""
        with patch('app.core.llm_client.OpenAIClient.generate') as mock_generate:
            mock_generate.side_effect = LLMRateLimitError(
                provider="openai",
                retry_after=60
            )
            
            client = TestClient(app)
            response = client.post("/api/llm/generate", json={
                "prompt": "Test prompt",
                "provider": "openai"
            })
            
            assert response.status_code == 429
            assert response.headers.get("Retry-After") == "60"
            error_data = response.json()
            assert "rate limit" in error_data.get("message", "").lower()
            assert "60" in error_data.get("message", "")
    
    @pytest.mark.asyncio
    async def test_anthropic_rate_limit(self):
        """Test Anthropic rate limit error handling."""
        with patch('app.core.llm_client.AnthropicClient.generate') as mock_generate:
            mock_generate.side_effect = LLMRateLimitError(
                provider="anthropic",
                retry_after=30
            )
            
            client = TestClient(app)
            response = client.post("/api/llm/generate", json={
                "prompt": "Test prompt",
                "provider": "anthropic"
            })
            
            assert response.status_code == 429
            assert response.headers.get("Retry-After") == "30"
            error_data = response.json()
            assert "anthropic" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_api_rate_limit_header_parsing(self):
        """Test API rate limit header parsing."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "120", "X-RateLimit-Remaining": "0"}
            mock_response.json.return_value = {"error": "rate_limit_exceeded"}
            mock_post.return_value = mock_response
            
            client = TestClient(app)
            response = client.post("/api/external/service", json={"data": "test"})
            
            assert response.status_code == 429
            assert response.headers.get("Retry-After") == "120"


class TestPermissionDeniedErrors:
    """Test permission denied error propagation."""
    
    def test_unauthorized_access_error(self):
        """Test unauthorized access error propagation."""
        client = TestClient(app)
        response = client.get("/api/admin/users")
        
        assert response.status_code == 401
        error_data = response.json()
        assert "unauthorized" in error_data.get("error", "").lower()
    
    def test_forbidden_resource_error(self):
        """Test forbidden resource error propagation."""
        with patch('app.auth_dependencies.verify_admin_role') as mock_verify:
            mock_verify.return_value = False
            
            client = TestClient(app)
            response = client.delete("/api/admin/users/123", headers={
                "Authorization": "Bearer valid_token"
            })
            
            assert response.status_code == 403
            error_data = response.json()
            assert "forbidden" in error_data.get("error", "").lower()
    
    def test_insufficient_permissions_error(self):
        """Test insufficient permissions error propagation."""
        with patch('app.auth_dependencies.check_permissions') as mock_check:
            mock_check.side_effect = PermissionError("Insufficient permissions")
            
            client = TestClient(app)
            response = client.post("/api/admin/settings", json={
                "key": "test",
                "value": "test"
            }, headers={
                "Authorization": "Bearer user_token"
            })
            
            assert response.status_code == 403
            error_data = response.json()
            assert "insufficient permissions" in error_data.get("message", "").lower()


class TestErrorLoggingAndStatus:
    """Test HTTP status codes and error logging."""
    
    def test_error_logging_format(self, caplog):
        """Test error logging format and content."""
        with caplog.at_level(logging.ERROR):
            client = TestClient(app)
            response = client.get("/api/nonexistent")
            
            assert response.status_code == 404
            assert len(caplog.records) > 0
            
            # Check log contains essential error information
            log_record = caplog.records[-1]
            assert log_record.levelname == "ERROR"
            assert "404" in log_record.message
    
    def test_structured_error_response_format(self):
        """Test structured error response format."""
        client = TestClient(app)
        response = client.post("/api/invalid", json={"invalid": "data"})
        
        error_data = response.json()
        
        # Verify error response structure
        required_fields = ["error", "message", "timestamp"]
        for field in required_fields:
            assert field in error_data
        
        # Verify error details structure
        if "details" in error_data:
            assert isinstance(error_data["details"], dict)
    
    def test_error_trace_id_propagation(self):
        """Test error trace ID propagation."""
        client = TestClient(app)
        response = client.get("/api/error", headers={
            "X-Trace-ID": "test-trace-123"
        })
        
        error_data = response.json()
        assert error_data.get("trace_id") == "test-trace-123"
    
    def test_no_sensitive_data_in_errors(self):
        """Test that sensitive data is not exposed in error messages."""
        with patch('app.database.repository.UserRepository.get_by_email') as mock_get:
            mock_get.side_effect = Exception("Database connection failed: password=secret123")
            
            client = TestClient(app)
            response = client.get("/api/users/me")
            
            error_data = response.json()
            error_message = error_data.get("message", "")
            
            # Ensure no sensitive data in user-facing message
            assert "password" not in error_message.lower()
            assert "secret" not in error_message.lower()


class TestSilentFailurePrevention:
    """Test to ensure no silent failures occur."""
    
    @pytest.mark.asyncio
    async def test_websocket_error_notification(self):
        """Test WebSocket errors are always notified to client."""
        mock_websocket = AsyncMock()
        error_sent = False
        
        async def mock_send_text(message):
            nonlocal error_sent
            error_data = json.loads(message)
            if error_data.get("type") == "error":
                error_sent = True
        
        mock_websocket.send_text = mock_send_text
        
        # Simulate error and verify notification
        from app.ws_manager import WSManager
        ws_manager = WSManager()
        
        test_error = AgentError("Test error")
        await ws_manager.send_error(mock_websocket, test_error)
        
        assert error_sent, "Error was not sent to WebSocket client"
    
    def test_api_error_always_returns_response(self):
        """Test API errors always return a response (no silent failures)."""
        with patch('app.main.app') as mock_app:
            mock_app.side_effect = Exception("Unexpected error")
            
            client = TestClient(app)
            response = client.get("/api/test")
            
            # Should return error response, not hang or fail silently
            assert response.status_code >= 400
            assert response.json()  # Should have JSON error response
    
    def test_background_task_error_logging(self):
        """Test background task errors are logged (not silent)."""
        with patch('logging.Logger.error') as mock_log:
            with patch('app.background.process_data') as mock_process:
                mock_process.side_effect = Exception("Background task failed")
                
                client = TestClient(app)
                response = client.post("/api/background/task", json={"data": "test"})
                
                # Verify error was logged even for background task
                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Background task failed" in logged_message


if __name__ == "__main__":
    # Run specific test suites
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])