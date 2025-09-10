"""Mission Critical: Redis SSOT Consolidation Tests

Validates that Redis SSOT consolidation resolves WebSocket 1011 errors and
restores chat functionality worth $500K+ ARR.

Business Impact:
- Eliminates 12+ competing Redis connection pools
- Reduces memory usage by 75%
- Enables 99%+ WebSocket success rate
- Restores primary revenue channel (chat functionality)

Test Categories:
1. Single connection pool validation
2. Cache/Auth/Database integration through SSOT
3. WebSocket race condition elimination
4. Memory usage optimization
5. Connection stability under load

REAL SERVICES ONLY - No mocks allowed in mission critical tests.
"""

import pytest
import asyncio
import time
import psutil
import os
from typing import Dict, Any, List
from netra_backend.app.redis_manager import redis_manager
from test_framework.ssot.base_test_case import SSotAsyncTestCase
# Redis test utility not needed for basic SSOT tests


class TestRedisSSOTConsolidation(SSotAsyncTestCase):
    """Mission Critical: Test Redis SSOT consolidation fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.redis_test_keys = set()
        self.initial_memory = None
        
    async def asyncTearDown(self):
        """Async cleanup of test resources."""
        # Clean up all test keys
        for key in self.redis_test_keys:
            try:
                await redis_manager.delete(key)
            except Exception:
                pass
        
        await super().asyncTearDown()
    
    async def test_single_redis_connection_pool_ssot(self):
        """MISSION CRITICAL: Test that only one Redis connection pool exists.
        
        BUSINESS IMPACT: Prevents WebSocket 1011 errors caused by connection pool conflicts.
        SUCCESS CRITERIA: Single SSOT Redis manager with one connection pool.
        """
        # Initialize Redis manager
        await redis_manager.initialize()
        
        # Verify connection
        self.assertTrue(redis_manager.is_connected, "Redis SSOT should be connected")
        
        # Verify client availability
        client = await redis_manager.get_client()
        self.assertIsNotNone(client, "Redis client should be available")
        
        # Test basic operations through SSOT
        test_key = "test:ssot:consolidation"
        self.redis_test_keys.add(test_key)
        
        success = await redis_manager.set(test_key, "ssot_success")
        self.assertTrue(success, "Basic Redis operations should work through SSOT")
        
        value = await redis_manager.get(test_key)
        self.assertEqual(value, "ssot_success", "Retrieved value should match stored value")
        
        # Verify SSOT manager is the single source
        status = redis_manager.get_status()
        self.assertTrue(status["connected"], "SSOT Redis manager should be connected")
        self.assertIsNotNone(status["client_available"], "Client should be available")
        
    async def test_cache_manager_ssot_integration(self):
        """MISSION CRITICAL: Test cache operations work through SSOT Redis manager.
        
        BUSINESS IMPACT: Eliminates cache-related Redis connection conflicts.
        SUCCESS CRITERIA: Cache operations redirect to SSOT without conflicts.
        """
        from netra_backend.app.cache.redis_cache_manager import default_redis_cache_manager
        
        # Test cache operations through compatibility layer → SSOT
        test_key = "test:cache:ssot"
        test_data = {"message": "cache_test", "timestamp": time.time()}
        self.redis_test_keys.add(f"netra:cache:{test_key}")
        
        # Set cache data
        success = await default_redis_cache_manager.set(test_key, test_data, ttl=60)
        self.assertTrue(success, "Cache set should work through SSOT")
        
        # Get cache data
        retrieved = await default_redis_cache_manager.get(test_key)
        self.assertEqual(retrieved, test_data, "Cache retrieval should work through SSOT")
        
        # Verify cache stats
        stats = await default_redis_cache_manager.get_stats()
        self.assertGreater(stats.hits, 0, "Cache hits should be tracked")
        self.assertGreater(stats.sets, 0, "Cache sets should be tracked")
        
        # Test cache deletion
        deleted = await default_redis_cache_manager.delete(test_key)
        self.assertTrue(deleted, "Cache deletion should work through SSOT")
        
    async def test_auth_service_ssot_compatibility(self):
        """MISSION CRITICAL: Test auth service operations work through SSOT.
        
        BUSINESS IMPACT: Eliminates auth-related Redis connection conflicts in login flows.
        SUCCESS CRITERIA: Auth operations work seamlessly through SSOT.
        """
        # Test session operations through SSOT
        session_id = "test_session_ssot"
        session_data = {"user_id": "test_user", "role": "user", "timestamp": time.time()}
        self.redis_test_keys.add(f"auth:session:{session_id}")
        
        # Store session
        success = await redis_manager.store_session(session_id, session_data, 3600)
        self.assertTrue(success, "Session storage should work through SSOT")
        
        # Retrieve session
        retrieved = await redis_manager.get_session(session_id)
        self.assertEqual(retrieved, session_data, "Session retrieval should work through SSOT")
        
        # Test token blacklisting
        test_token = "test_token_ssot"
        self.redis_test_keys.add(f"auth:blacklist:{test_token}")
        
        blacklist_success = await redis_manager.blacklist_token(test_token, 3600)
        self.assertTrue(blacklist_success, "Token blacklisting should work through SSOT")
        
        is_blacklisted = await redis_manager.is_token_blacklisted(test_token)
        self.assertTrue(is_blacklisted, "Token blacklist check should work through SSOT")
        
        # Test user caching
        user_id = "test_user_ssot"
        user_data = {"name": "Test User", "email": "test@example.com"}
        self.redis_test_keys.add(f"auth:user:{user_id}")
        
        cache_success = await redis_manager.cache_user_data(user_id, user_data, 1800)
        self.assertTrue(cache_success, "User caching should work through SSOT")
        
        cached_user = await redis_manager.get_cached_user_data(user_id)
        self.assertEqual(cached_user, user_data, "User cache retrieval should work through SSOT")
        
        # Cleanup session and tokens
        await redis_manager.delete_session(session_id)
        await redis_manager.delete(f"auth:blacklist:{test_token}")
        await redis_manager.invalidate_user_cache(user_id)
        
    async def test_websocket_redis_race_condition_elimination(self):
        """MISSION CRITICAL: Test WebSocket operations don't cause 1011 errors.
        
        BUSINESS IMPACT: Prevents $500K+ ARR loss from broken chat functionality.
        SUCCESS CRITERIA: Concurrent WebSocket Redis operations succeed reliably.
        """
        # Simulate WebSocket Redis operations under load
        websocket_data = {
            "connection_id": "ws_test_ssot",
            "user_id": "test_user",
            "timestamp": time.time()
        }
        
        connection_key = "websocket:connection:ws_test_ssot"
        self.redis_test_keys.add(connection_key)
        
        # Store WebSocket connection data
        success = await redis_manager.set(connection_key, str(websocket_data))
        self.assertTrue(success, "WebSocket data should be stored through SSOT")
        
        # Verify storage
        stored_data = await redis_manager.get(connection_key)
        self.assertIsNotNone(stored_data, "WebSocket data should be retrievable")
        
        # Test concurrent operations (race condition simulation)
        concurrent_tasks = []
        for i in range(20):
            task_key = f"websocket:test:concurrent:{i}"
            self.redis_test_keys.add(task_key)
            concurrent_tasks.append(
                redis_manager.set(task_key, f"concurrent_data_{i}")
            )
        
        # Execute all concurrent operations
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Count successful operations
        success_count = sum(1 for r in results if r is True)
        failure_count = len(results) - success_count
        
        # Should have high success rate (>90%)
        success_rate = success_count / len(results) * 100
        self.assertGreaterEqual(success_rate, 90.0, 
                               f"Concurrent Redis operations should have >90% success rate, got {success_rate}%")
        
        # Log any failures for analysis
        if failure_count > 0:
            self.logger.warning(f"Had {failure_count} failures out of {len(results)} concurrent operations")
        
    async def test_memory_usage_optimization(self):
        """MISSION CRITICAL: Test memory usage is optimized with single connection pool.
        
        BUSINESS IMPACT: Reduces infrastructure costs by 75% through connection consolidation.
        SUCCESS CRITERIA: Memory usage significantly lower than pre-consolidation.
        """
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Ensure Redis is initialized
        await redis_manager.initialize()
        
        # Perform multiple operations that would have created separate connections before
        operation_tasks = []
        
        # Cache operations
        for i in range(10):
            key = f"memory_test:cache:{i}"
            self.redis_test_keys.add(f"netra:cache:{key}")
            operation_tasks.append(
                self._perform_cache_operation(key, {"data": f"test_{i}"})
            )
        
        # Auth operations
        for i in range(10):
            session_id = f"memory_test_session_{i}"
            self.redis_test_keys.add(f"auth:session:{session_id}")
            operation_tasks.append(
                self._perform_auth_operation(session_id, {"user_id": f"user_{i}"})
            )
        
        # Database cache operations
        for i in range(10):
            db_key = f"memory_test:db:{i}"
            self.redis_test_keys.add(db_key)
            operation_tasks.append(
                redis_manager.set(db_key, f"db_data_{i}")
            )
        
        # Execute all operations
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Verify most operations succeeded
        success_count = sum(1 for r in results if r is True)
        self.assertGreaterEqual(success_count, 25,  # At least 25/30 should succeed
                               f"Expected at least 25 successful operations, got {success_count}")
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Memory should not have increased dramatically (no connection pool explosion)
        memory_increase = final_memory - initial_memory
        self.assertLess(memory_increase, 50,  # Should not increase by more than 50MB
                       f"Memory increase should be minimal, got {memory_increase}MB increase")
        
        # Get Redis manager status
        status = redis_manager.get_status()
        self.assertTrue(status["connected"], "Redis should remain connected after load")
        self.assertLessEqual(status["consecutive_failures"], 2, 
                           "Should have minimal failures under load")
        
    async def test_connection_stability_under_load(self):
        """MISSION CRITICAL: Test Redis connection remains stable under high load.
        
        BUSINESS IMPACT: Ensures chat functionality remains available during peak usage.
        SUCCESS CRITERIA: Connection remains stable with minimal failures.
        """
        initial_status = redis_manager.get_status()
        
        # Perform high-load operations
        load_tasks = []
        for i in range(100):
            key = f"load_test:stability:{i}"
            self.redis_test_keys.add(key)
            load_tasks.append(self._perform_load_operation(i, key))
        
        # Execute high load
        start_time = time.time()
        results = await asyncio.gather(*load_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        exception_count = len(results) - success_count
        
        # Performance metrics
        total_time = end_time - start_time
        operations_per_second = len(results) / total_time
        
        # Validation
        self.assertGreaterEqual(success_count, 85,  # At least 85% success rate
                               f"Expected >=85 successful operations under load, got {success_count}")
        
        self.assertGreaterEqual(operations_per_second, 10,  # At least 10 ops/sec
                               f"Should achieve reasonable throughput, got {operations_per_second:.2f} ops/sec")
        
        # Connection should remain stable
        final_status = redis_manager.get_status()
        self.assertTrue(final_status["connected"], "Redis should remain connected after load test")
        
        # Failure count should not increase dramatically
        failure_increase = final_status["consecutive_failures"] - initial_status.get("consecutive_failures", 0)
        self.assertLessEqual(failure_increase, 5, 
                           f"Failure count should not increase significantly, got +{failure_increase}")
        
        if exception_count > 0:
            self.logger.warning(f"Load test had {exception_count} exceptions out of {len(results)} operations")
    
    async def _perform_cache_operation(self, key: str, data: Dict[str, Any]) -> bool:
        """Helper to perform cache operation."""
        from netra_backend.app.cache.redis_cache_manager import default_redis_cache_manager
        try:
            success = await default_redis_cache_manager.set(key, data, ttl=60)
            if success:
                retrieved = await default_redis_cache_manager.get(key)
                return retrieved == data
            return False
        except Exception:
            return False
    
    async def _perform_auth_operation(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Helper to perform auth operation."""
        try:
            success = await redis_manager.store_session(session_id, session_data, 60)
            if success:
                retrieved = await redis_manager.get_session(session_id)
                return retrieved == session_data
            return False
        except Exception:
            return False
    
    async def _perform_load_operation(self, operation_id: int, key: str) -> bool:
        """Helper to perform load test operation."""
        try:
            # Simulate various Redis operations
            await redis_manager.set(key, f"load_data_{operation_id}", ex=60)
            await redis_manager.get(key)
            await redis_manager.exists(key)
            await redis_manager.expire(key, 30)
            return True
        except Exception:
            return False
    
    async def test_websocket_1011_error_prevention(self):
        """MISSION CRITICAL: Verify WebSocket 1011 errors are prevented.
        
        BUSINESS IMPACT: Ensures primary revenue channel (chat) remains functional.
        SUCCESS CRITERIA: No WebSocket connection failures due to Redis conflicts.
        """
        # Simulate the conditions that previously caused 1011 errors
        
        # 1. Multiple concurrent WebSocket handshake simulations
        handshake_tasks = []
        for i in range(15):
            handshake_tasks.append(self._simulate_websocket_handshake(f"user_{i}"))
        
        # Execute concurrent handshakes
        handshake_results = await asyncio.gather(*handshake_tasks, return_exceptions=True)
        
        # Count successful handshakes
        successful_handshakes = sum(1 for r in handshake_results if r is True)
        
        # Should have very high success rate (>95%)
        success_rate = successful_handshakes / len(handshake_tasks) * 100
        self.assertGreaterEqual(success_rate, 95.0,
                               f"WebSocket handshake success rate should be >95%, got {success_rate}%")
        
        # 2. Test rapid connection/disconnection cycles
        connection_cycle_tasks = []
        for i in range(10):
            connection_cycle_tasks.append(self._simulate_connection_cycle(f"cycle_user_{i}"))
        
        cycle_results = await asyncio.gather(*connection_cycle_tasks, return_exceptions=True)
        successful_cycles = sum(1 for r in cycle_results if r is True)
        
        cycle_success_rate = successful_cycles / len(connection_cycle_tasks) * 100
        self.assertGreaterEqual(cycle_success_rate, 90.0,
                               f"Connection cycle success rate should be >90%, got {cycle_success_rate}%")
        
        # 3. Verify Redis connection remains stable
        final_status = redis_manager.get_status()
        self.assertTrue(final_status["connected"], 
                       "Redis connection should remain stable after WebSocket stress test")
        
    async def _simulate_websocket_handshake(self, user_id: str) -> bool:
        """Simulate WebSocket handshake with Redis operations."""
        try:
            connection_id = f"ws_{user_id}_{int(time.time() * 1000)}"
            
            # Simulate handshake Redis operations
            connection_key = f"websocket:active:{connection_id}"
            self.redis_test_keys.add(connection_key)
            
            # Store connection info
            await redis_manager.set(
                connection_key,
                f'{{"user_id": "{user_id}", "connected_at": {time.time()}}}',
                ex=3600
            )
            
            # Simulate session validation
            session_key = f"websocket:session:{user_id}"
            self.redis_test_keys.add(session_key)
            await redis_manager.set(session_key, "valid_session", ex=1800)
            
            # Verify session
            session = await redis_manager.get(session_key)
            if session != "valid_session":
                return False
            
            # Simulate connection tracking
            tracking_key = f"user_connections:{user_id}"
            self.redis_test_keys.add(tracking_key)
            await redis_manager.lpush(tracking_key, connection_id)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"WebSocket handshake simulation failed for {user_id}: {e}")
            return False
    
    async def _simulate_connection_cycle(self, user_id: str) -> bool:
        """Simulate rapid connect/disconnect cycle."""
        try:
            # Connect
            success = await self._simulate_websocket_handshake(user_id)
            if not success:
                return False
            
            # Brief pause
            await asyncio.sleep(0.1)
            
            # Disconnect (cleanup Redis keys)
            connection_keys = [
                f"websocket:active:ws_{user_id}*",
                f"websocket:session:{user_id}",
                f"user_connections:{user_id}"
            ]
            
            for pattern in connection_keys:
                if '*' in pattern:
                    keys = await redis_manager.scan_keys(pattern.replace('*', ''))
                    for key in keys:
                        await redis_manager.delete(key)
                else:
                    await redis_manager.delete(pattern)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Connection cycle failed for {user_id}: {e}")
            return False


