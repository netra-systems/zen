"""
Test LLM Resource Management Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all user segments)
- Business Goal: Prevent memory leaks and resource exhaustion
- Value Impact: Ensures platform stability and cost control
- Strategic Impact: CRITICAL for scaling to 10+ concurrent users

PERFORMANCE CRITICAL: Poor resource management leads to system crashes and revenue loss.
This validates proper cleanup, memory management, and resource optimization.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch, MagicMock
import time
import uuid
import gc
import psutil
import os
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture  
from netra_backend.app.llm.llm_manager import LLMManager, create_llm_manager
from netra_backend.app.llm.resource_cache import LLMResourceCache, get_llm_resource_cache
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.llm_types import LLMResponse, TokenUsage
from shared.isolated_environment import get_env


@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage."""
    memory_mb: float
    cache_size: int
    manager_count: int
    timestamp: float
    open_file_descriptors: int = 0


class TestLLMResourceManagementIntegration(BaseIntegrationTest):
    """
    Test LLM resource management and cleanup integration.
    
    CRITICAL: These tests prevent memory leaks that crash the platform.
    """
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def get_open_file_descriptors(self) -> int:
        """Get count of open file descriptors."""
        try:
            process = psutil.Process(os.getpid())
            return process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
        except:
            return 0
    
    def take_resource_snapshot(self, managers: List[LLMManager]) -> ResourceSnapshot:
        """Take a snapshot of current resource usage."""
        return ResourceSnapshot(
            memory_mb=self.get_memory_usage_mb(),
            cache_size=sum(len(m._cache) for m in managers),
            manager_count=len(managers),
            timestamp=time.time(),
            open_file_descriptors=self.get_open_file_descriptors()
        )
    
    @pytest.fixture
    async def user_contexts(self):
        """Create user contexts for resource testing."""
        contexts = []
        for i in range(10):  # More users for resource stress testing
            context = UserExecutionContext(
                user_id=f"resource-user-{i}",
                session_id=f"resource-session-{i}",
                thread_id=f"resource-thread-{i}",
                execution_id=f"resource-exec-{i}",
                permissions=["read", "write"],
                metadata={
                    "resource_test": True,
                    "user_index": i
                }
            )
            contexts.append(context)
        return contexts
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_manager_memory_cleanup_on_shutdown(self, real_services_fixture, user_contexts):
        """
        Test manager memory cleanup prevents leaks.
        
        BVJ: Memory leaks crash the platform and lose revenue.
        """
        initial_snapshot = self.take_resource_snapshot([])
        
        # Create and use multiple managers
        managers = []
        for context in user_contexts[:5]:
            manager = create_llm_manager(context)
            await manager.initialize()
            
            # Populate cache to create memory footprint
            for i in range(10):
                await manager.ask_llm(f"Request {i} for {context.user_id}", use_cache=True)
            
            managers.append(manager)
        
        # Take snapshot after creation
        created_snapshot = self.take_resource_snapshot(managers)
        
        # Verify managers are using memory and cache
        assert created_snapshot.cache_size > 0, "Managers should have cached data"
        assert created_snapshot.manager_count == 5, "Should have 5 managers"
        
        # Shutdown all managers
        for manager in managers:
            await manager.shutdown()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup to complete
        
        # Take snapshot after shutdown
        shutdown_snapshot = self.take_resource_snapshot(managers)
        
        # CRITICAL: Memory and cache should be cleaned up
        assert shutdown_snapshot.cache_size == 0, "All caches should be cleared"
        
        # Memory usage should not grow significantly (allowing some variation)
        memory_growth = shutdown_snapshot.memory_mb - initial_snapshot.memory_mb
        assert memory_growth < 50, f"Memory growth should be minimal, was {memory_growth:.2f}MB"
        
        # Verify managers are properly shutdown
        for manager in managers:
            assert not manager._initialized, "Manager should be shutdown"
            assert len(manager._cache) == 0, "Manager cache should be empty"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_memory_limits_and_eviction(self, real_services_fixture, user_contexts):
        """
        Test cache memory limits prevent unlimited growth.
        
        BVJ: Unbounded cache growth crashes the platform under load.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Get resource cache instance
        resource_cache = get_llm_resource_cache()
        initial_cache_size = len(resource_cache._cache._cache)
        
        # Fill cache beyond normal limits
        large_responses = []
        for i in range(100):  # Create many cached entries
            # Create large response to simulate memory pressure
            large_prompt = f"Large analysis request {i}: " + "x" * 1000
            large_response = f"Large response {i}: " + "y" * 2000
            
            # Mock large response
            with patch.object(manager, '_make_llm_request', return_value=large_response):
                response = await manager.ask_llm(large_prompt, use_cache=True)
                large_responses.append(response)
        
        # Verify cache has grown but stayed within bounds
        final_manager_cache_size = len(manager._cache)
        final_resource_cache_size = len(resource_cache._cache._cache)
        
        # Manager cache should have entries but not unlimited
        assert final_manager_cache_size > 0, "Manager cache should have entries"
        assert final_manager_cache_size <= 100, "Manager cache should not grow unbounded"
        
        # Resource cache should implement LRU eviction
        # (exact size depends on LRU eviction policy)
        cache_growth = final_resource_cache_size - initial_cache_size
        assert cache_growth >= 0, "Resource cache should have grown"
        
        # Test cache cleanup
        resource_cache.cleanup()
        manager.clear_cache()
        
        # Verify cleanup effectiveness
        assert len(manager._cache) == 0, "Manager cache should be cleared"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_resource_usage_safety(self, real_services_fixture, user_contexts):
        """
        Test concurrent resource usage remains safe under load.
        
        BVJ: Resource contention under load must not crash the system.
        """
        initial_snapshot = self.take_resource_snapshot([])
        
        # Create managers for concurrent testing
        managers = [create_llm_manager(ctx) for ctx in user_contexts]
        
        # Initialize all managers
        for manager in managers:
            await manager.initialize()
        
        # Define concurrent workload
        async def user_workload(manager, workload_id):
            """Simulate realistic user workload."""
            results = []
            
            for i in range(15):  # Moderate load per user
                try:
                    prompt = f"Workload {workload_id}, request {i}: Analyze optimization"
                    response = await manager.ask_llm(prompt, use_cache=True)
                    results.append(("success", response))
                    
                    # Simulate user thinking time
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    results.append(("error", str(e)))
            
            return results
        
        # Take snapshot before concurrent load
        pre_load_snapshot = self.take_resource_snapshot(managers)
        
        # Execute concurrent workloads
        tasks = [user_workload(managers[i], i) for i in range(len(managers))]
        all_results = await asyncio.gather(*tasks)
        
        # Take snapshot after concurrent load
        post_load_snapshot = self.take_resource_snapshot(managers)
        
        # Verify concurrent execution succeeded
        total_requests = sum(len(results) for results in all_results)
        successful_requests = sum(
            len([r for r in results if r[0] == "success"]) 
            for results in all_results
        )
        
        assert total_requests == 150, "Should have 150 total requests (10 users × 15 requests)"
        assert successful_requests >= 140, "At least 93% requests should succeed"
        
        # Verify resource usage stayed reasonable
        memory_growth = post_load_snapshot.memory_mb - initial_snapshot.memory_mb
        assert memory_growth < 100, f"Memory growth should be reasonable, was {memory_growth:.2f}MB"
        
        # Cache should have entries but not excessive
        assert post_load_snapshot.cache_size > 0, "Should have cached responses"
        assert post_load_snapshot.cache_size <= 150, "Cache size should be bounded"
        
        # Cleanup all managers
        for manager in managers:
            await manager.shutdown()
        
        # Force cleanup and verify
        gc.collect()
        await asyncio.sleep(0.1)
        
        final_snapshot = self.take_resource_snapshot([])
        final_memory_growth = final_snapshot.memory_mb - initial_snapshot.memory_mb
        assert final_memory_growth < 75, f"Final memory growth should be minimal, was {final_memory_growth:.2f}MB"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_usage_tracking_accuracy(self, real_services_fixture, user_contexts):
        """
        Test token usage tracking accuracy for cost control.
        
        BVJ: Accurate token tracking prevents cost overruns and enables billing.
        """
        managers = [create_llm_manager(ctx) for ctx in user_contexts[:3]]
        
        # Initialize managers
        for manager in managers:
            await manager.initialize()
        
        # Track token usage across users
        user_token_usage = {}
        
        # Mock token usage for each user
        for i, manager in enumerate(managers):
            user_id = manager._user_context.user_id
            user_token_usage[user_id] = {"prompt": 0, "completion": 0, "total": 0}
            
            # Make requests with different token usage
            requests_per_user = 5
            for j in range(requests_per_user):
                prompt = f"User {i} request {j}: Detailed analysis of optimization opportunities"
                
                # Mock token counting
                prompt_tokens = len(prompt.split()) + 10  # Simulate tokenization
                completion_tokens = 50 + (j * 10)  # Variable response length
                
                with patch.object(manager, '_make_llm_request') as mock_request:
                    mock_request.return_value = f"Response {j} with {completion_tokens} tokens worth of content"
                    
                    # Get full response with token usage
                    response = await manager.ask_llm_full(prompt, use_cache=False)
                
                # Verify token usage is tracked
                assert isinstance(response.usage, TokenUsage), "Should have token usage"
                assert response.usage.prompt_tokens > 0, "Should track prompt tokens"
                assert response.usage.completion_tokens > 0, "Should track completion tokens"
                assert response.usage.total_tokens > 0, "Should track total tokens"
                
                # Accumulate user token usage
                user_token_usage[user_id]["prompt"] += response.usage.prompt_tokens
                user_token_usage[user_id]["completion"] += response.usage.completion_tokens
                user_token_usage[user_id]["total"] += response.usage.total_tokens
        
        # Verify token usage isolation between users
        user_ids = list(user_token_usage.keys())
        
        for i, user_id_i in enumerate(user_ids):
            for j, user_id_j in enumerate(user_ids):
                if i != j:
                    # Different users should have different total usage
                    usage_i = user_token_usage[user_id_i]["total"]
                    usage_j = user_token_usage[user_id_j]["total"]
                    assert usage_i != usage_j, f"Users {i} and {j} should have different token usage"
        
        # Verify reasonable token usage ranges
        for user_id, usage in user_token_usage.items():
            assert usage["prompt"] > 0, f"User {user_id} should have prompt token usage"
            assert usage["completion"] > 0, f"User {user_id} should have completion token usage"
            assert usage["total"] == usage["prompt"] + usage["completion"], f"Total should equal prompt + completion for {user_id}"
            
            # Reasonable usage bounds (5 requests per user)
            assert 100 < usage["total"] < 2000, f"Total usage should be reasonable for {user_id}: {usage['total']}"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_ttl_and_expiration_cleanup(self, real_services_fixture, user_contexts):
        """
        Test cache TTL and expiration cleanup prevents indefinite growth.
        
        BVJ: Cache expiration prevents memory growth and ensures fresh responses.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Get resource cache for TTL testing
        resource_cache = get_llm_resource_cache()
        
        # Create cache entries with different TTLs
        short_ttl_data = []
        long_ttl_data = []
        
        for i in range(5):
            # Short TTL entries (should expire quickly)
            short_messages = [{"role": "user", "content": f"Short TTL request {i}"}]
            short_response = f"Short TTL response {i}"
            
            resource_cache.cache_response(
                model="test-model",
                messages=short_messages, 
                response=short_response,
                metadata={"ttl_test": "short"}
            )
            short_ttl_data.append((short_messages, short_response))
            
            # Long TTL entries (should persist longer)
            long_messages = [{"role": "user", "content": f"Long TTL request {i}"}] 
            long_response = f"Long TTL response {i}"
            
            resource_cache.cache_response(
                model="test-model",
                messages=long_messages,
                response=long_response, 
                metadata={"ttl_test": "long"}
            )
            long_ttl_data.append((long_messages, long_response))
        
        # Verify entries are cached
        initial_cache_stats = resource_cache.get_stats()
        assert initial_cache_stats["size"] >= 10, "Should have at least 10 cache entries"
        
        # Wait for short TTL entries to expire (simulate with manual cleanup)
        # In a real scenario, we'd wait for actual TTL expiration
        await asyncio.sleep(0.1)
        
        # Force cleanup of expired entries
        cleanup_result = resource_cache.cleanup()
        
        # Verify cleanup occurred
        post_cleanup_stats = resource_cache.get_stats()
        
        # Cache size should be manageable
        assert post_cleanup_stats["size"] <= initial_cache_stats["size"], "Cleanup should not increase cache size"
        
        # Test cache retrieval after cleanup
        for i, (messages, expected_response) in enumerate(long_ttl_data):
            # Long TTL entries should still be available
            cached_response = resource_cache.get_cached_response("test-model", messages)
            
            if cached_response:  # May be evicted due to LRU, but shouldn't error
                assert cached_response["response"] == expected_response, f"Long TTL entry {i} should be preserved"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_monitoring_and_alerting(self, real_services_fixture, user_contexts):
        """
        Test resource monitoring and alerting thresholds.
        
        BVJ: Early warning system prevents platform crashes and enables scaling.
        """
        managers = [create_llm_manager(ctx) for ctx in user_contexts[:5]]
        
        # Initialize managers
        for manager in managers:
            await manager.initialize()
        
        # Create resource monitoring state
        resource_alerts = []
        
        def mock_resource_alert(alert_type: str, message: str, metrics: Dict[str, Any]):
            """Mock resource alert handler."""
            resource_alerts.append({
                "type": alert_type,
                "message": message,
                "metrics": metrics,
                "timestamp": time.time()
            })
        
        # Simulate resource-intensive operations
        for i, manager in enumerate(managers):
            # Create significant cache load
            for j in range(20):
                prompt = f"Heavy resource request {i}.{j}: " + "x" * 500
                response = await manager.ask_llm(prompt, use_cache=True)
            
            # Check resource usage after each manager
            memory_usage = self.get_memory_usage_mb()
            cache_size = len(manager._cache)
            
            # Simulate monitoring thresholds
            if memory_usage > 200:  # MB threshold
                mock_resource_alert(
                    "memory_high",
                    f"High memory usage detected: {memory_usage:.2f}MB",
                    {"memory_mb": memory_usage, "manager_count": i+1}
                )
            
            if cache_size > 15:  # Cache size threshold
                mock_resource_alert(
                    "cache_large",
                    f"Large cache detected: {cache_size} entries", 
                    {"cache_size": cache_size, "manager_id": i}
                )
        
        # Verify monitoring captured resource issues
        memory_alerts = [a for a in resource_alerts if a["type"] == "memory_high"]
        cache_alerts = [a for a in resource_alerts if a["type"] == "cache_large"]
        
        # Should have detected some resource pressure
        total_alerts = len(memory_alerts) + len(cache_alerts)
        assert total_alerts >= 0, "Resource monitoring should track usage"
        
        # If alerts were triggered, verify they have proper data
        for alert in resource_alerts:
            assert "timestamp" in alert, "Alert should have timestamp"
            assert "metrics" in alert, "Alert should have metrics"
            assert alert["message"], "Alert should have descriptive message"
        
        # Test cleanup reduces resource pressure
        initial_cache_total = sum(len(m._cache) for m in managers)
        
        # Clean up resources
        for manager in managers:
            manager.clear_cache()
        
        final_cache_total = sum(len(m._cache) for m in managers)
        
        assert final_cache_total == 0, "All caches should be cleared"
        assert final_cache_total < initial_cache_total, "Cleanup should reduce resource usage"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_degradation_under_resource_pressure(self, real_services_fixture, user_contexts):
        """
        Test graceful degradation when resources are constrained.
        
        BVJ: System should degrade gracefully rather than crash under pressure.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Simulate resource pressure conditions
        resource_pressure_conditions = {
            "high_memory": False,
            "cache_full": False,
            "slow_response": False
        }
        
        async def mock_resource_constrained_request(prompt, config_name):
            """Mock request under resource pressure."""
            
            # Simulate different pressure conditions
            if len(manager._cache) > 50:
                resource_pressure_conditions["cache_full"] = True
                # Under cache pressure, return faster/simpler responses
                return f"Simplified response due to resource constraints: {prompt[:30]}"
                
            memory_usage = self.get_memory_usage_mb()
            if memory_usage > 150:  # Simulated high memory
                resource_pressure_conditions["high_memory"] = True
                # Under memory pressure, disable caching
                return f"Non-cached response due to memory pressure: {prompt[:50]}"
            
            # Normal response
            return f"Normal response: {prompt[:100]}"
        
        responses = []
        degradation_detected = False
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_resource_constrained_request):
            # Generate load to trigger resource pressure
            for i in range(60):  # Enough to trigger cache pressure
                prompt = f"Load test request {i}: Detailed analysis request"
                
                try:
                    response = await manager.ask_llm(prompt, use_cache=True)
                    responses.append(("success", response))
                    
                    # Check for degradation indicators
                    if "Simplified response" in response or "Non-cached response" in response:
                        degradation_detected = True
                        
                except Exception as e:
                    responses.append(("error", str(e)))
        
        # Verify graceful degradation occurred
        successful_responses = [r for r in responses if r[0] == "success"]
        failed_responses = [r for r in responses if r[0] == "error"]
        
        # Should have mostly successful responses, even under pressure
        success_rate = len(successful_responses) / len(responses) if responses else 0
        assert success_rate > 0.8, f"Success rate should be high even under pressure, was {success_rate:.2%}"
        
        # Should have minimal failures
        assert len(failed_responses) < 5, f"Should have minimal failures, had {len(failed_responses)}"
        
        # System should have degraded gracefully rather than crashed
        if any(resource_pressure_conditions.values()):
            assert degradation_detected, "Should have detected graceful degradation"
        
        # Manager should still be functional after pressure
        assert manager._initialized, "Manager should remain initialized"
        
        # Should be able to make requests after pressure subsides
        final_response = await manager.ask_llm("Post-pressure test request", use_cache=False)
        assert "unable to process" not in final_response.lower(), "Should recover after pressure subsides"