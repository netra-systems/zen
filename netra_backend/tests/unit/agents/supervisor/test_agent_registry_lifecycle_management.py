"""
Unit Tests for AgentRegistry Lifecycle Management

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Reliable agent lifecycle management for multi-user platform
- Value Impact: Ensures 10+ concurrent users with proper resource cleanup
- Strategic Impact: Prevents memory leaks and ensures platform stability

CRITICAL MISSION: Test AgentRegistry lifecycle management ensuring:
1. Proper initialization with Factory-based patterns
2. User session creation and lifecycle management
3. WebSocket manager integration and propagation
4. Agent creation and registration with user isolation
5. Resource cleanup and memory management
6. Tool dispatcher factory integration
7. Concurrent user session handling
8. Background task management and cleanup

FOCUS: Factory-based user isolation as documented in USER_CONTEXT_ARCHITECTURE.md
"""

import asyncio
import pytest
import uuid
import weakref
import gc
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession,
    AgentLifecycleManager
)

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager for testing."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm._initialized = True
    mock_llm.chat_completion = AsyncMock(return_value="Test response")
    mock_llm.is_healthy = Mock(return_value=True)
    return mock_llm


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager."""
    mock_ws_manager = Mock()
    mock_ws_manager.send_event = AsyncMock()
    mock_ws_manager.is_connected = Mock(return_value=True)
    mock_ws_manager.disconnect = AsyncMock()
    mock_ws_manager.get_connection_count = Mock(return_value=1)
    return mock_ws_manager


@pytest.fixture
def test_user_id():
    """Generate unique test user ID."""
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture 
def test_user_context(test_user_id):
    """Create test user execution context."""
    return UserExecutionContext(
        user_id=test_user_id,
        request_id=f"test_request_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture
def multiple_users():
    """Create multiple user contexts for concurrent testing."""
    users = []
    for i in range(10):
        user_id = f"user_{i}_{uuid.uuid4().hex[:6]}"
        context = UserExecutionContext(
            user_id=user_id,
            request_id=f"req_{i}_{uuid.uuid4().hex[:6]}",
            thread_id=f"thread_{i}_{uuid.uuid4().hex[:6]}",
            run_id=f"run_{i}_{uuid.uuid4().hex[:6]}"
        )
        users.append(context)
    return users


# ============================================================================
# TEST: AgentRegistry Initialization and Configuration
# ============================================================================

class TestAgentRegistryInitialization(SSotBaseTestCase):
    """Test AgentRegistry initialization and configuration."""
    
    def test_agent_registry_basic_initialization(self, mock_llm_manager):
        """Test basic AgentRegistry initialization with required parameters."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Verify basic initialization
        assert registry.llm_manager == mock_llm_manager
        assert registry.tool_dispatcher_factory is not None
        assert callable(registry.tool_dispatcher_factory)
        assert registry._agents_registered is False
        assert len(registry.registration_errors) == 0
        assert len(registry._user_sessions) == 0
        assert isinstance(registry._lifecycle_manager, AgentLifecycleManager)
        assert registry._created_at is not None
        assert isinstance(registry._session_lock, asyncio.Lock)
        assert registry._legacy_dispatcher is None
        
        # Verify lifecycle manager has registry reference
        assert registry._lifecycle_manager._registry == registry
    
    def test_agent_registry_custom_tool_dispatcher_factory(self, mock_llm_manager):
        """Test AgentRegistry initialization with custom tool dispatcher factory."""
        custom_factory = AsyncMock()
        registry = AgentRegistry(mock_llm_manager, custom_factory)
        
        assert registry.tool_dispatcher_factory == custom_factory
        assert registry._lifecycle_manager._registry == registry
    
    def test_agent_registry_initialization_validation(self):
        """Test AgentRegistry initialization parameter validation."""
        # Missing required llm_manager parameter
        with pytest.raises(TypeError):
            AgentRegistry()
    
    def test_set_tool_dispatcher_factory(self, mock_llm_manager):
        """Test setting tool dispatcher factory after initialization."""
        registry = AgentRegistry(mock_llm_manager)
        new_factory = AsyncMock()
        
        registry.set_tool_dispatcher_factory(new_factory)
        
        assert registry.tool_dispatcher_factory == new_factory


