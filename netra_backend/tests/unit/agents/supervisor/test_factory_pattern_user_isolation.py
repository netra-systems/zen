"""
Unit Tests for Factory Pattern User Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Complete user data isolation for multi-tenant platform
- Value Impact: Enables 10+ concurrent users with zero context leakage
- Strategic Impact: Foundation for secure multi-user AI platform

CRITICAL MISSION: Test Factory Pattern User Isolation ensuring:
1. AgentInstanceFactory complete user isolation patterns
2. UserWebSocketEmitter per-user isolation and cleanup
3. Factory-based context creation with user boundaries
4. Concurrent user execution without state sharing
5. User-scoped agent instantiation with proper cleanup
6. WebSocket event isolation per user session
7. Resource cleanup and memory management per user
8. Factory performance optimization with user context

FOCUS: Factory-based isolation patterns from USER_CONTEXT_ARCHITECTURE.md
"""

import asyncio
import pytest
import time
import uuid
import weakref
import gc
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserWebSocketEmitter,
    get_agent_instance_factory,
    configure_agent_instance_factory
)

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.base_agent import BaseAgent


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_websocket_bridge():
    """Create mock WebSocket bridge."""
    mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
    mock_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
    mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
    mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
    mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
    mock_bridge.notify_agent_error = AsyncMock(return_value=True)
    mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    mock_bridge.unregister_run_mapping = AsyncMock(return_value=True)
    return mock_bridge


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager."""
    mock_manager = Mock(spec=WebSocketManager)
    mock_manager.send_event = AsyncMock(return_value=True)
    mock_manager.is_connected = Mock(return_value=True)
    mock_manager.disconnect = AsyncMock()
    return mock_manager


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value="Test response")
    mock_llm.is_healthy = Mock(return_value=True)
    return mock_llm


@pytest.fixture
def mock_agent_class_registry():
    """Create mock agent class registry."""
    mock_registry = Mock()
    mock_registry.get_agent_class = Mock()
    mock_registry.list_agent_names = Mock(return_value=["test_agent", "data_agent"])
    return mock_registry


@pytest.fixture
def test_user_context():
    """Create test user execution context."""
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        request_id=f"test_request_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture
def multiple_user_contexts():
    """Create multiple user contexts for isolation testing."""
    contexts = []
    for i in range(5):
        context = UserExecutionContext(
            user_id=f"user_{i}_{uuid.uuid4().hex[:6]}",
            request_id=f"req_{i}_{uuid.uuid4().hex[:6]}",
            thread_id=f"thread_{i}_{uuid.uuid4().hex[:6]}",
            run_id=f"run_{i}_{uuid.uuid4().hex[:6]}"
        )
        contexts.append(context)
    return contexts


@pytest.fixture
def mock_agent_class():
    """Create mock agent class for testing."""
    class MockAgent:
        def __init__(self, llm_manager=None, tool_dispatcher=None):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.cleanup = AsyncMock()
            self.set_websocket_bridge = Mock()
            self._websocket_adapter = Mock()
            self._websocket_adapter.set_websocket_bridge = Mock()
        
        @classmethod
        def create_agent_with_context(cls, user_context):
            instance = cls()
            instance.user_context = user_context
            return instance
    
    return MockAgent


# ============================================================================
# TEST: AgentInstanceFactory Initialization and Configuration
# ============================================================================

class TestAgentInstanceFactoryInitialization(SSotBaseTestCase):
    """Test AgentInstanceFactory initialization and configuration."""
    
    def test_factory_basic_initialization(self):
        """Test basic factory initialization with default settings."""
        factory = AgentInstanceFactory()
        
        # Verify basic initialization
        assert factory._agent_class_registry is None
        assert factory._agent_registry is None  
        assert factory._websocket_bridge is None
        assert factory._websocket_manager is None
        assert factory._llm_manager is None
        assert factory._tool_dispatcher is None
        
        # Verify performance configuration loaded
        assert factory._performance_config is not None
        assert factory._max_concurrent_per_user > 0
        assert factory._execution_timeout > 0
        
        # Verify tracking structures initialized
        assert isinstance(factory._user_semaphores, dict)
        assert isinstance(factory._active_contexts, dict)
        assert isinstance(factory._factory_metrics, dict)
        assert factory._factory_metrics['total_instances_created'] == 0
    
    def test_factory_configuration_comprehensive(self, mock_websocket_bridge, mock_websocket_manager,
                                                mock_llm_manager, mock_agent_class_registry):
        """Test comprehensive factory configuration."""
        factory = AgentInstanceFactory()
        
        # Configure factory
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge,
            websocket_manager=mock_websocket_manager,
            llm_manager=mock_llm_manager,
            tool_dispatcher=Mock()
        )
        
        # Verify all components configured
        assert factory._agent_class_registry == mock_agent_class_registry
        assert factory._websocket_bridge == mock_websocket_bridge
        assert factory._websocket_manager == mock_websocket_manager
        assert factory._llm_manager == mock_llm_manager
        assert factory._tool_dispatcher is not None
    
    def test_factory_configuration_validation(self):
        """Test factory configuration validation."""
        factory = AgentInstanceFactory()
        
        # Test None websocket_bridge validation
        with pytest.raises(ValueError, match="AgentWebSocketBridge cannot be None"):
            factory.configure(websocket_bridge=None)
    
    def test_factory_configure_with_global_agent_registry(self, mock_websocket_bridge):
        """Test factory configuration with global agent class registry."""
        factory = AgentInstanceFactory()
        
        # Mock global registry
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry') as mock_get_registry:
            mock_registry = Mock()
            mock_registry.__len__ = Mock(return_value=5)  # Non-empty registry
            mock_get_registry.return_value = mock_registry
            
            factory.configure(websocket_bridge=mock_websocket_bridge)
            
            # Should use global registry
            assert factory._agent_class_registry == mock_registry
    
    def test_factory_dependency_validation(self, mock_websocket_bridge):
        """Test factory validates agent dependencies."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test dependency validation for LLM-requiring agents
        with pytest.raises(RuntimeError, match="Cannot create DataSubAgent: Required dependency 'llm_manager' not available"):
            factory._validate_agent_dependencies("DataSubAgent")
    
    def test_factory_singleton_pattern(self):
        """Test factory singleton pattern."""
        factory1 = get_agent_instance_factory()
        factory2 = get_agent_instance_factory()
        
        # Should return same instance
        assert factory1 is factory2
    
    @pytest.mark.asyncio
    async def test_configure_agent_instance_factory_function(self, mock_websocket_bridge, mock_llm_manager):
        """Test global factory configuration function."""
        factory = await configure_agent_instance_factory(
            websocket_bridge=mock_websocket_bridge,
            llm_manager=mock_llm_manager
        )
        
        assert isinstance(factory, AgentInstanceFactory)
        assert factory._websocket_bridge == mock_websocket_bridge
        assert factory._llm_manager == mock_llm_manager


