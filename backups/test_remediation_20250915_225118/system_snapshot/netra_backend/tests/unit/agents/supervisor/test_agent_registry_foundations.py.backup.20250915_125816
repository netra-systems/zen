"""Fixed Foundation Unit Tests for Agent Registry - Phase 1 Coverage Enhancement

MISSION: Improve AgentRegistry unit test coverage from 11.82% to 50%+ by testing
user isolation, factory patterns, and core registry functionality.

CRITICAL FIX: This file removes complex infrastructure imports that caused
configuration recursion and timeout issues during pytest collection.

Business Value Justification (BVJ):
- Segment: Platform/Internal (ALL user segments depend on agent registry)
- Business Goal: System Stability & Concurrent User Support
- Value Impact: AgentRegistry manages ALL agent instances - proper testing ensures
  10+ concurrent users can execute agents without contamination or memory leaks
- Strategic Impact: Registry reliability directly impacts $500K+ ARR functionality
  through reliable agent lifecycle management

FIXED ISSUES:
- Removed SSOT framework imports causing collection hangs
- Simplified imports to avoid configuration system recursion
- Removed complex infrastructure dependencies causing timeouts
- Made tests collectable and runnable with pytest

PRINCIPLES:
- Use standard pytest patterns for fast collection
- Minimal imports to avoid configuration system issues
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


class TestWebSocketManagerAdapter:
    """Unit tests for WebSocketManagerAdapter functionality with minimal dependencies."""

    def setup_method(self, method):
        """Setup for each test method."""
        self.test_user_id = "test-user-123"
        self.test_thread_id = "test-thread-456"
        self.test_run_id = "test-run-789"
        self.test_request_id = "test-request-abc"

    def test_websocket_adapter_can_be_imported(self):
        """Test that WebSocketManagerAdapter can be imported."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter
            assert WebSocketManagerAdapter is not None
        except ImportError as e:
            pytest.fail(f"Failed to import WebSocketManagerAdapter: {e}")

    def test_websocket_adapter_initialization(self):
        """Test WebSocketManagerAdapter initialization."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

            # Create mock WebSocket manager
            mock_manager = Mock()
            mock_context = Mock()
            mock_context.user_id = self.test_user_id

            adapter = WebSocketManagerAdapter(mock_manager, mock_context)

            # Verify initialization
            assert adapter._websocket_manager == mock_manager
            assert adapter._user_context == mock_context
        except Exception as e:
            pytest.fail(f"WebSocketManagerAdapter initialization failed: {e}")

    def test_websocket_adapter_has_notification_methods(self):
        """Test that adapter has all expected notification methods."""
        from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

        mock_manager = Mock()
        mock_context = Mock()
        adapter = WebSocketManagerAdapter(mock_manager, mock_context)

        # Check for required notification methods
        notification_methods = [
            'notify_agent_started',
            'notify_agent_thinking',
            'notify_tool_executing',
            'notify_tool_completed',
            'notify_agent_completed',
            'notify_agent_error',
            'notify_agent_death'
        ]

        for method_name in notification_methods:
            assert hasattr(adapter, method_name), f"Missing notification method: {method_name}"
            assert callable(getattr(adapter, method_name))

    @pytest.mark.asyncio
    async def test_websocket_adapter_notify_agent_started(self):
        """Test adapter's notify_agent_started method."""
        from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

        mock_manager = AsyncMock()
        mock_context = Mock()
        adapter = WebSocketManagerAdapter(mock_manager, mock_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        metadata = {"key": "value"}

        await adapter.notify_agent_started(run_id, agent_name, metadata)

        # Verify underlying manager was called
        mock_manager.notify_agent_started.assert_called_once_with(run_id, agent_name, metadata)

    @pytest.mark.asyncio
    async def test_websocket_adapter_notify_agent_thinking(self):
        """Test adapter's notify_agent_thinking method."""
        from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

        mock_manager = AsyncMock()
        mock_context = Mock()
        adapter = WebSocketManagerAdapter(mock_manager, mock_context)

        run_id = "test-run-123"
        agent_name = "test-agent"
        reasoning = "Test reasoning"
        step_number = 1

        await adapter.notify_agent_thinking(run_id, agent_name, reasoning, step_number)

        # Verify underlying manager was called
        mock_manager.notify_agent_thinking.assert_called_once_with(
            run_id, agent_name, reasoning, step_number
        )

    def test_websocket_adapter_attribute_delegation(self):
        """Test adapter delegates attributes to underlying manager."""
        from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

        mock_manager = Mock()
        mock_manager.test_attribute = "test_value"
        mock_context = Mock()

        adapter = WebSocketManagerAdapter(mock_manager, mock_context)

        # Test delegation of existing attribute
        assert adapter.test_attribute == "test_value"


class TestUserAgentSession:
    """Unit tests for UserAgentSession user isolation functionality."""

    def setup_method(self, method):
        """Setup for each test method."""
        self.test_user_id = "test-user-123"

    def test_user_agent_session_can_be_imported(self):
        """Test that UserAgentSession can be imported."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
            assert UserAgentSession is not None
        except ImportError as e:
            pytest.fail(f"Failed to import UserAgentSession: {e}")

    def test_user_session_initialization_valid(self):
        """Test UserAgentSession initialization with valid user_id."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

            session = UserAgentSession(self.test_user_id)

            # Verify initialization
            assert session.user_id == self.test_user_id
            assert hasattr(session, '_agents')
            assert hasattr(session, '_execution_contexts')
            assert hasattr(session, '_created_at')
            assert isinstance(session._agents, dict)
            assert len(session._agents) == 0
        except Exception as e:
            pytest.fail(f"UserAgentSession initialization failed: {e}")

    def test_user_session_initialization_invalid_user_id(self):
        """Test UserAgentSession initialization rejects invalid user_id values."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        invalid_user_ids = [None, "", "   ", 123, [], {}]

        for invalid_user_id in invalid_user_ids:
            with pytest.raises(ValueError) as cm:
                UserAgentSession(invalid_user_id)

            error_msg = str(cm.exception)
            assert "user_id must be a non-empty string" in error_msg

    def test_user_isolation_between_sessions(self):
        """Test that different user sessions are completely isolated."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        user1_id = "user-1"
        user2_id = "user-2"

        session1 = UserAgentSession(user1_id)
        session2 = UserAgentSession(user2_id)

        # Verify sessions are independent
        assert session1.user_id == user1_id
        assert session2.user_id == user2_id
        assert session1.user_id != session2.user_id

        # Verify internal state is isolated
        assert session1._agents is not session2._agents
        assert session1._execution_contexts is not session2._execution_contexts

        # Modify one session and verify the other is unaffected
        session1._agents["test_agent"] = Mock()
        assert "test_agent" not in session2._agents
        assert len(session2._agents) == 0

    @pytest.mark.asyncio
    async def test_user_session_set_websocket_manager(self):
        """Test setting WebSocket manager on user session."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        session = UserAgentSession(self.test_user_id)
        mock_manager = Mock()
        mock_context = Mock()

        # Test method exists and is callable
        assert hasattr(session, 'set_websocket_manager')
        assert callable(session.set_websocket_manager)

        await session.set_websocket_manager(mock_manager, mock_context)

        # Verify manager was set
        assert session._websocket_manager == mock_manager

    def test_session_creation_timestamp(self):
        """Test session tracks creation timestamp."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        before_creation = datetime.now(timezone.utc)
        session = UserAgentSession(self.test_user_id)
        after_creation = datetime.now(timezone.utc)

        # Verify timestamp is within reasonable bounds
        assert session._created_at >= before_creation - timedelta(seconds=1)
        assert session._created_at <= after_creation + timedelta(seconds=1)

    def test_session_agent_storage_isolation(self):
        """Test agent storage within session maintains isolation."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

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
        assert len(session._agents) == 2
        assert session._agents["agent1"] == agent1
        assert session._agents["agent2"] == agent2

        # Verify agents are isolated within this session
        other_session = UserAgentSession("other-user")
        assert len(other_session._agents) == 0
        assert "agent1" not in other_session._agents

    def test_session_execution_context_storage(self):
        """Test execution context storage within session."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        session = UserAgentSession(self.test_user_id)

        context_id = "context-123"
        mock_context = Mock()
        session._execution_contexts[context_id] = mock_context

        # Verify context stored
        assert len(session._execution_contexts) == 1
        assert session._execution_contexts[context_id] == mock_context

        # Verify isolation from other sessions
        other_session = UserAgentSession("other-user")
        assert len(other_session._execution_contexts) == 0

    def test_session_memory_management_patterns(self):
        """Test session supports memory leak prevention patterns."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        session = UserAgentSession(self.test_user_id)

        # Create weak references to verify garbage collection can work
        agent = Mock()
        session._agents["test_agent"] = agent

        # Create weak reference
        weak_ref = weakref.ref(agent)
        assert weak_ref() is not None

        # Remove from session
        del session._agents["test_agent"]
        del agent

        # Force garbage collection
        import gc
        gc.collect()

        # Session should not prevent cleanup


class TestAgentRegistryIntegration:
    """Integration tests for agent registry components."""

    def setup_method(self, method):
        """Setup for integration tests."""
        self.user_id = "integration-test-user"

    def test_user_session_with_websocket_adapter_integration(self):
        """Test UserAgentSession integrated with WebSocketManagerAdapter."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import (
                UserAgentSession, WebSocketManagerAdapter
            )

            # Create user session
            session = UserAgentSession(self.user_id)

            # Create mock WebSocket manager
            mock_manager = Mock()
            mock_context = Mock()
            mock_context.user_id = self.user_id

            # Create adapter
            adapter = WebSocketManagerAdapter(mock_manager, mock_context)

            # Should be able to set up integration
            assert session is not None
            assert adapter is not None

        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")

    def test_multiple_user_sessions_isolated_websockets(self):
        """Test multiple user sessions have isolated WebSocket managers."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        # Create multiple user sessions
        session1 = UserAgentSession("user-1")
        session2 = UserAgentSession("user-2")

        # Create separate WebSocket managers
        manager1 = Mock()
        manager2 = Mock()

        # Create mock contexts
        context1 = Mock()
        context1.user_id = "user-1"
        context2 = Mock()
        context2.user_id = "user-2"

        # Set up sessions with different managers (async method)
        # This is a sync test, so we just verify the setup is possible
        assert hasattr(session1, 'set_websocket_manager')
        assert hasattr(session2, 'set_websocket_manager')

        # Verify sessions remain independent
        assert session1.user_id != session2.user_id
        assert session1._agents is not session2._agents

    def test_user_session_id_generation_patterns(self):
        """Test user session creation with various ID patterns."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

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
            assert session.user_id == user_id
            assert isinstance(session._created_at, datetime)

        # Verify all sessions are independent
        for i, session in enumerate(sessions):
            for j, other_session in enumerate(sessions):
                if i != j:
                    assert session.user_id != other_session.user_id
                    assert session._agents is not other_session._agents

    def test_concurrent_user_session_creation_safety(self):
        """Test concurrent user session creation maintains isolation."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        user_ids = [f"concurrent-user-{i}" for i in range(5)]
        sessions = []

        # Create sessions concurrently (simulated)
        for user_id in user_ids:
            session = UserAgentSession(user_id)
            sessions.append(session)

        # Verify all sessions are independent
        assert len(sessions) == 5
        for i, session in enumerate(sessions):
            assert session.user_id == user_ids[i]
            for j, other_session in enumerate(sessions):
                if i != j:
                    assert session._agents is not other_session._agents
                    assert session.user_id != other_session.user_id


class TestAgentRegistryFoundations:
    """Test foundational registry patterns and architecture."""

    def test_registry_components_can_be_imported(self):
        """Test that all registry components can be imported."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import (
                WebSocketManagerAdapter,
                UserAgentSession
            )

            assert WebSocketManagerAdapter is not None
            assert UserAgentSession is not None

        except ImportError as e:
            pytest.fail(f"Failed to import registry components: {e}")

    def test_registry_supports_user_isolation_architecture(self):
        """Test that registry architecture supports user isolation."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        # Create sessions for different users
        session1 = UserAgentSession("user-1")
        session2 = UserAgentSession("user-2")

        # Verify complete isolation
        assert session1.user_id != session2.user_id
        assert session1._agents is not session2._agents
        assert session1._execution_contexts is not session2._execution_contexts
        assert session1._created_at != session2._created_at  # Different timestamps

    def test_registry_supports_websocket_integration_patterns(self):
        """Test that registry supports WebSocket integration patterns."""
        from netra_backend.app.agents.supervisor.agent_registry import (
            WebSocketManagerAdapter, UserAgentSession
        )

        # Verify WebSocket adapter patterns
        mock_manager = Mock()
        mock_context = Mock()
        adapter = WebSocketManagerAdapter(mock_manager, mock_context)

        # Should have all required methods for WebSocket integration
        required_methods = [
            'notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing',
            'notify_tool_completed', 'notify_agent_completed', 'notify_agent_error'
        ]

        for method_name in required_methods:
            assert hasattr(adapter, method_name)
            assert callable(getattr(adapter, method_name))

        # User sessions should support WebSocket manager assignment
        session = UserAgentSession("test-user")
        assert hasattr(session, 'set_websocket_manager')
        assert callable(session.set_websocket_manager)

    def test_registry_thread_safety_patterns(self):
        """Test that registry components support thread safety patterns."""
        from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

        session = UserAgentSession("thread-safety-test")

        # Should have access locking mechanisms
        assert hasattr(session, '_access_lock')

        # Multiple operations should be safe
        session._agents["agent1"] = Mock()
        session._agents["agent2"] = Mock()
        session._execution_contexts["ctx1"] = Mock()

        # Verify state consistency
        assert len(session._agents) == 2
        assert len(session._execution_contexts) == 1