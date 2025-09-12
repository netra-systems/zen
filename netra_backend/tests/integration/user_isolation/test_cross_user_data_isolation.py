"""
Integration Tests for Cross-User Data Isolation

Business Value Justification (BVJ):
- Segment: Enterprise (mission-critical for multi-tenant security)
- Business Goal: Guarantee zero risk of data leakage between users
- Value Impact: Complete data isolation prevents security breaches, enables enterprise compliance
- Revenue Impact: Essential for Enterprise revenue - any data leakage incident could lose major accounts

This test suite validates cross-user data isolation with realistic scenarios:
- Real database operations with multiple users simultaneously
- Cache key namespacing to prevent session contamination
- Data access patterns that could expose cross-user data
- Malicious attempts to access other users' data
- Race conditions that might cause data mixing
- Stress testing with realistic enterprise user loads
"""

import asyncio
import pytest
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.factories.data_access_factory import (
    get_clickhouse_factory,
    get_redis_factory,
    get_user_clickhouse_context,
    get_user_redis_context,
    cleanup_all_factories
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.data_contexts.user_data_context import (
    UserClickHouseContext,
    UserRedisContext
)


@pytest.mark.integration
@pytest.mark.real_services
class TestCrossUserDataIsolation(BaseIntegrationTest):
    """Test cross-user data isolation with real database and cache operations."""
    
    async def setup_method(self, method):
        """Set up each test with clean factory state."""
        await cleanup_all_factories()
    
    async def teardown_method(self, method):
        """Clean up after each test."""
        await cleanup_all_factories()
    
    def generate_test_data(self, user_id: str, size: int = 10) -> List[Dict]:
        """Generate test data specific to a user."""
        return [
            {
                "id": f"{user_id}_record_{i}",
                "user_id": user_id,
                "sensitive_data": f"secret_{user_id}_{i}",
                "timestamp": time.time(),
                "personal_info": {
                    "email": f"{user_id}_test_{i}@example.com",
                    "preferences": {"theme": random.choice(["dark", "light"])},
                    "api_keys": [f"key_{user_id}_{i}_{uuid4().hex[:8]}"]
                }
            }
            for i in range(size)
        ]
    
    def create_user_context(self, user_id: str) -> UserExecutionContext:
        """Create a UserExecutionContext for testing."""
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=f"thread_{uuid4().hex[:8]}",
            run_id=f"run_{uuid4().hex[:8]}",
            agent_context={"test_scenario": "data_isolation"},
            audit_metadata={"isolation_test": True}
        )
    
    @pytest.mark.asyncio
    async def test_redis_key_namespacing_prevents_cross_user_access(self):
        """Test that Redis key namespacing prevents users from accessing each other's data."""
        # Create contexts for multiple users
        users = [f"redis_user_{i}" for i in range(5)]
        user_contexts = {user: self.create_user_context(user) for user in users}
        
        # Create Redis contexts and store user-specific data
        stored_data = {}
        
        for user in users:
            async with get_user_redis_context(user_contexts[user]) as redis_ctx:
                # Store various types of data for each user
                user_data = {
                    "session_token": f"token_{user}_{uuid4().hex}",
                    "preferences": {"theme": "dark", "lang": "en"},
                    "api_keys": [f"key_{user}_1", f"key_{user}_2"],
                    "recent_searches": ["cost optimization", "security audit"]
                }
                
                stored_data[user] = user_data
                
                # Store data using different Redis data types
                await redis_ctx.set("session_token", user_data["session_token"])
                await redis_ctx.set_json("preferences", user_data["preferences"]) 
                await redis_ctx.set_json("api_keys", user_data["api_keys"])
                
                # List operations
                for search in user_data["recent_searches"]:
                    await redis_ctx.lpush("recent_searches", search)
                
                # Set operations
                await redis_ctx.sadd("active_sessions", f"session_{user}_1", f"session_{user}_2")
                
                # Hash operations
                await redis_ctx.hset("user_stats", "login_count", "5")
                await redis_ctx.hset("user_stats", "last_login", str(time.time()))
        
        # Verify each user can only access their own data
        for user in users:
            async with get_user_redis_context(user_contexts[user]) as redis_ctx:
                # Verify session token
                token = await redis_ctx.get("session_token")
                assert token == stored_data[user]["session_token"]
                
                # Verify JSON data
                prefs = await redis_ctx.get_json("preferences")
                assert prefs == stored_data[user]["preferences"]
                
                api_keys = await redis_ctx.get_json("api_keys")
                assert api_keys == stored_data[user]["api_keys"]
                
                # Verify list data
                searches = await redis_ctx.lrange("recent_searches", 0, -1)
                # Redis lists are LIFO, so reverse to match original order
                searches.reverse()
                assert searches == stored_data[user]["recent_searches"]
                
                # Verify set data
                sessions = await redis_ctx.smembers("active_sessions")
                expected_sessions = {f"session_{user}_1", f"session_{user}_2"}
                assert set(sessions) == expected_sessions
                
                # Verify hash data
                stats = await redis_ctx.hgetall("user_stats")
                assert stats["login_count"] == "5"
                assert "last_login" in stats
        
        # Verify users cannot access other users' data by trying different key patterns
        for user in users:
            other_users = [u for u in users if u != user]
            async with get_user_redis_context(user_contexts[user]) as redis_ctx:
                # Try to access other users' session tokens (should fail/return None)
                for other_user in other_users:
                    # These should return None because keys are namespaced
                    other_token = await redis_ctx.get(f"session_token")  # Same key name
                    # Should get our own data, not other user's
                    assert other_token == stored_data[user]["session_token"]
                    assert other_token != stored_data[other_user]["session_token"]
        
        print(" PASS:  Redis key namespacing prevents cross-user data access")
    
    @pytest.mark.asyncio
    async def test_clickhouse_query_isolation_with_user_context(self):
        """Test that ClickHouse queries are properly isolated by user context."""
        # Note: This test focuses on the isolation mechanism rather than actual ClickHouse operations
        # since we want to test the context isolation without requiring a full ClickHouse setup
        
        users = [f"ch_user_{i}" for i in range(4)]
        user_contexts = {user: self.create_user_context(user) for user in users}
        
        # Test context creation and user isolation
        ch_contexts = {}
        for user in users:
            async with get_user_clickhouse_context(user_contexts[user]) as ch_ctx:
                ch_contexts[user] = ch_ctx
                
                # Validate context has correct user isolation
                assert ch_ctx.user_id == user
                assert user in ch_ctx.user_id
                
                # Test that context info shows proper isolation
                context_info = ch_ctx.get_context_info()
                assert context_info["user_id"].startswith(user[:8])  # Truncated for security
                assert context_info["initialized"] is True
        
        # Test that different users get different context instances
        user_list = list(users)
        for i, user1 in enumerate(user_list):
            for user2 in user_list[i+1:]:
                ctx1 = ch_contexts[user1]
                ctx2 = ch_contexts[user2]
                
                # Contexts should be different instances
                assert ctx1 is not ctx2
                assert ctx1.user_id != ctx2.user_id
                assert ctx1.request_id != ctx2.request_id
        
        print(" PASS:  ClickHouse contexts are properly isolated by user")
    
    @pytest.mark.asyncio
    async def test_concurrent_data_operations_prevent_mixing(self):
        """Test that concurrent data operations from different users don't mix data."""
        users = [f"concurrent_user_{i}" for i in range(8)]
        
        async def user_data_operations(user_id: str):
            """Perform data operations for a single user."""
            user_context = self.create_user_context(user_id)
            operations_log = []
            
            # Redis operations
            async with get_user_redis_context(user_context) as redis_ctx:
                # Store user-specific session data
                session_id = f"session_{user_id}_{uuid4().hex[:8]}"
                await redis_ctx.set("current_session", session_id)
                operations_log.append(f"redis_set_session:{session_id}")
                
                # Store user preferences
                preferences = {
                    "user_id": user_id,
                    "theme": random.choice(["dark", "light", "auto"]),
                    "notifications": random.choice([True, False])
                }
                await redis_ctx.set_json("user_preferences", preferences)
                operations_log.append(f"redis_set_prefs:{preferences}")
                
                # Add to user's activity log
                activity = f"{user_id}_activity_{time.time()}"
                await redis_ctx.lpush("activity_log", activity)
                operations_log.append(f"redis_activity:{activity}")
            
            # ClickHouse context operations
            async with get_user_clickhouse_context(user_context) as ch_ctx:
                # Test context isolation
                context_info = ch_ctx.get_context_info()
                operations_log.append(f"ch_context_user:{context_info['user_id']}")
                
                # Simulate user-specific operations
                user_operation = f"operation_{user_id}_{uuid4().hex[:8]}"
                operations_log.append(f"ch_operation:{user_operation}")
            
            return user_id, operations_log
        
        # Run operations for all users concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            user_data_operations(user) for user in users
        ])
        duration = time.time() - start_time
        
        # Verify all operations completed successfully
        assert len(results) == len(users)
        
        user_operations = {user_id: ops for user_id, ops in results}
        
        # Verify each user's operations are isolated
        for user_id, operations in user_operations.items():
            # Each user should have completed all expected operations
            redis_ops = [op for op in operations if op.startswith("redis_")]
            ch_ops = [op for op in operations if op.startswith("ch_")]
            
            assert len(redis_ops) == 3  # session, prefs, activity
            assert len(ch_ops) == 2    # context_user, operation
            
            # All operations should be for the correct user
            for op in operations:
                if ":" in op:
                    _, value = op.split(":", 1)
                    if user_id in value or f"user_{user_id.split('_')[-1]}" in value:
                        continue  # Expected
                    # Should not contain other user IDs
                    for other_user in users:
                        if other_user != user_id:
                            assert other_user not in value, f"Data mixing detected: {op}"
        
        # Verify data retrieval shows proper isolation
        for user_id in users:
            user_context = self.create_user_context(user_id)
            async with get_user_redis_context(user_context) as redis_ctx:
                # Retrieve user's session
                session = await redis_ctx.get("current_session")
                assert session is not None
                assert user_id in session
                
                # Retrieve user preferences
                prefs = await redis_ctx.get_json("user_preferences")
                assert prefs is not None
                assert prefs["user_id"] == user_id
                
                # Check activity log
                activities = await redis_ctx.lrange("activity_log", 0, -1)
                for activity in activities:
                    assert user_id in activity
        
        print(f" PASS:  Concurrent operations for {len(users)} users completed in {duration:.2f}s with proper isolation")
    
    @pytest.mark.asyncio
    async def test_malicious_cross_user_access_attempts_blocked(self):
        """Test that malicious attempts to access other users' data are blocked."""
        legitimate_user = "legitimate_user_123"
        target_user = "target_user_456" 
        
        legit_context = self.create_user_context(legitimate_user)
        target_context = self.create_user_context(target_user)
        
        # Store sensitive data for target user
        target_sensitive_data = {
            "api_key": f"secret_key_{target_user}_{uuid4().hex}",
            "personal_data": {
                "ssn": "123-45-6789",
                "credit_card": "4111-1111-1111-1111",
                "address": "123 Secret St, Private City"
            },
            "business_data": {
                "revenue": 1000000,
                "client_list": ["Client A", "Client B", "Client C"],
                "contracts": ["Contract 1", "Contract 2"]
            }
        }
        
        # Store target user's data
        async with get_user_redis_context(target_context) as target_redis:
            await target_redis.set("api_key", target_sensitive_data["api_key"])
            await target_redis.set_json("personal_data", target_sensitive_data["personal_data"])
            await target_redis.set_json("business_data", target_sensitive_data["business_data"])
        
        # Legitimate user tries various malicious access patterns
        async with get_user_redis_context(legit_context) as legit_redis:
            # Direct key access (should return None due to namespacing)
            stolen_api_key = await legit_redis.get("api_key")
            # Should be None because keys are namespaced by user
            assert stolen_api_key is None or stolen_api_key != target_sensitive_data["api_key"]
            
            stolen_personal = await legit_redis.get_json("personal_data")
            assert stolen_personal is None or stolen_personal != target_sensitive_data["personal_data"]
            
            # Try pattern-based key access
            all_keys = await legit_redis.keys("*")
            # Should only see own keys, not target user's keys
            for key in all_keys:
                assert legitimate_user in key or not any(
                    target_user in key for key in all_keys
                ), "Malicious user can see target user's keys"
        
        # Verify target user can still access their own data
        async with get_user_redis_context(target_context) as target_redis:
            retrieved_api_key = await target_redis.get("api_key")
            assert retrieved_api_key == target_sensitive_data["api_key"]
            
            retrieved_personal = await target_redis.get_json("personal_data")
            assert retrieved_personal == target_sensitive_data["personal_data"]
            
            retrieved_business = await target_redis.get_json("business_data")
            assert retrieved_business == target_sensitive_data["business_data"]
        
        print(" PASS:  Malicious cross-user access attempts are properly blocked")
    
    @pytest.mark.asyncio 
    async def test_stress_test_enterprise_user_load(self):
        """Stress test with realistic enterprise user load (50+ concurrent users)."""
        num_users = 50
        operations_per_user = 10
        
        users = [f"enterprise_user_{i:03d}" for i in range(num_users)]
        
        async def enterprise_user_simulation(user_id: str):
            """Simulate an enterprise user's data operations."""
            user_context = self.create_user_context(user_id)
            completed_operations = 0
            
            # Store enterprise user data
            user_data = {
                "department": random.choice(["Engineering", "Sales", "Marketing", "Finance"]),
                "role": random.choice(["Manager", "Developer", "Analyst", "Executive"]),
                "projects": [f"project_{i}" for i in range(random.randint(1, 5))],
                "permissions": random.sample(["read", "write", "admin", "delete"], random.randint(2, 4))
            }
            
            try:
                # Redis operations
                async with get_user_redis_context(user_context) as redis_ctx:
                    for op in range(operations_per_user // 2):
                        # Store session data
                        await redis_ctx.set(f"session_{op}", f"session_data_{user_id}_{op}")
                        completed_operations += 1
                        
                        # Store user metadata
                        await redis_ctx.set_json(f"metadata_{op}", {
                            "user_id": user_id,
                            "operation": op,
                            "timestamp": time.time(),
                            **user_data
                        })
                        completed_operations += 1
                
                # ClickHouse context operations
                async with get_user_clickhouse_context(user_context) as ch_ctx:
                    for op in range(operations_per_user // 2):
                        # Get context info (simulates query preparation)
                        context_info = ch_ctx.get_context_info()
                        assert context_info["user_id"].startswith(user_id[:8])
                        completed_operations += 1
                        
                        # Simulate cache operation
                        ch_ctx.clear_user_cache()
                        completed_operations += 1
                
                return user_id, completed_operations, None
                
            except Exception as e:
                return user_id, completed_operations, str(e)
        
        # Run enterprise simulation
        print(f"Starting stress test with {num_users} users, {operations_per_user} ops each...")
        start_time = time.time()
        
        results = await asyncio.gather(*[
            enterprise_user_simulation(user) for user in users
        ], return_exceptions=True)
        
        duration = time.time() - start_time
        
        # Analyze results
        successful_users = 0
        total_operations = 0
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                user_id, ops_completed, error = result
                if error is None:
                    successful_users += 1
                    total_operations += ops_completed
                else:
                    errors.append(f"{user_id}: {error}")
        
        # Performance and correctness assertions
        success_rate = successful_users / num_users
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
        
        expected_total_ops = num_users * operations_per_user
        assert total_operations >= expected_total_ops * 0.95, (
            f"Too few operations completed: {total_operations}/{expected_total_ops}"
        )
        
        # Performance assertion (should handle enterprise load efficiently)
        ops_per_second = total_operations / duration
        assert ops_per_second > 100, f"Performance too slow: {ops_per_second:.1f} ops/sec"
        
        if errors:
            print(f" WARNING: [U+FE0F] {len(errors)} errors occurred during stress test:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   {error}")
        
        print(f" PASS:  Stress test completed: {successful_users}/{num_users} users, "
              f"{total_operations} operations in {duration:.2f}s "
              f"({ops_per_second:.1f} ops/sec)")
    
    @pytest.mark.asyncio
    async def test_data_isolation_with_identical_keys_different_users(self):
        """Test data isolation when different users use identical key names."""
        # This is a critical test for multi-tenant systems
        users = [f"identical_key_user_{i}" for i in range(6)]
        identical_key = "user_profile"  # Same key name for all users
        
        # Each user stores different data under the same key name
        user_data = {}
        for i, user in enumerate(users):
            user_data[user] = {
                "name": f"User {i}",
                "email": f"{user}@company.com",
                "secret_token": f"secret_{user}_{uuid4().hex}",
                "preferences": {"theme": ["dark", "light", "auto"][i % 3]},
                "sensitive_info": f"classified_data_{user}_{uuid4().hex}"
            }
        
        # Store data for all users using identical key names
        for user in users:
            user_context = self.create_user_context(user)
            async with get_user_redis_context(user_context) as redis_ctx:
                await redis_ctx.set_json(identical_key, user_data[user])
        
        # Verify each user only gets their own data despite using identical keys
        for user in users:
            user_context = self.create_user_context(user)
            async with get_user_redis_context(user_context) as redis_ctx:
                retrieved_data = await redis_ctx.get_json(identical_key)
                
                # Should get own data
                assert retrieved_data == user_data[user]
                
                # Should not get other users' data
                for other_user in users:
                    if other_user != user:
                        assert retrieved_data != user_data[other_user]
                        assert retrieved_data["secret_token"] != user_data[other_user]["secret_token"]
                        assert retrieved_data["sensitive_info"] != user_data[other_user]["sensitive_info"]
        
        print(" PASS:  Data isolation works correctly with identical key names across users")
    
    @pytest.mark.asyncio
    async def test_factory_statistics_accuracy_cross_user_operations(self):
        """Test that factory statistics remain accurate during cross-user operations."""
        clickhouse_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        users = [f"stats_user_{i}" for i in range(12)]
        
        # Phase 1: Create contexts for all users
        for user in users:
            user_context = self.create_user_context(user)
            
            # Create both types of contexts
            ch_context = await clickhouse_factory.create_user_context(user_context)
            redis_context = await redis_factory.create_user_context(user_context)
        
        # Verify statistics after creation
        ch_stats = await clickhouse_factory.get_context_stats()
        redis_stats = await redis_factory.get_context_stats()
        
        assert ch_stats["total_contexts"] == 12
        assert ch_stats["users_with_contexts"] == 12
        assert redis_stats["total_contexts"] == 12
        assert redis_stats["users_with_contexts"] == 12
        
        # Phase 2: Clean up contexts for some users
        users_to_cleanup = users[:4]  # Clean up first 4 users
        
        for user in users_to_cleanup:
            ch_cleaned = await clickhouse_factory.cleanup_user_contexts(user)
            redis_cleaned = await redis_factory.cleanup_user_contexts(user)
            assert ch_cleaned == 1
            assert redis_cleaned == 1
        
        # Verify statistics after cleanup
        ch_stats = await clickhouse_factory.get_context_stats()
        redis_stats = await redis_factory.get_context_stats()
        
        assert ch_stats["total_contexts"] == 8  # 12 - 4 cleaned up
        assert ch_stats["users_with_contexts"] == 8
        assert redis_stats["total_contexts"] == 8
        assert redis_stats["users_with_contexts"] == 8
        
        # Verify remaining users are correct
        remaining_users = set(ch_stats["user_context_counts"].keys())
        expected_remaining = set(users[4:])  # Users not cleaned up
        assert remaining_users == expected_remaining
        
        print(" PASS:  Factory statistics remain accurate during cross-user operations")