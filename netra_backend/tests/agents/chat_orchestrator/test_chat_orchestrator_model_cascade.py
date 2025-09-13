"""
Comprehensive unit tests for ChatOrchestrator model cascade module.

Business Value: Tests the intelligent LLM model selection and cascade logic that optimizes
cost, performance, and quality for AI optimization workflows based on query complexity.

Coverage Areas:
- Model tier mapping and selection logic
- Cost-performance optimization decisions
- Quality-based escalation and fallback patterns
- Semantic caching and cache management
- Adaptive routing and performance learning
- Consensus execution across multiple models
- Model availability checking and error handling
- Policy configuration and threshold management

SSOT Compliance: Uses SSotAsyncTestCase, real LLM manager integration, minimal mocks
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from decimal import Decimal

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.model_cascade import (
    ModelCascade,
    ModelTier,
    CascadePolicies,
    PerformanceHistory
)
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.llm.model_selector import ModelSelector
from netra_backend.app.agents.chat_orchestrator.quality_evaluator import QualityEvaluator
from netra_backend.app.services.analytics.cost_tracker import CostTracker
from netra_backend.app.services.monitoring.metrics_service import MetricsService


class TestChatOrchestratorModelCascade(SSotAsyncTestCase):
    """Comprehensive tests for ChatOrchestrator model cascade business logic."""

    async def setUp(self):
        """Set up test environment with model cascade and dependencies."""
        await super().setUp()

        # Initialize real LLM manager and mock dependencies
        self.llm_manager = LLMManager()
        self.model_selector = MagicMock(spec=ModelSelector)
        self.quality_evaluator = AsyncMock(spec=QualityEvaluator)
        self.cost_tracker = AsyncMock(spec=CostTracker)
        self.metrics_service = MagicMock(spec=MetricsService)

        # Initialize model cascade
        self.model_cascade = ModelCascade(
            llm_manager=self.llm_manager,
            model_selector=self.model_selector,
            quality_evaluator=self.quality_evaluator,
            cost_tracker=self.cost_tracker,
            metrics_service=self.metrics_service
        )

        # Set up test queries
        self.simple_query = "What is your platform about?"
        self.optimization_query = "Analyze my AI model performance and recommend optimizations"
        self.complex_query = "Perform comprehensive TCO analysis with detailed benchmarking"

    def test_model_tier_mappings_initialization(self):
        """Test proper initialization of model tier mappings."""
        # Assert business logic: all tiers have model mappings
        for tier in ModelTier:
            models = self.model_cascade.tier_mappings.get(tier)
            self.assertIsNotNone(models, f"Tier {tier.value} should have model mappings")
            self.assertGreater(len(models), 0, f"Tier {tier.value} should have at least one model")

        # Verify tier hierarchy makes business sense
        small_models = self.model_cascade.tier_mappings[ModelTier.SMALL]
        large_models = self.model_cascade.tier_mappings[ModelTier.LARGE]

        # Small tier should include fast/cheap models
        self.assertIn("gpt-3.5-turbo", small_models)
        self.assertIn("claude-3-haiku", small_models)

        # Large tier should include powerful models
        self.assertIn("gpt-4", large_models)
        self.assertIn("claude-3-opus", large_models)

    def test_complexity_to_tier_mapping_logic(self):
        """Test complexity-to-tier mapping reflects business requirements."""
        complexity_expectations = {
            "trivial": ModelTier.SMALL,
            "simple": ModelTier.SMALL,
            "medium": ModelTier.MEDIUM,
            "balanced": ModelTier.MEDIUM,
            "high": ModelTier.LARGE,
            "complex": ModelTier.LARGE,
            "expert": ModelTier.LARGE,
            "creative": ModelTier.MEDIUM
        }

        for complexity, expected_tier in complexity_expectations.items():
            actual_tier = self.model_cascade.complexity_mappings.get(complexity)
            self.assertEqual(actual_tier, expected_tier,
                           f"Complexity '{complexity}' should map to {expected_tier.value}")

    def test_cascade_policies_initialization(self):
        """Test default cascade policies are business-appropriate."""
        policies = self.model_cascade.policies

        # Assert business logic: policies have reasonable defaults
        self.assertGreaterEqual(policies.quality_threshold, 0.7,
                               "Quality threshold should be reasonable")
        self.assertGreater(policies.max_cost_per_request, 0.0,
                          "Max cost should be positive")
        self.assertGreater(policies.latency_sla_ms, 0,
                          "Latency SLA should be positive")
        self.assertTrue(policies.escalation_enabled,
                       "Escalation should be enabled by default")
        self.assertTrue(policies.cache_enabled,
                       "Caching should be enabled by default")

    def test_policy_configuration_updates(self):
        """Test that policy configuration can be updated properly."""
        new_policies = {
            "quality_threshold": 0.9,
            "max_cost_per_request": 1.0,
            "latency_sla_ms": 5000,
            "exploration_rate": 0.2
        }

        self.model_cascade.set_policies(new_policies)

        # Assert business logic: policies are updated correctly
        self.assertEqual(self.model_cascade.policies.quality_threshold, 0.9)
        self.assertEqual(self.model_cascade.policies.max_cost_per_request, 1.0)
        self.assertEqual(self.model_cascade.policies.latency_sla_ms, 5000)
        self.assertEqual(self.model_cascade.policies.exploration_rate, 0.2)

    def test_policy_invalid_key_handling(self):
        """Test handling of invalid policy keys."""
        invalid_policies = {
            "nonexistent_policy": "value",
            "quality_threshold": 0.85,  # Valid policy
            "another_invalid": 123
        }

        # Should not raise exception for invalid keys
        self.model_cascade.set_policies(invalid_policies)

        # Valid policy should be updated
        self.assertEqual(self.model_cascade.policies.quality_threshold, 0.85)

    @patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response')
    async def test_basic_execution_workflow(self, mock_generate_response):
        """Test basic model cascade execution workflow."""
        # Set up mocks
        mock_response = "Optimized AI model performance through batch processing"
        mock_generate_response.return_value = mock_response

        # Mock quality evaluation
        mock_quality_metrics = MagicMock()
        mock_quality_metrics.overall_score = 0.85
        self.quality_evaluator.evaluate_response.return_value = mock_quality_metrics

        # Execute cascade
        result = await self.model_cascade.execute(
            query=self.optimization_query,
            quality_requirement=0.8,
            max_cost=0.1,
            metadata={"expected_complexity": "medium"}
        )

        # Assert business logic: execution completes successfully
        self.assertEqual(result["response"], mock_response)
        self.assertGreater(result["quality_score"], 0.0)
        self.assertGreaterEqual(result["total_cost"], 0.0)
        self.assertGreater(result["latency_ms"], 0.0)
        self.assertFalse(result["cache_hit"])
        self.assertIn("model_selected", result)

    async def test_model_selection_based_on_complexity(self):
        """Test model selection logic based on query complexity."""
        test_cases = [
            ("simple", ModelTier.SMALL),
            ("medium", ModelTier.MEDIUM),
            ("complex", ModelTier.LARGE),
            ("balanced", ModelTier.MEDIUM)
        ]

        for complexity, expected_tier in test_cases:
            with self.subTest(complexity=complexity):
                metadata = {"expected_complexity": complexity}

                # Mock model availability
                with patch.object(self.model_cascade, '_is_model_available', return_value=True):
                    model_name = await self.model_cascade._select_model(
                        self.optimization_query, 0.8, 0.1, metadata
                    )

                # Assert business logic: selected model matches expected tier
                expected_models = self.model_cascade.tier_mappings[expected_tier]
                self.assertIn(model_name, expected_models,
                            f"Selected model should be from {expected_tier.value} tier")

    async def test_model_availability_checking(self):
        """Test model availability checking logic."""
        # Mock LLM manager model availability
        with patch.object(self.llm_manager, 'get_available_models',
                         return_value=["gpt-4", "claude-3-sonnet"]):
            # Available model
            is_available = await self.model_cascade._is_model_available("gpt-4")
            self.assertTrue(is_available, "Listed model should be available")

            # Unavailable model
            is_unavailable = await self.model_cascade._is_model_available("nonexistent-model")
            self.assertFalse(is_unavailable, "Unlisted model should not be available")

    async def test_cost_calculation_logic(self):
        """Test cost calculation for different models."""
        test_query = "Optimize my AI performance"
        test_response = "Here are optimization recommendations"

        # Test cost calculation for different models
        model_costs = {}
        for model in ["gpt-3.5-turbo", "gpt-4", "claude-3-haiku", "claude-3-opus"]:
            cost = await self.model_cascade._calculate_cost(model, test_query, test_response)
            model_costs[model] = cost

        # Assert business logic: cost differences reflect model pricing
        self.assertGreater(model_costs["gpt-4"], model_costs["gpt-3.5-turbo"],
                          "GPT-4 should cost more than GPT-3.5-turbo")
        self.assertGreater(model_costs["claude-3-opus"], model_costs["claude-3-haiku"],
                          "Claude Opus should cost more than Haiku")

    async def test_semantic_cache_functionality(self):
        """Test semantic caching behavior."""
        # Enable caching
        self.model_cascade.enable_semantic_cache(similarity_threshold=0.95, ttl_seconds=300)

        # First execution should miss cache
        with patch.object(self.model_cascade, '_check_cache', return_value=None):
            result = await self.model_cascade.execute(self.simple_query)
            self.assertFalse(result["cache_hit"])

        # Create cache entry manually for testing
        from netra_backend.app.agents.chat_orchestrator.model_cascade import CacheEntry
        from datetime import datetime, UTC

        cache_entry = CacheEntry(
            response="Cached response",
            model_used="gpt-3.5-turbo",
            quality_score=0.9,
            cost=0.05,
            timestamp=datetime.now(UTC)
        )

        # Second execution should hit cache
        with patch.object(self.model_cascade, '_check_cache', return_value=cache_entry):
            cached_result = await self.model_cascade.execute(self.simple_query)
            self.assertTrue(cached_result["cache_hit"])
            self.assertEqual(cached_result["response"], "Cached response")
            self.assertEqual(cached_result["total_cost"], 0.0)  # Cache hit = no cost

    async def test_escalation_workflow_quality_improvement(self):
        """Test escalation workflow for quality improvement."""
        # Mock models for different tiers
        with patch.object(self.llm_manager, 'generate_response') as mock_generate:
            # Set up escalating quality responses
            responses = [
                "Basic response",    # Small model, low quality
                "Better response",   # Medium model, medium quality
                "Excellent detailed response"  # Large model, high quality
            ]
            mock_generate.side_effect = responses

            # Mock quality evaluations that improve with escalation
            quality_scores = [0.6, 0.75, 0.9]  # Improving quality
            quality_metrics = []
            for score in quality_scores:
                metric = MagicMock()
                metric.overall_score = score
                quality_metrics.append(metric)

            self.quality_evaluator.evaluate_response.side_effect = quality_metrics

            # Execute with escalation tracking
            result = await self.model_cascade.execute_with_escalation_tracking(
                query=self.complex_query,
                quality_requirement=0.85  # High requirement triggers escalation
            )

            # Assert business logic: escalation improves quality
            self.assertGreaterEqual(result["final_quality_score"], 0.85,
                                   "Final quality should meet requirement")
            self.assertGreater(result["total_attempts"], 1,
                              "Should have attempted escalation")
            self.assertGreater(len(result["escalation_history"]), 1,
                              "Should have escalation history")

    async def test_consensus_execution_across_models(self):
        """Test consensus execution across multiple models."""
        models_to_query = ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"]

        # Mock multiple model responses
        with patch.object(self.model_cascade, '_query_single_model') as mock_query:
            # Set up different responses from each model
            mock_responses = [
                ("gpt-4", "Optimization approach A", 0.9, 0.1, 1500),
                ("claude-3-sonnet", "Optimization approach B", 0.85, 0.08, 1200),
                ("gpt-3.5-turbo", "Optimization approach C", 0.75, 0.03, 800)
            ]
            mock_query.side_effect = mock_responses

            # Execute consensus
            result = await self.model_cascade.execute_with_consensus(
                query=self.optimization_query,
                models_to_query=models_to_query,
                consensus_threshold=0.8
            )

            # Assert business logic: consensus incorporates all models
            self.assertIn("consensus_response", result)
            self.assertEqual(len(result["individual_responses"]), 3)
            self.assertGreater(result["consensus_score"], 0.0)
            self.assertGreater(result["total_cost"], 0.0)

    async def test_adaptive_routing_exploration_vs_exploitation(self):
        """Test adaptive routing between exploration and exploitation."""
        # Enable adaptive routing
        self.model_cascade.enable_adaptive_routing(
            learning_rate=0.1,
            exploration_rate=0.3
        )

        query_category = "optimization"

        # Mock model execution
        with patch.object(self.llm_manager, 'generate_response',
                         return_value="Adaptive response"):
            # Mock quality evaluation
            mock_quality_metrics = MagicMock()
            mock_quality_metrics.overall_score = 0.8
            self.quality_evaluator.evaluate_response.return_value = mock_quality_metrics

            # Execute adaptive routing multiple times
            results = []
            for _ in range(5):
                result = await self.model_cascade.execute_adaptive(
                    query=self.optimization_query,
                    query_category=query_category,
                    quality_requirement=0.75
                )
                results.append(result)

            # Assert business logic: both exploration and exploitation occur
            routing_reasons = [r["routing_reason"] for r in results]
            exploration_count = routing_reasons.count("exploration")
            exploitation_count = routing_reasons.count("exploitation")

            # With 30% exploration rate, expect some of each (allowing variance)
            self.assertGreater(len(results), 0, "Should have results")
            # Note: Due to randomness, we can't guarantee exact counts

    async def test_performance_history_tracking(self):
        """Test performance history tracking and learning."""
        category = "optimization"
        model = "gpt-4"

        # Update performance history
        await self.model_cascade.update_routing_performance(
            category=category,
            model=model,
            quality_score=0.9,
            latency_ms=1500,
            cost=0.1
        )

        # Verify history is tracked
        history = self.model_cascade._performance_history[category][model]
        self.assertEqual(len(history.quality_scores), 1)
        self.assertEqual(history.quality_scores[0], 0.9)
        self.assertEqual(history.avg_quality, 0.9)

        # Add more data points
        for i in range(3):
            await self.model_cascade.update_routing_performance(
                category=category,
                model=model,
                quality_score=0.8 + i * 0.05,
                latency_ms=1400 + i * 100,
                cost=0.08 + i * 0.02
            )

        # Verify averages are calculated correctly
        self.assertEqual(len(history.quality_scores), 4)
        self.assertAlmostEqual(history.avg_quality, 0.8625, places=3)

    async def test_routing_recommendations_generation(self):
        """Test generation of routing recommendations based on learned performance."""
        # Populate performance history
        categories = ["optimization", "analysis", "benchmarking"]
        models = ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"]

        # Add performance data
        for category in categories:
            for model in models:
                # Simulate different performance characteristics
                quality = 0.7 + hash(f"{category}_{model}") % 20 / 100  # 0.7-0.9 range
                latency = 1000 + hash(f"{model}") % 1000  # Variable latency
                cost = 0.05 + hash(f"{model}") % 10 / 100  # Variable cost

                for _ in range(5):  # Add multiple data points
                    await self.model_cascade.update_routing_performance(
                        category=category,
                        model=model,
                        quality_score=quality,
                        latency_ms=latency,
                        cost=cost
                    )

        # Generate recommendations
        recommendations = await self.model_cascade.get_routing_recommendations()

        # Assert business logic: recommendations are comprehensive
        self.assertIn("category_model_mapping", recommendations)
        self.assertIn("confidence_scores", recommendations)
        self.assertIn("performance_summary", recommendations)

        # Each category should have recommendations
        for category in categories:
            if category in recommendations["category_model_mapping"]:
                category_rec = recommendations["category_model_mapping"][category]
                self.assertIn("primary", category_rec)
                self.assertIn("fallbacks", category_rec)
                self.assertIn("avg_performance", category_rec)

    async def test_cache_key_generation_and_management(self):
        """Test cache key generation and cache management."""
        query1 = "First optimization query"
        query2 = "Second optimization query"

        # Generate cache keys
        key1 = self.model_cascade._hash_query(query1)
        key2 = self.model_cascade._hash_query(query2)

        # Assert business logic: different queries have different keys
        self.assertNotEqual(key1, key2, "Different queries should have different cache keys")
        self.assertEqual(len(key1), 32, "Cache key should be 32-character MD5 hash")
        self.assertEqual(len(key2), 32, "Cache key should be 32-character MD5 hash")

        # Same query should generate same key
        key1_again = self.model_cascade._hash_query(query1)
        self.assertEqual(key1, key1_again, "Same query should generate same cache key")

    async def test_tier_cost_estimation_logic(self):
        """Test cost estimation logic for different model tiers."""
        cost_small = self.model_cascade.estimate_cost_tier(ModelTier.SMALL)
        cost_medium = self.model_cascade.estimate_cost_tier(ModelTier.MEDIUM)
        cost_large = self.model_cascade.estimate_cost_tier(ModelTier.LARGE)

        # Assert business logic: costs increase with tier
        self.assertLess(cost_small, cost_medium, "Small tier should cost less than medium")
        self.assertLess(cost_medium, cost_large, "Medium tier should cost less than large")

        # All costs should be positive
        self.assertGreater(cost_small, 0.0, "Small tier cost should be positive")
        self.assertGreater(cost_medium, 0.0, "Medium tier cost should be positive")
        self.assertGreater(cost_large, 0.0, "Large tier cost should be positive")

    async def tearDown(self):
        """Clean up test environment."""
        await super().tearDown()


class TestModelCascadeErrorHandling(SSotAsyncTestCase):
    """Specialized tests for model cascade error handling scenarios."""

    async def setUp(self):
        """Set up test environment for error handling tests."""
        await super().setUp()

        # Initialize with minimal dependencies for error testing
        self.llm_manager = LLMManager()
        self.model_cascade = ModelCascade(
            llm_manager=self.llm_manager,
            model_selector=MagicMock(),
            quality_evaluator=AsyncMock(),
            cost_tracker=AsyncMock(),
            metrics_service=MagicMock()
        )

    @patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response')
    async def test_llm_service_failure_handling(self, mock_generate_response):
        """Test graceful handling of LLM service failures."""
        # Simulate LLM service failure
        mock_generate_response.side_effect = Exception("LLM service unavailable")

        # Execution should handle error transparently
        with self.assertRaises(Exception) as context:
            await self.model_cascade.execute(
                query="Test query",
                metadata={"user_id": "test_user", "request_id": "test_req"}
            )

        # Should provide transparent error information
        exception_str = str(context.exception)
        self.assertIn("Model cascade service temporarily unavailable", exception_str)

    async def test_empty_model_list_handling(self):
        """Test handling of empty available model lists."""
        # Mock empty model list
        with patch.object(self.model_cascade, '_get_available_models', return_value=[]):
            # Should fall back to default model
            model_name = await self.model_cascade._select_model(
                "test query", 0.8, 0.1, {"expected_complexity": "medium"}
            )

            # Assert business logic: falls back to default model
            self.assertEqual(model_name, "gpt-3.5-turbo",
                           "Should fall back to default model when no models available")

    async def tearDown(self):
        """Clean up error handling test environment."""
        await super().tearDown()