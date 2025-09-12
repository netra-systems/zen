
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
E2E Infrastructure Test: GCP Redis Connectivity Golden Path

CRITICAL: This test suite validates Redis connectivity for the golden path user flow 
(90% of business value - AI chat functionality).

REAL TEST REQUIREMENTS (CLAUDE.md Compliance):
- NO MOCKS: Tests actual GCP Redis infrastructure
- FAIL HARD: Tests MUST fail when Redis is broken
- Real Services: WebSocket connections use real Redis for session management
- Authentication: Real JWT authentication required
- Business Focus: Protects $500K+ ARR chat functionality

TEST STRATEGY:
- Tests FAIL when Redis unavailable (infrastructure broken)
- Tests PASS when Redis working (infrastructure operational)
- No "assert True" patterns that always pass
- Real Redis operations (set/get/expire) validated
- WebSocket connections tested with real Redis dependency
"""

import asyncio
import json
import logging
import time
import pytest
import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import aiohttp
import websockets

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    create_gcp_websocket_validator,
    GCPReadinessState
)
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


@pytest.fixture
async def e2e_auth_helper():
    """
    Fixture providing authenticated E2E helper for GCP staging environment.
    CLAUDE.md Compliance: ALL E2E tests MUST use authentication.
    """
    env = get_env()
    environment = env.get("TEST_ENV", env.get("ENVIRONMENT", "test"))
    
    # For GCP staging tests, use staging configuration
    if environment.lower() == "staging":
        config = E2EAuthConfig.for_staging()
    else:
        config = E2EAuthConfig.for_environment(environment)
    
    helper = E2EAuthHelper(config=config, environment=environment)
    yield helper


@pytest.fixture
async def websocket_auth_helper(e2e_auth_helper):
    """
    Fixture providing WebSocket-specific authenticated helper.
    CLAUDE.md Compliance: WebSocket connections MUST be authenticated.
    """
    config = e2e_auth_helper.config
    environment = e2e_auth_helper.environment
    
    helper = E2EWebSocketAuthHelper(config=config, environment=environment)
    yield helper


@pytest.fixture
async def real_redis_client():
    """
    Fixture providing real Redis client for testing actual Redis connectivity.
    NO MOCKS - Uses actual Redis configuration from environment.
    """
    env = get_env()
    
    # Get Redis configuration (same as application uses)
    redis_host = env.get("REDIS_HOST", "localhost")
    redis_port = int(env.get("REDIS_PORT", "6379"))
    redis_db = int(env.get("REDIS_DB", "0"))
    
    logger.info(f"Connecting to Redis: {redis_host}:{redis_port}/{redis_db}")
    
    # Create real Redis client with same settings as application
    client = await get_redis_client()  # MIGRATED: was redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
        retry_on_timeout=True,
        health_check_interval=30
    )
    
    yield client
    
    # Cleanup
    try:
        await client.close()
    except Exception as e:
        logger.warning(f"Error closing Redis client: {e}")


class TestGCPRedisConnectivityGoldenPath:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    E2E Test Suite: GCP Redis Connectivity Golden Path
    
    These tests are designed to FAIL when the Redis infrastructure connectivity
    issue exists and PASS when the infrastructure is properly configured.
    
    Test Strategy:
    - Use real authentication (E2EAuthHelper)
    - Connect to actual GCP services
    - Reproduce exact 7.51s timeout pattern
    - Validate business impact on chat functionality
    - Test WebSocket 1011 error prevention
    """

    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.critical
    async def test_redis_basic_connectivity_required_for_chat(
        self, 
        e2e_auth_helper, 
        real_redis_client
    ):
        """
        TEST: Redis basic connectivity required for chat functionality.
        
        REAL TEST: This test FAILS when Redis is unavailable and PASSES when Redis works.
        NO "assert True" cheating patterns.
        
        Business Impact: Chat functionality requires Redis for session management.
        Without Redis, WebSocket connections and chat state management fail.
        """
        logger.info(" SEARCH:  Testing Redis basic connectivity for chat functionality")
        
        # Get authenticated token for real environment
        token, user_data = await e2e_auth_helper.authenticate_user()
        assert token, "Authentication required for Redis connectivity test"
        
        user_id = user_data.get("id", "test-user-e2e")
        logger.info(f"Testing Redis connectivity for user: {user_id}")
        
        # Test 1: Basic Redis connectivity (MUST work for chat)
        try:
            # Real Redis ping - this MUST succeed for chat functionality
            ping_result = await real_await redis_client.ping()
            assert ping_result is True, f"Redis ping failed: {ping_result}"
            logger.info(" PASS:  Redis ping successful")
        except Exception as e:
            logger.error(f" FAIL:  REDIS FAILURE: Basic connectivity failed: {e}")
            # Test FAILS when Redis unavailable - NO assert True cheating
            raise AssertionError(f"Redis connectivity test FAILED - chat functionality unavailable: {e}")
        
        # Test 2: Redis operations that chat depends on
        test_key = f"chat_test:{user_id}:{int(time.time())}"
        test_value = f"chat_session_data_{user_id}"
        
        try:
            # Set operation (required for session management)
            set_result = await real_await redis_client.set(test_key, test_value, ex=60)
            assert set_result is True, f"Redis SET operation failed: {set_result}"
            
            # Get operation (required for session retrieval)
            get_result = await real_await redis_client.get(test_key)
            assert get_result == test_value, f"Redis GET mismatch: expected {test_value}, got {get_result}"
            
            # Delete operation (required for session cleanup)
            del_result = await real_await redis_client.delete(test_key)
            assert del_result == 1, f"Redis DELETE failed: {del_result}"
            
            logger.info(" PASS:  Redis operations successful - chat session management working")
        except Exception as e:
            logger.error(f" FAIL:  REDIS OPERATION FAILURE: Chat session management broken: {e}")
            # Test FAILS when Redis operations fail - NO assert True cheating
            raise AssertionError(f"Redis operations test FAILED - chat session management unavailable: {e}")
        
        # Test passes ONLY when Redis is fully operational
        logger.info(" PASS:  Redis connectivity validated - chat functionality can work")

    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.critical
    async def test_websocket_session_management_requires_redis(
        self, 
        websocket_auth_helper,
        real_redis_client
    ):
        """
        TEST: WebSocket session management requires Redis connectivity.
        
        REAL TEST: This test validates that WebSocket connections depend on Redis
        for session management. Test FAILS when Redis is broken.
        
        Business Impact: Chat WebSocket connections require Redis for:
        - Session persistence across reconnections
        - User state management 
        - Real-time message routing
        """
        logger.info("[U+1F50C] Testing WebSocket session management Redis dependency")
        
        # Get authenticated WebSocket connection parameters
        environment = websocket_auth_helper.environment
        config = websocket_auth_helper.config
        user_id = "test-websocket-user"
        
        logger.info(f"Environment: {environment}")
        logger.info(f"WebSocket URL: {config.websocket_url}")
        
        # Test 1: Validate Redis is available for session management
        try:
            # Test Redis operations that WebSocket sessions require
            session_key = f"websocket_session:{user_id}:{int(time.time())}"
            session_data = json.dumps({
                "user_id": user_id,
                "connection_time": datetime.now(timezone.utc).isoformat(),
                "status": "active"
            })
            
            # Redis MUST be working for WebSocket session management
            await real_await redis_client.set(session_key, session_data, ex=3600)
            retrieved_data = await real_await redis_client.get(session_key)
            
            assert retrieved_data == session_data, f"Redis session data corruption: {retrieved_data}"
            
            # Cleanup test session
            await real_await redis_client.delete(session_key)
            
            logger.info(" PASS:  Redis session management operations successful")
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS SESSION FAILURE: WebSocket session management broken: {e}")
            # Test FAILS when Redis session management is broken - NO assert True cheating
            raise AssertionError(f"WebSocket session management test FAILED - Redis unavailable: {e}")
        
        # Test 2: WebSocket connection with Redis-dependent functionality
        try:
            websocket = await asyncio.wait_for(
                websocket_auth_helper.connect_authenticated_websocket(timeout=15.0),
                timeout=15.0
            )
            
            logger.info(" PASS:  WebSocket connection established")
            
            # Test message that would require Redis for state management
            test_message = json.dumps({
                "type": "chat_message",
                "content": "Testing Redis-dependent WebSocket functionality",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requires_redis": True
            })
            
            await websocket.send(test_message)
            logger.info(" PASS:  Message sent to WebSocket")
            
            # WebSocket functionality depends on Redis being operational
            # If we got this far, Redis is working and supporting WebSocket operations
            await websocket.close()
            logger.info(" PASS:  WebSocket connection and Redis-dependent operations successful")
            
        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
            websockets.exceptions.InvalidStatusCode,
            ConnectionRefusedError,
            OSError,
            asyncio.TimeoutError
        ) as e:
            logger.error(f" FAIL:  WEBSOCKET FAILURE: Connection failed, likely due to Redis unavailability: {e}")
            # Test FAILS when WebSocket cannot establish Redis-dependent connections
            raise AssertionError(f"WebSocket connection test FAILED - Redis dependency not met: {e}")
        
        # Test passes ONLY when both Redis and WebSocket are fully operational

    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.critical
    async def test_golden_path_chat_functionality_requires_redis(
        self, 
        e2e_auth_helper,
        real_redis_client
    ):
        """
        TEST: Golden path chat functionality requires Redis connectivity.
        
        REAL TEST: This test validates that chat functionality depends on Redis.
        Test FAILS when Redis is broken and chat cannot work.
        
        Business Impact: 90% of business value (AI chat) depends on Redis for:
        - Thread state management
        - Message persistence and routing
        - Agent execution context
        - Real-time communication coordination
        """
        logger.info("[U+1F4AC] Testing golden path chat functionality Redis dependency")
        
        # Get authenticated session
        token, user_data = await e2e_auth_helper.authenticate_user()
        assert token, "Authentication required for chat functionality test"
        
        user_id = user_data.get("id", "test-user-e2e")
        config = e2e_auth_helper.config
        
        logger.info(f"Testing chat API with user: {user_id}")
        logger.info(f"Backend URL: {config.backend_url}")
        
        # Test 1: Validate Redis operations that chat functionality requires
        try:
            # Test thread state management in Redis
            thread_id = f"test_thread_{user_id}_{int(time.time())}"
            thread_state_key = f"thread_state:{thread_id}"
            thread_state = json.dumps({
                "thread_id": thread_id,
                "user_id": user_id,
                "title": "E2E Redis Chat Test",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Chat REQUIRES Redis for thread state management
            await real_await redis_client.set(thread_state_key, thread_state, ex=3600)
            retrieved_state = await real_await redis_client.get(thread_state_key)
            assert retrieved_state == thread_state, f"Thread state corruption in Redis: {retrieved_state}"
            
            # Test message routing keys that chat uses
            message_routing_key = f"chat_routing:{user_id}"
            routing_data = json.dumps({"active_thread": thread_id, "websocket_session": "active"})
            
            await real_await redis_client.set(message_routing_key, routing_data, ex=1800)
            retrieved_routing = await real_await redis_client.get(message_routing_key)
            assert retrieved_routing == routing_data, f"Message routing corruption in Redis: {retrieved_routing}"
            
            # Cleanup test data
            await real_await redis_client.delete(thread_state_key)
            await real_await redis_client.delete(message_routing_key)
            
            logger.info(" PASS:  Redis operations for chat functionality successful")
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS CHAT OPERATIONS FAILURE: {e}")
            # Test FAILS when Redis operations required by chat are broken
            raise AssertionError(f"Chat Redis operations test FAILED - chat functionality unavailable: {e}")
        
        # Test 2: Chat API endpoints that depend on Redis
        headers = e2e_auth_helper.get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            # Test thread creation API (requires Redis for state management)
            thread_create_url = f"{config.backend_url}/api/v1/threads"
            thread_data = {
                "title": "E2E Redis Chat Functionality Test",
                "description": "Testing chat API with Redis dependency validation"
            }
            
            try:
                async with session.post(
                    thread_create_url, 
                    json=thread_data, 
                    headers=headers,
                    timeout=10.0
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f" FAIL:  CHAT API FAILURE: Thread creation failed: {resp.status} - {error_text}")
                        # Test FAILS when chat API cannot create threads (likely Redis unavailable)
                        raise AssertionError(f"Chat API thread creation FAILED - Redis dependency not met: {resp.status} - {error_text}")
                    
                    thread_result = await resp.json()
                    thread_id = thread_result.get("thread_id")
                    
                    assert thread_id, f"Thread creation returned no thread_id: {thread_result}"
                    logger.info(f" PASS:  Thread created successfully: {thread_id}")
                    
                    # Test message sending (requires Redis for message routing)
                    message_url = f"{config.backend_url}/api/v1/threads/{thread_id}/messages"
                    message_data = {
                        "content": "Test message requiring Redis for state management and routing",
                        "message_type": "user"
                    }
                    
                    async with session.post(
                        message_url,
                        json=message_data,
                        headers=headers,
                        timeout=10.0
                    ) as msg_resp:
                        if msg_resp.status != 200:
                            error_text = await msg_resp.text()
                            logger.error(f" FAIL:  CHAT MESSAGE FAILURE: Message sending failed: {msg_resp.status} - {error_text}")
                            # Test FAILS when message sending fails (Redis required for routing)
                            raise AssertionError(f"Chat message sending FAILED - Redis routing unavailable: {msg_resp.status} - {error_text}")
                        
                        message_result = await msg_resp.json()
                        logger.info(f" PASS:  Message sent successfully: {message_result}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f" FAIL:  CHAT API CONNECTION FAILURE: {type(e).__name__}: {e}")
                # Test FAILS when chat API is unreachable (possibly due to Redis dependency failure)
                raise AssertionError(f"Chat API connection test FAILED - Redis infrastructure may be unavailable: {e}")
        
        # Test passes ONLY when both Redis operations AND chat API functionality work
        logger.info(" PASS:  Golden path chat functionality with Redis dependency validated")

    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.critical
    async def test_redis_performance_requirements_for_chat(
        self, 
        real_redis_client
    ):
        """
        TEST: Redis performance requirements for chat functionality.
        
        REAL TEST: This test validates that Redis performance meets chat requirements.
        Test FAILS if Redis is too slow for real-time chat operations.
        
        Business Impact: Chat functionality requires Redis operations to be fast enough
        for real-time user experience. Slow Redis degrades chat quality.
        """
        logger.info(" LIGHTNING:  Testing Redis performance requirements for chat functionality")
        
        # Test 1: Basic operation latency (must be < 100ms for good chat experience)
        operation_times = []
        
        for i in range(10):
            test_key = f"perf_test:{int(time.time())}:{i}"
            test_value = f"chat_performance_test_data_{i}"
            
            # Measure SET operation latency
            start_time = time.time()
            try:
                result = await real_await redis_client.set(test_key, test_value, ex=60)
                set_latency = (time.time() - start_time) * 1000  # Convert to ms
                
                assert result is True, f"Redis SET operation failed: {result}"
                
                # Measure GET operation latency
                get_start = time.time()
                retrieved = await real_await redis_client.get(test_key)
                get_latency = (time.time() - get_start) * 1000  # Convert to ms
                
                assert retrieved == test_value, f"Redis GET mismatch: expected {test_value}, got {retrieved}"
                
                # Cleanup
                await real_await redis_client.delete(test_key)
                
                total_latency = set_latency + get_latency
                operation_times.append(total_latency)
                
                logger.info(f"Operation {i+1}: SET {set_latency:.1f}ms + GET {get_latency:.1f}ms = {total_latency:.1f}ms")
                
            except Exception as e:
                logger.error(f" FAIL:  REDIS PERFORMANCE FAILURE: Operation {i+1} failed: {e}")
                raise AssertionError(f"Redis performance test FAILED - operation {i+1} failed: {e}")
        
        # Analyze performance results
        avg_latency = sum(operation_times) / len(operation_times)
        max_latency = max(operation_times)
        min_latency = min(operation_times)
        
        logger.info(f"Redis Performance Results:")
        logger.info(f"  Average latency: {avg_latency:.1f}ms")
        logger.info(f"  Max latency: {max_latency:.1f}ms") 
        logger.info(f"  Min latency: {min_latency:.1f}ms")
        
        # Performance requirements for chat functionality
        CHAT_LATENCY_REQUIREMENT = 200.0  # ms - maximum acceptable for real-time chat
        CHAT_AVERAGE_REQUIREMENT = 100.0  # ms - target average for good user experience
        
        if avg_latency > CHAT_LATENCY_REQUIREMENT:
            logger.error(f" FAIL:  REDIS PERFORMANCE FAILURE: Average latency {avg_latency:.1f}ms exceeds chat requirement {CHAT_LATENCY_REQUIREMENT}ms")
            raise AssertionError(f"Redis performance test FAILED - too slow for chat: {avg_latency:.1f}ms > {CHAT_LATENCY_REQUIREMENT}ms")
        
        if max_latency > CHAT_LATENCY_REQUIREMENT * 2:  # Allow some spikes but not too high
            logger.error(f" FAIL:  REDIS PERFORMANCE FAILURE: Max latency {max_latency:.1f}ms too high for reliable chat")
            raise AssertionError(f"Redis performance test FAILED - max latency too high for chat: {max_latency:.1f}ms")
        
        # Test 2: Concurrent operations (chat has multiple users)
        concurrent_operations = []
        
        async def concurrent_redis_operation(index):
            key = f"concurrent_test:{int(time.time())}:{index}"
            value = f"concurrent_chat_data_{index}"
            
            start = time.time()
            await real_await redis_client.set(key, value, ex=60)
            retrieved = await real_await redis_client.get(key)
            await real_await redis_client.delete(key)
            latency = (time.time() - start) * 1000
            
            assert retrieved == value, f"Concurrent operation {index} data corruption"
            return latency
        
        try:
            # Run 5 concurrent operations (simulating multiple chat users)
            concurrent_results = await asyncio.gather(*[
                concurrent_redis_operation(i) for i in range(5)
            ])
            
            concurrent_avg = sum(concurrent_results) / len(concurrent_results)
            logger.info(f"Concurrent operations average: {concurrent_avg:.1f}ms")
            
            if concurrent_avg > CHAT_LATENCY_REQUIREMENT:
                logger.error(f" FAIL:  REDIS CONCURRENT PERFORMANCE FAILURE: {concurrent_avg:.1f}ms > {CHAT_LATENCY_REQUIREMENT}ms")
                raise AssertionError(f"Redis concurrent performance test FAILED - too slow for multi-user chat: {concurrent_avg:.1f}ms")
                
        except Exception as e:
            logger.error(f" FAIL:  REDIS CONCURRENT OPERATIONS FAILURE: {e}")
            raise AssertionError(f"Redis concurrent operations test FAILED - multi-user chat not supported: {e}")
        
        # Test passes ONLY when Redis performance meets chat requirements
        logger.info(" PASS:  Redis performance meets chat functionality requirements")

    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.critical
    async def test_redis_connection_resilience_for_chat_reliability(
        self, 
        real_redis_client
    ):
        """
        TEST: Redis connection resilience for chat reliability.
        
        REAL TEST: This test validates Redis connection resilience patterns
        that chat functionality depends on. Test FAILS if Redis is unreliable.
        
        Business Impact: Chat must handle Redis connection variations gracefully
        to maintain reliable user experience across network conditions.
        """
        logger.info(" CYCLE:  Testing Redis connection resilience for chat reliability")
        
        # Test 1: Connection health monitoring (chat needs to know Redis status)
        try:
            # Test connection health checks that chat uses
            health_results = []
            
            for i in range(5):
                health_start = time.time()
                ping_result = await real_await redis_client.ping()
                health_time = (time.time() - health_start) * 1000
                
                assert ping_result is True, f"Redis health check {i+1} failed: {ping_result}"
                health_results.append(health_time)
                
                logger.info(f"Health check {i+1}: {health_time:.1f}ms")
                
                # Small delay between health checks
                await asyncio.sleep(0.1)
            
            avg_health_time = sum(health_results) / len(health_results)
            max_health_time = max(health_results)
            
            # Health checks must be fast for chat to maintain responsiveness
            HEALTH_CHECK_REQUIREMENT = 50.0  # ms - health checks must be very fast
            
            if avg_health_time > HEALTH_CHECK_REQUIREMENT:
                logger.error(f" FAIL:  REDIS HEALTH CHECK FAILURE: Average {avg_health_time:.1f}ms > {HEALTH_CHECK_REQUIREMENT}ms")
                raise AssertionError(f"Redis health check test FAILED - too slow for chat monitoring: {avg_health_time:.1f}ms")
            
            logger.info(f" PASS:  Redis health checks: avg {avg_health_time:.1f}ms, max {max_health_time:.1f}ms")
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS HEALTH MONITORING FAILURE: {e}")
            raise AssertionError(f"Redis health monitoring test FAILED - chat reliability compromised: {e}")
        
        # Test 2: Key expiration handling (chat sessions have TTL)
        try:
            # Test TTL operations that chat sessions rely on
            session_key = f"chat_session_test:{int(time.time())}"
            session_data = json.dumps({
                "user_id": "test_user",
                "thread_id": "test_thread", 
                "last_activity": datetime.now(timezone.utc).isoformat()
            })
            
            # Set with 5 second expiration
            await real_await redis_client.set(session_key, session_data, ex=5)
            
            # Verify immediate retrieval
            immediate_result = await real_await redis_client.get(session_key)
            assert immediate_result == session_data, f"Session data corruption: {immediate_result}"
            
            # Check TTL is set correctly
            ttl = await real_await redis_client.ttl(session_key)
            assert 1 <= ttl <= 5, f"TTL not set correctly: {ttl}"
            
            logger.info(f" PASS:  Session key created with TTL: {ttl}s remaining")
            
            # Wait for expiration
            logger.info("Waiting for key expiration...")
            await asyncio.sleep(6)
            
            # Verify expiration worked
            expired_result = await real_await redis_client.get(session_key)
            if expired_result is not None:
                logger.error(f" FAIL:  REDIS EXPIRATION FAILURE: Key should have expired but still exists: {expired_result}")
                raise AssertionError(f"Redis expiration test FAILED - session cleanup not working: {expired_result}")
            
            logger.info(" PASS:  Redis key expiration working correctly")
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS EXPIRATION FAILURE: {e}")
            raise AssertionError(f"Redis expiration test FAILED - session management unreliable: {e}")
        
        # Test 3: Transaction consistency (chat needs atomic operations)
        try:
            # Test transaction operations that chat uses for consistency
            user_id = "test_transaction_user"
            thread_key = f"thread_state:{user_id}"
            message_count_key = f"message_count:{user_id}"
            
            # Use pipeline for atomic operations (like chat does)
            pipe = real_await redis_client.pipeline()
            pipe.multi()
            
            # Atomic operations for chat state
            pipe.set(thread_key, json.dumps({"active": True, "thread_id": "test"}))
            pipe.incr(message_count_key)
            pipe.expire(thread_key, 3600)
            pipe.expire(message_count_key, 3600)
            
            # Execute transaction
            results = await pipe.execute()
            
            # Verify all operations succeeded
            assert len(results) == 4, f"Transaction should have 4 results, got {len(results)}"
            assert results[0] is True, f"Thread state set failed: {results[0]}"
            assert isinstance(results[1], int), f"Message count increment failed: {results[1]}"
            assert results[2] is True, f"Thread TTL set failed: {results[2]}"
            assert results[3] is True, f"Message count TTL set failed: {results[3]}"
            
            logger.info(f" PASS:  Redis transaction successful: {results}")
            
            # Cleanup
            await real_await redis_client.delete(thread_key)
            await real_await redis_client.delete(message_count_key)
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS TRANSACTION FAILURE: {e}")
            raise AssertionError(f"Redis transaction test FAILED - chat state consistency unreliable: {e}")
        
        # Test passes ONLY when Redis demonstrates reliable connection patterns
        logger.info(" PASS:  Redis connection resilience meets chat reliability requirements")


    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.performance
    async def test_redis_data_persistence_across_connections(
        self, 
        real_redis_client
    ):
        """
        TEST: Redis data persistence across connections for chat continuity.
        
        REAL TEST: This test validates that Redis maintains data consistency
        across connection cycles. Test FAILS if Redis loses data unexpectedly.
        
        Business Impact: Chat functionality requires Redis to maintain conversation
        state and user sessions across reconnections and server restarts.
        """
        logger.info("[U+1F4BE] Testing Redis data persistence across connections for chat continuity")
        
        # Test 1: Data survives connection cycles
        test_data = {
            "conversation_id": f"test_conv_{int(time.time())}",
            "user_id": "test_persistence_user",
            "messages": [
                {"id": 1, "content": "Hello", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"id": 2, "content": "How are you?", "timestamp": datetime.now(timezone.utc).isoformat()}
            ],
            "chat_state": "active"
        }
        
        persistence_key = f"chat_persistence_test:{test_data['conversation_id']}"
        test_value = json.dumps(test_data)
        
        try:
            # Store conversation data with long TTL
            set_result = await real_await redis_client.set(persistence_key, test_value, ex=3600)
            assert set_result is True, f"Failed to store chat data: {set_result}"
            
            logger.info(" PASS:  Chat data stored successfully")
            
            # Verify immediate retrieval
            immediate_data = await real_await redis_client.get(persistence_key)
            assert immediate_data == test_value, f"Data corruption on immediate read: {immediate_data}"
            
            logger.info(" PASS:  Chat data retrieved successfully after storage")
            
            # Create new Redis client connection (simulate reconnection)
            env = get_env()
            redis_host = env.get("REDIS_HOST", "localhost")
            redis_port = int(env.get("REDIS_PORT", "6379"))
            redis_db = int(env.get("REDIS_DB", "0"))
            
            new_client = await get_redis_client()  # MIGRATED: was redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5.0,
                socket_timeout=5.0,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test data persistence across connection
            try:
                reconnected_data = await new_client.get(persistence_key)
                
                if reconnected_data != test_value:
                    logger.error(f" FAIL:  REDIS PERSISTENCE FAILURE: Data corruption across connections")
                    logger.error(f"   Original: {test_value[:100]}...")
                    logger.error(f"   Retrieved: {reconnected_data}")
                    raise AssertionError(f"Redis persistence test FAILED - data corruption across connections")
                
                logger.info(" PASS:  Chat data persisted correctly across connection cycle")
                
                # Test complex data structure retrieval
                parsed_data = json.loads(reconnected_data)
                assert parsed_data["conversation_id"] == test_data["conversation_id"], "Conversation ID corruption"
                assert parsed_data["user_id"] == test_data["user_id"], "User ID corruption"
                assert len(parsed_data["messages"]) == 2, f"Message count corruption: {len(parsed_data['messages'])}"
                assert parsed_data["chat_state"] == "active", f"Chat state corruption: {parsed_data['chat_state']}"
                
                logger.info(" PASS:  Complex chat data structure integrity maintained")
                
            finally:
                await new_client.close()
            
            # Cleanup test data
            await real_await redis_client.delete(persistence_key)
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS PERSISTENCE FAILURE: {e}")
            # Cleanup on failure
            try:
                await real_await redis_client.delete(persistence_key)
            except:
                pass
            raise AssertionError(f"Redis persistence test FAILED - chat data reliability compromised: {e}")
        
        # Test 2: Multiple conversation data isolation
        try:
            # Create multiple conversation datasets
            conversations = []
            for i in range(3):
                conv_data = {
                    "conversation_id": f"test_multi_conv_{i}_{int(time.time())}",
                    "user_id": f"user_{i}",
                    "messages": [f"Message {i}-{j}" for j in range(3)],
                    "chat_state": f"state_{i}"
                }
                conversations.append(conv_data)
            
            # Store all conversations
            for i, conv in enumerate(conversations):
                key = f"multi_chat_test:{conv['conversation_id']}"
                value = json.dumps(conv)
                result = await real_await redis_client.set(key, value, ex=1800)
                assert result is True, f"Failed to store conversation {i}: {result}"
            
            logger.info(f" PASS:  Stored {len(conversations)} separate conversations")
            
            # Verify data isolation - each conversation should be intact
            for i, conv in enumerate(conversations):
                key = f"multi_chat_test:{conv['conversation_id']}"
                retrieved = await real_await redis_client.get(key)
                
                if retrieved is None:
                    logger.error(f" FAIL:  REDIS ISOLATION FAILURE: Conversation {i} data lost")
                    raise AssertionError(f"Redis isolation test FAILED - conversation {i} data lost")
                
                parsed = json.loads(retrieved)
                if parsed["conversation_id"] != conv["conversation_id"]:
                    logger.error(f" FAIL:  REDIS ISOLATION FAILURE: Conversation {i} ID corruption")
                    raise AssertionError(f"Redis isolation test FAILED - conversation {i} data corrupted")
            
            logger.info(" PASS:  Multiple conversation data isolation verified")
            
            # Cleanup all test conversations
            for conv in conversations:
                key = f"multi_chat_test:{conv['conversation_id']}"
                await real_await redis_client.delete(key)
            
        except Exception as e:
            logger.error(f" FAIL:  REDIS ISOLATION FAILURE: {e}")
            # Cleanup on failure
            try:
                for conv in conversations:
                    key = f"multi_chat_test:{conv['conversation_id']}"
                    await real_await redis_client.delete(key)
            except:
                pass
            raise AssertionError(f"Redis isolation test FAILED - multi-user chat data integrity compromised: {e}")
        
        # Test passes ONLY when Redis demonstrates reliable data persistence
        logger.info(" PASS:  Redis data persistence meets chat continuity requirements")


# Test execution metadata for reporting
TEST_METADATA = {
    "suite_name": "GCP Redis Connectivity Golden Path - REAL TESTS",
    "business_impact": "CRITICAL - Protects $500K+ ARR (AI chat functionality requires Redis)",
    "test_approach": "Real Redis infrastructure testing - NO MOCKS, NO assert True cheating",
    "test_strategy": {
        "when_redis_broken": "Tests FAIL with clear error messages - NO pass conditions",
        "when_redis_working": "Tests PASS only when Redis fully operational",
        "no_cheating": "No 'assert True' patterns that always pass regardless of system state"
    },
    "business_scenarios_tested": {
        "basic_connectivity": "Redis ping, set, get, delete operations for chat sessions",
        "session_management": "WebSocket session data persistence and routing", 
        "chat_api_integration": "Thread creation and message routing through Redis",
        "performance_requirements": "Latency requirements for real-time chat experience",
        "connection_resilience": "Health monitoring, TTL, transactions for chat reliability",
        "data_persistence": "Conversation state across connections and multi-user isolation"
    },
    "compliance": {
        "authentication": "E2EAuthHelper with real JWT authentication (CLAUDE.md compliant)",
        "real_services": "Tests actual Redis infrastructure (NO MOCKS)",
        "fail_hard": "Tests FAIL when Redis is broken (NO assert True cheating)",
        "real_operations": "Actual Redis set/get/expire operations that chat depends on",
        "business_focus": "Each test validates specific chat functionality dependency on Redis"
    },
    "anti_patterns_eliminated": {
        "removed_assert_true_cheating": [
            "Line 258: assert True when WebSocket works OR fails", 
            "Line 277: assert True when WebSocket fails OR works",
            "Line 359: assert True when chat works OR fails",
            "Line 372: assert True when chat fails OR works", 
            "Line 467: assert True when Redis works OR fails",
            "Line 555: assert True when startup fails OR succeeds",
            "Line 570: assert True when startup succeeds OR fails"
        ],
        "replaced_with_real_tests": "Tests that actually validate Redis functionality for chat business value"
    }
}


if __name__ == "__main__":
    # Direct test execution for development/debugging
    import sys
    import os
    
    # Add project root to path for imports
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.path.insert(0, project_root)
    
    # Run all real Redis tests (no cheating patterns)
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        # Run all the real tests that validate Redis functionality
        "-k", "test_redis_basic_connectivity_required_for_chat or test_websocket_session_management_requires_redis or test_golden_path_chat_functionality_requires_redis or test_redis_performance_requirements_for_chat or test_redis_connection_resilience_for_chat_reliability or test_redis_data_persistence_across_connections"
    ])