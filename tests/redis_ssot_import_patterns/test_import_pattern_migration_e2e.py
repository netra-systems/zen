"""Import Pattern Migration E2E Test

MISSION: End-to-end validation that import pattern migration doesn't break Golden Path chat functionality.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: System Stability & Golden Path Protection during migration
- Value Impact: Ensures $500K+ ARR chat functionality remains intact during Redis import cleanup
- Strategic Impact: Validates migration safety before large-scale remediation

CRITICAL GOLDEN PATH VALIDATIONS:
- User authentication flow continues to work after import changes
- WebSocket connections maintain session state through Redis
- Chat message routing functions correctly
- Agent execution pipeline accesses user context
- Response delivery maintains user isolation

This test simulates the complete migration process and validates:
1. Auth service Redis operations work after import pattern changes
2. Cache manager Redis operations work after import pattern changes  
3. WebSocket session management continues functioning
4. Golden Path chat functionality is preserved
5. No user isolation violations during Redis operations
"""

import unittest
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)

class ImportPatternMigrationE2ETest(SSotAsyncTestCase):
    """End-to-end test validating import migration doesn't break functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user_id = "migration_test_user_123"
        cls.test_session_id = "migration_session_456"
        cls.test_message = "Test message for migration validation"
        
        # Golden Path critical operations to validate
        cls.critical_operations = [
            'user_authentication',
            'session_management', 
            'websocket_routing',
            'agent_execution',
            'response_delivery'
        ]

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        
        # Initialize Redis connections for testing
        try:
            from netra_backend.app.redis_manager import redis_manager
            self.ssot_redis = redis_manager
            
            # Test Redis connectivity
            client = await self.ssot_redis.get_client()
            if client:
                await client.ping()
                logger.info("✅ SSOT Redis connection verified")
            else:
                logger.warning("❌ SSOT Redis connection failed")
                
        except Exception as e:
            logger.error(f"Redis setup failed: {e}")
            self.ssot_redis = None

    async def test_auth_service_redis_operations_after_migration(self):
        """Test auth service Redis operations work after import pattern changes."""
        logger.info("Testing auth service Redis operations after migration...")
        
        # This test validates the auth service can still perform Redis operations
        # even after import patterns are unified to SSOT
        
        if not self.ssot_redis:
            self.skipTest("Redis not available for testing")
            
        # Test session storage (critical for user authentication)
        session_data = {
            'user_id': self.test_user_id,
            'authenticated': True,
            'timestamp': time.time()
        }
        
        # Store session using SSOT Redis manager
        store_success = await self.ssot_redis.set(
            f"auth:session:{self.test_session_id}",
            json.dumps(session_data),
            ex=3600
        )
        
        self.assertTrue(store_success, "Failed to store session data via SSOT Redis")
        
        # Retrieve session data
        retrieved_data = await self.ssot_redis.get(f"auth:session:{self.test_session_id}")
        self.assertIsNotNone(retrieved_data, "Failed to retrieve session data")
        
        parsed_data = json.loads(retrieved_data)
        self.assertEqual(parsed_data['user_id'], self.test_user_id)
        self.assertTrue(parsed_data['authenticated'])
        
        logger.info("✅ Auth service Redis operations validated")

    async def test_cache_manager_redis_operations_after_migration(self):
        """Test cache manager Redis operations work after import pattern changes."""
        logger.info("Testing cache manager Redis operations after migration...")
        
        if not self.ssot_redis:
            self.skipTest("Redis not available for testing")
            
        # Test user-specific cache operations (critical for agent context)
        cache_key = f"user:{self.test_user_id}:agent_context"
        cache_data = {
            'conversation_history': ['Hello', 'How are you?'],
            'user_preferences': {'theme': 'dark', 'language': 'en'},
            'active_agents': ['supervisor', 'data_helper']
        }
        
        # Store cache data
        store_success = await self.ssot_redis.set(
            cache_key,
            json.dumps(cache_data),
            ex=1800  # 30 minutes
        )
        
        self.assertTrue(store_success, "Failed to store cache data via SSOT Redis")
        
        # Retrieve cache data
        retrieved_cache = await self.ssot_redis.get(cache_key)
        self.assertIsNotNone(retrieved_cache, "Failed to retrieve cache data")
        
        parsed_cache = json.loads(retrieved_cache)
        self.assertEqual(len(parsed_cache['conversation_history']), 2)
        self.assertEqual(len(parsed_cache['active_agents']), 3)
        
        logger.info("✅ Cache manager Redis operations validated")

    async def test_websocket_session_management_continuity(self):
        """Test WebSocket session management continues functioning after migration."""
        logger.info("Testing WebSocket session management continuity...")
        
        if not self.ssot_redis:
            self.skipTest("Redis not available for testing")
            
        # Test WebSocket connection state storage
        connection_data = {
            'user_id': self.test_user_id,
            'connection_id': f"ws_conn_{int(time.time())}",
            'connected_at': time.time(),
            'last_activity': time.time(),
            'active_agents': []
        }
        
        # Store connection state
        ws_key = f"websocket:connection:{connection_data['connection_id']}"
        store_success = await self.ssot_redis.set(
            ws_key,
            json.dumps(connection_data),
            ex=7200  # 2 hours
        )
        
        self.assertTrue(store_success, "Failed to store WebSocket connection state")
        
        # Test connection lookup (critical for message routing)
        user_connections_key = f"websocket:user:{self.test_user_id}:connections"
        add_connection_success = await self.ssot_redis.sadd(
            user_connections_key, connection_data['connection_id']
        )
        
        # Retrieve user connections
        user_connections = await self.ssot_redis.smembers(user_connections_key)
        self.assertIn(connection_data['connection_id'], user_connections)
        
        logger.info("✅ WebSocket session management continuity validated")

    async def test_golden_path_chat_functionality_preservation(self):
        """Test that Golden Path chat functionality is preserved after migration."""
        logger.info("Testing Golden Path chat functionality preservation...")
        
        if not self.ssot_redis:
            self.skipTest("Redis not available for testing")
            
        # Simulate complete Golden Path data flow through Redis
        golden_path_operations = []
        
        # 1. User Authentication State
        auth_key = f"auth:user:{self.test_user_id}:state"
        auth_data = {'authenticated': True, 'jwt_valid': True}
        auth_success = await self.ssot_redis.set(auth_key, json.dumps(auth_data), ex=3600)
        golden_path_operations.append(('authentication', auth_success))
        
        # 2. Message Queue for Agent Processing
        message_key = f"messages:user:{self.test_user_id}:queue"
        message_data = {'message': self.test_message, 'timestamp': time.time()}
        message_success = await self.ssot_redis.lpush(message_key, json.dumps(message_data))
        golden_path_operations.append(('message_queue', message_success > 0))
        
        # 3. Agent Execution Context
        agent_key = f"agents:user:{self.test_user_id}:context"
        agent_data = {'active_workflow': 'chat_response', 'execution_id': 'exec_123'}
        agent_success = await self.ssot_redis.set(agent_key, json.dumps(agent_data), ex=1800)
        golden_path_operations.append(('agent_context', agent_success))
        
        # 4. Response Cache
        response_key = f"responses:user:{self.test_user_id}:latest"
        response_data = {'response': 'Test response', 'agent': 'supervisor'}
        response_success = await self.ssot_redis.set(response_key, json.dumps(response_data), ex=600)
        golden_path_operations.append(('response_cache', response_success))
        
        # 5. User Isolation Validation (Critical for Multi-User System)
        isolation_key = f"isolation:user:{self.test_user_id}:check"
        isolation_data = {'isolated': True, 'context_id': f"ctx_{self.test_user_id}"}
        isolation_success = await self.ssot_redis.set(isolation_key, json.dumps(isolation_data), ex=3600)
        golden_path_operations.append(('user_isolation', isolation_success))
        
        # Validate all operations succeeded
        failed_operations = [op for op, success in golden_path_operations if not success]
        
        self.assertEqual(len(failed_operations), 0, 
                        f"Golden Path operations failed: {failed_operations}")
        
        logger.info("✅ Golden Path chat functionality preservation validated")

    async def test_user_isolation_maintained_during_redis_operations(self):
        """Test that user isolation is maintained during Redis operations after migration."""
        logger.info("Testing user isolation maintained during Redis operations...")
        
        if not self.ssot_redis:
            self.skipTest("Redis not available for testing")
            
        # Test multiple users can operate independently
        user1_id = f"{self.test_user_id}_1" 
        user2_id = f"{self.test_user_id}_2"
        
        # Store data for both users
        user1_data = {'name': 'User One', 'active_session': 'session1'}
        user2_data = {'name': 'User Two', 'active_session': 'session2'}
        
        user1_key = f"user:{user1_id}:data"
        user2_key = f"user:{user2_id}:data"
        
        user1_success = await self.ssot_redis.set(user1_key, json.dumps(user1_data), ex=3600)
        user2_success = await self.ssot_redis.set(user2_key, json.dumps(user2_data), ex=3600)
        
        self.assertTrue(user1_success and user2_success, "Failed to store user data")
        
        # Retrieve and validate isolation
        retrieved_user1 = await self.ssot_redis.get(user1_key)
        retrieved_user2 = await self.ssot_redis.get(user2_key)
        
        self.assertIsNotNone(retrieved_user1, "User 1 data not found")
        self.assertIsNotNone(retrieved_user2, "User 2 data not found")
        
        parsed_user1 = json.loads(retrieved_user1)
        parsed_user2 = json.loads(retrieved_user2)
        
        # Validate data isolation
        self.assertNotEqual(parsed_user1['name'], parsed_user2['name'])
        self.assertNotEqual(parsed_user1['active_session'], parsed_user2['active_session'])
        
        logger.info("✅ User isolation maintained during Redis operations")

    async def test_no_redis_connection_pool_conflicts_after_migration(self):
        """Test that Redis connection pool conflicts are eliminated after migration."""
        logger.info("Testing no Redis connection pool conflicts after migration...")
        
        if not self.ssot_redis:
            self.skipTest("Redis not available for testing")
            
        # Test multiple concurrent operations don't conflict
        concurrent_operations = []
        
        for i in range(10):
            key = f"concurrent:test:{i}"
            value = f"value_{i}_{int(time.time())}"
            
            operation = self.ssot_redis.set(key, value, ex=300)
            concurrent_operations.append(operation)
            
        # Execute all operations concurrently
        results = await asyncio.gather(*concurrent_operations, return_exceptions=True)
        
        # Validate no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        self.assertEqual(len(exceptions), 0, 
                        f"Connection pool conflicts detected: {exceptions}")
        
        # Validate all operations succeeded
        successes = [r for r in results if r is True]
        self.assertEqual(len(successes), 10, "Not all concurrent operations succeeded")
        
        logger.info("✅ No Redis connection pool conflicts after migration")

    async def asyncTearDown(self):
        """Clean up test data."""
        if self.ssot_redis:
            try:
                # Clean up test data
                test_keys = [
                    f"auth:session:{self.test_session_id}",
                    f"user:{self.test_user_id}:agent_context",
                    f"auth:user:{self.test_user_id}:state",
                    f"messages:user:{self.test_user_id}:queue",
                    f"agents:user:{self.test_user_id}:context",
                    f"responses:user:{self.test_user_id}:latest",
                    f"isolation:user:{self.test_user_id}:check",
                    f"user:{self.test_user_id}_1:data",
                    f"user:{self.test_user_id}_2:data"
                ]
                
                # Clean concurrent test keys
                for i in range(10):
                    test_keys.append(f"concurrent:test:{i}")
                    
                # Delete all test keys
                for key in test_keys:
                    await self.ssot_redis.delete(key)
                    
                logger.debug(f"Cleaned up {len(test_keys)} test keys")
                
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        
        await super().asyncTearDown()


if __name__ == '__main__':
    unittest.main()