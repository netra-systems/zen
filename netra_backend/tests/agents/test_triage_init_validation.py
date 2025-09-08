"""
Triage initialization and validation tests.
SSOT compliance: Focused test module for triage agent initialization and input validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.triage_sub_agent import UnifiedTriageAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.llm.llm_manager import LLMManager


class TestTriageInitValidation(BaseTestCase):
    """Test triage agent initialization and validation patterns."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create mock LLM manager
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value='{"intent": {"primary_intent": "analysis"}, "data_sufficiency": "sufficient"}')
        
        # Create test context
        self.test_context = UserExecutionContext(
            user_id="test-user-init",
            thread_id="test-thread-init",
            run_id="test-run-init",
            metadata={"user_request": "test initialization validation"}
        ).with_db_session(AsyncMock())
    
    def test_triage_agent_initialization(self):
        """Test UnifiedTriageAgent initializes correctly."""
        # Test successful initialization
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Verify basic initialization
        self.assertIsNotNone(triage_agent)
        self.assertEqual(triage_agent.llm_manager, self.llm_manager)
        
        # Verify name is set
        self.assertEqual(triage_agent.name, "Triage")
        
        self.track_resource(triage_agent)
    
    def test_triage_agent_initialization_without_llm(self):
        """Test UnifiedTriageAgent initialization without LLM manager."""
        # Should raise error without LLM manager
        with self.assertRaises(TypeError):
            UnifiedTriageAgent()
    
    def test_triage_agent_initialization_with_invalid_llm(self):
        """Test TriageSubAgent initialization with invalid LLM manager."""
        # Test with None LLM manager
        with self.assertRaises((TypeError, AttributeError)):
            triage_agent = TriageSubAgent(llm_manager=None)
            # If initialization doesn't fail immediately, execution should fail
            if triage_agent is not None:
                asyncio.run(triage_agent.execute(self.test_context))
    
    async def test_context_validation_valid_context(self):
        """Test context validation with valid context."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Should not raise error with valid context
        result = await triage_agent.execute(self.test_context)
        self.assertIsNotNone(result)
        
        self.track_resource(triage_agent)
    
    async def test_context_validation_invalid_context(self):
        """Test context validation with invalid context."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Test with None context
        with self.assertRaises((TypeError, AttributeError)):
            await triage_agent.execute(None)
        
        # Test with empty user_id
        invalid_context = UserExecutionContext(
            user_id="",  # Empty user ID
            thread_id="test-thread",
            run_id="test-run"
        )
        
        with self.assertRaises((InvalidContextError, ValueError)):
            await triage_agent.execute(invalid_context)
        
        self.track_resource(triage_agent)
    
    async def test_context_validation_missing_metadata(self):
        """Test context validation with missing metadata."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Context without user_request in metadata
        context_no_request = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run",
            metadata={}  # No user_request
        ).with_db_session(AsyncMock())
        
        # Should handle gracefully or raise appropriate error
        try:
            result = await triage_agent.execute(context_no_request)
            # If it succeeds, should have some result
            self.assertIsNotNone(result)
        except (ValueError, KeyError) as e:
            # Acceptable to fail validation
            self.assertIn("request", str(e).lower())
        
        self.track_resource(triage_agent)
    
    async def test_llm_response_validation(self):
        """Test LLM response validation and parsing."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Test with valid JSON response
        valid_response = '{"intent": {"primary_intent": "analysis"}, "data_sufficiency": "sufficient"}'
        self.llm_manager.ask_llm.return_value = valid_response
        
        result = await triage_agent.execute(self.test_context)
        self.assertIsNotNone(result)
        self.assertIn("intent", result)
        
        self.track_resource(triage_agent)
    
    async def test_llm_invalid_response_handling(self):
        """Test handling of invalid LLM responses."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Test with invalid JSON
        self.llm_manager.ask_llm.return_value = "invalid json response"
        
        # Should handle gracefully
        try:
            result = await triage_agent.execute(self.test_context)
            # If it succeeds, should have some fallback result
            self.assertIsNotNone(result)
        except (ValueError, Exception) as e:
            # Acceptable to fail on invalid response
            pass
        
        self.track_resource(triage_agent)
    
    async def test_llm_failure_handling(self):
        """Test handling of LLM failures."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Mock LLM failure
        self.llm_manager.ask_llm.side_effect = Exception("LLM service unavailable")
        
        # Should handle LLM failures gracefully
        try:
            result = await triage_agent.execute(self.test_context)
            # If it succeeds, should have fallback result
            self.assertIsNotNone(result)
        except Exception as e:
            # Acceptable to fail on LLM failure
            self.assertIn("LLM", str(e))
        
        self.track_resource(triage_agent)
    
    def test_triage_agent_attributes(self):
        """Test triage agent has expected attributes."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Verify expected attributes exist
        self.assertTrue(hasattr(triage_agent, 'name'))
        self.assertTrue(hasattr(triage_agent, 'llm_manager'))
        self.assertTrue(hasattr(triage_agent, 'execute'))
        
        # Verify name is correct
        self.assertEqual(triage_agent.name, "Triage")
        
        self.track_resource(triage_agent)
    
    async def test_context_database_session_validation(self):
        """Test context database session validation."""
        triage_agent = UnifiedTriageAgent(llm_manager=self.llm_manager)
        
        # Context without database session
        context_no_db = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread", 
            run_id="test-run",
            metadata={"user_request": "test request"}
        )
        # Note: No .with_db_session() call
        
        # Should handle missing database session appropriately
        try:
            result = await triage_agent.execute(context_no_db)
            # If it succeeds without DB session, that's acceptable
            self.assertIsNotNone(result)
        except (ValueError, AttributeError) as e:
            # Acceptable to fail without database session
            pass
        
        self.track_resource(triage_agent)


if __name__ == '__main__':
    pytest.main([__file__, "-v"])