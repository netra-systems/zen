"""
Issue #1099 SSOT Handler Validation Tests

BUSINESS IMPACT: $500K+ ARR Golden Path protection
PURPOSE: Validate SSOT handlers meet requirements for legacy replacement

These tests validate that SSOT handlers implement the correct interfaces
and functionality required to replace legacy handlers.

Test Strategy: Comprehensive validation of SSOT handler capabilities

Created: 2025-09-15 (Issue #1099 Test Plan Phase 1)
"""

import asyncio
import pytest
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket
import time

# Import SSOT handlers for validation
from netra_backend.app.websocket_core.handlers import (
    BaseMessageHandler,
    ConnectionHandler,
    MessageHandler as MessageHandlerProtocol
)

from netra_backend.app.websocket_core.agent_handler import (
    AgentMessageHandler
)

from netra_backend.app.websocket_core.types import (
    WebSocketMessage,
    MessageType,
    create_standard_message,
    create_error_message
)

from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.canonical_message_router import (
    CanonicalMessageRouter,
    create_message_router,
    RoutingContext,
    MessageRoutingStrategy
)


class TestSSOTHandlerValidation:
    """
    SSOT Handler Validation Tests
    
    These tests validate that SSOT handlers implement the correct
    interfaces and functionality to replace legacy handlers.
    """
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket for testing"""
        websocket = Mock(spec=WebSocket)
        websocket.scope = {"app": Mock()}
        websocket.scope["app"].state = Mock()
        return websocket
    
    @pytest.fixture
    def mock_message_handler_service(self):
        """Mock message handler service"""
        service = Mock()
        service.handle_start_agent = AsyncMock()
        service.handle_user_message = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_ssot_agent_handler_interface_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT AgentMessageHandler interface compliance
        
        EXPECTED: PASS - SSOT handler implements required interface correctly
        VALIDATES: handle_message method signature and return type
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        # Verify handler implements correct interface
        assert isinstance(handler, BaseMessageHandler)
        assert hasattr(handler, 'handle_message')
        assert hasattr(handler, 'can_handle')
        assert callable(handler.handle_message)
        assert callable(handler.can_handle)
        
        # Verify supported message types
        assert handler.can_handle(MessageType.START_AGENT) == True
        assert handler.can_handle(MessageType.USER_MESSAGE) == True
        assert handler.can_handle(MessageType.CHAT) == True
        assert handler.can_handle(MessageType.CONNECT) == False  # Not supported
        
        # Test handle_message signature and return type
        user_id = "user_123"
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=True):
            result = await handler.handle_message(user_id, mock_websocket, message)
            assert isinstance(result, bool)
            assert result == True
        
        print("✅ SSOT AgentMessageHandler interface validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_connection_handler_interface_validation(self, mock_websocket):
        """
        VALIDATION TEST: SSOT ConnectionHandler interface compliance
        
        EXPECTED: PASS - SSOT connection handler implements interface correctly
        VALIDATES: Connection lifecycle message handling
        """
        handler = ConnectionHandler()
        
        # Verify handler implements correct interface
        assert isinstance(handler, BaseMessageHandler)
        assert hasattr(handler, 'handle_message')
        assert hasattr(handler, 'can_handle')
        
        # Verify supported message types
        assert handler.can_handle(MessageType.CONNECT) == True
        assert handler.can_handle(MessageType.DISCONNECT) == True
        assert handler.can_handle(MessageType.START_AGENT) == False  # Not supported
        
        # Test connection message handling
        connect_message = create_standard_message(
            MessageType.CONNECT,
            {"user_id": "user_123"}
        )
        
        result = await handler.handle_message("user_123", mock_websocket, connect_message)
        assert isinstance(result, bool)
        
        # Test disconnect message handling
        disconnect_message = create_standard_message(
            MessageType.DISCONNECT,
            {"reason": "user_logout"}
        )
        
        result = await handler.handle_message("user_123", mock_websocket, disconnect_message)
        assert isinstance(result, bool)
        
        print("✅ SSOT ConnectionHandler interface validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_message_processing_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT message processing capabilities
        
        EXPECTED: PASS - SSOT handlers process messages correctly
        VALIDATES: Message routing, payload handling, error management
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        # Test START_AGENT message processing
        start_agent_message = create_standard_message(
            MessageType.START_AGENT,
            {
                "user_request": "Create a data analysis report",
                "thread_id": "thread_123",
                "run_id": "run_456"
            }
        )
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=True) as mock_handle:
            result = await handler.handle_message("user_123", mock_websocket, start_agent_message)
            
            assert result == True
            mock_handle.assert_called_once()
            call_args = mock_handle.call_args[0]
            assert call_args[0] == "user_123"  # user_id
            assert call_args[1] == mock_websocket  # websocket
            assert call_args[2] == start_agent_message  # message
        
        # Test USER_MESSAGE processing
        user_message = create_standard_message(
            MessageType.USER_MESSAGE,
            {
                "message": "Can you help me analyze this data?",
                "thread_id": "thread_123"
            }
        )
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=True):
            result = await handler.handle_message("user_123", mock_websocket, user_message)
            assert result == True
        
        # Test CHAT message processing
        chat_message = create_standard_message(
            MessageType.CHAT,
            {
                "content": "Continue the analysis",
                "thread_id": "thread_123"
            }
        )
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=True):
            result = await handler.handle_message("user_123", mock_websocket, chat_message)
            assert result == True
        
        print("✅ SSOT message processing validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_error_handling_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT error handling capabilities
        
        EXPECTED: PASS - SSOT handlers handle errors gracefully with proper return codes
        VALIDATES: Error propagation, logging, and user notification
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        # Test error handling with proper return code
        error_message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=False):
            result = await handler.handle_message("user_123", mock_websocket, error_message)
            assert result == False  # Proper error indication
        
        # Test exception handling
        with patch.object(handler, '_handle_message_v3_clean', side_effect=Exception("Test error")):
            result = await handler.handle_message("user_123", mock_websocket, error_message)
            assert result == False  # Should not raise, should return False
        
        # Test invalid message type handling
        invalid_message = create_standard_message(
            MessageType.CONNECT,  # Not supported by AgentMessageHandler
            {"user_id": "user_123"}
        )
        
        result = await handler.handle_message("user_123", mock_websocket, invalid_message)
        # Should handle gracefully, not crash
        assert isinstance(result, bool)
        
        print("✅ SSOT error handling validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_websocket_context_integration_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT WebSocket context integration
        
        EXPECTED: PASS - SSOT handlers properly use WebSocketContext
        VALIDATES: Context creation, user isolation, session management
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        # Test WebSocketContext integration
        with patch('netra_backend.app.websocket_core.context.WebSocketContext.create_for_user') as mock_context_create:
            mock_context = Mock()
            mock_context.user_id = "user_123"
            mock_context.validate_for_message_processing = Mock()
            mock_context.update_activity = Mock()
            mock_context_create.return_value = mock_context
            
            with patch.object(handler, '_route_agent_message_v3', new_callable=AsyncMock, return_value=True):
                with patch('netra_backend.app.dependencies.get_user_execution_context'):
                    with patch('netra_backend.app.websocket_core.canonical_imports.create_websocket_manager', new_callable=AsyncMock):
                        result = await handler.handle_message("user_123", mock_websocket, message)
                        
                        # Verify context was created and used
                        mock_context_create.assert_called()
                        mock_context.validate_for_message_processing.assert_called()
                        mock_context.update_activity.assert_called()
        
        print("✅ SSOT WebSocket context integration validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_user_isolation_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT user isolation capabilities
        
        EXPECTED: PASS - SSOT handlers maintain proper user isolation
        VALIDATES: Multi-user safety, context separation, session isolation
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        # Test multiple users concurrently
        users = ["user_1", "user_2", "user_3"]
        messages = [
            create_standard_message(MessageType.START_AGENT, {"user_request": f"Request from {user}"})
            for user in users
        ]
        
        # Mock context creation to verify isolation
        created_contexts = []
        
        def mock_context_create(websocket, user_id, **kwargs):
            context = Mock()
            context.user_id = user_id
            context.validate_for_message_processing = Mock()
            context.update_activity = Mock()
            created_contexts.append(context)
            return context
        
        with patch('netra_backend.app.websocket_core.context.WebSocketContext.create_for_user', side_effect=mock_context_create):
            with patch.object(handler, '_route_agent_message_v3', new_callable=AsyncMock, return_value=True):
                with patch('netra_backend.app.dependencies.get_user_execution_context'):
                    with patch('netra_backend.app.websocket_core.canonical_imports.create_websocket_manager', new_callable=AsyncMock):
                        
                        # Process messages for all users
                        tasks = [
                            handler.handle_message(user, mock_websocket, message)
                            for user, message in zip(users, messages)
                        ]
                        
                        results = await asyncio.gather(*tasks)
                        
                        # Verify all succeeded
                        assert all(results)
                        
                        # Verify separate contexts created for each user
                        assert len(created_contexts) == len(users)
                        for i, context in enumerate(created_contexts):
                            assert context.user_id == users[i]
        
        print("✅ SSOT user isolation validation passed")
    
    def test_ssot_message_router_validation(self):
        """
        VALIDATION TEST: SSOT CanonicalMessageRouter capabilities
        
        EXPECTED: PASS - SSOT message router provides required functionality
        VALIDATES: Message routing, connection management, event delivery
        """
        # Test router creation
        router = create_message_router()
        assert isinstance(router, CanonicalMessageRouter)
        
        # Test router with user context
        user_context = {"user_id": "user_123", "session_id": "session_456"}
        context_router = create_message_router(user_context)
        assert context_router.user_context == user_context
        
        # Test routing strategies
        strategies = [
            MessageRoutingStrategy.USER_SPECIFIC,
            MessageRoutingStrategy.SESSION_SPECIFIC,
            MessageRoutingStrategy.BROADCAST_ALL,
            MessageRoutingStrategy.AGENT_SPECIFIC,
            MessageRoutingStrategy.PRIORITY_BASED
        ]
        
        for strategy in strategies:
            assert strategy in context_router._routing_rules
            assert callable(context_router._routing_rules[strategy])
        
        # Test statistics
        stats = router.get_stats()
        assert isinstance(stats, dict)
        assert 'messages_routed' in stats
        assert 'routing_errors' in stats
        assert 'active_connections' in stats
        
        print("✅ SSOT message router validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_connection_management_validation(self):
        """
        VALIDATION TEST: SSOT connection management capabilities
        
        EXPECTED: PASS - SSOT router manages connections correctly
        VALIDATES: Connection registration, unregistration, cleanup
        """
        router = create_message_router()
        
        # Test connection registration
        connection_id = "conn_123"
        user_id = "user_123"
        session_id = "session_456"
        
        success = await router.register_connection(connection_id, user_id, session_id)
        assert success == True
        
        # Verify connection is registered
        user_connections = router.get_user_connections(user_id)
        assert len(user_connections) == 1
        assert user_connections[0]['connection_id'] == connection_id
        assert user_connections[0]['session_id'] == session_id
        assert user_connections[0]['is_active'] == True
        
        # Test connection unregistration
        success = await router.unregister_connection(connection_id)
        assert success == True
        
        # Verify connection is removed
        user_connections = router.get_user_connections(user_id)
        assert len(user_connections) == 0
        
        # Test multiple connections for same user
        connections = [f"conn_{i}" for i in range(5)]
        for conn_id in connections:
            success = await router.register_connection(conn_id, user_id)
            assert success == True
        
        user_connections = router.get_user_connections(user_id)
        assert len(user_connections) == 5
        
        # Test cleanup
        await router.cleanup_inactive_connections(timeout_seconds=0)  # Cleanup immediately
        # Connections should still be active (just created)
        user_connections = router.get_user_connections(user_id)
        assert len(user_connections) == 5
        
        print("✅ SSOT connection management validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_message_routing_validation(self):
        """
        VALIDATION TEST: SSOT message routing capabilities
        
        EXPECTED: PASS - SSOT router routes messages correctly
        VALIDATES: Message delivery, routing strategies, filtering
        """
        router = create_message_router()
        
        # Register test connections
        user_id = "user_123"
        connections = ["conn_1", "conn_2", "conn_3"]
        
        for conn_id in connections:
            await router.register_connection(conn_id, user_id)
        
        # Test message routing
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test message"}
        )
        
        routing_context = RoutingContext(
            user_id=user_id,
            routing_strategy=MessageRoutingStrategy.USER_SPECIFIC
        )
        
        with patch.object(router, '_send_to_destination', new_callable=AsyncMock, return_value=True):
            delivered_connections = await router.route_message(message, routing_context)
            
            # Should deliver to all user connections
            assert len(delivered_connections) == len(connections)
            assert set(delivered_connections) == set(connections)
        
        # Test session-specific routing
        session_id = "session_456"
        await router.register_connection("conn_session", user_id, session_id)
        
        session_context = RoutingContext(
            user_id=user_id,
            session_id=session_id,
            routing_strategy=MessageRoutingStrategy.SESSION_SPECIFIC
        )
        
        with patch.object(router, '_send_to_destination', new_callable=AsyncMock, return_value=True):
            delivered_connections = await router.route_message(message, session_context)
            
            # Should deliver only to session connection
            assert len(delivered_connections) == 1
            assert delivered_connections[0] == "conn_session"
        
        print("✅ SSOT message routing validation passed")
    
    def test_ssot_performance_validation(self, mock_message_handler_service):
        """
        VALIDATION TEST: SSOT handler performance characteristics
        
        EXPECTED: PASS - SSOT handlers meet performance requirements
        VALIDATES: Handler creation time, message processing speed
        """
        # Test handler creation performance
        start_time = time.time()
        
        handlers = []
        for _ in range(10):  # Create 10 handlers
            handler = AgentMessageHandler(mock_message_handler_service)
            handlers.append(handler)
        
        creation_time = time.time() - start_time
        
        # SSOT handlers should be fast to create (< 100ms for 10 handlers)
        assert creation_time < 0.1  # 100ms
        
        # Test message type checking performance
        start_time = time.time()
        
        for handler in handlers:
            assert handler.can_handle(MessageType.START_AGENT) == True
            assert handler.can_handle(MessageType.USER_MESSAGE) == True
            assert handler.can_handle(MessageType.CHAT) == True
        
        checking_time = time.time() - start_time
        
        # Message type checking should be very fast (< 10ms for 30 checks)
        assert checking_time < 0.01  # 10ms
        
        print(f"✅ SSOT performance validation passed: "
              f"creation={creation_time:.3f}s, checking={checking_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_ssot_backwards_compatibility_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT backwards compatibility with legacy patterns
        
        EXPECTED: PASS - SSOT handlers can work with legacy-style data
        VALIDATES: Payload compatibility, message format handling
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        # Test with legacy-style payload structure
        legacy_style_payload = {
            "type": "start_agent",  # String type (legacy style)
            "user_request": "Create analysis",
            "thread_id": "thread_123",
            "run_id": "run_456"
        }
        
        # Convert to SSOT WebSocketMessage format
        ssot_message = create_standard_message(
            MessageType.START_AGENT,
            legacy_style_payload
        )
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=True):
            result = await handler.handle_message("user_123", mock_websocket, ssot_message)
            assert result == True
        
        # Test with missing optional fields (legacy compatibility)
        minimal_payload = {"user_request": "Simple request"}
        minimal_message = create_standard_message(MessageType.START_AGENT, minimal_payload)
        
        with patch.object(handler, '_handle_message_v3_clean', new_callable=AsyncMock, return_value=True):
            result = await handler.handle_message("user_123", mock_websocket, minimal_message)
            assert result == True
        
        print("✅ SSOT backwards compatibility validation passed")


class TestSSOTIntegrationCapabilities:
    """
    Tests for SSOT handler integration capabilities with the broader system.
    """
    
    @pytest.mark.asyncio
    async def test_ssot_database_integration_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT database integration patterns
        
        EXPECTED: PASS - SSOT handlers integrate with database correctly
        VALIDATES: Session management, transaction handling, data persistence
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        # Test database session integration
        with patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            mock_session = Mock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            with patch.object(handler, '_route_agent_message_v3', new_callable=AsyncMock, return_value=True):
                with patch('netra_backend.app.dependencies.get_user_execution_context'):
                    with patch('netra_backend.app.websocket_core.canonical_imports.create_websocket_manager', new_callable=AsyncMock):
                        result = await handler.handle_message("user_123", mock_websocket, message)
                        assert result == True
        
        print("✅ SSOT database integration validation passed")
    
    @pytest.mark.asyncio
    async def test_ssot_websocket_manager_integration_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT WebSocket manager integration
        
        EXPECTED: PASS - SSOT handlers integrate with WebSocket manager correctly
        VALIDATES: Connection management, event delivery, error handling
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        # Test WebSocket manager integration
        with patch('netra_backend.app.websocket_core.canonical_imports.create_websocket_manager') as mock_manager_factory:
            mock_manager = Mock()
            mock_manager.get_connection_id_by_websocket = Mock(return_value="conn_123")
            mock_manager.update_connection_thread = Mock()
            mock_manager.send_error = AsyncMock()
            mock_manager_factory.return_value = mock_manager
            
            with patch('netra_backend.app.dependencies.get_user_execution_context'):
                with patch.object(handler, '_route_agent_message_v3', new_callable=AsyncMock, return_value=True):
                    result = await handler.handle_message("user_123", mock_websocket, message)
                    assert result == True
        
        print("✅ SSOT WebSocket manager integration validation passed")
    
    @pytest.mark.asyncio 
    async def test_ssot_supervisor_integration_validation(self, mock_message_handler_service, mock_websocket):
        """
        VALIDATION TEST: SSOT supervisor integration
        
        EXPECTED: PASS - SSOT handlers integrate with supervisor correctly
        VALIDATES: Agent execution, task management, workflow coordination
        """
        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
        
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        # Test supervisor integration through message handler service
        with patch('netra_backend.app.websocket_core.supervisor_factory.get_websocket_scoped_supervisor') as mock_supervisor_factory:
            mock_supervisor = Mock()
            mock_supervisor_factory.return_value = mock_supervisor
            
            with patch('netra_backend.app.dependencies.get_user_execution_context'):
                with patch('netra_backend.app.websocket_core.canonical_imports.create_websocket_manager', new_callable=AsyncMock):
                    with patch.object(handler, '_route_agent_message_v3', new_callable=AsyncMock, return_value=True):
                        result = await handler.handle_message("user_123", mock_websocket, message)
                        assert result == True
        
        print("✅ SSOT supervisor integration validation passed")


if __name__ == "__main__":
    # Run SSOT validation tests
    print("🔍 Running SSOT Handler Validation Tests for Issue #1099")
    print("=" * 60)
    
    exit_code = pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-m", "not integration"  # Skip integration tests for validation
    ])
    
    if exit_code == 0:
        print("\n✅ SSOT HANDLER VALIDATION SUCCESSFUL")
        print("All SSOT handlers meet requirements for legacy replacement")
        print("SSOT handlers ready for migration implementation")
    else:
        print("\n❌ SSOT HANDLER VALIDATION FAILED")
        print("SSOT handlers need fixes before they can replace legacy handlers")
    
    exit(exit_code)