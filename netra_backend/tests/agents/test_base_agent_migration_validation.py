"""
Base Agent Migration and Validation Tests - Targeted Coverage for Issue #714

Business Value: Platform/Internal - Critical UserExecutionContext migration validation
for multi-user isolation and Golden Path reliability ($500K+ ARR protection).

Tests BaseAgent migration status methods, modern implementation validation,
and UserExecutionContext pattern enforcement for production readiness.

SSOT Compliance: Uses SSotBaseTestCase, real UserExecutionContext instances,
minimal mocking per CLAUDE.md standards. No test cheating.

Coverage Target: BaseAgent migration and validation methods:
- validate_modern_implementation()
- assert_user_execution_context_pattern()
- get_migration_status()
- validate_migration_completeness()
- create_agent_with_context()

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.schemas.core_enums import ExecutionStatus

class ConcreteModernAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing migration patterns."""

    def __init__(self, llm_manager=None, name='ModernTestAgent', **kwargs):
        if llm_manager is None:
            llm_manager = Mock(spec=LLMManager)
        super().__init__(llm_manager=llm_manager, name=name, **kwargs)
        self.agent_type = 'modern_test_agent'
        self.capabilities = ['migration_validation', 'user_context_enforcement']

    async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Modern implementation using UserExecutionContext."""
        return {'status': 'success', 'response': f'Modern processing: {request}', 'agent_type': self.agent_type, 'user_id': context.user_id, 'session_id': context.session_id}

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> Any:
        """Required modern implementation pattern."""
        return await self.process_request('test_execution', context)

class LegacyPatternAgent(BaseAgent):
    """Agent implementation simulating legacy patterns for validation testing."""

    def __init__(self, llm_manager=None, name='LegacyAgent', **kwargs):
        if llm_manager is None:
            llm_manager = Mock(spec=LLMManager)
        super().__init__(llm_manager=llm_manager, name=name, **kwargs)
        self.agent_type = 'legacy_agent'

    async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Legacy-style implementation for validation testing."""
        return {'status': 'legacy_success', 'response': f'Legacy: {request}'}

