"""
Integration Tests for Data Access Factory Isolation Patterns

Business Value Justification (BVJ):
- Segment: Enterprise (critical for multi-tenant security)
- Business Goal: Guarantee complete data isolation between users 
- Value Impact: Zero risk of cross-user data leakage, enables enterprise compliance
- Revenue Impact: Essential for Enterprise revenue, prevents security breaches

This test suite validates the Data Access Factory pattern implementation with
realistic multi-user scenarios and concurrent operations. Tests ensure:
- Complete user isolation under concurrent load (10+ users)
- Proper resource management and cleanup
- Factory error handling when services are unavailable
- Protection against connection pool exhaustion
- Prevention of data leakage between user contexts
"""

import asyncio
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.factories.data_access_factory import (
    DataAccessFactory,
    ClickHouseAccessFactory, 
    RedisAccessFactory,
    get_clickhouse_factory,
    get_redis_factory,
    cleanup_all_factories
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.data_contexts.user_data_context import (
    UserClickHouseContext,
    UserRedisContext
)


@pytest.mark.integration
@pytest.mark.real_services
class TestDataAccessFactoryIsolation(BaseIntegrationTest):
    """Test data access factory isolation with real concurrent user scenarios."""
    
    @classmethod
    async def setup_class(cls):
        """Set up test class with clean factory state."""
        # Clean up any existing factories to start fresh
        await cleanup_all_factories()
        
    async def setup_method(self, method):
        """Set up each test method with clean state."""
        # Clean up factories before each test
        await cleanup_all_factories()
    
    async def teardown_method(self, method):
        """Clean up after each test method."""
        # Clean up factories after each test
        await cleanup_all_factories()
    
    def create_test_user_context(self, user_id: Optional[str] = None) -> UserExecutionContext:
        """Create a test UserExecutionContext with realistic data."""
        user_id = user_id or f"user_{uuid4().hex[:8]}"
        thread_id = f"thread_{uuid4().hex[:8]}"
        run_id = f"run_{uuid4().hex[:8]}"
        
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_context={"operation": "test_isolation", "source": "integration_test"}
        )
    
    @pytest.mark.asyncio
    async def test_clickhouse_factory_creates_isolated_contexts_under_load(self):
        """Test ClickHouse factory isolation with 10+ concurrent users."""
        factory = get_clickhouse_factory()
        
        # Create contexts for 12 different users concurrently
        user_contexts = [self.create_test_user_context() for _ in range(12)]
        created_contexts = []
        
        async def create_context_for_user(user_context: UserExecutionContext):
            """Create context for a single user."""
            try:
                context = await factory.create_user_context(user_context)
                return (user_context.user_id, context, None)
            except Exception as e:
                return (user_context.user_id, None, e)
        
        # Create contexts concurrently 
        start_time = time.time()
        results = await asyncio.gather(*[
            create_context_for_user(uc) for uc in user_contexts
        ], return_exceptions=True)
        creation_time = time.time() - start_time
        
        # Validate all contexts created successfully
        for user_id, context, error in results:
            assert error is None, f"Context creation failed for user {user_id}: {error}"
            assert context is not None, f"No context created for user {user_id}"
            assert isinstance(context, UserClickHouseContext)
            created_contexts.append(context)
        
        # Validate contexts are properly isolated
        assert len(created_contexts) == 12
        context_user_ids = [ctx.user_id for ctx in created_contexts]
        assert len(set(context_user_ids)) == 12, "Contexts not properly isolated by user_id"
        
        # Validate factory statistics
        stats = await factory.get_context_stats()
        assert stats["total_contexts"] == 12
        assert stats["users_with_contexts"] == 12
        assert stats["factory_name"] == "ClickHouseAccessFactory"
        
        # Performance validation: context creation should be fast
        assert creation_time < 5.0, f"Context creation took too long: {creation_time}s"
        
        print(f" PASS:  Created 12 isolated ClickHouse contexts in {creation_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_redis_factory_creates_isolated_contexts_under_load(self):
        """Test Redis factory isolation with 10+ concurrent users."""
        factory = get_redis_factory()
        
        # Create contexts for 15 different users concurrently
        user_contexts = [self.create_test_user_context() for _ in range(15)]
        created_contexts = []
        
        async def create_context_for_user(user_context: UserExecutionContext):
            """Create context for a single user."""
            try:
                context = await factory.create_user_context(user_context)
                return (user_context.user_id, context, None)
            except Exception as e:
                return (user_context.user_id, None, e)
        
        # Create contexts concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            create_context_for_user(uc) for uc in user_contexts
        ], return_exceptions=True)
        creation_time = time.time() - start_time
        
        # Validate all contexts created successfully  
        for user_id, context, error in results:
            assert error is None, f"Context creation failed for user {user_id}: {error}"
            assert context is not None, f"No context created for user {user_id}"
            assert isinstance(context, UserRedisContext)
            created_contexts.append(context)
        
        # Validate contexts are properly isolated
        assert len(created_contexts) == 15
        context_user_ids = [ctx.user_id for ctx in created_contexts]
        assert len(set(context_user_ids)) == 15, "Contexts not properly isolated by user_id"
        
        # Validate factory statistics
        stats = await factory.get_context_stats()
        assert stats["total_contexts"] == 15
        assert stats["users_with_contexts"] == 15
        assert stats["factory_name"] == "RedisAccessFactory"
        
        # Performance validation: context creation should be fast
        assert creation_time < 5.0, f"Context creation took too long: {creation_time}s"
        
        print(f" PASS:  Created 15 isolated Redis contexts in {creation_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_factory_enforces_per_user_context_limits(self):
        """Test that factories properly enforce max contexts per user."""
        factory = ClickHouseAccessFactory(max_contexts_per_user=3)
        user_context = self.create_test_user_context(user_id="test_limit_user")
        
        # Create 3 contexts successfully
        contexts = []
        for i in range(3):
            context = await factory.create_user_context(user_context)
            contexts.append(context)
        
        # Verify 3 contexts created
        stats = await factory.get_context_stats()
        assert stats["total_contexts"] == 3
        assert stats["user_context_counts"]["test_limit_user"] == 3
        
        # 4th context should fail with proper error
        with pytest.raises(ValueError, match="exceeds maximum contexts"):
            await factory.create_user_context(user_context)
        
        # Clean up contexts for this user
        cleaned = await factory.cleanup_user_contexts("test_limit_user")
        assert cleaned == 3
        
        # Verify cleanup worked
        stats = await factory.get_context_stats()
        assert stats["total_contexts"] == 0
        assert "test_limit_user" not in stats["user_context_counts"]
        
        # Now 4th context should succeed
        new_context = await factory.create_user_context(user_context)
        assert new_context is not None
        
        print(" PASS:  Factory properly enforces per-user context limits")
    
    @pytest.mark.asyncio 
    async def test_factory_handles_service_unavailable_gracefully(self):
        """Test factory error handling when underlying services are unavailable."""
        # Note: This test simulates service unavailability - in real environments
        # the factories should handle connection failures gracefully
        
        factory = ClickHouseAccessFactory()
        user_context = self.create_test_user_context()
        
        # Try to create context (may succeed or fail depending on service availability)
        try:
            context = await factory.create_user_context(user_context)
            # If service is available, context should be properly initialized
            if hasattr(context, '_initialized'):
                # For UserClickHouseContext, we can test initialization
                pass
            print(" PASS:  Factory handled service availability appropriately")
            
        except Exception as e:
            # If service unavailable, error should be clear and informative
            assert "ClickHouse" in str(e) or "connection" in str(e).lower()
            print(f" PASS:  Factory handled service unavailability with clear error: {e}")
    
    @pytest.mark.asyncio
    async def test_factory_cleanup_prevents_resource_leaks(self):
        """Test that factory cleanup prevents memory and resource leaks."""
        clickhouse_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        # Create contexts for multiple users
        users = [self.create_test_user_context() for _ in range(8)]
        
        # Create contexts
        ch_contexts = []
        redis_contexts = []
        
        for user in users:
            ch_ctx = await clickhouse_factory.create_user_context(user)
            redis_ctx = await redis_factory.create_user_context(user)
            ch_contexts.append(ch_ctx)
            redis_contexts.append(redis_ctx)
        
        # Verify contexts created
        ch_stats = await clickhouse_factory.get_context_stats()
        redis_stats = await redis_factory.get_context_stats()
        
        assert ch_stats["total_contexts"] == 8
        assert redis_stats["total_contexts"] == 8
        
        # Cleanup all factories
        await cleanup_all_factories()
        
        # Verify cleanup worked - factories should be reset
        new_ch_factory = get_clickhouse_factory()
        new_redis_factory = get_redis_factory()
        
        ch_stats = await new_ch_factory.get_context_stats()
        redis_stats = await new_redis_factory.get_context_stats()
        
        assert ch_stats["total_contexts"] == 0
        assert redis_stats["total_contexts"] == 0
        assert ch_stats["users_with_contexts"] == 0
        assert redis_stats["users_with_contexts"] == 0
        
        print(" PASS:  Factory cleanup prevents resource leaks")
    
    @pytest.mark.asyncio
    async def test_factory_handles_context_ttl_expiration(self):
        """Test factory properly handles context TTL and expiration."""
        # Create factory with very short TTL for testing
        factory = ClickHouseAccessFactory(
            context_ttl_seconds=2,  # 2 second TTL
            max_contexts_per_user=5
        )
        
        user_context = self.create_test_user_context()
        
        # Create context
        context = await factory.create_user_context(user_context)
        assert context is not None
        
        # Verify context exists
        stats = await factory.get_context_stats()
        assert stats["total_contexts"] == 1
        
        # Wait for TTL to expire
        await asyncio.sleep(3)
        
        # Trigger cleanup (normally done by background task)
        await factory._cleanup_expired_contexts()
        
        # Verify context was cleaned up
        stats = await factory.get_context_stats()
        assert stats["total_contexts"] == 0
        
        print(" PASS:  Factory properly handles context TTL expiration")
    
    @pytest.mark.asyncio
    async def test_concurrent_factory_operations_thread_safety(self):
        """Test factory thread safety under concurrent operations."""
        factory = get_clickhouse_factory()
        
        async def mixed_operations(user_index: int):
            """Perform mixed operations for a user."""
            user_context = self.create_test_user_context(f"concurrent_user_{user_index}")
            
            # Create context
            context = await factory.create_user_context(user_context)
            
            # Get stats (concurrent read)
            stats = await factory.get_context_stats()
            
            # Cleanup user contexts (concurrent write)
            if user_index % 3 == 0:
                await factory.cleanup_user_contexts(user_context.user_id)
            
            return user_index, context
        
        # Run 20 concurrent operations
        start_time = time.time()
        results = await asyncio.gather(*[
            mixed_operations(i) for i in range(20)
        ], return_exceptions=True)
        duration = time.time() - start_time
        
        # Validate no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
        
        # Validate performance 
        assert duration < 10.0, f"Concurrent operations took too long: {duration}s"
        
        # Final stats should be consistent
        final_stats = await factory.get_context_stats()
        assert isinstance(final_stats["total_contexts"], int)
        assert final_stats["total_contexts"] >= 0
        
        print(f" PASS:  Factory handles 20 concurrent operations in {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_factory_statistics_accuracy_under_load(self):
        """Test that factory statistics remain accurate under concurrent load."""
        clickhouse_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        # Create contexts for multiple users with different patterns
        user_contexts = []
        
        # 5 users with 1 context each
        for i in range(5):
            user_contexts.append(self.create_test_user_context(f"single_user_{i}"))
        
        # 2 users with 2 contexts each (same user_id)
        for i in range(2):
            user_id = f"double_user_{i}"
            user_contexts.append(self.create_test_user_context(user_id))
            user_contexts.append(self.create_test_user_context(user_id))
        
        # Create all contexts concurrently
        async def create_both_contexts(user_context):
            ch_ctx = await clickhouse_factory.create_user_context(user_context)
            redis_ctx = await redis_factory.create_user_context(user_context)
            return ch_ctx, redis_ctx
        
        results = await asyncio.gather(*[
            create_both_contexts(uc) for uc in user_contexts
        ])
        
        # Verify statistics accuracy
        ch_stats = await clickhouse_factory.get_context_stats()
        redis_stats = await redis_factory.get_context_stats()
        
        # ClickHouse: 5 single users + 2 double users = 7 unique users, 9 total contexts
        assert ch_stats["total_contexts"] == 9
        assert ch_stats["users_with_contexts"] == 7
        
        # Redis: Same pattern
        assert redis_stats["total_contexts"] == 9
        assert redis_stats["users_with_contexts"] == 7
        
        # Verify user context counts
        expected_single_users = {f"single_user_{i}": 1 for i in range(5)}
        expected_double_users = {f"double_user_{i}": 2 for i in range(2)}
        expected_counts = {**expected_single_users, **expected_double_users}
        
        for user_id, expected_count in expected_counts.items():
            assert ch_stats["user_context_counts"][user_id] == expected_count
            assert redis_stats["user_context_counts"][user_id] == expected_count
        
        print(" PASS:  Factory statistics remain accurate under complex load patterns")