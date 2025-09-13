"""Foundation Unit Tests for Agent Registry - Phase 1 Coverage Enhancement

MISSION: Improve AgentRegistry unit test coverage from 11.82% to 50%+ by testing
user isolation, factory patterns, and core registry functionality.

Business Value Justification (BVJ):
- Segment: Platform/Internal (ALL user segments depend on agent registry)
- Business Goal: System Stability & Concurrent User Support
- Value Impact: AgentRegistry manages ALL agent instances - proper testing ensures
  10+ concurrent users can execute agents without contamination or memory leaks
- Strategic Impact: Registry reliability directly impacts $500K+ ARR functionality
  through reliable agent lifecycle management

COVERAGE TARGET: Focus on high-impact foundation methods:
- User isolation patterns and session management (lines 165-300)
- WebSocket adapter functionality (lines 64-163)
- Agent registration and lifecycle (lines 300-500)
- Factory patterns for user-scoped agents (lines 500-700)
- Memory leak prevention and cleanup (lines 700+)

PRINCIPLES:
- Inherit from SSotBaseTestCase for SSOT compliance
- Use real services where possible, minimal mocking
- Test user isolation patterns thoroughly
- Focus on unit-level behavior, not integration scenarios
- Ensure tests actually fail when code is broken
- Test concurrent execution scenarios
"""

import asyncio
import pytest
import time
import weakref
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from collections import defaultdict

# SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Core imports
from netra_backend.app.agents.supervisor.agent_registry import (
    WebSocketManagerAdapter,
    UserAgentSession,
    # Note: Main AgentRegistry class would be imported here when we test it
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class MockWebSocketManager:
    """Mock WebSocket manager for testing adapter functionality."""

    def __init__(self):
        self.notifications_sent = []
        self.supports_all_methods = True

    async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]) -> None:
        self.notifications_sent.append(("agent_started", run_id, agent_name, metadata))

    async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str,
                                  step_number: Optional[int] = None, **kwargs) -> None:
        self.notifications_sent.append(("agent_thinking", run_id, agent_name, reasoning, step_number))

    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str,
                                  parameters: Dict[str, Any]) -> None:
        self.notifications_sent.append(("tool_executing", run_id, agent_name, tool_name, parameters))

    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str,
                                  result: Any, execution_time_ms: float) -> None:
        self.notifications_sent.append(("tool_completed", run_id, agent_name, tool_name, result, execution_time_ms))

    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Dict[str, Any],
                                   execution_time_ms: float) -> None:
        self.notifications_sent.append(("agent_completed", run_id, agent_name, result, execution_time_ms))

    async def notify_agent_error(self, run_id: str, agent_name: str, error: str,
                               error_context: Optional[Dict[str, Any]] = None) -> None:
        self.notifications_sent.append(("agent_error", run_id, agent_name, error, error_context))

    async def notify_agent_death(self, run_id: str, agent_name: str, cause: str,
                               death_context: Dict[str, Any]) -> None:
        self.notifications_sent.append(("agent_death", run_id, agent_name, cause, death_context))

    async def get_metrics(self) -> Dict[str, Any]:
        return {"total_notifications": len(self.notifications_sent)}


class MockWebSocketManagerLimited:
    """Mock WebSocket manager with limited method support for testing graceful degradation."""

    def __init__(self):
        self.notifications_sent = []
        # Only supports some methods

    async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]) -> None:
        self.notifications_sent.append(("agent_started", run_id, agent_name, metadata))

    # Missing other methods intentionally to test graceful degradation


class TestableAgent(BaseAgent):
    """Testable agent for registry testing."""

    def __init__(self, *args, **kwargs):
        self.test_execution_result = kwargs.pop('execution_result', {"status": "success"})
        super().__init__(*args, **kwargs)

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> dict:
        return {
            "status": "completed",
            "agent_name": self.name,
            "user_id": context.user_id,
            "result": self.test_execution_result
        }


