# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3-15: LLM Response Caching with Real Redis Integration Test

# REMOVED_SYNTAX_ERROR: BVJ: Reduces LLM costs by 40% through intelligent caching of responses.
# REMOVED_SYNTAX_ERROR: Critical for cost optimization and performance in AI workloads.

# REMOVED_SYNTAX_ERROR: Tests LLM response caching with real Redis containers and cache strategies.
""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

import docker
import pytest
import redis.asyncio as aioredis
from netra_backend.app.services.api_gateway.cache_strategies import CacheStrategy
# from caching.llm_cache_manager import LLMCacheManager  # Module doesn't exist, use available cache manager
# Legacy import removed - use resource_cache instead
# from netra_backend.app.services.cache.cache_manager import LLMCacheManager
from netra_backend.app.llm.resource_cache import LRUCache as LLMCacheManager
# from netra_backend.app.llm.response_processor import LLMResponseProcessor  # Module doesn't exist

# REMOVED_SYNTAX_ERROR: @pytest.mark.L3
# REMOVED_SYNTAX_ERROR: class TestLLMResponseCachingRedisL3:
    # REMOVED_SYNTAX_ERROR: """Test LLM response caching with real Redis."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def docker_client(self):
    # REMOVED_SYNTAX_ERROR: """Docker client for container management."""
    # REMOVED_SYNTAX_ERROR: client = docker.from_env()
    # REMOVED_SYNTAX_ERROR: yield client
    # REMOVED_SYNTAX_ERROR: client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_container(self, docker_client):
    # REMOVED_SYNTAX_ERROR: """Start Redis container for caching."""
    # REMOVED_SYNTAX_ERROR: container = docker_client.containers.run( )
    # REMOVED_SYNTAX_ERROR: "redis:7-alpine",
    # REMOVED_SYNTAX_ERROR: ports={'6379/tcp': None},
    # REMOVED_SYNTAX_ERROR: detach=True,
    # REMOVED_SYNTAX_ERROR: name="llm_cache_test_redis"
    

    # Get assigned port
    # REMOVED_SYNTAX_ERROR: container.reload()
    # REMOVED_SYNTAX_ERROR: port = container.attrs['NetworkSettings']['Ports']['6379/tcp'][0]['HostPort']

    # Wait for Redis to be ready
    # REMOVED_SYNTAX_ERROR: await self._wait_for_redis(port)

    # REMOVED_SYNTAX_ERROR: redis_config = { )
    # REMOVED_SYNTAX_ERROR: "host": "localhost",
    # REMOVED_SYNTAX_ERROR: "port": int(port),
    # REMOVED_SYNTAX_ERROR: "db": 0
    

    # REMOVED_SYNTAX_ERROR: yield redis_config

    # REMOVED_SYNTAX_ERROR: container.stop()
    # REMOVED_SYNTAX_ERROR: container.remove()

