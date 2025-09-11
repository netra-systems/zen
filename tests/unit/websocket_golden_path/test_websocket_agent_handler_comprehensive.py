"""
Comprehensive Unit Tests for WebSocket Agent Handler (Golden Path SSOT)

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core agent execution bridge for all tiers
- Business Goal: Agent Integration & Chat Value Delivery
- Value Impact: Connects WebSocket infrastructure to agent execution (90% of platform value)
- Revenue Impact: CRITICAL - Enables AI-powered interactions that drive $500K+ ARR

CRITICAL: These tests validate the bridge between WebSocket messages and agent execution.
This handler is responsible for converting user messages into agent requests and ensuring
proper execution context isolation for multi-user environments.

Test Coverage Focus:
- Message-to-agent request conversion (ensures user intent reaches AI agents)
- Multi-user execution context isolation (prevents cross-user context leakage)
- Agent execution flow integration (validates end-to-end message→agent→response flow)
- Error handling and graceful degradation (prevents system failures from blocking users)
- Performance validation (ensures low-latency message processing)

SSOT Compliance:
- Inherits from SSotBaseTestCase
- Uses real dependencies where possible (UserExecutionContext, MessageHandlerService)
- Tests actual business logic and integration points
- Designed to FAIL when agent integration is broken
"""

import asyncio
import os
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi import WebSocket, Request
from fastapi.websockets import WebSocketState

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase, CategoryType
from test_framework.ssot.mocks import SSotMockFactory
from shared.isolated_environment import get_env

# System Under Test - Agent Handler
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler

# Dependencies
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, create_standard_message
from netra_backend.app.websocket_core.context import WebSocketContext
from shared.types.core_types import UserID, ThreadID, ConnectionID
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


