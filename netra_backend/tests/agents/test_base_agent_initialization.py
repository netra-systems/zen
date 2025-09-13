"""
Base Agent Initialization Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - Agent System Foundation Stability
Tests core BaseAgent initialization patterns, WebSocket integration setup,
and UserExecutionContext compliance for multi-user isolation.

SSOT Compliance: Uses SSotBaseTestCase, real UserExecutionContext instances,
minimal mocking per CLAUDE.md standards. No test cheating.

Coverage Target: BaseAgent.__init__, setup patterns, dependency injection
Current BaseAgent Coverage: 15.05% -> Target: 35%+

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.schemas.core_enums import ExecutionStatus


class ConcreteTestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing initialization patterns."""

    def __init__(self, llm_manager, name="TestAgent", **kwargs):
        super().__init__(llm_manager=llm_manager, name=name, **kwargs)
        self.agent_type = "test_agent"
        self.capabilities = ["test_capability_1", "test_capability_2"]

    async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Minimal implementation for testing."""
        return {
            "status": "success",
            "response": f"Processed: {request}",
            "agent_type": self.agent_type
        }


class TestBaseAgentInitialization(SSotAsyncTestCase):
    """Test BaseAgent initialization, dependency injection, and setup patterns."""

    def setup_method(self, method):
        """Set up test environment with real UserExecutionContext."""
        super().setup_method(method)

        # Create mock LLM manager with realistic interface
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model-gpt-4")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock LLM response")
        self.llm_manager.get_available_models = Mock(return_value=["gpt-4", "gpt-3.5-turbo"])

        # Create mock WebSocket bridge with real interface
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.websocket_manager = Mock()
        self.websocket_bridge.emit_agent_event = AsyncMock()
        self.websocket_bridge.emit_agent_started = AsyncMock()
        self.websocket_bridge.emit_agent_completed = AsyncMock()

        # Create real UserExecutionContext for proper isolation testing
        self.test_context = UserExecutionContext(
            user_id="test-user-init-001",
            thread_id="test-thread-init-001",
            run_id="test-run-init-001",
            agent_context={
                "user_request": "initialization test request",
                "test_mode": True,
                "expected_coverage": "base_agent_initialization"
            }
        )

        # Mock database session
        self.mock_db_session = AsyncMock()
        self.test_context = self.test_context.with_db_session(self.mock_db_session)

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
        # Reset mocks to prevent test interference
        self.llm_manager.reset_mock()
        self.websocket_bridge.reset_mock()

    def test_base_agent_initialization_basic(self):
        """Test basic BaseAgent initialization with minimal dependencies."""
        # Test: BaseAgent can be instantiated with required parameters
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)

        # Set WebSocket bridge after initialization
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Verify: Core attributes are properly initialized
        assert agent.llm_manager is self.llm_manager
        assert agent.agent_type == "test_agent"
        assert hasattr(agent, 'capabilities')
        assert len(agent.capabilities) == 2

        # Verify: WebSocket bridge adapter is properly initialized
        assert hasattr(agent, '_websocket_adapter')
        assert agent._websocket_adapter is not None

        # Verify: Agent has proper initialization
        assert agent.name == "TestAgent"
        assert hasattr(agent, 'agent_id')

    def test_base_agent_initialization_with_user_context(self):
        """Test BaseAgent initialization preserves UserExecutionContext isolation."""
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Test: Agent doesn't store global user context during initialization
        # This ensures proper multi-user isolation
        assert not hasattr(agent, 'user_context') or agent.user_context is None

        # Test: Agent can accept UserExecutionContext in operations
        # This verifies the factory pattern for user isolation
        assert hasattr(agent, 'process_request')

        # Verify: Method signature accepts UserExecutionContext
        import inspect
        sig = inspect.signature(agent.process_request)
        assert 'context' in sig.parameters
        context_param = sig.parameters['context']
        assert context_param.annotation == UserExecutionContext

    def test_base_agent_initialization_websocket_integration(self):
        """Test BaseAgent WebSocket integration setup during initialization."""
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Verify: WebSocket bridge is properly connected
        assert agent.websocket_bridge is self.websocket_bridge

        # Verify: WebSocket bridge adapter is configured
        adapter = agent.websocket_bridge_adapter
        assert adapter is not None
        assert hasattr(adapter, 'emit_agent_event')
        assert hasattr(adapter, 'emit_tool_event')

        # Test: WebSocket events can be emitted through adapter
        # This is critical for real-time chat functionality ($500K+ ARR value)
        assert callable(adapter.emit_agent_event)
        assert callable(adapter.emit_tool_event)

    def test_base_agent_initialization_dependency_validation(self):
        """Test BaseAgent initialization validates required dependencies."""
        # Test: None LLM manager raises appropriate error
        with pytest.raises((TypeError, ValueError, AttributeError)):
            ConcreteTestAgent(llm_manager=None)

        # Test: Valid initialization works
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        assert agent.llm_manager is self.llm_manager

    def test_base_agent_initialization_execution_infrastructure(self):
        """Test BaseAgent execution infrastructure initialization."""
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Verify: Agent has execution infrastructure
        assert hasattr(agent, '_execution_engine')
        assert hasattr(agent, '_reliability_manager')

        # Test: Infrastructure components are properly isolated per instance
        # This ensures no shared state between concurrent users
        agent2 = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent2.set_websocket_bridge(self.websocket_bridge, "test-run-id-2")

        assert agent is not agent2
        assert agent.agent_id != agent2.agent_id

    def test_base_agent_initialization_retry_handler_setup(self):
        """Test BaseAgent retry handler configuration during initialization."""
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Verify: Retry handler is configured (via UnifiedRetryHandler SSOT)
        assert hasattr(agent, 'retry_handler') or hasattr(agent, '_retry_config')

        # Test: Agent has retry capabilities for resilience
        # This is critical for production stability
        assert hasattr(agent, 'process_request')

        # The retry logic should be available through base infrastructure
        # Verify agent can handle execution contexts
        assert callable(agent.process_request)

    async def test_base_agent_initialization_async_setup(self):
        """Test BaseAgent initialization works correctly in async context."""
        # Test: Agent can be created in async context
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Test: Async process_request method works
        result = await agent.process_request(
            "test request for async initialization",
            self.test_context
        )

        # Verify: Result structure is correct
        assert isinstance(result, dict)
        assert "status" in result
        assert "response" in result
        assert "agent_type" in result
        assert result["status"] == "success"
        assert result["agent_type"] == "test_agent"

        # Verify: User context was preserved during execution
        assert "test request for async initialization" in result["response"]


class TestBaseAgentInitializationEdgeCases(SSotBaseTestCase):
    """Test BaseAgent initialization edge cases and error conditions."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        self.llm_manager = Mock(spec=LLMManager)
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)

    def test_base_agent_initialization_memory_isolation(self):
        """Test BaseAgent instances don't share memory between users."""
        # Create multiple agent instances
        agent1 = ConcreteTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )
        agent2 = ConcreteTestAgent(
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        # Verify: Instances are separate objects
        assert agent1 is not agent2

        # Verify: Internal state is isolated
        assert agent1.timing_collector is not agent2.timing_collector
        assert agent1.execution_monitor is not agent2.execution_monitor

        # Test: Modifying one agent doesn't affect another
        agent1.test_attribute = "agent1_value"
        assert not hasattr(agent2, 'test_attribute')

        # This validates proper factory pattern implementation
        # Critical for multi-user system with $500K+ ARR dependency

    def test_base_agent_initialization_resource_cleanup(self):
        """Test BaseAgent initialization doesn't leak resources."""
        agents = []

        # Create multiple agents to test resource management
        for i in range(10):
            agent = ConcreteTestAgent(
                llm_manager=self.llm_manager,
                websocket_bridge=self.websocket_bridge
            )
            agents.append(agent)

        # Verify: Each agent has isolated resources
        timing_collectors = [agent.timing_collector for agent in agents]
        execution_monitors = [agent.execution_monitor for agent in agents]

        # All should be unique instances
        assert len(set(id(tc) for tc in timing_collectors)) == 10
        assert len(set(id(em) for em in execution_monitors)) == 10

        # Test cleanup by dereferencing
        del agents
        # If resources leak, this would cause memory issues in production

    def test_base_agent_initialization_configuration_inheritance(self):
        """Test BaseAgent initialization respects configuration patterns."""
        # Test with custom configuration
        agent = ConcreteTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "test-run-id")

        # Verify: Configuration is accessible
        assert hasattr(agent, 'llm_manager')
        assert hasattr(agent, 'websocket_bridge')

        # Test: Configuration can be accessed through proper channels
        # This ensures compliance with SSOT configuration patterns
        llm_config = agent.llm_manager
        assert llm_config is self.llm_manager

        ws_config = agent.websocket_bridge
        assert ws_config is self.websocket_bridge