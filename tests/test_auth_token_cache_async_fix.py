"""Test for auth token cache async/await fix.

This test verifies that the AuthTokenCache methods are properly async
and can be awaited without causing "object NoneType can't be used in 
'await' expression" errors.
"""

import asyncio
import pytest
from typing import Dict, Any, Optional

# Import the fixed classes
from netra_backend.app.clients.auth_client_cache import AuthTokenCache
from netra_backend.app.clients.auth_client_core import AuthServiceClient


@pytest.mark.asyncio
async def test_auth_token_cache_async_methods():
    """Test that AuthTokenCache methods are properly async."""
    # Create cache instance
    cache = AuthTokenCache(cache_ttl_seconds=300)
    
    # Test data
    test_token = "test_jwt_token_12345"
    test_data = {
        "valid": True,
        "user_id": "test_user",
        "email": "test@example.com",
        "permissions": ["read", "write"]
    }
    
    # Test async cache_token - should not raise TypeError
    await cache.cache_token(test_token, test_data)
    
    # Test async get_cached_token - should not raise TypeError
    result = await cache.get_cached_token(test_token)
    assert result is not None, "Should retrieve cached token"
    assert result["user_id"] == "test_user"
    
    # Test async invalidate_cached_token - should not raise TypeError
    await cache.invalidate_cached_token(test_token)
    
    # Verify token was invalidated
    result = await cache.get_cached_token(test_token)
    assert result is None, "Token should be invalidated"


@pytest.mark.asyncio
async def test_auth_service_client_token_validation():
    """Test that AuthServiceClient can properly await token cache methods."""
    # Create client instance
    client = AuthServiceClient()
    
    # Test token
    test_token = "test_jwt_token_with_signature"
    
    # This should not raise "object NoneType can't be used in 'await' expression"
    # The method internally calls await self.token_cache.get_cached_token(token)
    try:
        result = await client._try_cached_token(test_token)
        # Result can be None (cache miss) or dict (cache hit)
        # The important thing is no TypeError is raised
        assert result is None or isinstance(result, dict)
    except TypeError as e:
        if "can't be used in 'await' expression" in str(e):
            pytest.fail(f"Async/await bug still present: {e}")
        raise


@pytest.mark.asyncio
async def test_concurrent_cache_operations():
    """Test that concurrent async operations work correctly."""
    cache = AuthTokenCache(cache_ttl_seconds=300)
    
    # Create multiple tokens
    tokens = [f"token_{i}" for i in range(10)]
    data_list = [{"user_id": f"user_{i}", "valid": True} for i in range(10)]
    
    # Cache all tokens concurrently
    await asyncio.gather(*[
        cache.cache_token(token, data) 
        for token, data in zip(tokens, data_list)
    ])
    
    # Retrieve all tokens concurrently
    results = await asyncio.gather(*[
        cache.get_cached_token(token) 
        for token in tokens
    ])
    
    # Verify all tokens were cached correctly
    for i, result in enumerate(results):
        assert result is not None, f"Token {i} should be cached"
        assert result["user_id"] == f"user_{i}"
    
    # Invalidate all tokens concurrently
    await asyncio.gather(*[
        cache.invalidate_cached_token(token) 
        for token in tokens
    ])
    
    # Verify all tokens were invalidated
    results = await asyncio.gather(*[
        cache.get_cached_token(token) 
        for token in tokens
    ])
    
    for result in results:
        assert result is None, "All tokens should be invalidated"


def test_synchronous_methods_still_exist():
    """Test that synchronous methods still exist for backward compatibility."""
    cache = AuthTokenCache(cache_ttl_seconds=300)
    
    # Verify sync methods exist
    assert hasattr(cache, 'get_cached_token_sync'), "Sync getter should exist"
    assert hasattr(cache, 'cache_token_sync'), "Sync setter should exist"
    assert hasattr(cache, 'invalidate_cached_token_sync'), "Sync invalidator should exist"
    
    # Test sync methods work
    test_token = "sync_test_token"
    test_data = {"user_id": "sync_user", "valid": True}
    
    cache.cache_token_sync(test_token, test_data)
    result = cache.get_cached_token_sync(test_token)
    assert result is not None
    assert result["user_id"] == "sync_user"
    
    cache.invalidate_cached_token_sync(test_token)
    result = cache.get_cached_token_sync(test_token)
    assert result is None


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_auth_token_cache_async_methods())
    asyncio.run(test_auth_service_client_token_validation())
    asyncio.run(test_concurrent_cache_operations())
    test_synchronous_methods_still_exist()
    print("All tests passed! Auth token cache async/await fix is working correctly.")