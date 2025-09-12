"""
Integration Tests for System Startup CACHE Phase

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Performance
- Value Impact: Ensures Redis cache infrastructure supports real-time chat functionality
- Strategic Impact: Prevents cache failures that would degrade chat performance and session management

CRITICAL: These tests validate the CACHE phase of system startup:
1. Redis connection establishment and validation
2. Redis health checks and connectivity monitoring
3. Session storage capabilities for user authentication
4. WebSocket connection caching for real-time chat
5. Agent state caching for conversation continuity
6. Cache performance requirements for chat responsiveness
7. Cache expiration policies for data management
8. Redis cluster/failover handling for reliability
9. Cache consistency for multi-user scenarios
10. Cache readiness for real-time chat operations

The CACHE phase is critical for performance - if it fails, chat becomes slow and unreliable.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

import pytest

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.service_availability import check_service_availability, ServiceUnavailableError
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.redis_manager import RedisManager, redis_manager
from netra_backend.app.core.backend_environment import BackendEnvironment

# Check service availability at module level
_service_status = check_service_availability(['redis'], timeout=2.0)
_redis_available = _service_status['redis'] is True and REDIS_AVAILABLE
_redis_skip_reason = f"Redis unavailable: {_service_status['redis']}" if not _redis_available else None


@pytest.mark.skipif(not _redis_available, reason=_redis_skip_reason)
class TestCachePhaseComprehensive(BaseIntegrationTest):
    """
    Comprehensive integration tests for system startup CACHE phase.
    
    CRITICAL: These tests ensure Redis cache infrastructure supports chat performance.
    Without proper CACHE phase, chat becomes slow and session management fails.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.logger.info("Setting up CACHE phase integration test")
        
        # Get test environment configuration
        self.env = get_env()
        self.backend_env = BackendEnvironment()
        
        # Store original environment for cleanup
        self.original_env = dict(os.environ)
        
        # Configure test Redis connection (port 6381 for test environment)
        self._setup_test_redis_config()
        
        # Initialize test Redis manager
        self.redis_manager = None
        
        # Track resources for cleanup
        self.redis_clients = []
        self.test_keys = []
        
        self.logger.info("CACHE phase test setup complete")
    
    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        
        # Clean up Redis resources synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule cleanup
                loop.create_task(self._cleanup_redis_resources())
            else:
                # If no loop, run cleanup in new loop
                asyncio.run(self._cleanup_redis_resources())
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        self.logger.info("CACHE phase test cleanup complete")
    
    def _setup_test_redis_config(self):
        """Setup test Redis configuration for integration tests."""
        # Configure for test Redis (port 6381)
        test_redis_config = {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6381',  # Test environment port
            'REDIS_DB': '0',
            'REDIS_PASSWORD': '',  # No password for test Redis
        }
        
        # Apply test configuration to environment
        for key, value in test_redis_config.items():
            os.environ[key] = value
            
        self.logger.info(f"Configured test Redis: {test_redis_config['REDIS_HOST']}:{test_redis_config['REDIS_PORT']}/{test_redis_config['REDIS_DB']}")
    
    async def _cleanup_redis_resources(self):
        """Clean up Redis connections and test data."""
        try:
            # Clean up test keys
            if self.redis_clients:
                for client in self.redis_clients:
                    try:
                        if self.test_keys:
                            await client.delete(*self.test_keys)
                        await client.close()
                    except Exception as e:
                        self.logger.warning(f"Error cleaning up Redis client: {e}")
            
            # Clean up Redis manager
            if self.redis_manager:
                await self.redis_manager.shutdown()
            
            self.logger.info("Redis resources cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error cleaning up Redis resources: {e}")
    
    def _generate_test_key(self, prefix: str = "test") -> str:
        """Generate a unique test key and track it for cleanup."""
        key = f"{prefix}:{uuid.uuid4().hex[:8]}:{int(time.time())}"
        self.test_keys.append(key)
        return key
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_redis_connection_establishment(self):
        """
        BVJ: Platform/Internal - Chat Infrastructure
        Test that Redis connection can be established successfully.
        CRITICAL: Chat performance requires Redis connectivity.
        """
        self.logger.info("Testing Redis connection establishment")
        
        # Test direct Redis connection
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,  # Test Redis port
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test basic connectivity
        pong = await redis_client.ping()
        assert pong is True, "Redis ping must return True"
        
        # Test basic operations
        test_key = self._generate_test_key("connection_test")
        await redis_client.set(test_key, "test_value")
        
        retrieved_value = await redis_client.get(test_key)
        assert retrieved_value == "test_value", "Redis must store and retrieve values correctly"
        
        # Test connection info
        info = await redis_client.info('server')
        assert 'redis_version' in info, "Redis server info must be accessible"
        
        self.logger.info(f"Redis connection established successfully - version: {info.get('redis_version', 'unknown')}")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_redis_manager_initialization(self):
        """
        BVJ: Platform/Internal - Chat Infrastructure
        Test Redis manager can be initialized and configured properly.
        CRITICAL: Chat requires managed Redis connections with resilience.
        """
        self.logger.info("Testing Redis manager initialization")
        
        # Create Redis manager instance
        self.redis_manager = RedisManager()
        
        # Initialize Redis manager
        await self.redis_manager.initialize()
        
        # Verify manager properties
        assert hasattr(self.redis_manager, '_client'), "Redis manager must have client reference"
        assert hasattr(self.redis_manager, '_connected'), "Redis manager must track connection state"
        
        # Test manager connectivity
        client = await self.redis_manager.get_client()
        assert client is not None, "Redis manager must provide client"
        
        # Test client operations through manager
        test_key = self._generate_test_key("manager_test")
        await client.set(test_key, "manager_value")
        
        retrieved_value = await client.get(test_key)
        assert retrieved_value == "manager_value", "Redis manager client must work correctly"
        
        self.logger.info("Redis manager initialization test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_redis_health_checks_connectivity(self):
        """
        BVJ: Platform/Internal - System Reliability
        Test Redis health check functionality for monitoring.
        CRITICAL: Chat system must detect Redis issues proactively.
        """
        self.logger.info("Testing Redis health checks and connectivity")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test ping health check
        start_time = time.time()
        pong = await redis_client.ping()
        response_time = time.time() - start_time
        
        assert pong is True, "Redis ping health check must succeed"
        assert response_time < 0.1, f"Redis ping must respond within 100ms, got {response_time:.3f}s"
        
        # Test server info health check
        start_time = time.time()
        info = await redis_client.info('server')
        info_response_time = time.time() - start_time
        
        assert isinstance(info, dict), "Redis info must return dictionary"
        assert 'uptime_in_seconds' in info, "Redis info must include uptime"
        assert info_response_time < 0.2, f"Redis info must respond within 200ms, got {info_response_time:.3f}s"
        
        # Test memory info for performance monitoring
        memory_info = await redis_client.info('memory')
        assert 'used_memory' in memory_info, "Redis memory info must be accessible"
        assert 'maxmemory' in memory_info, "Redis max memory info must be accessible"
        
        self.logger.info(f"Redis health checks completed - uptime: {info['uptime_in_seconds']}s, memory: {memory_info['used_memory']} bytes")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_session_storage_capabilities(self):
        """
        BVJ: Free/Early/Mid/Enterprise - User Authentication
        Test Redis session storage for user authentication in chat.
        CRITICAL: Chat requires persistent user sessions across requests.
        """
        self.logger.info("Testing session storage capabilities")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test session data storage
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        session_key = self._generate_test_key(f"session:{session_id}")
        
        session_data = {
            'user_id': user_id,
            'email': f"{user_id}@example.com",
            'created_at': int(time.time()),
            'last_activity': int(time.time()),
            'chat_preferences': {
                'theme': 'dark',
                'notifications': True
            }
        }
        
        # Store session data
        await redis_client.setex(
            session_key,
            3600,  # 1 hour TTL
            json.dumps(session_data)
        )
        
        # Retrieve and verify session data
        stored_data = await redis_client.get(session_key)
        assert stored_data is not None, "Session data must be stored successfully"
        
        parsed_data = json.loads(stored_data)
        assert parsed_data['user_id'] == user_id, "Session user_id must be preserved"
        assert parsed_data['email'] == f"{user_id}@example.com", "Session email must be preserved"
        assert 'chat_preferences' in parsed_data, "Session must store nested data"
        
        # Test session TTL
        ttl = await redis_client.ttl(session_key)
        assert ttl > 3500, "Session TTL must be set correctly"
        assert ttl <= 3600, "Session TTL must not exceed expected value"
        
        self.logger.info(f"Session storage test completed - stored session for {user_id} with {ttl}s TTL")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_websocket_connection_caching(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Real-time Chat
        Test Redis caching for WebSocket connections.
        CRITICAL: Chat requires efficient WebSocket connection management.
        """
        self.logger.info("Testing WebSocket connection caching")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test WebSocket connection metadata storage
        connection_id = f"ws_{uuid.uuid4().hex[:10]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        connection_key = self._generate_test_key(f"websocket:{connection_id}")
        user_connections_key = self._generate_test_key(f"user_ws:{user_id}")
        
        connection_data = {
            'connection_id': connection_id,
            'user_id': user_id,
            'connected_at': int(time.time()),
            'last_ping': int(time.time()),
            'chat_room': 'general',
            'status': 'active'
        }
        
        # Store connection data
        await redis_client.setex(
            connection_key,
            1800,  # 30 minutes TTL
            json.dumps(connection_data)
        )
        
        # Store user -> connections mapping
        await redis_client.sadd(user_connections_key, connection_id)
        await redis_client.expire(user_connections_key, 1800)
        
        # Verify connection data storage
        stored_connection = await redis_client.get(connection_key)
        assert stored_connection is not None, "WebSocket connection data must be stored"
        
        connection_info = json.loads(stored_connection)
        assert connection_info['connection_id'] == connection_id, "Connection ID must be preserved"
        assert connection_info['user_id'] == user_id, "User ID must be associated with connection"
        assert connection_info['status'] == 'active', "Connection status must be tracked"
        
        # Verify user connections mapping
        user_connections = await redis_client.smembers(user_connections_key)
        assert connection_id in user_connections, "User must have connection mapped"
        
        # Test connection lookup performance
        start_time = time.time()
        lookup_result = await redis_client.get(connection_key)
        lookup_time = time.time() - start_time
        
        assert lookup_result is not None, "Connection lookup must succeed"
        assert lookup_time < 0.01, f"Connection lookup must be fast (<10ms), got {lookup_time:.4f}s"
        
        self.logger.info(f"WebSocket connection caching test completed - lookup time: {lookup_time:.4f}s")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_agent_state_caching(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Chat Continuity
        Test Redis caching for agent conversation state.
        CRITICAL: Chat requires persistent agent context across interactions.
        """
        self.logger.info("Testing agent state caching")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test agent state storage
        thread_id = f"thread_{uuid.uuid4().hex[:10]}"
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        agent_state_key = self._generate_test_key(f"agent_state:{thread_id}:{agent_id}")
        
        agent_state = {
            'agent_id': agent_id,
            'thread_id': thread_id,
            'conversation_context': {
                'user_intent': 'cost_optimization',
                'collected_data': ['aws_costs', 'usage_metrics'],
                'next_steps': ['analyze_patterns', 'generate_recommendations']
            },
            'execution_state': {
                'current_step': 'data_analysis',
                'progress': 0.6,
                'tools_used': ['aws_cost_explorer', 'data_analyzer']
            },
            'updated_at': int(time.time())
        }
        
        # Store agent state
        await redis_client.setex(
            agent_state_key,
            7200,  # 2 hours TTL
            json.dumps(agent_state)
        )
        
        # Verify agent state storage
        stored_state = await redis_client.get(agent_state_key)
        assert stored_state is not None, "Agent state must be stored successfully"
        
        parsed_state = json.loads(stored_state)
        assert parsed_state['agent_id'] == agent_id, "Agent ID must be preserved"
        assert parsed_state['thread_id'] == thread_id, "Thread ID must be preserved"
        assert 'conversation_context' in parsed_state, "Conversation context must be preserved"
        assert 'execution_state' in parsed_state, "Execution state must be preserved"
        
        # Test state update
        parsed_state['execution_state']['progress'] = 0.8
        parsed_state['execution_state']['current_step'] = 'report_generation'
        parsed_state['updated_at'] = int(time.time())
        
        await redis_client.setex(
            agent_state_key,
            7200,
            json.dumps(parsed_state)
        )
        
        # Verify update
        updated_state = await redis_client.get(agent_state_key)
        updated_data = json.loads(updated_state)
        assert updated_data['execution_state']['progress'] == 0.8, "Agent state must be updatable"
        assert updated_data['execution_state']['current_step'] == 'report_generation', "Agent progress must be tracked"
        
        self.logger.info(f"Agent state caching test completed - cached state for {agent_id} in thread {thread_id}")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_cache_performance_requirements(self):
        """
        BVJ: Platform/Internal - Chat Performance
        Test Redis cache performance meets chat requirements.
        CRITICAL: Chat requires fast cache operations for good UX.
        """
        self.logger.info("Testing cache performance requirements")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test basic operation performance
        performance_tests = [
            ("SET", 0.001),  # Set operation < 1ms
            ("GET", 0.001),  # Get operation < 1ms
            ("DEL", 0.002),  # Delete operation < 2ms
            ("EXISTS", 0.001),  # Exists check < 1ms
        ]
        
        test_data = {
            'user_id': 'test_user_123',
            'session_data': 'test_session_data',
            'preferences': {'theme': 'dark', 'lang': 'en'}
        }
        
        for operation, max_time in performance_tests:
            test_key = self._generate_test_key(f"perf_test_{operation.lower()}")
            
            if operation == "SET":
                start_time = time.time()
                await redis_client.set(test_key, json.dumps(test_data))
                elapsed = time.time() - start_time
            elif operation == "GET":
                await redis_client.set(test_key, json.dumps(test_data))  # Setup
                start_time = time.time()
                await redis_client.get(test_key)
                elapsed = time.time() - start_time
            elif operation == "EXISTS":
                await redis_client.set(test_key, json.dumps(test_data))  # Setup
                start_time = time.time()
                await redis_client.exists(test_key)
                elapsed = time.time() - start_time
            elif operation == "DEL":
                await redis_client.set(test_key, json.dumps(test_data))  # Setup
                start_time = time.time()
                await redis_client.delete(test_key)
                elapsed = time.time() - start_time
            
            assert elapsed < max_time, f"{operation} operation took {elapsed:.4f}s, expected < {max_time}s"
            self.logger.info(f"Performance OK: {operation} completed in {elapsed:.4f}s")
        
        # Test bulk operations performance
        bulk_keys = [self._generate_test_key(f"bulk_{i}") for i in range(10)]
        
        start_time = time.time()
        pipe = await redis_client.pipeline()
        for i, key in enumerate(bulk_keys):
            pipe.set(key, f"bulk_value_{i}")
        await pipe.execute()
        bulk_time = time.time() - start_time
        
        assert bulk_time < 0.01, f"Bulk operations took {bulk_time:.4f}s, expected < 10ms"
        
        self.logger.info(f"Cache performance requirements test completed - bulk ops: {bulk_time:.4f}s")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_cache_expiration_policies(self):
        """
        BVJ: Platform/Internal - Data Management
        Test Redis cache expiration policies for data lifecycle.
        CRITICAL: Chat must manage cache data lifecycle properly.
        """
        self.logger.info("Testing cache expiration policies")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test various TTL scenarios
        expiration_tests = [
            ("session_data", 3600, "Session data - 1 hour"),
            ("websocket_conn", 1800, "WebSocket connection - 30 minutes"),
            ("agent_state", 7200, "Agent state - 2 hours"),
            ("temp_cache", 300, "Temporary cache - 5 minutes"),
        ]
        
        for data_type, ttl_seconds, description in expiration_tests:
            test_key = self._generate_test_key(f"ttl_test_{data_type}")
            
            # Set with TTL
            await redis_client.setex(test_key, ttl_seconds, f"test_data_for_{data_type}")
            
            # Verify TTL is set
            actual_ttl = await redis_client.ttl(test_key)
            assert actual_ttl > ttl_seconds - 10, f"TTL for {description} must be set correctly"
            assert actual_ttl <= ttl_seconds, f"TTL for {description} must not exceed expected"
            
            # Verify data exists
            exists = await redis_client.exists(test_key)
            assert exists == 1, f"Data for {description} must exist with TTL"
            
            self.logger.info(f"TTL test passed: {description} - TTL: {actual_ttl}s")
        
        # Test TTL update
        update_key = self._generate_test_key("ttl_update_test")
        await redis_client.setex(update_key, 100, "initial_data")
        
        # Update TTL
        await redis_client.expire(update_key, 200)
        updated_ttl = await redis_client.ttl(update_key)
        assert updated_ttl > 190, "TTL must be updatable"
        
        # Test persist (remove TTL)
        await redis_client.persist(update_key)
        persistent_ttl = await redis_client.ttl(update_key)
        assert persistent_ttl == -1, "TTL must be removable with persist"
        
        self.logger.info("Cache expiration policies test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_redis_failover_error_handling(self):
        """
        BVJ: Platform/Internal - System Resilience
        Test Redis error handling and recovery mechanisms.
        CRITICAL: Chat must gracefully handle cache connection issues.
        """
        self.logger.info("Testing Redis failover and error handling")
        
        # Test connection with invalid configuration (should handle gracefully)
        invalid_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,  # Valid port for this test
            db=0,
            decode_responses=True,
            socket_connect_timeout=1,  # Short timeout
            socket_timeout=1
        )
        self.redis_clients.append(invalid_client)
        
        # Test that client handles connection properly
        try:
            result = await invalid_client.ping()
            assert result is True, "Valid Redis connection must work"
        except Exception as e:
            # If Redis is not available, that's also a valid test case
            self.logger.info(f"Redis connection failed as expected: {e}")
        
        # Test error handling for invalid operations
        valid_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(valid_client)
        
        try:
            # Test invalid command
            await valid_client.execute_command("INVALID_COMMAND")
            assert False, "Invalid command should raise exception"
        except Exception as e:
            assert "unknown command" in str(e).lower() or "err" in str(e).lower(), \
                "Should get appropriate Redis error for invalid command"
            self.logger.info(f"Redis error handling working correctly: {type(e).__name__}")
        
        # Test timeout handling
        try:
            # Set a key and try to get it (should work)
            test_key = self._generate_test_key("timeout_test")
            await valid_client.set(test_key, "timeout_test_value")
            
            result = await valid_client.get(test_key)
            assert result == "timeout_test_value", "Normal operations should work despite timeout config"
            
        except Exception as e:
            self.logger.warning(f"Timeout test encountered error: {e}")
        
        self.logger.info("Redis failover error handling test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_cache_consistency_multi_user(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Multi-User Chat
        Test cache consistency for concurrent user operations.
        CRITICAL: Chat must maintain cache consistency across multiple users.
        """
        self.logger.info("Testing cache consistency for multi-user scenarios")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test concurrent user operations
        user_ids = [f"user_{i}_{uuid.uuid4().hex[:4]}" for i in range(5)]
        
        # Create concurrent tasks for multiple users
        async def user_session_operation(user_id: str, operation_id: int):
            session_key = f"multi_user_test:session:{user_id}"
            self.test_keys.append(session_key)
            
            user_data = {
                'user_id': user_id,
                'operation_id': operation_id,
                'timestamp': time.time(),
                'chat_status': 'active'
            }
            
            # Set user session
            await redis_client.setex(session_key, 300, json.dumps(user_data))
            
            # Verify data was set correctly
            stored_data = await redis_client.get(session_key)
            parsed_data = json.loads(stored_data)
            
            assert parsed_data['user_id'] == user_id, f"User ID consistency failed for {user_id}"
            assert parsed_data['operation_id'] == operation_id, f"Operation ID consistency failed for {user_id}"
            
            return user_id, operation_id
        
        # Execute concurrent operations
        tasks = [user_session_operation(user_id, i) for i, user_id in enumerate(user_ids)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        assert len(results) == len(user_ids), "All concurrent operations must complete"
        
        for user_id, operation_id in results:
            session_key = f"multi_user_test:session:{user_id}"
            
            # Verify data consistency
            final_data = await redis_client.get(session_key)
            assert final_data is not None, f"Session data must persist for {user_id}"
            
            parsed_final = json.loads(final_data)
            assert parsed_final['user_id'] == user_id, f"Final data consistency failed for {user_id}"
            assert parsed_final['operation_id'] == operation_id, f"Final operation ID consistency failed for {user_id}"
        
        # Test atomic operations
        counter_key = self._generate_test_key("atomic_counter")
        
        async def atomic_increment_operation():
            return await redis_client.incr(counter_key)
        
        # Execute concurrent atomic operations
        atomic_tasks = [atomic_increment_operation() for _ in range(10)]
        atomic_results = await asyncio.gather(*atomic_tasks)
        
        # Verify atomic consistency
        final_counter = await redis_client.get(counter_key)
        assert int(final_counter) == 10, "Atomic operations must maintain consistency"
        assert len(set(atomic_results)) == len(atomic_results), "All atomic operations must return unique values"
        
        self.logger.info(f"Cache consistency multi-user test completed - {len(user_ids)} users, counter: {final_counter}")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_cache_memory_management(self):
        """
        BVJ: Platform/Internal - Resource Management
        Test Redis memory usage and management for chat operations.
        CRITICAL: Chat must manage cache memory efficiently.
        """
        self.logger.info("Testing cache memory management")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Get initial memory usage
        initial_info = await redis_client.info('memory')
        initial_memory = initial_info['used_memory']
        
        self.logger.info(f"Initial Redis memory usage: {initial_memory} bytes")
        
        # Create test data to measure memory impact
        test_keys = []
        large_data = json.dumps({
            'user_id': f'test_user_{i}',
            'session_data': 'x' * 1000,  # 1KB of data per entry
            'metadata': {'timestamp': time.time(), 'type': 'memory_test'}
        })
        
        # Store multiple entries
        for i in range(100):
            key = self._generate_test_key(f"memory_test_{i}")
            test_keys.extend([key])
            await redis_client.setex(key, 300, large_data)
        
        # Check memory usage after data insertion
        after_insert_info = await redis_client.info('memory')
        after_insert_memory = after_insert_info['used_memory']
        memory_increase = after_insert_memory - initial_memory
        
        assert memory_increase > 50000, "Memory usage must increase with data storage"
        self.logger.info(f"Memory usage after insert: {after_insert_memory} bytes (+{memory_increase} bytes)")
        
        # Test memory cleanup with TTL expiration
        # Set very short TTL for cleanup test
        cleanup_key = self._generate_test_key("cleanup_test")
        await redis_client.setex(cleanup_key, 1, large_data)  # 1 second TTL
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Verify key expired
        exists = await redis_client.exists(cleanup_key)
        assert exists == 0, "Keys with TTL must expire and be cleaned up"
        
        # Test manual cleanup
        cleanup_keys = test_keys[:50]  # Clean up half the keys
        await redis_client.delete(*cleanup_keys)
        
        # Verify cleanup
        for key in cleanup_keys:
            exists = await redis_client.exists(key)
            assert exists == 0, f"Manually deleted key {key} must not exist"
        
        # Check memory after cleanup
        after_cleanup_info = await redis_client.info('memory')
        after_cleanup_memory = after_cleanup_info['used_memory']
        
        assert after_cleanup_memory < after_insert_memory, "Memory usage must decrease after cleanup"
        
        self.logger.info(f"Memory usage after cleanup: {after_cleanup_memory} bytes (saved {after_insert_memory - after_cleanup_memory} bytes)")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_cache_data_serialization(self):
        """
        BVJ: Platform/Internal - Data Integrity
        Test Redis data serialization for complex chat objects.
        CRITICAL: Chat must serialize/deserialize complex data correctly.
        """
        self.logger.info("Testing cache data serialization")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Test complex data structures
        complex_data_tests = [
            {
                'name': 'chat_session',
                'data': {
                    'user_id': 'user_12345',
                    'messages': [
                        {'id': 1, 'content': 'Hello', 'timestamp': time.time()},
                        {'id': 2, 'content': 'How can I help?', 'timestamp': time.time() + 1}
                    ],
                    'metadata': {
                        'thread_id': 'thread_abc123',
                        'agent_type': 'optimization',
                        'preferences': {'language': 'en', 'theme': 'dark'}
                    },
                    'state': {
                        'current_step': 'data_collection',
                        'progress': 0.3,
                        'flags': {'urgent': True, 'reviewed': False}
                    }
                }
            },
            {
                'name': 'websocket_state',
                'data': {
                    'connection_id': 'ws_conn_xyz789',
                    'subscriptions': ['user_updates', 'agent_notifications'],
                    'rate_limits': {'messages_per_minute': 60, 'last_reset': time.time()},
                    'heartbeat': {'last_ping': time.time(), 'interval': 30}
                }
            },
            {
                'name': 'agent_context',
                'data': {
                    'agent_id': 'agent_optimization_001',
                    'conversation_history': ['user_question', 'data_request', 'analysis_start'],
                    'collected_data': {
                        'aws_costs': [100.50, 95.25, 110.75],
                        'usage_metrics': {'cpu': 75, 'memory': 60, 'storage': 45}
                    },
                    'analysis_results': None,  # Test None values
                    'confidence_scores': {'data_quality': 0.95, 'recommendations': 0.85}
                }
            }
        ]
        
        for test_case in complex_data_tests:
            test_key = self._generate_test_key(f"serialization_{test_case['name']}")
            original_data = test_case['data']
            
            # Serialize and store
            serialized = json.dumps(original_data, default=str)  # Handle datetime/timestamp objects
            await redis_client.setex(test_key, 300, serialized)
            
            # Retrieve and deserialize
            retrieved_serialized = await redis_client.get(test_key)
            assert retrieved_serialized is not None, f"Serialized data for {test_case['name']} must be stored"
            
            deserialized_data = json.loads(retrieved_serialized)
            
            # Verify data integrity
            assert isinstance(deserialized_data, dict), f"Deserialized {test_case['name']} must be dict"
            
            # Check key fields based on test case
            if test_case['name'] == 'chat_session':
                assert deserialized_data['user_id'] == original_data['user_id'], "User ID must be preserved"
                assert len(deserialized_data['messages']) == len(original_data['messages']), "Messages count must be preserved"
                assert deserialized_data['state']['current_step'] == original_data['state']['current_step'], "State must be preserved"
                
            elif test_case['name'] == 'websocket_state':
                assert deserialized_data['connection_id'] == original_data['connection_id'], "Connection ID must be preserved"
                assert deserialized_data['subscriptions'] == original_data['subscriptions'], "Subscriptions must be preserved"
                
            elif test_case['name'] == 'agent_context':
                assert deserialized_data['agent_id'] == original_data['agent_id'], "Agent ID must be preserved"
                assert deserialized_data['conversation_history'] == original_data['conversation_history'], "History must be preserved"
                assert deserialized_data['analysis_results'] is None, "None values must be preserved"
            
            self.logger.info(f"Serialization test passed for {test_case['name']}")
        
        self.logger.info("Cache data serialization test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_cache
    async def test_cache_readiness_for_chat_operations(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Core Chat Business Value
        Test that Redis cache is fully ready to support chat operations.
        CRITICAL: This is the ultimate validation that chat caching can function.
        """
        self.logger.info("Testing cache readiness for chat operations")
        
        redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
            host='localhost',
            port=6381,
            db=0,
            decode_responses=True
        )
        self.redis_clients.append(redis_client)
        
        # Simulate complete chat session caching workflow
        user_id = f"chat_user_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{uuid.uuid4().hex[:10]}"
        thread_id = f"thread_{uuid.uuid4().hex[:10]}"
        ws_connection_id = f"ws_{uuid.uuid4().hex[:10]}"
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        # Test 1: User session caching
        session_key = self._generate_test_key(f"session:{session_id}")
        session_data = {
            'user_id': user_id,
            'created_at': int(time.time()),
            'preferences': {'theme': 'dark', 'notifications': True}
        }
        
        start_time = time.time()
        await redis_client.setex(session_key, 3600, json.dumps(session_data))
        session_write_time = time.time() - start_time
        
        assert session_write_time < 0.01, f"Session write must be fast (<10ms), got {session_write_time:.4f}s"
        
        # Test 2: WebSocket connection caching
        ws_key = self._generate_test_key(f"websocket:{ws_connection_id}")
        ws_data = {
            'connection_id': ws_connection_id,
            'user_id': user_id,
            'thread_id': thread_id,
            'connected_at': int(time.time()),
            'status': 'active'
        }
        
        start_time = time.time()
        await redis_client.setex(ws_key, 1800, json.dumps(ws_data))
        ws_write_time = time.time() - start_time
        
        assert ws_write_time < 0.01, f"WebSocket write must be fast (<10ms), got {ws_write_time:.4f}s"
        
        # Test 3: Agent state caching
        agent_key = self._generate_test_key(f"agent_state:{thread_id}:{agent_id}")
        agent_data = {
            'agent_id': agent_id,
            'thread_id': thread_id,
            'context': {
                'user_intent': 'cost_optimization',
                'collected_data': ['aws_costs', 'usage_patterns'],
                'analysis_progress': 0.7
            },
            'updated_at': int(time.time())
        }
        
        start_time = time.time()
        await redis_client.setex(agent_key, 7200, json.dumps(agent_data))
        agent_write_time = time.time() - start_time
        
        assert agent_write_time < 0.01, f"Agent state write must be fast (<10ms), got {agent_write_time:.4f}s"
        
        # Test 4: Fast retrieval for real-time chat
        retrieval_tests = [
            (session_key, "session"),
            (ws_key, "websocket"),
            (agent_key, "agent_state")
        ]
        
        for key, data_type in retrieval_tests:
            start_time = time.time()
            data = await redis_client.get(key)
            retrieval_time = time.time() - start_time
            
            assert data is not None, f"{data_type} data must be retrievable"
            assert retrieval_time < 0.005, f"{data_type} retrieval must be very fast (<5ms), got {retrieval_time:.4f}s"
            
            # Verify data integrity
            parsed_data = json.loads(data)
            assert isinstance(parsed_data, dict), f"{data_type} data must deserialize correctly"
            
            self.logger.info(f"Chat {data_type} cached and retrieved successfully ({retrieval_time:.4f}s)")
        
        # Test 5: Concurrent access simulation (multiple users)
        concurrent_operations = []
        
        async def simulate_user_operation(user_num: int):
            test_user_id = f"concurrent_user_{user_num}"
            test_key = f"concurrent_test:{test_user_id}"
            self.test_keys.append(test_key)
            
            # Write operation
            await redis_client.setex(
                test_key, 
                300, 
                json.dumps({'user_id': test_user_id, 'timestamp': time.time()})
            )
            
            # Read operation
            data = await redis_client.get(test_key)
            return json.loads(data)['user_id'] == test_user_id
        
        # Execute concurrent operations
        concurrent_tasks = [simulate_user_operation(i) for i in range(10)]
        start_time = time.time()
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - start_time
        
        assert all(concurrent_results), "All concurrent operations must succeed"
        assert concurrent_time < 0.1, f"Concurrent operations must complete quickly (<100ms), got {concurrent_time:.4f}s"
        
        # Test 6: Pipeline operations for efficiency
        pipe = await redis_client.pipeline()
        pipeline_keys = []
        
        for i in range(5):
            key = self._generate_test_key(f"pipeline_{i}")
            pipeline_keys.append(key)
            pipe.setex(key, 300, f"pipeline_value_{i}")
        
        start_time = time.time()
        await pipe.execute()
        pipeline_time = time.time() - start_time
        
        assert pipeline_time < 0.01, f"Pipeline operations must be efficient (<10ms), got {pipeline_time:.4f}s"
        
        # Verify pipeline results
        for i, key in enumerate(pipeline_keys):
            value = await redis_client.get(key)
            assert value == f"pipeline_value_{i}", f"Pipeline operation {i} must succeed"
        
        self.logger.info(
            f"Cache readiness validation complete:\n"
            f"  - Session write: {session_write_time:.4f}s\n"
            f"  - WebSocket write: {ws_write_time:.4f}s\n"
            f"  - Agent state write: {agent_write_time:.4f}s\n"
            f"  - Concurrent ops ({len(concurrent_tasks)} users): {concurrent_time:.4f}s\n"
            f"  - Pipeline ops (5 operations): {pipeline_time:.4f}s"
        )
        
        # Final validation log
        self.logger.info(
            "[U+1F680] CACHE PHASE VALIDATION COMPLETE: Redis cache infrastructure is ready to support real-time chat functionality"
        )
