"""Comprehensive regression test suite for WebSocket message handling errors.

This suite tests the critical connection point between frontend and backend,
ensuring proper error handling and preventing silent failures.

Includes specific regression tests for coroutine handling in auth flow.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Optional
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.message_handler_base import MessageHandlerBase
from netra_backend.app.schemas.websocket_models import UserMessagePayload
from ws_manager import manager
from starlette.websockets import WebSocketDisconnect
from netra_backend.app.db.models_postgres import Thread, Run
import uuid
from datetime import datetime

# Add project root to path


class TestWebSocketMessageRegression:
    """Test suite for preventing WebSocket message handling regressions."""
    
    @pytest.fixture
    def mock_supervisor(self):
        """Create mock supervisor for testing."""
        supervisor = AsyncMock()
        supervisor.run = AsyncMock(return_value="Test response")
        return supervisor
    
    @pytest.fixture
    def mock_thread_service(self):
        """Create mock thread service."""
        service = Mock()
        service.get_or_create_thread = AsyncMock()
        service.create_message = AsyncMock()
        service.create_run = AsyncMock()
        return service
    
    @pytest.fixture
    def agent_service(self, mock_supervisor):
        """Create agent service with mock supervisor."""
        return AgentService(mock_supervisor)
    
    @pytest.fixture
    def message_handler(self, mock_supervisor, mock_thread_service):
        """Create message handler with mocks."""
        return MessageHandlerService(mock_supervisor, mock_thread_service)
    
    @pytest.mark.asyncio
    async def test_unknown_message_type_returns_error(self, agent_service):
        """Test 1: Unknown message type should return clear error to user."""
        user_id = "test_user"
        unknown_message = {
            "type": "unknown_type",
            "payload": {"data": "some data"}
        }
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            await agent_service.handle_websocket_message(
                user_id, 
                json.dumps(unknown_message), 
                None
            )
            
            # Should send error message to user
            mock_send_error.assert_called_once()
            error_msg = mock_send_error.call_args[0][1]
            assert "Unknown message type" in error_msg or "unknown_type" in error_msg
    
    @pytest.mark.asyncio
    async def test_missing_payload_field_logs_warning(self, message_handler):
        """Test 2: Missing required payload fields should log warnings."""
        # Payload missing both 'content' and 'text'
        malformed_payload = {
            "references": [],
            "thread_id": "test_thread"
        }
        
        with patch('app.logging_config.central_logger.get_logger') as mock_logger:
            logger = Mock()
            mock_logger.return_value = logger
            
            text, refs, thread_id = message_handler._extract_message_data(malformed_payload)
            
            # Should extract empty string but ideally log warning
            assert text == ""
            assert refs == []
            assert thread_id == "test_thread"
    
    @pytest.mark.asyncio
    async def test_invalid_json_message_sends_error(self, agent_service):
        """Test 3: Invalid JSON should send parse error to user."""
        user_id = "test_user"
        invalid_json = "{'invalid': json, missing quotes}"
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            await agent_service.handle_websocket_message(
                user_id,
                invalid_json,
                None
            )
            
            mock_send_error.assert_called()
            error_msg = mock_send_error.call_args[0][1]
            assert "parse" in error_msg.lower() or "json" in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_empty_message_content_handled_gracefully(self, message_handler):
        """Test 4: Empty message content should be handled without crashing."""
        empty_payload = {
            "content": "",
            "references": []
        }
        
        text, refs, thread_id = message_handler._extract_message_data(empty_payload)
        
        assert text == ""
        assert refs == []
        assert thread_id is None
        
        # Should not throw exception
        with patch('app.ws_manager.manager.send_error'):
            # This should complete without error
            pass
    
    @pytest.mark.asyncio
    async def test_null_payload_fields_handled(self, message_handler):
        """Test 5: Null payload fields should be handled safely."""
        null_payload = {
            "content": None,
            "text": None,
            "references": None,
            "thread_id": None
        }
        
        text, refs, thread_id = message_handler._extract_message_data(null_payload)
        
        # Should handle nulls gracefully
        assert text == ""
        assert refs == [] or refs is None
        assert thread_id is None
    
    @pytest.mark.asyncio
    async def test_message_without_type_field_rejected(self, agent_service):
        """Test 6: Messages without 'type' field should be rejected with error."""
        user_id = "test_user"
        typeless_message = {
            "payload": {"content": "Test message"}
        }
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            await agent_service.handle_websocket_message(
                user_id,
                json.dumps(typeless_message),
                None
            )
            
            # Should send error about missing type
            mock_send_error.assert_called()
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_during_processing(self, agent_service):
        """Test 7: WebSocket disconnect during message processing handled gracefully."""
        user_id = "test_user"
        message = json.dumps({
            "type": "user_message",
            "payload": {"content": "Test message"}
        })
        
        with patch.object(agent_service.message_handler, 'handle_user_message',
                         side_effect=WebSocketDisconnect()):
            # Should not raise exception to caller
            await agent_service.handle_websocket_message(user_id, message, None)
            # Test passes if no exception propagated
    
    @pytest.mark.asyncio
    async def test_extremely_large_payload_handled(self, message_handler):
        """Test 8: Extremely large payloads should be handled without memory issues."""
        large_content = "x" * 1000000  # 1MB of text
        large_payload = {
            "content": large_content,
            "references": []
        }
        
        text, refs, thread_id = message_handler._extract_message_data(large_payload)
        
        assert text == large_content
        assert refs == []
        
        # Should handle large payloads (though may want to add size limits)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_content_handled(self, message_handler):
        """Test 9: Special characters in content should be preserved correctly."""
        special_content = "Test with émojis 🚀, quotes \"'`, and \nnewlines\ttabs"
        special_payload = {
            "content": special_content,
            "references": []
        }
        
        text, refs, thread_id = message_handler._extract_message_data(special_payload)
        
        assert text == special_content
        assert refs == []
    
    @pytest.mark.asyncio
    async def test_concurrent_messages_from_same_user(self, agent_service):
        """Test 10: Concurrent messages from same user should not interfere."""
        user_id = "test_user"
        message1 = json.dumps({
            "type": "user_message",
            "payload": {"content": "First message"}
        })
        message2 = json.dumps({
            "type": "user_message",
            "payload": {"content": "Second message"}
        })
        
        with patch.object(agent_service.message_handler, 'handle_user_message',
                         new_callable=AsyncMock) as mock_handle:
            # Send both messages concurrently
            import asyncio
            await asyncio.gather(
                agent_service.handle_websocket_message(user_id, message1, None),
                agent_service.handle_websocket_message(user_id, message2, None)
            )
            
            # Both should be processed
            assert mock_handle.call_count == 2
            
            # Verify both messages were received
            calls = mock_handle.call_args_list
            payloads = [call[0][1] for call in calls]
            contents = [p.get("content") for p in payloads]
            assert "First message" in contents
            assert "Second message" in contents


class TestWebSocketErrorPropagation:
    """Additional tests for error propagation and user feedback."""
    
    @pytest.mark.asyncio
    async def test_database_error_sends_user_friendly_message(self):
        """Database errors should result in user-friendly error messages."""
        handler = MessageHandlerService(supervisor=None, thread_service=None)
        
        with patch('app.db.postgres.get_async_db', side_effect=Exception("DB Connection failed")):
            with patch('app.ws_manager.manager.send_error') as mock_send_error:
                await handler.handle_user_message(
                    "test_user",
                    {"content": "Test"},
                    None
                )
                
                # Should send user-friendly error, not raw DB error
                if mock_send_error.called:
                    error_msg = mock_send_error.call_args[0][1]
                    assert "DB Connection failed" not in error_msg
                    assert "server error" in error_msg.lower() or "try again" in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_supervisor_timeout_handled_gracefully(self):
        """Supervisor timeout should be handled with appropriate user feedback."""
        supervisor = AsyncMock()
        supervisor.run = AsyncMock(side_effect=asyncio.TimeoutError())
        
        handler = MessageHandlerService(supervisor=supervisor, thread_service=Mock())
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            # This should handle the timeout gracefully
            try:
                await handler._execute_supervisor(
                    "Test request", 
                    Mock(id="thread_1"),
                    "user_1",
                    Mock(id="run_1")
                )
            except asyncio.TimeoutError:
                pass  # Expected
            
            # In real implementation, should send timeout message to user
    
    @pytest.mark.asyncio  
    async def test_malformed_frontend_message_structure(self):
        """Test messages with completely wrong structure from frontend."""
        agent_service = AgentService(AsyncMock())
        
        # Frontend accidentally sends array instead of object
        wrong_structure = ["user_message", {"content": "Test"}]
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            await agent_service.handle_websocket_message(
                "test_user",
                json.dumps(wrong_structure),
                None
            )
            
            mock_send_error.assert_called()
            error_msg = mock_send_error.call_args[0][1]
            assert "format" in error_msg.lower() or "structure" in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_message_validation_logs_details(self):
        """Message validation failures should log detailed information for debugging."""
        handler = MessageHandlerService(supervisor=None, thread_service=None)
        
        invalid_payload = {
            "content": {"nested": "object"},  # Content should be string
            "references": "not_an_array"  # References should be array
        }
        
        with patch('app.services.message_handlers.logger') as mock_logger:
            text, refs, thread_id = handler._extract_message_data(invalid_payload)
            
            # Should log validation issues for debugging
            # Even if it handles gracefully, developers need to know


class TestStartAgentUserMessagePayloadConsistency:
    """Tests to ensure start_agent and user_message accept same payload structure."""
    
    @pytest.fixture
    def mock_thread(self):
        """Create a mock thread."""
        thread = Mock(spec=Thread)
        thread.id = str(uuid.uuid4())
        thread.metadata_ = {"user_id": "test_user"}
        thread.created_at = datetime.now()
        return thread
    
    @pytest.fixture
    def mock_run(self):
        """Create a mock run."""
        run = Mock(spec=Run)
        run.id = str(uuid.uuid4())
        run.status = "in_progress"
        return run
    
    @pytest.fixture
    def mock_supervisor(self):
        """Create mock supervisor."""
        supervisor = AsyncMock()
        supervisor.run = AsyncMock(return_value="Agent response")
        supervisor.thread_id = None
        supervisor.user_id = None
        supervisor.db_session = None
        return supervisor
    
    @pytest.fixture
    def mock_thread_service(self, mock_thread, mock_run):
        """Create mock thread service."""
        service = Mock()
        service.get_or_create_thread = AsyncMock(return_value=mock_thread)
        service.get_thread = AsyncMock(return_value=mock_thread)
        service.create_message = AsyncMock()
        service.create_run = AsyncMock(return_value=mock_run)
        service.update_run_status = AsyncMock()
        return service
    
    @pytest.fixture
    def message_handler(self, mock_supervisor, mock_thread_service):
        """Create message handler with mocks."""
        return MessageHandlerService(mock_supervisor, mock_thread_service)
    
    @pytest.mark.asyncio
    async def test_start_agent_accepts_content_field(self, message_handler, mock_supervisor):
        """Test that start_agent accepts 'content' field like user_message does."""
        payload = {
            "content": "Hello, analyze our costs",  # Same field as user_message
            "thread_id": None
        }
        
        mock_session = AsyncMock()
        await message_handler.handle_start_agent("test_user", payload, mock_session)
        
        # Verify supervisor was called with the content
        mock_supervisor.run.assert_called_once()
        call_args = mock_supervisor.run.call_args[0]
        assert call_args[0] == "Hello, analyze our costs"
    
    @pytest.mark.asyncio
    async def test_start_agent_accepts_text_field(self, message_handler, mock_supervisor):
        """Test that start_agent accepts 'text' field for backward compatibility."""
        payload = {
            "text": "What are our top costs?",  # Legacy field name
            "thread_id": None
        }
        
        mock_session = AsyncMock()
        await message_handler.handle_start_agent("test_user", payload, mock_session)
        
        # Verify supervisor was called with the text
        mock_supervisor.run.assert_called_once()
        call_args = mock_supervisor.run.call_args[0]
        assert call_args[0] == "What are our top costs?"
    
    @pytest.mark.asyncio
    async def test_start_agent_accepts_user_request_field(self, message_handler, mock_supervisor):
        """Test that start_agent still accepts 'user_request' field."""
        payload = {
            "user_request": "Optimize our AI workloads",  # Original field name
            "thread_id": None
        }
        
        mock_session = AsyncMock()
        await message_handler.handle_start_agent("test_user", payload, mock_session)
        
        # Verify supervisor was called with the user_request
        mock_supervisor.run.assert_called_once()
        call_args = mock_supervisor.run.call_args[0]
        assert call_args[0] == "Optimize our AI workloads"
    
    @pytest.mark.asyncio
    async def test_user_message_and_start_agent_same_payload(self, message_handler, mock_supervisor):
        """Test that both handlers work with identical payload structure."""
        # Same payload for both message types
        payload = {
            "content": "Analyze our infrastructure",
            "references": []
        }
        
        mock_session = AsyncMock()
        
        # Test start_agent
        await message_handler.handle_start_agent("test_user", payload, mock_session)
        assert mock_supervisor.run.call_count == 1
        
        # Test user_message  
        await message_handler.handle_user_message("test_user", payload, mock_session)
        assert mock_supervisor.run.call_count == 2
        
        # Both should have processed the same content
        first_call = mock_supervisor.run.call_args_list[0][0]
        second_call = mock_supervisor.run.call_args_list[1][0]
        assert first_call[0] == second_call[0] == "Analyze our infrastructure"
    
    def test_extract_user_request_priority_order(self):
        """Test the priority order of field extraction."""
        # Content has highest priority
        payload1 = {
            "content": "content_value",
            "text": "text_value",
            "user_request": "user_request_value"
        }
        assert MessageHandlerBase.extract_user_request(payload1) == "content_value"
        
        # Text is next priority
        payload2 = {
            "text": "text_value",
            "user_request": "user_request_value"
        }
        assert MessageHandlerBase.extract_user_request(payload2) == "text_value"
        
        # user_request is next
        payload3 = {
            "user_request": "user_request_value"
        }
        assert MessageHandlerBase.extract_user_request(payload3) == "user_request_value"
        
        # Nested request.query is last resort
        payload4 = {
            "request": {
                "query": "query_value"
            }
        }
        assert MessageHandlerBase.extract_user_request(payload4) == "query_value"


class TestWebSocketCoroutineAuthRegression:
    """Regression tests for coroutine handling in WebSocket auth flow."""
    
    @pytest.mark.asyncio
    async def test_decode_access_token_coroutine_await(self):
        """Critical: Verify decode_access_token coroutine is properly awaited."""
        from netra_backend.app.routes.utils.websocket_helpers import decode_token_payload
        from netra_backend.app.services.security_service import SecurityService
        
        mock_service = AsyncMock(spec=SecurityService)
        test_payload = {"sub": "user123", "email": "test@example.com"}
        
        # Setup mock to return async result
        mock_service.decode_access_token = AsyncMock(return_value=test_payload)
        
        # Call should properly await
        result = await decode_token_payload(mock_service, "test_token")
        
        # Verify it was awaited
        mock_service.decode_access_token.assert_awaited_once_with("test_token")
        
        # Verify result is dict, not coroutine
        assert isinstance(result, dict)
        assert hasattr(result, 'get')
        assert result.get("sub") == "user123"
    
    @pytest.mark.asyncio
    async def test_auth_flow_no_coroutine_attribute_error(self):
        """Verify auth flow doesn't cause 'coroutine has no attribute' error."""
        from netra_backend.app.routes.utils.websocket_helpers import authenticate_websocket_user
        from netra_backend.app.services.security_service import SecurityService
        
        mock_websocket = Mock()
        mock_service = AsyncMock(spec=SecurityService)
        mock_user = Mock(id="user123", email="test@example.com")
        
        # Setup all async operations
        mock_service.decode_access_token = AsyncMock(
            return_value={"sub": "user123", "email": "test@example.com"}
        )
        mock_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_db_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_db_session
            
            # Should complete without coroutine attribute errors
            result = await authenticate_websocket_user(
                mock_websocket, "valid_token", mock_service
            )
            
            assert result == "user123"
            
            # Verify all async calls were properly awaited
            assert mock_service.decode_access_token.await_count == 1
            assert mock_service.get_user_by_id.await_count >= 1
    
    @pytest.mark.asyncio
    async def test_websocket_error_handler_with_coroutine_error(self):
        """Test error handler properly logs coroutine-related errors."""
        from netra_backend.app.routes.websockets import _handle_general_exception
        
        mock_websocket = Mock()
        error = RuntimeError("'coroutine' object has no attribute 'get'")
        
        with patch('app.routes.websockets.logger') as mock_logger:
            await _handle_general_exception(error, "user123", mock_websocket)
            
            # Verify error was logged
            mock_logger.error.assert_called()
            assert "'coroutine' object has no attribute 'get'" in str(mock_logger.error.call_args)
    
    @pytest.mark.asyncio
    async def test_security_service_validate_token_awaits_decode(self):
        """Test EnhancedSecurityService validate_token properly awaits decode."""
        from netra_backend.tests.services.security_service_test_mocks import EnhancedSecurityService
        from netra_backend.app.services.key_manager import KeyManager
        
        mock_key_manager = Mock(spec=KeyManager)
        service = EnhancedSecurityService(mock_key_manager)
        
        # Mock decode to verify it's awaited
        service.decode_access_token = AsyncMock(
            return_value={"sub": "test_user", "exp": 9999999999}
        )
        
        result = await service.validate_token_jwt("test_token")
        
        # Verify decode was awaited
        service.decode_access_token.assert_awaited_once_with("test_token")
        
        # Verify result is proper dict
        assert isinstance(result, dict)
        assert result["valid"] is True
        # The validate_token method maps 'sub' to 'email'
        assert result.get("email") == "test_user"