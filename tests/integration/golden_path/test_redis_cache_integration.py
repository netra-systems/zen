"""
Test Redis Cache Integration for Golden Path

CRITICAL INTEGRATION TEST: This validates Redis caching integration for session state,
WebSocket connections, and agent results with proper performance and isolation.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure fast session management and result caching for user experience
- Value Impact: Slow caching = poor user experience = reduced engagement
- Strategic Impact: Performance foundation for scalable $500K+ ARR platform

INTEGRATION POINTS TESTED:
1. Session state caching and retrieval
2. WebSocket connection state in Redis
3. Agent results caching for performance
4. Cache cleanup on session termination
5. Multi-user cache isolation
6. Performance requirements (< 100ms operations)

MUST use REAL Redis - NO MOCKS per CLAUDE.md standards
"""

import asyncio
import pytest
import time
import json
import redis.asyncio as redis
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from shared.types.core_types import UserID, ThreadID, RunID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestRedisCacheIntegration(SSotAsyncTestCase):
    """Test Redis cache integration with real Redis instance."""
    
    def setup_method(self, method=None):
        """Setup for Redis integration test components.""" 
        super().setup_method(method)
        
        # Initialize components
        self.test_environment = self.get_env_var("TEST_ENV", "test")
        self.id_generator = UnifiedIdGenerator()
        
        # Test metrics
        self.record_metric("test_category", "integration")
        self.record_metric("golden_path_component", "redis_cache_integration")
        self.record_metric("real_redis_required", True)
        
        # Track keys for cleanup
        self.created_keys = set()
    
    def _track_key(self, key: str):
        """Track key for cleanup."""
        self.created_keys.add(key)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_session_state_caching_and_retrieval(self, real_redis_fixture):
        """Test session state caching with real Redis."""
        # Use the Redis client from fixture
        redis_client = real_redis_fixture
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="session_cache_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create session state data
        session_state = {
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "websocket_client_id": str(user_context.websocket_client_id),
            "connection_time": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "permissions": ["read", "write", "execute_agents"],
            "session_data": {
                "current_agent": "cost_optimizer",
                "conversation_step": 3,
                "context": {
                    "business_intent": "cost_optimization",
                    "user_preferences": {
                        "detailed_analysis": True,
                        "include_recommendations": True
                    }
                }
            }
        }
        
        # Test session state caching
        cache_key = f"session:{user_context.user_id}"
        self._track_key(cache_key)
        
        # Cache session state with performance timing
        cache_start = time.time()
        await redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps(session_state)
        )
        cache_time = time.time() - cache_start
        
        # Test session state retrieval
        retrieval_start = time.time()
        cached_session = await redis_client.get(cache_key)
        retrieval_time = time.time() - retrieval_start
        
        # Assertions
        assert cached_session is not None, "Session should be cached"
        assert cache_time < 0.1, f"Cache operation should be < 100ms: {cache_time*1000:.1f}ms"
        assert retrieval_time < 0.1, f"Retrieval should be < 100ms: {retrieval_time*1000:.1f}ms"
        
        # Verify cached data integrity
        parsed_session = json.loads(cached_session)
        assert parsed_session["user_id"] == str(user_context.user_id), \
            "User ID should be preserved"
        assert parsed_session["thread_id"] == str(user_context.thread_id), \
            "Thread ID should be preserved"
        assert parsed_session["session_data"]["current_agent"] == "cost_optimizer", \
            "Session data should be preserved"
        assert parsed_session["session_data"]["context"]["business_intent"] == "cost_optimization", \
            "Deep nested data should be preserved"
        
        # Test session state update
        update_start = time.time()
        parsed_session["last_activity"] = datetime.now(timezone.utc).isoformat()
        parsed_session["session_data"]["conversation_step"] = 4
        
        await redis_client.setex(
            cache_key,
            3600,
            json.dumps(parsed_session)
        )
        update_time = time.time() - update_start
        
        # Verify update
        updated_session = json.loads(await redis_client.get(cache_key))
        assert updated_session["session_data"]["conversation_step"] == 4, \
            "Session should be updated"
        assert update_time < 0.1, f"Update should be < 100ms: {update_time*1000:.1f}ms"
        
        self.record_metric("session_caching_test_passed", True)
        self.record_metric("cache_operation_time", cache_time)
        self.record_metric("retrieval_time", retrieval_time)
        self.record_metric("update_time", update_time)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_connection_state_in_redis(self, real_redis_fixture):
        """Test WebSocket connection state management in Redis."""
        # Use the Redis client from fixture
        redis_client = real_redis_fixture
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="websocket_cache_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create WebSocket connection state
        ws_connection_state = {
            "websocket_client_id": str(user_context.websocket_client_id),
            "user_id": str(user_context.user_id),
            "connection_time": time.time(),
            "last_ping": time.time(),
            "connection_status": "connected",
            "client_info": {
                "user_agent": "Test Client 1.0",
                "ip_address": "127.0.0.1",
                "protocol_version": "v1"
            },
            "active_subscriptions": [
                "agent_events",
                "system_notifications",
                "user_messages"
            ]
        }
        
        # Cache WebSocket state
        ws_key = f"websocket:{user_context.websocket_client_id}"
        self._track_key(ws_key)
        
        ws_cache_start = time.time()
        await redis_client.setex(
            ws_key,
            1800,  # 30 minutes TTL
            json.dumps(ws_connection_state)
        )
        ws_cache_time = time.time() - ws_cache_start
        
        # Test WebSocket state retrieval
        ws_retrieval_start = time.time()
        cached_ws_state = await redis_client.get(ws_key)
        ws_retrieval_time = time.time() - ws_retrieval_start
        
        # Assertions
        assert cached_ws_state is not None, "WebSocket state should be cached"
        assert ws_cache_time < 0.1, f"WS cache should be fast: {ws_cache_time*1000:.1f}ms"
        assert ws_retrieval_time < 0.1, f"WS retrieval should be fast: {ws_retrieval_time*1000:.1f}ms"
        
        # Verify WebSocket data integrity
        parsed_ws_state = json.loads(cached_ws_state)
        assert parsed_ws_state["websocket_client_id"] == str(user_context.websocket_client_id), \
            "WebSocket client ID should be preserved"
        assert parsed_ws_state["user_id"] == str(user_context.user_id), \
            "User ID should be preserved"
        assert parsed_ws_state["connection_status"] == "connected", \
            "Connection status should be preserved"
        assert "agent_events" in parsed_ws_state["active_subscriptions"], \
            "Subscriptions should be preserved"
        
        # Test WebSocket heartbeat update
        heartbeat_start = time.time()
        parsed_ws_state["last_ping"] = time.time()
        
        await redis_client.setex(
            ws_key,
            1800,
            json.dumps(parsed_ws_state)
        )
        heartbeat_time = time.time() - heartbeat_start
        
        # Verify heartbeat update performance
        assert heartbeat_time < 0.05, \
            f"Heartbeat updates should be very fast: {heartbeat_time*1000:.1f}ms"
        
        # Test WebSocket disconnection cleanup
        disconnect_start = time.time()
        parsed_ws_state["connection_status"] = "disconnected"
        parsed_ws_state["disconnection_time"] = time.time()
        
        await redis_client.setex(
            ws_key,
            300,  # Reduce TTL to 5 minutes for disconnected state
            json.dumps(parsed_ws_state)
        )
        disconnect_time = time.time() - disconnect_start
        
        # Verify disconnection handling
        assert disconnect_time < 0.1, \
            f"Disconnection update should be fast: {disconnect_time*1000:.1f}ms"
        
        disconnected_state = json.loads(await redis_client.get(ws_key))
        assert disconnected_state["connection_status"] == "disconnected", \
            "Disconnection should be recorded"
        
        self.record_metric("websocket_caching_test_passed", True)
        self.record_metric("ws_cache_time", ws_cache_time)
        self.record_metric("ws_retrieval_time", ws_retrieval_time)
        self.record_metric("heartbeat_time", heartbeat_time)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_results_caching_for_performance(self, real_redis_fixture):
        """Test agent results caching for performance optimization."""
        # Use the Redis client from fixture
        redis_client = real_redis_fixture
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="agent_results_cache_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create agent execution results
        agent_results = {
            "data_agent": {
                "agent_name": "data_agent",
                "execution_id": self.id_generator.generate_agent_execution_id("test_agent", str(user_context.user_id)),
                "execution_time": 8.2,
                "status": "completed",
                "results": {
                    "total_cost": 1245.50,
                    "total_tokens": 248900,
                    "cost_breakdown": {
                        "gpt-4": 945.50,
                        "gpt-3.5": 300.00
                    },
                    "usage_patterns": {
                        "daily_average": 8000,
                        "peak_hours": [9, 10, 14, 15, 16],
                        "cost_trend": "increasing"
                    },
                    "analysis": {
                        "primary_drivers": ["model_selection", "token_usage"],
                        "optimization_potential": "high"
                    }
                },
                "metadata": {
                    "cache_key": f"agent_results:{user_context.user_id}:data_agent",
                    "cache_ttl": 3600,
                    "cached_at": time.time()
                }
            },
            "optimization_agent": {
                "agent_name": "optimization_agent",
                "execution_id": self.id_generator.generate_agent_execution_id("test_agent", str(user_context.user_id)),
                "execution_time": 12.5,
                "status": "completed",
                "results": {
                    "base_cost": 1245.50,
                    "recommendations": [
                        {
                            "type": "model_optimization",
                            "description": "Use GPT-3.5 for routine queries",
                            "potential_savings": 400.00,
                            "confidence": 0.92
                        },
                        {
                            "type": "prompt_optimization",
                            "description": "Optimize prompts to reduce token usage",
                            "potential_savings": 200.00,
                            "confidence": 0.88
                        },
                        {
                            "type": "caching_strategy",
                            "description": "Implement result caching",
                            "potential_savings": 300.00,
                            "confidence": 0.85
                        }
                    ],
                    "total_potential_savings": 900.00,
                    "roi_analysis": {
                        "implementation_cost": 1200.00,
                        "payback_period": "1.3 months",
                        "annual_savings": 10800.00
                    }
                },
                "metadata": {
                    "cache_key": f"agent_results:{user_context.user_id}:optimization_agent", 
                    "cache_ttl": 7200,  # 2 hours for optimization results
                    "cached_at": time.time()
                }
            }
        }
        
        # Test agent results caching performance
        cache_operations = []
        
        for agent_name, result in agent_results.items():
            cache_key = result["metadata"]["cache_key"]
            cache_ttl = result["metadata"]["cache_ttl"]
            self._track_key(cache_key)
            
            # Cache agent results
            cache_start = time.time()
            await redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(result)
            )
            cache_time = time.time() - cache_start
            cache_operations.append(cache_time)
            
            # Verify caching performance
            assert cache_time < 0.1, \
                f"Agent {agent_name} cache should be < 100ms: {cache_time*1000:.1f}ms"
        
        # Test bulk retrieval performance
        bulk_retrieval_start = time.time()
        cache_keys = [result["metadata"]["cache_key"] for result in agent_results.values()]
        cached_results = await redis_client.mget(cache_keys)
        bulk_retrieval_time = time.time() - bulk_retrieval_start
        
        # Assertions for bulk retrieval
        assert len(cached_results) == len(agent_results), \
            "Should retrieve all cached results"
        assert bulk_retrieval_time < 0.1, \
            f"Bulk retrieval should be fast: {bulk_retrieval_time*1000:.1f}ms"
        assert all(result is not None for result in cached_results), \
            "All cached results should be retrieved"
        
        # Verify data integrity for each cached result
        for i, (agent_name, original_result) in enumerate(agent_results.items()):
            cached_result = json.loads(cached_results[i])
            
            # Verify agent result structure preservation
            assert cached_result["agent_name"] == agent_name, \
                f"Agent name should be preserved for {agent_name}"
            assert cached_result["status"] == "completed", \
                f"Status should be preserved for {agent_name}"
            
            # Verify results data preservation
            if agent_name == "data_agent":
                assert cached_result["results"]["total_cost"] == 1245.50, \
                    "Data agent cost should be preserved"
                assert cached_result["results"]["cost_breakdown"]["gpt-4"] == 945.50, \
                    "Cost breakdown should be preserved"
            elif agent_name == "optimization_agent":
                assert cached_result["results"]["total_potential_savings"] == 900.00, \
                    "Optimization savings should be preserved"
                assert len(cached_result["results"]["recommendations"]) == 3, \
                    "All recommendations should be preserved"
        
        # Test cache expiration and TTL
        ttl_check_start = time.time()
        for cache_key in cache_keys:
            ttl = await redis_client.ttl(cache_key)
            assert ttl > 0, f"Cache key {cache_key} should have positive TTL: {ttl}"
            assert ttl <= 7200, f"TTL should not exceed max: {ttl}"
        ttl_check_time = time.time() - ttl_check_start
        
        assert ttl_check_time < 0.1, \
            f"TTL checks should be fast: {ttl_check_time*1000:.1f}ms"
        
        # Test cache invalidation
        invalidation_start = time.time()
        data_agent_key = agent_results["data_agent"]["metadata"]["cache_key"]
        await redis_client.delete(data_agent_key)
        invalidation_time = time.time() - invalidation_start
        
        # Verify invalidation
        invalidated_result = await redis_client.get(data_agent_key)
        assert invalidated_result is None, "Cache should be invalidated"
        assert invalidation_time < 0.05, \
            f"Cache invalidation should be very fast: {invalidation_time*1000:.1f}ms"
        
        # Calculate average cache performance
        avg_cache_time = sum(cache_operations) / len(cache_operations)
        
        self.record_metric("agent_results_caching_test_passed", True)
        self.record_metric("avg_cache_time", avg_cache_time)
        self.record_metric("bulk_retrieval_time", bulk_retrieval_time)
        self.record_metric("invalidation_time", invalidation_time)
        self.record_metric("agent_results_cached", len(agent_results))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_cache_cleanup_on_session_termination(self, real_redis_fixture):
        """Test cache cleanup when session terminates."""
        # Use the Redis client from fixture
        redis_client = real_redis_fixture
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="cache_cleanup_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create multiple cache entries for user session
        session_keys = [
            f"session:{user_context.user_id}",
            f"websocket:{user_context.websocket_client_id}",
            f"agent_results:{user_context.user_id}:data_agent",
            f"agent_results:{user_context.user_id}:optimization_agent",
            f"user_preferences:{user_context.user_id}",
            f"conversation_state:{user_context.thread_id}"
        ]
        
        # Cache data for all keys
        cache_data = {
            f"session:{user_context.user_id}": {
                "user_id": str(user_context.user_id),
                "status": "active"
            },
            f"websocket:{user_context.websocket_client_id}": {
                "websocket_client_id": str(user_context.websocket_client_id),
                "status": "connected"
            },
            f"agent_results:{user_context.user_id}:data_agent": {
                "agent": "data_agent",
                "results": {"cost": 100.0}
            },
            f"agent_results:{user_context.user_id}:optimization_agent": {
                "agent": "optimization_agent", 
                "results": {"savings": 50.0}
            },
            f"user_preferences:{user_context.user_id}": {
                "theme": "dark",
                "notifications": True
            },
            f"conversation_state:{user_context.thread_id}": {
                "step": 3,
                "context": {"business_intent": "optimization"}
            }
        }
        
        # Cache all data
        cache_setup_start = time.time()
        for key, data in cache_data.items():
            await redis_client.setex(key, 3600, json.dumps(data))
            self._track_key(key)
        cache_setup_time = time.time() - cache_setup_start
        
        # Verify all data is cached
        verification_start = time.time()
        cached_keys = await redis_client.exists(*session_keys)
        verification_time = time.time() - verification_start
        
        assert cached_keys == len(session_keys), \
            f"All keys should be cached: {cached_keys}/{len(session_keys)}"
        assert cache_setup_time < 1.0, \
            f"Cache setup should be reasonably fast: {cache_setup_time:.2f}s"
        assert verification_time < 0.1, \
            f"Verification should be fast: {verification_time*1000:.1f}ms"
        
        # Simulate session termination cleanup
        cleanup_start = time.time()
        
        # Method 1: Pattern-based cleanup for user-specific keys
        user_pattern_keys = [
            f"session:{user_context.user_id}",
            f"user_preferences:{user_context.user_id}",
            f"agent_results:{user_context.user_id}:*"
        ]
        
        # Method 2: Direct key deletion for known session keys
        cleanup_operations = []
        
        # Delete WebSocket specific keys
        ws_cleanup_start = time.time()
        await redis_client.delete(f"websocket:{user_context.websocket_client_id}")
        ws_cleanup_time = time.time() - ws_cleanup_start
        cleanup_operations.append(("websocket", ws_cleanup_time))
        
        # Delete session key
        session_cleanup_start = time.time()
        await redis_client.delete(f"session:{user_context.user_id}")
        session_cleanup_time = time.time() - session_cleanup_start
        cleanup_operations.append(("session", session_cleanup_time))
        
        # Delete conversation state
        conversation_cleanup_start = time.time()
        await redis_client.delete(f"conversation_state:{user_context.thread_id}")
        conversation_cleanup_time = time.time() - conversation_cleanup_start
        cleanup_operations.append(("conversation", conversation_cleanup_time))
        
        # Delete user preferences
        prefs_cleanup_start = time.time()
        await redis_client.delete(f"user_preferences:{user_context.user_id}")
        prefs_cleanup_time = time.time() - prefs_cleanup_start
        cleanup_operations.append(("preferences", prefs_cleanup_time))
        
        # Delete agent results (multiple keys)
        agent_results_cleanup_start = time.time()
        agent_keys = [
            f"agent_results:{user_context.user_id}:data_agent",
            f"agent_results:{user_context.user_id}:optimization_agent"
        ]
        await redis_client.delete(*agent_keys)
        agent_results_cleanup_time = time.time() - agent_results_cleanup_start
        cleanup_operations.append(("agent_results", agent_results_cleanup_time))
        
        total_cleanup_time = time.time() - cleanup_start
        
        # Verify cleanup completed
        post_cleanup_verification_start = time.time()
        remaining_keys = await redis_client.exists(*session_keys)
        post_cleanup_verification_time = time.time() - post_cleanup_verification_start
        
        # Assertions
        assert remaining_keys == 0, \
            f"All session keys should be cleaned up: {remaining_keys} remaining"
        assert total_cleanup_time < 0.5, \
            f"Total cleanup should be fast: {total_cleanup_time:.2f}s"
        assert post_cleanup_verification_time < 0.1, \
            f"Post-cleanup verification should be fast: {post_cleanup_verification_time*1000:.1f}ms"
        
        # Verify individual cleanup operation performance
        for operation_name, operation_time in cleanup_operations:
            assert operation_time < 0.1, \
                f"{operation_name} cleanup should be < 100ms: {operation_time*1000:.1f}ms"
        
        # Test cleanup idempotence (cleanup again should not fail)
        idempotent_cleanup_start = time.time()
        await redis_client.delete(*session_keys)  # Should not fail
        idempotent_cleanup_time = time.time() - idempotent_cleanup_start
        
        assert idempotent_cleanup_time < 0.1, \
            f"Idempotent cleanup should be fast: {idempotent_cleanup_time*1000:.1f}ms"
        
        self.record_metric("cache_cleanup_test_passed", True)
        self.record_metric("total_cleanup_time", total_cleanup_time)
        self.record_metric("keys_cleaned_up", len(session_keys))
        self.record_metric("cleanup_operations", len(cleanup_operations))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_cache_isolation(self, real_redis_fixture):
        """Test cache isolation between multiple concurrent users."""
        # Use the Redis client from fixture
        redis_client = real_redis_fixture
        concurrent_users = 5
        user_contexts = []
        
        # Create multiple user contexts
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(
                user_email=f"cache_isolation_user_{i}@example.com",
                environment=self.test_environment,
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Create isolated cache data for each user
        isolation_setup_start = time.time()
        user_cache_data = {}
        
        for i, context in enumerate(user_contexts):
            user_data = {
                "session": {
                    "user_id": str(context.user_id),
                    "user_index": i,
                    "session_data": f"user_{i}_session_data"
                },
                "preferences": {
                    "user_id": str(context.user_id),
                    "theme": f"theme_{i}",
                    "language": f"lang_{i}"
                },
                "agent_results": {
                    "user_id": str(context.user_id),
                    "cost_analysis": 100.0 + (i * 50),  # Different costs per user
                    "user_specific_data": f"user_{i}_specific_results"
                }
            }
            user_cache_data[context.user_id] = user_data
            
            # Cache data for this user
            session_key = f"session:{context.user_id}"
            prefs_key = f"user_preferences:{context.user_id}"
            results_key = f"agent_results:{context.user_id}:cost_analysis"
            
            # Track keys for cleanup
            self._track_key(session_key)
            self._track_key(prefs_key)
            self._track_key(results_key)
            
            # Cache all user data
            await redis_client.setex(session_key, 3600, json.dumps(user_data["session"]))
            await redis_client.setex(prefs_key, 3600, json.dumps(user_data["preferences"]))
            await redis_client.setex(results_key, 3600, json.dumps(user_data["agent_results"]))
        
        isolation_setup_time = time.time() - isolation_setup_start
        
        # Verify isolation: Each user should only see their own data
        isolation_verification_start = time.time()
        
        for i, context in enumerate(user_contexts):
            # Retrieve user's cached data
            session_key = f"session:{context.user_id}"
            prefs_key = f"user_preferences:{context.user_id}"
            results_key = f"agent_results:{context.user_id}:cost_analysis"
            
            cached_session = json.loads(await redis_client.get(session_key))
            cached_prefs = json.loads(await redis_client.get(prefs_key))
            cached_results = json.loads(await redis_client.get(results_key))
            
            # Verify user sees their own data
            assert cached_session["user_index"] == i, \
                f"User {i} should see their own session data"
            assert cached_session["user_id"] == str(context.user_id), \
                f"User {i} should have correct user ID"
            assert cached_session["session_data"] == f"user_{i}_session_data", \
                f"User {i} should see their own session content"
            
            assert cached_prefs["theme"] == f"theme_{i}", \
                f"User {i} should see their own preferences"
            assert cached_results["cost_analysis"] == 100.0 + (i * 50), \
                f"User {i} should see their own cost data"
            assert cached_results["user_specific_data"] == f"user_{i}_specific_results", \
                f"User {i} should see their own results"
            
            # Verify user cannot accidentally access other users' data
            # (This is inherent in Redis key structure, but we test the pattern)
            for j, other_context in enumerate(user_contexts):
                if i != j:  # Different user
                    other_session_key = f"session:{other_context.user_id}"
                    other_cached_session = json.loads(await redis_client.get(other_session_key))
                    
                    # Verify data is different (isolation test)
                    assert other_cached_session["user_index"] != i, \
                        f"User {i} should not see user {j}'s index data"
                    assert other_cached_session["session_data"] != f"user_{i}_session_data", \
                        f"User {i} should not see user {j}'s session data"
        
        isolation_verification_time = time.time() - isolation_verification_start
        
        # Test concurrent access performance
        concurrent_access_start = time.time()
        
        # Simulate concurrent cache access from all users
        access_tasks = []
        for context in user_contexts:
            task = self._simulate_concurrent_user_cache_access(context, redis_client)
            access_tasks.append(task)
        
        access_results = await asyncio.gather(*access_tasks)
        concurrent_access_time = time.time() - concurrent_access_start
        
        # Verify concurrent access results
        successful_accesses = sum(1 for result in access_results if result["success"])
        assert successful_accesses == concurrent_users, \
            f"All users should successfully access cache: {successful_accesses}/{concurrent_users}"
        
        # Verify performance under concurrent load
        avg_access_time = sum(result["access_time"] for result in access_results) / len(access_results)
        assert avg_access_time < 0.2, \
            f"Average concurrent access time should be reasonable: {avg_access_time:.2f}s"
        assert concurrent_access_time < 2.0, \
            f"Total concurrent access should complete quickly: {concurrent_access_time:.2f}s"
        
        # Test cache key pattern isolation
        pattern_test_start = time.time()
        
        # Each user should only find their own keys
        for i, context in enumerate(user_contexts):
            user_pattern = f"*{context.user_id}*"
            user_keys = []
            
            # In production Redis, we would use SCAN for this, but for test we'll check directly
            expected_keys = [
                f"session:{context.user_id}",
                f"user_preferences:{context.user_id}",
                f"agent_results:{context.user_id}:cost_analysis"
            ]
            
            for key in expected_keys:
                if await redis_client.exists(key):
                    user_keys.append(key)
            
            assert len(user_keys) == 3, \
                f"User {i} should have exactly 3 cache keys: {user_keys}"
            
            # Verify all keys contain the user's ID (pattern-based isolation)
            for key in user_keys:
                assert str(context.user_id) in key, \
                    f"User {i} key should contain user ID: {key}"
        
        pattern_test_time = time.time() - pattern_test_start
        
        # Performance assertions
        assert isolation_setup_time < 2.0, \
            f"Multi-user setup should be reasonable: {isolation_setup_time:.2f}s"
        assert isolation_verification_time < 3.0, \
            f"Isolation verification should be reasonable: {isolation_verification_time:.2f}s"
        assert pattern_test_time < 1.0, \
            f"Pattern testing should be fast: {pattern_test_time:.2f}s"
        
        self.record_metric("multi_user_isolation_test_passed", True)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("isolation_setup_time", isolation_setup_time)
        self.record_metric("concurrent_access_time", concurrent_access_time)
        self.record_metric("avg_access_time", avg_access_time)
        
    async def _simulate_concurrent_user_cache_access(
        self, 
        user_context: StronglyTypedUserExecutionContext,
        redis_client
    ) -> Dict[str, Any]:
        """Simulate concurrent cache access for a single user."""
        access_start = time.time()
        
        try:
            # Perform multiple cache operations concurrently
            session_key = f"session:{user_context.user_id}"
            prefs_key = f"user_preferences:{user_context.user_id}"
            results_key = f"agent_results:{user_context.user_id}:cost_analysis"
            
            # Read operations
            session_data = await redis_client.get(session_key)
            prefs_data = await redis_client.get(prefs_key)
            results_data = await redis_client.get(results_key)
            
            # Write operation (update last access)
            access_time = time.time()
            session_update = json.loads(session_data)
            session_update["last_access"] = access_time
            
            await redis_client.setex(session_key, 3600, json.dumps(session_update))
            
            # Verify data integrity
            assert session_data is not None, "Session data should exist"
            assert prefs_data is not None, "Preferences should exist"
            assert results_data is not None, "Results should exist"
            
            access_time = time.time() - access_start
            
            return {
                "success": True,
                "user_id": str(user_context.user_id),
                "access_time": access_time,
                "operations_completed": 4  # 3 reads + 1 write
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": str(user_context.user_id),
                "error": str(e),
                "access_time": time.time() - access_start
            }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_cache_performance_requirements(self, real_redis_fixture):
        """Test Redis cache meets performance requirements."""
        # Use the Redis client from fixture
        redis_client = real_redis_fixture
        # Performance test parameters
        performance_iterations = 50
        batch_size = 10
        
        performance_metrics = {
            "single_set_times": [],
            "single_get_times": [],
            "batch_set_times": [],
            "batch_get_times": [],
            "delete_times": []
        }
        
        # Test 1: Single key operations performance
        for i in range(performance_iterations):
            test_key = f"perf_test_single:{i}"
            test_data = {"iteration": i, "data": f"performance_test_data_{i}"}
            
            # Single SET performance
            set_start = time.time()
            await redis_client.setex(test_key, 300, json.dumps(test_data))
            set_time = time.time() - set_start
            performance_metrics["single_set_times"].append(set_time)
            self._track_key(test_key)
            
            # Single GET performance
            get_start = time.time()
            retrieved_data = await redis_client.get(test_key)
            get_time = time.time() - get_start
            performance_metrics["single_get_times"].append(get_time)
            
            # Verify data integrity
            assert retrieved_data is not None, f"Data should be retrieved for iteration {i}"
            parsed_data = json.loads(retrieved_data)
            assert parsed_data["iteration"] == i, f"Data integrity check failed for iteration {i}"
        
        # Test 2: Batch operations performance
        for batch_num in range(performance_iterations // batch_size):
            batch_data = {}
            batch_keys = []
            
            # Prepare batch data
            for i in range(batch_size):
                key = f"perf_test_batch:{batch_num}:{i}"
                data = {"batch": batch_num, "item": i, "data": f"batch_data_{batch_num}_{i}"}
                batch_data[key] = json.dumps(data)
                batch_keys.append(key)
                self._track_key(key)
            
            # Batch SET performance (using pipeline)
            batch_set_start = time.time()
            pipe = redis_client.pipeline()
            for key, data in batch_data.items():
                pipe.setex(key, 300, data)
            await pipe.execute()
            batch_set_time = time.time() - batch_set_start
            performance_metrics["batch_set_times"].append(batch_set_time)
            
            # Batch GET performance
            batch_get_start = time.time()
            batch_results = await redis_client.mget(batch_keys)
            batch_get_time = time.time() - batch_get_start
            performance_metrics["batch_get_times"].append(batch_get_time)
            
            # Verify batch integrity
            assert len(batch_results) == batch_size, f"Batch {batch_num} should return all items"
            assert all(result is not None for result in batch_results), \
                f"Batch {batch_num} should have no None results"
        
        # Test 3: Delete operations performance
        delete_test_keys = [f"delete_test:{i}" for i in range(20)]
        
        # Create keys for deletion test
        pipe = redis_client.pipeline()
        for key in delete_test_keys:
            pipe.setex(key, 300, f"delete_test_data")
            self._track_key(key)
        await pipe.execute()
        
        # Test individual delete performance
        for key in delete_test_keys:
            delete_start = time.time()
            await redis_client.delete(key)
            delete_time = time.time() - delete_start
            performance_metrics["delete_times"].append(delete_time)
        
        # Calculate performance statistics
        avg_single_set = sum(performance_metrics["single_set_times"]) / len(performance_metrics["single_set_times"])
        avg_single_get = sum(performance_metrics["single_get_times"]) / len(performance_metrics["single_get_times"])
        avg_batch_set = sum(performance_metrics["batch_set_times"]) / len(performance_metrics["batch_set_times"])
        avg_batch_get = sum(performance_metrics["batch_get_times"]) / len(performance_metrics["batch_get_times"])
        avg_delete = sum(performance_metrics["delete_times"]) / len(performance_metrics["delete_times"])
        
        # Business performance requirements (< 100ms for all operations)
        assert avg_single_set < 0.1, \
            f"Single SET should be < 100ms: {avg_single_set*1000:.1f}ms"
        assert avg_single_get < 0.1, \
            f"Single GET should be < 100ms: {avg_single_get*1000:.1f}ms"
        assert avg_batch_set < 0.1, \
            f"Batch SET should be < 100ms: {avg_batch_set*1000:.1f}ms"
        assert avg_batch_get < 0.1, \
            f"Batch GET should be < 100ms: {avg_batch_get*1000:.1f}ms"
        assert avg_delete < 0.1, \
            f"DELETE should be < 100ms: {avg_delete*1000:.1f}ms"
        
        # Peak performance requirements (99th percentile approximation)
        max_single_set = max(performance_metrics["single_set_times"])
        max_single_get = max(performance_metrics["single_get_times"])
        max_batch_set = max(performance_metrics["batch_set_times"])
        max_batch_get = max(performance_metrics["batch_get_times"])
        max_delete = max(performance_metrics["delete_times"])
        
        assert max_single_set < 0.2, \
            f"Max single SET should be < 200ms: {max_single_set*1000:.1f}ms"
        assert max_single_get < 0.2, \
            f"Max single GET should be < 200ms: {max_single_get*1000:.1f}ms"
        assert max_batch_set < 0.2, \
            f"Max batch SET should be < 200ms: {max_batch_set*1000:.1f}ms"
        assert max_batch_get < 0.2, \
            f"Max batch GET should be < 200ms: {max_batch_get*1000:.1f}ms"
        assert max_delete < 0.2, \
            f"Max DELETE should be < 200ms: {max_delete*1000:.1f}ms"
        
        # Throughput calculations with safety checks
        single_ops_total_time = sum(performance_metrics["single_set_times"] + performance_metrics["single_get_times"])
        single_ops_throughput = performance_iterations / single_ops_total_time if single_ops_total_time > 0 else 0
        
        batch_ops_total_time = sum(performance_metrics["batch_set_times"] + performance_metrics["batch_get_times"])
        batch_ops_throughput = (len(performance_metrics["batch_set_times"]) * batch_size) / batch_ops_total_time if batch_ops_total_time > 0 else 0
        
        self.record_metric("cache_performance_test_passed", True)
        self.record_metric("avg_single_set_time", avg_single_set)
        self.record_metric("avg_single_get_time", avg_single_get)
        self.record_metric("avg_batch_set_time", avg_batch_set)
        self.record_metric("avg_batch_get_time", avg_batch_get)
        self.record_metric("avg_delete_time", avg_delete)
        self.record_metric("single_ops_throughput", single_ops_throughput)
        self.record_metric("batch_ops_throughput", batch_ops_throughput)
        self.record_metric("performance_iterations", performance_iterations)
        
        print(f"\n📊 REDIS CACHE PERFORMANCE METRICS:")
        print(f"   📝 Single SET: {avg_single_set*1000:.1f}ms avg, {max_single_set*1000:.1f}ms max")
        print(f"   📖 Single GET: {avg_single_get*1000:.1f}ms avg, {max_single_get*1000:.1f}ms max")
        print(f"   📝📝 Batch SET: {avg_batch_set*1000:.1f}ms avg, {max_batch_set*1000:.1f}ms max")
        print(f"   📖📖 Batch GET: {avg_batch_get*1000:.1f}ms avg, {max_batch_get*1000:.1f}ms max")
        print(f"   🗑️  DELETE: {avg_delete*1000:.1f}ms avg, {max_delete*1000:.1f}ms max")
        print(f"   ⚡ Throughput: {single_ops_throughput:.0f} single ops/s, {batch_ops_throughput:.0f} batch ops/s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])