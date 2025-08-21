"""
L3-15: LLM Response Caching with Real Redis Integration Test

BVJ: Reduces LLM costs by 40% through intelligent caching of responses.
Critical for cost optimization and performance in AI workloads.

Tests LLM response caching with real Redis containers and cache strategies.
"""

import pytest
import asyncio
import docker
import time
import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis
from caching.llm_cache_manager import LLMCacheManager
from caching.cache_strategies import CacheStrategy
from llm.response_processor import LLMResponseProcessor


@pytest.mark.L3
class TestLLMResponseCachingRedisL3:
    """Test LLM response caching with real Redis."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def redis_container(self, docker_client):
        """Start Redis container for caching."""
        container = docker_client.containers.run(
            "redis:7-alpine",
            ports={'6379/tcp': None},
            detach=True,
            name="llm_cache_test_redis"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['6379/tcp'][0]['HostPort']
        
        # Wait for Redis to be ready
        await self._wait_for_redis(port)
        
        redis_config = {
            "host": "localhost",
            "port": int(port),
            "db": 0
        }
        
        yield redis_config
        
        container.stop()
        container.remove()
    
    async def _wait_for_redis(self, port: str, timeout: int = 30):
        """Wait for Redis to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                redis_client = aioredis.Redis(
                    host="localhost",
                    port=int(port),
                    decode_responses=True
                )
                await redis_client.ping()
                await redis_client.close()
                return
            except:
                await asyncio.sleep(0.5)
        raise TimeoutError(f"Redis not ready within {timeout}s")
    
    @pytest.fixture
    async def cache_manager(self, redis_container):
        """Create LLM cache manager with Redis backend."""
        manager = LLMCacheManager(redis_config=redis_container)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def response_processor(self, cache_manager):
        """Create LLM response processor with caching."""
        processor = LLMResponseProcessor(cache_manager=cache_manager)
        await processor.initialize()
        yield processor
        await processor.cleanup()
    
    @pytest.fixture
    async def mock_llm_responses(self):
        """Create mock LLM responses for testing."""
        responses = {
            "simple_question": {
                "prompt": "What is the capital of France?",
                "response": "The capital of France is Paris.",
                "model": "gpt-3.5-turbo",
                "tokens": 12,
                "cost": 0.00024
            },
            "complex_analysis": {
                "prompt": "Analyze the economic impact of renewable energy adoption",
                "response": "Renewable energy adoption has significant positive economic impacts including job creation, reduced energy costs, and increased energy independence...",
                "model": "gpt-4",
                "tokens": 350,
                "cost": 0.021
            },
            "code_generation": {
                "prompt": "Write a Python function to calculate fibonacci numbers",
                "response": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "model": "gpt-3.5-turbo",
                "tokens": 45,
                "cost": 0.0009
            }
        }
        return responses
    
    @pytest.mark.asyncio
    async def test_basic_cache_store_and_retrieve(
        self, 
        cache_manager, 
        mock_llm_responses
    ):
        """Test basic cache store and retrieve operations."""
        response_data = mock_llm_responses["simple_question"]
        
        # Generate cache key
        cache_key = cache_manager.generate_cache_key(
            prompt=response_data["prompt"],
            model=response_data["model"],
            parameters={}
        )
        
        # Store response in cache
        await cache_manager.store_response(
            cache_key,
            response_data["response"],
            metadata={
                "model": response_data["model"],
                "tokens": response_data["tokens"],
                "cost": response_data["cost"]
            }
        )
        
        # Retrieve response from cache
        cached_response = await cache_manager.get_response(cache_key)
        
        assert cached_response is not None
        assert cached_response["response"] == response_data["response"]
        assert cached_response["metadata"]["model"] == response_data["model"]
        assert cached_response["metadata"]["tokens"] == response_data["tokens"]
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_optimization(
        self, 
        cache_manager, 
        response_processor,
        mock_llm_responses
    ):
        """Test cache hit rate optimization with similar prompts."""
        # Store initial responses
        for response_key, response_data in mock_llm_responses.items():
            await response_processor.process_and_cache(
                prompt=response_data["prompt"],
                model=response_data["model"],
                response=response_data["response"],
                metadata={
                    "tokens": response_data["tokens"],
                    "cost": response_data["cost"]
                }
            )
        
        # Test exact match (should be cache hit)
        exact_match_result = await response_processor.get_cached_response(
            prompt=mock_llm_responses["simple_question"]["prompt"],
            model=mock_llm_responses["simple_question"]["model"]
        )
        
        assert exact_match_result is not None
        assert exact_match_result["cache_hit"] is True
        
        # Test similar prompt (should use semantic similarity)
        similar_prompt = "What's the capital city of France?"  # Similar to original
        similar_result = await response_processor.get_cached_response(
            prompt=similar_prompt,
            model=mock_llm_responses["simple_question"]["model"],
            similarity_threshold=0.8
        )
        
        # Should find similar cached response
        if similar_result:
            assert similar_result["similarity_score"] >= 0.8
        
        # Get cache statistics
        stats = await cache_manager.get_cache_stats()
        assert stats["total_requests"] >= 2
        assert stats["cache_hits"] >= 1
        assert stats["hit_rate"] > 0
    
    @pytest.mark.asyncio
    async def test_cache_expiration_and_ttl(
        self, 
        cache_manager, 
        mock_llm_responses
    ):
        """Test cache expiration and TTL functionality."""
        response_data = mock_llm_responses["complex_analysis"]
        
        # Store response with short TTL
        cache_key = cache_manager.generate_cache_key(
            prompt=response_data["prompt"],
            model=response_data["model"]
        )
        
        await cache_manager.store_response(
            cache_key,
            response_data["response"],
            metadata={"model": response_data["model"]},
            ttl=1  # 1 second TTL
        )
        
        # Immediate retrieval should work
        immediate_result = await cache_manager.get_response(cache_key)
        assert immediate_result is not None
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Should be expired now
        expired_result = await cache_manager.get_response(cache_key)
        assert expired_result is None
        
        # Verify TTL was set correctly
        ttl_info = await cache_manager.get_ttl_info(cache_key)
        assert ttl_info["expired"] is True
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_strategies(
        self, 
        cache_manager, 
        mock_llm_responses
    ):
        """Test different cache invalidation strategies."""
        # Store responses with different models
        for response_key, response_data in mock_llm_responses.items():
            cache_key = cache_manager.generate_cache_key(
                prompt=response_data["prompt"],
                model=response_data["model"]
            )
            
            await cache_manager.store_response(
                cache_key,
                response_data["response"],
                metadata={
                    "model": response_data["model"],
                    "category": "test_category"
                }
            )
        
        # Verify all responses are cached
        initial_count = await cache_manager.get_cache_count()
        assert initial_count >= 3
        
        # Test model-specific invalidation
        await cache_manager.invalidate_by_model("gpt-3.5-turbo")
        
        # Check that only gpt-4 responses remain
        remaining_responses = await cache_manager.get_cached_responses_by_model("gpt-4")
        assert len(remaining_responses) >= 1
        
        gpt35_responses = await cache_manager.get_cached_responses_by_model("gpt-3.5-turbo")
        assert len(gpt35_responses) == 0
        
        # Test category-based invalidation
        await cache_manager.invalidate_by_category("test_category")
        
        final_count = await cache_manager.get_cache_count()
        assert final_count == 0
    
    @pytest.mark.asyncio
    async def test_cost_optimization_tracking(
        self, 
        cache_manager, 
        response_processor,
        mock_llm_responses
    ):
        """Test cost optimization tracking through caching."""
        total_original_cost = 0
        total_cached_savings = 0
        
        # Process responses multiple times to simulate cache usage
        for _ in range(5):  # Simulate 5 identical requests
            for response_key, response_data in mock_llm_responses.items():
                result = await response_processor.process_request(
                    prompt=response_data["prompt"],
                    model=response_data["model"],
                    expected_response=response_data["response"],
                    cost=response_data["cost"]
                )
                
                total_original_cost += response_data["cost"]
                if result["from_cache"]:
                    total_cached_savings += response_data["cost"]
        
        # Get cost optimization stats
        cost_stats = await cache_manager.get_cost_optimization_stats()
        
        assert cost_stats["total_requests"] >= 15  # 3 responses × 5 iterations
        assert cost_stats["cached_requests"] > 0
        assert cost_stats["cost_savings"] > 0
        assert cost_stats["cost_savings_percentage"] > 0
        
        # Verify significant cost savings
        assert cost_stats["cost_savings_percentage"] >= 60  # Should save at least 60%
    
    @pytest.mark.asyncio
    async def test_semantic_similarity_caching(
        self, 
        cache_manager, 
        response_processor
    ):
        """Test semantic similarity-based caching."""
        # Store base response
        base_prompt = "How do I optimize database performance?"
        base_response = "To optimize database performance, you should: 1) Index frequently queried columns, 2) Optimize queries, 3) Monitor performance metrics..."
        
        await response_processor.process_and_cache(
            prompt=base_prompt,
            model="gpt-4",
            response=base_response,
            metadata={"tokens": 150, "cost": 0.009}
        )
        
        # Test semantically similar prompts
        similar_prompts = [
            "What are best practices for database optimization?",
            "How can I improve my database performance?",
            "Database performance optimization techniques",
            "Ways to make database queries faster"
        ]
        
        similarity_results = []
        for similar_prompt in similar_prompts:
            result = await response_processor.get_cached_response(
                prompt=similar_prompt,
                model="gpt-4",
                similarity_threshold=0.7
            )
            
            if result:
                similarity_results.append({
                    "prompt": similar_prompt,
                    "similarity_score": result["similarity_score"],
                    "cache_hit": True
                })
            else:
                similarity_results.append({
                    "prompt": similar_prompt,
                    "cache_hit": False
                })
        
        # Should find at least some similar matches
        cache_hits = [r for r in similarity_results if r["cache_hit"]]
        assert len(cache_hits) >= 2
        
        # Verify similarity scores are reasonable
        for hit in cache_hits:
            assert hit["similarity_score"] >= 0.7
    
    @pytest.mark.asyncio
    async def test_cache_size_management_and_eviction(
        self, 
        cache_manager
    ):
        """Test cache size management and eviction policies."""
        # Configure cache with size limits
        await cache_manager.configure_limits(
            max_entries=5,
            max_memory_mb=10,
            eviction_policy="lru"  # Least Recently Used
        )
        
        # Fill cache beyond limit
        for i in range(10):
            large_response = "x" * 1000  # 1KB response
            cache_key = f"test_key_{i}"
            
            await cache_manager.store_response(
                cache_key,
                large_response,
                metadata={"size": len(large_response)}
            )
        
        # Check that cache size is within limits
        cache_info = await cache_manager.get_cache_info()
        assert cache_info["entry_count"] <= 5
        assert cache_info["memory_usage_mb"] <= 10
        
        # Verify LRU eviction - access some keys to make them recently used
        for i in [7, 8, 9]:
            await cache_manager.get_response(f"test_key_{i}")
        
        # Add more entries to trigger eviction
        for i in range(10, 15):
            cache_key = f"test_key_{i}"
            await cache_manager.store_response(
                cache_key,
                "new_response",
                metadata={"size": 12}
            )
        
        # Recently accessed keys should still be present
        recent_keys_present = 0
        for i in [7, 8, 9]:
            result = await cache_manager.get_response(f"test_key_{i}")
            if result:
                recent_keys_present += 1
        
        assert recent_keys_present >= 2  # Most recent keys should remain
    
    @pytest.mark.asyncio
    async def test_cache_warming_and_preloading(
        self, 
        cache_manager, 
        response_processor
    ):
        """Test cache warming and preloading functionality."""
        # Define common prompts for warming
        warming_prompts = [
            {
                "prompt": "Explain machine learning concepts",
                "model": "gpt-4",
                "expected_response": "Machine learning is a subset of artificial intelligence...",
                "priority": "high"
            },
            {
                "prompt": "Best practices for API design",
                "model": "gpt-3.5-turbo", 
                "expected_response": "Good API design follows REST principles...",
                "priority": "medium"
            },
            {
                "prompt": "Python performance optimization tips",
                "model": "gpt-4",
                "expected_response": "To optimize Python performance: use list comprehensions...",
                "priority": "high"
            }
        ]
        
        # Warm the cache
        warming_results = await cache_manager.warm_cache(warming_prompts)
        
        assert warming_results["success"] is True
        assert warming_results["warmed_count"] == len(warming_prompts)
        
        # Verify all warming prompts are now cached
        for prompt_data in warming_prompts:
            cached_response = await response_processor.get_cached_response(
                prompt=prompt_data["prompt"],
                model=prompt_data["model"]
            )
            
            assert cached_response is not None
            assert cached_response["cache_hit"] is True
            assert cached_response["metadata"]["priority"] == prompt_data["priority"]
        
        # Test cache hit rate after warming
        post_warming_stats = await cache_manager.get_cache_stats()
        assert post_warming_stats["cache_hits"] >= len(warming_prompts)
    
    @pytest.mark.asyncio
    async def test_distributed_cache_consistency(
        self, 
        redis_container
    ):
        """Test cache consistency across multiple cache manager instances."""
        # Create two cache manager instances (simulating distributed setup)
        cache_manager_1 = LLMCacheManager(redis_config=redis_container)
        await cache_manager_1.initialize()
        
        cache_manager_2 = LLMCacheManager(redis_config=redis_container)
        await cache_manager_2.initialize()
        
        try:
            # Store response via first manager
            cache_key = "distributed_test_key"
            test_response = "Distributed cache test response"
            
            await cache_manager_1.store_response(
                cache_key,
                test_response,
                metadata={"source": "manager_1"}
            )
            
            # Retrieve via second manager
            retrieved_response = await cache_manager_2.get_response(cache_key)
            
            assert retrieved_response is not None
            assert retrieved_response["response"] == test_response
            assert retrieved_response["metadata"]["source"] == "manager_1"
            
            # Update via second manager
            updated_response = "Updated distributed response"
            await cache_manager_2.store_response(
                cache_key,
                updated_response,
                metadata={"source": "manager_2", "updated": True}
            )
            
            # Verify update via first manager
            updated_result = await cache_manager_1.get_response(cache_key)
            assert updated_result["response"] == updated_response
            assert updated_result["metadata"]["source"] == "manager_2"
            assert updated_result["metadata"]["updated"] is True
            
        finally:
            await cache_manager_1.cleanup()
            await cache_manager_2.cleanup()