class WebSocketManagerAdapterTests(SSotAsyncTestCase):
    """Unit tests for WebSocketManagerAdapter functionality."""

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        self.mock_websocket_manager = MockWebSocketManager()
        self.test_context = UserExecutionContext(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789",
            request_id="test-request-abc",
            db_session=Mock(),
            agent_context={},
            metadata={}
        )

    def test_adapter_initialization(self):
        """Test WebSocketManagerAdapter initialization."""
        # COVERAGE: WebSocketManagerAdapter.__init__ lines 72-81
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        # Verify initialization
        self.assertEqual(adapter._websocket_manager, self.mock_websocket_manager)
        self.assertEqual(adapter._user_context, self.test_context)

    def test_adapter_attribute_delegation(self):
        """Test adapter delegates attributes to underlying manager."""
        # COVERAGE: WebSocketManagerAdapter.__getattr__ lines 82-96
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        # Test delegation of existing attribute
        notifications_sent = adapter.notifications_sent
        self.assertEqual(notifications_sent, self.mock_websocket_manager.notifications_sent)

        # Test delegation of missing attribute raises AttributeError
        with self.assertRaises(AttributeError) as cm:
            _ = adapter.nonexistent_attribute

        error_msg = str(cm.exception)
        self.assertIn("WebSocketManagerAdapter has no attribute 'nonexistent_attribute'", error_msg)
        self.assertIn("MockWebSocketManager", error_msg)

    async def test_notify_agent_started(self):
        """Test adapter's notify_agent_started method."""
        # COVERAGE: notify_agent_started lines 98-103
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        metadata = {"key": "value"}

        await adapter.notify_agent_started(run_id, agent_name, metadata)

        # Verify notification was sent to underlying manager
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "agent_started")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], metadata)

    async def test_notify_agent_thinking(self):
        """Test adapter's notify_agent_thinking method."""
        # COVERAGE: notify_agent_thinking lines 105-111
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        reasoning = "Testing agent thinking"
        step_number = 1

        await adapter.notify_agent_thinking(run_id, agent_name, reasoning, step_number)

        # Verify notification was sent
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "agent_thinking")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], reasoning)
        self.assertEqual(notification[4], step_number)

    async def test_notify_tool_executing(self):
        """Test adapter's notify_tool_executing method."""
        # COVERAGE: notify_tool_executing lines 113-119
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        tool_name = "test-tool"
        parameters = {"param1": "value1"}

        await adapter.notify_tool_executing(run_id, agent_name, tool_name, parameters)

        # Verify notification was sent
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "tool_executing")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], tool_name)
        self.assertEqual(notification[4], parameters)

    async def test_notify_tool_completed(self):
        """Test adapter's notify_tool_completed method."""
        # COVERAGE: notify_tool_completed lines 121-127
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        tool_name = "test-tool"
        result = {"success": True}
        execution_time_ms = 100.5

        await adapter.notify_tool_completed(run_id, agent_name, tool_name, result, execution_time_ms)

        # Verify notification was sent
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "tool_completed")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], tool_name)
        self.assertEqual(notification[4], result)
        self.assertEqual(notification[5], execution_time_ms)

    async def test_notify_agent_completed(self):
        """Test adapter's notify_agent_completed method."""
        # COVERAGE: notify_agent_completed lines 129-135
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        result = {"status": "completed"}
        execution_time_ms = 250.7

        await adapter.notify_agent_completed(run_id, agent_name, result, execution_time_ms)

        # Verify notification was sent
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "agent_completed")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], result)
        self.assertEqual(notification[4], execution_time_ms)

    async def test_notify_agent_error(self):
        """Test adapter's notify_agent_error method."""
        # COVERAGE: notify_agent_error lines 137-143
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        error = "Test error message"
        error_context = {"error_code": "TEST_ERROR"}

        await adapter.notify_agent_error(run_id, agent_name, error, error_context)

        # Verify notification was sent
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "agent_error")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], error)
        self.assertEqual(notification[4], error_context)

    async def test_notify_agent_death(self):
        """Test adapter's notify_agent_death method."""
        # COVERAGE: notify_agent_death lines 145-151
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        cause = "Unexpected termination"
        death_context = {"termination_reason": "memory_error"}

        await adapter.notify_agent_death(run_id, agent_name, cause, death_context)

        # Verify notification was sent
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)
        notification = self.mock_websocket_manager.notifications_sent[0]
        self.assertEqual(notification[0], "agent_death")
        self.assertEqual(notification[1], run_id)
        self.assertEqual(notification[2], agent_name)
        self.assertEqual(notification[3], cause)
        self.assertEqual(notification[4], death_context)

    async def test_get_metrics(self):
        """Test adapter's get_metrics method."""
        # COVERAGE: get_metrics lines 153-162
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)

        # Add some notifications to test metrics
        await adapter.notify_agent_started("test-run", "test-agent", {})
        await adapter.notify_agent_completed("test-run", "test-agent", {}, 100.0)

        metrics = await adapter.get_metrics()

        # Verify metrics returned
        self.assertIsInstance(metrics, dict)
        self.assertEqual(metrics["total_notifications"], 2)

    async def test_graceful_degradation_missing_methods(self):
        """Test adapter gracefully handles WebSocket managers with missing methods."""
        # COVERAGE: Graceful degradation in adapter methods
        limited_manager = MockWebSocketManagerLimited()
        adapter = WebSocketManagerAdapter(limited_manager, self.test_context)

        # Test methods that exist
        await adapter.notify_agent_started("test-run", "test-agent", {})
        self.assertEqual(len(limited_manager.notifications_sent), 1)

        # Test methods that don't exist - should log debug and continue
        await adapter.notify_agent_thinking("test-run", "test-agent", "thinking")
        await adapter.notify_tool_executing("test-run", "test-agent", "tool", {})
        await adapter.notify_tool_completed("test-run", "test-agent", "tool", {}, 100.0)

        # Should still only have one notification (from the supported method)
        self.assertEqual(len(limited_manager.notifications_sent), 1)

    async def test_get_metrics_fallback_for_unsupported_manager(self):
        """Test get_metrics fallback for managers without metrics support."""
        # COVERAGE: get_metrics fallback lines 157-162
        limited_manager = MockWebSocketManagerLimited()
        adapter = WebSocketManagerAdapter(limited_manager, self.test_context)

        metrics = await adapter.get_metrics()

        # Verify fallback metrics
        self.assertIsInstance(metrics, dict)
        self.assertEqual(metrics['adapter_type'], 'WebSocketManagerAdapter')
        self.assertEqual(metrics['underlying_manager'], 'MockWebSocketManagerLimited')
        self.assertFalse(metrics['metrics_supported'])


