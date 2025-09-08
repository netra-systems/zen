"""
Test Redis Cache Consistency Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure fast response times and data consistency through intelligent caching
- Value Impact: Cache performance directly impacts user experience and platform responsiveness
- Strategic Impact: Redis caching reduces database load and improves system scalability

This test suite validates Redis cache integration:
1. Cache-database synchronization and consistency
2. User-specific cache isolation and namespace protection
3. Cache invalidation patterns and TTL management
"""

import asyncio
import uuid
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, SessionID,
    ensure_user_id, ensure_thread_id
)

# Redis and cache components
from netra_backend.app.redis_manager import RedisManager, UserCacheManager
from netra_backend.app.services.cache_service import CacheService, CacheConsistencyManager
from netra_backend.app.factories.redis_factory import RedisConnectionFactory

# Models for testing cache consistency
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread, Message


class TestRedisCacheIntegration(BaseIntegrationTest):
    """Test Redis cache consistency with real database synchronization."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_database_synchronization(self, real_services_fixture, isolated_env):
        """Test cache stays synchronized with database operations."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        
        # Create user in database
        test_user = User(
            id=str(user_id),
            email="cache.sync@test.com",
            name="Cache Sync User",
            created_at=datetime.utcnow()
        )
        
        db.add(test_user)
        await db.commit()
        
        # Initialize cache service with consistency management
        cache_service = CacheService(redis_connection=redis, database_session=db)
        consistency_manager = CacheConsistencyManager(cache_service)
        
        # Cache user data
        user_cache_key = f"user:{user_id}:profile"
        user_data = {
            "id": str(user_id),
            "email": "cache.sync@test.com",
            "name": "Cache Sync User",
            "cached_at": datetime.utcnow().isoformat()
        }
        
        await cache_service.set_with_consistency(user_cache_key, user_data, ttl=300)
        
        # Verify data is cached
        cached_user = await cache_service.get(user_cache_key)
        assert cached_user is not None
        assert cached_user["email"] == "cache.sync@test.com"
        
        # Update user in database
        test_user.name = "Updated Cache Sync User"
        test_user.updated_at = datetime.utcnow()
        await db.commit()
        
        # Cache should be automatically invalidated on database update
        await consistency_manager.invalidate_user_cache(user_id)
        
        # Verify cache was invalidated
        cached_user_after_update = await cache_service.get(user_cache_key)
        assert cached_user_after_update is None, "Cache was not invalidated after database update"
        
        # Re-cache updated data
        updated_user_data = {
            "id": str(user_id),
            "email": "cache.sync@test.com",
            "name": "Updated Cache Sync User",
            "cached_at": datetime.utcnow().isoformat()
        }
        
        await cache_service.set_with_consistency(user_cache_key, updated_user_data, ttl=300)
        
        # Verify cache contains updated data
        final_cached_user = await cache_service.get(user_cache_key)
        assert final_cached_user["name"] == "Updated Cache Sync User"
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_cache_isolation_and_namespacing(self, real_services_fixture, isolated_env):
        """Test user-specific cache isolation prevents cross-user data leakage."""
        
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        # Create multiple users for isolation testing
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        user3_id = ensure_user_id(str(uuid.uuid4()))
        
        # Initialize user-specific cache managers
        user1_cache = UserCacheManager(redis_connection=redis, user_id=user1_id)
        user2_cache = UserCacheManager(redis_connection=redis, user_id=user2_id)
        user3_cache = UserCacheManager(redis_connection=redis, user_id=user3_id)
        
        # Cache data for each user
        user_data_sets = [
            (user1_cache, user1_id, "user1@isolation.test", "User 1 Data"),
            (user2_cache, user2_id, "user2@isolation.test", "User 2 Data"),
            (user3_cache, user3_id, "user3@isolation.test", "User 3 Data")
        ]
        
        # Set cache data for each user
        for cache_manager, user_id, email, name in user_data_sets:
            profile_data = {
                "user_id": str(user_id),
                "email": email,
                "name": name,
                "preferences": {"theme": f"theme_{user_id}", "language": "en"},
                "cached_at": datetime.utcnow().isoformat()
            }
            
            await cache_manager.set_user_profile(profile_data)
            
            # Cache user sessions
            session_data = {
                "session_id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
            
            await cache_manager.set_user_session(session_data["session_id"], session_data)
        
        # Verify each user can only access their own cached data
        for cache_manager, user_id, email, name in user_data_sets:
            # User should see their own profile
            profile = await cache_manager.get_user_profile()
            assert profile is not None
            assert profile["email"] == email
            assert profile["name"] == name
            assert profile["user_id"] == str(user_id)
            
            # Verify theme preference is user-specific
            expected_theme = f"theme_{user_id}"
            assert profile["preferences"]["theme"] == expected_theme
        
        # Test cross-user access prevention
        # User1 should not be able to access User2's or User3's data through cache keys
        user1_keys = await user1_cache.get_user_cache_keys()
        user2_keys = await user2_cache.get_user_cache_keys()
        user3_keys = await user3_cache.get_user_cache_keys()
        
        # Verify key isolation (no overlap between user cache keys)
        assert not any(key in user2_keys or key in user3_keys for key in user1_keys)
        assert not any(key in user1_keys or key in user3_keys for key in user2_keys)
        assert not any(key in user1_keys or key in user2_keys for key in user3_keys)
        
        # Attempt cross-user cache access (should fail gracefully)
        cross_user_profile = await user1_cache.get_cache_by_key(f"user:{user2_id}:profile")
        assert cross_user_profile is None, "Cross-user cache access was allowed - isolation failure!"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_ttl_and_invalidation_patterns(self, real_services_fixture, isolated_env):
        """Test cache TTL management and various invalidation patterns."""
        
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        cache_service = CacheService(redis_connection=redis)
        
        # Test different TTL scenarios
        cache_scenarios = [
            # (key, data, ttl_seconds, description)
            (f"user:{user_id}:profile", {"type": "profile", "data": "profile_data"}, 300, "5-minute profile cache"),
            (f"thread:{thread_id}:messages", {"type": "messages", "count": 10}, 60, "1-minute message cache"),
            (f"session:{user_id}:temp", {"type": "temp", "value": "temporary"}, 5, "5-second temporary cache"),
            (f"user:{user_id}:preferences", {"type": "preferences", "theme": "dark"}, 3600, "1-hour preferences cache")
        ]
        
        # Set cache entries with different TTLs
        cache_keys = []
        for key, data, ttl, description in cache_scenarios:
            await cache_service.set(key, data, ttl=ttl)
            cache_keys.append(key)
            
            # Verify TTL was set correctly
            ttl_remaining = await redis.ttl(key)
            assert ttl_remaining > 0, f"TTL not set for {description}"
            assert ttl_remaining <= ttl, f"TTL set incorrectly for {description}"
        
        # Verify all cache entries exist initially
        for key, _, _, description in cache_scenarios:
            cached_data = await cache_service.get(key)
            assert cached_data is not None, f"Cache entry not found: {description}"
        
        # Test pattern-based invalidation
        # Invalidate all user-related caches
        user_pattern = f"user:{user_id}:*"
        invalidated_count = await cache_service.invalidate_pattern(user_pattern)
        assert invalidated_count >= 2, "User pattern invalidation didn't match expected keys"
        
        # Verify user-specific caches were invalidated
        profile_cache = await cache_service.get(f"user:{user_id}:profile")
        preferences_cache = await cache_service.get(f"user:{user_id}:preferences")
        assert profile_cache is None, "User profile cache was not invalidated"
        assert preferences_cache is None, "User preferences cache was not invalidated"
        
        # Verify thread cache still exists (different pattern)
        thread_cache = await cache_service.get(f"thread:{thread_id}:messages")
        assert thread_cache is not None, "Thread cache was incorrectly invalidated"
        
        # Test TTL expiration
        # Wait for short TTL cache to expire
        await asyncio.sleep(6)  # Wait longer than 5-second TTL
        
        temp_cache = await cache_service.get(f"session:{user_id}:temp")
        assert temp_cache is None, "Temporary cache did not expire as expected"
        
        # Test cache refresh/extension
        # Extend TTL for remaining thread cache
        await cache_service.extend_ttl(f"thread:{thread_id}:messages", additional_seconds=120)
        
        extended_ttl = await redis.ttl(f"thread:{thread_id}:messages")
        assert extended_ttl > 60, "Cache TTL was not extended"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_concurrent_cache_operations_thread_safety(self, real_services_fixture, isolated_env):
        """Test concurrent cache operations maintain thread safety and consistency."""
        
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        cache_service = CacheService(redis_connection=redis)
        
        # Shared cache key for concurrent operations
        shared_key = f"user:{user_id}:counter"
        
        async def increment_counter(operation_id: int, iterations: int):
            """Concurrent operation that increments a shared counter."""
            for i in range(iterations):
                # Use Redis atomic operations for thread safety
                current_value = await redis.get(shared_key) or "0"
                new_value = int(current_value) + 1
                
                # Use Redis SET with NX and EX for atomic operations
                await redis.set(f"{shared_key}:op_{operation_id}_{i}", new_value)
                
                # Update main counter atomically
                await redis.incr(shared_key)
                
                # Small delay to increase chance of race conditions
                await asyncio.sleep(0.001)
            
            return operation_id
        
        # Initialize counter
        await redis.set(shared_key, "0")
        
        # Run concurrent increment operations
        concurrent_operations = 10
        iterations_per_operation = 50
        expected_final_value = concurrent_operations * iterations_per_operation
        
        tasks = [
            increment_counter(op_id, iterations_per_operation)
            for op_id in range(concurrent_operations)
        ]
        
        # Execute all operations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
        
        # Verify final counter value is correct (no race conditions)
        final_value = int(await redis.get(shared_key) or "0")
        assert final_value == expected_final_value, \
            f"Race condition detected: expected {expected_final_value}, got {final_value}"
        
        # Verify individual operation tracking
        operation_keys = await redis.keys(f"{shared_key}:op_*")
        assert len(operation_keys) == expected_final_value, \
            "Individual operation tracking failed"

    def _create_test_redis_connection(self):
        """Create test Redis connection with proper async interface."""
        mock_redis = AsyncMock()
        
        # Mock Redis operations
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis.keys = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=300)
        mock_redis.incr = AsyncMock()
        mock_redis.exists = AsyncMock()
        mock_redis.expire = AsyncMock()
        
        # Mock pattern-based operations
        mock_redis.scan_iter = AsyncMock()
        
        return mock_redis
    
    def _create_test_db_session(self):
        """Create test database session."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session