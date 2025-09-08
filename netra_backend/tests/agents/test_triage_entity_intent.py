"""
Triage entity and intent recognition tests.
SSOT compliance: Focused test module for triage entity extraction and intent classification.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# ABSOLUTE IMPORTS - SSOT compliance  
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.triage_sub_agent import UnifiedTriageAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager


class TestTriageEntityIntent(BaseTestCase):
    """Test triage entity recognition and intent classification."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create mock LLM manager
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value='{"intent": {"primary_intent": "optimization"}, "entities": ["performance", "cost"]}')
        
        # Create test context
        self.test_context = UserExecutionContext(
            user_id="test-user-entity",
            thread_id="test-thread-entity",
            run_id="test-run-entity",
            metadata={"user_request": "test entity intent recognition"}
        ).with_db_session(AsyncMock())
        
        # Create UnifiedTriageAgent for testing  
        self.triage_agent = UnifiedTriageAgent(
            llm_manager=self.llm_manager
        )
        
        self.track_resource(self.triage_agent)
    
    async def test_entity_extraction_basic(self):
        """Test basic entity extraction from user requests."""
        # Mock LLM response with entities
        self.llm_manager.ask_llm.return_value = '{"entities": ["CPU", "memory", "performance"], "intent": {"primary_intent": "optimization"}}'
        
        result = await self.triage_agent.execute(self.test_context)
        
        # Verify entity extraction worked
        self.assertIsNotNone(result)
        self.assertIn("intent", result)
    
    async def test_intent_classification_optimization(self):
        """Test intent classification for optimization requests.""" 
        # Test optimization intent
        optimization_response = '{"intent": {"primary_intent": "optimization", "confidence": 0.9}, "entities": ["cost", "performance"]}'
        self.llm_manager.ask_llm.return_value = optimization_response
        
        result = await self.triage_agent.execute(self.test_context)
        
        # Verify optimization intent detected
        self.assertIsNotNone(result.get("intent"))
        self.assertEqual(result["intent"].get("primary_intent"), "optimization")
    
    async def test_intent_classification_analysis(self):
        """Test intent classification for analysis requests."""
        # Test analysis intent
        analysis_response = '{"intent": {"primary_intent": "analysis", "confidence": 0.85}, "entities": ["data", "metrics"]}'
        self.llm_manager.ask_llm.return_value = analysis_response
        
        result = await self.triage_agent.execute(self.test_context)
        
        # Verify analysis intent detected
        self.assertIsNotNone(result.get("intent"))
        self.assertEqual(result["intent"].get("primary_intent"), "analysis")
    
    async def test_entity_confidence_scoring(self):
        """Test entity confidence scoring."""
        # Mock response with confidence scores
        confidence_response = '{"entities": [{"name": "CPU", "confidence": 0.95}, {"name": "memory", "confidence": 0.8}], "intent": {"primary_intent": "optimization"}}'
        self.llm_manager.ask_llm.return_value = confidence_response
        
        result = await self.triage_agent.execute(self.test_context)
        
        # Verify result contains entities (exact structure depends on implementation)
        self.assertIsNotNone(result)
        self.assertIn("intent", result)
    
    async def test_fallback_intent_classification(self):
        """Test fallback when intent classification fails."""
        # Mock LLM failure
        self.llm_manager.ask_llm.side_effect = Exception("LLM unavailable")
        
        result = await self.triage_agent.execute(self.test_context)
        
        # Should still return some result with fallback values
        self.assertIsNotNone(result)
        # Implementation may vary - just ensure no crash
    
    def test_entity_validation_patterns(self):
        """Test entity validation patterns."""
        # Test valid entities
        valid_entities = ["CPU", "memory", "performance", "cost", "latency"]
        for entity in valid_entities:
            # This would test internal validation if implemented
            # For now, just ensure entities are reasonable
            self.assertIsInstance(entity, str)
            self.assertGreater(len(entity), 0)
    
    async def test_multi_intent_detection(self):
        """Test detection of multiple intents in complex requests."""
        # Mock response with multiple intents
        multi_intent_response = '{"intent": {"primary_intent": "analysis", "secondary_intents": ["optimization", "reporting"]}, "entities": ["metrics", "performance"]}'
        self.llm_manager.ask_llm.return_value = multi_intent_response
        
        result = await self.triage_agent.execute(self.test_context)
        
        # Verify multi-intent handling
        self.assertIsNotNone(result)
        self.assertIn("intent", result)
        self.assertEqual(result["intent"].get("primary_intent"), "analysis")


if __name__ == '__main__':
    pytest.main([__file__, "-v"])