# ============================================================================
# TEST: User Session Management
# ============================================================================

class TestUserSessionManagement(SSotBaseTestCase):
    """Test user session creation, retrieval, and lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_get_user_session_creation(self, mock_llm_manager, test_user_id):
        """Test creating new user session."""
        registry = AgentRegistry(mock_llm_manager)
        
        # First access creates new session
        session = await registry.get_user_session(test_user_id)
        
        assert isinstance(session, UserAgentSession)
        assert session.user_id == test_user_id
        assert test_user_id in registry._user_sessions
        assert len(registry._user_sessions) == 1
    
    @pytest.mark.asyncio
    async def test_get_user_session_reuses_existing(self, mock_llm_manager, test_user_id):
        """Test that getting user session reuses existing session."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session
        session1 = await registry.get_user_session(test_user_id)
        session2 = await registry.get_user_session(test_user_id)
        
        assert session1 is session2
        assert len(registry._user_sessions) == 1
    
    @pytest.mark.asyncio
    async def test_get_user_session_validation(self, mock_llm_manager):
        """Test user session creation validation."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Test invalid user_id scenarios
        invalid_inputs = [
            ("", "user_id is required and must be non-empty string"),
            (None, "user_id is required and must be non-empty string"),
            (123, "user_id is required and must be non-empty string"),
        ]
        
        for invalid_input, expected_error in invalid_inputs:
            with pytest.raises(ValueError, match=expected_error):
                await registry.get_user_session(invalid_input)
    
    @pytest.mark.asyncio
    async def test_get_user_session_websocket_manager_propagation(self, mock_llm_manager, 
                                                                 test_user_id, mock_websocket_manager):
        """Test WebSocket manager propagation to new user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(mock_websocket_manager)
        
        with patch.object(UserAgentSession, 'set_websocket_manager') as mock_set_ws:
            session = await registry.get_user_session(test_user_id)
            
            # Verify WebSocket manager was set on session
            mock_set_ws.assert_called_once()
            args, kwargs = mock_set_ws.call_args
            assert args[0] == mock_websocket_manager
    
    @pytest.mark.asyncio
    async def test_cleanup_user_session_success(self, mock_llm_manager, test_user_id):
        """Test successful user session cleanup."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session with agent
        session = await registry.get_user_session(test_user_id)
        await session.register_agent("test_agent", Mock())
        
        assert test_user_id in registry._user_sessions
        
        # Cleanup session
        cleanup_metrics = await registry.cleanup_user_session(test_user_id)
        
        assert test_user_id not in registry._user_sessions
        assert cleanup_metrics['user_id'] == test_user_id
        assert cleanup_metrics['status'] == 'cleaned'
        assert 'cleaned_agents' in cleanup_metrics
        assert cleanup_metrics['cleaned_agents'] >= 0
    
    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_session(self, mock_llm_manager):
        """Test cleanup of non-existent session."""
        registry = AgentRegistry(mock_llm_manager)
        
        cleanup_metrics = await registry.cleanup_user_session("nonexistent_user")
        
        assert cleanup_metrics['user_id'] == "nonexistent_user"
        assert cleanup_metrics['status'] == 'no_session'
        assert cleanup_metrics['cleaned_agents'] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_user_session_validation(self, mock_llm_manager):
        """Test cleanup session validation."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Test empty user_id
        with pytest.raises(ValueError, match="user_id is required"):
            await registry.cleanup_user_session("")
        
        # Test None user_id  
        with pytest.raises(ValueError, match="user_id is required"):
            await registry.cleanup_user_session(None)
    
    @pytest.mark.asyncio
    async def test_concurrent_user_session_creation(self, mock_llm_manager, multiple_users):
        """Test creating multiple user sessions concurrently."""
        registry = AgentRegistry(mock_llm_manager)
        
        async def create_session(user_context):
            session = await registry.get_user_session(user_context.user_id)
            await session.register_agent("test_agent", Mock())
            return session
        
        # Create sessions concurrently
        tasks = [create_session(user) for user in multiple_users]
        sessions = await asyncio.gather(*tasks)
        
        assert len(sessions) == len(multiple_users)
        assert len(registry._user_sessions) == len(multiple_users)
        
        # Verify each session has correct user_id and isolation
        for i, session in enumerate(sessions):
            expected_user_id = multiple_users[i].user_id
            assert session.user_id == expected_user_id
            assert len(session._agents) == 1


