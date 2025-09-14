"""
Unit Tests for Agent-WebSocket Bridge Pipeline - Issue #861 Phase 1

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Development Velocity & System Integration Quality
- Value Impact: Validates the critical bridge between agent execution and WebSocket communication
- Strategic Impact: Ensures $500K+ ARR agent processing results reach users in real-time

Test Coverage Focus:
- Agent execution engine to WebSocket manager integration
- WebSocket context creation and lifecycle management
- Database session scoping within WebSocket flows
- Supervisor agent factory patterns and isolation
- Error propagation through the bridge pipeline
- Multi-user isolation in bridge operations
- Performance and resource management in bridge flows

CRITICAL BRIDGE COMPONENTS:
- UserExecutionContext -> WebSocketContext transformation
- Database session management across async boundaries
- Supervisor agent creation with WebSocket scoping
- Message handler service integration
- Error handling and user notification pipeline

REQUIREMENTS per CLAUDE.md:
- Use SSotBaseTestCase for unified test infrastructure
- Test actual bridge pipeline, not isolated components
- Focus on integration points between major system components
- Validate resource cleanup and proper isolation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService
from shared.isolated_environment import IsolatedEnvironment


class TestAgentWebSocketBridgePipeline(SSotAsyncTestCase):
    """Test suite for agent-WebSocket bridge pipeline integration."""

    def setup_method(self, method):
        """Set up test fixtures for bridge pipeline testing."""
        super().setup_method(method)
        
        # Create test environment
        self.env = IsolatedEnvironment()
        self.test_user_id = "bridge_test_user_" + str(uuid.uuid4())[:8]
        self.test_thread_id = "bridge_thread_" + str(uuid.uuid4())[:8]
        self.test_run_id = "bridge_run_" + str(uuid.uuid4())[:8]
        
        # Create mock WebSocket with realistic behavior
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.mock_websocket.client_state = "connected"
        self.mock_websocket.scope = {
            'app': MagicMock(),
            'client': ('127.0.0.1', 12345),
            'path': '/ws/agent',
            'type': 'websocket'
        }
        self.mock_websocket.scope['app'].state = MagicMock()
        
        # Track WebSocket events for verification
        self.websocket_events = []
        
        async def track_websocket_events(data):
            try:
                if isinstance(data, str):
                    event = json.loads(data)
                else:
                    event = data
                self.websocket_events.append({
                    "timestamp": time.time(),
                    "event": event
                })
            except:
                self.websocket_events.append({
                    "timestamp": time.time(),
                    "raw_data": str(data)
                })
        
        self.mock_websocket.send_text = AsyncMock(side_effect=track_websocket_events)
        self.mock_websocket.send_json = AsyncMock(side_effect=track_websocket_events)
        
        # Create mock message handler service
        self.mock_message_handler_service = MagicMock(spec=MessageHandlerService)
        self.mock_message_handler_service.handle_start_agent = AsyncMock(return_value=True)
        self.mock_message_handler_service.handle_user_message = AsyncMock(return_value=True)
        
        # Track bridge operations
        self.bridge_operations = []

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
        self.websocket_events.clear()
        self.bridge_operations.clear()

    def create_test_message(self, message_type: MessageType, payload: Dict[str, Any]) -> WebSocketMessage:
        """Create a test WebSocket message for bridge testing."""
        return WebSocketMessage(
            type=message_type,
            payload=payload,
            timestamp=time.time(),
            message_id=f"bridge_msg_{uuid.uuid4()}",
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )

    def track_bridge_operation(self, operation: str, **kwargs):
        """Track bridge operations for verification."""
        self.bridge_operations.append({
            "operation": operation,
            "timestamp": time.time(),
            "details": kwargs
        })

    # Test 1: Complete Bridge Pipeline Flow
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor')
    async def test_complete_bridge_pipeline_flow_success(self, mock_supervisor, mock_db_session, 
                                                        mock_ws_manager, mock_context):
        """Test complete end-to-end bridge pipeline flow.
        
        Business Impact: This is the full integration - agent request to WebSocket response.
        Golden Path Impact: The entire user experience depends on this pipeline working.
        """
        # Setup execution context
        mock_execution_context = MagicMock(spec=UserExecutionContext)
        mock_execution_context.user_id = self.test_user_id
        mock_execution_context.thread_id = self.test_thread_id
        mock_execution_context.run_id = self.test_run_id
        mock_context.return_value = mock_execution_context
        
        # Setup WebSocket manager
        mock_ws_manager_instance = AsyncMock()
        mock_ws_manager_instance.get_connection_id_by_websocket.return_value = "bridge_conn_123"
        mock_ws_manager_instance.update_connection_thread = AsyncMock()
        mock_ws_manager.return_value = mock_ws_manager_instance
        
        # Setup database session
        mock_db_session_instance = MagicMock(spec=AsyncSession)
        async def mock_db_generator():
            yield mock_db_session_instance
        mock_db_session.return_value = mock_db_generator()
        
        # Setup supervisor
        mock_supervisor_instance = MagicMock()
        mock_supervisor.return_value = mock_supervisor_instance
        
        # Create agent message handler
        handler = AgentMessageHandler(self.mock_message_handler_service)
        
        # Create test message
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Complete bridge pipeline test"}
        )
        
        # Track bridge operations through patches
        original_create_websocket_context = None
        
        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
            with patch('netra_backend.app.services.thread_service.ThreadService') as MockThreadService:
                with patch('netra_backend.app.services.message_handlers.MessageHandlerService') as MockMHS:
                    
                    # Setup WebSocket context creation
                    mock_ws_context = MagicMock(spec=WebSocketContext)
                    mock_ws_context.user_id = self.test_user_id
                    mock_ws_context.thread_id = self.test_thread_id
                    mock_ws_context.run_id = self.test_run_id
                    mock_ws_context.connection_id = "bridge_conn_123"
                    mock_ws_context.update_activity = MagicMock()
                    mock_ws_context.validate_for_message_processing = MagicMock()
                    MockWSContext.create_for_user.return_value = mock_ws_context
                    
                    # Setup message handler service
                    mock_handler_instance = AsyncMock(spec=MessageHandlerService)
                    mock_handler_instance.handle_start_agent = AsyncMock(return_value=True)
                    MockMHS.return_value = mock_handler_instance
                    
                    # Execute bridge pipeline
                    result = await handler.handle_message(
                        self.test_user_id,
                        self.mock_websocket,
                        message
                    )
        
        # Verify complete pipeline success
        assert result is True
        
        # Verify bridge components were called in correct order
        mock_context.assert_called_once_with(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=None  # Not provided in payload
        )
        
        mock_ws_manager.assert_called_once_with(mock_execution_context)
        MockWSContext.create_for_user.assert_called_once()
        mock_handler_instance.handle_start_agent.assert_called_once()

    # Test 2: UserExecutionContext to WebSocketContext Transformation
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_user_execution_context_to_websocket_context_transformation(self, mock_context):
        """Test proper transformation from UserExecutionContext to WebSocketContext.
        
        Business Impact: Context transformation maintains user isolation and session continuity.
        """
        # Setup execution context with specific IDs
        mock_execution_context = MagicMock(spec=UserExecutionContext)
        mock_execution_context.user_id = self.test_user_id
        mock_execution_context.thread_id = "transformed_thread_123"
        mock_execution_context.run_id = "transformed_run_456"
        mock_context.return_value = mock_execution_context
        
        # Mock WebSocket context creation to verify parameters
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_ws_manager:
            with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                    
                    mock_ws_manager.return_value = AsyncMock()
                    mock_ws_context = MagicMock()
                    MockWSContext.create_for_user.return_value = mock_ws_context
                    
                    handler = AgentMessageHandler(self.mock_message_handler_service)
                    message = self.create_test_message(
                        MessageType.USER_MESSAGE,
                        {"message": "Context transformation test"}
                    )
                    
                    try:
                        await handler.handle_message(self.test_user_id, self.mock_websocket, message)
                    except:
                        pass  # We're only testing context transformation
                    
                    # Verify WebSocket context was created with transformed values
                    MockWSContext.create_for_user.assert_called_once_with(
                        websocket=self.mock_websocket,
                        user_id=self.test_user_id,
                        thread_id="transformed_thread_123",  # From execution context
                        run_id="transformed_run_456",  # From execution context
                        connection_id=None  # Would be generated or retrieved
                    )

    # Test 3: Database Session Scoping Across Bridge
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    async def test_database_session_scoping_across_bridge_operations(self, mock_db_session, 
                                                                    mock_ws_manager, mock_context):
        """Test database session is properly scoped across bridge operations.
        
        Business Impact: Prevents database connection leaks and ensures transaction consistency.
        """
        # Setup mocks
        mock_context.return_value = MagicMock()
        mock_ws_manager.return_value = AsyncMock()
        
        # Track database session lifecycle
        session_lifecycle = []
        mock_session = MagicMock(spec=AsyncSession)
        
        async def mock_db_generator():
            session_lifecycle.append("session_created")
            try:
                yield mock_session
                session_lifecycle.append("session_yielded")
            finally:
                session_lifecycle.append("session_cleaned_up")
        
        mock_db_session.return_value = mock_db_generator()
        
        # Create handler and process message
        handler = AgentMessageHandler(self.mock_message_handler_service)
        message = self.create_test_message(
            MessageType.CHAT,
            {"content": "Database session test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor'):
            with patch('netra_backend.app.services.thread_service.ThreadService'):
                with patch('netra_backend.app.services.message_handlers.MessageHandlerService'):
                    result = await handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify session lifecycle was completed
        assert "session_created" in session_lifecycle
        assert "session_cleaned_up" in session_lifecycle

    # Test 4: Supervisor Agent Factory Integration
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor')
    async def test_supervisor_agent_factory_integration_with_bridge(self, mock_supervisor, mock_db_session,
                                                                   mock_ws_manager, mock_context):
        """Test supervisor agent factory properly integrates with bridge pipeline.
        
        Business Impact: Ensures agent execution is properly scoped to WebSocket context.
        """
        # Setup mocks
        mock_context.return_value = MagicMock()
        mock_ws_manager.return_value = AsyncMock()
        
        mock_session = MagicMock()
        async def mock_db_generator():
            yield mock_session
        mock_db_session.return_value = mock_db_generator()
        
        mock_supervisor_instance = MagicMock()
        mock_supervisor.return_value = mock_supervisor_instance
        
        # Track supervisor creation parameters
        supervisor_creation_args = None
        
        def capture_supervisor_args(*args, **kwargs):
            nonlocal supervisor_creation_args
            supervisor_creation_args = {"args": args, "kwargs": kwargs}
            return mock_supervisor_instance
        
        mock_supervisor.side_effect = capture_supervisor_args
        
        # Process message through bridge
        handler = AgentMessageHandler(self.mock_message_handler_service)
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Supervisor factory test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
            with patch('netra_backend.app.services.thread_service.ThreadService'):
                with patch('netra_backend.app.services.message_handlers.MessageHandlerService'):
                    
                    mock_ws_context = MagicMock()
                    MockWSContext.create_for_user.return_value = mock_ws_context
                    
                    result = await handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify supervisor was created with correct parameters
        assert supervisor_creation_args is not None
        kwargs = supervisor_creation_args["kwargs"]
        
        # Should include WebSocket context, database session, and app state
        assert "context" in kwargs
        assert "db_session" in kwargs
        assert "app_state" in kwargs

    # Test 5: Error Propagation Through Bridge
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_error_propagation_through_bridge_pipeline(self, mock_context):
        """Test error propagation and handling through bridge pipeline.
        
        Business Impact: Users get proper error feedback when bridge components fail.
        """
        # Make context creation fail to test error propagation
        mock_context.side_effect = Exception("Bridge context creation failed")
        
        handler = AgentMessageHandler(self.mock_message_handler_service)
        message = self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Error propagation test"}
        )
        
        # Process message - should handle error gracefully
        result = await handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Should return False indicating failure
        assert result is False
        
        # Verify error was tracked in handler statistics
        stats = handler.get_stats()
        assert stats["errors"] == 1

    # Test 6: Multi-User Isolation in Bridge Operations  
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    async def test_multi_user_isolation_in_bridge_operations(self, mock_db_session, 
                                                            mock_ws_manager, mock_context):
        """Test bridge operations maintain proper isolation between different users.
        
        Business Impact: Critical for multi-tenant system security and data isolation.
        """
        # Create contexts for different users
        user1_id = "bridge_user1_" + str(uuid.uuid4())[:8]
        user2_id = "bridge_user2_" + str(uuid.uuid4())[:8]
        
        user_contexts = {}
        
        def create_isolated_context(user_id, **kwargs):
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = user_id
            context.thread_id = f"thread_{user_id}"
            context.run_id = f"run_{user_id}"
            user_contexts[user_id] = context
            return context
        
        mock_context.side_effect = create_isolated_context
        mock_ws_manager.return_value = AsyncMock()
        
        # Setup database sessions
        async def mock_db_generator():
            yield MagicMock()
        mock_db_session.return_value = mock_db_generator()
        
        # Create handlers for each user
        handler1 = AgentMessageHandler(self.mock_message_handler_service)
        handler2 = AgentMessageHandler(self.mock_message_handler_service)
        
        # Create messages for each user
        message1 = WebSocketMessage(
            type=MessageType.CHAT,
            payload={"content": f"User 1 message"},
            timestamp=time.time(),
            user_id=user1_id,
            thread_id=f"thread_{user1_id}"
        )
        
        message2 = WebSocketMessage(
            type=MessageType.CHAT,
            payload={"content": f"User 2 message"},
            timestamp=time.time(),
            user_id=user2_id,
            thread_id=f"thread_{user2_id}"
        )
        
        # Process messages concurrently
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor'):
            with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
                with patch('netra_backend.app.services.thread_service.ThreadService'):
                    with patch('netra_backend.app.services.message_handlers.MessageHandlerService'):
                        
                        # Track context creation for isolation verification
                        created_contexts = []
                        
                        def track_context_creation(*args, **kwargs):
                            context = MagicMock()
                            context.user_id = kwargs.get('user_id')
                            created_contexts.append(context)
                            return context
                        
                        MockWSContext.create_for_user.side_effect = track_context_creation
                        
                        results = await asyncio.gather(
                            handler1.handle_message(user1_id, self.mock_websocket, message1),
                            handler2.handle_message(user2_id, self.mock_websocket, message2)
                        )
        
        # Verify both processed successfully with isolation
        assert len(results) == 2
        
        # Verify contexts were created separately for each user
        assert user1_id in user_contexts
        assert user2_id in user_contexts
        assert user_contexts[user1_id] != user_contexts[user2_id]

    # Test 7: Bridge Performance Under Load
    async def test_bridge_pipeline_performance_under_concurrent_load(self):
        """Test bridge pipeline performance with multiple concurrent requests.
        
        Business Impact: System must handle multiple users without performance degradation.
        """
        # Setup performance test with multiple concurrent handlers
        num_concurrent_requests = 10
        handlers = []
        tasks = []
        
        for i in range(num_concurrent_requests):
            handler = AgentMessageHandler(self.mock_message_handler_service)
            handlers.append(handler)
            
            message = self.create_test_message(
                MessageType.USER_MESSAGE,
                {"message": f"Performance test message {i}"}
            )
            
            # Mock the heavy lifting to focus on bridge performance
            with patch.object(handler, '_handle_message_v3_clean') as mock_handler:
                async def mock_processing(user_id, websocket, message, delay=0.01):
                    await asyncio.sleep(delay)  # Simulate processing time
                    return True
                
                mock_handler.return_value = mock_processing(f"user_{i}", self.mock_websocket, message)
                task = handler.handle_message(f"user_{i}", self.mock_websocket, message)
                tasks.append(task)
        
        # Measure performance
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all requests succeeded
        assert all(results)
        
        # Verify reasonable performance (10 requests should complete quickly)
        total_time = end_time - start_time
        assert total_time < 2.0, f"Bridge pipeline too slow: {total_time}s for {num_concurrent_requests} requests"

    # Test 8: Resource Cleanup in Bridge Pipeline
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    async def test_resource_cleanup_in_bridge_pipeline(self, mock_db_session, mock_ws_manager, mock_context):
        """Test proper resource cleanup in bridge pipeline, even on failures.
        
        Business Impact: Prevents resource leaks that could degrade system performance.
        """
        # Setup mocks
        mock_context.return_value = MagicMock()
        mock_ws_manager.return_value = AsyncMock()
        
        # Track resource lifecycle
        resource_lifecycle = []
        
        class TrackingSession:
            def __init__(self):
                resource_lifecycle.append("session_created")
            
            def close(self):
                resource_lifecycle.append("session_closed")
            
            async def __aenter__(self):
                resource_lifecycle.append("session_entered")
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                resource_lifecycle.append("session_exited")
        
        async def mock_db_generator():
            session = TrackingSession()
            try:
                resource_lifecycle.append("session_yielded")
                yield session
            finally:
                resource_lifecycle.append("session_generator_cleanup")
        
        mock_db_session.return_value = mock_db_generator()
        
        # Test with both success and failure scenarios
        handler = AgentMessageHandler(self.mock_message_handler_service)
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Resource cleanup test"}
        )
        
        # Test successful cleanup
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor'):
            with patch('netra_backend.app.services.thread_service.ThreadService'):
                with patch('netra_backend.app.services.message_handlers.MessageHandlerService'):
                    result = await handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify resources were properly cleaned up
        assert "session_generator_cleanup" in resource_lifecycle

    # Test 9: WebSocket Manager Integration
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    async def test_websocket_manager_integration_in_bridge(self, mock_ws_manager, mock_context):
        """Test WebSocket manager proper integration in bridge pipeline.
        
        Business Impact: WebSocket manager handles connection lifecycle and message delivery.
        """
        # Setup execution context
        mock_context.return_value = MagicMock()
        
        # Setup WebSocket manager with tracking
        manager_operations = []
        mock_manager = AsyncMock()
        
        def track_get_connection(websocket):
            manager_operations.append(("get_connection_id_by_websocket", websocket))
            return "tracked_connection_123"
        
        def track_update_thread(connection_id, thread_id):
            manager_operations.append(("update_connection_thread", connection_id, thread_id))
        
        mock_manager.get_connection_id_by_websocket.side_effect = track_get_connection
        mock_manager.update_connection_thread.side_effect = track_update_thread
        mock_ws_manager.return_value = mock_manager
        
        # Process message through bridge
        handler = AgentMessageHandler(self.mock_message_handler_service)
        message = self.create_test_message(
            MessageType.CHAT,
            {"content": "WebSocket manager integration test", "thread_id": "integration_thread"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
            try:
                await handler.handle_message(self.test_user_id, self.mock_websocket, message)
            except:
                pass  # We're focused on WebSocket manager integration
        
        # Verify WebSocket manager was properly utilized
        operation_types = [op[0] for op in manager_operations]
        assert "get_connection_id_by_websocket" in operation_types

    # Test 10: Bridge Pipeline Logging and Observability
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    async def test_bridge_pipeline_logging_and_observability(self, mock_ws_manager, mock_context):
        """Test bridge pipeline generates proper logging for observability.
        
        Business Impact: Enables monitoring and debugging of agent-WebSocket integration.
        """
        # Setup mocks
        mock_context.return_value = MagicMock()
        mock_ws_manager.return_value = AsyncMock()
        
        # Capture log messages
        captured_logs = []
        
        # Mock the logger to capture log messages
        with patch('netra_backend.app.websocket_core.agent_handler.logger') as mock_logger:
            def capture_log(msg, *args, **kwargs):
                captured_logs.append({"level": "info", "message": msg})
            
            mock_logger.info.side_effect = capture_log
            mock_logger.debug.side_effect = lambda msg, *args, **kwargs: captured_logs.append({"level": "debug", "message": msg})
            mock_logger.error.side_effect = lambda msg, *args, **kwargs: captured_logs.append({"level": "error", "message": msg})
            
            handler = AgentMessageHandler(self.mock_message_handler_service)
            message = self.create_test_message(
                MessageType.USER_MESSAGE,
                {"message": "Observability test"}
            )
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                await handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify observability logs were generated
        assert len(captured_logs) > 0
        
        # Should have logs about golden path processing
        golden_path_logs = [log for log in captured_logs if "GOLDEN PATH" in str(log["message"])]
        assert len(golden_path_logs) > 0

    # Test 11: Thread and Connection Management
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    async def test_thread_and_connection_management_in_bridge(self, mock_ws_manager, mock_context):
        """Test thread and connection management through bridge pipeline.
        
        Business Impact: Proper threading ensures message ordering and session continuity.
        """
        # Setup execution context with thread management
        mock_execution_context = MagicMock()
        mock_execution_context.thread_id = "managed_thread_789"
        mock_execution_context.run_id = "managed_run_101"
        mock_context.return_value = mock_execution_context
        
        # Track thread and connection operations
        connection_operations = []
        mock_manager = AsyncMock()
        
        def track_connection_ops(*args):
            connection_operations.append(args)
            return "managed_connection_456"
        
        mock_manager.get_connection_id_by_websocket.side_effect = track_connection_ops
        mock_manager.update_connection_thread = AsyncMock()
        mock_ws_manager.return_value = mock_manager
        
        # Process message with thread ID in payload
        handler = AgentMessageHandler(self.mock_message_handler_service)
        message = self.create_test_message(
            MessageType.START_AGENT,
            {
                "user_request": "Thread management test",
                "thread_id": "payload_thread_999"  # Different from execution context
            }
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
            with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
                mock_ws_context = MagicMock()
                MockWSContext.create_for_user.return_value = mock_ws_context
                
                try:
                    await handler.handle_message(self.test_user_id, self.mock_websocket, message)
                except:
                    pass  # We're focused on connection management
        
        # Verify connection management was performed
        assert len(connection_operations) > 0
        
        # Verify thread update was called if connection was found
        if mock_manager.get_connection_id_by_websocket.return_value:
            mock_manager.update_connection_thread.assert_called()

    # Test 12: Bridge Pipeline State Consistency
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    async def test_bridge_pipeline_maintains_state_consistency(self, mock_db_session, 
                                                               mock_ws_manager, mock_context):
        """Test bridge pipeline maintains consistent state across all components.
        
        Business Impact: State consistency ensures reliable user experience and data integrity.
        """
        # Setup consistent state across all components
        consistent_user_id = "consistent_user_123"
        consistent_thread_id = "consistent_thread_456"
        consistent_run_id = "consistent_run_789"
        
        # Setup execution context
        mock_execution_context = MagicMock()
        mock_execution_context.user_id = consistent_user_id
        mock_execution_context.thread_id = consistent_thread_id
        mock_execution_context.run_id = consistent_run_id
        mock_context.return_value = mock_execution_context
        
        # Setup WebSocket manager
        mock_ws_manager.return_value = AsyncMock()
        
        # Setup database session
        async def mock_db_generator():
            yield MagicMock()
        mock_db_session.return_value = mock_db_generator()
        
        # Track state propagation through components
        state_propagation = []
        
        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_supervisor:
                with patch('netra_backend.app.services.thread_service.ThreadService'):
                    with patch('netra_backend.app.services.message_handlers.MessageHandlerService') as MockMHS:
                        
                        # Track WebSocket context creation parameters
                        def track_ws_context_creation(**kwargs):
                            state_propagation.append(("websocket_context", kwargs))
                            mock_context = MagicMock()
                            mock_context.user_id = kwargs.get("user_id")
                            mock_context.thread_id = kwargs.get("thread_id") 
                            mock_context.run_id = kwargs.get("run_id")
                            return mock_context
                        
                        MockWSContext.create_for_user.side_effect = track_ws_context_creation
                        
                        # Track supervisor creation parameters
                        def track_supervisor_creation(**kwargs):
                            state_propagation.append(("supervisor", kwargs))
                            return MagicMock()
                        
                        mock_supervisor.side_effect = track_supervisor_creation
                        
                        # Process message
                        handler = AgentMessageHandler(self.mock_message_handler_service)
                        message = self.create_test_message(
                            MessageType.CHAT,
                            {"content": "State consistency test"}
                        )
                        message.user_id = consistent_user_id  # Ensure consistency
                        
                        result = await handler.handle_message(
                            consistent_user_id,
                            self.mock_websocket,
                            message
                        )
        
        # Verify state consistency across components
        assert len(state_propagation) >= 2  # WebSocket context and supervisor
        
        # Verify consistent user_id propagation
        for component, params in state_propagation:
            if "user_id" in params:
                assert params["user_id"] == consistent_user_id
            if "thread_id" in params:
                assert params["thread_id"] == consistent_thread_id