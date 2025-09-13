"""
Comprehensive unit tests for ChatOrchestrator intent classification module.

Business Value: Tests the intent classification logic that routes user queries to appropriate
agent workflows, ensuring accurate categorization for optimal AI response generation.

Coverage Areas:
- Intent classification accuracy across all supported intent types
- Confidence scoring and threshold management
- Fallback handling for unclear or ambiguous intents
- Model cascade integration for classification decisions
- Edge cases and error handling

SSOT Compliance: Uses SSotAsyncTestCase, real LLM services, no mocks for core logic
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.intent_classifier import (
    IntentClassifier,
    IntentType
)
from netra_backend.app.agents.base.interface import ExecutionContext
from dataclasses import dataclass

@dataclass
class AgentState:
    """Simple agent state for testing ChatOrchestrator."""
    user_request: str = ""
    accumulated_data: dict = None

    def __post_init__(self):
        if self.accumulated_data is None:
            self.accumulated_data = {}
from netra_backend.app.llm.llm_manager import LLMManager


class TestChatOrchestratorIntentClassification(SSotAsyncTestCase):
    """Comprehensive tests for ChatOrchestrator intent classification business logic."""

    async def setUp(self):
        """Set up test environment with real services."""
        await super().setUp()

        # Initialize real LLM manager for testing
        self.llm_manager = LLMManager()
        self.intent_classifier = IntentClassifier(self.llm_manager)

        # Create test execution contexts
        self.optimization_context = self._create_test_context(
            "I need help optimizing my AI model performance and reducing costs"
        )
        self.tco_context = self._create_test_context(
            "What is the total cost of ownership for running GPT-4 vs Claude in production?"
        )
        self.pricing_context = self._create_test_context(
            "How much does it cost to run 1000 API calls per day?"
        )
        self.technical_context = self._create_test_context(
            "How do I implement batch processing for my API requests?"
        )
        self.general_context = self._create_test_context(
            "Hello, can you help me understand your platform?"
        )
        self.ambiguous_context = self._create_test_context(
            "I need something"  # Intentionally vague
        )

    def _create_test_context(self, user_request: str) -> ExecutionContext:
        """Create test execution context with user request."""
        state = AgentState()
        state.user_request = user_request

        context = ExecutionContext(
            request_id=f"test_req_{id(user_request)}",
            state=state,
            user_id="test_user_intent_classification"
        )
        return context

    async def test_optimization_intent_classification_accuracy(self):
        """Test accurate classification of optimization-related queries."""
        intent, confidence = await self.intent_classifier.classify(self.optimization_context)

        # Assert business logic: optimization queries should be classified correctly
        self.assertEqual(intent, IntentType.OPTIMIZATION_ADVICE)
        self.assertGreaterEqual(confidence, 0.7,
                               "Optimization intent should have high confidence")

        # Verify confidence reflects query clarity
        self.assertLessEqual(confidence, 1.0, "Confidence should not exceed 1.0")

    async def test_tco_analysis_intent_classification(self):
        """Test accurate classification of TCO analysis requests."""
        intent, confidence = await self.intent_classifier.classify(self.tco_context)

        # Assert business logic: TCO queries need high accuracy
        self.assertEqual(intent, IntentType.TCO_ANALYSIS)
        self.assertGreaterEqual(confidence, 0.75,
                               "TCO analysis requires high confidence classification")

    async def test_pricing_inquiry_intent_classification(self):
        """Test accurate classification of pricing-related questions."""
        intent, confidence = await self.intent_classifier.classify(self.pricing_context)

        # Assert business logic: pricing queries should be identified
        self.assertEqual(intent, IntentType.PRICING_INQUIRY)
        self.assertGreaterEqual(confidence, 0.6,
                               "Pricing inquiries should have reasonable confidence")

    async def test_technical_question_intent_classification(self):
        """Test accurate classification of technical implementation questions."""
        intent, confidence = await self.intent_classifier.classify(self.technical_context)

        # Assert business logic: technical questions properly categorized
        self.assertEqual(intent, IntentType.TECHNICAL_QUESTION)
        self.assertGreaterEqual(confidence, 0.65,
                               "Technical questions should be identifiable")

    async def test_general_inquiry_fallback_classification(self):
        """Test fallback to general inquiry for broad requests."""
        intent, confidence = await self.intent_classifier.classify(self.general_context)

        # Assert business logic: general inquiries as fallback category
        self.assertEqual(intent, IntentType.GENERAL_INQUIRY)
        self.assertGreaterEqual(confidence, 0.4,
                               "General inquiries should have moderate confidence")

    async def test_ambiguous_query_confidence_scoring(self):
        """Test confidence scoring for ambiguous or unclear queries."""
        intent, confidence = await self.intent_classifier.classify(self.ambiguous_context)

        # Assert business logic: ambiguous queries have lower confidence
        self.assertLessEqual(confidence, 0.6,
                            "Ambiguous queries should have lower confidence")
        self.assertEqual(intent, IntentType.GENERAL_INQUIRY,
                        "Ambiguous queries should default to general inquiry")

    async def test_intent_classification_prompt_building(self):
        """Test internal prompt building logic for classification."""
        prompt = self.intent_classifier._build_classification_prompt(self.optimization_context)

        # Assert business logic: prompt contains necessary components
        self.assertIn("optimization", prompt.lower())
        self.assertIn("category", prompt.lower())
        self.assertIn("JSON", prompt)

        # Verify all intent categories are included
        categories = self.intent_classifier._get_category_descriptions()
        for intent_type in IntentType:
            self.assertIn(intent_type.value, categories)

    async def test_classification_response_parsing_valid_json(self):
        """Test parsing of valid LLM classification responses."""
        valid_response = '{"intent": "optimization", "confidence": 0.85}'

        intent, confidence = self.intent_classifier._parse_classification_response(valid_response)

        # Assert business logic: valid responses parsed correctly
        self.assertEqual(intent, IntentType.OPTIMIZATION_ADVICE)
        self.assertEqual(confidence, 0.85)

    async def test_classification_response_parsing_invalid_json(self):
        """Test graceful handling of invalid JSON responses."""
        invalid_response = "This is not valid JSON"

        intent, confidence = self.intent_classifier._parse_classification_response(invalid_response)

        # Assert business logic: invalid responses default gracefully
        self.assertEqual(intent, IntentType.GENERAL_INQUIRY)
        self.assertEqual(confidence, 0.5)

    async def test_classification_response_parsing_invalid_intent(self):
        """Test handling of responses with invalid intent values."""
        invalid_intent_response = '{"intent": "invalid_intent_type", "confidence": 0.9}'

        intent, confidence = self.intent_classifier._parse_classification_response(invalid_intent_response)

        # Assert business logic: invalid intents default to general inquiry
        self.assertEqual(intent, IntentType.GENERAL_INQUIRY)
        self.assertEqual(confidence, 0.9)  # Keep original confidence

    async def test_confidence_extraction_boundary_values(self):
        """Test confidence extraction with boundary and edge values."""
        test_cases = [
            ('{"intent": "optimization", "confidence": -0.5}', 0.0),  # Below minimum
            ('{"intent": "optimization", "confidence": 1.5}', 1.0),   # Above maximum
            ('{"intent": "optimization", "confidence": 0.0}', 0.0),   # Minimum valid
            ('{"intent": "optimization", "confidence": 1.0}', 1.0),   # Maximum valid
            ('{"intent": "optimization", "confidence": "invalid"}', 0.5),  # Invalid type
        ]

        for response, expected_confidence in test_cases:
            with self.subTest(response=response):
                _, confidence = self.intent_classifier._parse_classification_response(response)
                self.assertEqual(confidence, expected_confidence)

    async def test_user_request_extraction_from_context(self):
        """Test extraction of user requests from execution context."""
        # Test with valid context and state
        extracted = self.intent_classifier._extract_user_request(self.optimization_context)
        self.assertEqual(extracted, "I need help optimizing my AI model performance and reducing costs")

        # Test with context but no state
        empty_context = ExecutionContext(request_id="test", state=None, user_id="test")
        extracted_empty = self.intent_classifier._extract_user_request(empty_context)
        self.assertEqual(extracted_empty, "")

        # Test with state but no user_request
        no_request_state = AgentState()
        no_request_state.user_request = None
        no_request_context = ExecutionContext(
            request_id="test",
            state=no_request_state,
            user_id="test"
        )
        extracted_none = self.intent_classifier._extract_user_request(no_request_context)
        self.assertEqual(extracted_none, "")

    async def test_all_intent_types_coverage(self):
        """Test that all defined intent types can be properly classified."""
        intent_test_cases = {
            IntentType.TCO_ANALYSIS: "Calculate the total cost of ownership for our AI infrastructure",
            IntentType.BENCHMARKING: "Compare performance between different LLM models",
            IntentType.PRICING_INQUIRY: "What are your pricing plans and costs?",
            IntentType.OPTIMIZATION_ADVICE: "How can I optimize my model performance?",
            IntentType.MARKET_RESEARCH: "What are the current trends in AI market?",
            IntentType.TECHNICAL_QUESTION: "How do I implement API rate limiting?",
            IntentType.GENERAL_INQUIRY: "Tell me about your platform"
        }

        for expected_intent, test_query in intent_test_cases.items():
            with self.subTest(intent=expected_intent.value):
                context = self._create_test_context(test_query)
                intent, confidence = await self.intent_classifier.classify(context)

                # Assert business logic: each intent type should be classifiable
                self.assertEqual(intent, expected_intent,
                               f"Failed to classify {test_query} as {expected_intent.value}")
                self.assertGreater(confidence, 0.0,
                                 f"Confidence should be positive for {expected_intent.value}")

    async def test_classification_consistency_multiple_calls(self):
        """Test consistency of classification across multiple calls."""
        # Run classification multiple times on same context
        results = []
        for _ in range(3):
            intent, confidence = await self.intent_classifier.classify(self.optimization_context)
            results.append((intent, confidence))

        # Assert business logic: classification should be consistent
        intents = [result[0] for result in results]
        confidences = [result[1] for result in results]

        # All intents should be the same
        self.assertTrue(all(intent == intents[0] for intent in intents),
                       "Intent classification should be consistent across calls")

        # Confidence values should be reasonably close (within 0.1)
        avg_confidence = sum(confidences) / len(confidences)
        for confidence in confidences:
            self.assertLess(abs(confidence - avg_confidence), 0.1,
                           "Confidence scores should be consistent across calls")

    @patch('netra_backend.app.llm.llm_manager.LLMManager.ask_llm')
    async def test_llm_service_integration_error_handling(self, mock_ask_llm):
        """Test graceful handling of LLM service errors during classification."""
        # Simulate LLM service error
        mock_ask_llm.side_effect = Exception("LLM service temporarily unavailable")

        # Classification should handle error gracefully
        with self.assertRaises(Exception) as context:
            await self.intent_classifier.classify(self.optimization_context)

        # Assert business logic: errors are propagated appropriately
        self.assertIn("LLM service temporarily unavailable", str(context.exception))

    async def test_intent_classifier_model_configuration(self):
        """Test that intent classifier uses appropriate model for classification."""
        # Assert business logic: uses fast, cost-effective model for classification
        self.assertEqual(self.intent_classifier.classification_model, "triage_llm")

        # Verify model choice makes business sense (fast classification)
        self.assertIn("triage", self.intent_classifier.classification_model)

    async def tearDown(self):
        """Clean up test environment."""
        # Clean up any test-specific resources
        await super().tearDown()


class TestIntentClassifierEdgeCases(SSotAsyncTestCase):
    """Test edge cases and error scenarios for intent classification."""

    async def setUp(self):
        """Set up test environment for edge case testing."""
        await super().setUp()
        self.llm_manager = LLMManager()
        self.intent_classifier = IntentClassifier(self.llm_manager)

    async def test_empty_user_request_handling(self):
        """Test handling of empty or whitespace-only user requests."""
        empty_context = self._create_test_context("")
        whitespace_context = self._create_test_context("   \n\t   ")

        # Test empty request
        intent, confidence = await self.intent_classifier.classify(empty_context)
        self.assertEqual(intent, IntentType.GENERAL_INQUIRY)
        self.assertLessEqual(confidence, 0.6)

        # Test whitespace-only request
        intent, confidence = await self.intent_classifier.classify(whitespace_context)
        self.assertEqual(intent, IntentType.GENERAL_INQUIRY)
        self.assertLessEqual(confidence, 0.6)

    def _create_test_context(self, user_request: str) -> ExecutionContext:
        """Create test execution context with user request."""
        state = AgentState()
        state.user_request = user_request

        context = ExecutionContext(
            request_id=f"test_req_{id(user_request)}",
            state=state,
            user_id="test_user_edge_cases"
        )
        return context

    async def test_very_long_user_request_handling(self):
        """Test handling of extremely long user requests."""
        # Create a very long request (simulate token limit testing)
        long_request = "optimization " * 1000  # 1000 repetitions
        long_context = self._create_test_context(long_request)

        intent, confidence = await self.intent_classifier.classify(long_context)

        # Should still classify correctly despite length
        self.assertEqual(intent, IntentType.OPTIMIZATION_ADVICE)
        self.assertGreater(confidence, 0.0)

    async def test_multilingual_request_handling(self):
        """Test handling of non-English user requests."""
        multilingual_contexts = [
            self._create_test_context("¿Cuánto cuesta optimizar mis modelos de IA?"),  # Spanish
            self._create_test_context("Comment optimiser les performances de mon IA?"),  # French
            self._create_test_context("如何优化我的AI模型性能？"),  # Chinese
        ]

        for context in multilingual_contexts:
            intent, confidence = await self.intent_classifier.classify(context)

            # Should provide some classification even for non-English
            self.assertIsInstance(intent, IntentType)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)

    async def tearDown(self):
        """Clean up edge case test environment."""
        await super().tearDown()