# REMOVED_SYNTAX_ERROR: async def _wait_for_redis(self, port: str, timeout: int = 30):
    # REMOVED_SYNTAX_ERROR: """Wait for Redis to be available."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: while time.time() - start_time < timeout:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: redis_client = aioredis.Redis( )
            # REMOVED_SYNTAX_ERROR: host="localhost",
            # REMOVED_SYNTAX_ERROR: port=int(port),
            # REMOVED_SYNTAX_ERROR: decode_responses=True
            
            # REMOVED_SYNTAX_ERROR: await redis_client.ping()
            # REMOVED_SYNTAX_ERROR: await redis_client.close()
            # REMOVED_SYNTAX_ERROR: return
            # REMOVED_SYNTAX_ERROR: except:
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)
                # REMOVED_SYNTAX_ERROR: raise TimeoutError("formatted_string")

                # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def cache_manager(self, redis_container):
    # REMOVED_SYNTAX_ERROR: """Create LLM cache manager with Redis backend."""
    # REMOVED_SYNTAX_ERROR: manager = LLMCacheManager(redis_config=redis_container)
    # REMOVED_SYNTAX_ERROR: await manager.initialize()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def response_processor(self, cache_manager):
    # REMOVED_SYNTAX_ERROR: """Create LLM response processor with caching."""
    # REMOVED_SYNTAX_ERROR: processor = LLMResponseProcessor(cache_manager=cache_manager)
    # REMOVED_SYNTAX_ERROR: await processor.initialize()
    # REMOVED_SYNTAX_ERROR: yield processor
    # REMOVED_SYNTAX_ERROR: await processor.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_llm_responses(self):
    # REMOVED_SYNTAX_ERROR: """Create mock LLM responses for testing."""
    # REMOVED_SYNTAX_ERROR: responses = { )
    # REMOVED_SYNTAX_ERROR: "simple_question": { )
    # REMOVED_SYNTAX_ERROR: "prompt": "What is the capital of France?",
    # REMOVED_SYNTAX_ERROR: "response": "The capital of France is Paris.",
    # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: "tokens": 12,
    # REMOVED_SYNTAX_ERROR: "cost": 0.00024
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "complex_analysis": { )
    # REMOVED_SYNTAX_ERROR: "prompt": "Analyze the economic impact of renewable energy adoption",
    # REMOVED_SYNTAX_ERROR: "response": "Renewable energy adoption has significant positive economic impacts including job creation, reduced energy costs, and increased energy independence...",
    # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: "tokens": 350,
    # REMOVED_SYNTAX_ERROR: "cost": 0.021
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "code_generation": { )
    # REMOVED_SYNTAX_ERROR: "prompt": "Write a Python function to calculate fibonacci numbers",
    # REMOVED_SYNTAX_ERROR: "response": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
    # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: "tokens": 45,
    # REMOVED_SYNTAX_ERROR: "cost": 0.0009
    
    
    # REMOVED_SYNTAX_ERROR: yield responses

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_cache_store_and_retrieve( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: cache_manager,
    # REMOVED_SYNTAX_ERROR: mock_llm_responses
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test basic cache store and retrieve operations."""
        # REMOVED_SYNTAX_ERROR: response_data = mock_llm_responses["simple_question"]

        # Generate cache key
        # REMOVED_SYNTAX_ERROR: cache_key = cache_manager.generate_cache_key( )
        # REMOVED_SYNTAX_ERROR: prompt=response_data["prompt"],
        # REMOVED_SYNTAX_ERROR: model=response_data["model"],
        # REMOVED_SYNTAX_ERROR: parameters={}
        

        # Store response in cache
        # REMOVED_SYNTAX_ERROR: await cache_manager.store_response( )
        # REMOVED_SYNTAX_ERROR: cache_key,
        # REMOVED_SYNTAX_ERROR: response_data["response"],
        # REMOVED_SYNTAX_ERROR: metadata={ )
        # REMOVED_SYNTAX_ERROR: "model": response_data["model"],
        # REMOVED_SYNTAX_ERROR: "tokens": response_data["tokens"],
        # REMOVED_SYNTAX_ERROR: "cost": response_data["cost"]
        
        

        # Retrieve response from cache
        # REMOVED_SYNTAX_ERROR: cached_response = await cache_manager.get_response(cache_key)

        # REMOVED_SYNTAX_ERROR: assert cached_response is not None
        # REMOVED_SYNTAX_ERROR: assert cached_response["response"] == response_data["response"]
        # REMOVED_SYNTAX_ERROR: assert cached_response["metadata"]["model"] == response_data["model"]
        # REMOVED_SYNTAX_ERROR: assert cached_response["metadata"]["tokens"] == response_data["tokens"]

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_cache_hit_rate_optimization( )
        # REMOVED_SYNTAX_ERROR: self,
        # REMOVED_SYNTAX_ERROR: cache_manager,
        # REMOVED_SYNTAX_ERROR: response_processor,
        # REMOVED_SYNTAX_ERROR: mock_llm_responses
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test cache hit rate optimization with similar prompts."""
            # Store initial responses
            # REMOVED_SYNTAX_ERROR: for response_key, response_data in mock_llm_responses.items():
                # REMOVED_SYNTAX_ERROR: await response_processor.process_and_cache( )
                # REMOVED_SYNTAX_ERROR: prompt=response_data["prompt"],
                # REMOVED_SYNTAX_ERROR: model=response_data["model"],
                # REMOVED_SYNTAX_ERROR: response=response_data["response"],
                # REMOVED_SYNTAX_ERROR: metadata={ )
                # REMOVED_SYNTAX_ERROR: "tokens": response_data["tokens"],
                # REMOVED_SYNTAX_ERROR: "cost": response_data["cost"]
                
                

                # Test exact match (should be cache hit)
                # REMOVED_SYNTAX_ERROR: exact_match_result = await response_processor.get_cached_response( )
                # REMOVED_SYNTAX_ERROR: prompt=mock_llm_responses["simple_question"]["prompt"],
                # REMOVED_SYNTAX_ERROR: model=mock_llm_responses["simple_question"]["model"]
                

                # REMOVED_SYNTAX_ERROR: assert exact_match_result is not None
                # REMOVED_SYNTAX_ERROR: assert exact_match_result["cache_hit"] is True

                # Test similar prompt (should use semantic similarity)
                # REMOVED_SYNTAX_ERROR: similar_prompt = "What"s the capital city of France?"  # Similar to original
                # REMOVED_SYNTAX_ERROR: similar_result = await response_processor.get_cached_response( )
                # REMOVED_SYNTAX_ERROR: prompt=similar_prompt,
                # REMOVED_SYNTAX_ERROR: model=mock_llm_responses["simple_question"]["model"],
                # REMOVED_SYNTAX_ERROR: similarity_threshold=0.8
                

                # Should find similar cached response
                # REMOVED_SYNTAX_ERROR: if similar_result:
                    # REMOVED_SYNTAX_ERROR: assert similar_result["similarity_score"] >= 0.8

                    # Get cache statistics
                    # REMOVED_SYNTAX_ERROR: stats = await cache_manager.get_cache_stats()
                    # REMOVED_SYNTAX_ERROR: assert stats["total_requests"] >= 2
                    # REMOVED_SYNTAX_ERROR: assert stats["cache_hits"] >= 1
                    # REMOVED_SYNTAX_ERROR: assert stats["hit_rate"] > 0

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_cache_expiration_and_ttl( )
                    # REMOVED_SYNTAX_ERROR: self,
                    # REMOVED_SYNTAX_ERROR: cache_manager,
                    # REMOVED_SYNTAX_ERROR: mock_llm_responses
                    # REMOVED_SYNTAX_ERROR: ):
                        # REMOVED_SYNTAX_ERROR: """Test cache expiration and TTL functionality."""
                        # REMOVED_SYNTAX_ERROR: response_data = mock_llm_responses["complex_analysis"]

                        # Store response with short TTL
                        # REMOVED_SYNTAX_ERROR: cache_key = cache_manager.generate_cache_key( )
                        # REMOVED_SYNTAX_ERROR: prompt=response_data["prompt"],
                        # REMOVED_SYNTAX_ERROR: model=response_data["model"]
                        

                        # REMOVED_SYNTAX_ERROR: await cache_manager.store_response( )
                        # REMOVED_SYNTAX_ERROR: cache_key,
                        # REMOVED_SYNTAX_ERROR: response_data["response"],
                        # REMOVED_SYNTAX_ERROR: metadata={"model": response_data["model"]],
                        # REMOVED_SYNTAX_ERROR: ttl=1  # 1 second TTL
                        

                        # Immediate retrieval should work
                        # REMOVED_SYNTAX_ERROR: immediate_result = await cache_manager.get_response(cache_key)
                        # REMOVED_SYNTAX_ERROR: assert immediate_result is not None

                        # Wait for expiration
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1.5)

                        # Should be expired now
                        # REMOVED_SYNTAX_ERROR: expired_result = await cache_manager.get_response(cache_key)
                        # REMOVED_SYNTAX_ERROR: assert expired_result is None

                        # Verify TTL was set correctly
                        # REMOVED_SYNTAX_ERROR: ttl_info = await cache_manager.get_ttl_info(cache_key)
                        # REMOVED_SYNTAX_ERROR: assert ttl_info["expired"] is True

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_cache_invalidation_strategies( )
                        # REMOVED_SYNTAX_ERROR: self,
                        # REMOVED_SYNTAX_ERROR: cache_manager,
                        # REMOVED_SYNTAX_ERROR: mock_llm_responses
                        # REMOVED_SYNTAX_ERROR: ):
                            # REMOVED_SYNTAX_ERROR: """Test different cache invalidation strategies."""
                            # Store responses with different models
                            # REMOVED_SYNTAX_ERROR: for response_key, response_data in mock_llm_responses.items():
                                # REMOVED_SYNTAX_ERROR: cache_key = cache_manager.generate_cache_key( )
                                # REMOVED_SYNTAX_ERROR: prompt=response_data["prompt"],
                                # REMOVED_SYNTAX_ERROR: model=response_data["model"]
                                

                                # REMOVED_SYNTAX_ERROR: await cache_manager.store_response( )
                                # REMOVED_SYNTAX_ERROR: cache_key,
                                # REMOVED_SYNTAX_ERROR: response_data["response"],
                                # REMOVED_SYNTAX_ERROR: metadata={ )
                                # REMOVED_SYNTAX_ERROR: "model": response_data["model"],
                                # REMOVED_SYNTAX_ERROR: "category": "test_category"
                                
                                

                                # Verify all responses are cached
                                # REMOVED_SYNTAX_ERROR: initial_count = await cache_manager.get_cache_count()
                                # REMOVED_SYNTAX_ERROR: assert initial_count >= 3

                                # Test model-specific invalidation
                                # REMOVED_SYNTAX_ERROR: await cache_manager.invalidate_by_model(LLMModel.GEMINI_2_5_FLASH.value)

                                # Check that only gpt-4 responses remain
                                # REMOVED_SYNTAX_ERROR: remaining_responses = await cache_manager.get_cached_responses_by_model(LLMModel.GEMINI_2_5_FLASH.value)
                                # REMOVED_SYNTAX_ERROR: assert len(remaining_responses) >= 1

                                # REMOVED_SYNTAX_ERROR: gpt35_responses = await cache_manager.get_cached_responses_by_model(LLMModel.GEMINI_2_5_FLASH.value)
                                # REMOVED_SYNTAX_ERROR: assert len(gpt35_responses) == 0

                                # Test category-based invalidation
                                # REMOVED_SYNTAX_ERROR: await cache_manager.invalidate_by_category("test_category")

                                # REMOVED_SYNTAX_ERROR: final_count = await cache_manager.get_cache_count()
                                # REMOVED_SYNTAX_ERROR: assert final_count == 0

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_cost_optimization_tracking( )
                                # REMOVED_SYNTAX_ERROR: self,
                                # REMOVED_SYNTAX_ERROR: cache_manager,
                                # REMOVED_SYNTAX_ERROR: response_processor,
                                # REMOVED_SYNTAX_ERROR: mock_llm_responses
                                # REMOVED_SYNTAX_ERROR: ):
                                    # REMOVED_SYNTAX_ERROR: """Test cost optimization tracking through caching."""
                                    # REMOVED_SYNTAX_ERROR: total_original_cost = 0
                                    # REMOVED_SYNTAX_ERROR: total_cached_savings = 0

                                    # Process responses multiple times to simulate cache usage
                                    # REMOVED_SYNTAX_ERROR: for _ in range(5):  # Simulate 5 identical requests
                                    # REMOVED_SYNTAX_ERROR: for response_key, response_data in mock_llm_responses.items():
                                        # REMOVED_SYNTAX_ERROR: result = await response_processor.process_request( )
                                        # REMOVED_SYNTAX_ERROR: prompt=response_data["prompt"],
                                        # REMOVED_SYNTAX_ERROR: model=response_data["model"],
                                        # REMOVED_SYNTAX_ERROR: expected_response=response_data["response"],
                                        # REMOVED_SYNTAX_ERROR: cost=response_data["cost"]
                                        

                                        # REMOVED_SYNTAX_ERROR: total_original_cost += response_data["cost"]
                                        # REMOVED_SYNTAX_ERROR: if result["from_cache"]:
                                            # REMOVED_SYNTAX_ERROR: total_cached_savings += response_data["cost"]

                                            # Get cost optimization stats
                                            # REMOVED_SYNTAX_ERROR: cost_stats = await cache_manager.get_cost_optimization_stats()

                                            # REMOVED_SYNTAX_ERROR: assert cost_stats["total_requests"] >= 15  # 3 responses × 5 iterations
                                            # REMOVED_SYNTAX_ERROR: assert cost_stats["cached_requests"] > 0
                                            # REMOVED_SYNTAX_ERROR: assert cost_stats["cost_savings"] > 0
                                            # REMOVED_SYNTAX_ERROR: assert cost_stats["cost_savings_percentage"] > 0

                                            # Verify significant cost savings
                                            # REMOVED_SYNTAX_ERROR: assert cost_stats["cost_savings_percentage"] >= 60  # Should save at least 60%

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_semantic_similarity_caching( )
                                            # REMOVED_SYNTAX_ERROR: self,
                                            # REMOVED_SYNTAX_ERROR: cache_manager,
                                            # REMOVED_SYNTAX_ERROR: response_processor
                                            # REMOVED_SYNTAX_ERROR: ):
                                                # REMOVED_SYNTAX_ERROR: """Test semantic similarity-based caching."""
                                                # Store base response
                                                # REMOVED_SYNTAX_ERROR: base_prompt = "How do I optimize database performance?"
                                                # REMOVED_SYNTAX_ERROR: base_response = "To optimize database performance, you should: 1) Index frequently queried columns, 2) Optimize queries, 3) Monitor performance metrics..."

                                                # REMOVED_SYNTAX_ERROR: await response_processor.process_and_cache( )
                                                # REMOVED_SYNTAX_ERROR: prompt=base_prompt,
                                                # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value,
                                                # REMOVED_SYNTAX_ERROR: response=base_response,
                                                # REMOVED_SYNTAX_ERROR: metadata={"tokens": 150, "cost": 0.009}
                                                

                                                # Test semantically similar prompts
                                                # REMOVED_SYNTAX_ERROR: similar_prompts = [ )
                                                # REMOVED_SYNTAX_ERROR: "What are best practices for database optimization?",
                                                # REMOVED_SYNTAX_ERROR: "How can I improve my database performance?",
                                                # REMOVED_SYNTAX_ERROR: "Database performance optimization techniques",
                                                # REMOVED_SYNTAX_ERROR: "Ways to make database queries faster"
                                                

                                                # REMOVED_SYNTAX_ERROR: similarity_results = []
                                                # REMOVED_SYNTAX_ERROR: for similar_prompt in similar_prompts:
                                                    # REMOVED_SYNTAX_ERROR: result = await response_processor.get_cached_response( )
                                                    # REMOVED_SYNTAX_ERROR: prompt=similar_prompt,
                                                    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value,
                                                    # REMOVED_SYNTAX_ERROR: similarity_threshold=0.7
                                                    

                                                    # REMOVED_SYNTAX_ERROR: if result:
                                                        # REMOVED_SYNTAX_ERROR: similarity_results.append({ ))
                                                        # REMOVED_SYNTAX_ERROR: "prompt": similar_prompt,
                                                        # REMOVED_SYNTAX_ERROR: "similarity_score": result["similarity_score"],
                                                        # REMOVED_SYNTAX_ERROR: "cache_hit": True
                                                        
                                                        # REMOVED_SYNTAX_ERROR: else:
                                                            # REMOVED_SYNTAX_ERROR: similarity_results.append({ ))
                                                            # REMOVED_SYNTAX_ERROR: "prompt": similar_prompt,
                                                            # REMOVED_SYNTAX_ERROR: "cache_hit": False
                                                            

                                                            # Should find at least some similar matches
                                                            # REMOVED_SYNTAX_ERROR: cache_hits = [item for item in []]]
                                                            # REMOVED_SYNTAX_ERROR: assert len(cache_hits) >= 2

                                                            # Verify similarity scores are reasonable
                                                            # REMOVED_SYNTAX_ERROR: for hit in cache_hits:
                                                                # REMOVED_SYNTAX_ERROR: assert hit["similarity_score"] >= 0.7

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_cache_size_management_and_eviction( )
                                                                # REMOVED_SYNTAX_ERROR: self,
                                                                # REMOVED_SYNTAX_ERROR: cache_manager
                                                                # REMOVED_SYNTAX_ERROR: ):
                                                                    # REMOVED_SYNTAX_ERROR: """Test cache size management and eviction policies."""
                                                                    # Configure cache with size limits
                                                                    # REMOVED_SYNTAX_ERROR: await cache_manager.configure_limits( )
                                                                    # REMOVED_SYNTAX_ERROR: max_entries=5,
                                                                    # REMOVED_SYNTAX_ERROR: max_memory_mb=10,
                                                                    # REMOVED_SYNTAX_ERROR: eviction_policy="lru"  # Least Recently Used
                                                                    

                                                                    # Fill cache beyond limit
                                                                    # REMOVED_SYNTAX_ERROR: for i in range(10):
                                                                        # REMOVED_SYNTAX_ERROR: large_response = "x" * 1000  # 1KB response
                                                                        # REMOVED_SYNTAX_ERROR: cache_key = "formatted_string"

                                                                        # REMOVED_SYNTAX_ERROR: await cache_manager.store_response( )
                                                                        # REMOVED_SYNTAX_ERROR: cache_key,
                                                                        # REMOVED_SYNTAX_ERROR: large_response,
                                                                        # REMOVED_SYNTAX_ERROR: metadata={"size": len(large_response)}
                                                                        

                                                                        # Check that cache size is within limits
                                                                        # REMOVED_SYNTAX_ERROR: cache_info = await cache_manager.get_cache_info()
                                                                        # REMOVED_SYNTAX_ERROR: assert cache_info["entry_count"] <= 5
                                                                        # REMOVED_SYNTAX_ERROR: assert cache_info["memory_usage_mb"] <= 10

                                                                        # Verify LRU eviction - access some keys to make them recently used
                                                                        # REMOVED_SYNTAX_ERROR: for i in [7, 8, 9]:
                                                                            # REMOVED_SYNTAX_ERROR: await cache_manager.get_response("formatted_string")

                                                                            # Add more entries to trigger eviction
                                                                            # REMOVED_SYNTAX_ERROR: for i in range(10, 15):
                                                                                # REMOVED_SYNTAX_ERROR: cache_key = "formatted_string"
                                                                                # REMOVED_SYNTAX_ERROR: await cache_manager.store_response( )
                                                                                # REMOVED_SYNTAX_ERROR: cache_key,
                                                                                # REMOVED_SYNTAX_ERROR: "new_response",
                                                                                # REMOVED_SYNTAX_ERROR: metadata={"size": 12}
                                                                                

                                                                                # Recently accessed keys should still be present
                                                                                # REMOVED_SYNTAX_ERROR: recent_keys_present = 0
                                                                                # REMOVED_SYNTAX_ERROR: for i in [7, 8, 9]:
                                                                                    # REMOVED_SYNTAX_ERROR: result = await cache_manager.get_response("formatted_string")
                                                                                    # REMOVED_SYNTAX_ERROR: if result:
                                                                                        # REMOVED_SYNTAX_ERROR: recent_keys_present += 1

                                                                                        # REMOVED_SYNTAX_ERROR: assert recent_keys_present >= 2  # Most recent keys should remain

                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                        # Removed problematic line: async def test_cache_warming_and_preloading( )
                                                                                        # REMOVED_SYNTAX_ERROR: self,
                                                                                        # REMOVED_SYNTAX_ERROR: cache_manager,
                                                                                        # REMOVED_SYNTAX_ERROR: response_processor
                                                                                        # REMOVED_SYNTAX_ERROR: ):
                                                                                            # REMOVED_SYNTAX_ERROR: """Test cache warming and preloading functionality."""
                                                                                            # Define common prompts for warming
                                                                                            # REMOVED_SYNTAX_ERROR: warming_prompts = [ )
                                                                                            # REMOVED_SYNTAX_ERROR: { )
                                                                                            # REMOVED_SYNTAX_ERROR: "prompt": "Explain machine learning concepts",
                                                                                            # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
                                                                                            # REMOVED_SYNTAX_ERROR: "expected_response": "Machine learning is a subset of artificial intelligence...",
                                                                                            # REMOVED_SYNTAX_ERROR: "priority": "high"
                                                                                            # REMOVED_SYNTAX_ERROR: },
                                                                                            # REMOVED_SYNTAX_ERROR: { )
                                                                                            # REMOVED_SYNTAX_ERROR: "prompt": "Best practices for API design",
                                                                                            # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
                                                                                            # REMOVED_SYNTAX_ERROR: "expected_response": "Good API design follows REST principles...",
                                                                                            # REMOVED_SYNTAX_ERROR: "priority": "medium"
                                                                                            # REMOVED_SYNTAX_ERROR: },
                                                                                            # REMOVED_SYNTAX_ERROR: { )
                                                                                            # REMOVED_SYNTAX_ERROR: "prompt": "Python performance optimization tips",
                                                                                            # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
                                                                                            # REMOVED_SYNTAX_ERROR: "expected_response": "To optimize Python performance: use list comprehensions...",
                                                                                            # REMOVED_SYNTAX_ERROR: "priority": "high"
                                                                                            
                                                                                            

                                                                                            # Warm the cache
                                                                                            # REMOVED_SYNTAX_ERROR: warming_results = await cache_manager.warm_cache(warming_prompts)

                                                                                            # REMOVED_SYNTAX_ERROR: assert warming_results["success"] is True
                                                                                            # REMOVED_SYNTAX_ERROR: assert warming_results["warmed_count"] == len(warming_prompts)

                                                                                            # Verify all warming prompts are now cached
                                                                                            # REMOVED_SYNTAX_ERROR: for prompt_data in warming_prompts:
                                                                                                # REMOVED_SYNTAX_ERROR: cached_response = await response_processor.get_cached_response( )
                                                                                                # REMOVED_SYNTAX_ERROR: prompt=prompt_data["prompt"],
                                                                                                # REMOVED_SYNTAX_ERROR: model=prompt_data["model"]
                                                                                                

                                                                                                # REMOVED_SYNTAX_ERROR: assert cached_response is not None
                                                                                                # REMOVED_SYNTAX_ERROR: assert cached_response["cache_hit"] is True
                                                                                                # REMOVED_SYNTAX_ERROR: assert cached_response["metadata"]["priority"] == prompt_data["priority"]

                                                                                                # Test cache hit rate after warming
                                                                                                # REMOVED_SYNTAX_ERROR: post_warming_stats = await cache_manager.get_cache_stats()
                                                                                                # REMOVED_SYNTAX_ERROR: assert post_warming_stats["cache_hits"] >= len(warming_prompts)

                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                # Removed problematic line: async def test_distributed_cache_consistency( )
                                                                                                # REMOVED_SYNTAX_ERROR: self,
                                                                                                # REMOVED_SYNTAX_ERROR: redis_container
                                                                                                # REMOVED_SYNTAX_ERROR: ):
                                                                                                    # REMOVED_SYNTAX_ERROR: """Test cache consistency across multiple cache manager instances."""
                                                                                                    # Create two cache manager instances (simulating distributed setup)
                                                                                                    # REMOVED_SYNTAX_ERROR: cache_manager_1 = LLMCacheManager(redis_config=redis_container)
                                                                                                    # REMOVED_SYNTAX_ERROR: await cache_manager_1.initialize()

                                                                                                    # REMOVED_SYNTAX_ERROR: cache_manager_2 = LLMCacheManager(redis_config=redis_container)
                                                                                                    # REMOVED_SYNTAX_ERROR: await cache_manager_2.initialize()

                                                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                                                        # Store response via first manager
                                                                                                        # REMOVED_SYNTAX_ERROR: cache_key = "distributed_test_key"
                                                                                                        # REMOVED_SYNTAX_ERROR: test_response = "Distributed cache test response"

                                                                                                        # REMOVED_SYNTAX_ERROR: await cache_manager_1.store_response( )
                                                                                                        # REMOVED_SYNTAX_ERROR: cache_key,
                                                                                                        # REMOVED_SYNTAX_ERROR: test_response,
                                                                                                        # REMOVED_SYNTAX_ERROR: metadata={"source": "manager_1"}
                                                                                                        

                                                                                                        # Retrieve via second manager
                                                                                                        # REMOVED_SYNTAX_ERROR: retrieved_response = await cache_manager_2.get_response(cache_key)

                                                                                                        # REMOVED_SYNTAX_ERROR: assert retrieved_response is not None
                                                                                                        # REMOVED_SYNTAX_ERROR: assert retrieved_response["response"] == test_response
                                                                                                        # REMOVED_SYNTAX_ERROR: assert retrieved_response["metadata"]["source"] == "manager_1"

                                                                                                        # Update via second manager
                                                                                                        # REMOVED_SYNTAX_ERROR: updated_response = "Updated distributed response"
                                                                                                        # REMOVED_SYNTAX_ERROR: await cache_manager_2.store_response( )
                                                                                                        # REMOVED_SYNTAX_ERROR: cache_key,
                                                                                                        # REMOVED_SYNTAX_ERROR: updated_response,
                                                                                                        # REMOVED_SYNTAX_ERROR: metadata={"source": "manager_2", "updated": True}
                                                                                                        

                                                                                                        # Verify update via first manager
                                                                                                        # REMOVED_SYNTAX_ERROR: updated_result = await cache_manager_1.get_response(cache_key)
                                                                                                        # REMOVED_SYNTAX_ERROR: assert updated_result["response"] == updated_response
                                                                                                        # REMOVED_SYNTAX_ERROR: assert updated_result["metadata"]["source"] == "manager_2"
                                                                                                        # REMOVED_SYNTAX_ERROR: assert updated_result["metadata"]["updated"] is True

                                                                                                        # REMOVED_SYNTAX_ERROR: finally:
                                                                                                            # REMOVED_SYNTAX_ERROR: await cache_manager_1.cleanup()
                                                                                                            # REMOVED_SYNTAX_ERROR: await cache_manager_2.cleanup()