# ============================================================================
# TEST: User Execution Context Creation and Isolation
# ============================================================================

class TestUserExecutionContextCreationAndIsolation(SSotBaseTestCase):
    """Test user execution context creation with complete isolation."""
    
    @pytest.mark.asyncio
    async def test_create_user_execution_context_success(self, mock_websocket_bridge):
        """Test successful user execution context creation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        
        # Create context
        context = await factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Verify context properties
        assert context.user_id == user_id
        assert context.thread_id == thread_id  
        assert context.run_id == run_id
        assert context.created_at is not None
        
        # Verify tracking
        context_id = f"{user_id}_{thread_id}_{run_id}"
        assert context_id in factory._active_contexts
        assert factory._factory_metrics['total_instances_created'] == 1
        assert factory._factory_metrics['active_contexts'] == 1
    
    @pytest.mark.asyncio
    async def test_create_user_execution_context_with_metadata(self, mock_websocket_bridge):
        """Test user context creation with metadata."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        metadata = {"source": "test", "priority": "high"}
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            metadata=metadata
        )
        
        assert context.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_create_user_execution_context_validation(self, mock_websocket_bridge):
        """Test user context creation validation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test missing parameters
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("", "thread", "run")
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("user", "", "run")
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("user", "thread", "")
    
    @pytest.mark.asyncio
    async def test_create_user_execution_context_unconfigured_factory(self):
        """Test context creation with unconfigured factory."""
        factory = AgentInstanceFactory()
        
        # Should raise error for unconfigured factory
        with pytest.raises(ValueError, match="Factory not configured - call configure\\(\\) first"):
            await factory.create_user_execution_context("user", "thread", "run")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_context_creation(self, mock_websocket_bridge, multiple_user_contexts):
        """Test concurrent user context creation maintains isolation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        async def create_context(user_context):
            return await factory.create_user_execution_context(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id
            )
        
        # Create contexts concurrently
        tasks = [create_context(ctx) for ctx in multiple_user_contexts]
        created_contexts = await asyncio.gather(*tasks)
        
        # Verify all contexts created successfully
        assert len(created_contexts) == len(multiple_user_contexts)
        assert factory._factory_metrics['active_contexts'] == len(multiple_user_contexts)
        
        # Verify each context has correct user isolation
        for i, context in enumerate(created_contexts):
            expected_user_id = multiple_user_contexts[i].user_id
            assert context.user_id == expected_user_id
            
            # Verify no cross-contamination
            for j, other_context in enumerate(created_contexts):
                if i != j:
                    assert context.user_id != other_context.user_id
                    assert context.run_id != other_context.run_id
    
    @pytest.mark.asyncio
    async def test_user_execution_scope_context_manager(self, mock_websocket_bridge):
        """Test user execution scope context manager for automatic cleanup."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        context = None
        user_id = f"scope_user_{uuid.uuid4().hex[:8]}"
        
        # Use context manager
        async with factory.user_execution_scope(user_id, "thread", "run") as ctx:
            context = ctx
            assert context.user_id == user_id
            assert factory._factory_metrics['active_contexts'] == 1
        
        # Context should be cleaned up automatically
        context_id = f"{user_id}_thread_run"
        assert context_id not in factory._active_contexts
        assert factory._factory_metrics['active_contexts'] == 0


# ============================================================================
# TEST: UserWebSocketEmitter Isolation
# ============================================================================

class TestUserWebSocketEmitterIsolation(SSotBaseTestCase):
    """Test UserWebSocketEmitter provides complete per-user isolation."""
    
    def test_user_websocket_emitter_initialization(self, mock_websocket_bridge):
        """Test UserWebSocketEmitter initialization with user binding."""
        user_id = "test_user"
        thread_id = "test_thread" 
        run_id = "test_run"
        
        emitter = UserWebSocketEmitter(user_id, thread_id, run_id, mock_websocket_bridge)
        
        assert emitter.user_id == user_id
        assert emitter.thread_id == thread_id
        assert emitter.run_id == run_id
        assert emitter.websocket_bridge == mock_websocket_bridge
        assert emitter.created_at is not None
        assert emitter._event_count == 0
        assert emitter._last_event_time is None
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_agent_started_notification(self, mock_websocket_bridge):
        """Test agent started notification isolation per user."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        # Send notification
        success = await emitter.notify_agent_started("test_agent", {"context": "test"})
        
        assert success is True
        assert emitter._event_count == 1
        assert emitter._last_event_time is not None
        
        # Verify bridge called with correct parameters
        mock_websocket_bridge.notify_agent_started.assert_called_once_with(
            run_id="run1",
            agent_name="test_agent", 
            context={"context": "test"}
        )
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_agent_thinking_notification(self, mock_websocket_bridge):
        """Test agent thinking notification with user isolation."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        success = await emitter.notify_agent_thinking("test_agent", "Processing data", 1, 25.0)
        
        assert success is True
        assert emitter._event_count == 1
        
        mock_websocket_bridge.notify_agent_thinking.assert_called_once_with(
            run_id="run1",
            agent_name="test_agent",
            reasoning="Processing data",
            step_number=1,
            progress_percentage=25.0
        )
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_tool_notifications(self, mock_websocket_bridge):
        """Test tool execution notifications with user context."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        # Test tool executing
        success1 = await emitter.notify_tool_executing("test_agent", "search_tool", {"query": "test"})
        assert success1 is True
        
        # Test tool completed
        success2 = await emitter.notify_tool_completed("test_agent", "search_tool", {"results": []}, 150.0)
        assert success2 is True
        
        assert emitter._event_count == 2
        
        # Verify both calls made with correct run_id
        mock_websocket_bridge.notify_tool_executing.assert_called_once_with(
            run_id="run1", agent_name="test_agent", tool_name="search_tool", parameters={"query": "test"}
        )
        mock_websocket_bridge.notify_tool_completed.assert_called_once_with(
            run_id="run1", agent_name="test_agent", tool_name="search_tool", 
            result={"results": []}, execution_time_ms=150.0
        )
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_agent_completed_notification(self, mock_websocket_bridge):
        """Test agent completed notification with user context."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        result = {"status": "success", "data": "processed"}
        success = await emitter.notify_agent_completed("test_agent", result, 5000.0)
        
        assert success is True
        mock_websocket_bridge.notify_agent_completed.assert_called_once_with(
            run_id="run1", agent_name="test_agent", result=result, execution_time_ms=5000.0
        )
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_error_notification(self, mock_websocket_bridge):
        """Test agent error notification handling."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        success = await emitter.notify_agent_error("test_agent", "Processing failed", {"step": 1})
        
        assert success is True
        mock_websocket_bridge.notify_agent_error.assert_called_once_with(
            run_id="run1", agent_name="test_agent", error="Processing failed", error_context={"step": 1}
        )
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_failure_handling(self, mock_websocket_bridge):
        """Test emitter handles WebSocket failures appropriately."""
        mock_websocket_bridge.notify_agent_started.return_value = False  # Simulate failure
        
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        # Should raise ConnectionError on failure
        with pytest.raises(ConnectionError, match="WebSocket bridge returned failure"):
            await emitter.notify_agent_started("test_agent")
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_exception_handling(self, mock_websocket_bridge):
        """Test emitter handles exceptions in WebSocket bridge."""
        mock_websocket_bridge.notify_agent_started.side_effect = Exception("Bridge error")
        
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        # Should raise RuntimeError with context
        with pytest.raises(RuntimeError, match="Agent communication failure"):
            await emitter.notify_agent_started("test_agent")
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_cleanup(self, mock_websocket_bridge):
        """Test proper cleanup of WebSocket emitter resources."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        # Send some events first
        await emitter.notify_agent_started("test_agent")
        await emitter.notify_agent_completed("test_agent")
        
        assert emitter._event_count == 2
        
        # Cleanup
        await emitter.cleanup()
        
        # Bridge reference should be cleared
        assert emitter.websocket_bridge is None
    
    def test_user_websocket_emitter_status_reporting(self, mock_websocket_bridge):
        """Test emitter status reporting for monitoring."""
        emitter = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        
        status = emitter.get_emitter_status()
        
        assert status['user_id'] == "user1"
        assert status['thread_id'] == "thread1" 
        assert status['run_id'] == "run1"
        assert status['event_count'] == 0
        assert status['last_event_time'] is None
        assert status['created_at'] is not None
        assert status['has_websocket_bridge'] is True
    
    @pytest.mark.asyncio
    async def test_multiple_user_emitters_isolation(self, mock_websocket_bridge):
        """Test multiple user emitters maintain complete isolation."""
        # Create emitters for different users
        emitter1 = UserWebSocketEmitter("user1", "thread1", "run1", mock_websocket_bridge)
        emitter2 = UserWebSocketEmitter("user2", "thread2", "run2", mock_websocket_bridge)
        emitter3 = UserWebSocketEmitter("user3", "thread3", "run3", mock_websocket_bridge)
        
        # Each emitter sends different events
        await emitter1.notify_agent_started("agent1")
        await emitter2.notify_agent_thinking("agent2", "thinking") 
        await emitter3.notify_tool_executing("agent3", "tool1")
        
        # Verify each emitter maintains its own state
        assert emitter1._event_count == 1
        assert emitter2._event_count == 1
        assert emitter3._event_count == 1
        
        # Verify no cross-contamination
        assert emitter1.user_id == "user1"
        assert emitter2.user_id == "user2" 
        assert emitter3.user_id == "user3"


# ============================================================================
# TEST: Agent Instance Creation with User Isolation
# ============================================================================

class TestAgentInstanceCreationWithUserIsolation(SSotBaseTestCase):
    """Test agent instance creation maintains complete user isolation."""
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_with_user_context(self, mock_websocket_bridge, 
                                                          test_user_context, mock_agent_class,
                                                          mock_agent_class_registry):
        """Test agent instance creation with proper user context binding."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        # Mock registry to return our test agent class
        mock_agent_class_registry.get_agent_class.return_value = mock_agent_class
        
        # Create agent instance
        agent = await factory.create_agent_instance("test_agent", test_user_context)
        
        assert agent is not None
        assert hasattr(agent, 'user_context')
        assert agent.user_context == test_user_context
        
        # Verify WebSocket bridge was set with correct run_id
        agent._websocket_adapter.set_websocket_bridge.assert_called_once()
        args, kwargs = agent._websocket_adapter.set_websocket_bridge.call_args
        assert args[0] == mock_websocket_bridge
        assert args[1] == test_user_context.run_id
        assert args[2] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_dependency_injection(self, mock_websocket_bridge,
                                                             test_user_context, mock_agent_class,
                                                             mock_agent_class_registry, mock_llm_manager):
        """Test agent instance creation with proper dependency injection."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge,
            llm_manager=mock_llm_manager
        )
        
        mock_agent_class_registry.get_agent_class.return_value = mock_agent_class
        
        # Create agent instance
        agent = await factory.create_agent_instance("test_agent", test_user_context)
        
        assert agent.llm_manager == mock_llm_manager
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_validation(self, mock_websocket_bridge, mock_agent_class_registry):
        """Test agent instance creation validation."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        # Test None user context
        with pytest.raises(ValueError, match="UserExecutionContext is required"):
            await factory.create_agent_instance("test_agent", None)
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_unknown_agent(self, mock_websocket_bridge, 
                                                       test_user_context, mock_agent_class_registry):
        """Test creation of unknown agent type."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        mock_agent_class_registry.get_agent_class.return_value = None
        mock_agent_class_registry.list_agent_names.return_value = ["known_agent"]
        
        with pytest.raises(ValueError, match="Agent 'unknown_agent' not found in AgentClassRegistry"):
            await factory.create_agent_instance("unknown_agent", test_user_context)
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_websocket_bridge_validation(self, test_user_context):
        """Test agent creation validates WebSocket bridge configuration."""
        factory = AgentInstanceFactory()
        # Don't configure WebSocket bridge
        
        with pytest.raises(RuntimeError, match="AgentInstanceFactory not configured"):
            await factory.create_agent_instance("test_agent", test_user_context)
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_instance_creation(self, mock_websocket_bridge, 
                                                     multiple_user_contexts, mock_agent_class,
                                                     mock_agent_class_registry):
        """Test concurrent agent instance creation maintains user isolation."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        mock_agent_class_registry.get_agent_class.return_value = mock_agent_class
        
        async def create_agent_for_user(user_context):
            return await factory.create_agent_instance("test_agent", user_context)
        
        # Create agents concurrently for different users
        tasks = [create_agent_for_user(ctx) for ctx in multiple_user_contexts]
        agents = await asyncio.gather(*tasks)
        
        # Verify all agents created successfully
        assert len(agents) == len(multiple_user_contexts)
        
        # Verify each agent has correct user context isolation
        for i, agent in enumerate(agents):
            expected_context = multiple_user_contexts[i]
            assert agent.user_context == expected_context
            
            # Verify no cross-contamination
            for j, other_agent in enumerate(agents):
                if i != j:
                    assert agent.user_context.user_id != other_agent.user_context.user_id
                    assert agent.user_context.run_id != other_agent.user_context.run_id


