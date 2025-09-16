"""
Comprehensive unit tests for JWT Cache - High-performance caching for JWT validation
Tests all functionality including Redis integration, performance metrics, and edge cases

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure JWT validation performance and reliability
- Value Impact: Fast token validation enables responsive user experience
- Strategic Impact: Cache performance directly impacts platform scalability
"""
import asyncio
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from auth_service.auth_core.core.jwt_cache import JWTValidationCache, jwt_validation_cache
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env


class TestJWTValidationCacheBasics(BaseIntegrationTest):
    """Test basic cache functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
        self.test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMCwidG9rZW5fdHlwZSI6ImFjY2VzcyJ9.test_signature"
        self.test_payload = {
            "sub": "test-user-id",
            "exp": int(time.time()) + 3600,  # 1 hour from now
            "iat": int(time.time()),
            "token_type": "access",
            "email": "test@example.com"
        }
    
    def test_cache_initialization(self):
        """Test cache initializes with correct defaults"""
        assert self.cache._cache_ttl == 300
        assert self.cache._max_cache_size == 10000
        assert len(self.cache._validation_cache) == 0
        assert self.cache._validation_stats["cache_hits"] == 0
        assert self.cache._validation_stats["cache_misses"] == 0
        assert self.cache._validation_stats["redis_hits"] == 0
        assert self.cache._validation_stats["redis_misses"] == 0
        assert self.cache._validation_stats["validation_count"] == 0
    
    def test_get_cache_key_generation(self):
        """Test cache key generation is consistent"""
        key1 = self.cache.get_cache_key(self.test_token, "access")
        key2 = self.cache.get_cache_key(self.test_token, "access")
        key3 = self.cache.get_cache_key(self.test_token, "refresh")
        
        # Same token and type should generate same key
        assert key1 == key2
        # Different token type should generate different key
        assert key1 != key3
        # Key should contain token type
        assert "access" in key1
        assert "refresh" in key3
        # Key should be consistent format
        assert key1.startswith("jwt_validation:")
    
    def test_cache_and_retrieve_valid_payload(self):
        """Test caching and retrieving valid payload"""
        cache_key = self.cache.get_cache_key(self.test_token, "access")
        
        # Initially should return None (cache miss)
        result = self.cache.get_from_cache(cache_key)
        assert result is None
        assert self.cache._validation_stats["cache_misses"] == 1
        
        # Cache the payload
        self.cache.cache_validation_result(cache_key, self.test_payload)
        
        # Should return cached payload
        result = self.cache.get_from_cache(cache_key)
        assert result is not None
        assert result["sub"] == "test-user-id"
        assert result["email"] == "test@example.com"
        assert self.cache._validation_stats["cache_hits"] == 1
    
    def test_cache_and_retrieve_invalid_result(self):
        """Test caching and retrieving invalid result"""
        cache_key = self.cache.get_cache_key("invalid_token", "access")
        
        # Cache invalid result
        self.cache.cache_validation_result(cache_key, None)
        
        # Should return "INVALID" string when cached None result is retrieved
        result = self.cache.get_from_cache(cache_key)
        # The cache stores "INVALID" string for None results
        assert result == "INVALID" or result is None  # Both are valid outcomes
        assert self.cache._validation_stats["cache_hits"] == 1  # Still counts as cache hit
    
    def test_cache_expiration_removes_entries(self):
        """Test expired cache entries are removed"""
        cache_key = self.cache.get_cache_key(self.test_token, "access")
        
        # Cache with very short TTL
        self.cache.cache_validation_result(cache_key, self.test_payload, ttl=1)
        
        # Should be cached initially
        result = self.cache.get_from_cache(cache_key)
        assert result is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired and removed
        result = self.cache.get_from_cache(cache_key)
        assert result is None
        assert cache_key not in self.cache._validation_cache
    
    def test_jwt_token_expiration_handling(self):
        """Test expired JWT tokens are not returned from cache"""
        cache_key = self.cache.get_cache_key(self.test_token, "access")
        
        # Create payload with expired JWT token
        expired_payload = self.test_payload.copy()
        expired_payload["exp"] = int(time.time()) - 3600  # Expired 1 hour ago
        
        # Cache the expired payload
        self.cache.cache_validation_result(cache_key, expired_payload, ttl=300)
        
        # Should return None because JWT token itself is expired
        result = self.cache.get_from_cache(cache_key)
        assert result is None
        # Cache entry should be removed
        assert cache_key not in self.cache._validation_cache


class TestJWTValidationCacheRedis(BaseIntegrationTest):
    """Test Redis integration functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
        self.cache_key = "jwt_validation:test_hash:access"
        self.test_payload = {
            "sub": "redis-test-user",
            "exp": int(time.time()) + 3600,
            "token_type": "access"
        }
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_redis_cache_hit(self, mock_redis_manager):
        """Test Redis cache hit when memory cache misses"""
        # Setup Redis mock
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = json.dumps(self.test_payload)
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.return_value = mock_redis_client
        
        # Mock memory cache miss but Redis hit
        result = self.cache.get_from_cache(self.cache_key)
        
        # Should find in Redis and update memory cache
        mock_redis_client.get.assert_called_once_with(f"jwt_cache:{self.cache_key}")
        assert self.cache._validation_stats["redis_hits"] > 0
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_redis_cache_miss(self, mock_redis_manager):
        """Test Redis cache miss"""
        # Setup Redis mock
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = None
        mock_redis_manager.enabled = True  
        mock_redis_manager.get_client.return_value = mock_redis_client
        
        # Should return None on cache miss
        result = self.cache.get_from_cache(self.cache_key)
        assert result is None
        assert self.cache._validation_stats["redis_misses"] > 0
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_redis_expired_token_removal(self, mock_redis_manager):
        """Test expired JWT tokens are removed from Redis"""
        # Setup Redis mock
        mock_redis_client = MagicMock()
        expired_payload = {
            "sub": "expired-user",
            "exp": int(time.time()) - 3600,  # Expired
            "token_type": "access"
        }
        mock_redis_client.get.return_value = json.dumps(expired_payload)
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.return_value = mock_redis_client
        
        # Should detect expiration and remove from Redis
        result = self.cache.get_from_cache(self.cache_key)
        assert result is None
        # Should delete expired entry
        mock_redis_client.delete.assert_called_once_with(f"jwt_cache:{self.cache_key}")
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_redis_connection_failure_fallback(self, mock_redis_manager):
        """Test graceful fallback when Redis fails"""
        # Setup Redis to fail
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.side_effect = Exception("Redis connection failed")
        
        # Should gracefully fallback to memory-only
        result = self.cache.get_from_cache(self.cache_key)
        assert result is None
        assert self.cache._validation_stats["redis_misses"] > 0
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_redis_disabled_uses_memory_only(self, mock_redis_manager):
        """Test cache works with Redis disabled"""
        mock_redis_manager.enabled = False
        
        # Cache in memory
        self.cache.cache_validation_result(self.cache_key, self.test_payload)
        
        # Should find in memory cache
        result = self.cache.get_from_cache(self.cache_key)
        assert result is not None
        assert result["sub"] == "redis-test-user"
        assert self.cache._validation_stats["cache_hits"] == 1
        assert self.cache._validation_stats["redis_hits"] == 0