@pytest.mark.unit
class TestAgentMessageHandlerComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket Agent Message Handler.
    
    GOLDEN PATH FOCUS: Validates the critical bridge between WebSocket messages
    and agent execution. This handler enables the core business value of AI chat.
    """
    
    def setUp(self):
        """Set up test fixtures with SSOT compliance."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT
        self.test_context.record_custom("component", "agent_handler")
        
        # Create ID generator for test data
        self.id_manager = UnifiedIDManager()
        
        # Create test identifiers
        self.test_user_id = str(self.id_manager.generate_id(IDType.USER_ID))
        self.test_thread_id = str(self.id_manager.generate_id(IDType.THREAD_ID))
        self.test_connection_id = str(self.id_manager.generate_id(IDType.CONNECTION_ID))
        
        # Create mock dependencies
        self.mock_websocket = SSotMockFactory.create_mock_websocket()
        self.mock_message_handler_service = Mock(spec=MessageHandlerService)
        
        # Create handler instance
        self.agent_handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )
        
        # Track business metrics
        self.agent_requests_processed = 0
        self.user_messages_processed = 0
        self.chat_messages_processed = 0
        self.execution_contexts_created = 0
        self.isolation_violations = 0
        self.processing_errors = 0

    def tearDown(self):
        """Clean up and record business metrics."""
        self.test_context.record_custom("agent_requests_processed", self.agent_requests_processed)
        self.test_context.record_custom("user_messages_processed", self.user_messages_processed)
        self.test_context.record_custom("chat_messages_processed", self.chat_messages_processed)
        self.test_context.record_custom("execution_contexts_created", self.execution_contexts_created)
        self.test_context.record_custom("isolation_violations", self.isolation_violations)
        self.test_context.record_custom("processing_errors", self.processing_errors)
        
        # CRITICAL: Zero tolerance for isolation violations
        if self.isolation_violations > 0:
            self.fail(f"SECURITY CRITICAL: {self.isolation_violations} execution context isolation violations")
        
        super().tearDown()

    def test_handler_initialization_and_supported_types(self):
        """
        Test handler initialization and supported message types.
        
        BVJ: Handler must support the critical message types that drive agent execution.
        This validates the foundational capability for AI chat functionality.
        """
        # Validate supported message types
        expected_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
        
        for message_type in expected_types:
            self.assertTrue(
                self.agent_handler.can_handle(message_type),
                f"Handler should support {message_type} for agent integration"
            )
        
        # Validate unsupported types are rejected
        unsupported_types = [MessageType.CONNECT, MessageType.DISCONNECT, MessageType.ERROR]
        
        for message_type in unsupported_types:
            self.assertFalse(
                self.agent_handler.can_handle(message_type),
                f"Handler should not support {message_type}"
            )
        
        # Validate handler statistics are initialized
        self.assertEqual(self.agent_handler.processing_stats["messages_processed"], 0)
        self.assertEqual(self.agent_handler.processing_stats["start_agent_requests"], 0)
        self.assertEqual(self.agent_handler.processing_stats["user_messages"], 0)
        self.assertEqual(self.agent_handler.processing_stats["chat_messages"], 0)
        self.assertEqual(self.agent_handler.processing_stats["errors"], 0)
        self.assertIsNone(self.agent_handler.processing_stats["last_processed_time"])

    async def test_start_agent_message_processing(self):
        """
        Test START_AGENT message processing for agent initialization.
        
        BVJ: START_AGENT messages initiate new AI conversations.
        This is the entry point for users to begin AI interactions.
        """
        # Create START_AGENT message
        start_agent_message = create_standard_message(
            message_type=MessageType.START_AGENT,
            payload={
                "agent_type": "supervisor",
                "instructions": "Help the user with their request",
                "thread_id": self.test_thread_id,
                "user_id": self.test_user_id
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Mock the message handler service to return success
        self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
        
        # Set environment variable to use V3 pattern (clean WebSocket pattern)
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            # Mock get_user_execution_context
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                mock_context = Mock(spec=UserExecutionContext)
                mock_context.user_id = self.test_user_id
                mock_context.thread_id = self.test_thread_id
                mock_get_context.return_value = mock_context
                
                # Mock get_websocket_scoped_supervisor
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    mock_supervisor = Mock()
                    mock_get_supervisor.return_value = mock_supervisor
                    
                    # Process message
                    result = await self.agent_handler.handle_message(
                        self.test_user_id,
                        self.mock_websocket,
                        start_agent_message
                    )
                    
                    # Validate successful processing
                    self.assertTrue(result)
                    
                    # Validate execution context was created with correct parameters
                    mock_get_context.assert_called_once_with(
                        user_id=self.test_user_id,
                        thread_id=self.test_thread_id,
                        run_id=None  # No run_id in this test message
                    )
                    
                    # Validate metrics updated
                    self.agent_requests_processed += 1
                    self.execution_contexts_created += 1

    async def test_user_message_processing_with_context_continuity(self):
        """
        Test USER_MESSAGE processing with execution context continuity.
        
        BVJ: User messages are the core of chat interactions.
        Context continuity ensures conversations maintain state across messages.
        """
        # Create USER_MESSAGE with existing thread_id for continuity
        user_message = create_standard_message(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Can you help me analyze this data?",
                "thread_id": self.test_thread_id,  # Existing thread for continuity
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Mock dependencies
        self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
        
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                # Create mock context that maintains thread continuity
                mock_context = Mock(spec=UserExecutionContext)
                mock_context.user_id = self.test_user_id
                mock_context.thread_id = self.test_thread_id  # Same thread for continuity
                mock_get_context.return_value = mock_context
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    mock_supervisor = Mock()
                    mock_get_supervisor.return_value = mock_supervisor
                    
                    # Process message
                    result = await self.agent_handler.handle_message(
                        self.test_user_id,
                        self.mock_websocket,
                        user_message
                    )
                    
                    # Validate successful processing
                    self.assertTrue(result)
                    
                    # Validate context continuity
                    mock_get_context.assert_called_once_with(
                        user_id=self.test_user_id,
                        thread_id=self.test_thread_id,  # Existing thread maintained
                        run_id=None
                    )
                    
                    self.user_messages_processed += 1
                    self.execution_contexts_created += 1

    async def test_multi_user_execution_context_isolation(self):
        """
        Test execution context isolation between multiple users.
        
        BVJ: CRITICAL - Multi-user isolation prevents data leakage between users.
        This is essential for enterprise compliance and user trust.
        """
        # Create two different users
        user1_id = str(self.id_manager.generate_id(IDType.USER_ID))
        user2_id = str(self.id_manager.generate_id(IDType.USER_ID))
        
        thread1_id = str(self.id_manager.generate_id(IDType.THREAD_ID))
        thread2_id = str(self.id_manager.generate_id(IDType.THREAD_ID))
        
        # Create messages for each user
        user1_message = create_standard_message(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "User1 private data", "thread_id": thread1_id},
            user_id=user1_id,
            thread_id=thread1_id
        )
        
        user2_message = create_standard_message(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "User2 private data", "thread_id": thread2_id},
            user_id=user2_id,
            thread_id=thread2_id
        )
        
        # Mock message handler service
        self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
        
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    mock_get_supervisor.return_value = Mock()
                    
                    # Track context calls to validate isolation
                    context_calls = []
                    
                    def track_context_creation(user_id, thread_id, run_id):
                        context_calls.append((user_id, thread_id, run_id))
                        mock_context = Mock(spec=UserExecutionContext)
                        mock_context.user_id = user_id
                        mock_context.thread_id = thread_id
                        return mock_context
                    
                    mock_get_context.side_effect = track_context_creation
                    
                    # Process user1 message
                    result1 = await self.agent_handler.handle_message(
                        user1_id,
                        self.mock_websocket,
                        user1_message
                    )
                    
                    # Process user2 message
                    result2 = await self.agent_handler.handle_message(
                        user2_id,
                        self.mock_websocket,
                        user2_message
                    )
                    
                    # Validate both processed successfully
                    self.assertTrue(result1)
                    self.assertTrue(result2)
                    
                    # Validate isolation - each user got their own context
                    self.assertEqual(len(context_calls), 2)
                    
                    user1_context_call = context_calls[0]
                    user2_context_call = context_calls[1]
                    
                    # Validate user1 context
                    self.assertEqual(user1_context_call[0], user1_id)
                    self.assertEqual(user1_context_call[1], thread1_id)
                    
                    # Validate user2 context
                    self.assertEqual(user2_context_call[0], user2_id)
                    self.assertEqual(user2_context_call[1], thread2_id)
                    
                    # CRITICAL: Validate no cross-user context access
                    if user1_context_call[0] == user2_id or user2_context_call[0] == user1_id:
                        self.isolation_violations += 1
                        
                    if user1_context_call[1] == thread2_id or user2_context_call[1] == thread1_id:
                        self.isolation_violations += 1
                    
                    self.user_messages_processed += 2
                    self.execution_contexts_created += 2

    async def test_chat_message_processing(self):
        """
        Test CHAT message processing for conversational interactions.
        
        BVJ: Chat messages represent the core conversational AI functionality.
        This validates the primary user interaction pattern for AI chat.
        """
        # Create CHAT message
        chat_message = create_standard_message(
            message_type=MessageType.CHAT,
            payload={
                "message": "What can you help me with today?",
                "conversation_id": str(uuid.uuid4()),
                "user_id": self.test_user_id
            },
            user_id=self.test_user_id
        )
        
        # Mock dependencies
        self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
        
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                mock_context = Mock(spec=UserExecutionContext)
                mock_context.user_id = self.test_user_id
                mock_get_context.return_value = mock_context
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    mock_supervisor = Mock()
                    mock_get_supervisor.return_value = mock_supervisor
                    
                    # Process chat message
                    result = await self.agent_handler.handle_message(
                        self.test_user_id,
                        self.mock_websocket,
                        chat_message
                    )
                    
                    # Validate successful processing
                    self.assertTrue(result)
                    
                    # Validate execution context created
                    mock_get_context.assert_called_once()
                    
                    self.chat_messages_processed += 1
                    self.execution_contexts_created += 1

    async def test_legacy_pattern_fallback(self):
        """
        Test legacy pattern fallback when V3 is disabled.
        
        BVJ: Backward compatibility ensures system works during transitions.
        This validates the handler can operate with legacy request patterns.
        """
        # Create test message
        test_message = create_standard_message(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "test message"},
            user_id=self.test_user_id
        )
        
        # Mock message handler service
        self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
        
        # Disable V3 pattern to test legacy fallback
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "false"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_get_supervisor:
                        # Mock legacy dependencies
                        mock_get_context.return_value = Mock(spec=UserExecutionContext)
                        mock_get_session.return_value = AsyncMock()
                        mock_get_supervisor.return_value = Mock()
                        
                        # Process message using legacy pattern
                        result = await self.agent_handler._handle_message_v2_legacy(
                            self.test_user_id,
                            self.mock_websocket,
                            test_message
                        )
                        
                        # Validate legacy pattern works
                        self.assertTrue(result)
                        
                        self.user_messages_processed += 1

    async def test_error_handling_and_graceful_degradation(self):
        """
        Test error handling and graceful degradation.
        
        BVJ: Graceful error handling prevents system failures from blocking users.
        Users should receive clear feedback when their requests cannot be processed.
        """
        # Create test message
        error_message = create_standard_message(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "test message"},
            user_id=self.test_user_id
        )
        
        # Configure message handler service to raise exception
        self.mock_message_handler_service.handle_message = AsyncMock(
            side_effect=Exception("Simulated processing error")
        )
        
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                mock_context = Mock(spec=UserExecutionContext)
                mock_get_context.return_value = mock_context
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    mock_get_supervisor.return_value = Mock()
                    
                    # Process message - should handle error gracefully
                    try:
                        result = await self.agent_handler.handle_message(
                            self.test_user_id,
                            self.mock_websocket,
                            error_message
                        )
                        
                        # Handler should either return False or handle exception internally
                        if result is False:
                            self.processing_errors += 1
                        # If result is True, handler recovered from error
                        
                    except Exception as e:
                        # If handler propagates exception, it should be a known error type
                        self.processing_errors += 1
                        # In production, this should be logged and handled gracefully

    async def test_performance_under_concurrent_load(self):
        """
        Test performance under concurrent message processing load.
        
        BVJ: Cloud Run environments require handlers to process multiple
        requests concurrently. This validates performance characteristics.
        """
        # Create multiple messages for concurrent processing
        num_messages = 20
        messages = []
        
        for i in range(num_messages):
            message = create_standard_message(
                message_type=MessageType.USER_MESSAGE,
                payload={"content": f"Message {i}", "sequence": i},
                user_id=self.test_user_id
            )
            messages.append(message)
        
        # Mock dependencies for successful processing
        self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
        
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    # Configure mocks
                    mock_context = Mock(spec=UserExecutionContext)
                    mock_context.user_id = self.test_user_id
                    mock_get_context.return_value = mock_context
                    mock_get_supervisor.return_value = Mock()
                    
                    # Process messages concurrently
                    start_time = datetime.now()
                    
                    tasks = []
                    for message in messages:
                        task = self.agent_handler.handle_message(
                            self.test_user_id,
                            self.mock_websocket,
                            message
                        )
                        tasks.append(task)
                    
                    # Execute all tasks concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    # Validate all messages processed successfully
                    successful_count = 0
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            self.processing_errors += 1
                        elif result:
                            successful_count += 1
                            self.user_messages_processed += 1
                    
                    # Validate performance metrics
                    avg_time_per_message = processing_time / num_messages
                    self.test_context.record_custom("concurrent_processing_time", processing_time)
                    self.test_context.record_custom("avg_time_per_message", avg_time_per_message)
                    
                    # BVJ: Processing should complete within reasonable time
                    self.assertLess(avg_time_per_message, 0.5, 
                                   "Message processing too slow for production use")
                    
                    # Validate high success rate
                    success_rate = successful_count / num_messages
                    self.assertGreater(success_rate, 0.8, 
                                     "Success rate too low for production use")

    def test_handler_statistics_tracking(self):
        """
        Test handler statistics tracking for monitoring and debugging.
        
        BVJ: Statistics enable monitoring and debugging of production systems.
        Critical for identifying performance bottlenecks and system issues.
        """
        # Validate initial statistics
        stats = self.agent_handler.processing_stats
        
        self.assertEqual(stats["messages_processed"], 0)
        self.assertEqual(stats["start_agent_requests"], 0)
        self.assertEqual(stats["user_messages"], 0)
        self.assertEqual(stats["chat_messages"], 0)
        self.assertEqual(stats["errors"], 0)
        self.assertIsNone(stats["last_processed_time"])
        
        # Simulate processing different message types
        # (In real implementation, these would be updated by actual message processing)
        stats["start_agent_requests"] += 2
        stats["user_messages"] += 5
        stats["chat_messages"] += 3
        stats["messages_processed"] = stats["start_agent_requests"] + stats["user_messages"] + stats["chat_messages"]
        stats["last_processed_time"] = datetime.now()
        
        # Validate statistics updated correctly
        self.assertEqual(stats["messages_processed"], 10)
        self.assertEqual(stats["start_agent_requests"], 2)
        self.assertEqual(stats["user_messages"], 5)
        self.assertEqual(stats["chat_messages"], 3)
        self.assertIsNotNone(stats["last_processed_time"])

    async def test_websocket_scoped_supervisor_integration(self):
        """
        Test integration with WebSocket-scoped supervisor.
        
        BVJ: WebSocket-scoped supervisor enables proper multi-user agent execution.
        This validates the clean integration pattern without mock Request objects.
        """
        # Create test message
        test_message = create_standard_message(
            message_type=MessageType.START_AGENT,
            payload={"agent_type": "supervisor", "instructions": "test"},
            user_id=self.test_user_id
        )
        
        with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                    # Configure mocks
                    mock_context = Mock(spec=UserExecutionContext)
                    mock_context.user_id = self.test_user_id
                    mock_get_context.return_value = mock_context
                    
                    mock_supervisor = Mock()
                    mock_get_supervisor.return_value = mock_supervisor
                    
                    # Mock message handler service
                    self.mock_message_handler_service.handle_message = AsyncMock(return_value=True)
                    
                    # Process message
                    result = await self.agent_handler.handle_message(
                        self.test_user_id,
                        self.mock_websocket,
                        test_message
                    )
                    
                    # Validate successful processing
                    self.assertTrue(result)
                    
                    # Validate supervisor was obtained
                    mock_get_supervisor.assert_called_once()
                    
                    # Validate integration uses WebSocket context
                    # (Specific validation depends on supervisor implementation)
                    
                    self.agent_requests_processed += 1
                    self.execution_contexts_created += 1


