"""Unit Tests for Golden Path Agent Registry Configuration Issues

Business Value Justification (BVJ):
- Segment: Platform/Internal (Test Infrastructure) 
- Business Goal: Restore $500K+ ARR functionality by fixing agent orchestration
- Value Impact: Enables Golden Path integration tests to validate core user flow
- Strategic Impact: Critical for CI/CD pipeline reliability and agent system validation

This test module reproduces and validates fixes for agent registry configuration
issues that are causing Golden Path integration test failures. These tests ensure
that agent creation and factory configuration work correctly.

Test Coverage:
- Agent registry configuration failures (primary Golden Path blocker)
- AgentInstanceFactory configuration patterns
- Agent class registry population and freezing
- Factory method validation and error handling
"""

import asyncio
import pytest
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Agent infrastructure imports
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    get_agent_instance_factory,
    configure_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_class_registry import (
    AgentClassRegistry,
    get_agent_class_registry
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestAgentRegistryConfiguration(SSotAsyncTestCase):
    """Unit tests reproducing agent registry configuration failures from Golden Path tests.
    
    These tests reproduce the primary error: 'No agent registry configured - cannot create agent'
    that is blocking Golden Path integration tests from running successfully.
    """

    def setup_method(self, method):
        """Setup test environment with clean factory state."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
        # Create test user context
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = str(uuid.uuid4())
        self.test_run_id = str(uuid.uuid4())
        
        # Mock LLM manager for agent dependencies
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_factory.create_llm_client_mock()

    async def test_agent_instance_factory_missing_registry_error(self):
        """FAILING TEST: Reproduce 'No agent registry configured' error from Golden Path tests.
        
        This test reproduces the exact error that's causing Golden Path integration test failures.
        The test should FAIL initially, demonstrating the issue that needs to be fixed.
        """
        # Create unconfigured factory (this simulates the problem state)
        factory = AgentInstanceFactory()
        
        user_context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id, 
            run_id=self.test_run_id
        )
        
        # This should fail with "No agent registry configured" error
        with self.assertRaises(ValueError) as cm:
            await factory.create_agent_instance("supervisor_orchestration", user_context)
        
        error_message = str(cm.exception)
        
        # Verify we get the exact error that's blocking Golden Path tests
        self.assertIn("No agent registry configured", error_message)
        logger.info(f"✅ Successfully reproduced Golden Path error: {error_message}")

    async def test_agent_instance_factory_empty_registry_error(self):
        """FAILING TEST: Reproduce empty agent registry error from Golden Path tests.
        
        This test reproduces the scenario where the registry exists but is empty,
        which also causes agent creation failures.
        """
        factory = AgentInstanceFactory()
        
        # Create empty agent class registry
        empty_registry = AgentClassRegistry()
        # Don't populate it - leave it empty
        empty_registry.freeze()
        
        # Configure factory with empty registry
        factory.configure(agent_class_registry=empty_registry)
        
        user_context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # This should fail because the registry is empty
        with self.assertRaises(ValueError) as cm:
            await factory.create_agent_instance("supervisor_orchestration", user_context)
        
        error_message = str(cm.exception)
        
        # Verify we get an agent not found error
        self.assertIn("not found", error_message.lower())
        logger.info(f"✅ Successfully reproduced empty registry error: {error_message}")

    async def test_configure_agent_instance_factory_fixes_registry(self):
        """PASSING TEST: Verify factory configuration resolves registry issues.
        
        This test demonstrates the correct way to configure the AgentInstanceFactory
        to resolve the Golden Path integration test failures.
        """
        factory = AgentInstanceFactory()
        
        # Create and populate test agent class registry
        registry = AgentClassRegistry()
        
        # Create a test agent class that matches what Golden Path tests expect
        class TestSupervisorAgent(BaseAgent):
            def __init__(self, llm_manager=None, **kwargs):
                super().__init__(llm_manager=llm_manager, name="TestSupervisorAgent")
            
            async def execute(self, *args, **kwargs):
                return {"status": "success", "agent": "test_supervisor"}
        
        # Register test agents that Golden Path tests try to create
        test_agents = [
            ("supervisor_orchestration", TestSupervisorAgent, "Test supervisor for orchestration"),
            ("triage", TestSupervisorAgent, "Test triage agent"),
            ("data_helper", TestSupervisorAgent, "Test data helper agent"),
            ("apex_optimizer", TestSupervisorAgent, "Test optimizer agent"),
            ("reporting", TestSupervisorAgent, "Test reporting agent")
        ]
        
        for agent_name, agent_class, description in test_agents:
            registry.register(agent_name, agent_class, description)
        
        registry.freeze()
        
        # Configure factory with populated registry and WebSocket bridge
        websocket_bridge = AgentWebSocketBridge()
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=websocket_bridge,
            llm_manager=self.mock_llm_manager
        )
        
        # Now agent creation should work
        user_context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        agent = await factory.create_agent_instance("supervisor_orchestration", user_context)
        
        # Verify agent creation succeeded
        self.assertIsNotNone(agent)
        self.assertIsInstance(agent, TestSupervisorAgent)
        logger.info("✅ Agent creation succeeded after proper factory configuration")

    async def test_global_configure_agent_instance_factory_integration(self):
        """INTEGRATION TEST: Test global factory configuration pattern used in Golden Path.
        
        This test validates the configure_agent_instance_factory() function that should
        be called during system startup to prevent Golden Path test failures.
        """
        # Create test agent class registry
        registry = AgentClassRegistry()
        
        # Populate with minimal test agents
        class MockAgent(BaseAgent):
            async def execute(self, *args, **kwargs):
                return {"status": "success"}
        
        registry.register("test_agent", MockAgent, "Test agent")
        registry.freeze()
        
        # Test global configuration function
        websocket_bridge = AgentWebSocketBridge()
        configured_factory = await configure_agent_instance_factory(
            agent_class_registry=registry,
            websocket_bridge=websocket_bridge,
            llm_manager=self.mock_llm_manager
        )
        
        # Verify factory is configured
        self.assertIsNotNone(configured_factory)
        
        # Verify global factory is also configured
        global_factory = get_agent_instance_factory()
        self.assertEqual(configured_factory, global_factory)
        
        # Verify agent creation works through global factory
        user_context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        agent = await global_factory.create_agent_instance("test_agent", user_context)
        self.assertIsNotNone(agent)
        logger.info("✅ Global factory configuration pattern validated")

    async def test_agent_class_registry_population_patterns(self):
        """UNIT TEST: Validate agent class registry population patterns from Golden Path.
        
        This test ensures the agent registry population logic works correctly
        and can handle the agent types that Golden Path tests require.
        """
        registry = AgentClassRegistry()
        
        # Test registry starts empty
        self.assertEqual(len(registry), 0)
        
        # Test agent registration
        class TestAgent(BaseAgent):
            pass
        
        registry.register("test_agent", TestAgent, "Test agent description")
        self.assertEqual(len(registry), 1)
        
        # Test agent retrieval
        retrieved_class = registry.get_agent_class("test_agent")
        self.assertEqual(retrieved_class, TestAgent)
        
        # Test agent listing
        agent_names = registry.list_agent_names()
        self.assertIn("test_agent", agent_names)
        
        # Test registry freezing
        registry.freeze()
        
        # Should not be able to register after freezing
        with self.assertRaises(Exception):
            registry.register("another_agent", TestAgent, "Another agent")
        
        logger.info("✅ Agent class registry population patterns validated")

    async def test_websocket_bridge_configuration_requirements(self):
        """UNIT TEST: Validate WebSocket bridge configuration requirements.
        
        This test ensures that WebSocket bridge configuration works correctly
        and handles the None case gracefully (for test environments).
        """
        factory = AgentInstanceFactory()
        
        # Test configuration with None WebSocket bridge (test mode)
        registry = AgentClassRegistry()
        
        class TestAgent(BaseAgent):
            async def execute(self, *args, **kwargs):
                return {"status": "success"}
        
        registry.register("test_agent", TestAgent, "Test agent")
        registry.freeze()
        
        # Configure without WebSocket bridge (should work for tests)
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=None,  # Test mode
            llm_manager=self.mock_llm_manager
        )
        
        user_context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Agent creation should still work (WebSocket events disabled)
        agent = await factory.create_agent_instance("test_agent", user_context)
        self.assertIsNotNone(agent)
        
        # Test configuration with real WebSocket bridge
        websocket_bridge = AgentWebSocketBridge()
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=websocket_bridge,
            llm_manager=self.mock_llm_manager
        )
        
        # Agent creation should work with WebSocket bridge
        agent = await factory.create_agent_instance("test_agent", user_context)
        self.assertIsNotNone(agent)
        
        logger.info("✅ WebSocket bridge configuration patterns validated")

    async def test_llm_manager_dependency_validation(self):
        """UNIT TEST: Validate LLM manager dependency handling.
        
        This test ensures that agents requiring LLM managers fail appropriately
        when the dependency is not available, preventing silent failures.
        """
        factory = AgentInstanceFactory()
        registry = AgentClassRegistry()
        
        # Create agent that requires LLM manager
        class LLMRequiredAgent(BaseAgent):
            def __init__(self, llm_manager=None, **kwargs):
                if not llm_manager:
                    raise ValueError("LLM manager is required")
                super().__init__(llm_manager=llm_manager, **kwargs)
        
        registry.register("llm_agent", LLMRequiredAgent, "Agent requiring LLM")
        registry.freeze()
        
        # Configure factory without LLM manager
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=None,
            llm_manager=None  # No LLM manager
        )
        
        user_context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Should fail when creating LLM-dependent agent
        with self.assertRaises(RuntimeError) as cm:
            await factory.create_agent_instance("llm_agent", user_context)
        
        error_message = str(cm.exception)
        self.assertIn("LLM manager", error_message)
        
        # Configure factory with LLM manager
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=None,
            llm_manager=self.mock_llm_manager
        )
        
        # Should succeed with LLM manager
        agent = await factory.create_agent_instance("llm_agent", user_context)
        self.assertIsNotNone(agent)
        
        logger.info("✅ LLM manager dependency validation completed")

    def teardown_method(self, method):
        """Clean up test environment."""
        # Reset factory state for test isolation
        factory = get_agent_instance_factory()
        if hasattr(factory, 'reset_for_testing'):
            factory.reset_for_testing()
        
        super().teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])