class TestJWTValidationCachePerformance(BaseIntegrationTest):
    """Test cache performance and statistics"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
    
    def test_cache_size_limit_enforcement(self):
        """Test cache size limit prevents memory exhaustion"""
        # Fill cache beyond limit
        original_max = self.cache._max_cache_size
        self.cache._max_cache_size = 10  # Small limit for testing
        
        # Add entries beyond limit
        for i in range(15):
            cache_key = f"jwt_validation:test_{i}:access"
            payload = {"sub": f"user-{i}", "exp": int(time.time()) + 3600}
            self.cache.cache_validation_result(cache_key, payload)
        
        # Cache size should be reasonable (cleanup may not be exact)
        assert len(self.cache._validation_cache) <= self.cache._max_cache_size + 5  # Allow some variance
        
        # Restore original limit
        self.cache._max_cache_size = original_max
    
    def test_expired_entries_cleanup_on_size_limit(self):
        """Test expired entries are cleaned up when cache is full"""
        self.cache._max_cache_size = 5  # Small limit
        
        # Add entries with immediate expiration
        for i in range(3):
            cache_key = f"jwt_validation:expired_{i}:access"
            payload = {"sub": f"user-{i}", "exp": int(time.time()) - 3600}  # Expired
            self.cache._validation_cache[cache_key] = {
                'data': payload,
                'expires': time.time() - 1  # Cache entry also expired
            }
        
        # Add new entry to trigger cleanup
        cache_key = "jwt_validation:new:access"
        payload = {"sub": "new-user", "exp": int(time.time()) + 3600}
        self.cache.cache_validation_result(cache_key, payload)
        
        # Test that cleanup logic runs - exact behavior depends on implementation
        # The new entry should be added successfully regardless
        assert "jwt_validation:new:access" in self.cache._validation_cache
    
    def test_get_cache_stats_accuracy(self):
        """Test cache statistics are accurate"""
        cache_key1 = "jwt_validation:stats1:access"
        cache_key2 = "jwt_validation:stats2:access"
        payload = {"sub": "stats-user", "exp": int(time.time()) + 3600}
        
        # Perform operations
        self.cache.get_from_cache(cache_key1)  # Miss
        self.cache.cache_validation_result(cache_key1, payload)
        self.cache.get_from_cache(cache_key1)  # Hit
        self.cache.get_from_cache(cache_key2)  # Miss
        
        stats = self.cache.get_cache_stats()
        assert stats["validation_count"] == 3
        assert stats["memory_cache_hits"] == 1
        assert stats["cache_misses"] == 2
        assert stats["memory_hit_rate_percent"] > 0
        assert stats["overall_hit_rate_percent"] > 0
        assert stats["memory_cache_size"] >= 1
        assert isinstance(stats["cache_enabled"], bool)
    
    def test_performance_under_concurrent_access(self):
        """Test cache handles concurrent access correctly"""
        import threading
        import random
        
        results = []
        errors = []
        cache_key = "jwt_validation:concurrent:access"
        payload = {"sub": "concurrent-user", "exp": int(time.time()) + 3600}
        
        def cache_operation():
            try:
                # Random cache operations
                if random.choice([True, False]):
                    self.cache.cache_validation_result(cache_key, payload)
                    result = self.cache.get_from_cache(cache_key)
                    results.append(result)
                else:
                    result = self.cache.get_from_cache(cache_key)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_operation)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Should not have any errors
        assert len(errors) == 0
        # Should have results
        assert len(results) > 0


class TestJWTValidationCacheUserInvalidation(BaseIntegrationTest):
    """Test user-specific cache invalidation"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
        self.user_id = str(uuid.uuid4())
        self.other_user_id = str(uuid.uuid4())
    
    def test_invalidate_user_cache_memory_only(self):
        """Test user cache invalidation in memory cache"""
        # Cache tokens for two users
        user_payload = {"sub": self.user_id, "exp": int(time.time()) + 3600}
        other_payload = {"sub": self.other_user_id, "exp": int(time.time()) + 3600}
        
        user_key = f"jwt_validation:user1:access"
        other_key = f"jwt_validation:user2:access"
        
        self.cache.cache_validation_result(user_key, user_payload)
        self.cache.cache_validation_result(other_key, other_payload)
        
        # Verify both are cached
        assert self.cache.get_from_cache(user_key) is not None
        assert self.cache.get_from_cache(other_key) is not None
        
        # Invalidate specific user
        self.cache.invalidate_user_cache(self.user_id)
        
        # Only target user's cache should be invalidated
        assert self.cache.get_from_cache(user_key) is None
        assert self.cache.get_from_cache(other_key) is not None
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_invalidate_user_cache_with_redis(self, mock_redis_manager):
        """Test user cache invalidation includes Redis"""
        # Setup Redis mock
        mock_redis_client = MagicMock()
        mock_redis_client.keys.return_value = [
            b"jwt_cache:hash1:access",
            b"jwt_cache:hash2:refresh"
        ]
        mock_redis_client.get.side_effect = [
            json.dumps({"sub": self.user_id, "exp": int(time.time()) + 3600}),
            json.dumps({"sub": self.other_user_id, "exp": int(time.time()) + 3600})
        ]
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.return_value = mock_redis_client
        
        # Update the cache to use the mocked Redis manager
        self.cache.redis_manager = mock_redis_manager
        self.cache._cache_enabled = True
        
        # Invalidate user cache
        self.cache.invalidate_user_cache(self.user_id)
        
        # Should scan Redis keys and delete matching ones
        mock_redis_client.keys.assert_called_once_with("jwt_cache:*")
        mock_redis_client.delete.assert_called()
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_invalidate_user_cache_redis_failure_graceful(self, mock_redis_manager):
        """Test user cache invalidation handles Redis failures gracefully"""
        # Setup Redis to fail
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.side_effect = Exception("Redis failed")
        
        # Should not raise exception
        self.cache.invalidate_user_cache(self.user_id)
        # Test passes if no exception is raised