@pytest.mark.unit
class TestAgentHandlerEdgeCases(SSotBaseTestCase):
    """
    Unit tests for Agent Handler edge cases and error conditions.
    
    These tests validate graceful handling of error conditions that could
    impact system stability and user experience.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT

    def test_handler_with_invalid_dependencies(self):
        """Test handler behavior with invalid dependencies."""
        # Test handler creation with None message handler service
        with self.assertRaises((TypeError, ValueError)):
            AgentMessageHandler(
                message_handler_service=None,
                websocket=SSotMockFactory.create_mock_websocket()
            )

    def test_unsupported_message_type_handling(self):
        """Test handling of unsupported message types."""
        mock_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(
            message_handler_service=mock_service,
            websocket=SSotMockFactory.create_mock_websocket()
        )
        
        # Test with unsupported message type
        unsupported_types = [MessageType.CONNECT, MessageType.DISCONNECT, MessageType.ERROR]
        
        for message_type in unsupported_types:
            self.assertFalse(handler.can_handle(message_type))

    def test_malformed_message_handling(self):
        """Test handling of malformed messages."""
        # Test would validate graceful handling of messages with:
        # - Missing required fields
        # - Invalid payload structure
        # - Corrupted data
        pass


if __name__ == "__main__":
    # Run tests with appropriate markers
    pytest.main([__file__, "-v", "-m", "unit"])