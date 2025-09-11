"""Integration Tests for Agent Response Caching and Optimization

Tests the agent response caching mechanisms and optimization strategies
to ensure efficient response delivery and reduced computational overhead.

Business Value Justification (BVJ):
- Segment: Mid/Enterprise - Performance-sensitive customers
- Business Goal: Improve system efficiency and reduce costs
- Value Impact: Faster response times and lower infrastructure costs
- Strategic Impact: Enables scaling to more customers without proportional cost increases
"""

import asyncio
import pytest
import time
import hashlib
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.real_services_test_fixtures import (
    real_database_session,
    real_redis_connection
)
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import (
    TypedAgentResult,
    AgentExecutionResult
)
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseCachingOptimization(BaseIntegrationTest):
    """Test agent response caching and optimization mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # BVJ: Real Redis connection for caching validation
        self.redis_client = real_redis_connection()
        
        # BVJ: Real database for persistence testing
        self.db_session = real_database_session()
        
        # Test data for caching scenarios
        self.cache_test_data = {
            "user_query": "What are the best optimization strategies for AI workloads?",
            "agent_type": "optimization_agent",
            "context_data": {"user_tier": "enterprise", "previous_queries": 5}
        }

    async def test_response_cache_hit_optimization(self):
        """
        Test that cached responses are returned efficiently.
        
        BVJ: Enterprise segment - Cache hits reduce response time by 80%+
        and decrease computational costs significantly.
        """
        logger.info("Testing response cache hit optimization")
        
        env = self.get_env()
        user_id = "cache_test_user_001"
        
        # Create user context for caching
        with create_isolated_execution_context(user_id) as context:
            
            # First request - should miss cache and compute response
            start_time = time.time()
            
            agent = DataHelperAgent(
                agent_id="cache_agent_001",
                user_context=context
            )
            
            # Generate initial response
            query_hash = hashlib.md5(
                self.cache_test_data["user_query"].encode()
            ).hexdigest()
            
            first_result = await agent.arun(
                input_data=self.cache_test_data["user_query"],
                user_context=context
            )
            
            first_duration = time.time() - start_time
            
            # Second request - should hit cache
            start_time = time.time()
            
            cached_result = await agent.arun(
                input_data=self.cache_test_data["user_query"],
                user_context=context
            )
            
            cached_duration = time.time() - start_time
            
            # Validate cache performance improvement
            assert cached_duration < first_duration * 0.5, \
                f"Cache hit should be at least 50% faster: {cached_duration} vs {first_duration}"
            
            # Validate response consistency
            assert first_result.result_data == cached_result.result_data, \
                "Cached response should match original response"
            
            logger.info(f"Cache optimization successful: {first_duration:.3f}s -> {cached_duration:.3f}s")

    async def test_cache_invalidation_strategies(self):
        """
        Test cache invalidation when context changes.
        
        BVJ: Enterprise segment - Ensures data freshness while maintaining
        performance benefits of caching.
        """
        logger.info("Testing cache invalidation strategies")
        
        env = self.get_env()
        user_id = "cache_invalidation_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            
            agent = DataHelperAgent(
                agent_id="invalidation_agent_001",
                user_context=context
            )
            
            # Initial cached response
            initial_result = await agent.arun(
                input_data="Show me optimization metrics",
                user_context=context
            )
            
            # Change context data (should invalidate cache)
            context.context_data["user_tier"] = "premium"
            context.context_data["feature_flags"] = ["advanced_analytics"]
            
            # Request with changed context
            updated_result = await agent.arun(
                input_data="Show me optimization metrics",
                user_context=context
            )
            
            # Validate cache was invalidated and response updated
            assert initial_result.result_data != updated_result.result_data, \
                "Cache should be invalidated when context changes"
            
            # Verify context-aware response
            assert "premium" in str(updated_result.result_data).lower() or \
                   "advanced" in str(updated_result.result_data).lower(), \
                   "Response should reflect updated context"

    async def test_multi_user_cache_isolation(self):
        """
        Test that cache isolation prevents cross-user data leakage.
        
        BVJ: Enterprise segment - Critical for multi-tenant security
        and data privacy compliance.
        """
        logger.info("Testing multi-user cache isolation")
        
        env = self.get_env()
        user_a_id = "cache_user_a_001"
        user_b_id = "cache_user_b_001"
        
        # User A context
        with create_isolated_execution_context(user_a_id) as context_a:
            context_a.context_data["company"] = "TechCorp"
            context_a.context_data["data_access"] = ["internal", "confidential"]
            
            agent_a = DataHelperAgent(
                agent_id="cache_agent_a_001",
                user_context=context_a
            )
            
            result_a = await agent_a.arun(
                input_data="Show company-specific optimization data",
                user_context=context_a
            )
        
        # User B context (different company)
        with create_isolated_execution_context(user_b_id) as context_b:
            context_b.context_data["company"] = "InnovateLab"
            context_b.context_data["data_access"] = ["public"]
            
            agent_b = DataHelperAgent(
                agent_id="cache_agent_b_001",
                user_context=context_b
            )
            
            result_b = await agent_b.arun(
                input_data="Show company-specific optimization data",
                user_context=context_b
            )
        
        # Validate cache isolation
        assert result_a.result_data != result_b.result_data, \
            "Different users should get different cached responses"
        
        # Verify no cross-contamination
        result_a_str = str(result_a.result_data).lower()
        result_b_str = str(result_b.result_data).lower()
        
        assert "techcorp" not in result_b_str, \
            "User B should not see User A's company data"
        assert "innovatelab" not in result_a_str, \
            "User A should not see User B's company data"

    async def test_response_compression_optimization(self):
        """
        Test response compression for large agent outputs.
        
        BVJ: All segments - Reduces bandwidth usage and improves
        mobile user experience significantly.
        """
        logger.info("Testing response compression optimization")
        
        env = self.get_env()
        user_id = "compression_test_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            
            agent = DataHelperAgent(
                agent_id="compression_agent_001",
                user_context=context
            )
            
            # Generate large response for compression testing
            large_query = "Generate a comprehensive optimization report with detailed metrics, " \
                         "recommendations, and historical analysis for the past 12 months"
            
            # Request with compression enabled
            start_time = time.time()
            
            compressed_result = await agent.arun(
                input_data=large_query,
                user_context=context
            )
            
            compression_time = time.time() - start_time
            
            # Validate response size and compression
            result_size = len(str(compressed_result.result_data))
            
            assert result_size > 1000, \
                "Should generate substantial response for compression testing"
            
            # Verify compression metadata if available
            if hasattr(compressed_result, 'metadata'):
                compression_ratio = compressed_result.metadata.get('compression_ratio', 1.0)
                assert compression_ratio > 1.1, \
                    "Should achieve meaningful compression ratio"
            
            logger.info(f"Compression test completed: {result_size} bytes in {compression_time:.3f}s")

    async def test_cache_memory_optimization(self):
        """
        Test cache memory usage and cleanup strategies.
        
        BVJ: Platform stability - Prevents memory leaks and ensures
        sustainable system performance under load.
        """
        logger.info("Testing cache memory optimization")
        
        env = self.get_env()
        
        # Track memory usage patterns
        cache_operations = []
        
        for i in range(10):
            user_id = f"memory_test_user_{i:03d}"
            
            with create_isolated_execution_context(user_id) as context:
                
                agent = DataHelperAgent(
                    agent_id=f"memory_agent_{i:03d}",
                    user_context=context
                )
                
                # Generate varying response sizes
                query = f"Optimization analysis #{i} with detailed metrics"
                
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                cache_operations.append({
                    "user_id": user_id,
                    "response_size": len(str(result.result_data)),
                    "timestamp": time.time()
                })
        
        # Validate cache operations completed
        assert len(cache_operations) == 10, \
            "All cache operations should complete successfully"
        
        # Test cache cleanup (if supported)
        total_size = sum(op["response_size"] for op in cache_operations)
        logger.info(f"Cache memory test completed: {total_size} total bytes across 10 operations")
        
        # Verify reasonable memory usage
        avg_response_size = total_size / len(cache_operations)
        assert avg_response_size < 50000, \
            "Average response size should be reasonable for caching"

    async def test_cache_performance_under_load(self):
        """
        Test cache performance under concurrent load.
        
        BVJ: Enterprise segment - Validates system stability
        under high concurrent usage scenarios.
        """
        logger.info("Testing cache performance under load")
        
        env = self.get_env()
        
        # Concurrent cache operations
        async def cache_operation(user_index: int) -> Dict[str, Any]:
            user_id = f"load_test_user_{user_index:03d}"
            
            with create_isolated_execution_context(user_id) as context:
                
                agent = DataHelperAgent(
                    agent_id=f"load_agent_{user_index:03d}",
                    user_context=context
                )
                
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=f"Load test query #{user_index}",
                    user_context=context
                )
                
                duration = time.time() - start_time
                
                return {
                    "user_index": user_index,
                    "duration": duration,
                    "success": result is not None
                }
        
        # Run concurrent operations
        start_time = time.time()
        
        tasks = [cache_operation(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Validate concurrent performance
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        assert len(successful_operations) == 5, \
            "All concurrent cache operations should succeed"
        
        avg_duration = sum(r["duration"] for r in successful_operations) / len(successful_operations)
        
        assert avg_duration < 10.0, \
            f"Average operation duration should be reasonable: {avg_duration:.3f}s"
        
        logger.info(f"Load test completed: {len(successful_operations)}/5 operations in {total_duration:.3f}s")

    async def test_cache_consistency_across_sessions(self):
        """
        Test cache consistency across multiple user sessions.
        
        BVJ: All segments - Ensures reliable user experience
        across different login sessions and devices.
        """
        logger.info("Testing cache consistency across sessions")
        
        env = self.get_env()
        user_id = "consistency_test_user_001"
        test_query = "Get optimization recommendations for my account"
        
        # Session 1
        with create_isolated_execution_context(user_id) as context1:
            context1.context_data["session_id"] = "session_001"
            context1.context_data["device"] = "desktop"
            
            agent1 = DataHelperAgent(
                agent_id="consistency_agent_001",
                user_context=context1
            )
            
            result1 = await agent1.arun(
                input_data=test_query,
                user_context=context1
            )
        
        # Session 2 (same user, different session)
        with create_isolated_execution_context(user_id) as context2:
            context2.context_data["session_id"] = "session_002"
            context2.context_data["device"] = "mobile"
            
            agent2 = DataHelperAgent(
                agent_id="consistency_agent_002",
                user_context=context2
            )
            
            result2 = await agent2.arun(
                input_data=test_query,
                user_context=context2
            )
        
        # Validate consistency across sessions
        # Results should be consistent for same user
        assert result1.result_data == result2.result_data, \
            "Cache should provide consistent results across sessions for same user"
        
        # Verify both results are valid
        assert result1.result_data is not None, "Session 1 should return valid result"
        assert result2.result_data is not None, "Session 2 should return valid result"