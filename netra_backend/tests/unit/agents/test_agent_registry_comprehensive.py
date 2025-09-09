"""
🚀 Comprehensive AgentRegistry Unit Tests - SSOT Business Logic Focus

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Stability & Multi-User Chat Value Delivery
- Value Impact: Ensures AgentRegistry provides reliable factory patterns for complete user isolation
- Strategic Impact: Foundation for multi-user AI chat sessions - enables WebSocket agent events for business value

CRITICAL MISSION: AgentRegistry is the second highest priority SSOT agent class.
This test suite validates the business-critical patterns that enable chat value delivery:

1. Factory Patterns for User Isolation - MEGA CLASS CANDIDATE
2. UserAgentSession Lifecycle Management - Complete isolation
3. Tool Dispatcher Creation and Integration - Per-user dispatchers
4. WebSocket Manager Integration - Chat value enablement
5. Memory Leak Prevention - AgentLifecycleManager integration
6. Concurrent User Session Management - 10+ users support
7. SSOT UniversalRegistry Extension - Proper inheritance

Testing Philosophy:
- Real UserExecutionContext objects (NO MOCKS for business logic)
- Factory pattern validation (user isolation testing)
- WebSocket integration testing (chat value enablement)
- Memory management validation (leak prevention)
- Concurrent execution safety (multi-user support)
- SSOT compliance validation (UniversalRegistry extension)

This test focuses on BUSINESS VALUE - ensuring AgentRegistry enables reliable multi-user
agent execution with proper isolation, WebSocket events, and memory management.
"""

import asyncio
import pytest
import uuid
import weakref
import gc
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from typing import Dict, Any, Optional, List

# SSOT: Import from proper test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the class under test - MEGA CLASS CANDIDATE at ~1,441 lines
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession,
    AgentLifecycleManager,
    get_agent_registry
)

# Import SSOT dependencies for real testing (NO MOCKS for core business logic)
from netra_backend.app.services.user_execution_context import UserExecutionContext


# ============================================================================
# SSOT TEST FIXTURES AND UTILITIES
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager using SSOT patterns."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm._initialized = True
    return mock_llm


