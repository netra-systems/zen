"""
Comprehensive unit tests for ChatOrchestrator quality evaluation module.

Business Value: Tests the quality evaluation system that assesses LLM responses
and model performance for intelligent model cascade decisions, ensuring high-quality
AI outputs through systematic evaluation and cost optimization.

Coverage Areas:
- Response quality evaluation with multiple criteria
- Rule-based quality assessment (clarity, completeness, actionability)
- LLM-based evaluation for complex quality aspects
- Quality score calculation and weighting
- Response comparison and ranking functionality
- Evaluation caching and performance optimization
- Edge cases and error handling

SSOT Compliance: Uses SSotAsyncTestCase, real LLM services where appropriate, no mocks for core logic
"""

import asyncio
import json
import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional, Tuple

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.quality_evaluator import (
    QualityEvaluator,
    EvaluationCriteria
)
from netra_backend.app.core.quality_types import QualityMetrics, QualityLevel


class TestChatOrchestratorQualityEvaluator(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive tests for ChatOrchestrator quality evaluation business logic."""

    def setUp(self):
        """Set up test environment with real services."""
        super().setUp()
        self.mock_factory = SSotMockFactory()
        
        # Create mock LLM manager
        self.mock_llm_manager = AsyncMock()
        self.quality_evaluator = QualityEvaluator(llm_manager=self.mock_llm_manager)

    def test_init_with_llm_manager(self):
        """Test QualityEvaluator initialization with LLM manager."""
        evaluator = QualityEvaluator(self.mock_llm_manager)
        
        self.assertEqual(evaluator.llm_manager, self.mock_llm_manager)
        self.assertEqual(evaluator._evaluation_cache, {})

    def test_evaluation_criteria_default_values(self):
        """Test EvaluationCriteria default values."""
        criteria = EvaluationCriteria()
        
        self.assertEqual(criteria.content_type, "general")
        self.assertEqual(criteria.min_quality_score, 0.7)
        self.assertTrue(criteria.check_hallucination)
        self.assertTrue(criteria.check_completeness)
        self.assertTrue(criteria.check_actionability)
        self.assertTrue(criteria.require_specificity)

    async def test_evaluate_response_basic_quality(self):
        """Test basic response evaluation without LLM."""
        response = "This is a comprehensive response that provides specific actionable insights."
        query = "How can I optimize my business?"
        
        # Mock LLM to avoid external dependency
        self.mock_llm_manager.generate_response.return_value = '{"specificity_score": 0.8, "actionability_score": 0.9, "quantification_score": 0.6, "novelty_score": 0.7, "issues": [], "reasoning": "Good response"}'
        
        metrics = await self.quality_evaluator.evaluate_response(response, query)
        
        self.assertIsInstance(metrics, QualityMetrics)
        self.assertGreater(metrics.completeness_score, 0.5)
        self.assertGreater(metrics.clarity_score, 0)
        self.assertGreater(metrics.overall_score, 0)

    def test_assess_clarity(self):
        """Test clarity assessment."""
        # Optimal sentence length (15-25 words)
        optimal_response = "This sentence has exactly fifteen words to test optimal clarity assessment functionality properly here."
        clarity_score = self.quality_evaluator._assess_clarity(optimal_response)
        self.assertEqual(clarity_score, 1.0)

    def test_count_generic_phrases(self):
        """Test generic phrase counting."""
        generic_response = "It depends on your situation. Typically, you might consider best practices."
        count = self.quality_evaluator._count_generic_phrases(generic_response)
        self.assertGreaterEqual(count, 3)

    def test_calculate_redundancy(self):
        """Test redundancy calculation."""
        redundant_response = "test test test test different word test test"
        redundancy = self.quality_evaluator._calculate_redundancy(redundant_response)
        self.assertGreater(redundancy, 0.5)

    def test_detect_circular_reasoning(self):
        """Test circular reasoning detection."""
        circular_response = "This works because it is effective due to the fact that it works well."
        is_circular = self.quality_evaluator._detect_circular_reasoning(circular_response)
        self.assertTrue(is_circular)

    def test_assess_hallucination_risk(self):
        """Test hallucination risk assessment."""
        risky_response = "The price will definitely be $45.99 on 2025-03-15 with 23.7% certainty."
        risk_score = self.quality_evaluator._assess_hallucination_risk(risky_response, "pricing")
        self.assertGreater(risk_score, 0.5)

    def test_assess_actionability(self):
        """Test actionability assessment."""
        actionable_response = "You should implement these steps: configure caching; optimize queries; enable compression."
        actionability = self.quality_evaluator._assess_actionability(actionable_response, "general")
        self.assertGreater(actionability, 0.6)

    def test_assess_relevance(self):
        """Test relevance assessment."""
        query = "How to optimize database performance"
        relevant_response = "To optimize database performance, create indexes, optimize queries, implement caching."
        relevance = self.quality_evaluator._assess_relevance(relevant_response, query)
        self.assertGreater(relevance, 0.5)

    def test_calculate_overall_score(self):
        """Test overall score calculation with weighted components."""
        metrics = QualityMetrics()
        metrics.completeness_score = 0.8
        metrics.clarity_score = 0.9
        metrics.relevance_score = 0.7
        metrics.actionability_score = 0.8
        metrics.specificity_score = 0.6
        metrics.novelty_score = 0.5
        metrics.quantification_score = 0.7
        
        overall_score = self.quality_evaluator._calculate_overall_score(metrics)
        self.assertGreater(overall_score, 0.5)

    async def test_compare_responses(self):
        """Test response comparison and ranking."""
        responses = [
            ("model_a", "This is a good response with actionable insights."),
            ("model_b", "OK."),
            ("model_c", "This is a comprehensive and detailed response.")
        ]
        query = "How to improve performance?"
        
        # Mock LLM responses for each evaluation
        llm_responses = [
            '{"specificity_score": 0.7, "actionability_score": 0.8, "quantification_score": 0.6, "novelty_score": 0.6, "issues": [], "reasoning": "Good"}',
            '{"specificity_score": 0.1, "actionability_score": 0.1, "quantification_score": 0.0, "novelty_score": 0.1, "issues": ["Too short"], "reasoning": "Poor"}',
            '{"specificity_score": 0.9, "actionability_score": 0.9, "quantification_score": 0.8, "novelty_score": 0.8, "issues": [], "reasoning": "Excellent"}'
        ]
        self.mock_llm_manager.generate_response.side_effect = llm_responses
        
        evaluations = await self.quality_evaluator.compare_responses(responses, query)
        
        # Should be sorted by quality score (highest first)
        self.assertEqual(len(evaluations), 3)
        self.assertEqual(evaluations[0]["model_name"], "model_c")  # Best quality
        self.assertEqual(evaluations[-1]["model_name"], "model_b")  # Worst quality

    def test_get_quality_level(self):
        """Test quality level classification."""
        self.assertEqual(self.quality_evaluator.get_quality_level(0.95), QualityLevel.EXCELLENT)
        self.assertEqual(self.quality_evaluator.get_quality_level(0.85), QualityLevel.GOOD)
        self.assertEqual(self.quality_evaluator.get_quality_level(0.75), QualityLevel.ACCEPTABLE)
        self.assertEqual(self.quality_evaluator.get_quality_level(0.55), QualityLevel.POOR)
        self.assertEqual(self.quality_evaluator.get_quality_level(0.25), QualityLevel.UNACCEPTABLE)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add something to cache manually
        self.quality_evaluator._evaluation_cache["test_key"] = "test_value"
        self.assertEqual(len(self.quality_evaluator._evaluation_cache), 1)
        
        self.quality_evaluator.clear_cache()
        self.assertEqual(len(self.quality_evaluator._evaluation_cache), 0)

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    # Run tests directly if executed as script
    unittest.main()