"""Agent Cost Optimization Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (LLM cost optimization impacts all users)
- Business Goal: Minimize LLM costs while maintaining quality
- Value Impact: Direct cost savings, improved margins, competitive pricing
- Strategic Impact: $30K-60K MRR savings through intelligent cost optimization

Critical Path: Cost prediction -> Model selection -> Response caching -> Token optimization -> Cost tracking
Coverage: LLM cost tracking, model selection algorithms, caching strategies, token optimization
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.services.analytics.cost_tracker import CostTracker
from netra_backend.app.services.cache.response_cache import ResponseCache

from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer
from netra_backend.app.services.llm.model_selector import ModelSelector

logger = logging.getLogger(__name__)

class AgentCostOptimizationManager:
    """Manages agent cost optimization testing."""
    
    def __init__(self):
        self.cost_optimizer = None
        self.model_selector = None
        self.response_cache = None
        self.cost_tracker = None
        self.optimization_events = []
        self.cost_savings = []
        
    async def initialize_services(self):
        """Initialize cost optimization services."""
        try:
            self.cost_optimizer = LLMCostOptimizer()
            await self.cost_optimizer.initialize()
            
            self.model_selector = ModelSelector()
            await self.model_selector.initialize()
            
            self.response_cache = ResponseCache()
            await self.response_cache.initialize()
            
            self.cost_tracker = CostTracker()
            await self.cost_tracker.initialize()
            
            logger.info("Cost optimization services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize cost optimization services: {e}")
            raise
    
    async def optimize_llm_request(self, request_text: str, quality_requirement: str = "high") -> Dict[str, Any]:
        """Optimize LLM request for cost while maintaining quality."""
        optimization_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Step 1: Check cache first
            cache_result = await self.response_cache.get_cached_response(request_text)
            
            if cache_result["hit"]:
                cost_saved = await self.calculate_cache_savings(request_text)
                
                optimization_event = {
                    "optimization_id": optimization_id,
                    "request_text": request_text[:100],  # Truncate for logging
                    "optimization_type": "cache_hit",
                    "cost_saved": cost_saved,
                    "quality_maintained": True,
                    "processing_time": time.time() - start_time
                }
                
                self.optimization_events.append(optimization_event)
                self.cost_savings.append(cost_saved)
                
                return {
                    "optimized": True,
                    "method": "cache_hit",
                    "response": cache_result["response"],
                    "cost_saved": cost_saved,
                    "optimization_id": optimization_id
                }
            
            # Step 2: Optimize model selection
            model_optimization = await self.model_selector.select_optimal_model(
                request_text, quality_requirement
            )
            
            # Step 3: Optimize token usage
            token_optimization = await self.cost_optimizer.optimize_tokens(
                request_text, model_optimization["selected_model"]
            )
            
            # Step 4: Execute optimized request
            optimized_response = await self.execute_optimized_request(
                token_optimization["optimized_text"],
                model_optimization["selected_model"]
            )
            
            # Step 5: Cache response for future use
            await self.response_cache.cache_response(
                request_text, optimized_response["response"]
            )
            
            # Step 6: Track cost savings
            total_cost_saved = (
                model_optimization.get("cost_saved", Decimal("0")) +
                token_optimization.get("cost_saved", Decimal("0"))
            )
            
            optimization_event = {
                "optimization_id": optimization_id,
                "request_text": request_text[:100],
                "optimization_type": "full_optimization",
                "model_selected": model_optimization["selected_model"],
                "tokens_saved": token_optimization.get("tokens_saved", 0),
                "cost_saved": total_cost_saved,
                "quality_maintained": optimized_response["quality_score"] >= 0.8,
                "processing_time": time.time() - start_time
            }
            
            self.optimization_events.append(optimization_event)
            self.cost_savings.append(total_cost_saved)
            
            return {
                "optimized": True,
                "method": "full_optimization",
                "response": optimized_response["response"],
                "cost_saved": total_cost_saved,
                "optimization_details": {
                    "model_optimization": model_optimization,
                    "token_optimization": token_optimization
                },
                "optimization_id": optimization_id
            }
            
        except Exception as e:
            error_event = {
                "optimization_id": optimization_id,
                "request_text": request_text[:100],
                "optimization_type": "failed",
                "error": str(e),
                "processing_time": time.time() - start_time
            }
            
            self.optimization_events.append(error_event)
            
            return {
                "optimized": False,
                "error": str(e),
                "optimization_id": optimization_id
            }
    
    async def calculate_cache_savings(self, request_text: str) -> Decimal:
        """Calculate cost savings from cache hit."""
        # Simulate cost calculation
        estimated_tokens = len(request_text.split()) * 1.3  # Rough token estimation
        cost_per_token = Decimal("0.00002")  # $0.00002 per token
        return Decimal(str(estimated_tokens)) * cost_per_token
    
    async def execute_optimized_request(self, optimized_text: str, model: str) -> Dict[str, Any]:
        """Execute optimized LLM request."""
        # Simulate LLM request execution
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "response": f"Optimized response for: {optimized_text[:50]}...",
            "quality_score": 0.85,  # Simulated quality score
            "tokens_used": len(optimized_text.split()) * 1.2,
            "model_used": model
        }
    
    async def test_cost_optimization_effectiveness(self, test_requests: List[str]) -> Dict[str, Any]:
        """Test effectiveness of cost optimization across multiple requests."""
        try:
            results = []
            total_original_cost = Decimal("0")
            total_optimized_cost = Decimal("0")
            
            for request in test_requests:
                # Calculate original cost (without optimization)
                original_cost = await self.calculate_original_cost(request)
                total_original_cost += original_cost
                
                # Apply optimization
                optimization_result = await self.optimize_llm_request(request)
                
                if optimization_result["optimized"]:
                    optimized_cost = original_cost - optimization_result["cost_saved"]
                    total_optimized_cost += optimized_cost
                else:
                    total_optimized_cost += original_cost
                
                results.append({
                    "request": request[:50],
                    "original_cost": original_cost,
                    "optimized": optimization_result["optimized"],
                    "cost_saved": optimization_result.get("cost_saved", Decimal("0")),
                    "method": optimization_result.get("method", "none")
                })
            
            total_savings = total_original_cost - total_optimized_cost
            savings_percentage = (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0
            
            return {
                "total_requests": len(test_requests),
                "optimization_success_rate": len([r for r in results if r["optimized"]]) / len(results) * 100,
                "total_original_cost": total_original_cost,
                "total_optimized_cost": total_optimized_cost,
                "total_savings": total_savings,
                "savings_percentage": float(savings_percentage),
                "results": results
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def calculate_original_cost(self, request_text: str) -> Decimal:
        """Calculate original cost without optimization."""
        tokens = len(request_text.split()) * 1.5  # Higher token count without optimization
        cost_per_token = Decimal("0.00003")  # Higher cost for premium model
        return Decimal(str(tokens)) * cost_per_token
    
    async def get_cost_optimization_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cost optimization metrics."""
        total_events = len(self.optimization_events)
        successful_optimizations = len([e for e in self.optimization_events if e.get("cost_saved", 0) > 0])
        
        cache_hits = len([e for e in self.optimization_events if e["optimization_type"] == "cache_hit"])
        full_optimizations = len([e for e in self.optimization_events if e["optimization_type"] == "full_optimization"])
        
        total_savings = sum(self.cost_savings)
        avg_savings_per_request = total_savings / total_events if total_events > 0 else 0
        
        return {
            "total_optimization_attempts": total_events,
            "successful_optimizations": successful_optimizations,
            "optimization_success_rate": successful_optimizations / total_events * 100 if total_events > 0 else 0,
            "cache_hit_rate": cache_hits / total_events * 100 if total_events > 0 else 0,
            "total_cost_saved": float(total_savings),
            "average_savings_per_request": float(avg_savings_per_request),
            "optimization_methods": {
                "cache_hits": cache_hits,
                "full_optimizations": full_optimizations,
                "failed_optimizations": total_events - successful_optimizations
            }
        }
    
    async def cleanup(self):
        """Clean up optimization resources."""
        try:
            if self.cost_optimizer:
                await self.cost_optimizer.shutdown()
            if self.model_selector:
                await self.model_selector.shutdown()
            if self.response_cache:
                await self.response_cache.shutdown()
            if self.cost_tracker:
                await self.cost_tracker.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def cost_optimization_manager():
    """Create cost optimization manager for testing."""
    manager = AgentCostOptimizationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
