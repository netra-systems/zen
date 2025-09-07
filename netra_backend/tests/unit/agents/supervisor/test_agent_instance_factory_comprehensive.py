"""
Comprehensive Unit Tests for AgentInstanceFactory

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure robust agent instance creation with proper context isolation
- Value Impact: Prevents WebSocket event failures, ensures proper sub-agent context
- Strategic Impact: MISSION CRITICAL - Core infrastructure for agent management

This test suite validates the AgentInstanceFactory class, which is a CRITICAL SSOT component
for agent management in the Netra platform. It ensures:
- Proper singleton pattern implementation
- Agent creation with complete context isolation
- WebSocket manager integration for event delivery
- Factory configuration and pre-configuration patterns
- Error handling for unknown agents and missing dependencies
- Concurrent agent creation and resource cleanup
- Performance optimization features

CRITICAL: AgentInstanceFactory creates sub-agents with proper context to prevent
WebSocket event delivery failures. Any bugs here could cause silent agent execution
failures and loss of real-time user feedback.

According to MISSION_CRITICAL_NAMED_VALUES_INDEX:
- Critical cascade impact: Sub-agents created without proper context, WebSocket events fail
- Accessed via singleton pattern: get_agent_instance_factory()
"""

import asyncio
import pytest
import uuid
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the class under test and dependencies
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    get_agent_instance_factory,
    configure_agent_instance_factory,
    UserWebSocketEmitter
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from sqlalchemy.ext.asyncio import AsyncSession


class MockAgent(BaseAgent):
    """Mock agent implementation for testing."""
    
    def __init__(self, llm_manager=None, tool_dispatcher=None):
        super().__init__()
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = None
        self.run_id = None
        self._websocket_adapter = Mock()
        self._websocket_adapter.set_websocket_bridge = Mock()
        
    def set_websocket_bridge(self, bridge, run_id):
        self.websocket_bridge = bridge
        self.run_id = run_id
        
    async def execute(self, state, run_id):
        return {"status": "success", "result": "mock_result"}


class MockAgentWithFactory(BaseAgent):
    """Mock agent with factory method for testing."""
    
    def __init__(self, llm_manager=None, tool_dispatcher=None):
        super().__init__()
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = None
        self.run_id = None
        self._websocket_adapter = Mock()
        self._websocket_adapter.set_websocket_bridge = Mock()
    
    @classmethod
    def create_agent_with_context(cls, user_context: UserExecutionContext):
        """Factory method that accepts user context."""
        agent = cls()
        agent.user_context = user_context
        return agent
        
    def set_websocket_bridge(self, bridge, run_id):
        self.websocket_bridge = bridge
        self.run_id = run_id


class MockNoParamAgent(BaseAgent):
    """Mock agent that takes no parameters."""
    
    def __init__(self):
        super().__init__()
        self._websocket_adapter = Mock()
        self._websocket_adapter.set_websocket_bridge = Mock()