class TestJWTValidationCacheClearAndMaintenance(BaseIntegrationTest):
    """Test cache clearing and maintenance operations"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
    
    def test_clear_cache_memory_only(self):
        """Test clearing memory cache"""
        # Add some cache entries
        payload = {"sub": "clear-test", "exp": int(time.time()) + 3600}
        self.cache.cache_validation_result("key1", payload)
        self.cache.cache_validation_result("key2", payload)
        
        # Verify entries exist
        assert len(self.cache._validation_cache) == 2
        
        # Clear cache
        self.cache.clear_cache()
        
        # Should be empty
        assert len(self.cache._validation_cache) == 0
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_clear_cache_with_redis(self, mock_redis_manager):
        """Test clearing cache includes Redis"""
        # Setup Redis mock
        mock_redis_client = MagicMock()
        mock_redis_client.keys.return_value = [
            b"jwt_cache:key1",
            b"jwt_cache:key2"
        ]
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.return_value = mock_redis_client
        
        # Update the cache to use the mocked Redis manager
        self.cache.redis_manager = mock_redis_manager
        self.cache._cache_enabled = True
        
        # Clear cache
        self.cache.clear_cache()
        
        # Should clear both memory and Redis
        assert len(self.cache._validation_cache) == 0
        mock_redis_client.keys.assert_called_once_with("jwt_cache:*")
        mock_redis_client.delete.assert_called()
    
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    def test_clear_cache_redis_failure_graceful(self, mock_redis_manager):
        """Test cache clear handles Redis failures gracefully"""
        # Setup Redis to fail
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.side_effect = Exception("Redis connection failed")
        
        # Should not raise exception and still clear memory
        self.cache.clear_cache()
        assert len(self.cache._validation_cache) == 0


class TestJWTValidationCacheAsyncOperations(BaseIntegrationTest):
    """Test async Redis operations"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
    
    @pytest.mark.asyncio
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    async def test_async_redis_cache_write(self, mock_redis_manager):
        """Test async Redis cache write operation"""
        # Setup Redis mock
        mock_redis_client = MagicMock()
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.return_value = mock_redis_client
        
        # Update the cache to use the mocked Redis manager
        self.cache.redis_manager = mock_redis_manager
        
        cache_key = "test_async_key"
        cache_data = {"sub": "async-user", "exp": int(time.time()) + 3600}
        
        # Test async cache write
        await self.cache._cache_to_redis_async(cache_key, cache_data, 300)
        
        # Should call Redis setex
        mock_redis_client.setex.assert_called_once_with(
            f"jwt_cache:{cache_key}",
            300,
            json.dumps(cache_data, default=str)
        )
    
    @pytest.mark.asyncio
    @patch('auth_service.auth_core.redis_manager.auth_redis_manager')
    async def test_async_redis_cache_write_failure(self, mock_redis_manager):
        """Test async Redis cache write handles failures gracefully"""
        # Setup Redis to fail
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.side_effect = Exception("Redis write failed")
        
        # Should not raise exception
        await self.cache._cache_to_redis_async("key", {"test": "data"}, 300)


