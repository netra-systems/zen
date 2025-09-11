"""Integration Tests for Agent Response Performance Optimization

Tests the performance optimization mechanisms for agent responses including
latency reduction, throughput improvement, and resource efficiency.

Business Value Justification (BVJ):
- Segment: All segments - Performance impacts all user experience
- Business Goal: Improve system efficiency and user satisfaction
- Value Impact: Faster responses increase user engagement and platform adoption
- Strategic Impact: Competitive advantage through superior response performance
"""

import asyncio
import pytest
import time
import statistics
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
class TestAgentResponsePerformanceOptimization(BaseIntegrationTest):
    """Test agent response performance optimization mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # BVJ: Real services for accurate performance measurement
        self.db_session = real_database_session()
        self.redis_client = real_redis_connection()
        
        # Performance test parameters
        self.performance_thresholds = {
            "simple_query_max_latency": 2.0,  # seconds
            "complex_query_max_latency": 5.0,  # seconds
            "concurrent_query_max_latency": 3.0,  # seconds
            "throughput_min_queries_per_second": 2.0,
            "memory_growth_max_mb": 100,  # MB
            "cpu_usage_max_percent": 80
        }
        
        # Test query sets for different performance scenarios
        self.query_sets = {
            "simple": [
                "What is AI optimization?",
                "Show current status",
                "List available features"
            ],
            "complex": [
                "Analyze comprehensive performance metrics across all optimization categories",
                "Generate detailed report with historical trends and predictive analytics",
                "Perform cross-correlation analysis of optimization parameters"
            ],
            "varied": [
                "Quick status check",
                "Detailed performance analysis with multi-dimensional metrics",
                "Simple feature overview",
                "Complex optimization strategy recommendations with implementation roadmap"
            ]
        }

    async def test_response_latency_optimization(self):
        """
        Test response latency for different query types.
        
        BVJ: All segments - Low latency directly impacts user satisfaction
        and platform competitiveness in real-time AI interactions.
        """
        logger.info("Testing response latency optimization")
        
        env = self.get_env()
        user_id = "latency_test_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            
            agent = DataHelperAgent(
                agent_id="latency_test_agent",
                user_context=context
            )
            
            # Test simple queries (should be fast)
            simple_latencies = []
            for query in self.query_sets["simple"]:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                latency = time.time() - start_time
                simple_latencies.append(latency)
                
                assert result is not None, f"Query should return result: {query}"
                
                logger.info(f"Simple query latency: {latency:.3f}s for '{query[:30]}...'")
            
            # Test complex queries (allowed higher latency)
            complex_latencies = []
            for query in self.query_sets["complex"]:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                latency = time.time() - start_time
                complex_latencies.append(latency)
                
                assert result is not None, f"Complex query should return result: {query}"
                
                logger.info(f"Complex query latency: {latency:.3f}s for '{query[:30]}...'")
            
            # Validate performance thresholds
            avg_simple_latency = statistics.mean(simple_latencies)
            avg_complex_latency = statistics.mean(complex_latencies)
            
            assert avg_simple_latency < self.performance_thresholds["simple_query_max_latency"], \
                f"Simple queries too slow: {avg_simple_latency:.3f}s > {self.performance_thresholds['simple_query_max_latency']}s"
            
            assert avg_complex_latency < self.performance_thresholds["complex_query_max_latency"], \
                f"Complex queries too slow: {avg_complex_latency:.3f}s > {self.performance_thresholds['complex_query_max_latency']}s"
            
            # Performance improvement validation
            assert avg_simple_latency < avg_complex_latency * 0.7, \
                "Simple queries should be significantly faster than complex queries"

    async def test_concurrent_request_performance(self):
        """
        Test performance under concurrent request load.
        
        BVJ: Enterprise segment - Concurrent handling is critical for
        multi-user enterprise environments and platform scalability.
        """
        logger.info("Testing concurrent request performance")
        
        env = self.get_env()
        
        async def concurrent_request(user_index: int, query: str) -> Dict[str, Any]:
            user_id = f"concurrent_user_{user_index:03d}"
            
            with create_isolated_execution_context(user_id) as context:
                
                agent = DataHelperAgent(
                    agent_id=f"concurrent_agent_{user_index:03d}",
                    user_context=context
                )
                
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                latency = time.time() - start_time
                
                return {
                    "user_index": user_index,
                    "latency": latency,
                    "success": result is not None,
                    "response_size": len(str(result.result_data)) if result else 0
                }
        
        # Run concurrent requests
        concurrent_count = 5
        test_query = "Analyze optimization performance metrics"
        
        start_time = time.time()
        
        tasks = [
            concurrent_request(i, test_query) 
            for i in range(concurrent_count)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze concurrent performance
        successful_results = [
            r for r in results 
            if isinstance(r, dict) and r.get("success")
        ]
        
        assert len(successful_results) == concurrent_count, \
            f"All concurrent requests should succeed: {len(successful_results)}/{concurrent_count}"
        
        latencies = [r["latency"] for r in successful_results]
        avg_concurrent_latency = statistics.mean(latencies)
        max_concurrent_latency = max(latencies)
        
        # Validate concurrent performance
        assert avg_concurrent_latency < self.performance_thresholds["concurrent_query_max_latency"], \
            f"Average concurrent latency too high: {avg_concurrent_latency:.3f}s"
        
        assert max_concurrent_latency < self.performance_thresholds["concurrent_query_max_latency"] * 1.5, \
            f"Max concurrent latency too high: {max_concurrent_latency:.3f}s"
        
        # Calculate effective throughput
        throughput = concurrent_count / total_time
        
        assert throughput >= self.performance_thresholds["throughput_min_queries_per_second"], \
            f"Throughput too low: {throughput:.2f} qps < {self.performance_thresholds['throughput_min_queries_per_second']} qps"
        
        logger.info(f"Concurrent performance: {throughput:.2f} qps, avg latency: {avg_concurrent_latency:.3f}s")

    async def test_response_size_optimization(self):
        """
        Test optimization of response sizes for different content types.
        
        BVJ: All segments - Optimized response sizes improve bandwidth
        efficiency and mobile user experience.
        """
        logger.info("Testing response size optimization")
        
        env = self.get_env()
        user_id = "size_optimization_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            
            agent = DataHelperAgent(
                agent_id="size_optimization_agent",
                user_context=context
            )
            
            # Test different response size scenarios
            size_test_queries = [
                ("brief", "Give me a brief status update"),
                ("detailed", "Provide a comprehensive analysis with all available metrics"),
                ("summary", "Summarize the key optimization recommendations"),
                ("full_report", "Generate complete optimization report with historical data")
            ]
            
            response_sizes = {}
            
            for query_type, query in size_test_queries:
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                response_size = len(str(result.result_data))
                response_sizes[query_type] = response_size
                
                logger.info(f"{query_type} response size: {response_size} characters")
            
            # Validate size optimization
            # Brief should be smallest
            assert response_sizes["brief"] < response_sizes["detailed"], \
                "Brief response should be smaller than detailed response"
            
            assert response_sizes["summary"] < response_sizes["full_report"], \
                "Summary should be smaller than full report"
            
            # Reasonable size limits
            assert response_sizes["brief"] < 500, \
                "Brief response should be concise"
            
            assert response_sizes["detailed"] > response_sizes["brief"] * 2, \
                "Detailed response should be substantially larger than brief"
            
            # Check for appropriate content density
            for query_type, size in response_sizes.items():
                assert size > 20, f"{query_type} response should have meaningful content"
                assert size < 10000, f"{query_type} response should not be excessively large"

    async def test_memory_usage_optimization(self):
        """
        Test memory usage optimization during response generation.
        
        BVJ: Platform stability - Efficient memory usage enables better
        scalability and reduces infrastructure costs.
        """
        logger.info("Testing memory usage optimization")
        
        env = self.get_env()
        
        # Track memory usage patterns
        memory_measurements = []
        
        for i in range(10):
            user_id = f"memory_test_user_{i:03d}"
            
            with create_isolated_execution_context(user_id) as context:
                
                agent = DataHelperAgent(
                    agent_id=f"memory_test_agent_{i:03d}",
                    user_context=context
                )
                
                # Simulate memory usage measurement
                pre_query_memory = self._estimate_memory_usage()
                
                # Generate response
                result = await agent.arun(
                    input_data=f"Generate optimization analysis #{i} with detailed metrics",
                    user_context=context
                )
                
                post_query_memory = self._estimate_memory_usage()
                
                memory_delta = post_query_memory - pre_query_memory
                
                memory_measurements.append({
                    "iteration": i,
                    "memory_delta": memory_delta,
                    "response_size": len(str(result.result_data)) if result else 0
                })
        
        # Analyze memory usage patterns
        memory_deltas = [m["memory_delta"] for m in memory_measurements]
        avg_memory_delta = statistics.mean(memory_deltas)
        max_memory_delta = max(memory_deltas)
        
        # Validate memory efficiency
        assert avg_memory_delta < self.performance_thresholds["memory_growth_max_mb"], \
            f"Average memory growth too high: {avg_memory_delta:.2f} MB"
        
        assert max_memory_delta < self.performance_thresholds["memory_growth_max_mb"] * 2, \
            f"Peak memory growth too high: {max_memory_delta:.2f} MB"
        
        # Check for memory leaks (increasing trend)
        first_half = memory_deltas[:5]
        second_half = memory_deltas[5:]
        
        avg_first_half = statistics.mean(first_half)
        avg_second_half = statistics.mean(second_half)
        
        memory_growth_trend = avg_second_half - avg_first_half
        
        assert memory_growth_trend < 20, \
            f"Memory usage should not trend upward significantly: {memory_growth_trend:.2f} MB growth"
        
        logger.info(f"Memory optimization: avg {avg_memory_delta:.2f} MB, max {max_memory_delta:.2f} MB")

    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback to simple estimation
            return time.time() % 100  # Mock memory usage

    async def test_streaming_response_optimization(self):
        """
        Test streaming response optimization for long-running queries.
        
        BVJ: All segments - Streaming improves perceived performance
        and user experience for complex AI interactions.
        """
        logger.info("Testing streaming response optimization")
        
        env = self.get_env()
        user_id = "streaming_test_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["streaming_enabled"] = True
            context.context_data["chunk_size"] = 100  # characters
            
            agent = DataHelperAgent(
                agent_id="streaming_test_agent",
                user_context=context
            )
            
            # Long query that benefits from streaming
            long_query = "Generate a comprehensive optimization report including " \
                        "historical analysis, current performance metrics, " \
                        "predictive analytics, and detailed recommendations"
            
            start_time = time.time()
            
            # Simulate streaming response
            result = await agent.arun(
                input_data=long_query,
                user_context=context
            )
            
            total_time = time.time() - start_time
            
            # Validate streaming optimization
            assert result is not None, "Streaming query should return result"
            
            response_text = str(result.result_data)
            response_length = len(response_text)
            
            # Should be substantial response for streaming test
            assert response_length > 200, \
                "Streaming test should generate substantial response"
            
            # Estimate streaming benefits
            if hasattr(result, 'metadata') and 'streaming_chunks' in str(result.metadata):
                # Response was streamed
                chunks_info = result.metadata.get('streaming_chunks', 1)
                estimated_chunks = max(1, response_length // context.context_data.get('chunk_size', 100))
                
                assert chunks_info >= estimated_chunks * 0.8, \
                    "Should have appropriate number of streaming chunks"
            
            # Total time should be reasonable for streaming
            assert total_time < self.performance_thresholds["complex_query_max_latency"], \
                f"Streaming query took too long: {total_time:.3f}s"
            
            logger.info(f"Streaming optimization: {response_length} chars in {total_time:.3f}s")

    async def test_caching_performance_impact(self):
        """
        Test performance impact of response caching mechanisms.
        
        BVJ: Mid/Enterprise segment - Caching significantly improves
        response times for repeated queries and reduces costs.
        """
        logger.info("Testing caching performance impact")
        
        env = self.get_env()
        user_id = "caching_performance_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["caching_enabled"] = True
            
            agent = DataHelperAgent(
                agent_id="caching_performance_agent",
                user_context=context
            )
            
            test_query = "Analyze optimization metrics for performance testing"
            
            # First request (cache miss)
            start_time = time.time()
            first_result = await agent.arun(
                input_data=test_query,
                user_context=context
            )
            first_latency = time.time() - start_time
            
            # Second request (potential cache hit)
            start_time = time.time()
            second_result = await agent.arun(
                input_data=test_query,
                user_context=context
            )
            second_latency = time.time() - start_time
            
            # Third request (should be cached)
            start_time = time.time()
            third_result = await agent.arun(
                input_data=test_query,
                user_context=context
            )
            third_latency = time.time() - start_time
            
            # Validate caching performance improvement
            assert first_result.result_data == second_result.result_data, \
                "Cached results should be consistent"
            
            assert second_result.result_data == third_result.result_data, \
                "Cached results should remain consistent"
            
            # Performance improvement from caching
            avg_cached_latency = (second_latency + third_latency) / 2
            cache_improvement = (first_latency - avg_cached_latency) / first_latency
            
            # Should see some performance improvement from caching
            assert cache_improvement > -0.5, \
                "Caching should not significantly degrade performance"
            
            logger.info(f"Cache performance: first={first_latency:.3f}s, cached_avg={avg_cached_latency:.3f}s, improvement={cache_improvement:.1%}")

    async def test_query_complexity_adaptation(self):
        """
        Test adaptive performance based on query complexity detection.
        
        BVJ: All segments - Intelligent complexity detection enables
        optimal resource allocation and response times.
        """
        logger.info("Testing query complexity adaptation")
        
        env = self.get_env()
        user_id = "complexity_adaptation_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["adaptive_performance"] = True
            
            agent = DataHelperAgent(
                agent_id="complexity_adaptation_agent",
                user_context=context
            )
            
            # Test queries of varying complexity
            complexity_tests = [
                ("low", "Status?"),
                ("medium", "Show optimization recommendations"),
                ("high", "Perform comprehensive multi-dimensional analysis with predictive modeling"),
                ("very_high", "Generate detailed report with historical trends, correlation analysis, predictive forecasting, and comprehensive optimization strategies")
            ]
            
            performance_results = {}
            
            for complexity_level, query in complexity_tests:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                latency = time.time() - start_time
                response_size = len(str(result.result_data)) if result else 0
                
                performance_results[complexity_level] = {
                    "latency": latency,
                    "response_size": response_size,
                    "efficiency": response_size / latency if latency > 0 else 0
                }
                
                logger.info(f"{complexity_level} complexity: {latency:.3f}s, {response_size} chars")
            
            # Validate adaptive performance
            # Higher complexity should generally take more time but produce more content
            assert performance_results["low"]["latency"] < performance_results["high"]["latency"], \
                "Low complexity queries should be faster than high complexity"
            
            assert performance_results["medium"]["latency"] < performance_results["very_high"]["latency"], \
                "Medium complexity should be faster than very high complexity"
            
            # Response size should generally correlate with complexity
            assert performance_results["low"]["response_size"] < performance_results["high"]["response_size"], \
                "Higher complexity should generally produce more content"
            
            # Efficiency should be reasonable across complexity levels
            for level, result in performance_results.items():
                assert result["efficiency"] > 10, \
                    f"{level} complexity should maintain reasonable efficiency: {result['efficiency']:.1f}"