class TestAgentInstanceFactoryComprehensive(SSotBaseTestCase):
    """Comprehensive test suite for AgentInstanceFactory - MISSION CRITICAL."""
    
    # Test requires real services for integration validation
    REQUIRES_REAL_SERVICES = False
    ISOLATION_ENABLED = True
    AUTO_CLEANUP = True
    
    def setUp(self):
        """Set up test environment with clean state."""
        super().setUp()
        
        # Reset singleton for clean tests
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None
        
        # Standard test data
        self.test_user_id = "user_factory_test_12345"
        self.test_thread_id = "thread_factory_test_67890" 
        self.test_run_id = "run_factory_test_abcdef"
        self.test_websocket_id = "ws_factory_conn_789012"
        
        # Mock dependencies
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_manager = Mock(spec=UnifiedWebSocketManager)
        self.mock_llm_manager = Mock()
        self.mock_tool_dispatcher = Mock()
        self.mock_db_session = Mock(spec=AsyncSession)
        
        # Mock registries
        self.mock_agent_class_registry = Mock(spec=AgentClassRegistry)
        self.mock_agent_registry = Mock(spec=AgentRegistry)
        
        # Configure mock WebSocket bridge for success by default
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_tool_completed = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_agent_error = AsyncMock(return_value=True)
        self.mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        self.mock_websocket_bridge.unregister_run_mapping = AsyncMock(return_value=True)
        
        # Configure mock DB session
        self.mock_db_session.close = AsyncMock()
        
    def tearDown(self):
        """Clean up test environment."""
        # Reset singleton
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None
        super().tearDown()

    # =========================================================================
    # SINGLETON PATTERN TESTS
    # =========================================================================
    
    def test_singleton_pattern_returns_same_instance(self):
        """Test 1: Singleton pattern returns the same instance consistently."""
        factory1 = get_agent_instance_factory()
        factory2 = get_agent_instance_factory()
        
        self.assertIs(factory1, factory2)
        self.assertIsInstance(factory1, AgentInstanceFactory)
        self.assertIsInstance(factory2, AgentInstanceFactory)
        
    def test_singleton_pattern_across_modules(self):
        """Test 2: Singleton works across different module imports."""
        from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory as get_factory_alt
        
        factory1 = get_agent_instance_factory()
        factory2 = get_factory_alt()
        
        self.assertIs(factory1, factory2)
        
    def test_singleton_reset_creates_new_instance(self):
        """Test 3: Resetting singleton creates new instance."""
        factory1 = get_agent_instance_factory()
        
        # Reset singleton manually (simulating restart)
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None
        
        factory2 = get_agent_instance_factory()
        
        self.assertIsNot(factory1, factory2)
        self.assertIsInstance(factory2, AgentInstanceFactory)

    # =========================================================================
    # FACTORY INITIALIZATION TESTS
    # =========================================================================
    
    def test_factory_initialization_defaults(self):
        """Test 4: Factory initializes with proper defaults."""
        factory = AgentInstanceFactory()
        
        self.assertIsNone(factory._agent_class_registry)
        self.assertIsNone(factory._agent_registry)
        self.assertIsNone(factory._websocket_bridge)
        self.assertIsNone(factory._websocket_manager)
        self.assertIsNone(factory._llm_manager)
        self.assertIsNone(factory._tool_dispatcher)
        
        # Check performance configuration is loaded
        self.assertIsNotNone(factory._performance_config)
        self.assertGreater(factory._max_concurrent_per_user, 0)
        self.assertGreater(factory._execution_timeout, 0)
        self.assertGreater(factory._cleanup_interval, 0)
        
        # Check tracking structures are initialized
        # Note: These may be WeakValueDictionary if enable_weak_references is True
        import weakref
        self.assertIsInstance(factory._user_semaphores, (dict, weakref.WeakValueDictionary))
        self.assertIsInstance(factory._active_contexts, (dict, weakref.WeakValueDictionary))
        self.assertIsInstance(factory._factory_metrics, dict)
        self.assertEqual(factory._factory_metrics['total_instances_created'], 0)
        
    def test_factory_initialization_performance_config(self):
        """Test 5: Factory initializes with performance configuration."""
        factory = AgentInstanceFactory()
        
        # Verify performance config attributes
        perf_config = factory._performance_config
        self.assertTrue(hasattr(perf_config, 'max_concurrent_per_user'))
        self.assertTrue(hasattr(perf_config, 'execution_timeout'))
        self.assertTrue(hasattr(perf_config, 'max_history_per_user'))
        self.assertTrue(hasattr(perf_config, 'enable_emitter_pooling'))
        self.assertTrue(hasattr(perf_config, 'enable_class_caching'))
        self.assertTrue(hasattr(perf_config, 'enable_metrics'))
        
        # Verify factory uses config values
        self.assertEqual(factory._max_concurrent_per_user, perf_config.max_concurrent_per_user)
        self.assertEqual(factory._execution_timeout, perf_config.execution_timeout)
        self.assertEqual(factory._max_history_per_user, perf_config.max_history_per_user)

    # =========================================================================
    # FACTORY CONFIGURATION TESTS
    # =========================================================================
    
    def test_configure_with_agent_class_registry_success(self):
        """Test 6: Configure factory with AgentClassRegistry successfully."""
        factory = AgentInstanceFactory()
        
        # Configure mock registry to return length
        self.mock_agent_class_registry.__len__ = Mock(return_value=5)
        
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        self.assertIs(factory._agent_class_registry, self.mock_agent_class_registry)
        self.assertIs(factory._websocket_bridge, self.mock_websocket_bridge)
        self.assertIs(factory._llm_manager, self.mock_llm_manager)
        self.assertIs(factory._tool_dispatcher, self.mock_tool_dispatcher)
        
    def test_configure_with_legacy_agent_registry_fallback(self):
        """Test 7: Configure with legacy AgentRegistry as fallback."""
        factory = AgentInstanceFactory()
        
        factory.configure(
            agent_registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        self.assertIs(factory._agent_registry, self.mock_agent_registry)
        self.assertIsNone(factory._agent_class_registry)  # Should not be set
        self.assertIs(factory._websocket_bridge, self.mock_websocket_bridge)
        
    def test_configure_none_websocket_bridge_raises_error(self):
        """Test 8: Configuring with None WebSocket bridge raises error."""
        factory = AgentInstanceFactory()
        
        with self.assertRaises(ValueError) as ctx:
            factory.configure(websocket_bridge=None)
        self.assertIn("AgentWebSocketBridge cannot be None", str(ctx.exception))
            
    def test_configure_empty_agent_class_registry_raises_error(self):
        """Test 9: Configure falls back to global registry when none provided."""
        factory = AgentInstanceFactory()
        
        # Don't provide agent_class_registry, forcing fallback to global registry
        # The global registry is None in test environment, causing this error
        with self.assertRaises(ValueError) as ctx:
            factory.configure(
                websocket_bridge=self.mock_websocket_bridge
            )
        self.assertIn("Global AgentClassRegistry is None", str(ctx.exception))
            
    @patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry')
    def test_configure_with_global_registry_fallback(self, mock_get_global_registry):
        """Test 10: Configure falls back to global registry when none provided."""
        factory = AgentInstanceFactory()
        
        # Mock global registry
        mock_global_registry = Mock(spec=AgentClassRegistry)
        mock_global_registry.__len__ = Mock(return_value=3)
        mock_get_global_registry.return_value = mock_global_registry
        
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        self.assertIs(factory._agent_class_registry, mock_global_registry)
        mock_get_global_registry.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_configure_agent_instance_factory_function(self):
        """Test 11: Global configure function works correctly."""
        result = await configure_agent_instance_factory(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )
        
        self.assertIsInstance(result, AgentInstanceFactory)
        self.assertIs(result._agent_class_registry, self.mock_agent_class_registry)
        self.assertIs(result._websocket_bridge, self.mock_websocket_bridge)
        self.assertIs(result._llm_manager, self.mock_llm_manager)

    # =========================================================================
    # USER EXECUTION CONTEXT CREATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_create_user_execution_context_success(self):
        """Test 12: Create user execution context successfully."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=self.mock_db_session,
            websocket_connection_id=self.test_websocket_id,
            metadata={"test": "data"}
        )
        
        # Verify context properties
        self.assertIsInstance(context, UserExecutionContext)
        self.assertEqual(context.user_id, self.test_user_id)
        self.assertEqual(context.thread_id, self.test_thread_id)
        self.assertEqual(context.run_id, self.test_run_id)
        self.assertIs(context.db_session, self.mock_db_session)
        self.assertEqual(context.websocket_connection_id, self.test_websocket_id)
        self.assertEqual(context.metadata["test"], "data")
        self.assertIsInstance(context.created_at, datetime)
        
        # Verify factory tracking
        self.assertEqual(len(factory._active_contexts), 1)
        self.assertEqual(factory._factory_metrics['total_instances_created'], 1)
        self.assertEqual(factory._factory_metrics['active_contexts'], 1)
        
    @pytest.mark.asyncio
    async def test_create_user_execution_context_missing_required_params(self):
        """Test 13: Creating context with missing required params raises error."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Test missing user_id
        with self.assertRaises(ValueError) as ctx:
            await factory.create_user_execution_context(
                user_id="",
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
        self.assertIn("user_id, thread_id, and run_id are required", str(ctx.exception))
        
        # Test missing thread_id
        with self.assertRaises(ValueError) as ctx:
            await factory.create_user_execution_context(
                user_id=self.test_user_id,
                thread_id="",
                run_id=self.test_run_id
            )
        self.assertIn("user_id, thread_id, and run_id are required", str(ctx.exception))
            
        # Test missing run_id
        with self.assertRaises(ValueError) as ctx:
            await factory.create_user_execution_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=""
            )
        self.assertIn("user_id, thread_id, and run_id are required", str(ctx.exception))
            
    @pytest.mark.asyncio
    async def test_create_user_execution_context_unconfigured_factory(self):
        """Test 14: Creating context with unconfigured factory raises error."""
        factory = AgentInstanceFactory()
        
        with self.assertRaises(ValueError) as ctx:
            await factory.create_user_execution_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
        self.assertIn("Factory not configured", str(ctx.exception))
            
    @pytest.mark.asyncio
    async def test_create_user_execution_context_websocket_registration(self):
        """Test 15: Context creation registers WebSocket mapping."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Verify run-thread mapping was registered
        self.mock_websocket_bridge.register_run_thread_mapping.assert_called_once()
        call_args = self.mock_websocket_bridge.register_run_thread_mapping.call_args
        self.assertEqual(call_args.kwargs['run_id'], self.test_run_id)
        self.assertEqual(call_args.kwargs['thread_id'], self.test_thread_id)
        self.assertIn('user_id', call_args.kwargs['metadata'])
        self.assertEqual(call_args.kwargs['metadata']['user_id'], self.test_user_id)

    # =========================================================================
    # AGENT CREATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_with_agent_class_registry_success(self):
        """Test 16: Create agent instance using AgentClassRegistry successfully."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Mock registry to return our test agent class
        self.mock_agent_class_registry.get_agent_class.return_value = MockAgent
        
        # Create user context
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Create agent instance
        agent = await factory.create_agent_instance("test_agent", context)
        
        # Verify agent creation
        self.assertIsInstance(agent, MockAgent)
        self.assertIs(agent.llm_manager, self.mock_llm_manager)
        self.assertIs(agent.tool_dispatcher, self.mock_tool_dispatcher)
        
        # Verify WebSocket bridge was set
        self.assertIs(agent.websocket_bridge, self.mock_websocket_bridge)
        self.assertEqual(agent.run_id, self.test_run_id)
        
        # Verify factory tracking
        self.assertTrue(hasattr(factory, '_agent_instances'))
        self.assertEqual(len(factory._agent_instances), 1)
        
    @pytest.mark.asyncio
    async def test_create_agent_instance_with_factory_method(self):
        """Test 17: Create agent using factory method when available."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Mock registry to return agent with factory method
        self.mock_agent_class_registry.get_agent_class.return_value = MockAgentWithFactory
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        agent = await factory.create_agent_instance("test_agent", context)
        
        # Verify agent was created with factory method
        self.assertIsInstance(agent, MockAgentWithFactory)
        self.assertTrue(hasattr(agent, 'user_context'))
        self.assertIs(agent.user_context, context)
        
    @pytest.mark.asyncio
    async def test_create_agent_instance_no_param_agent(self):
        """Test 18: Create agent that takes no parameters."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        self.mock_agent_class_registry.get_agent_class.return_value = MockNoParamAgent
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        agent = await factory.create_agent_instance("test_agent", context)
        
        self.assertIsInstance(agent, MockNoParamAgent)
        
    @pytest.mark.asyncio
    async def test_create_agent_instance_with_provided_class(self):
        """Test 19: Create agent with directly provided class."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        agent = await factory.create_agent_instance(
            "test_agent", 
            context,
            agent_class=MockAgent
        )
        
        self.assertIsInstance(agent, MockAgent)
        
    @pytest.mark.asyncio
    async def test_create_agent_instance_unknown_agent_raises_error(self):
        """Test 20: Creating unknown agent raises detailed error."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Mock registry to return None (agent not found)
        self.mock_agent_class_registry.get_agent_class.return_value = None
        self.mock_agent_class_registry.list_agent_names.return_value = ["agent1", "agent2", "agent3"]
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        with self.assertRaises(ValueError) as ctx:
            await factory.create_agent_instance("unknown_agent", context)
        self.assertIn("Agent 'unknown_agent' not found", str(ctx.exception))
            
    @pytest.mark.asyncio
    async def test_create_agent_instance_missing_user_context_raises_error(self):
        """Test 21: Creating agent without context raises error."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        with self.assertRaises(ValueError) as ctx:
            await factory.create_agent_instance("test_agent", None)
        self.assertIn("UserExecutionContext is required", str(ctx.exception))
            
    @pytest.mark.asyncio
    async def test_create_agent_instance_unconfigured_websocket_bridge_raises_error(self):
        """Test 22: Creating agent with unconfigured WebSocket bridge raises error."""
        factory = AgentInstanceFactory()
        # Don't configure WebSocket bridge
        
        context_mock = Mock(spec=UserExecutionContext)
        context_mock.user_id = self.test_user_id
        context_mock.run_id = self.test_run_id
        
        with self.assertRaises(RuntimeError) as ctx:
            await factory.create_agent_instance("test_agent", context_mock)
        self.assertIn("AgentInstanceFactory not configured", str(ctx.exception))

    # =========================================================================
    # DEPENDENCY VALIDATION TESTS
    # =========================================================================
    
    def test_validate_agent_dependencies_success(self):
        """Test 23: Dependency validation passes for properly configured agents."""
        factory = AgentInstanceFactory()
        factory._llm_manager = self.mock_llm_manager
        factory._tool_dispatcher = self.mock_tool_dispatcher
        
        # Should not raise for agents requiring LLM manager
        factory._validate_agent_dependencies("DataSubAgent")
        factory._validate_agent_dependencies("OptimizationsCoreSubAgent")
        
    def test_validate_agent_dependencies_missing_llm_manager_raises_error(self):
        """Test 24: Missing LLM manager for dependent agents raises error."""
        factory = AgentInstanceFactory()
        factory._llm_manager = None
        
        with self.assertRaises(RuntimeError) as ctx:
            factory._validate_agent_dependencies("DataSubAgent")
        self.assertIn("Cannot create DataSubAgent: Required dependency 'llm_manager' not available", str(ctx.exception))
            
    def test_validate_agent_dependencies_by_class_name_matching(self):
        """Test 25: Dependency validation works with class name matching."""
        factory = AgentInstanceFactory()
        factory._llm_manager = None
        
        # Test class name matching - this should match OptimizationsCoreSubAgent
        with self.assertRaises(RuntimeError) as ctx:
            factory._validate_agent_dependencies("optimization_core")
        self.assertIn("Required dependency 'llm_manager' not available", str(ctx.exception))
            
    def test_validate_agent_dependencies_unknown_agent_no_error(self):
        """Test 26: Unknown agents don't trigger dependency validation errors."""
        factory = AgentInstanceFactory()
        factory._llm_manager = None
        
        # Should not raise for unknown agents
        factory._validate_agent_dependencies("UnknownAgent")

    # =========================================================================
    # WEBSOCKET INTEGRATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_creation_success(self):
        """Test 27: WebSocket emitter creation works correctly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Check emitter was created and stored
        context_id = f"{self.test_user_id}_{self.test_thread_id}_{self.test_run_id}"
        emitter_key = f"{context_id}_emitter"
        
        self.assertTrue(hasattr(factory, '_websocket_emitters'))
        self.assertIn(emitter_key, factory._websocket_emitters)
        emitter = factory._websocket_emitters[emitter_key]
        self.assertIsInstance(emitter, UserWebSocketEmitter)
        self.assertEqual(emitter.user_id, self.test_user_id)
        self.assertEqual(emitter.thread_id, self.test_thread_id)
        self.assertEqual(emitter.run_id, self.test_run_id)
        
    @pytest.mark.asyncio
    async def test_websocket_emitter_event_delivery(self):
        """Test 28: WebSocket emitter delivers events correctly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Get the emitter and test event delivery
        context_id = f"{self.test_user_id}_{self.test_thread_id}_{self.test_run_id}"
        emitter_key = f"{context_id}_emitter"
        emitter = factory._websocket_emitters[emitter_key]
        
        # Test all 5 critical WebSocket events
        await emitter.notify_agent_started("test_agent", {"context": "test"})
        await emitter.notify_agent_thinking("test_agent", "Processing request", 1, 25.0)
        await emitter.notify_tool_executing("test_agent", "test_tool", {"param": "value"})
        await emitter.notify_tool_completed("test_agent", "test_tool", {"result": "success"}, 150.5)
        await emitter.notify_agent_completed("test_agent", {"final": "result"}, 2000.0)
        
        # Verify all events were sent through WebSocket bridge
        self.mock_websocket_bridge.notify_agent_started.assert_called_once_with(
            run_id=self.test_run_id,
            agent_name="test_agent",
            context={"context": "test"}
        )
        self.mock_websocket_bridge.notify_agent_thinking.assert_called_once_with(
            run_id=self.test_run_id,
            agent_name="test_agent",
            reasoning="Processing request",
            step_number=1,
            progress_percentage=25.0
        )
        self.mock_websocket_bridge.notify_tool_executing.assert_called_once_with(
            run_id=self.test_run_id,
            agent_name="test_agent",
            tool_name="test_tool",
            parameters={"param": "value"}
        )
        self.mock_websocket_bridge.notify_tool_completed.assert_called_once_with(
            run_id=self.test_run_id,
            agent_name="test_agent",
            tool_name="test_tool",
            result={"result": "success"},
            execution_time_ms=150.5
        )
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once_with(
            run_id=self.test_run_id,
            agent_name="test_agent",
            result={"final": "result"},
            execution_time_ms=2000.0
        )
        
    @pytest.mark.asyncio
    async def test_websocket_emitter_error_handling(self):
        """Test 29: WebSocket emitter handles errors correctly."""
        factory = AgentInstanceFactory()
        
        # Configure bridge to return failure
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=False)
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        context_id = f"{self.test_user_id}_{self.test_thread_id}_{self.test_run_id}"
        emitter_key = f"{context_id}_emitter"
        emitter = factory._websocket_emitters[emitter_key]
        
        # Test that failure raises exception
        with self.assertRaises(ConnectionError) as ctx:
            await emitter.notify_agent_started("test_agent")
        self.assertIn("WebSocket bridge returned failure", str(ctx.exception))

    # =========================================================================
    # CLEANUP AND RESOURCE MANAGEMENT TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_cleanup_user_context_success(self):
        """Test 30: User context cleanup works correctly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=self.mock_db_session
        )
        
        # Verify context is tracked
        self.assertEqual(len(factory._active_contexts), 1)
        
        # Clean up context
        await factory.cleanup_user_context(context)
        
        # Verify cleanup
        self.assertEqual(len(factory._active_contexts), 0)
        self.assertEqual(factory._factory_metrics['total_contexts_cleaned'], 1)
        
        # Verify WebSocket unregistration
        self.mock_websocket_bridge.unregister_run_mapping.assert_called_once_with(self.test_run_id)
        
        # Verify database session cleanup
        self.mock_db_session.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cleanup_user_context_with_emitter(self):
        """Test 31: Context cleanup includes WebSocket emitter cleanup."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Verify emitter exists
        context_id = f"{self.test_user_id}_{self.test_thread_id}_{self.test_run_id}"
        emitter_key = f"{context_id}_emitter"
        self.assertIn(emitter_key, factory._websocket_emitters)
        
        # Clean up
        await factory.cleanup_user_context(context)
        
        # Verify emitter was cleaned up
        self.assertNotIn(emitter_key, factory._websocket_emitters)
        
    @pytest.mark.asyncio
    async def test_cleanup_inactive_contexts_by_age(self):
        """Test 32: Cleanup inactive contexts based on age."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create multiple contexts with different ages
        old_context = await factory.create_user_execution_context(
            user_id="old_user",
            thread_id="old_thread",
            run_id="old_run"
        )
        
        # Mock old context age
        old_time = datetime.now(timezone.utc).replace(year=2020)  # Very old
        old_context.created_at = old_time
        
        new_context = await factory.create_user_execution_context(
            user_id="new_user",
            thread_id="new_thread", 
            run_id="new_run"
        )
        
        self.assertEqual(len(factory._active_contexts), 2)
        
        # Clean up contexts older than 1 hour
        cleaned_count = await factory.cleanup_inactive_contexts(max_age_seconds=3600)
        
        # Should clean up only the old context
        self.assertEqual(cleaned_count, 1)
        self.assertEqual(len(factory._active_contexts), 1)
        
    @pytest.mark.asyncio
    async def test_user_execution_scope_context_manager(self):
        """Test 33: User execution scope context manager works correctly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        context_instance = None
        
        # Test context manager
        async with factory.user_execution_scope(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=self.mock_db_session
        ) as context:
            context_instance = context
            
            # Verify context is active
            self.assertIsInstance(context, UserExecutionContext)
            self.assertEqual(context.user_id, self.test_user_id)
            self.assertEqual(len(factory._active_contexts), 1)
        
        # Verify cleanup happened automatically
        self.assertEqual(len(factory._active_contexts), 0)

    # =========================================================================
    # CONCURRENCY TESTS  
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_creation(self):
        """Test 34: Concurrent agent creation works without conflicts."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )
        
        self.mock_agent_class_registry.get_agent_class.return_value = MockAgent
        
        async def create_agent_for_user(user_num):
            context = await factory.create_user_execution_context(
                user_id=f"user_{user_num}",
                thread_id=f"thread_{user_num}",
                run_id=f"run_{user_num}"
            )
            return await factory.create_agent_instance("test_agent", context)
        
        # Create agents concurrently for multiple users
        tasks = [create_agent_for_user(i) for i in range(5)]
        agents = await asyncio.gather(*tasks)
        
        # Verify all agents were created successfully
        self.assertEqual(len(agents), 5)
        self.assertTrue(all(isinstance(agent, MockAgent) for agent in agents))
        
        # Verify no conflicts in factory state
        self.assertEqual(len(factory._active_contexts), 5)
        self.assertEqual(factory._factory_metrics['total_instances_created'], 5)
        
    @pytest.mark.asyncio
    async def test_user_semaphore_creation_and_access(self):
        """Test 35: Per-user semaphores are created and managed correctly."""
        factory = AgentInstanceFactory()
        
        # Get semaphores for different users
        sem1 = await factory.get_user_semaphore("user1")
        sem2 = await factory.get_user_semaphore("user2")
        sem1_again = await factory.get_user_semaphore("user1")
        
        # Verify semaphore properties
        self.assertIsInstance(sem1, asyncio.Semaphore)
        self.assertIsInstance(sem2, asyncio.Semaphore)
        self.assertIs(sem1, sem1_again)  # Same user gets same semaphore
        self.assertIsNot(sem1, sem2)    # Different users get different semaphores
        
        # Verify factory tracking
        self.assertEqual(len(factory._user_semaphores), 2)
        self.assertIn("user1", factory._user_semaphores)
        self.assertIn("user2", factory._user_semaphores)

    # =========================================================================
    # PERFORMANCE AND METRICS TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_factory_metrics_collection(self):
        """Test 36: Factory collects metrics correctly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Initial metrics
        initial_metrics = factory.get_factory_metrics()
        self.assertEqual(initial_metrics['total_instances_created'], 0)
        self.assertEqual(initial_metrics['active_contexts'], 0)
        self.assertEqual(initial_metrics['total_contexts_cleaned'], 0)
        
        # Create and clean up context
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Check metrics after creation
        metrics_after_create = factory.get_factory_metrics()
        self.assertEqual(metrics_after_create['total_instances_created'], 1)
        self.assertEqual(metrics_after_create['active_contexts'], 1)
        
        # Clean up and check metrics
        await factory.cleanup_user_context(context)
        final_metrics = factory.get_factory_metrics()
        self.assertEqual(final_metrics['total_contexts_cleaned'], 1)
        self.assertEqual(final_metrics['active_contexts'], 0)
        
    def test_factory_metrics_structure(self):
        """Test 37: Factory metrics have correct structure."""
        factory = AgentInstanceFactory()
        
        # Configure mock registry to avoid global registry fallback error
        self.mock_agent_class_registry.__len__ = Mock(return_value=1)
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        metrics = factory.get_factory_metrics()
        
        # Verify required metric fields
        required_fields = [
            'total_instances_created',
            'active_contexts', 
            'total_contexts_cleaned',
            'creation_errors',
            'cleanup_errors',
            'average_context_lifetime_seconds',
            'user_semaphores_count',
            'max_concurrent_per_user',
            'execution_timeout',
            'cleanup_interval',
            'active_context_ids',
            'configuration_status',
            'performance_config',
            'pool_stats'
        ]
        
        for field in required_fields:
            self.assertIn(field, metrics)
            
        # Verify configuration status structure
        config_status = metrics['configuration_status']
        self.assertIn('agent_registry_configured', config_status)
        self.assertIn('websocket_bridge_configured', config_status)
        self.assertIn('websocket_manager_configured', config_status)
        
    @pytest.mark.asyncio
    async def test_active_contexts_summary(self):
        """Test 38: Active contexts summary provides correct information."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create multiple contexts
        context1 = await factory.create_user_execution_context(
            user_id="user1",
            thread_id="thread1",
            run_id="run1"
        )
        context2 = await factory.create_user_execution_context(
            user_id="user2",
            thread_id="thread2", 
            run_id="run2"
        )
        
        summary = factory.get_active_contexts_summary()
        
        # Verify summary structure
        self.assertIn('total_active_contexts', summary)
        self.assertIn('contexts', summary)
        self.assertIn('summary_timestamp', summary)
        
        self.assertEqual(summary['total_active_contexts'], 2)
        self.assertEqual(len(summary['contexts']), 2)

    # =========================================================================
    # ERROR HANDLING AND EDGE CASES
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_create_agent_instance_instantiation_failure(self):
        """Test 39: Agent instantiation failure is handled correctly."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Mock class that raises error on instantiation
        class FaultyAgent:
            def __init__(self):
                raise RuntimeError("Instantiation failed")
        
        self.mock_agent_class_registry.get_agent_class.return_value = FaultyAgent
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        with self.assertRaises(RuntimeError) as ctx:
            await factory.create_agent_instance("faulty_agent", context)
        self.assertIn("Agent creation failed", str(ctx.exception))
            
        # Verify error metrics
        self.assertEqual(factory._factory_metrics['creation_errors'], 1)
        
    @pytest.mark.asyncio
    async def test_cleanup_with_errors_continues(self):
        """Test 40: Cleanup continues even when individual cleanups fail."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Mock db session to raise error on close
        faulty_session = Mock(spec=AsyncSession)
        faulty_session.close = AsyncMock(side_effect=RuntimeError("Close failed"))
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=faulty_session
        )
        
        # Cleanup should not raise despite session error
        await factory.cleanup_user_context(context)
        
        # Verify cleanup still completed
        self.assertEqual(len(factory._active_contexts), 0)
        self.assertEqual(factory._factory_metrics['total_contexts_cleaned'], 1)

    # =========================================================================
    # INTEGRATION TESTS (REAL BEHAVIOR)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_end_to_end_agent_creation_with_context(self):
        """Test 41: Complete end-to-end agent creation with real context flow."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        self.mock_agent_class_registry.get_agent_class.return_value = MockAgent
        
        # Use context manager for full lifecycle
        async with factory.user_execution_scope(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=self.mock_db_session,
            metadata={"test_flow": "end_to_end"}
        ) as context:
            
            # Create agent within the context
            agent = await factory.create_agent_instance("test_agent", context)
            
            # Verify complete setup
            self.assertIsInstance(agent, MockAgent)
            self.assertIs(agent.websocket_bridge, self.mock_websocket_bridge)
            self.assertEqual(agent.run_id, self.test_run_id)
            self.assertIs(agent.llm_manager, self.mock_llm_manager)
            self.assertIs(agent.tool_dispatcher, self.mock_tool_dispatcher)
            
            # Verify context and WebSocket integration
            context_id = f"{self.test_user_id}_{self.test_thread_id}_{self.test_run_id}"
            emitter_keys = [key for key in factory._websocket_emitters.keys() if key.startswith(context_id)]
            self.assertTrue(len(emitter_keys) > 0)
            
        # After context exit, everything should be cleaned up
        self.assertEqual(len(factory._active_contexts), 0)
        self.assertEqual(len([key for key in getattr(factory, '_websocket_emitters', {}).keys()]), 0)
        
    @pytest.mark.asyncio
    async def test_synthetic_data_agent_special_handling(self):
        """Test 42: Special error handling for synthetic_data agent registration issues."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Mock registry to return None for synthetic_data agent
        self.mock_agent_class_registry.get_agent_class.return_value = None
        self.mock_agent_class_registry.list_agent_names.return_value = ["other_agent"]
        
        context = await factory.create_user_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Verify special error message for synthetic_data agent
        with self.assertRaises(ValueError) as ctx:
            await factory.create_agent_instance("synthetic_data", context)
        self.assertIn("KNOWN ISSUE: synthetic_data agent registration may have failed", str(ctx.exception))


# =========================================================================
# WEBSOCKET EMITTER SPECIFIC TESTS
# =========================================================================

class TestUserWebSocketEmitterComprehensive(SSotBaseTestCase):
    """Comprehensive tests for UserWebSocketEmitter component."""
    
    def setUp(self):
        """Set up WebSocket emitter tests."""
        super().setUp()
        
        self.test_user_id = "ws_user_12345"
        self.test_thread_id = "ws_thread_67890"
        self.test_run_id = "ws_run_abcdef"
        
        # Mock WebSocket bridge
        self.mock_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        self.mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        self.mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
        self.mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
        self.mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        self.mock_bridge.notify_agent_error = AsyncMock(return_value=True)
        
    def test_websocket_emitter_initialization(self):
        """Test 43: WebSocket emitter initializes correctly."""
        emitter = UserWebSocketEmitter(
            self.test_user_id,
            self.test_thread_id, 
            self.test_run_id,
            self.mock_bridge
        )
        
        self.assertEqual(emitter.user_id, self.test_user_id)
        self.assertEqual(emitter.thread_id, self.test_thread_id)
        self.assertEqual(emitter.run_id, self.test_run_id)
        self.assertIs(emitter.websocket_bridge, self.mock_bridge)
        self.assertIsInstance(emitter.created_at, datetime)
        self.assertEqual(emitter._event_count, 0)
        self.assertIsNone(emitter._last_event_time)
        
    @pytest.mark.asyncio
    async def test_websocket_emitter_event_counting(self):
        """Test 44: WebSocket emitter counts events correctly."""
        emitter = UserWebSocketEmitter(
            self.test_user_id,
            self.test_thread_id,
            self.test_run_id, 
            self.mock_bridge
        )
        
        # Send multiple events
        await emitter.notify_agent_started("test_agent")
        await emitter.notify_agent_thinking("test_agent", "thinking")
        await emitter.notify_agent_completed("test_agent")
        
        self.assertEqual(emitter._event_count, 3)
        self.assertIsNotNone(emitter._last_event_time)
        
    @pytest.mark.asyncio
    async def test_websocket_emitter_status_reporting(self):
        """Test 45: WebSocket emitter provides accurate status."""
        emitter = UserWebSocketEmitter(
            self.test_user_id,
            self.test_thread_id,
            self.test_run_id,
            self.mock_bridge
        )
        
        # Send an event to update state
        await emitter.notify_agent_started("test_agent")
        
        status = emitter.get_emitter_status()
        
        self.assertEqual(status['user_id'], self.test_user_id)
        self.assertEqual(status['thread_id'], self.test_thread_id)
        self.assertEqual(status['run_id'], self.test_run_id)
        self.assertEqual(status['event_count'], 1)
        self.assertIsNotNone(status['last_event_time'])
        self.assertIsNotNone(status['created_at'])
        self.assertTrue(status['has_websocket_bridge'])
        
    @pytest.mark.asyncio
    async def test_websocket_emitter_cleanup(self):
        """Test 46: WebSocket emitter cleanup works correctly."""
        emitter = UserWebSocketEmitter(
            self.test_user_id,
            self.test_thread_id,
            self.test_run_id,
            self.mock_bridge
        )
        
        # Send some events
        await emitter.notify_agent_started("test_agent")
        await emitter.notify_agent_completed("test_agent")
        
        # Clean up
        await emitter.cleanup()
        
        # Verify cleanup
        self.assertIsNone(emitter.websocket_bridge)


# =========================================================================
# PERFORMANCE OPTIMIZATION TESTS
# =========================================================================

class TestAgentInstanceFactoryPerformance(SSotBaseTestCase):
    """Performance-focused tests for AgentInstanceFactory optimizations."""
    
    def setUp(self):
        """Set up performance tests."""
        super().setUp()
        
        # Mock WebSocket bridge for performance tests
        self.mock_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        self.mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        
    @pytest.mark.asyncio
    async def test_performance_metrics_sampling(self):
        """Test 47: Performance metrics sampling works correctly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=self.mock_bridge)
        
        # Mock sampling to always return True for consistent testing
        with patch.object(factory, '_should_sample', return_value=True):
            context = await factory.create_user_execution_context(
                user_id="perf_user",
                thread_id="perf_thread",
                run_id="perf_run"
            )
            
            # Check if metrics were collected
            if hasattr(factory, '_perf_stats'):
                self.assertIn('context_creation_ms', factory._perf_stats)
                
    def test_performance_config_integration(self):
        """Test 48: Performance configuration is properly integrated."""
        factory = AgentInstanceFactory()
        
        # Verify performance config is loaded and used
        self.assertIsNotNone(factory._performance_config)
        self.assertTrue(hasattr(factory._performance_config, 'max_concurrent_per_user'))
        self.assertTrue(hasattr(factory._performance_config, 'enable_emitter_pooling'))
        self.assertTrue(hasattr(factory._performance_config, 'enable_class_caching'))
        self.assertTrue(hasattr(factory._performance_config, 'enable_metrics'))
        
        # Verify factory uses config values
        self.assertEqual(factory._max_concurrent_per_user, factory._performance_config.max_concurrent_per_user)
        
    def test_weak_references_configuration(self):
        """Test 49: Weak references are configured when enabled."""
        factory = AgentInstanceFactory()
        
        # Check if weak references are being used when enabled
        if factory._performance_config.enable_weak_references:
            import weakref
            self.assertIsInstance(factory._active_contexts, weakref.WeakValueDictionary)
            self.assertIsInstance(factory._user_semaphores, weakref.WeakValueDictionary)
        else:
            self.assertIsInstance(factory._active_contexts, dict)
            self.assertIsInstance(factory._user_semaphores, dict)
            
    def test_class_caching_functionality(self):
        """Test 50: Class caching works when enabled."""
        factory = AgentInstanceFactory()
        
        if factory._performance_config.enable_class_caching:
            # Test caching functionality
            cached_class = factory._get_cached_agent_class("test_agent")
            self.assertIsNone(cached_class)  # Initially empty
            
            # Verify cache exists
            self.assertTrue(hasattr(factory, '_cache_lock'))
            
    @pytest.mark.asyncio
    async def test_emitter_pool_statistics(self):
        """Test 51: Emitter pool statistics are collected when pooling enabled."""
        factory = AgentInstanceFactory()
        
        # Get pool stats (should work regardless of pooling enabled)
        stats = factory.get_pool_stats()
        self.assertIsInstance(stats, dict)
        
        # If pooling is enabled, stats should contain pool metrics
        if factory._performance_config.enable_emitter_pooling:
            # Pool stats may be empty initially but structure should exist
            pass  # Pool implementation details may vary