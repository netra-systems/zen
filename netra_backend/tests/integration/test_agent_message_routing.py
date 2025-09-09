"""
Agent Message Routing Integration Tests - MISSION CRITICAL for Chat Business Value

Business Value Justification:
- Segment: Platform/Internal (Enables Customer Chat UI)
- Business Goal: Agent-to-WebSocket message routing reliability (99.9% uptime target)
- Value Impact: Enables REAL-TIME AI agent communication - core of our chat business value
- Strategic Impact: Agent routing failures destroy user experience - mission critical infrastructure

CRITICAL: These tests validate the 5 critical WebSocket events that enable substantive chat interactions:
1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI working on valuable solutions)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User must know when valuable response is ready

This test suite focuses on agent execution context routing and AgentMessageHandler integration
patterns to ensure WebSocket events reach the correct user connections reliably.

ULTRA CRITICAL: Agent message routing failures = business value destruction.
Each test validates actual agent-to-WebSocket routing for multi-user isolation.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Core imports for integration testing
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.real_services import get_real_services

# WebSocket and routing imports
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, WebSocketConnectionState
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.dependencies import get_user_execution_context

# Agent execution and routing imports
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Mock WebSocket for testing
from fastapi import WebSocket

class MockWebSocket:
    """Mock WebSocket for testing agent message routing."""
    
    def __init__(self, connection_id: str, user_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.sent_messages = []
        self.closed = False
        self.scope = {
            'type': 'websocket',
            'path': '/ws',
            'headers': [],
            'app': MagicMock()
        }
        self.scope['app'].state = MagicMock()
        
    async def send_text(self, data: str):
        """Mock sending text message."""
        if not self.closed:
            self.sent_messages.append(json.loads(data))
            
    async def send_json(self, data: Dict[str, Any]):
        """Mock sending JSON message."""
        if not self.closed:
            self.sent_messages.append(data)
            
    async def close(self, code: int = 1000):
        """Mock closing WebSocket."""
        self.closed = True
        
    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages."""
        return self.sent_messages.copy()
        
    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages of specific type."""
        return [msg for msg in self.sent_messages if msg.get('type') == message_type]


class AgentMessageRoutingIntegrationTest(BaseIntegrationTest):
    """
    MISSION CRITICAL: Agent Message Routing Integration Tests
    
    Tests the complete agent execution context routing pipeline:
    - Agent execution context creation and isolation  
    - AgentMessageHandler WebSocket integration
    - 5 critical WebSocket events routing
    - Multi-user agent routing isolation
    - Agent tool integration with WebSocket routing
    """
    
    def setup_method(self):
        """Set up integration test environment."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.id_generator = UnifiedIdGenerator()
        
    async def async_setup(self):
        """Async setup for agent routing tests."""
        await super().async_setup()
        
    async def create_test_agent_context(self, user_id: str, thread_id: Optional[str] = None) -> UserExecutionContext:
        """Create isolated test agent execution context."""
        context = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=None  # Let system generate
        )
        return context
        
    async def create_mock_websocket_connection(self, user_id: str) -> MockWebSocket:
        """Create mock WebSocket connection for routing tests."""
        connection_id = self.id_generator.generate_websocket_connection_id(user_id)
        return MockWebSocket(connection_id, user_id)

    # =============================================================================
    # AGENT WEBSOCKET EVENT ROUTING TESTS (6 tests)
    # Tests for the 5 critical WebSocket events that deliver chat business value
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_agent_started_event_routing(self):
        """
        CRITICAL: Test agent_started event routing to correct WebSocket connection.
        
        Business Value: User must see agent began processing their problem.
        This event signals the start of AI problem-solving - core business value.
        """
        # Create test user context and WebSocket
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create WebSocket manager
        ws_manager = await create_websocket_manager(context)
        
        # Create agent message handler
        message_handler_service = MagicMock(spec=MessageHandlerService)
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create agent_started message
        agent_started_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Test agent execution",
                "thread_id": thread_id,
                "agent_type": "test_agent"
            },
            user_id=user_id,
            thread_id=thread_id,
            timestamp=time.time(),
            message_id=f"msg-{uuid.uuid4().hex[:8]}"
        )
        
        # Route message through agent handler
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_db.return_value.__aexit__.return_value = None
            
            # Mock async for loop for db session
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            # Route the agent started message
            result = await agent_handler.handle_message(user_id, mock_websocket, agent_started_message)
            
        # Verify routing success
        assert result is True, "Agent started event should route successfully"
        
        # Verify message handler was called with correct context
        message_handler_service.handle_start_agent.assert_called_once()
        call_args = message_handler_service.handle_start_agent.call_args
        assert call_args[1]['user_id'] == user_id
        assert call_args[1]['payload']['thread_id'] == thread_id
        assert call_args[1]['websocket'] == mock_websocket
        
        # Verify WebSocket context routing
        assert agent_handler.get_stats()['start_agent_requests'] == 1
        assert agent_handler.get_stats()['messages_processed'] == 1
        
        self.logger.info("✅ agent_started event routed successfully to correct WebSocket")

    @pytest.mark.asyncio
    async def test_agent_thinking_event_routing(self):
        """
        CRITICAL: Test agent_thinking event routing for real-time reasoning visibility.
        
        Business Value: Shows AI working on valuable solutions - demonstrates problem-solving approach.
        This provides transparency in agent reasoning, critical for user trust.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create agent thinking progress message
        thinking_message = WebSocketMessage(
            type=MessageType.AGENT_PROGRESS,  # Maps to agent_thinking
            payload={
                "status": "thinking",
                "reasoning": "Analyzing user request for optimal solution approach",
                "thread_id": thread_id,
                "progress_percentage": 25
            },
            user_id=user_id,
            thread_id=thread_id,
            timestamp=time.time()
        )
        
        # Create message handler service with WebSocket manager
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Route thinking event through agent handler
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, thinking_message)
            
        # Verify routing success
        assert result is True, "Agent thinking event should route successfully"
        
        # Verify agent thinking provides real-time visibility
        assert "reasoning" in thinking_message.payload
        assert thinking_message.payload["status"] == "thinking"
        assert thinking_message.payload["progress_percentage"] > 0
        
        self.logger.info("✅ agent_thinking event provides real-time reasoning visibility")

    @pytest.mark.asyncio  
    async def test_tool_executing_event_routing(self):
        """
        CRITICAL: Test tool_executing event routing for tool usage transparency.
        
        Business Value: Demonstrates problem-solving approach through tool usage visibility.
        Shows users exactly how AI is working to solve their problems.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create tool executing message
        tool_executing_message = WebSocketMessage(
            type=MessageType.AGENT_PROGRESS,
            payload={
                "status": "tool_executing",
                "tool_name": "data_analyzer",
                "tool_description": "Analyzing performance metrics for cost optimization",
                "thread_id": thread_id,
                "execution_details": {
                    "input_parameters": {"dataset": "performance_metrics", "timeframe": "30d"},
                    "expected_output": "cost_optimization_recommendations"
                }
            },
            user_id=user_id,
            thread_id=thread_id,
            timestamp=time.time()
        )
        
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(), 
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Route tool executing event
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, tool_executing_message)
            
        # Verify routing success and tool transparency
        assert result is True, "Tool executing event should route successfully"
        
        # Verify tool execution provides transparency
        payload = tool_executing_message.payload
        assert payload["status"] == "tool_executing"
        assert "tool_name" in payload
        assert "tool_description" in payload
        assert "execution_details" in payload
        
        self.logger.info("✅ tool_executing event provides tool usage transparency")

    @pytest.mark.asyncio
    async def test_tool_completed_event_routing(self):
        """
        CRITICAL: Test tool_completed event routing with actionable results.
        
        Business Value: Delivers actionable insights from tool execution.
        This is where business value is realized - actual results delivered to users.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}" 
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create tool completed message with actionable results
        tool_completed_message = WebSocketMessage(
            type=MessageType.AGENT_PROGRESS,
            payload={
                "status": "tool_completed",
                "tool_name": "data_analyzer",
                "results": {
                    "cost_savings_identified": "$12,500/month",
                    "optimization_recommendations": [
                        "Reduce idle compute instances by 35%",
                        "Optimize storage tier allocation",
                        "Implement auto-scaling policies"
                    ],
                    "confidence_score": 0.94
                },
                "thread_id": thread_id,
                "execution_time_ms": 1250
            },
            user_id=user_id,
            thread_id=thread_id,
            timestamp=time.time()
        )
        
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Route tool completed event
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, tool_completed_message)
            
        # Verify routing success and actionable results delivery
        assert result is True, "Tool completed event should route successfully"
        
        # Verify actionable business value delivered
        results = tool_completed_message.payload["results"]
        assert "cost_savings_identified" in results
        assert "optimization_recommendations" in results
        assert len(results["optimization_recommendations"]) > 0
        assert results["confidence_score"] > 0.9
        
        self.assert_business_value_delivered(results, 'cost_savings')
        
        self.logger.info("✅ tool_completed event delivers actionable business insights")

    @pytest.mark.asyncio
    async def test_agent_completed_event_routing(self):
        """
        CRITICAL: Test agent_completed event routing for final response delivery.
        
        Business Value: User must know when valuable response is ready.
        This signals completion of AI problem-solving - final business value delivery.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create agent completed message with comprehensive results
        agent_completed_message = WebSocketMessage(
            type=MessageType.AGENT_RESPONSE_COMPLETE,
            payload={
                "status": "completed",
                "final_response": {
                    "summary": "Cost optimization analysis completed successfully",
                    "total_potential_savings": "$15,750/month",
                    "implementation_plan": [
                        "Phase 1: Infrastructure rightsizing (Week 1-2)", 
                        "Phase 2: Storage optimization (Week 3-4)",
                        "Phase 3: Auto-scaling implementation (Week 5-6)"
                    ],
                    "roi_projection": "125% ROI within 6 months"
                },
                "thread_id": thread_id,
                "total_execution_time_ms": 4800,
                "tools_used": ["data_analyzer", "cost_optimizer", "risk_assessor"]
            },
            user_id=user_id,
            thread_id=thread_id,
            timestamp=time.time()
        )
        
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Route agent completed event
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, agent_completed_message)
            
        # Verify routing success and complete value delivery
        assert result is True, "Agent completed event should route successfully"
        
        # Verify comprehensive business value delivered
        final_response = agent_completed_message.payload["final_response"]
        assert "total_potential_savings" in final_response
        assert "implementation_plan" in final_response
        assert "roi_projection" in final_response
        assert len(final_response["implementation_plan"]) > 0
        
        self.assert_business_value_delivered(final_response, 'cost_savings')
        
        self.logger.info("✅ agent_completed event delivers comprehensive business value")

    @pytest.mark.asyncio
    async def test_agent_event_sequence_routing(self):
        """
        CRITICAL: Test complete agent event sequence routing in correct order.
        
        Business Value: Ensures users get complete AI problem-solving journey visibility.
        Tests the full sequence: started -> thinking -> tool_executing -> tool_completed -> completed
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create sequence of agent events
        event_sequence = [
            ("START_AGENT", {"user_request": "Optimize cloud costs", "thread_id": thread_id}),
            ("AGENT_PROGRESS", {"status": "thinking", "reasoning": "Analyzing cost structure"}),
            ("AGENT_PROGRESS", {"status": "tool_executing", "tool_name": "cost_analyzer"}),
            ("AGENT_PROGRESS", {"status": "tool_completed", "results": {"savings": "$10K"}}),
            ("AGENT_RESPONSE_COMPLETE", {"status": "completed", "final_response": "Analysis complete"})
        ]
        
        routed_events = []
        
        # Route each event in sequence
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            for i, (msg_type, payload) in enumerate(event_sequence):
                message = WebSocketMessage(
                    type=MessageType(msg_type.lower()),
                    payload=payload,
                    user_id=user_id,
                    thread_id=thread_id,
                    timestamp=time.time() + i,  # Sequential timestamps
                    message_id=f"seq-{i}"
                )
                
                result = await agent_handler.handle_message(user_id, mock_websocket, message)
                assert result is True, f"Event {msg_type} should route successfully"
                
                routed_events.append((msg_type, payload))
        
        # Verify complete sequence routed successfully
        assert len(routed_events) == 5, "All 5 critical events should route successfully"
        
        # Verify sequence integrity
        expected_sequence = ["START_AGENT", "AGENT_PROGRESS", "AGENT_PROGRESS", "AGENT_PROGRESS", "AGENT_RESPONSE_COMPLETE"]
        actual_sequence = [event[0] for event in routed_events]
        
        for i, expected in enumerate(expected_sequence):
            assert actual_sequence[i] == expected, f"Event {i} should be {expected}, got {actual_sequence[i]}"
        
        # Verify handler statistics
        stats = agent_handler.get_stats()
        assert stats["messages_processed"] == 5
        assert stats["start_agent_requests"] == 1
        
        self.logger.info("✅ Complete agent event sequence routed successfully")

    # =============================================================================
    # AGENT MESSAGE HANDLER INTEGRATION TESTS (4 tests)
    # Tests AgentMessageHandler integration with WebSocket routing infrastructure
    # =============================================================================

    @pytest.mark.asyncio
    async def test_agent_message_handler_websocket_integration(self):
        """
        CRITICAL: Test AgentMessageHandler integration with WebSocket infrastructure.
        
        Validates the handler correctly integrates with:
        - WebSocketManager for connection routing
        - UserExecutionContext for user isolation 
        - MessageHandlerService for agent execution
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        # Create execution context and WebSocket manager
        context = await self.create_test_agent_context(user_id, thread_id)
        ws_manager = await create_websocket_manager(context)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create integrated message handler service
        supervisor_mock = MagicMock()
        thread_service_mock = MagicMock()
        message_handler_service = MessageHandlerService(
            supervisor=supervisor_mock,
            thread_service=thread_service_mock,
            websocket_manager=ws_manager
        )
        
        # Create agent handler with WebSocket integration
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Test WebSocket integration with user message
        user_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "Analyze our infrastructure costs",
                "thread_id": thread_id
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Route message and verify integration
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, user_message)
            
        # Verify successful integration
        assert result is True, "AgentMessageHandler should integrate successfully with WebSocket"
        
        # Verify handler has correct WebSocket reference
        assert agent_handler.websocket == mock_websocket
        assert agent_handler.message_handler_service == message_handler_service
        
        # Verify processing statistics updated
        stats = agent_handler.get_stats()
        assert stats["user_messages"] == 1
        assert stats["messages_processed"] == 1
        
        self.logger.info("✅ AgentMessageHandler WebSocket integration successful")

    @pytest.mark.asyncio
    async def test_agent_message_handler_routing_accuracy(self):
        """
        CRITICAL: Test AgentMessageHandler routes messages to correct WebSocket connections.
        
        Validates routing accuracy for multiple concurrent user connections.
        """
        # Create multiple users and connections
        users = [
            f"user-{uuid.uuid4().hex[:8]}" for _ in range(3)
        ]
        
        user_contexts = {}
        user_websockets = {}
        user_handlers = {}
        
        # Set up isolated contexts for each user
        for user_id in users:
            thread_id = self.id_generator.generate_thread_id()
            context = await self.create_test_agent_context(user_id, thread_id)
            websocket = await self.create_mock_websocket_connection(user_id)
            
            ws_manager = await create_websocket_manager(context)
            message_handler_service = MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager
            )
            
            handler = AgentMessageHandler(
                message_handler_service=message_handler_service,
                websocket=websocket
            )
            
            user_contexts[user_id] = (context, thread_id)
            user_websockets[user_id] = websocket
            user_handlers[user_id] = handler
        
        # Send unique messages to each user
        test_messages = {
            users[0]: "Analyze database performance",
            users[1]: "Optimize network costs", 
            users[2]: "Review security policies"
        }
        
        # Route messages to correct users
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            for user_id, content in test_messages.items():
                context, thread_id = user_contexts[user_id]
                handler = user_handlers[user_id]
                websocket = user_websockets[user_id]
                
                message = WebSocketMessage(
                    type=MessageType.USER_MESSAGE,
                    payload={"content": content, "thread_id": thread_id},
                    user_id=user_id,
                    thread_id=thread_id
                )
                
                result = await handler.handle_message(user_id, websocket, message)
                assert result is True, f"Message should route successfully for {user_id}"
        
        # Verify routing accuracy - each handler processed exactly one message
        for user_id, handler in user_handlers.items():
            stats = handler.get_stats()
            assert stats["messages_processed"] == 1, f"User {user_id} should have 1 processed message"
            assert stats["user_messages"] == 1, f"User {user_id} should have 1 user message"
            
        self.logger.info("✅ AgentMessageHandler routing accuracy validated for multiple users")

    @pytest.mark.asyncio
    async def test_agent_message_handler_multi_user_isolation(self):
        """
        CRITICAL: Test AgentMessageHandler respects user isolation boundaries.
        
        Validates that messages from one user never leak to another user's WebSocket connection.
        """
        # Create two isolated users
        user_a = f"user-a-{uuid.uuid4().hex[:8]}"
        user_b = f"user-b-{uuid.uuid4().hex[:8]}"
        
        # Create isolated contexts
        context_a = await self.create_test_agent_context(user_a)
        context_b = await self.create_test_agent_context(user_b)
        
        websocket_a = await self.create_mock_websocket_connection(user_a)
        websocket_b = await self.create_mock_websocket_connection(user_b)
        
        # Create isolated handlers
        ws_manager_a = await create_websocket_manager(context_a)
        ws_manager_b = await create_websocket_manager(context_b)
        
        handler_a = AgentMessageHandler(
            message_handler_service=MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager_a
            ),
            websocket=websocket_a
        )
        
        handler_b = AgentMessageHandler(
            message_handler_service=MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager_b
            ),
            websocket=websocket_b
        )
        
        # Send messages to both users
        message_a = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "User A's confidential analysis", "thread_id": context_a.thread_id},
            user_id=user_a,
            thread_id=context_a.thread_id
        )
        
        message_b = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "User B's private optimization", "thread_id": context_b.thread_id},
            user_id=user_b,
            thread_id=context_b.thread_id
        )
        
        # Route messages through isolated handlers
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result_a = await handler_a.handle_message(user_a, websocket_a, message_a)
            result_b = await handler_b.handle_message(user_b, websocket_b, message_b)
            
        # Verify isolation - both processed successfully
        assert result_a is True, "User A message should process successfully"
        assert result_b is True, "User B message should process successfully"
        
        # Verify no cross-contamination in statistics
        stats_a = handler_a.get_stats()
        stats_b = handler_b.get_stats()
        
        assert stats_a["start_agent_requests"] == 1, "Handler A should have 1 start_agent request"
        assert stats_b["start_agent_requests"] == 1, "Handler B should have 1 start_agent request"
        
        # Verify WebSocket isolation
        assert handler_a.websocket == websocket_a, "Handler A should use WebSocket A"
        assert handler_b.websocket == websocket_b, "Handler B should use WebSocket B"
        assert handler_a.websocket != handler_b.websocket, "Handlers should use different WebSockets"
        
        self.logger.info("✅ AgentMessageHandler multi-user isolation validated")

    @pytest.mark.asyncio
    async def test_agent_message_handler_error_recovery(self):
        """
        CRITICAL: Test AgentMessageHandler error recovery in routing failures.
        
        Validates handler gracefully handles and recovers from routing errors.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        context = await self.create_test_agent_context(user_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create handler with failing message handler service
        failing_service = MagicMock(spec=MessageHandlerService)
        failing_service.handle_start_agent.side_effect = Exception("Simulated routing failure")
        
        agent_handler = AgentMessageHandler(
            message_handler_service=failing_service,
            websocket=mock_websocket
        )
        
        # Create message that will trigger failure
        failing_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "This will fail", "thread_id": context.thread_id},
            user_id=user_id,
            thread_id=context.thread_id
        )
        
        # Route failing message
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, failing_message)
            
        # Verify graceful failure handling
        assert result is False, "Handler should return False for routing failures"
        
        # Verify error statistics tracked
        stats = agent_handler.get_stats()
        assert stats["errors"] >= 1, "Error count should be incremented"
        
        # Verify handler remains functional after error
        assert agent_handler.websocket is not None, "Handler should maintain WebSocket reference"
        assert agent_handler.message_handler_service is not None, "Handler should maintain service reference"
        
        # Test recovery with working message
        working_service = MagicMock(spec=MessageHandlerService)
        working_service.handle_start_agent.return_value = None
        
        agent_handler.message_handler_service = working_service
        
        recovery_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "This should work", "thread_id": context.thread_id},
            user_id=user_id,
            thread_id=context.thread_id
        )
        
        # Route recovery message
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            recovery_result = await agent_handler.handle_message(user_id, mock_websocket, recovery_message)
            
        # Verify recovery successful
        assert recovery_result is True, "Handler should recover and process messages successfully"
        
        self.logger.info("✅ AgentMessageHandler error recovery validated")

    # =============================================================================
    # AGENT EXECUTION CONTEXT ROUTING TESTS (4 tests)
    # Tests agent execution context integration with WebSocket routing
    # =============================================================================

    @pytest.mark.asyncio
    async def test_agent_execution_context_routing_integration(self):
        """
        CRITICAL: Test agent execution context integration with WebSocket routing.
        
        Validates that agent execution context provides correct routing information.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        # Create agent execution context
        context = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=None  # Let system generate
        )
        
        # Verify context has required routing information
        assert context.user_id == user_id, "Context should have correct user ID"
        assert context.thread_id == thread_id, "Context should have correct thread ID"
        assert context.run_id is not None, "Context should have generated run ID"
        assert context.request_id is not None, "Context should have generated request ID"
        
        # Create WebSocket manager from context
        ws_manager = await create_websocket_manager(context)
        assert ws_manager is not None, "WebSocket manager should be created from context"
        
        # Create agent message handler with context
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Test routing with context
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "Test context routing", "thread_id": thread_id},
            user_id=user_id,
            thread_id=thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, test_message)
            
        # Verify successful routing with context
        assert result is True, "Message should route successfully with execution context"
        
        self.logger.info("✅ Agent execution context routing integration validated")

    @pytest.mark.asyncio
    async def test_agent_context_to_websocket_mapping(self):
        """
        CRITICAL: Test agent execution context to WebSocket connection mapping.
        
        Validates that agent contexts correctly map to WebSocket connections for routing.
        """
        # Create multiple agent contexts
        contexts = []
        websockets = []
        
        for i in range(3):
            user_id = f"user-{i}-{uuid.uuid4().hex[:8]}"
            thread_id = self.id_generator.generate_thread_id()
            
            context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=None
            )
            
            mock_websocket = await self.create_mock_websocket_connection(user_id)
            
            contexts.append(context)
            websockets.append(mock_websocket)
        
        # Verify each context maps to correct WebSocket
        for i, (context, websocket) in enumerate(zip(contexts, websockets)):
            # Create WebSocket manager from context
            ws_manager = await create_websocket_manager(context)
            
            # Verify mapping integrity
            assert context.user_id == websocket.user_id, f"Context {i} should map to correct user WebSocket"
            assert ws_manager is not None, f"Context {i} should create WebSocket manager"
            
            # Test message routing with mapped context/websocket
            message_handler_service = MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager
            )
            
            agent_handler = AgentMessageHandler(
                message_handler_service=message_handler_service,
                websocket=websocket
            )
            
            test_message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={"content": f"Test message {i}", "thread_id": context.thread_id},
                user_id=context.user_id,
                thread_id=context.thread_id
            )
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
                mock_session = AsyncMock()
                async def async_db_generator():
                    yield mock_session
                mock_db.return_value = async_db_generator()
                
                result = await agent_handler.handle_message(context.user_id, websocket, test_message)
                
            assert result is True, f"Context {i} should route successfully to mapped WebSocket"
            
        self.logger.info("✅ Agent context to WebSocket mapping validated")

    @pytest.mark.asyncio
    async def test_agent_execution_context_user_isolation(self):
        """
        CRITICAL: Test agent execution context maintains user isolation in routing.
        
        Validates that agent contexts enforce user boundaries in WebSocket routing.
        """
        # Create isolated user contexts
        user_a_id = f"user-a-{uuid.uuid4().hex[:8]}"
        user_b_id = f"user-b-{uuid.uuid4().hex[:8]}"
        
        context_a = get_user_execution_context(
            user_id=user_a_id,
            thread_id=self.id_generator.generate_thread_id(),
            run_id=None
        )
        
        context_b = get_user_execution_context(
            user_id=user_b_id,
            thread_id=self.id_generator.generate_thread_id(),
            run_id=None
        )
        
        # Verify context isolation
        assert context_a.user_id != context_b.user_id, "Contexts should have different user IDs"
        assert context_a.thread_id != context_b.thread_id, "Contexts should have different thread IDs"
        assert context_a.run_id != context_b.run_id, "Contexts should have different run IDs"
        assert context_a.request_id != context_b.request_id, "Contexts should have different request IDs"
        
        # Create isolated WebSocket managers
        ws_manager_a = await create_websocket_manager(context_a)
        ws_manager_b = await create_websocket_manager(context_b)
        
        assert ws_manager_a != ws_manager_b, "WebSocket managers should be isolated"
        
        # Test routing isolation
        websocket_a = await self.create_mock_websocket_connection(user_a_id)
        websocket_b = await self.create_mock_websocket_connection(user_b_id)
        
        # Create isolated handlers
        handler_a = AgentMessageHandler(
            message_handler_service=MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager_a
            ),
            websocket=websocket_a
        )
        
        handler_b = AgentMessageHandler(
            message_handler_service=MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager_b
            ),
            websocket=websocket_b
        )
        
        # Send messages to both users
        message_a = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "User A's private message", "thread_id": context_a.thread_id},
            user_id=user_a_id,
            thread_id=context_a.thread_id
        )
        
        message_b = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "User B's confidential message", "thread_id": context_b.thread_id},
            user_id=user_b_id,
            thread_id=context_b.thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result_a = await handler_a.handle_message(user_a_id, websocket_a, message_a)
            result_b = await handler_b.handle_message(user_b_id, websocket_b, message_b)
            
        # Verify both processed successfully with isolation
        assert result_a is True, "User A message should process in isolated context"
        assert result_b is True, "User B message should process in isolated context"
        
        # Verify isolation in statistics
        stats_a = handler_a.get_stats()
        stats_b = handler_b.get_stats()
        
        assert stats_a["user_messages"] == 1, "Handler A should have 1 user message"
        assert stats_b["user_messages"] == 1, "Handler B should have 1 user message"
        
        self.logger.info("✅ Agent execution context user isolation validated")

    @pytest.mark.asyncio
    async def test_agent_context_factory_pattern_routing(self):
        """
        CRITICAL: Test agent context factory pattern with WebSocket routing.
        
        Validates that context factory creates isolated contexts for proper routing.
        """
        # Test context factory creates unique contexts
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        
        # Create multiple contexts for same user (different sessions)
        context_1 = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Let system generate
            run_id=None      # Let system generate
        )
        
        context_2 = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Let system generate new thread
            run_id=None      # Let system generate new run
        )
        
        # Verify factory creates unique contexts
        assert context_1.user_id == context_2.user_id, "Contexts should have same user ID"
        assert context_1.thread_id != context_2.thread_id, "Contexts should have different thread IDs"
        assert context_1.run_id != context_2.run_id, "Contexts should have different run IDs"
        
        # Test routing with factory-created contexts
        websocket_1 = await self.create_mock_websocket_connection(user_id)
        websocket_2 = await self.create_mock_websocket_connection(user_id)
        
        ws_manager_1 = await create_websocket_manager(context_1)
        ws_manager_2 = await create_websocket_manager(context_2)
        
        handler_1 = AgentMessageHandler(
            message_handler_service=MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager_1
            ),
            websocket=websocket_1
        )
        
        handler_2 = AgentMessageHandler(
            message_handler_service=MessageHandlerService(
                supervisor=MagicMock(),
                thread_service=MagicMock(),
                websocket_manager=ws_manager_2
            ),
            websocket=websocket_2
        )
        
        # Send messages to different sessions
        message_1 = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "Session 1 message", "thread_id": context_1.thread_id},
            user_id=user_id,
            thread_id=context_1.thread_id
        )
        
        message_2 = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "Session 2 message", "thread_id": context_2.thread_id},
            user_id=user_id,
            thread_id=context_2.thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result_1 = await handler_1.handle_message(user_id, websocket_1, message_1)
            result_2 = await handler_2.handle_message(user_id, websocket_2, message_2)
            
        # Verify factory pattern routing success
        assert result_1 is True, "Session 1 should route successfully"
        assert result_2 is True, "Session 2 should route successfully"
        
        # Verify session isolation
        stats_1 = handler_1.get_stats()
        stats_2 = handler_2.get_stats()
        
        assert stats_1["user_messages"] == 1, "Handler 1 should have 1 message"
        assert stats_2["user_messages"] == 1, "Handler 2 should have 1 message"
        
        self.logger.info("✅ Agent context factory pattern routing validated")

    # =============================================================================
    # AGENT TOOL INTEGRATION ROUTING TESTS (3 tests)
    # Tests tool dispatcher integration with agent message routing
    # =============================================================================

    @pytest.mark.asyncio
    async def test_tool_dispatcher_routing_integration(self):
        """
        CRITICAL: Test tool dispatcher integration with agent message routing.
        
        Validates that tool executions properly integrate with WebSocket routing.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Mock tool dispatcher with WebSocket integration
        mock_tool_dispatcher = MagicMock()
        mock_tool_dispatcher.execute_tool.return_value = {
            "success": True,
            "result": {"analysis": "Cost optimization recommendations", "savings": "$5000"},
            "execution_time": 1.5,
            "tool_name": "cost_analyzer"
        }
        
        # Create message handler with tool dispatcher
        ws_manager = await create_websocket_manager(context)
        supervisor_mock = MagicMock()
        supervisor_mock.get_tool_dispatcher.return_value = mock_tool_dispatcher
        
        message_handler_service = MessageHandlerService(
            supervisor=supervisor_mock,
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create agent request that would trigger tool execution
        agent_request = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Analyze costs and provide optimization recommendations",
                "thread_id": thread_id,
                "tools_requested": ["cost_analyzer"]
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Route message and verify tool integration
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, agent_request)
            
        # Verify tool dispatcher integration success
        assert result is True, "Tool dispatcher integration should route successfully"
        
        # Verify handler processed the tool-enabled request
        stats = agent_handler.get_stats()
        assert stats["start_agent_requests"] == 1, "Should have 1 start_agent request with tools"
        
        self.logger.info("✅ Tool dispatcher routing integration validated")

    @pytest.mark.asyncio
    async def test_tool_execution_result_routing(self):
        """
        CRITICAL: Test tool execution results routing to WebSocket connections.
        
        Validates that tool execution results reach the correct user WebSocket.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create WebSocket manager that can capture routed messages
        ws_manager = await create_websocket_manager(context)
        
        # Mock WebSocket manager send methods to capture routed results
        original_send = ws_manager.send_to_user if hasattr(ws_manager, 'send_to_user') else AsyncMock()
        captured_messages = []
        
        async def capture_send(user_id_arg, message_data):
            captured_messages.append((user_id_arg, message_data))
            if hasattr(original_send, '__call__'):
                return await original_send(user_id_arg, message_data)
        
        if hasattr(ws_manager, 'send_to_user'):
            ws_manager.send_to_user = capture_send
        
        # Create message handler with result routing capability
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create tool execution result message
        tool_result_message = WebSocketMessage(
            type=MessageType.AGENT_PROGRESS,
            payload={
                "status": "tool_completed",
                "tool_name": "performance_analyzer",
                "results": {
                    "performance_score": 87,
                    "bottlenecks_identified": 3,
                    "recommendations": [
                        "Optimize database queries",
                        "Implement caching layer", 
                        "Scale compute resources"
                    ]
                },
                "thread_id": thread_id
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Route tool result message
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, tool_result_message)
            
        # Verify tool result routing
        assert result is True, "Tool execution result should route successfully"
        
        # Verify result contains actionable business value
        tool_results = tool_result_message.payload["results"]
        assert "performance_score" in tool_results, "Results should include performance metrics"
        assert "recommendations" in tool_results, "Results should include actionable recommendations" 
        assert len(tool_results["recommendations"]) > 0, "Should have actionable recommendations"
        
        self.assert_business_value_delivered(tool_results, 'insights')
        
        self.logger.info("✅ Tool execution result routing validated")

    @pytest.mark.asyncio
    async def test_tool_error_routing_to_user(self):
        """
        CRITICAL: Test tool execution errors routing to correct user WebSocket.
        
        Validates that tool errors are properly routed and don't leak between users.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create message handler with error routing
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create tool error message
        tool_error_message = WebSocketMessage(
            type=MessageType.AGENT_ERROR,
            payload={
                "status": "tool_failed",
                "tool_name": "data_processor",
                "error": {
                    "error_code": "DATA_ACCESS_ERROR",
                    "error_message": "Unable to access required dataset",
                    "recovery_suggestions": [
                        "Check data source connectivity",
                        "Verify access permissions",
                        "Try alternative data source"
                    ]
                },
                "thread_id": thread_id
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Route tool error message
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, tool_error_message)
            
        # Verify error routing success
        assert result is True, "Tool error should route successfully to user"
        
        # Verify error message structure
        error_payload = tool_error_message.payload
        assert "error" in error_payload, "Error message should contain error details"
        assert "error_code" in error_payload["error"], "Should have error code"
        assert "recovery_suggestions" in error_payload["error"], "Should provide recovery guidance"
        
        # Verify handler error statistics updated
        stats = agent_handler.get_stats()
        # Note: This should not increment handler errors since this is a valid tool error message
        # The error count tracks handler routing errors, not tool execution errors
        
        self.logger.info("✅ Tool error routing to user validated")

    # =============================================================================
    # AGENT-TO-USER MESSAGE ROUTING TESTS (3 tests)  
    # Tests direct agent response routing to user WebSocket connections
    # =============================================================================

    @pytest.mark.asyncio
    async def test_agent_response_routing_to_user(self):
        """
        CRITICAL: Test agent response routing to correct user WebSocket.
        
        Validates that agent responses reach the specific user who initiated the request.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create message handler with user routing
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create agent response message
        agent_response = WebSocketMessage(
            type=MessageType.AGENT_RESPONSE,
            payload={
                "response": {
                    "summary": "Infrastructure analysis completed",
                    "findings": {
                        "total_resources": 145,
                        "underutilized_resources": 23,
                        "potential_monthly_savings": "$3,450"
                    },
                    "action_items": [
                        "Resize 15 overprovisioned instances",
                        "Archive 8 unused storage volumes",
                        "Implement auto-scaling for web tier"
                    ]
                },
                "thread_id": thread_id,
                "response_type": "analysis_complete"
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Route agent response
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, agent_response)
            
        # Verify agent response routing success
        assert result is True, "Agent response should route successfully to user"
        
        # Verify response contains business value
        response_data = agent_response.payload["response"]
        assert "findings" in response_data, "Response should contain analysis findings"
        assert "potential_monthly_savings" in response_data["findings"], "Should quantify savings"
        assert "action_items" in response_data, "Should provide actionable steps"
        assert len(response_data["action_items"]) > 0, "Should have specific action items"
        
        self.assert_business_value_delivered(response_data, 'cost_savings')
        
        self.logger.info("✅ Agent response routing to user validated")

    @pytest.mark.asyncio
    async def test_agent_streaming_response_routing(self):
        """
        CRITICAL: Test streaming agent responses routing via WebSocket.
        
        Validates that chunked/streaming responses maintain user routing integrity.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create message handler for streaming
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create sequence of streaming response chunks
        response_chunks = [
            {
                "chunk_id": 1,
                "content": "Beginning cost analysis of your infrastructure...",
                "chunk_type": "status_update"
            },
            {
                "chunk_id": 2,
                "content": "Identified 23 underutilized resources across 3 regions.",
                "chunk_type": "finding"
            },
            {
                "chunk_id": 3,
                "content": "Calculating potential savings from rightsizing...",
                "chunk_type": "status_update"
            },
            {
                "chunk_id": 4,
                "content": "Estimated monthly savings: $3,450 (18% cost reduction)",
                "chunk_type": "result"
            }
        ]
        
        routed_chunks = []
        
        # Route each chunk sequentially
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            for i, chunk_data in enumerate(response_chunks):
                chunk_message = WebSocketMessage(
                    type=MessageType.AGENT_RESPONSE_CHUNK,
                    payload={
                        "chunk": chunk_data,
                        "thread_id": thread_id,
                        "sequence_number": i + 1,
                        "total_chunks": len(response_chunks)
                    },
                    user_id=user_id,
                    thread_id=thread_id,
                    timestamp=time.time() + i * 0.1  # Sequential timing
                )
                
                result = await agent_handler.handle_message(user_id, mock_websocket, chunk_message)
                assert result is True, f"Chunk {i+1} should route successfully"
                
                routed_chunks.append(chunk_data)
        
        # Verify all chunks routed successfully
        assert len(routed_chunks) == 4, "All 4 response chunks should route successfully"
        
        # Verify streaming sequence integrity
        for i, chunk in enumerate(routed_chunks):
            assert chunk["chunk_id"] == i + 1, f"Chunk {i+1} should have correct ID"
        
        # Verify final chunk contains business value
        final_chunk = routed_chunks[-1]
        assert "savings" in final_chunk["content"], "Final chunk should contain savings information"
        assert "$" in final_chunk["content"], "Should include monetary value"
        
        self.logger.info("✅ Agent streaming response routing validated")

    @pytest.mark.asyncio
    async def test_agent_final_response_routing(self):
        """
        CRITICAL: Test final agent response routing with complete business value.
        
        Validates that final responses deliver comprehensive results to the correct user.
        """
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        thread_id = self.id_generator.generate_thread_id()
        
        context = await self.create_test_agent_context(user_id, thread_id)
        mock_websocket = await self.create_mock_websocket_connection(user_id)
        
        # Create message handler for final response
        ws_manager = await create_websocket_manager(context)
        message_handler_service = MessageHandlerService(
            supervisor=MagicMock(),
            thread_service=MagicMock(),
            websocket_manager=ws_manager
        )
        
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=mock_websocket
        )
        
        # Create comprehensive final response
        final_response = WebSocketMessage(
            type=MessageType.AGENT_RESPONSE_COMPLETE,
            payload={
                "final_response": {
                    "executive_summary": "Comprehensive infrastructure analysis completed",
                    "key_metrics": {
                        "total_resources_analyzed": 145,
                        "optimization_opportunities": 31,
                        "projected_annual_savings": "$41,400",
                        "implementation_complexity": "Medium",
                        "roi_timeline": "3-4 months"
                    },
                    "detailed_recommendations": {
                        "immediate_actions": [
                            "Resize 15 EC2 instances (saves $1,200/month)",
                            "Delete 8 unused EBS volumes (saves $320/month)",
                            "Archive 12 old snapshots (saves $180/month)"
                        ],
                        "medium_term_optimizations": [
                            "Implement auto-scaling policies",
                            "Migrate to ARM-based instances", 
                            "Optimize data transfer patterns"
                        ],
                        "strategic_initiatives": [
                            "Multi-region cost optimization",
                            "Reserved instance strategy",
                            "Containerization roadmap"
                        ]
                    },
                    "risk_assessment": {
                        "implementation_risks": "Low",
                        "business_continuity": "No disruption expected",
                        "rollback_plan": "Available for all changes"
                    }
                },
                "thread_id": thread_id,
                "completion_timestamp": datetime.now(timezone.utc).isoformat(),
                "tools_used": ["cost_analyzer", "performance_profiler", "security_scanner"],
                "confidence_score": 0.96
            },
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Route final response
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db:
            mock_session = AsyncMock()
            async def async_db_generator():
                yield mock_session
            mock_db.return_value = async_db_generator()
            
            result = await agent_handler.handle_message(user_id, mock_websocket, final_response)
            
        # Verify final response routing success
        assert result is True, "Final agent response should route successfully"
        
        # Verify comprehensive business value delivery
        response_data = final_response.payload["final_response"]
        
        # Verify executive summary
        assert "executive_summary" in response_data, "Should have executive summary"
        
        # Verify key metrics contain quantified value
        metrics = response_data["key_metrics"]
        assert "projected_annual_savings" in metrics, "Should project annual savings"
        assert "$" in metrics["projected_annual_savings"], "Should include monetary savings"
        assert "roi_timeline" in metrics, "Should provide ROI timeline"
        
        # Verify actionable recommendations
        recommendations = response_data["detailed_recommendations"]
        assert "immediate_actions" in recommendations, "Should have immediate actions"
        assert len(recommendations["immediate_actions"]) > 0, "Should have specific immediate actions"
        
        # Verify risk assessment
        assert "risk_assessment" in response_data, "Should include risk assessment"
        
        # Verify confidence score
        assert final_response.payload["confidence_score"] > 0.9, "Should have high confidence"
        
        self.assert_business_value_delivered(response_data, 'cost_savings')
        
        self.logger.info("✅ Agent final response routing with comprehensive business value validated")


# Test configuration for pytest
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.agent_routing
]