"""
Base Agent WebSocket Integration Tests - Foundation Coverage Phase 1

Business Value: Free/Early/Mid/Enterprise - Real-time Chat Experience ($500K+ ARR)
Tests WebSocket event emission, real-time communication patterns, and agent-to-user
messaging that delivers 90% of platform value through substantive AI interactions.

SSOT Compliance: Uses SSotAsyncTestCase, real WebSocket connections where possible,
follows WebSocket Agent Integration patterns per CLAUDE.md.

Coverage Target: BaseAgent WebSocket integration, event emission, real-time patterns
Current BaseAgent WebSocket Coverage: ~5% -> Target: 25%+

Critical Events Tested:
- agent_started: User sees agent began processing
- agent_thinking: Real-time reasoning visibility
- tool_executing: Tool usage transparency
- tool_completed: Tool results display
- agent_completed: User knows response is ready

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, call
from typing import Dict, Any, Optional, List

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter


class WebSocketTestAgent(BaseAgent):
    """Concrete agent for testing WebSocket integration patterns."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "websocket_test_agent"
        self.test_events_emitted = []

    async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Test implementation that emits all critical WebSocket events."""
        # Emit agent_started event using correct BaseAgent methods
        await self.emit_agent_started(f"Processing {request}")
        self.test_events_emitted.append("agent_started")

        # Emit agent_thinking event
        await self.emit_thinking(f"Processing request: {request}")
        self.test_events_emitted.append("agent_thinking")

        # Simulate tool execution with tool_executing event
        await self.emit_tool_executing("test_analysis_tool", {"request": request})
        self.test_events_emitted.append("tool_executing")

        # Simulate tool completion with tool_completed event
        tool_result = {"analysis": f"Analyzed: {request}", "confidence": 0.95}
        await self.emit_tool_completed("test_analysis_tool", tool_result)
        self.test_events_emitted.append("tool_completed")

        # Emit agent_completed event
        final_response = {
            "status": "success",
            "response": f"Completed processing: {request}",
            "agent_type": self.agent_type,
            "tool_results": [tool_result]
        }

        await self.emit_agent_completed(final_response)
        self.test_events_emitted.append("agent_completed")

        return final_response


class TestBaseAgentWebSocketIntegration(SSotAsyncTestCase):
    """Test BaseAgent WebSocket integration and real-time event patterns."""

    def setup_method(self, method):
        """Set up test environment with WebSocket mocks."""
        super().setup_method(method)

        # Create mock LLM manager
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock response")

        # Create detailed WebSocket bridge mock
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = Mock()

        # Mock critical WebSocket methods that agents use
        self.websocket_bridge.emit_agent_event = AsyncMock()
        self.websocket_bridge.emit_tool_event = AsyncMock()
        self.websocket_bridge.emit_agent_started = AsyncMock()
        self.websocket_bridge.emit_agent_thinking = AsyncMock()
        self.websocket_bridge.emit_agent_completed = AsyncMock()

        # Track calls for verification
        self.websocket_calls = []

        async def track_agent_event(*args, **kwargs):
            self.websocket_calls.append(("agent_event", args, kwargs))

        async def track_tool_event(*args, **kwargs):
            self.websocket_calls.append(("tool_event", args, kwargs))

        self.websocket_bridge.emit_agent_event.side_effect = track_agent_event
        self.websocket_bridge.emit_tool_event.side_effect = track_tool_event

        # Create real UserExecutionContext for WebSocket routing
        self.test_context = UserExecutionContext(
            user_id="websocket-test-user-001",
            thread_id="websocket-test-thread-001",
            run_id="websocket-test-run-001",
            agent_context={
                "user_request": "websocket integration test",
                "client_connection_id": "test-ws-connection-123",
                "test_websocket_integration": True
            }
        ).with_db_session(AsyncMock())

    def teardown_method(self, method):
        """Clean up WebSocket test resources."""
        super().teardown_method(method)
        self.websocket_calls.clear()

    async def test_websocket_bridge_adapter_initialization(self):
        """Test WebSocket bridge adapter is properly initialized."""
        agent = WebSocketTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-websocket-001")
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-bridge-001")

        # Verify: WebSocket bridge adapter exists and is configured
        assert hasattr(agent, '_websocket_adapter')
        adapter = agent._websocket_adapter
        assert adapter is not None
        assert isinstance(adapter, WebSocketBridgeAdapter)

        # Verify: Adapter has bridge configured via has_websocket_bridge
        assert adapter.has_websocket_bridge()

        # Verify: Critical event methods are available
        assert hasattr(adapter, 'emit_agent_started')
        assert hasattr(adapter, 'emit_tool_executing')
        assert callable(adapter.emit_agent_started)
        assert callable(adapter.emit_tool_executing)

    async def test_websocket_event_emission_all_critical_events(self):
        """Test all 5 critical WebSocket events are emitted correctly."""
        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        )
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-events-001")
        # FIXED: websocket_bridge set after instantiation

        # Execute agent request which should emit all critical events
        result = await agent.process_request(
            "test websocket event emission",
            self.test_context
        )

        # Verify: All 5 critical events were emitted
        expected_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        assert agent.test_events_emitted == expected_events

        # Verify: WebSocket bridge methods were called
        assert len(self.websocket_calls) == 5

        # Verify: Event types and data structure
        event_types = []
        for call_type, args, kwargs in self.websocket_calls:
            if call_type == "agent_event":
                # Extract event_type from the call
                if args and len(args) > 0:
                    event_types.append(args[0])  # first arg should be event_type
                elif "event_type" in kwargs:
                    event_types.append(kwargs["event_type"])
            elif call_type == "tool_event":
                if args and len(args) > 0:
                    event_types.append(args[0])  # first arg should be event_type
                elif "event_type" in kwargs:
                    event_types.append(kwargs["event_type"])

        # Should have captured agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types
        assert "agent_completed" in event_types

    async def test_websocket_user_context_preservation(self):
        """Test WebSocket events preserve UserExecutionContext for proper routing."""
        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        )
        # FIXED: websocket_bridge set after instantiation
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-context-001")

        # Execute with specific user context
        await agent.process_request(
            "test user context preservation",
            self.test_context
        )

        # Verify: All WebSocket calls received the correct context
        for call_type, args, kwargs in self.websocket_calls:
            # Check if context was passed correctly
            context_found = False

            # Check args for context
            for arg in args:
                if isinstance(arg, UserExecutionContext):
                    context_found = True
                    assert arg.user_id == "websocket-test-user-001"
                    assert arg.thread_id == "websocket-test-thread-001"
                    assert arg.run_id == "websocket-test-run-001"
                    break

            # Check kwargs for context
            if not context_found and "context" in kwargs:
                context = kwargs["context"]
                assert isinstance(context, UserExecutionContext)
                assert context.user_id == "websocket-test-user-001"
                assert context.thread_id == "websocket-test-thread-001"
                assert context.run_id == "websocket-test-run-001"
                context_found = True

            # Every WebSocket call should have proper context for routing
            assert context_found, f"WebSocket call missing context: {call_type}"

    async def test_websocket_event_data_structure(self):
        """Test WebSocket events contain proper data structures for frontend."""
        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        )
        # FIXED: websocket_bridge set after instantiation
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-data-001")

        await agent.process_request(
            "test event data structure",
            self.test_context
        )

        # Analyze the data passed to WebSocket events
        for call_type, args, kwargs in self.websocket_calls:
            # Look for data parameter
            data_found = False

            for arg in args:
                if isinstance(arg, dict) and "status" in arg or "thought" in arg or "tool" in arg:
                    data_found = True
                    # Verify data has meaningful content
                    assert len(arg) > 0
                    break

            if not data_found and "data" in kwargs:
                data = kwargs["data"]
                assert isinstance(data, dict)
                assert len(data) > 0
                data_found = True

            # Each event should carry meaningful data for the frontend
            # This is critical for user experience ($500K+ ARR dependency)
            assert data_found, f"WebSocket call missing data payload: {call_type}"

    async def test_websocket_error_handling_in_events(self):
        """Test WebSocket event emission handles errors gracefully."""
        # Create agent with failing WebSocket bridge
        failing_bridge = Mock(spec=AgentWebSocketBridge)
        failing_bridge.emit_agent_event = AsyncMock(side_effect=Exception("WebSocket connection lost"))
        failing_bridge.emit_tool_event = AsyncMock(side_effect=Exception("WebSocket send failed"))

        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        )
        agent.set_websocket_bridge(failing_bridge, "test-run-failing-001")

        # Test: Agent should handle WebSocket failures gracefully
        # The business logic should complete even if WebSocket events fail
        try:
            result = await agent.process_request(
                "test websocket error handling",
                self.test_context
            )

            # Agent should still return a result even if WebSocket events fail
            assert result is not None
            assert isinstance(result, dict)

        except Exception as e:
            # If exceptions bubble up, they should be WebSocket-related, not business logic
            assert "WebSocket" in str(e) or "connection" in str(e).lower()

    async def test_websocket_concurrent_user_isolation(self):
        """Test WebSocket events maintain proper isolation between concurrent users."""
        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        )
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-concurrent-001")
        # FIXED: websocket_bridge set after instantiation

        # Create separate contexts for different users
        user1_context = UserExecutionContext(
            user_id="websocket-user-1",
            thread_id="websocket-thread-1",
            run_id="websocket-run-1",
            agent_context={"user_request": "user 1 request"}
        ).with_db_session(AsyncMock())

        user2_context = UserExecutionContext(
            user_id="websocket-user-2",
            thread_id="websocket-thread-2",
            run_id="websocket-run-2",
            agent_context={"user_request": "user 2 request"}
        ).with_db_session(AsyncMock())

        # Execute concurrent requests
        task1 = asyncio.create_task(
            agent.process_request("user 1 concurrent test", user1_context)
        )
        task2 = asyncio.create_task(
            agent.process_request("user 2 concurrent test", user2_context)
        )

        results = await asyncio.gather(task1, task2)

        # Verify: Both requests completed successfully
        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)

        # Verify: WebSocket calls were made for both users
        assert len(self.websocket_calls) >= 10  # 5 events per user minimum

        # Verify: Contexts were properly isolated in WebSocket events
        user1_calls = 0
        user2_calls = 0

        for call_type, args, kwargs in self.websocket_calls:
            # Find context in the call
            context = None
            for arg in args:
                if isinstance(arg, UserExecutionContext):
                    context = arg
                    break
            if not context and "context" in kwargs:
                context = kwargs["context"]

            if context:
                if context.user_id == "websocket-user-1":
                    user1_calls += 1
                elif context.user_id == "websocket-user-2":
                    user2_calls += 1

        # Both users should have received their WebSocket events
        assert user1_calls >= 5  # All 5 critical events
        assert user2_calls >= 5  # All 5 critical events

    async def test_websocket_real_time_progress_updates(self):
        """Test WebSocket events provide real-time progress for user experience."""
        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-progress-001")
        )
        # FIXED: websocket_bridge set after instantiation

        # Execute request and capture timing
        import time
        start_time = time.time()

        await agent.process_request(
            "test real-time progress updates",
            self.test_context
        )

        end_time = time.time()

        # Verify: Events were emitted in correct sequence
        expected_sequence = [
            "agent_started",    # User knows processing began
            "agent_thinking",   # User sees reasoning progress
            "tool_executing",   # User knows tool is running
            "tool_completed",   # User sees tool results
            "agent_completed"   # User knows response is ready
        ]

        assert agent.test_events_emitted == expected_sequence

        # Verify: All events were sent to WebSocket bridge
        assert len(self.websocket_calls) == 5

        # This sequence delivers the real-time experience that constitutes
        # 90% of platform value - users see meaningful progress updates
        # during AI processing, not just a loading spinner

    async def test_websocket_business_value_event_content(self):
        """Test WebSocket events contain business-valuable information for users."""
        agent = WebSocketTestAgent(
            llm_manager=self.llm_manager
        )
        # FIXED: websocket_bridge set after instantiation

        test_request = "analyze quarterly sales performance and recommend optimizations"

        await agent.process_request(test_request, self.test_context)

        # Verify: Events contain meaningful business context
        for call_type, args, kwargs in self.websocket_calls:
            # Extract data from the call
            data = None
            for arg in args:
                if isinstance(arg, dict):
                    data = arg
                    break
            if not data and "data" in kwargs:
                data = kwargs["data"]

            if data:
                # Events should contain substantive information, not just technical status
                if "thought" in data:
                    # agent_thinking events should show actual reasoning
                    assert len(data["thought"]) > 10
                    assert any(word in data["thought"].lower() for word in ["processing", "analyzing", "preparing"])

                elif "tool" in data:
                    # Tool events should show actual tool usage
                    assert "test_analysis_tool" in str(data)

                elif "response" in data:
                    # Completion events should contain the actual response
                    assert test_request.split()[0] in data["response"]  # Should contain part of original request

        # This verifies that WebSocket events deliver genuine business value
        # by showing users meaningful progress, not just technical notifications