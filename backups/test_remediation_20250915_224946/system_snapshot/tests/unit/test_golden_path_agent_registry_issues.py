_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
'Unit Tests for Golden Path Agent Registry Configuration Issues\n\nBusiness Value Justification (BVJ):\n- Segment: Platform/Internal (Test Infrastructure) \n- Business Goal: Restore $500K+ ARR functionality by fixing agent orchestration\n- Value Impact: Enables Golden Path integration tests to validate core user flow\n- Strategic Impact: Critical for CI/CD pipeline reliability and agent system validation\n\nThis test module reproduces and validates fixes for agent registry configuration\nissues that are causing Golden Path integration test failures. These tests ensure\nthat agent creation and factory configuration work correctly.\n\nTest Coverage:\n- Agent registry configuration failures (primary Golden Path blocker)\n- AgentInstanceFactory configuration patterns\n- Agent class registry population and freezing\n- Factory method validation and error handling\n'
import asyncio
import pytest
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, get_agent_instance_factory, configure_agent_instance_factory, create_agent_instance_factory
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry, get_agent_class_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.logging_config import central_logger
from shared.id_generation import UnifiedIdGenerator
logger = central_logger.get_logger(__name__)

@pytest.mark.unit
class AgentRegistryConfigurationTests(SSotAsyncTestCase):
    """Unit tests reproducing agent registry configuration failures from Golden Path tests.
    
    These tests reproduce the primary error: 'No agent registry configured - cannot create agent'
    that is blocking Golden Path integration tests from running successfully.
    """

    def setup_method(self, method):
        """Setup test environment with clean factory state."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = str(uuid.uuid4())
        self.test_run_id = str(uuid.uuid4())
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_factory.create_llm_client_mock()

    async def test_agent_instance_factory_missing_registry_error(self):
        """FAILING TEST: Reproduce 'No agent registry configured' error from Golden Path tests.
        
        This test reproduces the exact error that's causing Golden Path integration test failures.
        The test should FAIL initially, demonstrating the issue that needs to be fixed.
        """
        factory = AgentInstanceFactory()
        user_context = UserExecutionContext.from_request_supervisor(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        with pytest.raises(RuntimeError) as exc_info:
            await factory.create_agent_instance('supervisor_orchestration', user_context)
        error_message = str(exc_info.value)
        assert 'No agent registry configured' in error_message
        logger.info(f' PASS:  Successfully reproduced Golden Path error: {error_message}')

    async def test_agent_instance_factory_empty_registry_error(self):
        """FAILING TEST: Reproduce empty agent registry error from Golden Path tests.
        
        This test reproduces the scenario where the registry exists but is empty,
        which also causes agent creation failures.
        """
        factory = AgentInstanceFactory()
        empty_registry = AgentClassRegistry()
        empty_registry.freeze()
        factory.configure(agent_class_registry=empty_registry)
        user_context = UserExecutionContext.from_request_supervisor(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        with pytest.raises(ValueError) as exc_info:
            await factory.create_agent_instance('supervisor_orchestration', user_context)
        error_message = str(exc_info.value)
        assert 'not found' in error_message.lower()
        logger.info(f' PASS:  Successfully reproduced empty registry error: {error_message}')

    async def test_configure_agent_instance_factory_fixes_registry(self):
        """PASSING TEST: Verify factory configuration resolves registry issues.
        
        This test demonstrates the correct way to configure the AgentInstanceFactory
        to resolve the Golden Path integration test failures.
        """
        factory = AgentInstanceFactory()
        registry = AgentClassRegistry()

        class SupervisorAgentTests(BaseAgent):

            def __init__(self, llm_manager=None, **kwargs):
                super().__init__(llm_manager=llm_manager, name='SupervisorAgentTests')

            async def execute(self, *args, **kwargs):
                return {'status': 'success', 'agent': 'test_supervisor'}
        test_agents = [('supervisor_orchestration', SupervisorAgentTests, 'Test supervisor for orchestration'), ('triage', SupervisorAgentTests, 'Test triage agent'), ('data_helper', SupervisorAgentTests, 'Test data helper agent'), ('apex_optimizer', SupervisorAgentTests, 'Test optimizer agent'), ('reporting', SupervisorAgentTests, 'Test reporting agent')]
        for agent_name, agent_class, description in test_agents:
            registry.register(agent_name, agent_class, description)
        registry.freeze()
        websocket_bridge = AgentWebSocketBridge()
        factory.configure(agent_class_registry=registry, websocket_bridge=websocket_bridge, llm_manager=self.mock_llm_manager)
        user_context = UserExecutionContext.from_request_supervisor(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        agent = await factory.create_agent_instance('supervisor_orchestration', user_context)
        assert agent is not None
        assert isinstance(agent, SupervisorAgentTests)
        logger.info(' PASS:  Agent creation succeeded after proper factory configuration')

    async def test_global_configure_agent_instance_factory_integration(self):
        """INTEGRATION TEST: Test global factory configuration pattern used in Golden Path.
        
        This test validates the configure_agent_instance_factory() function that should
        be called during system startup to prevent Golden Path test failures.
        """
        registry = AgentClassRegistry()

        class MockAgent(BaseAgent):

            async def execute(self, *args, **kwargs):
                return {'status': 'success'}
        registry.register('test_agent', MockAgent, 'Test agent')
        registry.freeze()
        websocket_bridge = AgentWebSocketBridge()
        configured_factory = await configure_agent_instance_factory(agent_class_registry=registry, websocket_bridge=websocket_bridge, llm_manager=self.mock_llm_manager)
        assert configured_factory is not None
        # Create user context for SSOT factory pattern
        user_context = UserExecutionContext.from_request_supervisor(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)

        # Create SSOT factory instance for testing
        ssot_factory = create_agent_instance_factory(user_context)
        agent = await ssot_factory.create_agent_instance('test_agent', user_context)
        assert agent is not None
        logger.info(' PASS:  Global factory configuration pattern validated')

    async def test_agent_class_registry_population_patterns(self):
        """UNIT TEST: Validate agent class registry population patterns from Golden Path.
        
        This test ensures the agent registry population logic works correctly
        and can handle the agent types that Golden Path tests require.
        """
        registry = AgentClassRegistry()
        self.assertEqual(len(registry), 0)

        class AgentTests(BaseAgent):
            pass
        registry.register('test_agent', AgentTests, 'Test agent description')
        self.assertEqual(len(registry), 1)
        retrieved_class = registry.get_agent_class('test_agent')
        self.assertEqual(retrieved_class, AgentTests)
        agent_names = registry.list_agent_names()
        self.assertIn('test_agent', agent_names)
        registry.freeze()
        with self.assertRaises(Exception):
            registry.register('another_agent', AgentTests, 'Another agent')
        logger.info(' PASS:  Agent class registry population patterns validated')

    async def test_websocket_bridge_configuration_requirements(self):
        """UNIT TEST: Validate WebSocket bridge configuration requirements.
        
        This test ensures that WebSocket bridge configuration works correctly
        and handles the None case gracefully (for test environments).
        """
        factory = AgentInstanceFactory()
        registry = AgentClassRegistry()

        class AgentTests(BaseAgent):

            async def execute(self, *args, **kwargs):
                return {'status': 'success'}
        registry.register('test_agent', AgentTests, 'Test agent')
        registry.freeze()
        factory.configure(agent_class_registry=registry, websocket_bridge=None, llm_manager=self.mock_llm_manager)
        user_context = UserExecutionContext.from_request_supervisor(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        agent = await factory.create_agent_instance('test_agent', user_context)
        self.assertIsNotNone(agent)
        websocket_bridge = AgentWebSocketBridge()
        factory.configure(agent_class_registry=registry, websocket_bridge=websocket_bridge, llm_manager=self.mock_llm_manager)
        agent = await factory.create_agent_instance('test_agent', user_context)
        self.assertIsNotNone(agent)
        logger.info(' PASS:  WebSocket bridge configuration patterns validated')

    async def test_llm_manager_dependency_validation(self):
        """UNIT TEST: Validate LLM manager dependency handling.
        
        This test ensures that agents requiring LLM managers fail appropriately
        when the dependency is not available, preventing silent failures.
        """
        factory = AgentInstanceFactory()
        registry = AgentClassRegistry()

        class LLMRequiredAgent(BaseAgent):

            def __init__(self, llm_manager=None, **kwargs):
                if not llm_manager:
                    raise ValueError('LLM manager is required')
                super().__init__(llm_manager=llm_manager, **kwargs)
        registry.register('llm_agent', LLMRequiredAgent, 'Agent requiring LLM')
        registry.freeze()
        factory.configure(agent_class_registry=registry, websocket_bridge=None, llm_manager=None)
        user_context = UserExecutionContext.from_request_supervisor(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        with self.assertRaises(RuntimeError) as cm:
            await factory.create_agent_instance('llm_agent', user_context)
        error_message = str(cm.exception)
        self.assertIn('LLM manager', error_message)
        factory.configure(agent_class_registry=registry, websocket_bridge=None, llm_manager=self.mock_llm_manager)
        agent = await factory.create_agent_instance('llm_agent', user_context)
        self.assertIsNotNone(agent)
        logger.info(' PASS:  LLM manager dependency validation completed')

    def teardown_method(self, method):
        """Clean up test environment."""
        # Create temporary user context for cleanup purposes
        cleanup_user_context = UserExecutionContext(
            user_id=f"cleanup_{UnifiedIdGenerator.generate_base_id('user')}",
            thread_id=f"cleanup_{UnifiedIdGenerator.generate_base_id('thread')}",
            run_id=UnifiedIdGenerator.generate_base_id('run')
        )
        factory = create_agent_instance_factory(cleanup_user_context)
        if hasattr(factory, 'reset_for_testing'):
            factory.reset_for_testing()
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')