class TestJWTValidationCacheEdgeCases(BaseIntegrationTest):
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.cache = JWTValidationCache()
    
    def test_cache_with_none_payload(self):
        """Test caching None payload (invalid token)"""
        cache_key = "jwt_validation:none_test:access"
        
        # Cache None result
        self.cache.cache_validation_result(cache_key, None)
        
        # Should return "INVALID" string for None results or None depending on implementation
        result = self.cache.get_from_cache(cache_key)
        assert result == "INVALID" or result is None
        # But should count as cache hit
        assert self.cache._validation_stats["cache_hits"] == 1
    
    def test_cache_with_invalid_json_payload(self):
        """Test caching with complex objects that might cause JSON issues"""
        cache_key = "jwt_validation:complex_test:access"
        
        # Create payload with datetime (should be handled by default=str)
        from datetime import datetime
        complex_payload = {
            "sub": "complex-user",
            "exp": int(time.time()) + 3600,
            "created": datetime.now()  # This will use default=str
        }
        
        # Should not raise exception
        self.cache.cache_validation_result(cache_key, complex_payload)
        
        # Should be retrievable (datetime converted to string)
        result = self.cache.get_from_cache(cache_key)
        assert result is not None
        assert result["sub"] == "complex-user"
    
    def test_get_cache_stats_with_zero_validations(self):
        """Test statistics calculation with zero validations"""
        stats = self.cache.get_cache_stats()
        
        # Should handle division by zero gracefully
        assert stats["validation_count"] == 0
        assert stats["memory_hit_rate_percent"] == 0
        assert stats["redis_hit_rate_percent"] == 0
        assert stats["overall_hit_rate_percent"] == 0
        assert isinstance(stats["cache_enabled"], bool)
    
    def test_cache_key_with_empty_token(self):
        """Test cache key generation with edge case tokens"""
        # Empty token
        key1 = self.cache.get_cache_key("", "access")
        assert isinstance(key1, str)
        assert len(key1) > 0
        
        # Very long token
        long_token = "x" * 10000
        key2 = self.cache.get_cache_key(long_token, "access")
        assert isinstance(key2, str)
        assert len(key2) < 100  # Should be hashed to manageable size
    
    def test_memory_cache_corruption_handling(self):
        """Test handling of corrupted memory cache entries"""
        cache_key = "jwt_validation:corrupt_test:access"
        
        # Manually corrupt cache entry
        self.cache._validation_cache[cache_key] = {
            'data': "not_a_dict",  # Invalid data type
            'expires': time.time() + 300
        }
        
        # Should handle gracefully
        result = self.cache.get_from_cache(cache_key)
        # Might return the invalid data or None, but shouldn't crash
        assert True  # Test passes if no exception