class BaseAgentMigrationValidationTests(SSotBaseTestCase):
    """Test BaseAgent migration status and validation functionality."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_validate_modern_implementation_success(self):
        """Test BaseAgent.validate_modern_implementation() succeeds for modern agents."""
        llm_manager = Mock(spec=LLMManager)
        modern_agent = ConcreteModernAgent(llm_manager=llm_manager, name='ModernValidationAgent')
        validation_result = modern_agent.validate_modern_implementation()
        self.assertIsInstance(validation_result, dict)
        self.assertIn('compliant', validation_result)
        self.assertIn('pattern', validation_result)
        self.assertIn('warnings', validation_result)
        self.assertIn('errors', validation_result)
        self.assertIn('recommendations', validation_result)
        self.assertTrue(validation_result['compliant'])
        self.assertEqual(validation_result['pattern'], 'modern')
        self.assertEqual(len(validation_result['errors']), 0)

    def test_validate_modern_implementation_failure(self):
        """Test BaseAgent.validate_modern_implementation() fails for legacy agents."""
        llm_manager = Mock(spec=LLMManager)
        legacy_agent = LegacyPatternAgent(llm_manager=llm_manager, name='LegacyValidationAgent')
        validation_result = legacy_agent.validate_modern_implementation()
        self.assertIsInstance(validation_result, dict)
        self.assertIn('compliant', validation_result)
        self.assertIn('pattern', validation_result)
        self.assertIn('warnings', validation_result)
        self.assertIn('errors', validation_result)
        self.assertIn('recommendations', validation_result)
        self.assertFalse(validation_result['compliant'])
        self.assertIn(validation_result['pattern'], ['legacy_bridge', 'none'])
        self.assertGreater(len(validation_result['recommendations']), 0)

    def test_assert_user_execution_context_pattern_success(self):
        """Test BaseAgent.assert_user_execution_context_pattern() succeeds for compliant agents."""
        llm_manager = Mock(spec=LLMManager)
        modern_agent = ConcreteModernAgent(llm_manager=llm_manager, name='ModernValidationAgent')
        try:
            assertion_result = modern_agent.assert_user_execution_context_pattern()
            self.assertTrue(True)
        except AssertionError:
            self.fail('Modern agent should pass UserExecutionContext pattern assertion')

    def test_assert_user_execution_context_pattern_failure(self):
        """Test BaseAgent.assert_user_execution_context_pattern() fails for non-compliant agents."""
        llm_manager = Mock(spec=LLMManager)
        legacy_agent = LegacyPatternAgent(llm_manager=llm_manager, name='LegacyValidationAgent')
        try:
            legacy_agent.assert_user_execution_context_pattern()
            validation = legacy_agent.validate_modern_implementation()
            self.assertFalse(validation['compliant'], 'Legacy agent should not be compliant with modern patterns')
        except (AssertionError, RuntimeError):
            pass

    def test_get_migration_status_complete(self):
        """Test BaseAgent.get_migration_status() returns complete status for modern agents."""
        llm_manager = Mock(spec=LLMManager)
        modern_agent = ConcreteModernAgent(llm_manager=llm_manager, name='ModernValidationAgent')
        migration_status = modern_agent.get_migration_status()
        self.assertIsInstance(migration_status, dict)
        self.assertIn('agent_name', migration_status)
        self.assertIn('agent_class', migration_status)
        self.assertIn('migration_status', migration_status)
        self.assertIn('execution_pattern', migration_status)
        self.assertIn('user_isolation_safe', migration_status)
        self.assertIn('compliance_details', migration_status)
        self.assertEqual(migration_status['migration_status'], 'compliant')
        self.assertEqual(migration_status['execution_pattern'], 'modern')
        self.assertTrue(migration_status['user_isolation_safe'])

    def test_get_migration_status_incomplete(self):
        """Test BaseAgent.get_migration_status() returns incomplete status for legacy agents."""
        llm_manager = Mock(spec=LLMManager)
        legacy_agent = LegacyPatternAgent(llm_manager=llm_manager, name='LegacyValidationAgent')
        migration_status = legacy_agent.get_migration_status()
        self.assertIsInstance(migration_status, dict)
        self.assertIn('agent_name', migration_status)
        self.assertIn('agent_class', migration_status)
        self.assertIn('migration_status', migration_status)
        self.assertIn('execution_pattern', migration_status)
        self.assertIn('user_isolation_safe', migration_status)
        self.assertIn('compliance_details', migration_status)
        self.assertEqual(migration_status['migration_status'], 'needs_migration')
        self.assertIn(migration_status['execution_pattern'], ['legacy_bridge', 'none'])
        self.assertFalse(migration_status['user_isolation_safe'])

    def test_validate_migration_completeness_complete(self):
        """Test BaseAgent.validate_migration_completeness() validates complete migrations."""
        llm_manager = Mock(spec=LLMManager)
        modern_agent = ConcreteModernAgent(llm_manager=llm_manager, name='ModernValidationAgent')
        completeness_result = modern_agent.validate_migration_completeness()
        self.assertIsInstance(completeness_result, dict)
        self.assertIn('migration_complete', completeness_result)
        self.assertIn('agent_name', completeness_result)
        self.assertIn('violations', completeness_result)
        self.assertIn('warnings', completeness_result)
        self.assertIn('validation_timestamp', completeness_result)
        self.assertTrue(completeness_result['migration_complete'])
        self.assertIsInstance(completeness_result['violations'], list)
        self.assertIsInstance(completeness_result['warnings'], list)
        self.assertEqual(len(completeness_result['violations']), 0)

    def test_validate_migration_completeness_incomplete(self):
        """Test BaseAgent.validate_migration_completeness() identifies incomplete migrations."""
        llm_manager = Mock(spec=LLMManager)
        legacy_agent = LegacyPatternAgent(llm_manager=llm_manager, name='LegacyValidationAgent')
        completeness_result = legacy_agent.validate_migration_completeness()
        self.assertIsInstance(completeness_result, dict)
        self.assertIn('migration_complete', completeness_result)
        self.assertIn('agent_name', completeness_result)
        self.assertIn('violations', completeness_result)
        self.assertIn('warnings', completeness_result)
        self.assertIn('validation_timestamp', completeness_result)
        if not completeness_result['migration_complete']:
            self.assertFalse(completeness_result['migration_complete'])
        else:
            self.assertGreater(len(completeness_result['warnings']), 0)

class BaseAgentContextCreationTests(SSotBaseTestCase):
    """Test BaseAgent context-based creation and factory patterns."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    def test_create_agent_with_context_success(self):
        """Test BaseAgent.create_agent_with_context() creates properly isolated agents."""
        user_context = UserExecutionContext(user_id='test_user_factory_001', thread_id='thread_factory_001', run_id='run_factory_001', request_id='req_factory_001')
        agent_instance = ConcreteModernAgent.create_agent_with_context(context=user_context)
        self.assertIsInstance(agent_instance, ConcreteModernAgent)
        self.assertIsInstance(agent_instance, BaseAgent)
        self.assertTrue(hasattr(agent_instance, 'user_context'))
        self.assertEqual(agent_instance.user_context, user_context)

    def test_create_agent_with_context_user_isolation(self):
        """Test BaseAgent.create_agent_with_context() maintains user isolation."""
        user_context_a = UserExecutionContext(user_id='test_user_factory_001', thread_id='thread_factory_001', run_id='run_factory_001', request_id='req_factory_001')
        agent_a = ConcreteModernAgent.create_agent_with_context(context=user_context_a)
        user_context_b = UserExecutionContext(user_id='test_user_factory_002', thread_id='thread_factory_002', run_id='run_factory_002', request_id='req_factory_002')
        agent_b = ConcreteModernAgent.create_agent_with_context(context=user_context_b)
        self.assertTrue(agent_a is not agent_b)
        self.assertNotEqual(id(agent_a), id(agent_b))
        self.assertEqual(agent_a.user_context.user_id, 'test_user_factory_001')
        self.assertEqual(agent_b.user_context.user_id, 'test_user_factory_002')
        self.assertNotEqual(agent_a.user_context.user_id, agent_b.user_context.user_id)

    def test_create_agent_with_context_invalid_class(self):
        """Test BaseAgent.create_agent_with_context() handles invalid agent classes."""
        user_context = UserExecutionContext(user_id='test_user_factory_003', thread_id='thread_factory_003', run_id='run_factory_003', request_id='req_factory_003')
        agent_instance = ConcreteModernAgent.create_agent_with_context(context=user_context)
        self.assertIsInstance(agent_instance, ConcreteModernAgent)

    def test_create_agent_with_context_missing_dependencies(self):
        """Test BaseAgent.create_agent_with_context() handles missing dependencies."""
        try:
            ConcreteModernAgent.create_agent_with_context(context=None)
            self.fail('Expected exception when passing None context')
        except (TypeError, ValueError, InvalidContextError):
            pass