# ============================================================================
# TEST: User Context Cleanup and Resource Management
# ============================================================================

class TestUserContextCleanupAndResourceManagement(SSotBaseTestCase):
    """Test proper cleanup and resource management per user context."""
    
    @pytest.mark.asyncio
    async def test_cleanup_user_context_comprehensive(self, mock_websocket_bridge, test_user_context):
        """Test comprehensive user context cleanup."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create user context
        context = await factory.create_user_execution_context(
            user_id=test_user_context.user_id,
            thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id
        )
        
        context_id = f"{context.user_id}_{context.thread_id}_{context.run_id}"
        assert context_id in factory._active_contexts
        assert factory._factory_metrics['active_contexts'] == 1
        
        # Cleanup context
        await factory.cleanup_user_context(context)
        
        # Verify cleanup
        assert context_id not in factory._active_contexts
        assert factory._factory_metrics['active_contexts'] == 0
        assert factory._factory_metrics['total_contexts_cleaned'] == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_user_context_with_websocket_emitters(self, mock_websocket_bridge, test_user_context):
        """Test cleanup includes WebSocket emitters."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create context which creates emitter
        context = await factory.create_user_execution_context(
            user_id=test_user_context.user_id,
            thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id
        )
        
        context_id = f"{context.user_id}_{context.thread_id}_{context.run_id}"
        emitter_key = f"{context_id}_emitter"
        
        # Verify emitter was created and tracked
        assert hasattr(factory, '_websocket_emitters')
        assert emitter_key in factory._websocket_emitters
        
        # Cleanup context
        await factory.cleanup_user_context(context)
        
        # Verify emitter was cleaned up
        assert emitter_key not in factory._websocket_emitters
    
    @pytest.mark.asyncio
    async def test_cleanup_user_context_with_database_session(self, mock_websocket_bridge):
        """Test cleanup properly closes database session."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create mock database session
        mock_db_session = AsyncMock()
        mock_db_session.close = AsyncMock()
        
        # Create context with database session
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            db_session=mock_db_session
        )
        
        # Cleanup should close database session
        await factory.cleanup_user_context(context)
        
        mock_db_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_user_context_handles_exceptions(self, mock_websocket_bridge, test_user_context):
        """Test cleanup handles exceptions gracefully."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create context
        context = await factory.create_user_execution_context(
            user_id=test_user_context.user_id,
            thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id
        )
        
        # Create failing database session
        context.db_session = Mock()
        context.db_session.close = AsyncMock(side_effect=Exception("DB close failed"))
        
        # Cleanup should not raise exception
        await factory.cleanup_user_context(context)
        
        # Context should still be removed despite DB cleanup failure
        context_id = f"{context.user_id}_{context.thread_id}_{context.run_id}"
        assert context_id not in factory._active_contexts
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_contexts_by_age(self, mock_websocket_bridge):
        """Test cleanup of inactive contexts based on age."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create old and new contexts
        old_context = await factory.create_user_execution_context("old_user", "thread1", "run1")
        new_context = await factory.create_user_execution_context("new_user", "thread2", "run2")
        
        # Artificially age the old context
        old_context.created_at = datetime.now(timezone.utc).replace(year=2020)
        
        assert factory._factory_metrics['active_contexts'] == 2
        
        # Cleanup contexts older than 1 hour
        cleaned_count = await factory.cleanup_inactive_contexts(max_age_seconds=3600)
        
        # Only old context should be cleaned
        assert cleaned_count >= 1
        assert factory._factory_metrics['active_contexts'] < 2
    
    @pytest.mark.asyncio
    async def test_concurrent_context_cleanup_safety(self, mock_websocket_bridge, multiple_user_contexts):
        """Test concurrent context cleanup is thread-safe."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create multiple contexts
        contexts = []
        for user_ctx in multiple_user_contexts:
            context = await factory.create_user_execution_context(
                user_id=user_ctx.user_id,
                thread_id=user_ctx.thread_id,
                run_id=user_ctx.run_id
            )
            contexts.append(context)
        
        assert factory._factory_metrics['active_contexts'] == len(contexts)
        
        # Cleanup contexts concurrently
        cleanup_tasks = [factory.cleanup_user_context(ctx) for ctx in contexts]
        await asyncio.gather(*cleanup_tasks)
        
        # All contexts should be cleaned up
        assert factory._factory_metrics['active_contexts'] == 0
        assert factory._factory_metrics['total_contexts_cleaned'] == len(contexts)