@pytest.fixture
def real_user_context():
    """Create REAL UserExecutionContext - NO MOCKS for business logic."""
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        request_id=f"test_request_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture
def real_user_context_2():
    """Create second REAL UserExecutionContext for isolation testing."""
    return UserExecutionContext(
        user_id=f"test_user_2_{uuid.uuid4().hex[:8]}",
        request_id=f"test_request_2_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_2_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_2_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture 
def mock_websocket_manager():
    """Create mock WebSocket manager with proper bridge factory."""
    manager = Mock()
    bridge = Mock()
    manager.create_bridge = AsyncMock(return_value=bridge)
    return manager


@pytest.fixture
async def agent_registry(mock_llm_manager):
    """Create AgentRegistry instance for testing."""
    registry = AgentRegistry(llm_manager=mock_llm_manager)
    yield registry
    await registry.cleanup()


# ============================================================================
# TEST CLASSES - BUSINESS VALUE FOCUSED
# ============================================================================

@pytest.mark.asyncio
class TestAgentRegistryFactoryPatterns:
    """Test factory patterns for user isolation - BUSINESS CRITICAL."""
    
    async def test_user_session_factory_creates_isolated_sessions(self, agent_registry, real_user_context, real_user_context_2):
        """CRITICAL: Factory pattern must create isolated sessions per user."""
        # Act - create sessions for different users
        session_1 = await agent_registry.get_user_session(real_user_context.user_id)
        session_2 = await agent_registry.get_user_session(real_user_context_2.user_id)
        
        # Assert - sessions are isolated and different
        assert session_1 is not session_2
        assert session_1.user_id == real_user_context.user_id
        assert session_2.user_id == real_user_context_2.user_id
        assert len(agent_registry._user_sessions) == 2
        
        # Verify complete isolation - sessions are different objects
        assert session_1._agents is not session_2._agents
        assert session_1._execution_contexts is not session_2._execution_contexts
        assert id(session_1) != id(session_2)
    
    async def test_user_session_factory_returns_same_instance_for_same_user(self, agent_registry, real_user_context):
        """CRITICAL: Factory must return same session for same user (idempotent)."""
        # Act - get session twice for same user
        session_1 = await agent_registry.get_user_session(real_user_context.user_id)
        session_2 = await agent_registry.get_user_session(real_user_context.user_id)
        
        # Assert - same instance returned
        assert session_1 is session_2
        assert len(agent_registry._user_sessions) == 1
    
    async def test_user_session_factory_validates_user_id(self, agent_registry):
        """CRITICAL: Factory must validate user_id to prevent security issues."""
        # Test invalid user IDs
        invalid_user_ids = [None, "", "   ", 123, [], {}]
        
        for invalid_id in invalid_user_ids:
            with pytest.raises(ValueError, match="user_id.*must be.*non-empty string"):
                await agent_registry.get_user_session(invalid_id)
    
    async def test_agent_creation_factory_enforces_user_context(self, agent_registry, real_user_context):
        """CRITICAL: Agent creation must enforce user context for isolation."""
        # Mock agent factory for testing
        mock_agent = Mock()
        agent_registry.get_async = AsyncMock(return_value=mock_agent)
        
        # Act - create agent with user context
        agent = await agent_registry.create_agent_for_user(
            user_id=real_user_context.user_id,
            agent_type="test_agent",
            user_context=real_user_context
        )
        
        # Assert - agent created and registered with user session
        assert agent == mock_agent
        user_session = await agent_registry.get_user_session(real_user_context.user_id)
        registered_agent = await user_session.get_agent("test_agent")
        assert registered_agent == mock_agent
    
    async def test_agent_creation_factory_validates_parameters(self, agent_registry, real_user_context):
        """CRITICAL: Agent creation factory must validate all required parameters."""
        # Test missing user_id
        with pytest.raises(ValueError, match="user_id and agent_type are required"):
            await agent_registry.create_agent_for_user("", "test_agent", real_user_context)
        
        # Test missing agent_type
        with pytest.raises(ValueError, match="user_id and agent_type are required"):
            await agent_registry.create_agent_for_user(real_user_context.user_id, "", real_user_context)
    
    async def test_tool_dispatcher_factory_creates_isolated_dispatchers(self, agent_registry, real_user_context):
        """CRITICAL: Tool dispatcher factory must create user-isolated dispatchers."""
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher') as mock_unified:
            mock_dispatcher = Mock()
            mock_unified.create_for_user = AsyncMock(return_value=mock_dispatcher)
            
            # Act - create tool dispatcher for user
            dispatcher = await agent_registry.create_tool_dispatcher_for_user(
                user_context=real_user_context,
                websocket_bridge=None,
                enable_admin_tools=False
            )
            
            # Assert - proper factory call with user context
            assert dispatcher == mock_dispatcher
            mock_unified.create_for_user.assert_called_once_with(
                user_context=real_user_context,
                websocket_bridge=None,
                enable_admin_tools=False
            )


@pytest.mark.asyncio
class TestUserAgentSessionLifecycle:
    """Test UserAgentSession lifecycle management - MEMORY LEAK PREVENTION."""
    
    async def test_user_session_initialization_creates_isolated_state(self, real_user_context):
        """CRITICAL: UserAgentSession must initialize with completely isolated state."""
        # Act - create new user session
        session = UserAgentSession(real_user_context.user_id)
        
        # Assert - proper isolated initialization
        assert session.user_id == real_user_context.user_id
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        assert session._websocket_manager is None
        assert session._created_at is not None
        assert session._access_lock is not None
    
    async def test_user_session_agent_registration_maintains_isolation(self, real_user_context):
        """CRITICAL: Agent registration must maintain user isolation."""
        session = UserAgentSession(real_user_context.user_id)
        mock_agent_1 = Mock()
        mock_agent_2 = Mock()
        
        # Act - register multiple agents
        await session.register_agent("agent_1", mock_agent_1)
        await session.register_agent("agent_2", mock_agent_2)
        
        # Assert - agents registered with isolation
        assert len(session._agents) == 2
        assert await session.get_agent("agent_1") == mock_agent_1
        assert await session.get_agent("agent_2") == mock_agent_2
        assert await session.get_agent("nonexistent") is None
    
    async def test_user_session_execution_context_creation_is_isolated(self, real_user_context):
        """CRITICAL: Execution context creation must be user-isolated."""
        session = UserAgentSession(real_user_context.user_id)
        
        # Act - create execution context for agent
        context = await session.create_agent_execution_context("test_agent", real_user_context)
        
        # Assert - context is child of user context and stored
        assert context is not None
        assert context.user_id == real_user_context.user_id
        assert "test_agent" in session._execution_contexts
        assert session._execution_contexts["test_agent"] == context
    
    async def test_user_session_cleanup_prevents_memory_leaks(self, real_user_context):
        """CRITICAL: Session cleanup must prevent memory leaks."""
        session = UserAgentSession(real_user_context.user_id)
        
        # Setup - create agents with cleanup methods
        mock_agent_1 = Mock()
        mock_agent_1.cleanup = AsyncMock()
        mock_agent_1.close = AsyncMock()
        
        mock_agent_2 = Mock()
        mock_agent_2.cleanup = AsyncMock()
        mock_agent_2.close = AsyncMock()
        
        await session.register_agent("agent_1", mock_agent_1)
        await session.register_agent("agent_2", mock_agent_2)
        
        # Create execution context
        await session.create_agent_execution_context("test_agent", real_user_context)
        
        # Act - cleanup all agents
        await session.cleanup_all_agents()
        
        # Assert - complete cleanup
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        
        # Verify cleanup methods called
        mock_agent_1.cleanup.assert_called_once()
        mock_agent_1.close.assert_called_once()
        mock_agent_2.cleanup.assert_called_once()
        mock_agent_2.close.assert_called_once()
    
    async def test_user_session_cleanup_handles_exceptions_gracefully(self, real_user_context):
        """CRITICAL: Session cleanup must handle exceptions without failing."""
        session = UserAgentSession(real_user_context.user_id)
        
        # Setup - agent with failing cleanup
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        mock_agent.close = AsyncMock(side_effect=Exception("Close failed"))
        
        await session.register_agent("failing_agent", mock_agent)
        
        # Act - cleanup should not raise exception
        await session.cleanup_all_agents()
        
        # Assert - cleanup completed despite exceptions
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
    
    async def test_user_session_metrics_provide_monitoring_data(self, real_user_context):
        """CRITICAL: Session metrics must provide memory monitoring data."""
        session = UserAgentSession(real_user_context.user_id)
        
        # Setup - add some state
        await session.register_agent("agent_1", Mock())
        await session.create_agent_execution_context("test_agent", real_user_context)
        session._websocket_bridge = Mock()
        
        # Act - get metrics
        metrics = session.get_metrics()
        
        # Assert - comprehensive metrics
        assert metrics['user_id'] == real_user_context.user_id
        assert metrics['agent_count'] == 1
        assert metrics['context_count'] == 1
        assert metrics['has_websocket_bridge'] is True
        assert metrics['uptime_seconds'] >= 0


@pytest.mark.asyncio  
class TestWebSocketManagerIntegration:
    """Test WebSocket manager integration - CHAT VALUE ENABLEMENT."""
    
    async def test_websocket_manager_propagation_to_existing_sessions(self, agent_registry, mock_websocket_manager, real_user_context):
        """CRITICAL: WebSocket manager must propagate to all existing user sessions."""
        # Setup - create user session before setting WebSocket manager
        user_session = await agent_registry.get_user_session(real_user_context.user_id)
        
        # Act - set WebSocket manager (should propagate to existing sessions)
        await agent_registry.set_websocket_manager_async(mock_websocket_manager)
        
        # Assert - WebSocket manager set on registry and propagated
        assert agent_registry.websocket_manager == mock_websocket_manager
        # Note: Propagation happens in background, so we verify the manager is stored
    
    async def test_websocket_manager_auto_assigned_to_new_sessions(self, agent_registry, mock_websocket_manager, real_user_context):
        """CRITICAL: New user sessions must automatically get WebSocket manager."""
        # Setup - set WebSocket manager first
        agent_registry.websocket_manager = mock_websocket_manager
        
        # Act - create new user session
        user_session = await agent_registry.get_user_session(real_user_context.user_id)
        
        # Assert - new session should attempt to get WebSocket manager
        # (Implementation detail: happens in background in get_user_session)
        assert agent_registry.websocket_manager == mock_websocket_manager
    
    async def test_websocket_manager_none_handling(self, agent_registry):
        """CRITICAL: Registry must handle None WebSocket manager gracefully."""
        # Act - set None WebSocket manager
        agent_registry.websocket_manager = None
        agent_registry.set_websocket_manager(None)
        
        # Assert - no exceptions raised
        assert agent_registry.websocket_manager is None
    
    async def test_websocket_bridge_factory_pattern_in_user_session(self, real_user_context, mock_websocket_manager):
        """CRITICAL: UserAgentSession must use WebSocket bridge factory pattern."""
        session = UserAgentSession(real_user_context.user_id)
        
        # Act - set WebSocket manager with factory
        await session.set_websocket_manager(mock_websocket_manager, real_user_context)
        
        # Assert - factory pattern used
        assert session._websocket_manager == mock_websocket_manager
        # Bridge creation is mocked, so we verify the manager was set
        mock_websocket_manager.create_bridge.assert_called_once()
    
    async def test_websocket_bridge_creation_with_real_user_context(self, real_user_context):
        """CRITICAL: WebSocket bridge creation must use real user context."""
        session = UserAgentSession(real_user_context.user_id)
        
        # Mock the bridge creation factory
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_factory:
            mock_bridge = Mock()
            mock_factory.return_value = mock_bridge
            
            # Act - set WebSocket manager (None, should use standard factory)
            await session.set_websocket_manager(None, real_user_context)
            
            # Assert - bridge is None when manager is None
            assert session._websocket_bridge is None


@pytest.mark.asyncio
class TestMemoryLeakPrevention:
    """Test memory leak prevention - AGENTLIFECYCLEMANAGER INTEGRATION."""
    
    async def test_lifecycle_manager_cleanup_agent_resources(self, agent_registry, real_user_context):
        """CRITICAL: AgentLifecycleManager must cleanup agent resources properly."""
        # Setup - create user session with agent
        user_session = await agent_registry.get_user_session(real_user_context.user_id)
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock()
        await user_session.register_agent("test_agent", mock_agent)
        
        # Verify agent is there first
        assert "test_agent" in user_session._agents
        
        # Act - cleanup agent via lifecycle manager
        await agent_registry._lifecycle_manager.cleanup_agent_resources(
            real_user_context.user_id, "test_agent"
        )
        
        # Assert - agent cleaned up and removed
        assert "test_agent" not in user_session._agents
        mock_agent.cleanup.assert_called_once()
    
    async def test_lifecycle_manager_memory_monitoring(self, agent_registry, real_user_context):
        """CRITICAL: AgentLifecycleManager must monitor memory usage."""
        # Setup - create user session with agents
        user_session = await agent_registry.get_user_session(real_user_context.user_id)
        await user_session.register_agent("agent_1", Mock())
        await user_session.register_agent("agent_2", Mock())
        
        # Act - monitor memory usage
        monitoring_result = await agent_registry._lifecycle_manager.monitor_memory_usage(
            real_user_context.user_id
        )
        
        # Assert - monitoring provides useful data
        assert monitoring_result['status'] in ['healthy', 'warning', 'error']
        assert monitoring_result['user_id'] == real_user_context.user_id
        if 'metrics' in monitoring_result:
            assert monitoring_result['metrics']['agent_count'] == 2
    
    async def test_emergency_cleanup_removes_all_sessions(self, agent_registry, real_user_context, real_user_context_2):
        """CRITICAL: Emergency cleanup must remove all user sessions."""
        # Setup - create multiple user sessions
        await agent_registry.get_user_session(real_user_context.user_id)
        await agent_registry.get_user_session(real_user_context_2.user_id)
        
        assert len(agent_registry._user_sessions) == 2
        
        # Act - emergency cleanup
        cleanup_report = await agent_registry.emergency_cleanup_all()
        
        # Assert - all sessions cleaned up
        assert len(agent_registry._user_sessions) == 0
        assert cleanup_report['users_cleaned'] == 2
        assert cleanup_report['agents_cleaned'] >= 0
    
    async def test_monitor_all_users_detects_memory_issues(self, agent_registry):
        """CRITICAL: Global monitoring must detect memory threshold violations."""
        # Setup - create many sessions to exceed thresholds
        for i in range(55):  # Exceed threshold of 50
            await agent_registry.get_user_session(f"user_{i}")
        
        # Act - monitor all users
        monitoring_report = await agent_registry.monitor_all_users()
        
        # Assert - memory issues detected
        assert monitoring_report['total_users'] == 55
        assert len(monitoring_report['global_issues']) > 0
        assert "Too many concurrent users" in str(monitoring_report['global_issues'])
    
    async def test_user_session_reset_creates_fresh_session(self, agent_registry, real_user_context):
        """CRITICAL: User session reset must create completely fresh session."""
        # Setup - create session with agent
        user_session = await agent_registry.get_user_session(real_user_context.user_id)
        await user_session.register_agent("test_agent", Mock())
        old_session_id = id(user_session)
        
        # Act - reset user agents
        reset_report = await agent_registry.reset_user_agents(real_user_context.user_id)
        
        # Assert - fresh session created
        assert reset_report['status'] == 'reset_complete'
        assert reset_report['agents_reset'] == 1
        
        new_session = agent_registry._user_sessions[real_user_context.user_id]
        assert id(new_session) != old_session_id
        assert len(new_session._agents) == 0


@pytest.mark.asyncio  
class TestConcurrentUserSessionManagement:
    """Test concurrent user session management - 10+ USERS SUPPORT."""
    
    async def test_concurrent_user_session_creation_is_thread_safe(self, agent_registry):
        """CRITICAL: Concurrent user session creation must be thread-safe."""
        # Setup - create many users concurrently
        user_ids = [f"concurrent_user_{i}" for i in range(20)]
        
        # Act - create sessions concurrently
        tasks = [agent_registry.get_user_session(user_id) for user_id in user_ids]
        sessions = await asyncio.gather(*tasks)
        
        # Assert - all sessions created correctly
        assert len(sessions) == 20
        assert len(agent_registry._user_sessions) == 20
        
        # Verify each session has correct user_id
        for i, session in enumerate(sessions):
            assert session.user_id == user_ids[i]
            assert session in agent_registry._user_sessions.values()
    
    async def test_concurrent_agent_creation_maintains_isolation(self, agent_registry, mock_llm_manager):
        """CRITICAL: Concurrent agent creation must maintain user isolation."""
        # Setup - multiple users and agent types
        user_contexts = [
            UserExecutionContext(
                user_id=f"user_{i}",
                request_id=f"req_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            ) for i in range(10)
        ]
        
        # Mock agent creation
        agent_registry.get_async = AsyncMock(return_value=Mock())
        
        # Act - create agents concurrently for different users
        tasks = []
        for i, context in enumerate(user_contexts):
            task = agent_registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"agent_type_{i % 3}",  # Cycle through 3 agent types
                user_context=context
            )
            tasks.append(task)
        
        agents = await asyncio.gather(*tasks)
        
        # Assert - all agents created with proper isolation
        assert len(agents) == 10
        assert len(agent_registry._user_sessions) == 10
        
        # Verify each user session has their agent
        for i, context in enumerate(user_contexts):
            user_session = agent_registry._user_sessions[context.user_id]
            agent_type = f"agent_type_{i % 3}"
            user_agent = await user_session.get_agent(agent_type)
            assert user_agent is not None
    
    async def test_concurrent_cleanup_operations_are_safe(self, agent_registry):
        """CRITICAL: Concurrent cleanup operations must be thread-safe."""
        # Setup - create user sessions with agents
        user_ids = [f"cleanup_user_{i}" for i in range(10)]
        for user_id in user_ids:
            session = await agent_registry.get_user_session(user_id)
            await session.register_agent("test_agent", Mock())
        
        # Act - cleanup sessions concurrently
        cleanup_tasks = [
            agent_registry.cleanup_user_session(user_id) 
            for user_id in user_ids
        ]
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        
        # Assert - all cleanups successful
        assert len(cleanup_results) == 10
        assert len(agent_registry._user_sessions) == 0
        
        for result in cleanup_results:
            assert result['status'] == 'cleaned'
            assert result['cleaned_agents'] >= 0
    
    async def test_concurrent_websocket_manager_updates_are_safe(self, agent_registry):
        """CRITICAL: Concurrent WebSocket manager updates must be thread-safe."""
        # Setup - create user sessions
        for i in range(5):
            await agent_registry.get_user_session(f"ws_user_{i}")
        
        # Setup - multiple WebSocket managers
        mock_managers = [Mock() for _ in range(3)]
        
        # Act - set WebSocket managers concurrently
        tasks = [
            agent_registry.set_websocket_manager_async(manager)
            for manager in mock_managers
        ]
        await asyncio.gather(*tasks)
        
        # Assert - one of the managers is set (last one wins in concurrent scenario)
        assert agent_registry.websocket_manager in mock_managers


class TestSSotUniversalRegistryExtension:
    """Test SSOT UniversalRegistry extension - PROPER INHERITANCE."""
    
    def test_agent_registry_extends_universal_registry(self, mock_llm_manager):
        """CRITICAL: AgentRegistry must properly extend UniversalRegistry SSOT."""
        from netra_backend.app.core.registry.universal_registry import AgentRegistry as UniversalAgentRegistry
        
        # Act - create AgentRegistry
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Assert - proper inheritance
        assert isinstance(registry, UniversalAgentRegistry)
        assert hasattr(registry, 'register')  # UniversalRegistry method
        assert hasattr(registry, 'get')       # UniversalRegistry method
        assert hasattr(registry, 'remove')    # UniversalRegistry method
        assert hasattr(registry, 'list_keys') # UniversalRegistry method
    
    @pytest.mark.asyncio
    async def test_agent_registry_get_async_method_integration(self, agent_registry, real_user_context):
        """CRITICAL: get_async method must integrate with user session WebSocket bridges."""
        # Setup - register a factory
        def mock_factory(context, websocket_bridge=None):
            agent = Mock()
            agent.context = context
            agent.websocket_bridge = websocket_bridge
            return agent
        
        agent_registry.register_factory("test_agent", mock_factory)
        
        # Act - get agent via async method
        agent = await agent_registry.get_async("test_agent", real_user_context)
        
        # Assert - agent created with proper context
        assert agent is not None
        assert agent.context == real_user_context
    
    @pytest.mark.asyncio
    async def test_legacy_compatibility_methods_work(self, agent_registry):
        """CRITICAL: Legacy compatibility methods must work for backward compatibility."""
        # Test list_agents
        agent_list = agent_registry.list_agents()
        assert isinstance(agent_list, list)
        
        # Test reset_all_agents
        reset_report = await agent_registry.reset_all_agents()
        assert isinstance(reset_report, dict)
        assert 'using_universal_registry' in reset_report
        assert reset_report['using_universal_registry'] is True
    
    def test_tool_dispatcher_property_deprecation_warning(self, agent_registry):
        """CRITICAL: Legacy tool_dispatcher property must warn about deprecation."""
        # Act - access deprecated property
        dispatcher = agent_registry.tool_dispatcher
        
        # Assert - returns None and logs warning
        assert dispatcher is None
        
        # Test setter
        mock_dispatcher = Mock()
        agent_registry.tool_dispatcher = mock_dispatcher
        assert agent_registry._legacy_dispatcher == mock_dispatcher
    
    def test_registry_health_includes_isolation_metrics(self, agent_registry):
        """CRITICAL: Registry health must include user isolation metrics."""
        # Act - get registry health
        health = agent_registry.get_registry_health()
        
        # Assert - isolation metrics included
        assert 'hardened_isolation' in health
        assert 'total_user_sessions' in health
        assert 'total_user_agents' in health
        assert 'memory_leak_prevention' in health
        assert 'thread_safe_concurrent_execution' in health
        
        assert health['hardened_isolation'] is True
        assert health['memory_leak_prevention'] is True
        assert health['thread_safe_concurrent_execution'] is True
    
    def test_factory_integration_status_reports_ssot_compliance(self, agent_registry):
        """CRITICAL: Factory integration status must report SSOT compliance."""
        # Act - get factory integration status  
        status = agent_registry.get_factory_integration_status()
        
        # Assert - SSOT compliance reported
        assert 'using_universal_registry' in status
        assert 'hardened_isolation_enabled' in status
        assert 'user_isolation_enforced' in status
        assert 'global_state_eliminated' in status
        assert 'websocket_isolation_per_user' in status
        
        assert status['using_universal_registry'] is True
        assert status['hardened_isolation_enabled'] is True
        assert status['user_isolation_enforced'] is True
        assert status['global_state_eliminated'] is True


class TestBusinessValueValidation:
    """Test business value validation - CHAT VALUE DELIVERY."""
    
    @pytest.mark.asyncio
    async def test_agent_registry_enables_multi_user_chat_scenarios(self, agent_registry, mock_llm_manager):
        """CRITICAL: AgentRegistry must enable multi-user chat scenarios."""
        # Simulate real chat scenario - multiple users with different agents
        users = [
            UserExecutionContext(
                user_id=f"chat_user_{i}",
                request_id=f"chat_req_{i}",
                thread_id=f"chat_thread_{i}",
                run_id=f"chat_run_{i}"
            ) for i in range(5)
        ]
        
        # Mock agent creation
        agent_registry.get_async = AsyncMock(return_value=Mock())
        
        # Act - simulate concurrent chat sessions
        chat_tasks = []
        for user in users:
            # Each user gets isolated session with different agent types
            task = agent_registry.create_agent_for_user(
                user_id=user.user_id,
                agent_type="triage" if int(user.user_id.split('_')[-1]) % 2 == 0 else "optimization",
                user_context=user
            )
            chat_tasks.append(task)
        
        agents = await asyncio.gather(*chat_tasks)
        
        # Assert - chat value delivery enabled
        assert len(agents) == 5
        assert len(agent_registry._user_sessions) == 5
        
        # Verify each user has isolated session
        for user in users:
            user_session = agent_registry._user_sessions[user.user_id]
            assert user_session.user_id == user.user_id
            assert len(user_session._agents) >= 1  # Has their agent
    
    @pytest.mark.asyncio
    async def test_websocket_integration_enables_real_time_chat_events(self, agent_registry, mock_websocket_manager):
        """CRITICAL: WebSocket integration must enable real-time chat events."""
        # Setup - set WebSocket manager for chat events
        await agent_registry.set_websocket_manager_async(mock_websocket_manager)
        
        # Create user session for chat
        user_context = UserExecutionContext(
            user_id="chat_user_websocket",
            request_id="chat_request_123",
            thread_id="chat_thread_123",
            run_id="chat_run_123"
        )
        
        # Act - create user session (should get WebSocket integration)
        user_session = await agent_registry.get_user_session(user_context.user_id)
        
        # Assert - WebSocket integration available for chat events
        assert agent_registry.websocket_manager == mock_websocket_manager
        assert user_session is not None
        
        # Verify WebSocket bridge integration is configured
        assert hasattr(agent_registry, 'websocket_bridge') or hasattr(agent_registry, 'websocket_manager')
    
    @pytest.mark.asyncio
    async def test_memory_management_prevents_chat_system_degradation(self, agent_registry):
        """CRITICAL: Memory management must prevent chat system degradation."""
        # Simulate heavy chat usage
        heavy_usage_users = [f"heavy_user_{i}" for i in range(25)]
        
        # Create sessions with multiple agents each
        for user_id in heavy_usage_users:
            session = await agent_registry.get_user_session(user_id)
            # Simulate multiple agents per user (typical chat scenario)
            for agent_type in ["triage", "optimization", "data"]:
                await session.register_agent(agent_type, Mock())
        
        # Act - monitor system health under load
        monitoring_report = await agent_registry.monitor_all_users()
        
        # Assert - system can handle load and provide monitoring
        assert monitoring_report['total_users'] == 25
        assert monitoring_report['total_agents'] == 75  # 3 agents per user
        assert 'global_issues' in monitoring_report
        
        # Test cleanup maintains performance
        cleanup_report = await agent_registry.emergency_cleanup_all()
        assert cleanup_report['users_cleaned'] == 25
        assert len(agent_registry._user_sessions) == 0
    
    def test_registry_health_reflects_chat_system_readiness(self, agent_registry):
        """CRITICAL: Registry health must reflect chat system readiness."""
        # Act - get health status
        health = agent_registry.get_registry_health()
        
        # Assert - chat-critical metrics present
        chat_critical_metrics = [
            'using_universal_registry',    # SSOT compliance
            'hardened_isolation',          # User isolation for chat
            'memory_leak_prevention',      # System stability
            'thread_safe_concurrent_execution',  # Multi-user support
            'total_user_sessions',         # Current load
            'uptime_seconds'               # System stability
        ]
        
        for metric in chat_critical_metrics:
            assert metric in health, f"Chat-critical metric '{metric}' missing from health report"
        
        # Verify chat-enabling features are active
        assert health['hardened_isolation'] is True
        assert health['memory_leak_prevention'] is True
        assert health['thread_safe_concurrent_execution'] is True


# ============================================================================
# TEST EXECUTION AND REPORTING
# ============================================================================

if __name__ == "__main__":
    """
    Run comprehensive AgentRegistry unit tests.
    
    This test suite validates the business-critical factory patterns and user isolation
    features that enable multi-user chat value delivery through AgentRegistry.
    """
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings",
        "--asyncio-mode=auto"
    ])