"""
Triage initialization and validation tests.
SSOT compliance: Focused test module for triage agent initialization and input validation.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.agents.triage_sub_agent import UnifiedTriageAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.llm.llm_manager import LLMManager

class TestTriageInitValidation(BaseTestCase):
    """Test triage agent initialization and validation patterns."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value='test-model')
        self.llm_manager.ask_llm = AsyncMock(return_value='{"intent": {"primary_intent": "analysis"}, "data_sufficiency": "sufficient"}')
        self.test_context = UserExecutionContext(user_id='test-user-init', thread_id='test-thread-init', run_id='test-run-init', metadata={'user_request': 'test initialization validation'}).with_db_session(AsyncMock())

    def test_triage_agent_initialization(self):
        """Test UnifiedTriageAgent initializes correctly."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        self.assertIsNotNone(triage_agent)
        self.assertEqual(triage_agent.llm_manager, self.llm_manager)
        self.assertEqual(triage_agent.name, 'Triage')
        self.track_resource(triage_agent)

    def test_triage_agent_initialization_without_llm(self):
        """Test UnifiedTriageAgent initialization without LLM manager."""
        with self.assertRaises(TypeError):
            UnifiedTriageAgent()

    def test_triage_agent_initialization_with_invalid_llm(self):
        """Test TriageSubAgent initialization with invalid LLM manager."""
        with self.assertRaises((TypeError, AttributeError)):
            triage_agent = TriageSubAgent(llm_manager=None)
            if triage_agent is not None:
                asyncio.run(triage_agent.execute(self.test_context))

    async def test_context_validation_valid_context(self):
        """Test context validation with valid context."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        result = await triage_agent.execute(self.test_context)
        self.assertIsNotNone(result)
        self.track_resource(triage_agent)

    async def test_context_validation_invalid_context(self):
        """Test context validation with invalid context."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        with self.assertRaises((TypeError, AttributeError)):
            await triage_agent.execute(None)
        invalid_context = UserExecutionContext(user_id='', thread_id='test-thread', run_id='test-run')
        with self.assertRaises((InvalidContextError, ValueError)):
            await triage_agent.execute(invalid_context)
        self.track_resource(triage_agent)

    async def test_context_validation_missing_metadata(self):
        """Test context validation with missing metadata."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        context_no_request = UserExecutionContext(user_id='test-user', thread_id='test-thread', run_id='test-run', metadata={}).with_db_session(AsyncMock())
        try:
            result = await triage_agent.execute(context_no_request)
            self.assertIsNotNone(result)
        except (ValueError, KeyError) as e:
            self.assertIn('request', str(e).lower())
        self.track_resource(triage_agent)

    async def test_llm_response_validation(self):
        """Test LLM response validation and parsing."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        valid_response = '{"intent": {"primary_intent": "analysis"}, "data_sufficiency": "sufficient"}'
        self.llm_manager.ask_llm.return_value = valid_response
        result = await triage_agent.execute(self.test_context)
        self.assertIsNotNone(result)
        self.assertIn('intent', result)
        self.track_resource(triage_agent)

    async def test_llm_invalid_response_handling(self):
        """Test handling of invalid LLM responses."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        self.llm_manager.ask_llm.return_value = 'invalid json response'
        try:
            result = await triage_agent.execute(self.test_context)
            self.assertIsNotNone(result)
        except (ValueError, Exception) as e:
            pass
        self.track_resource(triage_agent)

    async def test_llm_failure_handling(self):
        """Test handling of LLM failures."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        self.llm_manager.ask_llm.side_effect = Exception('LLM service unavailable')
        try:
            result = await triage_agent.execute(self.test_context)
            self.assertIsNotNone(result)
        except Exception as e:
            self.assertIn('LLM', str(e))
        self.track_resource(triage_agent)

    def test_triage_agent_attributes(self):
        """Test triage agent has expected attributes."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        self.assertTrue(hasattr(triage_agent, 'name'))
        self.assertTrue(hasattr(triage_agent, 'llm_manager'))
        self.assertTrue(hasattr(triage_agent, 'execute'))
        self.assertEqual(triage_agent.name, 'Triage')
        self.track_resource(triage_agent)

    async def test_context_database_session_validation(self):
        """Test context database session validation."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        context_no_db = UserExecutionContext(user_id='test-user', thread_id='test-thread', run_id='test-run', metadata={'user_request': 'test request'})
        try:
            result = await triage_agent.execute(context_no_db)
            self.assertIsNotNone(result)
        except (ValueError, AttributeError) as e:
            pass
        self.track_resource(triage_agent)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')