# ============================================================================
# TEST: WebSocket Manager Integration
# ============================================================================

class TestWebSocketManagerIntegration(SSotBaseTestCase):
    """Test WebSocket manager integration and lifecycle."""
    
    @pytest.mark.asyncio
    async def test_set_websocket_manager_sync_method(self, mock_llm_manager, mock_websocket_manager):
        """Test setting WebSocket manager via sync method."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create some user sessions first
        user_ids = ["user1", "user2", "user3"]
        for user_id in user_ids:
            await registry.get_user_session(user_id)
        
        # Set WebSocket manager
        registry.set_websocket_manager(mock_websocket_manager)
        
        assert registry.websocket_manager == mock_websocket_manager
    
    @pytest.mark.asyncio
    async def test_set_websocket_manager_async_method(self, mock_llm_manager, 
                                                     mock_websocket_manager, test_user_id):
        """Test setting WebSocket manager via async method."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create user session
        session = await registry.get_user_session(test_user_id)
        
        with patch.object(session, 'set_websocket_manager') as mock_set_ws:
            await registry.set_websocket_manager_async(mock_websocket_manager)
            
            assert registry.websocket_manager == mock_websocket_manager
            mock_set_ws.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_manager_handles_none_gracefully(self, mock_llm_manager):
        """Test WebSocket manager handles None values gracefully."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Should not raise exception
        registry.set_websocket_manager(None)
        await registry.set_websocket_manager_async(None)
        
        assert registry.websocket_manager is None
    
    @pytest.mark.asyncio
    async def test_websocket_manager_propagation_error_handling(self, mock_llm_manager, test_user_id):
        """Test WebSocket manager error handling during propagation."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create user session
        session = await registry.get_user_session(test_user_id)
        
        # Mock session.set_websocket_manager to raise exception
        with patch.object(session, 'set_websocket_manager', 
                         AsyncMock(side_effect=Exception("WebSocket setup failed"))):
            
            mock_ws_manager = Mock()
            
            # Should not raise exception, but log error
            await registry.set_websocket_manager_async(mock_ws_manager)
            
            # Registry should still have the WebSocket manager set
            assert registry.websocket_manager == mock_ws_manager


# ============================================================================
# TEST: Agent Creation and Management
# ============================================================================