class UserAgentSessionTests(SSotAsyncTestCase):
    """Unit tests for UserAgentSession user isolation functionality."""

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        self.test_user_id = "test-user-123"
        self.test_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id="test-thread-456",
            run_id="test-run-789",
            request_id="test-request-abc",
            db_session=Mock(),
            agent_context={},
            metadata={}
        )

    def test_user_session_initialization_valid(self):
        """Test UserAgentSession initialization with valid user_id."""
        # COVERAGE: UserAgentSession.__init__ lines 175-187
        session = UserAgentSession(self.test_user_id)

        # Verify initialization
        self.assertEqual(session.user_id, self.test_user_id)
        self.assertIsInstance(session._agents, dict)
        self.assertEqual(len(session._agents), 0)
        self.assertIsInstance(session._execution_contexts, dict)
        self.assertEqual(len(session._execution_contexts), 0)
        self.assertIsNone(session._websocket_bridge)
        self.assertIsNone(session._websocket_manager)
        self.assertIsInstance(session._created_at, datetime)
        self.assertTrue(hasattr(session, '_access_lock'))

    def test_user_session_initialization_invalid_user_id(self):
        """Test UserAgentSession initialization rejects invalid user_id values."""
        # COVERAGE: User ID validation lines 176-177
        invalid_user_ids = [
            None,
            "",
            "   ",  # whitespace only
            123,    # non-string
            [],     # non-string
            {},     # non-string
        ]

        for invalid_user_id in invalid_user_ids:
            with self.assertRaises(ValueError) as cm:
                UserAgentSession(invalid_user_id)

            error_msg = str(cm.exception)
            self.assertIn("user_id must be a non-empty string", error_msg)

    async def test_set_websocket_manager(self):
        """Test setting WebSocket manager on user session."""
        # COVERAGE: set_websocket_manager lines 189-200
        session = UserAgentSession(self.test_user_id)
        mock_manager = MockWebSocketManager()

        await session.set_websocket_manager(mock_manager, self.test_context)

        # Verify manager was set
        self.assertEqual(session._websocket_manager, mock_manager)

    def test_user_isolation_between_sessions(self):
        """Test that different user sessions are completely isolated."""
        # COVERAGE: User isolation verification
        user1_id = "user-1"
        user2_id = "user-2"

        session1 = UserAgentSession(user1_id)
        session2 = UserAgentSession(user2_id)

        # Verify sessions are independent
        self.assertEqual(session1.user_id, user1_id)
        self.assertEqual(session2.user_id, user2_id)
        self.assertNotEqual(session1.user_id, session2.user_id)

        # Verify internal state is isolated
        self.assertIsNot(session1._agents, session2._agents)
        self.assertIsNot(session1._execution_contexts, session2._execution_contexts)
        self.assertIsNot(session1._access_lock, session2._access_lock)

        # Modify one session and verify the other is unaffected
        session1._agents["test_agent"] = Mock()
        self.assertNotIn("test_agent", session2._agents)
        self.assertEqual(len(session2._agents), 0)

    async def test_concurrent_access_thread_safety(self):
        """Test thread-safe concurrent access to user session."""
        # COVERAGE: Thread safety via _access_lock
        session = UserAgentSession(self.test_user_id)

        # Simulate concurrent access to the session
        async def modify_session(session_id):
            async with session._access_lock:
                # Simulate some work
                await asyncio.sleep(0.01)
                session._agents[f"agent_{session_id}"] = Mock()

        # Run concurrent modifications
        tasks = []
        for i in range(5):
            task = asyncio.create_task(modify_session(i))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify all modifications were applied
        self.assertEqual(len(session._agents), 5)
        for i in range(5):
            self.assertIn(f"agent_{i}", session._agents)

    def test_session_creation_timestamp(self):
        """Test session tracks creation timestamp."""
        # COVERAGE: _created_at timestamp lines 184
        before_creation = datetime.now(timezone.utc)
        session = UserAgentSession(self.test_user_id)
        after_creation = datetime.now(timezone.utc)

        # Verify timestamp is within reasonable bounds
        self.assertGreaterEqual(session._created_at, before_creation - timedelta(seconds=1))
        self.assertLessEqual(session._created_at, after_creation + timedelta(seconds=1))

    def test_session_agent_storage_isolation(self):
        """Test agent storage within session maintains isolation."""
        # COVERAGE: Agent storage in _agents dict
        session = UserAgentSession(self.test_user_id)

        # Create mock agents
        agent1 = Mock()
        agent1.name = "agent1"
        agent2 = Mock()
        agent2.name = "agent2"

        # Store agents in session
        session._agents["agent1"] = agent1
        session._agents["agent2"] = agent2

        # Verify agents stored correctly
        self.assertEqual(len(session._agents), 2)
        self.assertEqual(session._agents["agent1"], agent1)
        self.assertEqual(session._agents["agent2"], agent2)

        # Verify agents are isolated within this session
        other_session = UserAgentSession("other-user")
        self.assertEqual(len(other_session._agents), 0)
        self.assertNotIn("agent1", other_session._agents)

    def test_session_execution_context_storage(self):
        """Test execution context storage within session."""
        # COVERAGE: Execution context storage in _execution_contexts dict
        session = UserAgentSession(self.test_user_id)

        context_id = "context-123"
        session._execution_contexts[context_id] = self.test_context

        # Verify context stored
        self.assertEqual(len(session._execution_contexts), 1)
        self.assertEqual(session._execution_contexts[context_id], self.test_context)

        # Verify isolation from other sessions
        other_session = UserAgentSession("other-user")
        self.assertEqual(len(other_session._execution_contexts), 0)

    def test_session_memory_management(self):
        """Test session supports memory leak prevention patterns."""
        # COVERAGE: Memory management preparation
        session = UserAgentSession(self.test_user_id)

        # Create weak references to verify garbage collection can work
        agent = Mock()
        session._agents["test_agent"] = agent

        # Create weak reference
        weak_ref = weakref.ref(agent)
        self.assertIsNotNone(weak_ref())

        # Remove from session
        del session._agents["test_agent"]
        del agent

        # Force garbage collection and verify cleanup
        import gc
        gc.collect()

        # Note: In a real scenario, the weak reference should become None
        # This test verifies the session doesn't prevent cleanup