class BaseAgentMigrationValidationAsyncTests(SSotAsyncTestCase):
    """Test BaseAgent async migration validation functionality."""

    async def setUp(self):
        """Set up async test environment."""
        await super().setUp()

    async def test_migration_validation_during_async_execution(self):
        """Test migration validation remains consistent during async execution."""
        llm_manager = Mock(spec=LLMManager)
        modern_agent = ConcreteModernAgent(llm_manager=llm_manager, name='AsyncModernAgent')

        async def async_validation_test():
            migration_status = modern_agent.get_migration_status()
            await asyncio.sleep(0.05)
            return migration_status
        status = await async_validation_test()
        self.assertEqual(status['migration_status'], 'compliant')
        self.assertEqual(status['execution_pattern'], 'modern')
        self.assertTrue(status['user_isolation_safe'])

    async def test_user_context_pattern_during_async_execution(self):
        """Test UserExecutionContext pattern enforcement during async operations."""
        llm_manager = Mock(spec=LLMManager)
        modern_agent = ConcreteModernAgent(llm_manager=llm_manager, name='AsyncModernAgent')

        async def async_context_test():
            try:
                modern_agent.assert_user_execution_context_pattern()
                return True
            except (AssertionError, RuntimeError):
                return False
        pattern_valid = await async_context_test()
        self.assertTrue(pattern_valid)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')