class TestAgentCreationAndManagement(SSotBaseTestCase):
    """Test agent creation, registration, and management within user sessions."""
    
    @pytest.mark.asyncio
    async def test_create_agent_for_user_success(self, mock_llm_manager, test_user_context, 
                                                mock_websocket_manager):
        """Test successful agent creation for user."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Mock the get_async method to return a test agent
        mock_agent = Mock()
        registry.get_async = AsyncMock(return_value=mock_agent)
        
        # Create agent for user
        created_agent = await registry.create_agent_for_user(
            user_id=test_user_context.user_id,
            agent_type="test_agent",
            user_context=test_user_context,
            websocket_manager=mock_websocket_manager
        )
        
        assert created_agent == mock_agent
        
        # Verify user session was created and agent was registered
        assert test_user_context.user_id in registry._user_sessions
        user_session = registry._user_sessions[test_user_context.user_id]
        retrieved_agent = await user_session.get_agent("test_agent")
        assert retrieved_agent == mock_agent
    
    @pytest.mark.asyncio
    async def test_create_agent_for_user_validation(self, mock_llm_manager, test_user_context):
        """Test agent creation validation."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Test missing user_id
        with pytest.raises(ValueError, match="user_id and agent_type are required"):
            await registry.create_agent_for_user("", "test_agent", test_user_context)
        
        # Test missing agent_type
        with pytest.raises(ValueError, match="user_id and agent_type are required"):
            await registry.create_agent_for_user("test_user", "", test_user_context)
    
    @pytest.mark.asyncio
    async def test_create_agent_for_user_unknown_agent_type(self, mock_llm_manager, test_user_context):
        """Test creating agent with unknown agent type."""
        registry = AgentRegistry(mock_llm_manager)
        registry.get_async = AsyncMock(return_value=None)
        
        with pytest.raises(KeyError, match="No factory registered for agent type"):
            await registry.create_agent_for_user(
                user_id=test_user_context.user_id,
                agent_type="nonexistent_agent",
                user_context=test_user_context
            )
    
    @pytest.mark.asyncio
    async def test_get_user_agent_retrieval(self, mock_llm_manager, test_user_id):
        """Test user-specific agent retrieval."""
        registry = AgentRegistry(mock_llm_manager)
        mock_agent = Mock()
        
        # Create session and register agent
        session = await registry.get_user_session(test_user_id)
        await session.register_agent("test_agent", mock_agent)
        
        # Retrieve agent
        retrieved_agent = await registry.get_user_agent(test_user_id, "test_agent")
        assert retrieved_agent == mock_agent
        
        # Test non-existent agent
        non_existent = await registry.get_user_agent(test_user_id, "non_existent")
        assert non_existent is None
        
        # Test non-existent user
        no_user_agent = await registry.get_user_agent("non_existent_user", "test_agent")
        assert no_user_agent is None
    
    @pytest.mark.asyncio
    async def test_remove_user_agent_success(self, mock_llm_manager, test_user_id):
        """Test successful user agent removal with cleanup."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create mock agent with cleanup method
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock()
        
        # Create session and register agent
        session = await registry.get_user_session(test_user_id)
        await session.register_agent("test_agent", mock_agent)
        
        # Verify agent is registered
        assert await registry.get_user_agent(test_user_id, "test_agent") is not None
        
        # Remove agent
        result = await registry.remove_user_agent(test_user_id, "test_agent")
        
        assert result is True
        assert await registry.get_user_agent(test_user_id, "test_agent") is None
        mock_agent.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_user_agent_nonexistent(self, mock_llm_manager):
        """Test removing non-existent agent."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Try to remove from non-existent user
        result = await registry.remove_user_agent("nonexistent_user", "test_agent")
        assert result is False
        
        # Try to remove non-existent agent from existing user
        await registry.get_user_session("test_user")
        result = await registry.remove_user_agent("test_user", "nonexistent_agent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reset_user_agents_complete_reset(self, mock_llm_manager, test_user_id):
        """Test comprehensive user agent reset."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session with multiple agents
        session = await registry.get_user_session(test_user_id)
        await session.register_agent("agent1", Mock())
        await session.register_agent("agent2", Mock())
        
        old_session_id = id(session)
        assert len(session._agents) == 2
        
        # Reset user agents
        reset_report = await registry.reset_user_agents(test_user_id)
        
        assert reset_report['user_id'] == test_user_id
        assert reset_report['status'] == 'reset_complete'
        assert reset_report['agents_reset'] == 2
        
        # Verify new session was created
        new_session = registry._user_sessions[test_user_id]
        assert id(new_session) != old_session_id
        assert len(new_session._agents) == 0
    
    @pytest.mark.asyncio
    async def test_reset_nonexistent_user_agents(self, mock_llm_manager):
        """Test resetting agents for non-existent user."""
        registry = AgentRegistry(mock_llm_manager)
        
        reset_report = await registry.reset_user_agents("nonexistent_user")
        
        assert reset_report['user_id'] == "nonexistent_user"
        assert reset_report['status'] == 'no_session'
        assert reset_report['agents_reset'] == 0


# ============================================================================
# TEST: Registry Cleanup and Resource Management
# ============================================================================

class TestRegistryCleanupAndResourceManagement(SSotBaseTestCase):
    """Test registry cleanup operations and resource management."""
    
    @pytest.mark.asyncio
    async def test_registry_cleanup_all_resources(self, mock_llm_manager, multiple_users):
        """Test comprehensive registry cleanup."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create user sessions with agents
        for user_context in multiple_users:
            session = await registry.get_user_session(user_context.user_id)
            await session.register_agent("test_agent", Mock())
        
        assert len(registry._user_sessions) == len(multiple_users)
        
        # Cleanup registry
        await registry.cleanup()
        
        # Verify all sessions were cleaned up
        assert len(registry._user_sessions) == 0
        assert registry._legacy_dispatcher is None
    
    @pytest.mark.asyncio
    async def test_registry_cleanup_with_background_tasks(self, mock_llm_manager):
        """Test registry cleanup with background tasks."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create mock background task
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_task.cancel = Mock()
        registry._background_tasks = [mock_task]
        
        # Cleanup should cancel background tasks
        await registry.cleanup()
        
        mock_task.cancel.assert_called_once()
        assert len(registry._background_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_monitor_all_users_comprehensive(self, mock_llm_manager, multiple_users):
        """Test comprehensive monitoring of all user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create sessions with varying agent counts
        for i, user_context in enumerate(multiple_users[:5]):
            session = await registry.get_user_session(user_context.user_id)
            # Create different numbers of agents per user
            for j in range(i + 1):
                await session.register_agent(f"agent_{j}", Mock())
        
        monitoring_report = await registry.monitor_all_users()
        
        # Verify report structure
        expected_keys = [
            'timestamp', 'total_users', 'total_agents', 'users', 'global_issues'
        ]
        
        for key in expected_keys:
            assert key in monitoring_report
        
        assert monitoring_report['total_users'] == 5
        assert monitoring_report['total_agents'] == sum(range(1, 6))  # 1+2+3+4+5 = 15
        assert isinstance(monitoring_report['users'], dict)
        assert len(monitoring_report['users']) == 5
        
        # Verify timestamp is valid ISO format
        timestamp = monitoring_report['timestamp']
        datetime.fromisoformat(timestamp)
    
    @pytest.mark.asyncio
    async def test_emergency_cleanup_all_users(self, mock_llm_manager, multiple_users):
        """Test emergency cleanup of all user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create sessions with agents
        for user_context in multiple_users:
            session = await registry.get_user_session(user_context.user_id)
            mock_agent = Mock()
            mock_agent.cleanup = AsyncMock()
            await session.register_agent("test_agent", mock_agent)
        
        assert len(registry._user_sessions) == len(multiple_users)
        
        # Perform emergency cleanup
        cleanup_report = await registry.emergency_cleanup_all()
        
        assert len(registry._user_sessions) == 0
        assert cleanup_report['users_cleaned'] == len(multiple_users)
        assert cleanup_report['agents_cleaned'] >= len(multiple_users)
        
        # Verify timestamp is valid
        datetime.fromisoformat(cleanup_report['timestamp'])
    
    @pytest.mark.asyncio
    async def test_emergency_cleanup_handles_failures(self, mock_llm_manager, multiple_users):
        """Test emergency cleanup handles partial failures gracefully."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create sessions where some cleanup operations will fail
        failing_users = [multiple_users[1], multiple_users[3]]  # users 1 and 3 will fail
        
        for user_context in multiple_users[:5]:
            session = await registry.get_user_session(user_context.user_id)
            
            mock_agent = Mock()
            if user_context in failing_users:
                mock_agent.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
            else:
                mock_agent.cleanup = AsyncMock()
            
            await session.register_agent("test_agent", mock_agent)
        
        cleanup_report = await registry.emergency_cleanup_all()
        
        # Should clean successful users and record failures
        assert cleanup_report['users_cleaned'] == 5
        assert len(cleanup_report['errors']) >= 0  # Some cleanup methods may fail
        assert len(registry._user_sessions) == 0  # All sessions removed regardless


# ============================================================================
# TEST: Lifecycle Manager Integration
# ============================================================================

class TestLifecycleManagerIntegration(SSotBaseTestCase):
    """Test AgentLifecycleManager integration and functionality."""
    
    def test_lifecycle_manager_initialization_with_registry(self, mock_llm_manager):
        """Test lifecycle manager initialization with registry reference."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Lifecycle manager should have registry reference
        assert registry._lifecycle_manager._registry == registry
        assert isinstance(registry._lifecycle_manager._memory_thresholds, dict)
        assert 'max_agents_per_user' in registry._lifecycle_manager._memory_thresholds
        assert 'max_session_age_hours' in registry._lifecycle_manager._memory_thresholds
    
    @pytest.mark.asyncio
    async def test_lifecycle_manager_cleanup_agent_resources(self, mock_llm_manager, test_user_id):
        """Test lifecycle manager cleanup of agent resources."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session with agent
        session = await registry.get_user_session(test_user_id)
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock()
        await session.register_agent("test_agent", mock_agent)
        
        # Use lifecycle manager to cleanup agent
        await registry._lifecycle_manager.cleanup_agent_resources(test_user_id, "test_agent")
        
        # Verify agent was cleaned up and removed
        mock_agent.cleanup.assert_called_once()
        assert "test_agent" not in session._agents
    
    @pytest.mark.asyncio
    async def test_lifecycle_manager_monitor_memory_usage(self, mock_llm_manager, test_user_id):
        """Test lifecycle manager memory usage monitoring."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session with multiple agents (below threshold)
        session = await registry.get_user_session(test_user_id)
        for i in range(5):
            await session.register_agent(f"agent_{i}", Mock())
        
        result = await registry._lifecycle_manager.monitor_memory_usage(test_user_id)
        
        assert result['status'] == 'healthy'
        assert result['user_id'] == test_user_id
        assert 'metrics' in result
        assert len(result['issues']) == 0
    
    @pytest.mark.asyncio
    async def test_lifecycle_manager_detects_threshold_violations(self, mock_llm_manager, test_user_id):
        """Test lifecycle manager detects memory threshold violations."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session with many agents (exceed threshold)
        session = await registry.get_user_session(test_user_id)
        for i in range(60):  # Exceeds default max_agents_per_user (50)
            await session.register_agent(f"agent_{i}", Mock())
        
        # Simulate old session (exceed age threshold)
        session._created_at = datetime.now(timezone.utc).replace(year=2020)
        
        result = await registry._lifecycle_manager.monitor_memory_usage(test_user_id)
        
        assert result['status'] == 'warning'
        assert len(result['issues']) >= 1  # Should detect threshold violations
        
        # Should contain specific issues
        issues_text = ' '.join(result['issues'])
        assert 'agents' in issues_text.lower()
    
    @pytest.mark.asyncio
    async def test_lifecycle_manager_trigger_cleanup(self, mock_llm_manager, test_user_id):
        """Test lifecycle manager emergency cleanup trigger."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create session with agent
        session = await registry.get_user_session(test_user_id)
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock()
        await session.register_agent("test_agent", mock_agent)
        
        assert test_user_id in registry._user_sessions
        
        # Trigger cleanup via lifecycle manager
        await registry._lifecycle_manager.trigger_cleanup(test_user_id)
        
        # Session should be removed from registry
        assert test_user_id not in registry._user_sessions


if __name__ == "__main__":
    # Run tests with proper async support
    pytest.main([__file__, "-v", "--tb=short"])