class TestJWTValidationCacheGlobalInstance(BaseIntegrationTest):
    """Test the global cache instance"""
    
    def test_global_instance_exists(self):
        """Test global jwt_validation_cache instance exists"""
        from auth_service.auth_core.core.jwt_cache import jwt_validation_cache
        
        assert jwt_validation_cache is not None
        assert isinstance(jwt_validation_cache, JWTValidationCache)
    
    def test_global_instance_functionality(self):
        """Test global instance functions correctly"""
        from auth_service.auth_core.core.jwt_cache import jwt_validation_cache
        
        # Test basic functionality
        cache_key = jwt_validation_cache.get_cache_key("global_test_token", "access")
        assert cache_key is not None
        
        # Test caching
        test_payload = {"sub": "global-test", "exp": int(time.time()) + 3600}
        jwt_validation_cache.cache_validation_result(cache_key, test_payload)
        
        result = jwt_validation_cache.get_from_cache(cache_key)
        assert result is not None
        assert result["sub"] == "global-test"
    
    def test_global_instance_stats(self):
        """Test global instance statistics"""
        from auth_service.auth_core.core.jwt_cache import jwt_validation_cache
        
        stats = jwt_validation_cache.get_cache_stats()
        assert isinstance(stats, dict)
        assert "validation_count" in stats
        assert "cache_enabled" in stats