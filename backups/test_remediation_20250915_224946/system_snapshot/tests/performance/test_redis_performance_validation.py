"""
Redis Performance Validation Test Suite

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: Chat Performance & Scalability (90% of platform value)
- Value Impact: Ensures Redis operations don't bottleneck real-time chat
- Strategic Impact: Validates performance for $500K+ ARR scalability

This test suite validates:
1. Redis connection pool efficiency under load
2. Auto-reconnection performance characteristics
3. Circuit breaker overhead and recovery times
4. Multi-user concurrent operation performance
5. WebSocket event delivery performance with Redis state
6. Memory and connection leak prevention

CRITICAL: Uses REAL Redis services (non-Docker) for accurate performance metrics
Performance thresholds based on chat functionality requirements
"""

import asyncio
import pytest
import time
import json
import uuid
import statistics
import psutil
import gc
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Redis SSOT imports
from netra_backend.app.redis_manager import redis_manager, RedisManager, UserCacheManager

# Shared utilities
from shared.isolated_environment import get_env

# Logging
import logging
logger = logging.getLogger(__name__)


class TestRedisPerformanceValidation(SSotAsyncTestCase):
    """Test Redis performance characteristics for chat functionality."""
    
    async def asyncSetUp(self):
        """Set up test environment for Redis performance validation."""
        await super().asyncSetUp()
        
        # Configure test environment
        self.test_env = {
            "TESTING": "true",
            "ENVIRONMENT": "test",
            "TEST_DISABLE_REDIS": "false",
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in self.test_env.items():
            self.set_env_var(key, value)
        
        # Initialize Redis manager
        await redis_manager.initialize()
        
        # Performance test session
        self.perf_session_id = f"perf_{uuid.uuid4().hex[:8]}"
        self.performance_metrics = {}
        
        # Initialize user cache manager for testing
        self.user_cache = UserCacheManager(redis_manager)
        
        logger.info(f"Redis performance test session: {self.perf_session_id}")
    
    async def asyncTearDown(self):
        """Clean up Redis performance test state."""
        try:
            # Clean up test data
            if redis_manager.is_connected:
                test_keys = await redis_manager.keys(f"perf:{self.perf_session_id}:*")
                for key in test_keys:
                    await redis_manager.delete(key)
            
            # Log performance summary
            if self.performance_metrics:
                logger.info(f"Performance Test Summary: {json.dumps(self.performance_metrics, indent=2)}")
            
        except Exception as e:
            logger.debug(f"Performance cleanup error (non-critical): {e}")
        
        await super().asyncTearDown()
    
    async def test_redis_connection_performance(self):
        """Test Redis connection establishment and basic operation performance."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping connection performance test")
        
        # Measure connection status check performance
        connection_checks = 100
        start_time = time.time()
        
        for _ in range(connection_checks):
            _ = redis_manager.is_connected
        
        connection_check_time = time.time() - start_time
        avg_connection_check = connection_check_time / connection_checks
        
        # Connection status check should be very fast (< 1ms per check)
        self.assertLess(avg_connection_check, 0.001, "Connection status check should be < 1ms")
        
        # Measure get_client performance
        client_gets = 50
        start_time = time.time()
        
        for _ in range(client_gets):
            client = await redis_manager.get_client()
            self.assertIsNotNone(client, "Client should be available")
        
        client_get_time = time.time() - start_time
        avg_client_get = client_get_time / client_gets
        
        # get_client should be fast (< 10ms per call for chat responsiveness)
        self.assertLess(avg_client_get, 0.010, "get_client should be < 10ms for chat responsiveness")
        
        self.performance_metrics["connection_performance"] = {
            "avg_connection_check_ms": avg_connection_check * 1000,
            "avg_client_get_ms": avg_client_get * 1000,
            "total_connection_checks": connection_checks,
            "total_client_gets": client_gets
        }
    
    async def test_redis_basic_operation_performance(self):
        """Test basic Redis operation performance for chat functionality."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping basic operation performance test")
        
        # Test set/get/delete performance
        operations_count = 100
        test_data = {
            "user_id": "perf_test_user",
            "agent_state": "processing",
            "websocket_connected": True,
            "session_data": "performance_test_data"
        }
        test_value = json.dumps(test_data)
        
        # Measure SET operations
        set_times = []
        for i in range(operations_count):
            start_time = time.time()
            key = f"perf:{self.perf_session_id}:set_test:{i}"
            result = await redis_manager.set(key, test_value, ex=60)
            set_times.append(time.time() - start_time)
            self.assertTrue(result, f"Set operation {i} should succeed")
        
        # Measure GET operations
        get_times = []
        for i in range(operations_count):
            start_time = time.time()
            key = f"perf:{self.perf_session_id}:set_test:{i}"
            value = await redis_manager.get(key)
            get_times.append(time.time() - start_time)
            self.assertEqual(value, test_value, f"Get operation {i} should return correct value")
        
        # Measure DELETE operations
        delete_times = []
        for i in range(operations_count):
            start_time = time.time()
            key = f"perf:{self.perf_session_id}:set_test:{i}"
            result = await redis_manager.delete(key)
            delete_times.append(time.time() - start_time)
            self.assertTrue(result, f"Delete operation {i} should succeed")
        
        # Calculate performance statistics
        avg_set = statistics.mean(set_times) * 1000  # Convert to ms
        avg_get = statistics.mean(get_times) * 1000
        avg_delete = statistics.mean(delete_times) * 1000
        
        p95_set = statistics.quantiles(set_times, n=20)[18] * 1000  # 95th percentile
        p95_get = statistics.quantiles(get_times, n=20)[18] * 1000
        p95_delete = statistics.quantiles(delete_times, n=20)[18] * 1000
        
        # Performance assertions for chat functionality
        self.assertLess(avg_set, 5.0, "Average SET should be < 5ms for chat responsiveness")
        self.assertLess(avg_get, 3.0, "Average GET should be < 3ms for chat responsiveness")
        self.assertLess(avg_delete, 5.0, "Average DELETE should be < 5ms for cleanup efficiency")
        
        self.assertLess(p95_set, 15.0, "95th percentile SET should be < 15ms")
        self.assertLess(p95_get, 10.0, "95th percentile GET should be < 10ms")
        self.assertLess(p95_delete, 15.0, "95th percentile DELETE should be < 15ms")
        
        self.performance_metrics["basic_operations"] = {
            "operations_count": operations_count,
            "avg_set_ms": avg_set,
            "avg_get_ms": avg_get,
            "avg_delete_ms": avg_delete,
            "p95_set_ms": p95_set,
            "p95_get_ms": p95_get,
            "p95_delete_ms": p95_delete
        }
    
    async def test_redis_concurrent_user_performance(self):
        """Test Redis performance under concurrent user load."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping concurrent user performance test")
        
        # Simulate concurrent users (chat scalability test)
        user_count = 10
        operations_per_user = 20
        
        async def simulate_user_operations(user_id: str) -> Dict[str, float]:
            """Simulate a user's Redis operations with timing."""
            user_times = {"set": [], "get": [], "user_cache": []}
            
            # User session data
            for i in range(operations_per_user):
                # Set operation
                start_time = time.time()
                key = f"perf:{self.perf_session_id}:user:{user_id}:op:{i}"
                value = json.dumps({"user": user_id, "operation": i, "timestamp": time.time()})
                await redis_manager.set(key, value, ex=120)
                user_times["set"].append(time.time() - start_time)
                
                # Get operation
                start_time = time.time()
                retrieved_value = await redis_manager.get(key)
                user_times["get"].append(time.time() - start_time)
                
                # User cache operation
                start_time = time.time()
                cache_key = f"cache_op_{i}"
                cache_value = f"user_{user_id}_cache_data_{i}"
                await self.user_cache.set_user_cache(user_id, cache_key, cache_value, ttl=120)
                user_times["user_cache"].append(time.time() - start_time)
                
                # Small delay to simulate realistic usage
                await asyncio.sleep(0.01)
            
            return user_times
        
        # Run concurrent user operations
        users = [f"user_{i}" for i in range(user_count)]
        start_time = time.time()
        
        user_results = await asyncio.gather(*[
            simulate_user_operations(user_id)
            for user_id in users
        ])
        
        total_time = time.time() - start_time
        
        # Aggregate performance metrics
        all_set_times = []
        all_get_times = []
        all_cache_times = []
        
        for user_times in user_results:
            all_set_times.extend(user_times["set"])
            all_get_times.extend(user_times["get"])
            all_cache_times.extend(user_times["user_cache"])
        
        # Calculate concurrent performance statistics
        total_operations = len(all_set_times) + len(all_get_times) + len(all_cache_times)
        operations_per_second = total_operations / total_time
        
        avg_set_concurrent = statistics.mean(all_set_times) * 1000
        avg_get_concurrent = statistics.mean(all_get_times) * 1000
        avg_cache_concurrent = statistics.mean(all_cache_times) * 1000
        
        # Performance assertions for concurrent users
        self.assertLess(avg_set_concurrent, 10.0, "Concurrent SET should be < 10ms")
        self.assertLess(avg_get_concurrent, 8.0, "Concurrent GET should be < 8ms")
        self.assertLess(avg_cache_concurrent, 12.0, "Concurrent user cache should be < 12ms")
        
        # Throughput should support chat scalability
        self.assertGreater(operations_per_second, 100.0, "Should handle > 100 ops/sec for chat scalability")
        
        self.performance_metrics["concurrent_users"] = {
            "user_count": user_count,
            "operations_per_user": operations_per_user,
            "total_operations": total_operations,
            "operations_per_second": operations_per_second,
            "avg_set_concurrent_ms": avg_set_concurrent,
            "avg_get_concurrent_ms": avg_get_concurrent,
            "avg_cache_concurrent_ms": avg_cache_concurrent,
            "total_test_time_seconds": total_time
        }
    
    async def test_redis_websocket_event_performance(self):
        """Test Redis performance for WebSocket event handling."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping WebSocket event performance test")
        
        # Simulate WebSocket event sequence performance
        event_count = 100
        events_per_session = 5  # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        
        event_storage_times = []
        event_retrieval_times = []
        
        for session_i in range(event_count // events_per_session):
            session_id = f"ws_session_{session_i}"
            
            # Store event sequence
            for event_i in range(events_per_session):
                event_data = {
                    "type": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"][event_i],
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "data": {"event_number": event_i, "session": session_i}
                }
                
                # Measure event storage
                start_time = time.time()
                event_key = f"perf:{self.perf_session_id}:event:{session_id}:{event_i}"
                await redis_manager.set(event_key, json.dumps(event_data), ex=300)
                event_storage_times.append(time.time() - start_time)
                
                # Measure event retrieval
                start_time = time.time()
                retrieved_event = await redis_manager.get(event_key)
                event_retrieval_times.append(time.time() - start_time)
                
                self.assertIsNotNone(retrieved_event, "Event should be retrievable")
        
        # Calculate WebSocket event performance
        avg_storage = statistics.mean(event_storage_times) * 1000
        avg_retrieval = statistics.mean(event_retrieval_times) * 1000
        
        p95_storage = statistics.quantiles(event_storage_times, n=20)[18] * 1000
        p95_retrieval = statistics.quantiles(event_retrieval_times, n=20)[18] * 1000
        
        # WebSocket events must be very fast for real-time chat
        self.assertLess(avg_storage, 3.0, "WebSocket event storage should be < 3ms")
        self.assertLess(avg_retrieval, 2.0, "WebSocket event retrieval should be < 2ms")
        self.assertLess(p95_storage, 8.0, "95th percentile event storage should be < 8ms")
        self.assertLess(p95_retrieval, 5.0, "95th percentile event retrieval should be < 5ms")
        
        self.performance_metrics["websocket_events"] = {
            "total_events": event_count,
            "avg_storage_ms": avg_storage,
            "avg_retrieval_ms": avg_retrieval,
            "p95_storage_ms": p95_storage,
            "p95_retrieval_ms": p95_retrieval
        }
    
    async def test_redis_circuit_breaker_performance_overhead(self):
        """Test circuit breaker performance overhead."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping circuit breaker performance test")
        
        # Measure operations with circuit breaker
        operations_count = 200
        
        # Measure circuit breaker check overhead
        circuit_check_times = []
        for _ in range(operations_count):
            start_time = time.time()
            can_execute = redis_manager._circuit_breaker.can_execute()
            circuit_check_times.append(time.time() - start_time)
            self.assertIsInstance(can_execute, bool)
        
        # Measure operations with circuit breaker overhead
        operation_times = []
        for i in range(operations_count):
            start_time = time.time()
            
            # This includes circuit breaker check overhead
            key = f"perf:{self.perf_session_id}:circuit:{i}"
            value = f"circuit_breaker_test_{i}"
            result = await redis_manager.set(key, value, ex=60)
            
            operation_times.append(time.time() - start_time)
            self.assertTrue(result, f"Operation {i} should succeed through circuit breaker")
        
        # Calculate circuit breaker overhead
        avg_circuit_check = statistics.mean(circuit_check_times) * 1000
        avg_operation_with_cb = statistics.mean(operation_times) * 1000
        
        # Circuit breaker overhead should be minimal
        self.assertLess(avg_circuit_check, 0.1, "Circuit breaker check should be < 0.1ms overhead")
        self.assertLess(avg_operation_with_cb, 8.0, "Operations with circuit breaker should be < 8ms")
        
        self.performance_metrics["circuit_breaker"] = {
            "avg_circuit_check_ms": avg_circuit_check,
            "avg_operation_with_cb_ms": avg_operation_with_cb,
            "operations_tested": operations_count
        }
    
    async def test_redis_auto_reconnection_performance(self):
        """Test auto-reconnection performance characteristics."""
        # Test reconnection timing
        if redis_manager.is_connected:
            # Measure force reconnection time
            start_time = time.time()
            reconnect_success = await redis_manager.force_reconnect()
            reconnect_time = time.time() - start_time
            
            if reconnect_success:
                # Reconnection should be fast for minimal chat disruption
                self.assertLess(reconnect_time, 2.0, "Force reconnection should be < 2 seconds")
                
                # Test post-reconnection operation performance
                post_reconnect_times = []
                for i in range(10):
                    start_time = time.time()
                    key = f"perf:{self.perf_session_id}:reconnect:{i}"
                    result = await redis_manager.set(key, f"post_reconnect_{i}", ex=60)
                    post_reconnect_times.append(time.time() - start_time)
                    self.assertTrue(result, f"Post-reconnection operation {i} should succeed")
                
                avg_post_reconnect = statistics.mean(post_reconnect_times) * 1000
                self.assertLess(avg_post_reconnect, 10.0, "Post-reconnection operations should be < 10ms")
                
                self.performance_metrics["auto_reconnection"] = {
                    "reconnect_time_seconds": reconnect_time,
                    "avg_post_reconnect_ms": avg_post_reconnect,
                    "reconnect_success": True
                }
            else:
                self.performance_metrics["auto_reconnection"] = {
                    "reconnect_success": False,
                    "note": "Reconnection failed in test environment"
                }
        else:
            self.skipTest("Redis not connected - skipping auto-reconnection performance test")
    
    async def test_redis_memory_usage_efficiency(self):
        """Test Redis manager memory usage and leak prevention."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        if redis_manager.is_connected:
            # Perform many operations to test for memory leaks
            operations_count = 500
            large_data = "x" * 1024  # 1KB of data per operation
            
            for i in range(operations_count):
                key = f"perf:{self.perf_session_id}:memory:{i}"
                value = f"large_data_{i}_{large_data}"
                
                await redis_manager.set(key, value, ex=60)
                
                # Periodically check if data exists
                if i % 50 == 0:
                    exists = await redis_manager.exists(key)
                    self.assertTrue(exists, f"Key {i} should exist")
            
            # Force garbage collection
            gc.collect()
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (< 50MB for test operations)
            self.assertLess(memory_increase, 50.0, "Memory increase should be < 50MB for test operations")
            
            # Clean up test data
            for i in range(operations_count):
                key = f"perf:{self.perf_session_id}:memory:{i}"
                await redis_manager.delete(key)
            
            self.performance_metrics["memory_usage"] = {
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "memory_increase_mb": memory_increase,
                "operations_count": operations_count
            }
        else:
            self.skipTest("Redis not connected - skipping memory usage test")


class TestRedisPerformanceScalability(SSotAsyncTestCase):
    """Test Redis performance scalability characteristics."""
    
    async def asyncSetUp(self):
        """Set up scalability test environment."""
        await super().asyncSetUp()
        
        self.set_env_var("TESTING", "true")
        self.set_env_var("ENVIRONMENT", "test")
        
        await redis_manager.initialize()
        
        self.scalability_session_id = f"scale_{uuid.uuid4().hex[:8]}"
        self.scalability_metrics = {}
    
    async def asyncTearDown(self):
        """Clean up scalability test state."""
        try:
            if redis_manager.is_connected:
                test_keys = await redis_manager.keys(f"scale:{self.scalability_session_id}:*")
                for key in test_keys:
                    await redis_manager.delete(key)
            
            if self.scalability_metrics:
                logger.info(f"Scalability Test Summary: {json.dumps(self.scalability_metrics, indent=2)}")
        except Exception as e:
            logger.debug(f"Scalability cleanup error (non-critical): {e}")
        
        await super().asyncTearDown()
    
    async def test_redis_throughput_scalability(self):
        """Test Redis throughput under increasing load."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping throughput scalability test")
        
        # Test increasing operation loads
        load_levels = [10, 50, 100, 200]  # Operations per load level
        throughput_results = {}
        
        for load in load_levels:
            start_time = time.time()
            
            # Concurrent operations at this load level
            async def perform_operations(op_id: int):
                key = f"scale:{self.scalability_session_id}:load_{load}:op_{op_id}"
                value = f"scalability_test_{load}_{op_id}"
                
                # Set and get operation
                await redis_manager.set(key, value, ex=120)
                retrieved = await redis_manager.get(key)
                return retrieved == value
            
            # Run operations concurrently
            results = await asyncio.gather(*[
                perform_operations(i) for i in range(load)
            ])
            
            load_time = time.time() - start_time
            throughput = load / load_time
            success_rate = sum(results) / len(results)
            
            throughput_results[load] = {
                "throughput_ops_per_sec": throughput,
                "success_rate": success_rate,
                "load_time_seconds": load_time
            }
            
            # All operations should succeed
            self.assertEqual(success_rate, 1.0, f"All operations should succeed at load {load}")
            
            # Throughput should scale reasonably
            self.assertGreater(throughput, 10.0, f"Throughput should be > 10 ops/sec at load {load}")
        
        # Verify throughput doesn't degrade dramatically with load
        throughput_10 = throughput_results[10]["throughput_ops_per_sec"]
        throughput_200 = throughput_results[200]["throughput_ops_per_sec"]
        
        # Throughput at 200 ops should be at least 30% of throughput at 10 ops
        throughput_ratio = throughput_200 / throughput_10
        self.assertGreater(throughput_ratio, 0.3, "Throughput should not degrade too much with load")
        
        self.scalability_metrics["throughput_scalability"] = throughput_results
    
    async def test_redis_user_isolation_scalability(self):
        """Test user isolation performance with increasing user count."""
        if not redis_manager.is_connected:
            self.skipTest("Redis not connected - skipping user isolation scalability test")
        
        user_counts = [5, 10, 20, 30]  # Increasing user loads
        isolation_results = {}
        
        for user_count in user_counts:
            user_cache = UserCacheManager(redis_manager)
            
            async def simulate_user_session(user_id: str):
                # Each user performs isolated operations
                operations = 10
                user_times = []
                
                for i in range(operations):
                    start_time = time.time()
                    cache_key = f"session_data_{i}"
                    cache_value = f"user_{user_id}_data_{i}"
                    
                    await user_cache.set_user_cache(user_id, cache_key, cache_value, ttl=120)
                    retrieved = await user_cache.get_user_cache(user_id, cache_key)
                    
                    user_times.append(time.time() - start_time)
                    
                    if retrieved != cache_value:
                        return False, user_times
                
                return True, user_times
            
            # Run concurrent user sessions
            users = [f"scale_user_{i}" for i in range(user_count)]
            start_time = time.time()
            
            results = await asyncio.gather(*[
                simulate_user_session(user_id) for user_id in users
            ])
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful_users = sum(1 for success, _ in results if success)
            all_times = [time for _, times in results for time in times]
            
            avg_operation_time = statistics.mean(all_times) * 1000  # ms
            
            isolation_results[user_count] = {
                "successful_users": successful_users,
                "total_users": user_count,
                "success_rate": successful_users / user_count,
                "avg_operation_time_ms": avg_operation_time,
                "total_test_time_seconds": total_time
            }
            
            # All users should succeed
            self.assertEqual(successful_users, user_count, f"All {user_count} users should succeed")
            
            # Operation times should remain reasonable
            self.assertLess(avg_operation_time, 20.0, f"Average operation time should be < 20ms with {user_count} users")
        
        self.scalability_metrics["user_isolation_scalability"] = isolation_results


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])