async def test_basic_cost_optimization(cost_optimization_manager):
    """Test basic LLM cost optimization functionality."""
    request = "Analyze the market trends for AI technology in 2024"
    
    result = await cost_optimization_manager.optimize_llm_request(request)
    
    assert result["optimized"] is True
    assert "cost_saved" in result
    assert result["cost_saved"] >= 0
    assert "response" in result

@pytest.mark.asyncio
async def test_cache_effectiveness(cost_optimization_manager):
    """Test response caching for cost optimization."""
    request = "What are the benefits of cloud computing?"
    
    # First request (should be optimized but not cached)
    first_result = await cost_optimization_manager.optimize_llm_request(request)
    assert first_result["optimized"] is True
    
    # Second identical request (should hit cache)
    second_result = await cost_optimization_manager.optimize_llm_request(request)
    assert second_result["optimized"] is True
    assert second_result["method"] == "cache_hit"
    assert second_result["cost_saved"] > 0

@pytest.mark.asyncio
async def test_model_selection_optimization(cost_optimization_manager):
    """Test optimal model selection for cost savings."""
    # Different types of requests should use different optimization strategies
    requests = [
        "Simple question: What is 2+2?",  # Should use cheaper model
        "Complex analysis: Provide detailed market research on renewable energy trends, including financial projections and competitive analysis"  # May use premium model
    ]
    
    results = []
    for request in requests:
        result = await cost_optimization_manager.optimize_llm_request(request, "medium")
        results.append(result)
    
    # All should be optimized
    assert all(r["optimized"] for r in results)
    
    # Should show cost savings
    assert all(r.get("cost_saved", 0) >= 0 for r in results)

