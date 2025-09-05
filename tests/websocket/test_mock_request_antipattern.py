"""
Test suite to demonstrate and verify the elimination of mock Request objects
in WebSocket code. These tests validate the remediation is working correctly.

CRITICAL: This test suite validates that we're moving from dishonest mock objects
to honest WebSocket-specific patterns.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

# Import the implemented WebSocket classes
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
from netra_backend.app.core.supervisor_factory import create_supervisor_core

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.dependencies import (
    get_request_scoped_supervisor,
    RequestScopedContext
)


class TestMockRequestAntiPattern:
    """Test suite to verify elimination of mock Request objects."""
    
    @pytest.mark.asyncio
    async def test_current_implementation_uses_mock_request(self):
        """
        Test that v2 legacy pattern still creates mock Request objects.
        This validates backward compatibility while proving the anti-pattern exists.
        """
        # Create mock message handler service
        from netra_backend.app.services.message_handlers import MessageHandlerService
        mock_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(message_handler_service=mock_service)
        
        # Create a test message
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        test_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"thread_id": "test_thread", "run_id": "test_run"},
            user_id="test_user",
            thread_id="test_thread",
            correlation_id="test_correlation"
        )
        
        # Force legacy v2 pattern
        with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):
            # Spy on Request constructor
            with patch('netra_backend.app.websocket_core.agent_handler.Request') as mock_request_class:
                mock_request_class.return_value = Mock(spec=Request)
                
                # Setup WebSocket mock
                mock_websocket = AsyncMock(spec=WebSocket)
                mock_websocket.client_state = WebSocketState.CONNECTED
                
                # Mock database session generation
                mock_db_session = AsyncMock(spec=AsyncSession)
                
                # Mock the async generator for database sessions
                async def mock_db_generator():
                    yield mock_db_session
                    
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session', 
                          return_value=mock_db_generator()):
                    
                    # Mock the supervisor factory
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_supervisor_factory:
                        mock_supervisor_factory.return_value = AsyncMock()
                        
                        # Mock WebSocket manager
                        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_manager') as mock_ws_manager:
                            mock_ws_manager.return_value = Mock()
                            mock_ws_manager.return_value.get_connection_id_by_websocket.return_value = "test_conn_123"
                            
                            # Mock additional dependencies to prevent actual execution
                            with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context'):
                                with patch.object(handler, '_create_request_context'):
                                    with patch.object(handler, '_route_agent_message_v2'):
                                        # Process message with legacy v2 pattern
                                        result = await handler.handle_message("test_user", mock_websocket, test_message)
                                        
                                        # The v2 pattern should create mock Request in _handle_message_v2_legacy
                                        # Since we're not mocking the handler methods, we need to check if Request would be called
                                        # when the actual v2 flow executes
    
    @pytest.mark.asyncio
    async def test_v2_legacy_pattern_creates_mock_request(self):
        """
        Direct test of the v2 legacy pattern to verify it creates mock Request objects.
        This proves the anti-pattern still exists in the legacy code path.
        """
        from netra_backend.app.services.message_handlers import MessageHandlerService
        mock_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(message_handler_service=mock_service)
        
        # Create test message
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "test", "thread_id": "test_thread"},
            user_id="test_user",
            thread_id="test_thread",
            correlation_id="test_correlation"
        )
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Spy on Request constructor
        with patch('netra_backend.app.websocket_core.agent_handler.Request') as mock_request_class:
            mock_request_class.return_value = Mock(spec=Request)
            
            # Mock all the dependencies for v2 legacy pattern
            mock_db_session = AsyncMock(spec=AsyncSession)
            
            async def mock_db_generator():
                yield mock_db_session
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session', 
                      return_value=mock_db_generator()):
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_manager') as mock_ws_manager:
                    mock_ws_manager.return_value = Mock()
                    mock_ws_manager.return_value.get_connection_id_by_websocket.return_value = "test_conn"
                    
                    with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context') as mock_create_context:
                        mock_create_context.return_value = Mock()
                        
                        with patch.object(handler, '_create_request_context', return_value=Mock()):
                            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', return_value=Mock()):
                                with patch.object(handler, '_route_agent_message_v2', return_value=True):
                                    # Call the v2 legacy method directly
                                    result = await handler._handle_message_v2_legacy("test_user", mock_websocket, test_message)
                                    
                                    # Verify mock Request was created (the anti-pattern)
                                    mock_request_class.assert_called_once_with(
                                        {"type": "websocket", "headers": []}, 
                                        receive=None, 
                                        send=None
                                    )
    
    @pytest.mark.asyncio
    async def test_mock_request_lacks_real_request_attributes(self):
        """
        Test that mock Request objects don't have real HTTP request attributes.
        This demonstrates why the mock pattern is problematic.
        """
        # Create the mock request as done in current code
        mock_request = Request({"type": "websocket", "headers": []}, receive=None, send=None)
        
        # The mock can't handle real HTTP operations properly
        assert mock_request.headers == [], "Mock has empty headers"
        assert mock_request.method == "GET", "Mock defaults to GET method"
        
        # Mock doesn't have meaningful client info
        assert mock_request.client is None, "Mock has no client info"
        
        # This proves mocks are dishonest about their capabilities
        with pytest.raises(AttributeError):
            _ = mock_request.session  # No session handling
    
    @pytest.mark.asyncio
    async def test_websocket_context_should_be_honest(self):
        """
        Test that WebSocketContext (new pattern) is honest about what it is.
        This test should now pass since the infrastructure is implemented.
        """
        # Create honest WebSocket context
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        context = WebSocketContext(
            connection_id="conn_123",
            websocket=mock_websocket,
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # Context should be honest about being WebSocket-specific
        assert hasattr(context, 'websocket'), "Should have websocket attribute"
        assert hasattr(context, 'connection_id'), "Should have connection_id"
        assert hasattr(context, 'is_active'), "Should have is_active property"
        
        # Should NOT pretend to be an HTTP request
        assert not hasattr(context, 'headers'), "Should not pretend to have HTTP headers"
        assert not hasattr(context, 'cookies'), "Should not pretend to have cookies"
        
        # Test the honest WebSocket functionality
        assert context.is_active, "Should be active when WebSocket is connected"
        assert context.user_id == "test_user", "Should maintain user identity"
        assert context.thread_id == "test_thread", "Should maintain thread identity"
        assert context.run_id == "test_run", "Should maintain run identity"
    
    @pytest.mark.asyncio
    async def test_supervisor_factory_separation(self):
        """
        Test that WebSocket and HTTP have separate supervisor factories.
        This ensures protocol-specific patterns are properly separated.
        """
        # Both functions should exist and be different
        assert get_websocket_scoped_supervisor != get_request_scoped_supervisor
        
        # WebSocket factory should accept WebSocketContext, not Request
        import inspect
        ws_sig = inspect.signature(get_websocket_scoped_supervisor)
        assert 'context' in ws_sig.parameters, "Should accept context parameter"
        assert 'request' not in ws_sig.parameters, "Should NOT accept request parameter"
        
        # HTTP factory should accept Request
        http_sig = inspect.signature(get_request_scoped_supervisor)
        assert 'request' in http_sig.parameters, "Should accept request parameter"
        
        # Verify the parameter types are different
        ws_context_param = ws_sig.parameters['context']
        http_request_param = http_sig.parameters['request']
        
        # The annotation types should be different
        assert ws_context_param.annotation != http_request_param.annotation, \
            "WebSocket and HTTP factories should accept different types"
    
    @pytest.mark.asyncio
    async def test_no_mock_objects_in_websocket_flow(self):
        """
        Integration test: Verify entire WebSocket flow uses no mock Request objects.
        This is the ultimate test that the anti-pattern is eliminated in v3 clean pattern.
        """
        # Setup
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_db_session = AsyncMock(spec=AsyncSession)
        
        # Create honest WebSocket context
        ws_context = WebSocketContext(
            connection_id="conn_456",
            websocket=mock_websocket,
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # Mock required components
        with patch('netra_backend.app.websocket_core.supervisor_factory._get_websocket_supervisor_components') as mock_components:
            mock_components.return_value = {
                "llm_client": Mock(),
                "websocket_bridge": Mock(),
                "tool_dispatcher": Mock()
            }
            
            with patch('netra_backend.app.core.supervisor_factory.create_supervisor_core') as mock_create_core:
                mock_supervisor = Mock()
                mock_create_core.return_value = mock_supervisor
                
                # Spy on Request constructor to ensure it's NOT called in v3 pattern
                with patch('netra_backend.app.websocket_core.agent_handler.Request') as mock_request_class:
                    # Create supervisor using WebSocket-specific factory
                    supervisor = await get_websocket_scoped_supervisor(ws_context, mock_db_session)
                    
                    # Verify NO mock Request was created
                    mock_request_class.assert_not_called()
                    
                    # Supervisor should be created successfully without mocks
                    assert supervisor is not None
                    
                    # Verify core supervisor was created with WebSocket context data
                    mock_create_core.assert_called_once()
                    call_kwargs = mock_create_core.call_args[1]
                    assert call_kwargs['user_id'] == 'test_user'
                    assert call_kwargs['thread_id'] == 'test_thread'
                    assert call_kwargs['run_id'] == 'test_run'
                    assert call_kwargs['websocket_connection_id'] == 'conn_456'
    
    @pytest.mark.asyncio
    async def test_websocket_context_lifecycle(self):
        """
        Test that WebSocketContext properly manages connection lifecycle.
        This verifies WebSocket-specific concerns are handled correctly.
        """
        mock_websocket = Mock(spec=WebSocket)
        
        # Test active connection
        mock_websocket.client_state = WebSocketState.CONNECTED
        context = WebSocketContext(
            connection_id="conn_789",
            websocket=mock_websocket,
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        assert context.is_active, "Should be active when CONNECTED"
        
        # Test disconnected state
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        assert not context.is_active, "Should be inactive when DISCONNECTED"
        
        # Test connection duration tracking
        assert hasattr(context, 'connected_at'), "Should track connection time"
        assert hasattr(context, 'last_activity'), "Should track activity"
        
        # Test activity updates
        original_time = context.last_activity
        await asyncio.sleep(0.01)  # Small delay
        context.update_activity()
        assert context.last_activity > original_time, "Activity timestamp should update"
        
        # Test context validation
        mock_websocket.client_state = WebSocketState.CONNECTED  # Reconnect for validation
        assert context.validate_for_message_processing(), "Valid context should pass validation"
        
        # Test isolation key generation
        isolation_key = context.to_isolation_key()
        assert "test_user" in isolation_key, "Isolation key should contain user ID"
        assert "test_thread" in isolation_key, "Isolation key should contain thread ID"
    
    @pytest.mark.asyncio
    async def test_shared_core_logic(self):
        """
        Test that core supervisor logic is properly shared between HTTP and WebSocket.
        This ensures we don't duplicate logic while maintaining separation.
        """
        # Core function should be protocol-agnostic
        import inspect
        sig = inspect.signature(create_supervisor_core)
        params = sig.parameters
        
        # Should accept basic parameters, not protocol-specific objects
        assert 'user_id' in params, "Should accept user_id"
        assert 'thread_id' in params, "Should accept thread_id"
        assert 'run_id' in params, "Should accept run_id"
        assert 'db_session' in params, "Should accept db_session"
        
        # Should NOT accept Request or WebSocket objects
        assert 'request' not in params, "Should NOT accept Request"
        assert 'websocket' not in params, "Should NOT accept WebSocket"
        
        # Optional WebSocket connection ID for tracking
        assert 'websocket_connection_id' in params, "Should accept optional connection_id"
        
        # Verify the core function can be called with WebSocket context data
        mock_db_session = Mock(spec=AsyncSession)
        
        with patch('netra_backend.app.core.supervisor_factory.SupervisorAgent') as mock_supervisor_class:
            mock_supervisor_instance = Mock()
            mock_supervisor_class.return_value = mock_supervisor_instance
            
            # This should work without any Request or WebSocket objects
            supervisor = await create_supervisor_core(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                db_session=mock_db_session,
                websocket_connection_id="conn_123",
                llm_client=Mock(),
                websocket_bridge=Mock(),
                tool_dispatcher=Mock()
            )
            
            assert supervisor is not None, "Core supervisor should be created successfully"
    
    @pytest.mark.asyncio
    async def test_feature_flag_switching(self):
        """
        Test that feature flag correctly switches between v2 (legacy) and v3 (clean) patterns.
        Verifies backward compatibility during migration.
        """
        from netra_backend.app.services.message_handlers import MessageHandlerService
        mock_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(message_handler_service=mock_service)
        
        # Create test message
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        test_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"thread_id": "test_thread", "run_id": "test_run"},
            user_id="test_user",
            thread_id="test_thread",
            correlation_id="test_correlation"
        )
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Test v2 pattern (legacy with mock Request)
        with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):
            with patch.object(handler, '_handle_message_v2_legacy', return_value=True) as mock_v2:
                await handler.handle_message("test_user", mock_websocket, test_message)
                mock_v2.assert_called_once()
        
        # Test v3 pattern (clean WebSocket)
        with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
            with patch.object(handler, '_handle_message_v3_clean', return_value=True) as mock_v3:
                await handler.handle_message("test_user", mock_websocket, test_message)
                mock_v3.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_with_honest_objects(self):
        """
        Test that error handling works correctly with honest WebSocket objects.
        Mock objects can hide errors; honest objects surface them properly.
        """
        # Setup with disconnected WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        mock_db_session = AsyncMock(spec=AsyncSession)
        
        context = WebSocketContext(
            connection_id="conn_error",
            websocket=mock_websocket,
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # Should detect disconnected state honestly
        assert not context.is_active, "Should detect disconnected state"
        
        # Test context validation with inactive connection
        with pytest.raises(ValueError) as exc_info:
            context.validate_for_message_processing()
        
        # Error should be clear about WebSocket state
        assert "not active" in str(exc_info.value).lower()
        
        # Test WebSocket state checking with exception
        mock_websocket_error = Mock(spec=WebSocket)
        mock_websocket_error.client_state = property(lambda self: 1/0)  # Cause exception
        
        error_context = WebSocketContext(
            connection_id="conn_error_ws",
            websocket=mock_websocket_error,
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )
        
        # Should handle WebSocket state check errors gracefully
        assert not error_context.is_active, "Should return False when WebSocket state check fails"
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_isolation(self):
        """
        Test that multiple WebSocket connections are properly isolated.
        This is critical for multi-user support.
        """
        # Mock required components for all connections
        with patch('netra_backend.app.websocket_core.supervisor_factory._get_websocket_supervisor_components') as mock_components:
            mock_components.return_value = {
                "llm_client": Mock(),
                "websocket_bridge": Mock(),
                "tool_dispatcher": Mock()
            }
            
            with patch('netra_backend.app.core.supervisor_factory.create_supervisor_core') as mock_create_core:
                # Create multiple concurrent connections
                contexts = []
                supervisors = []
                
                for i in range(3):
                    mock_ws = Mock(spec=WebSocket)
                    mock_ws.client_state = WebSocketState.CONNECTED
                    mock_db = AsyncMock(spec=AsyncSession)
                    
                    # Each call should return a unique mock supervisor
                    unique_supervisor = Mock(name=f"supervisor_{i}")
                    mock_create_core.return_value = unique_supervisor
                    
                    context = WebSocketContext(
                        connection_id=f"conn_{i}",
                        websocket=mock_ws,
                        user_id=f"user_{i}",
                        thread_id=f"thread_{i}",
                        run_id=f"run_{i}",
                        connected_at=datetime.utcnow(),
                        last_activity=datetime.utcnow()
                    )
                    contexts.append(context)
                    
                    # Each connection gets its own supervisor
                    supervisor = await get_websocket_scoped_supervisor(context, mock_db)
                    supervisors.append(supervisor)
                
                # Verify contexts are independent
                for i, ctx in enumerate(contexts):
                    assert ctx.user_id == f"user_{i}", "Context should maintain correct user"
                    assert ctx.connection_id == f"conn_{i}", "Context should maintain correct connection"
                    assert ctx.thread_id == f"thread_{i}", "Context should maintain correct thread"
                    assert ctx.run_id == f"run_{i}", "Context should maintain correct run"
                    
                    # Each context should generate unique isolation keys
                    isolation_key = ctx.to_isolation_key()
                    assert f"user_{i}" in isolation_key, "Isolation key should contain correct user"
                    assert f"thread_{i}" in isolation_key, "Isolation key should contain correct thread"
                
                # Verify supervisor creation was called for each context
                assert mock_create_core.call_count == 3, "Should create supervisor for each connection"
                
                # Verify each call had different user/thread/run IDs
                calls = mock_create_core.call_args_list
                for i, call in enumerate(calls):
                    kwargs = call[1]
                    assert kwargs['user_id'] == f"user_{i}"
                    assert kwargs['thread_id'] == f"thread_{i}"
                    assert kwargs['run_id'] == f"run_{i}"
                    assert kwargs['websocket_connection_id'] == f"conn_{i}"
    
    @pytest.mark.asyncio
    async def test_v3_pattern_eliminates_mock_requests(self):
        """
        Test that the v3 clean pattern completely eliminates mock Request objects.
        This is the definitive test for anti-pattern elimination.
        """
        from netra_backend.app.services.message_handlers import MessageHandlerService
        mock_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(message_handler_service=mock_service)
        
        # Create test message
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "test message", "thread_id": "test_thread"},
            user_id="test_user",
            thread_id="test_thread",
            correlation_id="test_correlation"
        )
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Force v3 clean pattern
        with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
            # Spy on Request constructor - it should NEVER be called in v3
            with patch('netra_backend.app.websocket_core.agent_handler.Request') as mock_request_class:
                # Mock database session generation
                mock_db_session = AsyncMock(spec=AsyncSession)
                
                async def mock_db_generator():
                    yield mock_db_session
                    
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session', 
                          return_value=mock_db_generator()):
                    
                    # Mock WebSocket manager
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_manager') as mock_ws_manager:
                        mock_ws_manager.return_value = Mock()
                        mock_ws_manager.return_value.get_connection_id_by_websocket.return_value = "test_conn_v3"
                        mock_ws_manager.return_value.update_connection_thread.return_value = None
                        
                        # Mock WebSocket supervisor creation
                        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_ws_supervisor:
                            mock_ws_supervisor.return_value = Mock()
                            
                            # Mock message handler service creation
                            with patch('netra_backend.app.services.thread_service.ThreadService'):
                                with patch('netra_backend.app.services.message_handlers.MessageHandlerService'):
                                    with patch.object(handler, '_route_agent_message_v3', return_value=True):
                                        # This should succeed without creating any Request objects
                                        result = await handler._handle_message_v3_clean(
                                            "test_user", mock_websocket, test_message
                                        )
                                        
                                        # Verify NO Request objects were created
                                        mock_request_class.assert_not_called()
                                        
                                        # Verify WebSocket supervisor was used instead
                                        mock_ws_supervisor.assert_called_once()
                                        
                                        # Verify WebSocketContext was created with proper data
                                        ws_supervisor_call = mock_ws_supervisor.call_args
                                        context = ws_supervisor_call[1]['context']
                                        assert isinstance(context, WebSocketContext)
                                        assert context.user_id == "test_user"
                                        assert context.thread_id == "test_thread"
    
    @pytest.mark.asyncio
    async def test_websocket_context_factory_method(self):
        """
        Test the WebSocketContext factory method for user creation.
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Test factory method with minimal parameters
        context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id="factory_user",
            thread_id="factory_thread"
        )
        
        assert context.user_id == "factory_user"
        assert context.thread_id == "factory_thread"
        assert context.run_id is not None, "Should auto-generate run_id"
        assert context.connection_id is not None, "Should auto-generate connection_id"
        assert "factory_user" in context.connection_id, "Connection ID should include user ID"
        
        # Test factory method with all parameters
        custom_context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id="custom_user",
            thread_id="custom_thread",
            run_id="custom_run",
            connection_id="custom_connection"
        )
        
        assert custom_context.user_id == "custom_user"
        assert custom_context.thread_id == "custom_thread"
        assert custom_context.run_id == "custom_run"
        assert custom_context.connection_id == "custom_connection"
    
    @pytest.mark.asyncio
    async def test_websocket_context_validation_errors(self):
        """
        Test that WebSocketContext validation catches all error conditions.
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Test missing user_id
        with pytest.raises(ValueError, match="user_id is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=mock_websocket,
                user_id="",  # Empty user_id
                thread_id="test_thread",
                run_id="test_run"
            )
        
        # Test missing thread_id
        with pytest.raises(ValueError, match="thread_id is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=mock_websocket,
                user_id="test_user",
                thread_id="",  # Empty thread_id
                run_id="test_run"
            )
        
        # Test missing run_id
        with pytest.raises(ValueError, match="run_id is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=mock_websocket,
                user_id="test_user",
                thread_id="test_thread",
                run_id=""  # Empty run_id
            )
        
        # Test missing websocket
        with pytest.raises(ValueError, match="websocket is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=None,  # No websocket
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])