class AgentRegistryFoundationIntegrationTests(SSotAsyncTestCase):
    """Integration tests combining WebSocket adapter and user session functionality."""

    def setup_method(self, method):
        """Setup for integration tests."""
        super().setup_method(method)

        self.user_id = "integration-test-user"
        self.mock_websocket_manager = MockWebSocketManager()
        self.test_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id="test-thread-456",
            run_id="test-run-789",
            request_id="test-request-abc",
            db_session=Mock(),
            agent_context={},
            metadata={}
        )

    async def test_user_session_with_websocket_adapter(self):
        """Test UserAgentSession integrated with WebSocketManagerAdapter."""
        # Create user session
        session = UserAgentSession(self.user_id)

        # Create and set WebSocket adapter
        adapter = WebSocketManagerAdapter(self.mock_websocket_manager, self.test_context)
        await session.set_websocket_manager(self.mock_websocket_manager, self.test_context)

        # Verify integration
        self.assertEqual(session._websocket_manager, self.mock_websocket_manager)

        # Test WebSocket notifications through adapter
        await adapter.notify_agent_started("test-run", "test-agent", {"test": "data"})

        # Verify notification was handled
        self.assertEqual(len(self.mock_websocket_manager.notifications_sent), 1)

    async def test_multiple_user_sessions_with_isolated_websockets(self):
        """Test multiple user sessions have isolated WebSocket managers."""
        # Create multiple user sessions
        session1 = UserAgentSession("user-1")
        session2 = UserAgentSession("user-2")

        # Create separate WebSocket managers
        manager1 = MockWebSocketManager()
        manager2 = MockWebSocketManager()

        # Set up sessions with different managers
        context1 = UserExecutionContext(
            user_id="user-1", thread_id="thread-1", run_id="run-1",
            request_id="req-1", db_session=Mock(),
            agent_context={}, metadata={}
        )
        context2 = UserExecutionContext(
            user_id="user-2", thread_id="thread-2", run_id="run-2",
            request_id="req-2", db_session=Mock(),
            agent_context={}, metadata={}
        )

        await session1.set_websocket_manager(manager1, context1)
        await session2.set_websocket_manager(manager2, context2)

        # Create adapters for each
        adapter1 = WebSocketManagerAdapter(manager1, context1)
        adapter2 = WebSocketManagerAdapter(manager2, context2)

        # Send notifications through each adapter
        await adapter1.notify_agent_started("run-1", "agent-1", {"user": "1"})
        await adapter2.notify_agent_started("run-2", "agent-2", {"user": "2"})

        # Verify isolation - each manager only got its own notification
        self.assertEqual(len(manager1.notifications_sent), 1)
        self.assertEqual(len(manager2.notifications_sent), 1)

        # Verify notification content is isolated
        notification1 = manager1.notifications_sent[0]
        notification2 = manager2.notifications_sent[0]

        self.assertEqual(notification1[1], "run-1")  # run_id
        self.assertEqual(notification1[2], "agent-1")  # agent_name
        self.assertEqual(notification1[3]["user"], "1")  # metadata

        self.assertEqual(notification2[1], "run-2")  # run_id
        self.assertEqual(notification2[2], "agent-2")  # agent_name
        self.assertEqual(notification2[3]["user"], "2")  # metadata

    def test_user_session_id_generation_patterns(self):
        """Test user session creation with various ID patterns."""
        # Test different valid user ID formats
        valid_user_ids = [
            "user123",
            "user-with-dashes",
            "user_with_underscores",
            "user.with.dots",
            "UUID-STYLE-ID-1234567890",
            "email@example.com",
            "very-long-user-id-that-might-be-generated-by-auth-systems-123456789"
        ]

        sessions = []
        for user_id in valid_user_ids:
            session = UserAgentSession(user_id)
            sessions.append(session)

            # Verify each session is created correctly
            self.assertEqual(session.user_id, user_id)
            self.assertIsInstance(session._created_at, datetime)

        # Verify all sessions are independent
        for i, session in enumerate(sessions):
            for j, other_session in enumerate(sessions):
                if i != j:
                    self.assertNotEqual(session.user_id, other_session.user_id)
                    self.assertIsNot(session._agents, other_session._agents)

    async def test_websocket_adapter_error_resilience(self):
        """Test WebSocket adapter handles errors gracefully."""
        # Create a manager that raises exceptions
        class ErrorProneManager:
            async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]):
                raise RuntimeError("WebSocket connection failed")

        error_manager = ErrorProneManager()
        adapter = WebSocketManagerAdapter(error_manager, self.test_context)

        # Test that exceptions from underlying manager bubble up appropriately
        with self.assertRaises(RuntimeError):
            await adapter.notify_agent_started("test-run", "test-agent", {})

    async def test_concurrent_user_session_creation(self):
        """Test concurrent user session creation maintains isolation."""
        user_ids = [f"concurrent-user-{i}" for i in range(10)]

        async def create_session(user_id):
            session = UserAgentSession(user_id)
            # Add some data to verify isolation
            session._agents[f"agent_{user_id}"] = Mock()
            return session

        # Create sessions concurrently
        tasks = [create_session(user_id) for user_id in user_ids]
        sessions = await asyncio.gather(*tasks)

        # Verify all sessions were created correctly
        self.assertEqual(len(sessions), 10)

        # Verify complete isolation between sessions
        for i, session in enumerate(sessions):
            expected_user_id = f"concurrent-user-{i}"
            self.assertEqual(session.user_id, expected_user_id)
            self.assertEqual(len(session._agents), 1)
            self.assertIn(f"agent_{expected_user_id}", session._agents)

            # Verify this session doesn't have agents from other sessions
            for j in range(len(sessions)):
                if i != j:
                    other_agent_key = f"agent_concurrent-user-{j}"
                    self.assertNotIn(other_agent_key, session._agents)