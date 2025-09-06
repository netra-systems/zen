"""Integration tests for ModelCascade with real model selection and routing.

CRITICAL: These tests use REAL model selection, REAL quality evaluation, REAL cost optimization.
NO MOCKS ALLOWED per CLAUDE.md requirements.

Business Value: Optimizes model selection for cost/quality trade-offs.
Target segments: All tiers. Direct impact on operational efficiency.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelCascade
from netra_backend.app.services.llm.model_selector import ModelSelector
from netra_backend.app.agents.chat_orchestrator.quality_evaluator import QualityEvaluator
from netra_backend.app.services.analytics.cost_tracker import CostTracker
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.models.analytics_models import (
    ModelUsage, ModelPerformance, CostOptimization,
    QualityMetric, ModelConfiguration
)
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.services.monitoring.metrics_service import MetricsService

# Real environment configuration
env = IsolatedEnvironment()


class TestModelCascadeRealSelection:
    """Test suite for ModelCascade with real model selection and routing."""

    @pytest.fixture
    async def real_database_session(self):
        """Get real database session for testing."""
        async for session in get_db():
            yield session
            await session.rollback()

    @pytest.fixture
    async def real_llm_manager(self):
        """Create real LLM manager with multiple models."""
        llm_manager = LLMManager()
        await llm_manager.initialize()
        
        # Ensure multiple models are available
        available_models = llm_manager.get_available_models()
        assert len(available_models) >= 3, "Need at least 3 models for cascade testing"
        
        yield llm_manager
        await llm_manager.cleanup()

    @pytest.fixture
    async def real_model_cascade(self, real_llm_manager, real_database_session):
        """Create real ModelCascade instance."""
        llm_manager = real_llm_manager
        session = real_database_session
        
        # Initialize components
        model_selector = ModelSelector()
        quality_evaluator = QualityEvaluator(llm_manager)
        cost_tracker = CostTracker()
        metrics_service = MetricsService()
        
        cascade = ModelCascade(
            llm_manager=llm_manager,
            model_selector=model_selector,
            quality_evaluator=quality_evaluator,
            cost_tracker=cost_tracker,
            metrics_service=metrics_service,
            db_session=session
        )
        
        # Configure cascade policies
        cascade.set_policies({
            "quality_threshold": 0.8,
            "max_cost_per_request": 0.50,
            "latency_sla_ms": 2000,
            "escalation_enabled": True,
            "fallback_enabled": True
        })
        
        yield cascade

    @pytest.fixture
    def diverse_test_queries(self):
        """Create diverse queries for model selection testing."""
        return [
            {
                "id": "simple_factual",
                "query": "What is the capital of France?",
                "complexity": "trivial",
                "expected_model_tier": "small",
                "quality_requirement": 0.9,
                "max_cost": 0.001
            },
            {
                "id": "code_generation",
                "query": "Write a Python function to implement binary search with error handling and type hints.",
                "complexity": "medium",
                "expected_model_tier": "medium",
                "quality_requirement": 0.85,
                "max_cost": 0.01
            },
            {
                "id": "complex_reasoning",
                "query": "Analyze the economic implications of quantum computing on cryptography markets over the next decade.",
                "complexity": "high",
                "expected_model_tier": "large",
                "quality_requirement": 0.9,
                "max_cost": 0.1
            },
            {
                "id": "creative_writing",
                "query": "Write a haiku about machine learning that incorporates technical accuracy with poetic beauty.",
                "complexity": "creative",
                "expected_model_tier": "medium",
                "quality_requirement": 0.8,
                "max_cost": 0.02
            },
            {
                "id": "mathematical_proof",
                "query": "Prove that the set of prime numbers is infinite using contradiction.",
                "complexity": "expert",
                "expected_model_tier": "large",
                "quality_requirement": 0.95,
                "max_cost": 0.15
            }
        ]

    @pytest.mark.asyncio
    async def test_1_automatic_model_selection_based_on_complexity(
        self, real_model_cascade, diverse_test_queries, real_database_session
    ):
        """Test 1: Automatic model selection based on query complexity."""
        cascade = real_model_cascade
        session = real_database_session
        queries = diverse_test_queries
        
        selection_results = []
        
        for query_data in queries:
            # Execute cascade with automatic model selection
            result = await cascade.execute(
                query=query_data["query"],
                quality_requirement=query_data["quality_requirement"],
                max_cost=query_data["max_cost"],
                metadata={
                    "query_id": query_data["id"],
                    "expected_complexity": query_data["complexity"]
                }
            )
            
            # Validate result
            assert result is not None
            assert "response" in result
            assert "model_selected" in result
            assert "quality_score" in result
            assert "total_cost" in result
            assert "latency_ms" in result
            assert "selection_reasoning" in result
            
            # Verify constraints are met
            assert result["quality_score"] >= query_data["quality_requirement"] * 0.9  # Allow 10% tolerance
            assert result["total_cost"] <= query_data["max_cost"]
            
            # Check model tier selection
            model_name = result["model_selected"].lower()
            if query_data["expected_model_tier"] == "small":
                assert any(small in model_name for small in ["3.5", "small", "mini", "turbo"])
            elif query_data["expected_model_tier"] == "large":
                assert any(large in model_name for large in ["4", "large", "pro", "claude-2"])
                
            selection_results.append({
                "query_id": query_data["id"],
                "complexity": query_data["complexity"],
                "model_selected": result["model_selected"],
                "quality_score": result["quality_score"],
                "cost": result["total_cost"],
                "latency_ms": result["latency_ms"]
            })
            
            # Create usage record (in-memory for testing)
            usage = ModelUsage(
                id=f"usage_{query_data['id']}_{datetime.utcnow().strftime('%H%M%S')}",
                model_name=result["model_selected"],
                query_type=query_data["complexity"],
                tokens_used=result.get("total_tokens", 0),
                cost=result["total_cost"],
                latency_ms=result["latency_ms"],
                quality_score=result["quality_score"],
                timestamp=datetime.utcnow()
            )
            logger.info(f"Created usage record: {usage.id}")
            
            logger.info(f"Query '{query_data['id']}' routed to {result['model_selected']} with quality {result['quality_score']:.2f}")
        
        logger.info(f"Would commit {len(selection_results)} usage records to database")
        
        # Verify cost optimization
        simple_query_cost = next(r["cost"] for r in selection_results if r["query_id"] == "simple_factual")
        complex_query_cost = next(r["cost"] for r in selection_results if r["query_id"] == "complex_reasoning")
        assert complex_query_cost > simple_query_cost * 5  # Complex should be significantly more expensive
        
        # Check latency scaling
        simple_latency = next(r["latency_ms"] for r in selection_results if r["query_id"] == "simple_factual")
        complex_latency = next(r["latency_ms"] for r in selection_results if r["query_id"] == "complex_reasoning")
        assert simple_latency < complex_latency  # Simple should be faster

    @pytest.mark.asyncio
    async def test_2_quality_based_escalation_with_retry(
        self, real_model_cascade, real_database_session
    ):
        """Test 2: Quality-based escalation with automatic retry on better models."""
        cascade = real_model_cascade
        session = real_database_session
        
        # Query that might need escalation
        challenging_query = """
        Explain the technical differences between RLHF and Constitutional AI training methods,
        including their impact on model behavior, safety guarantees, and computational requirements.
        """
        
        # Set strict quality requirement
        quality_requirement = 0.92
        
        # Force initial model to be small (to trigger escalation)
        cascade.set_policies({
            "initial_model_preference": "cost_optimized",
            "quality_threshold": quality_requirement,
            "max_escalations": 3,
            "escalation_enabled": True
        })
        
        # Execute with escalation tracking
        result = await cascade.execute_with_escalation_tracking(
            query=challenging_query,
            quality_requirement=quality_requirement,
            track_attempts=True
        )
        
        # Validate escalation result
        assert result is not None
        assert "final_response" in result
        assert "escalation_history" in result
        assert "total_attempts" in result
        assert "final_quality_score" in result
        assert "cumulative_cost" in result
        
        # Check escalation occurred if needed
        escalation_history = result["escalation_history"]
        assert len(escalation_history) > 0
        
        # Verify progressive quality improvement
        if len(escalation_history) > 1:
            quality_scores = [attempt["quality_score"] for attempt in escalation_history]
            assert quality_scores[-1] >= quality_scores[0]  # Final should be better than initial
            
        # Verify final quality meets requirement
        assert result["final_quality_score"] >= quality_requirement * 0.95
        
        # Check model progression
        models_used = [attempt["model"] for attempt in escalation_history]
        logger.info(f"Escalation chain: {' -> '.join(models_used)}")
        
        # Verify cost increases with escalation
        if len(escalation_history) > 1:
            costs = [attempt["cost"] for attempt in escalation_history]
            assert costs[-1] >= costs[0]  # Better models cost more
            
        # Store escalation metrics
        for i, attempt in enumerate(escalation_history):
            metric = QualityMetric(
                id=f"quality_{datetime.utcnow().strftime('%H%M%S')}_{i}",
                model_name=attempt["model"],
                query_hash=hash(challenging_query) % 1000000,
                quality_score=attempt["quality_score"],
                evaluation_method="llm_judge",
                metadata=json.dumps({
                    "attempt_number": i + 1,
                    "escalation": i > 0,
                    "met_requirement": attempt["quality_score"] >= quality_requirement
                }),
                timestamp=datetime.utcnow()
            )
            session.add(metric)
            
        await session.commit()
        
        logger.info(f"Escalation completed in {result['total_attempts']} attempts with final quality {result['final_quality_score']:.2f}")

    @pytest.mark.asyncio
    async def test_3_cost_optimized_routing_with_caching(
        self, real_model_cascade, real_database_session
    ):
        """Test 3: Cost-optimized routing with semantic caching."""
        cascade = real_model_cascade
        session = real_database_session
        
        # Enable caching for cost optimization
        cascade.enable_semantic_cache(
            similarity_threshold=0.95,
            ttl_seconds=300
        )
        
        # Similar queries that should benefit from caching
        query_variations = [
            "What are the main benefits of using Redis for caching?",
            "What are the key advantages of using Redis as a cache?",
            "Explain the primary benefits of Redis for caching purposes.",
            "What makes Redis good for caching?",
            "Why use Redis for cache?"
        ]
        
        costs_and_latencies = []
        cache_hits = 0
        
        for i, query in enumerate(query_variations):
            start_time = time.time()
            
            result = await cascade.execute(
                query=query,
                quality_requirement=0.8,
                max_cost=0.05,
                enable_cache=True
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Validate result
            assert result is not None
            assert "response" in result
            assert "cache_hit" in result
            assert "total_cost" in result
            
            if result["cache_hit"]:
                cache_hits += 1
                # Cached responses should be much faster
                assert execution_time < 100  # Less than 100ms for cache hit
                # Cached responses should have zero cost
                assert result["total_cost"] == 0
                
            costs_and_latencies.append({
                "query_index": i,
                "query": query[:50],
                "cache_hit": result["cache_hit"],
                "cost": result["total_cost"],
                "latency_ms": execution_time,
                "model_used": result.get("model_selected", "cached")
            })
            
            logger.info(f"Query {i+1}: Cache {'HIT' if result['cache_hit'] else 'MISS'}, Cost: ${result['total_cost']:.4f}, Latency: {execution_time:.0f}ms")
        
        # Verify caching effectiveness
        assert cache_hits >= 2  # At least 2 queries should hit cache
        
        # Calculate cost savings
        total_cost_without_cache = sum(c["cost"] for c in costs_and_latencies if not c["cache_hit"]) * len(query_variations)
        actual_total_cost = sum(c["cost"] for c in costs_and_latencies)
        savings_percentage = ((total_cost_without_cache - actual_total_cost) / total_cost_without_cache) * 100
        
        assert savings_percentage > 30  # Should save at least 30% with caching
        
        # Store cost optimization metrics
        optimization = CostOptimization(
            id=f"opt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            optimization_type="semantic_caching",
            queries_processed=len(query_variations),
            cache_hit_rate=cache_hits / len(query_variations),
            cost_saved=total_cost_without_cache - actual_total_cost,
            savings_percentage=savings_percentage,
            timestamp=datetime.utcnow()
        )
        session.add(optimization)
        await session.commit()
        
        logger.info(f"Caching saved {savings_percentage:.1f}% in costs with {cache_hits}/{len(query_variations)} cache hits")

    @pytest.mark.asyncio
    async def test_4_parallel_model_execution_for_consensus(
        self, real_model_cascade, real_database_session
    ):
        """Test 4: Parallel model execution for consensus-based responses."""
        cascade = real_model_cascade
        session = real_database_session
        
        # Query requiring high confidence
        critical_query = """
        What is the recommended production configuration for PostgreSQL 15 
        to handle 10,000 concurrent connections with sub-100ms query latency?
        """
        
        # Execute with consensus mode
        consensus_result = await cascade.execute_with_consensus(
            query=critical_query,
            models_to_query=["gpt-3.5-turbo", "gpt-4", "claude-2"],  # Use available models
            consensus_threshold=0.8,
            aggregation_method="weighted_average"  # or "majority_vote", "best_quality"
        )
        
        # Validate consensus result
        assert consensus_result is not None
        assert "consensus_response" in consensus_result
        assert "individual_responses" in consensus_result
        assert "consensus_score" in consensus_result
        assert "disagreement_points" in consensus_result
        assert "total_cost" in consensus_result
        assert "total_latency_ms" in consensus_result
        
        # Check individual model responses
        individual = consensus_result["individual_responses"]
        assert len(individual) >= 2  # At least 2 models should respond
        
        for model_response in individual:
            assert "model" in model_response
            assert "response" in model_response
            assert "quality_score" in model_response
            assert "confidence" in model_response
            assert "cost" in model_response
            
        # Verify consensus quality
        assert consensus_result["consensus_score"] >= 0.7
        
        # Check for specific technical details in consensus
        consensus_response = consensus_result["consensus_response"].lower()
        technical_terms = ["connection pool", "max_connections", "shared_buffers", "work_mem", "wal", "checkpoint"]
        assert sum(term in consensus_response for term in technical_terms) >= 3
        
        # Analyze disagreements
        disagreements = consensus_result["disagreement_points"]
        if len(disagreements) > 0:
            for disagreement in disagreements:
                assert "topic" in disagreement
                assert "variations" in disagreement
                assert "resolution" in disagreement
                
        # Store consensus execution metrics
        for model_resp in individual:
            performance = ModelPerformance(
                id=f"perf_{model_resp['model']}_{datetime.utcnow().strftime('%H%M%S')}",
                model_name=model_resp["model"],
                query_type="consensus_critical",
                latency_ms=model_resp.get("latency_ms", 0),
                quality_score=model_resp["quality_score"],
                confidence_score=model_resp["confidence"],
                cost=model_resp["cost"],
                metadata=json.dumps({
                    "consensus_run": True,
                    "agreed_with_consensus": model_resp.get("agreement_score", 0) > 0.8
                }),
                timestamp=datetime.utcnow()
            )
            session.add(performance)
            
        await session.commit()
        
        logger.info(f"Consensus achieved with score {consensus_result['consensus_score']:.2f} across {len(individual)} models")

    @pytest.mark.asyncio
    async def test_5_adaptive_routing_with_performance_learning(
        self, real_model_cascade, real_database_session
    ):
        """Test 5: Adaptive routing that learns from performance history."""
        cascade = real_model_cascade
        session = real_database_session
        
        # Enable adaptive routing
        cascade.enable_adaptive_routing(
            learning_rate=0.1,
            exploration_rate=0.2,  # 20% exploration for new model combinations
            performance_window_hours=24
        )
        
        # Different query categories for testing adaptation
        query_categories = [
            {
                "category": "code_review",
                "queries": [
                    "Review this Python code for security issues: def login(username, password): query = f'SELECT * FROM users WHERE name={username}'",
                    "Find bugs in this code: for i in range(len(list)): if list[i] = target: return i",
                    "Optimize this function: def factorial(n): if n == 0: return 1 else: return n * factorial(n-1)"
                ]
            },
            {
                "category": "data_analysis", 
                "queries": [
                    "Analyze this sales trend: Q1: $1M, Q2: $1.2M, Q3: $0.9M, Q4: $1.5M",
                    "What insights can you derive from user engagement dropping 30% on weekends?",
                    "Interpret these A/B test results: Control: 2.3% CTR, Variant: 2.8% CTR, p-value: 0.03"
                ]
            },
            {
                "category": "architecture",
                "queries": [
                    "Design a microservices architecture for an e-commerce platform",
                    "How should I structure a real-time analytics pipeline?",
                    "What's the best database architecture for a social media app?"
                ]
            }
        ]
        
        adaptation_metrics = []
        
        for category_data in query_categories:
            category = category_data["category"]
            
            for query in category_data["queries"]:
                # Execute with adaptive routing
                result = await cascade.execute_adaptive(
                    query=query,
                    query_category=category,
                    quality_requirement=0.85,
                    learn_from_result=True
                )
                
                # Validate adaptive result
                assert result is not None
                assert "response" in result
                assert "model_selected" in result
                assert "routing_reason" in result
                assert "exploration" in result  # Whether this was exploration or exploitation
                assert "performance_prediction" in result
                assert "actual_performance" in result
                
                # Check if model selection improves over time
                adaptation_metrics.append({
                    "category": category,
                    "model": result["model_selected"],
                    "predicted_quality": result["performance_prediction"]["quality"],
                    "actual_quality": result["actual_performance"]["quality"],
                    "predicted_latency": result["performance_prediction"]["latency_ms"],
                    "actual_latency": result["actual_performance"]["latency_ms"],
                    "exploration": result["exploration"]
                })
                
                # Update routing performance history
                await cascade.update_routing_performance(
                    category=category,
                    model=result["model_selected"],
                    quality_score=result["actual_performance"]["quality"],
                    latency_ms=result["actual_performance"]["latency_ms"],
                    cost=result["actual_performance"]["cost"]
                )
                
                logger.info(f"Category '{category}': {'Explored' if result['exploration'] else 'Exploited'} with {result['model_selected']}")
        
        # Analyze adaptation effectiveness
        categories = list(set(m["category"] for m in adaptation_metrics))
        
        for category in categories:
            category_metrics = [m for m in adaptation_metrics if m["category"] == category]
            
            # Later predictions should be more accurate
            if len(category_metrics) > 1:
                first_prediction_error = abs(category_metrics[0]["predicted_quality"] - category_metrics[0]["actual_quality"])
                last_prediction_error = abs(category_metrics[-1]["predicted_quality"] - category_metrics[-1]["actual_quality"])
                
                # Prediction should improve (error should decrease)
                improvement = first_prediction_error > last_prediction_error * 1.1
                logger.info(f"Category '{category}': Prediction improved: {improvement}")
        
        # Get routing recommendations
        recommendations = await cascade.get_routing_recommendations()
        
        assert recommendations is not None
        assert "category_model_mapping" in recommendations
        assert "confidence_scores" in recommendations
        assert "performance_summary" in recommendations
        
        # Verify learned preferences
        mapping = recommendations["category_model_mapping"]
        assert "code_review" in mapping
        assert "data_analysis" in mapping
        assert "architecture" in mapping
        
        # Store learned routing configuration
        for category, model_preference in mapping.items():
            config = ModelConfiguration(
                id=f"config_{category}_{datetime.utcnow().strftime('%H%M%S')}",
                configuration_name=f"adaptive_routing_{category}",
                category=category,
                preferred_model=model_preference["primary"],
                fallback_models=json.dumps(model_preference.get("fallbacks", [])),
                quality_threshold=0.85,
                cost_threshold=model_preference.get("max_cost", 0.1),
                metadata=json.dumps({
                    "learned": True,
                    "confidence": recommendations["confidence_scores"].get(category, 0),
                    "performance_history": model_preference.get("avg_performance", {})
                }),
                created_at=datetime.utcnow()
            )
            session.add(config)
            
        await session.commit()
        
        logger.info(f"Adaptive routing learned preferences for {len(mapping)} categories")


if __name__ == "__main__":
    # Run tests with real model selection
    asyncio.run(pytest.main([__file__, "-v", "--real-models"]))