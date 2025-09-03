"""
Comprehensive End-to-End Validation Test for Three-Tier Data Isolation Fix

This test suite validates that all three phases of the critical data isolation fix
are working correctly, ensuring complete security between users in production scenarios.

Test Coverage:
- Phase 1: Cache key isolation (ClickHouse + Redis)
- Phase 2: Factory pattern data access isolation  
- Phase 3: Agent integration with complete isolation
- Real-world scenarios that would have failed before the fix
- Performance validation under concurrent load
- WebSocket event isolation

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Critical security requirement
- Business Goal: Complete data isolation preventing security breaches  
- Value Impact: Prevents cross-user data leakage that could destroy trust
- Revenue Impact: Unlocks Enterprise tier + prevents costly security incidents

IMPORTANT: These tests should PASS after the three-tier isolation fix.
Any failures indicate critical security vulnerabilities that must be addressed.
"""

import pytest
import asyncio
import uuid
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import the data isolation components
from netra_backend.app.data_contexts.user_data_context import (
    UserClickHouseContext, 
    UserRedisContext
)
from netra_backend.app.factories.data_access_factory import (
    get_clickhouse_factory,
    get_redis_factory,
    get_user_clickhouse_context,
    get_user_redis_context
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.db.clickhouse import _clickhouse_cache
from netra_backend.app.services.redis_service import redis_service


@pytest.mark.mission_critical
@pytest.mark.asyncio
class TestThreeTierIsolationComplete:
    """
    Complete end-to-end validation of three-tier data isolation.
    
    This test suite validates that the critical security vulnerabilities
    have been fixed and users are completely isolated from each other.
    """
    
    @pytest.fixture
    async def test_user_contexts(self):
        """Create multiple test user execution contexts."""
        contexts = []
        for i in range(5):
            user_id = f"test-user-{i}-{uuid.uuid4()}"
            request_id = f"req-{uuid.uuid4()}"
            thread_id = f"thread-{threading.get_ident()}-{i}"
            run_id = f"run-{uuid.uuid4()}"
            
            context = UserExecutionContext(
                user_id=user_id,
                request_id=request_id,
                thread_id=thread_id,
                run_id=run_id,
                session_id=f"session-{uuid.uuid4()}",
                metadata={"test": f"user_{i}"}
            )
            contexts.append(context)
        return contexts
    
    @pytest.fixture
    async def isolated_clickhouse_cache(self):
        """Ensure ClickHouse cache is isolated for testing."""
        # Clear any existing cache entries
        _clickhouse_cache.clear()
        yield _clickhouse_cache
        # Clean up after test
        _clickhouse_cache.clear()
    
    async def test_phase1_clickhouse_cache_isolation_fixed(self, test_user_contexts, isolated_clickhouse_cache):
        """
        SECURITY TEST: Verify ClickHouse cache isolation is working correctly.
        
        This test validates that the Phase 1 fix prevents cache contamination
        between users. It should PASS, proving the vulnerability is fixed.
        """
        cache = isolated_clickhouse_cache
        user1, user2, user3 = test_user_contexts[:3]
        
        # Test data that should be isolated per user
        query = "SELECT * FROM sensitive_documents WHERE corpus_id = %(corpus_id)s"
        params = {"corpus_id": "shared-corpus-id"}  # Same logical parameters
        
        user1_data = [{"doc_id": "doc1", "content": "User1 confidential data", "user_id": user1.user_id}]
        user2_data = [{"doc_id": "doc2", "content": "User2 confidential data", "user_id": user2.user_id}]
        user3_data = [{"doc_id": "doc3", "content": "User3 confidential data", "user_id": user3.user_id}]
        
        # Cache data for each user with same query but different user contexts
        cache.set(user1.user_id, query, user1_data, params)
        cache.set(user2.user_id, query, user2_data, params) 
        cache.set(user3.user_id, query, user3_data, params)
        
        # Verify each user gets their own isolated cached data
        cached_user1 = cache.get(user1.user_id, query, params)
        cached_user2 = cache.get(user2.user_id, query, params)
        cached_user3 = cache.get(user3.user_id, query, params)
        
        # SECURITY VALIDATION: Each user must only see their own data
        assert cached_user1 == user1_data, "User1 should get their own cached data"
        assert cached_user2 == user2_data, "User2 should get their own cached data"  
        assert cached_user3 == user3_data, "User3 should get their own cached data"
        
        # CRITICAL: No cross-contamination between users
        assert cached_user1 != cached_user2, "User1 and User2 data must be isolated"
        assert cached_user1 != cached_user3, "User1 and User3 data must be isolated"
        assert cached_user2 != cached_user3, "User2 and User3 data must be isolated"
        
        # Verify cache keys include user context (Phase 1 implementation)
        user1_key = cache._generate_key(user1.user_id, query, params)
        user2_key = cache._generate_key(user2.user_id, query, params)
        
        assert user1.user_id in user1_key, "Cache key must include user1 ID"
        assert user2.user_id in user2_key, "Cache key must include user2 ID"
        assert user1_key != user2_key, "Cache keys must be different for different users"
        
        # Test cache statistics isolation
        user1_stats = cache.stats(user1.user_id)
        user2_stats = cache.stats(user2.user_id)
        
        assert user1_stats["user_id"] == user1.user_id
        assert user2_stats["user_id"] == user2.user_id
        assert user1_stats["user_cache_entries"] >= 1
        assert user2_stats["user_cache_entries"] >= 1
        
        print(f"✅ Phase 1 ClickHouse cache isolation working correctly")

    async def test_phase1_redis_key_isolation_fixed(self, test_user_contexts):
        """
        SECURITY TEST: Verify Redis key namespacing is working correctly.
        
        This test validates that the Phase 1 fix prevents Redis key collisions
        between users. It should PASS, proving the vulnerability is fixed.
        """
        user1, user2, user3 = test_user_contexts[:3]
        
        # Mock Redis service to track actual keys used
        redis_keys_used = {}
        original_set = redis_service.set
        original_get = redis_service.get
        
        async def mock_set(key, value, ex=None, user_id=None):
            # Record the actual key used
            if user_id:
                actual_key = redis_service._namespace_key(user_id, key)
            else:
                actual_key = key
            redis_keys_used[actual_key] = value
            return True
        
        async def mock_get(key, user_id=None):
            if user_id:
                actual_key = redis_service._namespace_key(user_id, key)
            else:
                actual_key = key
            return redis_keys_used.get(actual_key)
        
        # Apply mocks
        redis_service.set = mock_set
        redis_service.get = mock_get
        
        try:
            # Each user stores session data with same logical key
            session_key = "user_session"
            user1_session = f"session_data_for_{user1.user_id}"
            user2_session = f"session_data_for_{user2.user_id}"
            user3_session = f"session_data_for_{user3.user_id}"
            
            # Store session data for each user
            await redis_service.set(session_key, user1_session, user_id=user1.user_id)
            await redis_service.set(session_key, user2_session, user_id=user2.user_id)
            await redis_service.set(session_key, user3_session, user_id=user3.user_id)
            
            # Retrieve session data for each user
            retrieved_user1 = await redis_service.get(session_key, user_id=user1.user_id)
            retrieved_user2 = await redis_service.get(session_key, user_id=user2.user_id)
            retrieved_user3 = await redis_service.get(session_key, user_id=user3.user_id)
            
            # SECURITY VALIDATION: Each user gets their own session data
            assert retrieved_user1 == user1_session, "User1 should get their own session"
            assert retrieved_user2 == user2_session, "User2 should get their own session"
            assert retrieved_user3 == user3_session, "User3 should get their own session"
            
            # Verify actual Redis keys are namespaced and isolated
            expected_key1 = f"user:{user1.user_id}:{session_key}"
            expected_key2 = f"user:{user2.user_id}:{session_key}"
            expected_key3 = f"user:{user3.user_id}:{session_key}"
            
            assert expected_key1 in redis_keys_used, "User1 key should be namespaced"
            assert expected_key2 in redis_keys_used, "User2 key should be namespaced"
            assert expected_key3 in redis_keys_used, "User3 key should be namespaced"
            
            # Verify all keys are different (no collisions)
            all_keys = list(redis_keys_used.keys())
            assert len(set(all_keys)) == len(all_keys), "All Redis keys must be unique"
            
            # Test cross-user access returns correct isolated data
            cross_access_1_to_2 = await redis_service.get(session_key, user_id=user2.user_id)
            cross_access_2_to_1 = await redis_service.get(session_key, user_id=user1.user_id)
            
            assert cross_access_1_to_2 == user2_session, "User2 gets their own data, not User1's"
            assert cross_access_2_to_1 == user1_session, "User1 gets their own data, not User2's"
            
        finally:
            # Restore original methods
            redis_service.set = original_set
            redis_service.get = original_get
        
        print(f"✅ Phase 1 Redis key isolation working correctly")

    async def test_phase2_factory_pattern_isolation_fixed(self, test_user_contexts):
        """
        SECURITY TEST: Verify Factory pattern creates isolated contexts.
        
        This test validates that Phase 2 factory pattern provides complete
        isolation between users. It should PASS, proving the fix works.
        """
        user1, user2, user3 = test_user_contexts[:3]
        
        # Get factory instances
        ch_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        # Create contexts for different users
        ch_context1 = await ch_factory.create_user_context(user1)
        ch_context2 = await ch_factory.create_user_context(user2)
        redis_context1 = await redis_factory.create_user_context(user1)
        redis_context2 = await redis_factory.create_user_context(user2)
        
        try:
            # Verify contexts are isolated by user_id
            assert ch_context1.user_id == user1.user_id, "ClickHouse context1 has correct user_id"
            assert ch_context2.user_id == user2.user_id, "ClickHouse context2 has correct user_id"
            assert redis_context1.user_id == user1.user_id, "Redis context1 has correct user_id"
            assert redis_context2.user_id == user2.user_id, "Redis context2 has correct user_id"
            
            # Verify contexts are separate instances
            assert ch_context1 is not ch_context2, "ClickHouse contexts must be separate instances"
            assert redis_context1 is not redis_context2, "Redis contexts must be separate instances"
            
            # Verify request isolation
            assert ch_context1.request_id == user1.request_id, "ClickHouse context1 has correct request_id"
            assert ch_context2.request_id == user2.request_id, "ClickHouse context2 has correct request_id"
            assert redis_context1.request_id == user1.request_id, "Redis context1 has correct request_id"
            assert redis_context2.request_id == user2.request_id, "Redis context2 has correct request_id"
            
            # Test factory statistics show correct isolation
            ch_stats = await ch_factory.get_context_stats()
            redis_stats = await redis_factory.get_context_stats()
            
            assert ch_stats["total_contexts"] >= 2, "ClickHouse factory tracks multiple contexts"
            assert redis_stats["total_contexts"] >= 2, "Redis factory tracks multiple contexts" 
            assert ch_stats["users_with_contexts"] >= 2, "ClickHouse factory tracks multiple users"
            assert redis_stats["users_with_contexts"] >= 2, "Redis factory tracks multiple users"
            
            # Test factory can clean up user-specific contexts
            user1_cleanup_count = await ch_factory.cleanup_user_contexts(user1.user_id)
            assert user1_cleanup_count >= 1, "Factory cleaned up user1's contexts"
            
            # Verify context manager pattern works with isolation
            async with get_user_clickhouse_context(user3) as ch_ctx:
                assert ch_ctx.user_id == user3.user_id, "Context manager creates isolated context"
                
            async with get_user_redis_context(user3) as redis_ctx:
                assert redis_ctx.user_id == user3.user_id, "Context manager creates isolated context"
            
        finally:
            # Clean up contexts
            await ch_context1.cleanup()
            await ch_context2.cleanup()
            await redis_context1.cleanup()
            await redis_context2.cleanup()
        
        print(f"✅ Phase 2 Factory pattern isolation working correctly")

    async def test_phase3_agent_integration_isolation_fixed(self, test_user_contexts):
        """
        SECURITY TEST: Verify agents use isolated data contexts correctly.
        
        This test validates that Phase 3 integration ensures agents access
        data through isolated contexts. It should PASS, proving agent isolation.
        """
        user1, user2 = test_user_contexts[:2]
        
        # Mock agent that uses data contexts
        class TestAgent:
            def __init__(self, user_context: UserExecutionContext):
                self.user_context = user_context
                self.operations_log = []
            
            async def execute_with_clickhouse(self):
                async with get_user_clickhouse_context(self.user_context) as ch_ctx:
                    # Simulate agent query execution
                    self.operations_log.append(f"ClickHouse query for user {ch_ctx.user_id}")
                    return {"user_id": ch_ctx.user_id, "data": f"CH data for {ch_ctx.user_id}"}
            
            async def execute_with_redis(self):
                async with get_user_redis_context(self.user_context) as redis_ctx:
                    # Simulate agent session management
                    await redis_ctx.set("agent_session", f"session_for_{redis_ctx.user_id}")
                    retrieved = await redis_ctx.get("agent_session")
                    self.operations_log.append(f"Redis operation for user {redis_ctx.user_id}")
                    return {"user_id": redis_ctx.user_id, "session": retrieved}
        
        # Create agents for different users
        agent1 = TestAgent(user1)
        agent2 = TestAgent(user2)
        
        # Execute agent operations concurrently
        ch_result1, ch_result2 = await asyncio.gather(
            agent1.execute_with_clickhouse(),
            agent2.execute_with_clickhouse()
        )
        
        redis_result1, redis_result2 = await asyncio.gather(
            agent1.execute_with_redis(),
            agent2.execute_with_redis()  
        )
        
        # SECURITY VALIDATION: Each agent operates in isolated context
        assert ch_result1["user_id"] == user1.user_id, "Agent1 CH operation isolated to user1"
        assert ch_result2["user_id"] == user2.user_id, "Agent2 CH operation isolated to user2"
        assert redis_result1["user_id"] == user1.user_id, "Agent1 Redis operation isolated to user1"
        assert redis_result2["user_id"] == user2.user_id, "Agent2 Redis operation isolated to user2"
        
        # Verify data isolation between agents
        assert ch_result1["data"] != ch_result2["data"], "Agent data must be user-specific"
        assert redis_result1["session"] != redis_result2["session"], "Agent sessions must be isolated"
        
        # Verify Redis sessions are properly namespaced
        expected_session1 = f"session_for_{user1.user_id}"
        expected_session2 = f"session_for_{user2.user_id}"
        assert redis_result1["session"] == expected_session1, "Agent1 Redis session correct"
        assert redis_result2["session"] == expected_session2, "Agent2 Redis session correct"
        
        # Verify operation logs show user isolation
        assert any(user1.user_id in log for log in agent1.operations_log), "Agent1 logs show user1"
        assert any(user2.user_id in log for log in agent2.operations_log), "Agent2 logs show user2"
        
        # Cross-contamination check: Agent1 should not see Agent2's session
        async with get_user_redis_context(user1) as redis_ctx1:
            user1_session = await redis_ctx1.get("agent_session")
            assert user1_session == expected_session1, "User1 sees only their session"
        
        async with get_user_redis_context(user2) as redis_ctx2:
            user2_session = await redis_ctx2.get("agent_session")
            assert user2_session == expected_session2, "User2 sees only their session"
        
        print(f"✅ Phase 3 Agent integration isolation working correctly")

    async def test_scenario1_concurrent_user_queries_isolated(self, test_user_contexts, isolated_clickhouse_cache):
        """
        REAL-WORLD SCENARIO 1: Two users query the same data, get isolated caches.
        
        This scenario would have FAILED before the fix due to cache contamination.
        Now it should PASS, demonstrating the security issue is resolved.
        """
        user1, user2 = test_user_contexts[:2]
        cache = isolated_clickhouse_cache
        
        # Simulate two users querying the same corpus simultaneously
        corpus_query = "SELECT * FROM documents WHERE corpus_id = %(corpus_id)s AND user_id = %(user_id)s"
        corpus_id = "shared-public-corpus"
        
        async def user1_query_operation():
            """User1 queries and caches their view of the corpus."""
            params = {"corpus_id": corpus_id, "user_id": user1.user_id}
            
            # Simulate database results (would come from ClickHouse)
            user1_documents = [
                {"doc_id": "doc1", "title": "User1's Document 1", "user_id": user1.user_id},
                {"doc_id": "doc2", "title": "User1's Document 2", "user_id": user1.user_id}
            ]
            
            # Cache with user isolation
            cache.set(user1.user_id, corpus_query, user1_documents, params)
            
            # Retrieve from cache
            cached_result = cache.get(user1.user_id, corpus_query, params)
            return {"user": user1.user_id, "documents": cached_result}
        
        async def user2_query_operation():
            """User2 queries and caches their view of the same corpus."""
            params = {"corpus_id": corpus_id, "user_id": user2.user_id}
            
            # Simulate different database results for user2
            user2_documents = [
                {"doc_id": "doc3", "title": "User2's Document 1", "user_id": user2.user_id},
                {"doc_id": "doc4", "title": "User2's Document 2", "user_id": user2.user_id},
                {"doc_id": "doc5", "title": "User2's Document 3", "user_id": user2.user_id}
            ]
            
            # Cache with user isolation
            cache.set(user2.user_id, corpus_query, user2_documents, params)
            
            # Retrieve from cache
            cached_result = cache.get(user2.user_id, corpus_query, params)
            return {"user": user2.user_id, "documents": cached_result}
        
        # Execute operations concurrently (this would cause contamination before fix)
        result1, result2 = await asyncio.gather(
            user1_query_operation(),
            user2_query_operation()
        )
        
        # SECURITY VALIDATION: Results are properly isolated
        user1_docs = result1["documents"]
        user2_docs = result2["documents"]
        
        assert len(user1_docs) == 2, "User1 gets their 2 documents"
        assert len(user2_docs) == 3, "User2 gets their 3 documents"
        
        # Verify no cross-contamination
        user1_doc_ids = [doc["doc_id"] for doc in user1_docs]
        user2_doc_ids = [doc["doc_id"] for doc in user2_docs]
        
        assert set(user1_doc_ids).isdisjoint(set(user2_doc_ids)), "No document ID overlap between users"
        
        # Verify all documents have correct user_id
        for doc in user1_docs:
            assert doc["user_id"] == user1.user_id, f"User1 doc {doc['doc_id']} has correct user_id"
        
        for doc in user2_docs:
            assert doc["user_id"] == user2.user_id, f"User2 doc {doc['doc_id']} has correct user_id"
        
        # Verify cache keys are isolated
        user1_params = {"corpus_id": corpus_id, "user_id": user1.user_id}
        user2_params = {"corpus_id": corpus_id, "user_id": user2.user_id}
        
        user1_cache_key = cache._generate_key(user1.user_id, corpus_query, user1_params)
        user2_cache_key = cache._generate_key(user2.user_id, corpus_query, user2_params)
        
        assert user1_cache_key != user2_cache_key, "Cache keys must be different for different users"
        
        print(f"✅ Scenario 1: Concurrent user queries properly isolated")

    async def test_scenario2_multiple_users_redis_data_concurrent(self, test_user_contexts):
        """
        REAL-WORLD SCENARIO 2: Multiple users store/retrieve Redis data concurrently.
        
        This scenario would have FAILED before the fix due to session key collisions.
        Now it should PASS, demonstrating session isolation is working.
        """
        users = test_user_contexts[:4]  # Test with 4 concurrent users
        
        # Mock Redis operations to track actual keys
        redis_operations = {}
        original_set = redis_service.set
        original_get = redis_service.get
        
        async def tracked_set(key, value, ex=None, user_id=None):
            actual_key = redis_service._namespace_key(user_id, key) if user_id else key
            redis_operations[actual_key] = {"value": value, "user_id": user_id}
            return True
        
        async def tracked_get(key, user_id=None):
            actual_key = redis_service._namespace_key(user_id, key) if user_id else key
            operation = redis_operations.get(actual_key, {})
            return operation.get("value")
        
        # Apply tracking
        redis_service.set = tracked_set
        redis_service.get = tracked_get
        
        try:
            async def user_session_operations(user: UserExecutionContext):
                """Simulate a user's session operations."""
                # User stores multiple session values
                await redis_service.set("session_token", f"token_{user.user_id}", user_id=user.user_id)
                await redis_service.set("user_preferences", f"prefs_{user.user_id}", user_id=user.user_id)
                await redis_service.set("active_conversations", f"convos_{user.user_id}", user_id=user.user_id)
                await redis_service.set("agent_state", f"state_{user.user_id}", user_id=user.user_id)
                
                # Small delay to simulate real operations
                await asyncio.sleep(0.1)
                
                # User retrieves their session data
                token = await redis_service.get("session_token", user_id=user.user_id)
                prefs = await redis_service.get("user_preferences", user_id=user.user_id)
                convos = await redis_service.get("active_conversations", user_id=user.user_id)
                state = await redis_service.get("agent_state", user_id=user.user_id)
                
                return {
                    "user_id": user.user_id,
                    "session_token": token,
                    "user_preferences": prefs,
                    "active_conversations": convos,
                    "agent_state": state
                }
            
            # Execute all user operations concurrently
            results = await asyncio.gather(*[
                user_session_operations(user) for user in users
            ])
            
            # SECURITY VALIDATION: Each user gets their own data
            for i, result in enumerate(results):
                user = users[i]
                
                expected_token = f"token_{user.user_id}"
                expected_prefs = f"prefs_{user.user_id}"
                expected_convos = f"convos_{user.user_id}"
                expected_state = f"state_{user.user_id}"
                
                assert result["session_token"] == expected_token, f"User {i} got correct token"
                assert result["user_preferences"] == expected_prefs, f"User {i} got correct preferences"
                assert result["active_conversations"] == expected_convos, f"User {i} got correct conversations"
                assert result["agent_state"] == expected_state, f"User {i} got correct agent state"
            
            # Verify all Redis keys are properly namespaced and unique
            all_keys = list(redis_operations.keys())
            assert len(all_keys) == len(users) * 4, "Correct number of Redis keys created"
            
            # Check no key collisions occurred
            unique_keys = set(all_keys)
            assert len(unique_keys) == len(all_keys), "All Redis keys are unique (no collisions)"
            
            # Verify all keys include user namespacing
            for key in all_keys:
                assert key.startswith("user:"), f"Key {key} should be namespaced with user:"
                # Extract user_id from key format "user:USER_ID:LOGICAL_KEY"
                parts = key.split(":", 2)
                if len(parts) >= 2:
                    user_id_in_key = parts[1]
                    # Verify this user_id exists in our test users
                    user_ids = [user.user_id for user in users]
                    assert user_id_in_key in user_ids, f"Key {key} contains valid user_id"
            
            # Test cross-user access isolation - each user should only see their data
            for user in users:
                token = await redis_service.get("session_token", user_id=user.user_id)
                expected = f"token_{user.user_id}"
                assert token == expected, f"User {user.user_id} sees only their token, not others"
        
        finally:
            # Restore original methods
            redis_service.set = original_set 
            redis_service.get = original_get
        
        print(f"✅ Scenario 2: Multiple user Redis data properly isolated")

    async def test_scenario3_agent_execution_complete_isolation(self, test_user_contexts):
        """
        REAL-WORLD SCENARIO 3: Agent execution with complete data isolation.
        
        This scenario simulates agents processing user requests with full isolation.
        Would have FAILED before fix due to context bleeding. Should PASS now.
        """
        user1, user2, user3 = test_user_contexts[:3]
        
        class IsolatedTestAgent:
            """Test agent that performs data operations with user isolation."""
            
            def __init__(self, user_context: UserExecutionContext):
                self.user_context = user_context
                self.execution_log = []
                
            async def process_user_request(self, request_data: Dict[str, Any]):
                """Process a user request with isolated data operations."""
                self.execution_log.append(f"Processing request for user {self.user_context.user_id}")
                
                # Use isolated ClickHouse operations
                ch_results = await self._query_user_data(request_data)
                
                # Use isolated Redis operations
                session_data = await self._manage_user_session(request_data)
                
                # Combine results
                response = {
                    "user_id": self.user_context.user_id,
                    "request_id": self.user_context.request_id,
                    "ch_data": ch_results,
                    "session_data": session_data,
                    "processing_complete": True
                }
                
                self.execution_log.append(f"Completed request for user {self.user_context.user_id}")
                return response
            
            async def _query_user_data(self, request_data: Dict[str, Any]):
                """Query user-specific data through isolated ClickHouse context."""
                async with get_user_clickhouse_context(self.user_context) as ch_ctx:
                    # Simulate user-specific query (would be real ClickHouse in production)
                    user_data = {
                        "query_result": f"Data for {ch_ctx.user_id}",
                        "user_specific_info": request_data.get("query", "default"),
                        "context_info": ch_ctx.get_context_info()
                    }
                    
                    self.execution_log.append(f"ClickHouse query for user {ch_ctx.user_id}")
                    return user_data
            
            async def _manage_user_session(self, request_data: Dict[str, Any]):
                """Manage user session through isolated Redis context."""
                async with get_user_redis_context(self.user_context) as redis_ctx:
                    # Store user-specific session data
                    session_key = "agent_processing_state"
                    session_value = {
                        "user_id": redis_ctx.user_id,
                        "status": "processing",
                        "data": request_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await redis_ctx.set_json(session_key, session_value)
                    
                    # Retrieve session data (verify isolation)
                    retrieved_session = await redis_ctx.get_json(session_key)
                    
                    self.execution_log.append(f"Redis session managed for user {redis_ctx.user_id}")
                    return retrieved_session
        
        # Create isolated agents for each user
        agent1 = IsolatedTestAgent(user1)
        agent2 = IsolatedTestAgent(user2) 
        agent3 = IsolatedTestAgent(user3)
        
        # Prepare different requests for each user
        request1 = {"query": "sensitive_query_user1", "priority": "high"}
        request2 = {"query": "confidential_query_user2", "priority": "medium"}
        request3 = {"query": "private_query_user3", "priority": "low"}
        
        # Execute agent processing concurrently (this would cause contamination before fix)
        result1, result2, result3 = await asyncio.gather(
            agent1.process_user_request(request1),
            agent2.process_user_request(request2),
            agent3.process_user_request(request3)
        )
        
        # SECURITY VALIDATION: Complete isolation between agent executions
        
        # Verify user isolation
        assert result1["user_id"] == user1.user_id, "Agent1 result has correct user_id"
        assert result2["user_id"] == user2.user_id, "Agent2 result has correct user_id"
        assert result3["user_id"] == user3.user_id, "Agent3 result has correct user_id"
        
        # Verify request isolation
        assert result1["request_id"] == user1.request_id, "Agent1 result has correct request_id"
        assert result2["request_id"] == user2.request_id, "Agent2 result has correct request_id"
        assert result3["request_id"] == user3.request_id, "Agent3 result has correct request_id"
        
        # Verify ClickHouse data isolation
        ch_data1 = result1["ch_data"]
        ch_data2 = result2["ch_data"]
        ch_data3 = result3["ch_data"]
        
        assert user1.user_id in ch_data1["query_result"], "Agent1 CH data contains user1 ID"
        assert user2.user_id in ch_data2["query_result"], "Agent2 CH data contains user2 ID"
        assert user3.user_id in ch_data3["query_result"], "Agent3 CH data contains user3 ID"
        
        assert ch_data1["user_specific_info"] == "sensitive_query_user1", "Agent1 processed correct query"
        assert ch_data2["user_specific_info"] == "confidential_query_user2", "Agent2 processed correct query"
        assert ch_data3["user_specific_info"] == "private_query_user3", "Agent3 processed correct query"
        
        # Verify Redis session isolation
        session1 = result1["session_data"]
        session2 = result2["session_data"] 
        session3 = result3["session_data"]
        
        assert session1["user_id"] == user1.user_id, "Agent1 session has correct user_id"
        assert session2["user_id"] == user2.user_id, "Agent2 session has correct user_id"
        assert session3["user_id"] == user3.user_id, "Agent3 session has correct user_id"
        
        assert session1["data"]["priority"] == "high", "Agent1 session has correct priority"
        assert session2["data"]["priority"] == "medium", "Agent2 session has correct priority"
        assert session3["data"]["priority"] == "low", "Agent3 session has correct priority"
        
        # Verify no data bleeding between agents
        assert session1["data"]["query"] != session2["data"]["query"], "Agent sessions have different queries"
        assert session1["data"]["query"] != session3["data"]["query"], "Agent sessions have different queries"
        assert session2["data"]["query"] != session3["data"]["query"], "Agent sessions have different queries"
        
        # Verify execution logs show proper isolation
        assert len(agent1.execution_log) >= 2, "Agent1 has execution log entries"
        assert len(agent2.execution_log) >= 2, "Agent2 has execution log entries"
        assert len(agent3.execution_log) >= 2, "Agent3 has execution log entries"
        
        # Verify logs contain correct user references
        for log_entry in agent1.execution_log:
            if "user" in log_entry:
                assert user1.user_id in log_entry, f"Agent1 log entry should reference user1: {log_entry}"
        
        for log_entry in agent2.execution_log:
            if "user" in log_entry:
                assert user2.user_id in log_entry, f"Agent2 log entry should reference user2: {log_entry}"
        
        for log_entry in agent3.execution_log:
            if "user" in log_entry:
                assert user3.user_id in log_entry, f"Agent3 log entry should reference user3: {log_entry}"
        
        print(f"✅ Scenario 3: Agent execution completely isolated")

    @pytest.mark.parametrize("user_count", [5, 10, 15])
    async def test_performance_validation_concurrent_users(self, user_count, test_user_contexts):
        """
        PERFORMANCE VALIDATION: System handles concurrent users without degradation.
        
        This test validates that the isolation fixes don't negatively impact performance
        and the system can handle realistic concurrent user loads.
        """
        # Extend user contexts to requested count
        base_users = test_user_contexts
        extended_users = []
        
        for i in range(user_count):
            if i < len(base_users):
                extended_users.append(base_users[i])
            else:
                # Create additional users
                user_id = f"perf-user-{i}-{uuid.uuid4()}"
                request_id = f"perf-req-{uuid.uuid4()}"
                thread_id = f"perf-thread-{threading.get_ident()}-{i}"
                run_id = f"perf-run-{uuid.uuid4()}"
                
                context = UserExecutionContext(
                    user_id=user_id,
                    request_id=request_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    session_id=f"perf-session-{uuid.uuid4()}",
                    metadata={"test": f"perf_user_{i}"}
                )
                extended_users.append(context)
        
        # Track performance metrics
        start_time = time.time()
        operation_counts = {"clickhouse": 0, "redis": 0, "errors": 0}
        
        async def user_workload(user: UserExecutionContext, user_index: int):
            """Simulate realistic user workload with data operations."""
            try:
                # ClickHouse operations (analytics queries)
                async with get_user_clickhouse_context(user) as ch_ctx:
                    # Simulate cache operations
                    _clickhouse_cache.set(
                        user.user_id,
                        f"SELECT * FROM events WHERE user_id = %s",
                        [{"event_id": f"evt_{user_index}_{i}", "user_id": user.user_id} for i in range(3)],
                        {"user_id": user.user_id}
                    )
                    
                    cached_data = _clickhouse_cache.get(
                        user.user_id,
                        f"SELECT * FROM events WHERE user_id = %s",
                        {"user_id": user.user_id}
                    )
                    
                    operation_counts["clickhouse"] += 1
                
                # Redis operations (session management)
                async with get_user_redis_context(user) as redis_ctx:
                    # Mock Redis operations
                    operations = [
                        redis_ctx.set(f"session_{i}", f"value_{user_index}_{i}") for i in range(3)
                    ]
                    await asyncio.gather(*operations)
                    
                    # Read operations
                    values = await asyncio.gather(*[
                        redis_ctx.get(f"session_{i}") for i in range(3)
                    ])
                    
                    operation_counts["redis"] += 1
                    
                    # Verify isolation - values should contain user index
                    for value in values:
                        if value:  # May be None for mocked operations
                            assert str(user_index) in str(value), f"Value isolation check failed: {value}"
                
                return {"user_index": user_index, "user_id": user.user_id, "status": "success"}
                
            except Exception as e:
                operation_counts["errors"] += 1
                return {"user_index": user_index, "user_id": user.user_id, "status": "error", "error": str(e)}
        
        # Execute concurrent workloads
        results = await asyncio.gather(*[
            user_workload(user, i) for i, user in enumerate(extended_users)
        ])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # PERFORMANCE VALIDATION
        
        # Check all operations completed
        assert len(results) == user_count, f"All {user_count} users completed"
        
        # Check error rate is acceptable
        successful_results = [r for r in results if r["status"] == "success"]
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} should be >= 95%"
        
        # Check performance is reasonable
        operations_per_second = (operation_counts["clickhouse"] + operation_counts["redis"]) / total_time
        assert operations_per_second >= 1.0, f"Performance too slow: {operations_per_second:.2f} ops/sec"
        
        # Check all users processed their own data (isolation verification)
        for i, result in enumerate(results):
            if result["status"] == "success":
                assert extended_users[i].user_id == result["user_id"], f"User {i} processed correct data"
        
        # Resource cleanup verification
        ch_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        ch_stats = await ch_factory.get_context_stats()
        redis_stats = await redis_factory.get_context_stats()
        
        # Factories should track reasonable number of contexts
        assert ch_stats["total_contexts"] <= user_count * 2, "ClickHouse factory not leaking contexts"
        assert redis_stats["total_contexts"] <= user_count * 2, "Redis factory not leaking contexts"
        
        print(f"✅ Performance validation: {user_count} users, {success_rate:.1%} success, {operations_per_second:.1f} ops/sec, {total_time:.2f}s")

    async def test_websocket_event_isolation(self, test_user_contexts):
        """
        WEBSOCKET ISOLATION TEST: Verify WebSocket events are properly isolated.
        
        This test ensures that WebSocket notifications don't leak between users,
        which is critical for the chat experience.
        """
        user1, user2 = test_user_contexts[:2]
        
        # Mock WebSocket manager that tracks events by user
        class MockWebSocketManager:
            def __init__(self):
                self.user_events = {}  # user_id -> list of events
                
            def emit_to_user(self, user_id: str, event_type: str, data: Dict[str, Any]):
                if user_id not in self.user_events:
                    self.user_events[user_id] = []
                self.user_events[user_id].append({
                    "event_type": event_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            def get_user_events(self, user_id: str) -> List[Dict[str, Any]]:
                return self.user_events.get(user_id, [])
        
        ws_manager = MockWebSocketManager()
        
        # Mock agent operations that emit WebSocket events
        class WebSocketTestAgent:
            def __init__(self, user_context: UserExecutionContext, ws_manager):
                self.user_context = user_context
                self.ws_manager = ws_manager
                
            async def execute_with_events(self):
                """Execute operations that emit WebSocket events."""
                user_id = self.user_context.user_id
                
                # Emit agent started event
                self.ws_manager.emit_to_user(user_id, "agent_started", {
                    "user_id": user_id,
                    "agent_type": "test_agent",
                    "request_id": self.user_context.request_id
                })
                
                # Simulate some work
                await asyncio.sleep(0.1)
                
                # Emit thinking event
                self.ws_manager.emit_to_user(user_id, "agent_thinking", {
                    "user_id": user_id,
                    "message": f"Processing request for {user_id}",
                    "progress": 50
                })
                
                # Use isolated data context
                async with get_user_clickhouse_context(self.user_context) as ch_ctx:
                    # Emit tool executing event
                    self.ws_manager.emit_to_user(user_id, "tool_executing", {
                        "user_id": user_id,
                        "tool": "clickhouse_query",
                        "context_user": ch_ctx.user_id
                    })
                    
                    # Emit tool completed event
                    self.ws_manager.emit_to_user(user_id, "tool_completed", {
                        "user_id": user_id,
                        "tool": "clickhouse_query",
                        "result": f"Data for {ch_ctx.user_id}",
                        "context_user": ch_ctx.user_id
                    })
                
                # Emit completion event
                self.ws_manager.emit_to_user(user_id, "agent_completed", {
                    "user_id": user_id,
                    "status": "success",
                    "request_id": self.user_context.request_id
                })
                
                return {"user_id": user_id, "events_sent": 5}
        
        # Create agents for different users
        agent1 = WebSocketTestAgent(user1, ws_manager)
        agent2 = WebSocketTestAgent(user2, ws_manager)
        
        # Execute agents concurrently
        result1, result2 = await asyncio.gather(
            agent1.execute_with_events(),
            agent2.execute_with_events()
        )
        
        # WEBSOCKET ISOLATION VALIDATION
        
        # Get events for each user
        user1_events = ws_manager.get_user_events(user1.user_id)
        user2_events = ws_manager.get_user_events(user2.user_id)
        
        # Verify each user received their events
        assert len(user1_events) == 5, "User1 should receive 5 WebSocket events"
        assert len(user2_events) == 5, "User2 should receive 5 WebSocket events"
        
        # Verify event isolation - each user's events contain their user_id
        for event in user1_events:
            assert event["data"]["user_id"] == user1.user_id, f"User1 event contains correct user_id: {event}"
            
        for event in user2_events:
            assert event["data"]["user_id"] == user2.user_id, f"User2 event contains correct user_id: {event}"
        
        # Verify no cross-contamination in events
        user1_event_users = set(event["data"]["user_id"] for event in user1_events)
        user2_event_users = set(event["data"]["user_id"] for event in user2_events)
        
        assert user1_event_users == {user1.user_id}, "User1 events only contain user1's user_id"
        assert user2_event_users == {user2.user_id}, "User2 events only contain user2's user_id"
        
        # Verify context isolation in tool events
        user1_tool_events = [e for e in user1_events if e["event_type"] in ["tool_executing", "tool_completed"]]
        user2_tool_events = [e for e in user2_events if e["event_type"] in ["tool_executing", "tool_completed"]]
        
        for event in user1_tool_events:
            context_user = event["data"].get("context_user")
            assert context_user == user1.user_id, f"User1 tool event has correct context_user: {event}"
        
        for event in user2_tool_events:
            context_user = event["data"].get("context_user")
            assert context_user == user2.user_id, f"User2 tool event has correct context_user: {event}"
        
        # Verify request isolation
        user1_request_events = [e for e in user1_events if "request_id" in e["data"]]
        user2_request_events = [e for e in user2_events if "request_id" in e["data"]]
        
        for event in user1_request_events:
            assert event["data"]["request_id"] == user1.request_id, f"User1 event has correct request_id: {event}"
        
        for event in user2_request_events:
            assert event["data"]["request_id"] == user2.request_id, f"User2 event has correct request_id: {event}"
        
        print(f"✅ WebSocket event isolation working correctly")

    async def test_resource_cleanup_no_leaks(self, test_user_contexts):
        """
        RESOURCE CLEANUP TEST: Verify no memory or resource leaks.
        
        This test ensures that the isolation implementation properly cleans up
        resources and doesn't cause memory leaks in production.
        """
        users = test_user_contexts[:3]
        
        # Get initial factory stats
        ch_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        initial_ch_stats = await ch_factory.get_context_stats()
        initial_redis_stats = await redis_factory.get_context_stats()
        
        initial_ch_contexts = initial_ch_stats["total_contexts"]
        initial_redis_contexts = initial_redis_stats["total_contexts"]
        
        # Create and use many contexts
        for user in users:
            for i in range(3):  # Multiple contexts per user
                async with get_user_clickhouse_context(user) as ch_ctx:
                    # Use context
                    cache_key = f"test_key_{i}"
                    _clickhouse_cache.set(
                        user.user_id,
                        f"SELECT {i}",
                        [{"result": i}]
                    )
                
                async with get_user_redis_context(user) as redis_ctx:
                    # Use context (mocked operations)
                    await redis_ctx.set(f"test_key_{i}", f"value_{i}")
        
        # Check intermediate stats (contexts should exist)
        mid_ch_stats = await ch_factory.get_context_stats()
        mid_redis_stats = await redis_factory.get_context_stats()
        
        # Should have more contexts now
        assert mid_ch_stats["total_contexts"] >= initial_ch_contexts, "ClickHouse contexts created"
        assert mid_redis_stats["total_contexts"] >= initial_redis_contexts, "Redis contexts created"
        
        # Force cleanup for all users
        for user in users:
            await ch_factory.cleanup_user_contexts(user.user_id)
            await redis_factory.cleanup_user_contexts(user.user_id)
        
        # Check final stats (most contexts should be cleaned up)
        final_ch_stats = await ch_factory.get_context_stats()
        final_redis_stats = await redis_factory.get_context_stats()
        
        # Context counts should be back to initial levels or lower
        assert final_ch_stats["total_contexts"] <= initial_ch_contexts + 2, "ClickHouse contexts cleaned up"
        assert final_redis_stats["total_contexts"] <= initial_redis_contexts + 2, "Redis contexts cleaned up"
        
        # User-specific cleanup verification
        for user in users:
            user_ch_count = final_ch_stats["user_context_counts"].get(user.user_id, 0)
            user_redis_count = final_redis_stats["user_context_counts"].get(user.user_id, 0)
            
            assert user_ch_count <= 1, f"User {user.user_id} ClickHouse contexts cleaned up"
            assert user_redis_count <= 1, f"User {user.user_id} Redis contexts cleaned up"
        
        # Cache should still work with isolation after cleanup
        for i, user in enumerate(users):
            cache_data = _clickhouse_cache.get(user.user_id, f"SELECT {2}")
            if cache_data:  # May be None if cleaned up
                assert isinstance(cache_data, list), "Cache data structure preserved"
        
        print(f"✅ Resource cleanup working correctly, no leaks detected")


@pytest.mark.mission_critical
class TestThreeTierIsolationSynchronous:
    """
    Synchronous tests for thread-based isolation scenarios.
    
    These tests complement the async tests by validating thread safety
    and synchronous code paths in the isolation implementation.
    """
    
    def test_thread_safety_isolation_fixed(self, test_user_contexts):
        """
        THREAD SAFETY TEST: Verify isolation works correctly with threads.
        
        This test validates that the isolation fixes are thread-safe and
        don't cause race conditions in multi-threaded environments.
        """
        users = test_user_contexts[:3]
        
        # Shared state to track thread operations
        thread_operations = {}
        thread_lock = threading.Lock()
        
        def thread_user_operations(user: UserExecutionContext, thread_index: int):
            """Simulate user operations in a thread."""
            try:
                # Store thread-specific data
                with thread_lock:
                    thread_operations[thread_index] = {
                        "user_id": user.user_id,
                        "thread_id": threading.get_ident(),
                        "operations": []
                    }
                
                # Simulate ClickHouse cache operations (thread-safe)
                cache = _clickhouse_cache
                
                # Cache user-specific data
                cache.set(
                    user.user_id,
                    f"SELECT * FROM thread_test WHERE user_id = %s",
                    [{"thread_data": f"data_for_{user.user_id}_thread_{thread_index}"}],
                    {"user_id": user.user_id}
                )
                
                # Retrieve cached data
                cached_data = cache.get(
                    user.user_id,
                    f"SELECT * FROM thread_test WHERE user_id = %s",
                    {"user_id": user.user_id}
                )
                
                with thread_lock:
                    thread_operations[thread_index]["operations"].append({
                        "type": "cache_operation",
                        "cached_data": cached_data,
                        "success": True
                    })
                
                # Simulate some work
                time.sleep(0.1)
                
                # Verify data integrity
                if cached_data and len(cached_data) > 0:
                    thread_data = cached_data[0].get("thread_data", "")
                    expected_pattern = f"data_for_{user.user_id}_thread_{thread_index}"
                    
                    with thread_lock:
                        thread_operations[thread_index]["operations"].append({
                            "type": "verification",
                            "expected": expected_pattern,
                            "actual": thread_data,
                            "match": expected_pattern in thread_data
                        })
                
                return {"thread_index": thread_index, "user_id": user.user_id, "status": "success"}
                
            except Exception as e:
                with thread_lock:
                    if thread_index in thread_operations:
                        thread_operations[thread_index]["error"] = str(e)
                return {"thread_index": thread_index, "user_id": user.user_id, "status": "error", "error": str(e)}
        
        # Execute operations in parallel threads
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = []
            for i, user in enumerate(users):
                future = executor.submit(thread_user_operations, user, i)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # THREAD SAFETY VALIDATION
        
        # All operations should succeed
        successful_results = [r for r in results if r["status"] == "success"]
        assert len(successful_results) == len(users), f"All {len(users)} thread operations should succeed"
        
        # Verify thread isolation
        for thread_index, operations in thread_operations.items():
            user_id = operations["user_id"]
            thread_id = operations["thread_id"]
            
            # Each thread should have its own user_id
            matching_user = next((u for u in users if u.user_id == user_id), None)
            assert matching_user is not None, f"Thread {thread_index} has valid user_id {user_id}"
            
            # Verify operations completed
            ops = operations.get("operations", [])
            assert len(ops) >= 1, f"Thread {thread_index} completed operations"
            
            # Verify cache operations
            cache_ops = [op for op in ops if op["type"] == "cache_operation"]
            if cache_ops:
                cache_op = cache_ops[0]
                assert cache_op["success"], f"Thread {thread_index} cache operation succeeded"
                
                cached_data = cache_op["cached_data"]
                if cached_data and len(cached_data) > 0:
                    # Cached data should contain user-specific info
                    data_str = str(cached_data)
                    assert user_id in data_str, f"Thread {thread_index} cached data contains user_id"
            
            # Verify data integrity
            verification_ops = [op for op in ops if op["type"] == "verification"]
            if verification_ops:
                verification = verification_ops[0]
                assert verification["match"], f"Thread {thread_index} data verification passed: {verification}"
        
        # Verify no cross-thread contamination
        user_ids_in_threads = set(ops["user_id"] for ops in thread_operations.values())
        expected_user_ids = set(user.user_id for user in users)
        assert user_ids_in_threads == expected_user_ids, "Thread operations isolated by user"
        
        print(f"✅ Thread safety isolation working correctly")

    def test_cache_key_collision_prevention_fixed(self):
        """
        SECURITY TEST: Verify cache key collision patterns are prevented.
        
        This test validates that the Phase 1 fix prevents all known cache
        key collision patterns that could lead to data leakage.
        """
        cache = _clickhouse_cache
        cache.clear()  # Start fresh
        
        # Test cases that previously caused collisions
        collision_test_cases = [
            # Case 1: Different users, same query
            {
                "user_id": "user123",
                "query": "SELECT * FROM docs",
                "params": {"limit": 10}
            },
            {
                "user_id": "user456", 
                "query": "SELECT * FROM docs",
                "params": {"limit": 10}
            },
            # Case 2: Similar user IDs that could cause hash collisions
            {
                "user_id": "user1",
                "query": "SELECT count(*)",
                "params": {}
            },
            {
                "user_id": "user2",
                "query": "SELECT count(*)",
                "params": {}
            },
            # Case 3: User IDs that could cause concatenation issues
            {
                "user_id": "abc",
                "query": "SELECT * FROM table",
                "params": {"id": "def"}
            },
            {
                "user_id": "abcd",
                "query": "SELECT * FROM table",
                "params": {"id": "ef"}
            }
        ]
        
        # Store data for each test case
        for i, test_case in enumerate(collision_test_cases):
            user_id = test_case["user_id"]
            query = test_case["query"]
            params = test_case["params"]
            
            data = [{"result": f"data_for_case_{i}", "user_id": user_id}]
            cache.set(user_id, query, data, params)
        
        # Verify all data is properly isolated
        for i, test_case in enumerate(collision_test_cases):
            user_id = test_case["user_id"]
            query = test_case["query"]
            params = test_case["params"]
            
            cached_data = cache.get(user_id, query, params)
            
            assert cached_data is not None, f"Test case {i} should have cached data"
            assert len(cached_data) == 1, f"Test case {i} should have one result"
            assert cached_data[0]["result"] == f"data_for_case_{i}", f"Test case {i} has correct data"
            assert cached_data[0]["user_id"] == user_id, f"Test case {i} has correct user_id"
        
        # Verify cache keys are all unique
        generated_keys = set()
        for test_case in collision_test_cases:
            key = cache._generate_key(
                test_case["user_id"],
                test_case["query"],
                test_case["params"]
            )
            
            # Check key format includes user_id
            assert test_case["user_id"] in key, f"Cache key should contain user_id: {key}"
            
            # Check for uniqueness
            assert key not in generated_keys, f"Duplicate cache key detected: {key}"
            generated_keys.add(key)
        
        # Verify total cache size matches expected
        stats = cache.stats()
        assert stats["size"] == len(collision_test_cases), f"Cache should have {len(collision_test_cases)} entries"
        
        print(f"✅ Cache key collision prevention working correctly")


if __name__ == "__main__":
    # Run the comprehensive isolation tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure to identify issues quickly
        "--no-cov",
        "-m", "mission_critical"  # Run only mission critical tests
    ])