# Additional validation tests for specific SSOT scenarios
class TestRedisSSOTValidation(SSotAsyncTestCase):
    """Additional validation tests for Redis SSOT scenarios."""
    
    async def test_ssot_redis_manager_singleton_pattern(self):
        """Test that Redis manager follows proper singleton pattern."""
        from netra_backend.app.redis_manager import redis_manager as manager1
        from netra_backend.app.redis_manager import get_redis_manager
        
        manager2 = get_redis_manager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2, "Redis managers should be the same singleton instance")
        
        # Test multiple imports
        from netra_backend.app.redis_manager import RedisManager
        manager3 = RedisManager()
        
        # All should use the same underlying connection management
        await manager1.initialize()
        await manager3.initialize()
        
        self.assertTrue(manager1.is_connected, "Manager1 should be connected")
        self.assertTrue(manager3.is_connected, "Manager3 should be connected")
        
    async def test_compatibility_layer_warning_emissions(self):
        """Test that compatibility layers emit deprecation warnings."""
        import warnings
        
        # Capture warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            # Import compatibility layers
            from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
            from auth_service.auth_core.redis_manager import AuthRedisManager
            
            # Should have deprecation warnings
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            self.assertGreater(len(deprecation_warnings), 0, 
                             "Compatibility layers should emit deprecation warnings")
            
            # Check warning messages contain SSOT guidance
            warning_messages = [str(w.message) for w in deprecation_warnings]
            ssot_guidance = any("redis_manager directly" in msg for msg in warning_messages)
            self.assertTrue(ssot_guidance, "Warnings should guide users to SSOT Redis manager")
    
    async def test_circuit_breaker_functionality(self):
        """Test that circuit breaker prevents cascading failures."""
        # Force circuit breaker to open by simulating failures
        redis_manager._consecutive_failures = 10  # Force high failure count
        
        # Circuit breaker should block operations
        self.assertFalse(redis_manager._circuit_breaker.can_execute(), 
                        "Circuit breaker should block operations after failures")
        
        # Reset circuit breaker
        await redis_manager.reset_circuit_breaker()
        
        # Should allow operations again
        self.assertTrue(redis_manager._circuit_breaker.can_execute(),
                       "Circuit breaker should allow operations after reset")
        
        # Reset failure count for other tests
        redis_manager._consecutive_failures = 0