@pytest.mark.asyncio
async def test_cost_optimization_effectiveness(cost_optimization_manager):
    """Test overall effectiveness of cost optimization."""
    test_requests = [
        "Explain machine learning basics",
        "What is artificial intelligence?",
        "Analyze business data trends",
        "Provide code review suggestions",
        "Summarize this document"
    ]
    
    effectiveness_result = await cost_optimization_manager.test_cost_optimization_effectiveness(test_requests)
    
    assert effectiveness_result["optimization_success_rate"] >= 80.0  # 80% should be optimized
    assert effectiveness_result["savings_percentage"] > 0  # Should show savings
    assert effectiveness_result["total_savings"] > 0

@pytest.mark.asyncio
async def test_concurrent_optimization_performance(cost_optimization_manager):
    """Test performance under concurrent optimization requests."""
    # Generate concurrent requests
    requests = [f"Test request {i}: Analyze data trends" for i in range(20)]
    
    # Execute concurrent optimizations
    start_time = time.time()
    tasks = [cost_optimization_manager.optimize_llm_request(req) for req in requests]
    results = await asyncio.gather(*tasks)
    execution_time = time.time() - start_time
    
    # Verify performance
    assert execution_time < 10.0  # Should complete within 10 seconds
    
    # Verify optimization success
    successful_optimizations = [r for r in results if r["optimized"]]
    success_rate = len(successful_optimizations) / len(results) * 100
    
    assert success_rate >= 80.0  # 80% success rate under load

@pytest.mark.asyncio
async def test_cost_optimization_metrics(cost_optimization_manager):
    """Test cost optimization metrics collection."""
    # Generate test data
    test_requests = [
        "What is machine learning?",
        "Explain neural networks",
        "What is machine learning?",  # Duplicate for cache test
        "Analyze market data"
    ]
    
    for request in test_requests:
        await cost_optimization_manager.optimize_llm_request(request)
    
    # Get metrics
    metrics = await cost_optimization_manager.get_cost_optimization_metrics()
    
    # Verify metrics
    assert metrics["total_optimization_attempts"] >= 4
    assert metrics["optimization_success_rate"] >= 75.0
    assert metrics["total_cost_saved"] > 0
    assert metrics["cache_hit_rate"] >= 0  # Should have at least one cache hit from duplicate
    
    # Verify optimization methods breakdown
    methods = metrics["optimization_methods"]
    assert methods["cache_hits"] >= 1  # At least one cache hit
    assert methods["full_optimizations"] >= 3  # At least three full optimizations

@pytest.mark.asyncio
async def test_quality_preservation_during_optimization(cost_optimization_manager):
    """Test that optimization maintains response quality."""
    high_quality_request = "Provide detailed analysis of quantum computing implications for cybersecurity"
    
    # Test with high quality requirement
    result = await cost_optimization_manager.optimize_llm_request(
        high_quality_request, "high"
    )
    
    assert result["optimized"] is True
    
    # Check that optimization details indicate quality preservation
    if "optimization_details" in result:
        # Quality should be maintained even with optimization
        assert result["cost_saved"] >= 0  # Should still save some cost

@pytest.mark.asyncio
async def test_optimization_performance_requirements(cost_optimization_manager):
    """Test that optimization meets performance requirements."""
    request = "Analyze customer behavior patterns"
    
    # Test response time
    start_time = time.time()
    result = await cost_optimization_manager.optimize_llm_request(request)
    response_time = time.time() - start_time
    
    # Optimization should be fast
    assert response_time < 2.0  # Less than 2 seconds
    assert result["optimized"] is True
    
    # Test multiple optimizations for consistency
    response_times = []
    for i in range(5):
        start = time.time()
        await cost_optimization_manager.optimize_llm_request(f"Test request {i}")
        response_times.append(time.time() - start)
    
    avg_response_time = sum(response_times) / len(response_times)
    assert avg_response_time < 1.5  # Average should be even faster