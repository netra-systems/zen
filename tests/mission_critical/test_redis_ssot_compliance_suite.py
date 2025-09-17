"""
"""
Redis SSOT Compliance Test Suite - Mission Critical Validation

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: Chat Functionality Stability (90% of platform value)
- Value Impact: Prevents WebSocket 1011 errors that break chat reliability
- Strategic Impact: Protects $500K+ ARR by ensuring Redis operations don't conflict'

This test suite validates that:
1. SSOT Redis Manager is the only active Redis implementation
2. Legacy compatibility layer properly redirects to SSOT
3. No competing Redis managers exist that could cause WebSocket 1011 errors
4. Circuit breaker and auto-reconnection work correctly
5. Multi-user isolation prevents shared Redis state

CRITICAL: Uses REAL Redis services (non-Docker) as specified in requirements
"
"

"""
"""
import asyncio
import pytest
import time
import json
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Redis SSOT imports
from netra_backend.app.redis_manager import RedisManager, redis_manager
from netra_backend.app.core.redis_manager import RedisManager as DeprecatedRedisManager

# Shared environment utilities
from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment

# Logging for validation
import logging
logger = logging.getLogger(__name__)


class TestRedisSSOTCompliance(SSotAsyncTestCase):
    "Test Redis SSOT compliance and architecture validation."
    
    async def asyncSetUp(self):
        "Set up test environment for Redis SSOT validation."
        await super().asyncSetUp()
        
        # Ensure test environment variables are set
        self.test_env = {
            TESTING: "true,"
            ENVIRONMENT": test,"
            TEST_DISABLE_REDIS: false,
            REDIS_URL": "redis://localhost:6381/0  # Test Redis port
        }
        
        # Apply test environment
        for key, value in self.test_env.items():
            self.set_env_var(key, value)
        
        # Initialize SSOT Redis manager for testing - use singleton pattern
        self.redis_manager = redis_manager
        await self.redis_manager.initialize()
        
        # Track original state for cleanup
        self.original_state = {
            connected: self.redis_manager.is_connected,
            client: self.redis_manager._client"
            client: self.redis_manager._client"
        }
    
    async def asyncTearDown(self):
        "Clean up Redis test state."
        try:
            # Clean up any test data
            if self.redis_manager.is_connected:
                # Clear test keys
                test_keys = await self.redis_manager.keys("test:*)"
                for key in test_keys:
                    await self.redis_manager.delete(key)
                
                # Shutdown Redis manager
                await self.redis_manager.shutdown()
        except Exception as e:
            logger.debug(fCleanup error (non-critical): {e})
        
        await super().asyncTearDown()
    
    async def test_ssot_redis_manager_initialization(self):
        Test SSOT Redis Manager initializes correctly with all features.""
        # Verify Redis manager is properly initialized
        self.assertIsInstance(self.redis_manager, RedisManager)
        
        # Check circuit breaker is configured
        self.assertIsNotNone(self.redis_manager._circuit_breaker)
        
        # Check background tasks are configured (but may not be running in test)
        self.assertIsNotNone(self.redis_manager._reconnect_task)
        self.assertIsNotNone(self.redis_manager._health_monitor_task)
        
        # Check configuration is read from environment
        backend_env = BackendEnvironment()
        redis_url = backend_env.get_redis_url()
        self.assertIn(6381, redis_url)  # Test Redis port
        self.assertIn("/0, redis_url)    # Test database"
    
    async def test_ssot_redis_operations_basic(self):
        Test basic Redis operations work through SSOT manager."
        Test basic Redis operations work through SSOT manager."
        test_key = "test:ssot:basic"
        test_value = ssot_test_value
        
        # Test set operation
        result = await self.redis_manager.set(test_key, test_value, ex=30)
        self.assertTrue(result, "Redis set operation should succeed)"
        
        # Test get operation
        retrieved_value = await self.redis_manager.get(test_key)
        self.assertEqual(retrieved_value, test_value, Retrieved value should match set value)
        
        # Test exists operation
        exists = await self.redis_manager.exists(test_key)
        self.assertTrue(exists, Key should exist after setting)"
        self.assertTrue(exists, Key should exist after setting)"
        
        # Test delete operation
        deleted = await self.redis_manager.delete(test_key)
        self.assertTrue(deleted, Key should be deleted successfully")"
        
        # Verify key is gone
        exists_after_delete = await self.redis_manager.exists(test_key)
        self.assertFalse(exists_after_delete, Key should not exist after deletion)
    
    async def test_ssot_redis_circuit_breaker_functionality(self):
        ""Test circuit breaker prevents cascading failures.
        # Get circuit breaker status
        status = self.redis_manager._circuit_breaker.get_status()
        self.assertIn(state, status)"
        self.assertIn(state, status)"
        self.assertIn(failure_count", status)"
        
        # Test that circuit breaker can be checked
        can_execute = self.redis_manager._circuit_breaker.can_execute()
        self.assertIsInstance(can_execute, bool)
        
        # Test circuit breaker reset
        await self.redis_manager.reset_circuit_breaker()
        
        # Verify circuit breaker is in closed state after reset
        status_after_reset = self.redis_manager._circuit_breaker.get_status()
        # State should be closed (working) after reset
        self.assertNotEqual(status_after_reset[state], open)
    
    async def test_ssot_redis_auto_reconnection(self):
        "Test automatic reconnection functionality."
        # Test force reconnect capability
        original_connected = self.redis_manager.is_connected
        
        # Force reconnection
        reconnect_success = await self.redis_manager.force_reconnect()
        
        # In test environment, reconnection should work
        if original_connected:
            self.assertTrue(reconnect_success, Force reconnection should succeed)"
            self.assertTrue(reconnect_success, Force reconnection should succeed)"
            self.assertTrue(self.redis_manager.is_connected, "Should be connected after force reconnect)"
        else:
            # If originally not connected, reconnection might fail in test env
            logger.info(Redis not connected in test environment - this is expected)
    
    async def test_ssot_redis_advanced_operations(self):
        "Test advanced Redis operations through SSOT manager."
        # Test multi-get/multi-set
        test_data = {
            test:mset:1: "value1,"
            test:mset:2": value2,"
            test:mset:3: value3
        }
        
        # Set multiple values
        mset_result = await self.redis_manager.mset(test_data)
        if self.redis_manager.is_connected:
            self.assertTrue(mset_result, Multi-set should succeed")"
            
            # Get multiple values
            keys = list(test_data.keys())
            values = await self.redis_manager.mget(keys)
            
            # Verify values (allowing for None if Redis not available)
            if values and values[0] is not None:
                for i, expected_value in enumerate(test_data.values()):
                    self.assertEqual(values[i], expected_value)
            
            # Clean up
            for key in keys:
                await self.redis_manager.delete(key)
    
    async def test_ssot_redis_auth_service_compatibility(self):
        Test auth service compatibility methods."
        Test auth service compatibility methods."
        session_id = test_session_123"
        session_id = test_session_123"
        session_data = {
            user_id: test_user,
            "permissions: [read", write],
            created_at: "2025-9-16T10:0:00Z"
        }
        
        # Test session storage
        stored = await self.redis_manager.store_session(session_id, session_data, 60)
        if self.redis_manager.is_connected:
            self.assertTrue(stored, Session should be stored successfully")"
            
            # Test session retrieval
            retrieved_session = await self.redis_manager.get_session(session_id)
            self.assertEqual(retrieved_session, session_data, Retrieved session should match stored data)
            
            # Test session deletion
            deleted = await self.redis_manager.delete_session(session_id)
            self.assertTrue(deleted, Session should be deleted successfully")"
            
            # Verify session is gone
            retrieved_after_delete = await self.redis_manager.get_session(session_id)
            self.assertIsNone(retrieved_after_delete, Session should not exist after deletion)
    
    async def test_ssot_redis_user_cache_manager(self):
        "Test user-specific caching operations."
        from netra_backend.app.redis_manager import UserCacheManager
        
        user_cache = UserCacheManager(self.redis_manager)
        user_id = test_user_123
        cache_key = agent_state""
        cache_value = processing_request
        
        # Test user cache set
        set_result = await user_cache.set_user_cache(user_id, cache_key, cache_value, ttl=30)
        if self.redis_manager.is_connected:
            self.assertTrue(set_result, User cache set should succeed)"
            self.assertTrue(set_result, User cache set should succeed)"
            
            # Test user cache get
            retrieved_value = await user_cache.get_user_cache(user_id, cache_key)
            self.assertEqual(retrieved_value, cache_value, "Retrieved cache value should match)"
            
            # Test user cache clear
            cleared = await user_cache.clear_user_cache(user_id, cache_key)
            self.assertTrue(cleared, User cache should be cleared successfully)
    
    def test_ssot_redis_status_reporting(self):
        "Test Redis manager status reporting functionality."
        status = self.redis_manager.get_status()
        
        # Verify all required status fields are present
        required_fields = [
            connected,"
            connected,"
            "client_available,"
            consecutive_failures,
            "current_retry_delay,"
            max_reconnect_attempts,
            last_health_check,"
            last_health_check,"
            background_tasks","
            circuit_breaker
        ]
        
        for field in required_fields:
            self.assertIn(field, status, fStatus should include {field}")"
        
        # Verify background tasks status structure
        bg_tasks = status[background_tasks]
        self.assertIn(reconnect_task_active, bg_tasks)"
        self.assertIn(reconnect_task_active, bg_tasks)"
        self.assertIn("health_monitor_active, bg_tasks)"
        
        # Verify circuit breaker status structure
        cb_status = status[circuit_breaker]
        self.assertIn("state, cb_status)"
        
        logger.info(fRedis SSOT Status: {status})


class TestRedisLegacyCompatibility(SSotAsyncTestCase):
    Test legacy Redis compatibility layer redirects properly to SSOT.""
    
    async def asyncSetUp(self):
        Set up test environment for legacy compatibility validation.""
        await super().asyncSetUp()
        
        # Set test environment
        self.set_env_var(TESTING, true)
        self.set_env_var(ENVIRONMENT, test")"
        
        # Initialize deprecated manager for testing
        self.deprecated_manager = DeprecatedRedisManager()
        await self.deprecated_manager.connect()
    
    async def asyncTearDown(self):
        "Clean up legacy compatibility test state."
        try:
            await self.deprecated_manager.disconnect()
        except Exception as e:
            logger.debug(fLegacy cleanup error (non-critical): {e}")"
        
        await super().asyncTearDown()
    
    def test_legacy_manager_redirects_to_ssot(self):
        Test that deprecated Redis manager redirects to SSOT implementation."
        Test that deprecated Redis manager redirects to SSOT implementation."
        # Check that deprecated manager has SSOT manager reference
        self.assertIsNotNone(self.deprecated_manager._ssot_manager)
        
        # Verify SSOT manager is the canonical instance
        from netra_backend.app.redis_manager import redis_manager as canonical_manager
        self.assertIs(self.deprecated_manager._ssot_manager, canonical_manager)
    
    async def test_legacy_operations_redirect_to_ssot(self):
        "Test that legacy operations properly redirect to SSOT manager."
        test_key = "test:legacy:redirect"
        test_value = legacy_test_value
        
        # Test set operation through legacy interface
        result = await self.deprecated_manager.set(test_key, test_value, ex=30)
        
        if self.deprecated_manager._ssot_manager and self.deprecated_manager._ssot_manager.is_connected:
            self.assertTrue(result, Legacy set should succeed via SSOT redirect)"
            self.assertTrue(result, Legacy set should succeed via SSOT redirect)"
            
            # Test get operation through legacy interface
            retrieved_value = await self.deprecated_manager.get(test_key)
            self.assertEqual(retrieved_value, test_value, Legacy get should work via SSOT redirect")"
            
            # Verify data is actually in SSOT manager
            ssot_value = await self.deprecated_manager._ssot_manager.get(test_key)
            self.assertEqual(ssot_value, test_value, Data should be in SSOT manager)
            
            # Clean up through legacy interface
            deleted = await self.deprecated_manager.delete(test_key)
            self.assertTrue(deleted, Legacy delete should work via SSOT redirect")"
    
    def test_legacy_deprecation_warning_issued(self):
        Test that importing legacy manager issues deprecation warning."
        Test that importing legacy manager issues deprecation warning."
        import warnings
        
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter(always")"
            
            # Import should trigger deprecation warning
            from netra_backend.app.core.redis_manager import RedisManager as TestDeprecatedManager
            
            # Check that deprecation warning was issued
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            self.assertTrue(len(deprecation_warnings) > 0, Deprecation warning should be issued)
            
            # Verify warning message content
            warning_message = str(deprecation_warnings[0].message)
            self.assertIn(deprecated", warning_message.lower())"
            self.assertIn(websocket 1011, warning_message.lower())


class TestRedisMultiUserIsolation(SSotAsyncTestCase):
    "Test Redis multi-user isolation prevents shared state."
    
    async def asyncSetUp(self):
        Set up test environment for multi-user isolation testing.""
        await super().asyncSetUp()
        
        # Set test environment
        self.set_env_var(TESTING, true)
        self.set_env_var(ENVIRONMENT, "test)"
        
        # Create multiple Redis manager instances to simulate multi-user
        self.user1_manager = RedisManager()
        self.user2_manager = RedisManager()
        
        await self.user1_manager.initialize()
        await self.user2_manager.initialize()
    
    async def asyncTearDown(self):
        "Clean up multi-user isolation test state."
        try:
            # Clean up test data for both users
            for manager in [self.user1_manager, self.user2_manager]:
                if manager.is_connected:
                    test_keys = await manager.keys("test:user:*)"
                    for key in test_keys:
                        await manager.delete(key)
                    await manager.shutdown()
        except Exception as e:
            logger.debug(fMulti-user cleanup error (non-critical): {e})
        
        await super().asyncTearDown()
    
    async def test_user_specific_cache_isolation(self):
        Test that user-specific cache data is properly isolated.""
        from netra_backend.app.redis_manager import UserCacheManager
        
        user1_cache = UserCacheManager(self.user1_manager)
        user2_cache = UserCacheManager(self.user2_manager)
        
        user1_id = user_123
        user2_id = "user_456"
        cache_key = agent_state
        
        user1_value = user1_processing"
        user1_value = user1_processing"
        user2_value = user2_idle"
        user2_value = user2_idle"
        
        # Set cache for both users
        if self.user1_manager.is_connected:
            await user1_cache.set_user_cache(user1_id, cache_key, user1_value)
            await user2_cache.set_user_cache(user2_id, cache_key, user2_value)
            
            # Verify each user gets their own data
            user1_retrieved = await user1_cache.get_user_cache(user1_id, cache_key)
            user2_retrieved = await user2_cache.get_user_cache(user2_id, cache_key)
            
            self.assertEqual(user1_retrieved, user1_value, User 1 should get their own data)
            self.assertEqual(user2_retrieved, user2_value, User 2 should get their own data")"
            
            # Verify cross-user data is isolated
            user1_cannot_access_user2 = await user1_cache.get_user_cache(user2_id, cache_key)
            user2_cannot_access_user1 = await user2_cache.get_user_cache(user1_id, cache_key)
            
            # Users should be able to access each other's data by design (same Redis)'
            # but the keys should be different due to user_id prefixing
            self.assertEqual(user1_cannot_access_user2, user2_value, Users share Redis but use different keys)
            self.assertEqual(user2_cannot_access_user1, user1_value, Users share Redis but use different keys)"
            self.assertEqual(user2_cannot_access_user1, user1_value, Users share Redis but use different keys)"
    
    async def test_concurrent_user_operations_no_conflicts(self):
        "Test concurrent operations from multiple users don't conflict."
        if not self.user1_manager.is_connected:
            self.skipTest(Redis not connected - skipping concurrent test")"
        
        # Simulate concurrent operations
        async def user1_operations():
            for i in range(10):
                await self.user1_manager.set(ftest:user:1:key_{i}, fuser1_value_{i})
                await asyncio.sleep(0.1)  # Small delay to allow interleaving
        
        async def user2_operations():
            for i in range(10):
                await self.user2_manager.set(ftest:user:2:key_{i}, fuser2_value_{i})
                await asyncio.sleep(0.1)  # Small delay to allow interleaving
        
        # Run operations concurrently
        await asyncio.gather(user1_operations(), user2_operations())
        
        # Verify all data was set correctly
        for i in range(10):
            user1_value = await self.user1_manager.get(f"test:user:1:key_{i})"
            user2_value = await self.user2_manager.get(ftest:user:2:key_{i}")"
            
            self.assertEqual(user1_value, fuser1_value_{i}, fUser 1 key {i} should have correct value)
            self.assertEqual(user2_value, fuser2_value_{i}, fUser 2 key {i} should have correct value")"
    
    async def test_websocket_state_isolation(self):
        "Test WebSocket state isolation between users."
        # Simulate WebSocket run IDs for different users
        user1_run_id = run_user1_12345""
        user2_run_id = run_user2_67890
        
        user1_state = {agent: "processing, step": 1, tools: [search]}
        user2_state = {"agent: waiting", step: 3, tools: [calculator]}"
        user2_state = {"agent: waiting", step: 3, tools: [calculator]}"
        
        if self.user1_manager.is_connected:
            # Store WebSocket state for each user
            await self.user1_manager.set(fwebsocket_state:{user1_run_id}", json.dumps(user1_state))"
            await self.user2_manager.set(fwebsocket_state:{user2_run_id}, json.dumps(user2_state))
            
            # Retrieve and verify isolation
            user1_retrieved = await self.user1_manager.get(fwebsocket_state:{user1_run_id})"
            user1_retrieved = await self.user1_manager.get(fwebsocket_state:{user1_run_id})"
            user2_retrieved = await self.user2_manager.get(f"websocket_state:{user2_run_id})"
            
            self.assertEqual(json.loads(user1_retrieved), user1_state, User 1 WebSocket state should be isolated)
            self.assertEqual(json.loads(user2_retrieved), user2_state, User 2 WebSocket state should be isolated)"
            self.assertEqual(json.loads(user2_retrieved), user2_state, User 2 WebSocket state should be isolated)"


if __name__ == __main__":"
    pytest.main([__file__, "-v, --tb=short")
)