# ============================================================================
# TEST: Factory Performance Metrics and Monitoring
# ============================================================================

class TestFactoryPerformanceMetricsAndMonitoring(SSotBaseTestCase):
    """Test factory performance metrics and monitoring capabilities."""
    
    def test_factory_metrics_initialization(self):
        """Test factory metrics are properly initialized."""
        factory = AgentInstanceFactory()
        
        metrics = factory.get_factory_metrics()
        
        # Verify all expected metrics present
        expected_metrics = [
            'total_instances_created', 'active_contexts', 'total_contexts_cleaned',
            'creation_errors', 'cleanup_errors', 'average_context_lifetime_seconds',
            'user_semaphores_count', 'max_concurrent_per_user', 'execution_timeout',
            'cleanup_interval', 'active_context_ids', 'configuration_status',
            'performance_config'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
        
        # Verify initial values
        assert metrics['total_instances_created'] == 0
        assert metrics['active_contexts'] == 0
        assert metrics['total_contexts_cleaned'] == 0
        assert isinstance(metrics['active_context_ids'], list)
        assert len(metrics['active_context_ids']) == 0
    
    @pytest.mark.asyncio
    async def test_factory_metrics_tracking_lifecycle(self, mock_websocket_bridge):
        """Test factory metrics track complete lifecycle."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create context (should increment creation metrics)
        context = await factory.create_user_execution_context("test_user", "thread", "run")
        
        metrics_after_creation = factory.get_factory_metrics()
        assert metrics_after_creation['total_instances_created'] == 1
        assert metrics_after_creation['active_contexts'] == 1
        assert len(metrics_after_creation['active_context_ids']) == 1
        
        # Cleanup context (should increment cleanup metrics)
        await factory.cleanup_user_context(context)
        
        metrics_after_cleanup = factory.get_factory_metrics()
        assert metrics_after_cleanup['total_instances_created'] == 1  # Unchanged
        assert metrics_after_cleanup['active_contexts'] == 0
        assert metrics_after_cleanup['total_contexts_cleaned'] == 1
        assert len(metrics_after_cleanup['active_context_ids']) == 0
    
    def test_factory_configuration_status_reporting(self, mock_websocket_bridge, mock_websocket_manager):
        """Test factory configuration status is properly reported."""
        factory = AgentInstanceFactory()
        factory.configure(
            websocket_bridge=mock_websocket_bridge,
            websocket_manager=mock_websocket_manager
        )
        
        metrics = factory.get_factory_metrics()
        config_status = metrics['configuration_status']
        
        assert config_status['websocket_bridge_configured'] is True
        assert config_status['websocket_manager_configured'] is True
        assert config_status['agent_registry_configured'] is False  # Not configured in this test
    
    def test_get_active_contexts_summary(self, mock_websocket_bridge):
        """Test active contexts summary reporting."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        summary = factory.get_active_contexts_summary()
        
        assert 'total_active_contexts' in summary
        assert 'contexts' in summary
        assert 'summary_timestamp' in summary
        assert summary['total_active_contexts'] == 0
        assert isinstance(summary['contexts'], dict)
        
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(summary['summary_timestamp'])
    
    def test_factory_reset_for_testing(self, mock_websocket_bridge):
        """Test factory reset functionality for testing isolation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Add some state
        factory._active_contexts['test_context'] = Mock()
        factory._user_semaphores['test_user'] = Mock()
        factory._factory_metrics['total_instances_created'] = 5
        
        # Reset factory
        factory.reset_for_testing()
        
        # Verify all state cleared
        assert len(factory._active_contexts) == 0
        assert len(factory._user_semaphores) == 0
        assert factory._factory_metrics['total_instances_created'] == 0
        assert factory._factory_metrics['active_contexts'] == 0
        assert factory._factory_metrics['total_contexts_cleaned'] == 0


# ============================================================================
# TEST: User Semaphore and Concurrency Control
# ============================================================================

class TestUserSemaphoreAndConcurrencyControl(SSotBaseTestCase):
    """Test per-user semaphore and concurrency control mechanisms."""
    
    @pytest.mark.asyncio
    async def test_get_user_semaphore_creation(self, mock_websocket_bridge):
        """Test user semaphore creation and retrieval."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Get semaphore for user (should create new one)
        semaphore1 = await factory.get_user_semaphore("user1")
        
        assert isinstance(semaphore1, asyncio.Semaphore)
        assert "user1" in factory._user_semaphores
        
        # Get same semaphore again (should reuse)
        semaphore2 = await factory.get_user_semaphore("user1")
        assert semaphore1 is semaphore2
    
    @pytest.mark.asyncio
    async def test_user_semaphore_concurrency_limits(self, mock_websocket_bridge):
        """Test user semaphore enforces concurrency limits."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Get user semaphore
        semaphore = await factory.get_user_semaphore("test_user")
        
        # Verify semaphore has correct limit
        assert semaphore._value == factory._max_concurrent_per_user
    
    @pytest.mark.asyncio
    async def test_multiple_user_semaphores_isolation(self, mock_websocket_bridge):
        """Test multiple users get isolated semaphores."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Get semaphores for different users
        semaphore1 = await factory.get_user_semaphore("user1")
        semaphore2 = await factory.get_user_semaphore("user2")
        semaphore3 = await factory.get_user_semaphore("user3")
        
        # Should all be different semaphore instances
        assert semaphore1 is not semaphore2
        assert semaphore2 is not semaphore3
        assert semaphore1 is not semaphore3
        
        # Should have separate entries in factory
        assert len(factory._user_semaphores) == 3
        assert "user1" in factory._user_semaphores
        assert "user2" in factory._user_semaphores
        assert "user3" in factory._user_semaphores
    
    @pytest.mark.asyncio
    async def test_concurrent_semaphore_access_thread_safety(self, mock_websocket_bridge):
        """Test concurrent access to user semaphores is thread-safe."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        async def get_semaphore_for_user(user_id):
            return await factory.get_user_semaphore(user_id)
        
        # Concurrently request same semaphore
        tasks = [get_semaphore_for_user("shared_user") for _ in range(10)]
        semaphores = await asyncio.gather(*tasks)
        
        # All should be same instance (thread-safe creation)
        for semaphore in semaphores[1:]:
            assert semaphore is semaphores[0]
        
        # Only one entry in factory
        assert len(factory._user_semaphores) == 1
        assert "shared_user" in factory._user_semaphores


if __name__ == "__main__":
    # Run tests with proper async support
    pytest.main([__file__, "-v", "--tb=short"])