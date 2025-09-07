"""Unit test regression suite for TokenCache - Critical Authentication Fix

This test suite ensures the TokenCache properly implements the cache_token method
that is required by auth_client_core.py to prevent authentication failures.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability
- Value Impact: Prevents authentication failures that block user access
- Strategic Impact: Ensures core authentication flow works reliably

ERROR BEING FIXED:
2025-09-07 03:07:59 - netra_backend.app.clients.auth_client_core - CRITICAL - 
USER AUTHENTICATION FAILURE: Token validation failed: 'TokenCache' object has no attribute 'cache_token'
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Import the modules under test
from netra_backend.app.clients.auth_client_cache import (
    TokenCache,
    AuthClientCache,
    CacheEntry
)


class TestTokenCacheRegression:
    """Regression test suite for TokenCache to ensure cache_token method exists and works correctly."""
    
    @pytest.fixture
    def auth_cache(self):
        """Create AuthClientCache instance for testing."""
        return AuthClientCache(default_ttl=300)
    
    @pytest.fixture
    def token_cache(self, auth_cache):
        """Create TokenCache instance for testing."""
        return TokenCache(auth_cache)
    
    @pytest.mark.asyncio
    async def test_cache_token_method_exists(self, token_cache):
        """CRITICAL: Verify cache_token method exists to prevent AttributeError.
        
        This test ensures the method that auth_client_core.py calls actually exists.
        """
        # Verify the method exists
        assert hasattr(token_cache, 'cache_token'), "TokenCache must have cache_token method"
        assert callable(getattr(token_cache, 'cache_token', None)), "cache_token must be callable"
    
    @pytest.mark.asyncio
    async def test_cache_token_stores_validation_result(self, token_cache):
        """Test that cache_token properly stores token validation results.
        
        This matches the usage in auth_client_core.py line 217:
        self.token_cache.cache_token(token, result)
        """
        # Test data matching real validation results
        test_token = "test_jwt_token_123"
        validation_result = {
            "valid": True,
            "user_id": "user_123",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "exp": int(time.time()) + 3600
        }
        
        # Call cache_token as auth_client_core does
        await token_cache.cache_token(test_token, validation_result)
        
        # Verify the token was cached
        cached_result = await token_cache.get_cached_token(test_token)
        assert cached_result is not None, "Token should be cached"
        assert cached_result == validation_result, "Cached result should match original"
    
    @pytest.mark.asyncio
    async def test_cache_token_with_ttl(self, token_cache):
        """Test cache_token with custom TTL for token expiration."""
        test_token = "short_lived_token"
        validation_result = {"valid": True, "user_id": "temp_user"}
        
        # Cache with short TTL
        await token_cache.cache_token(test_token, validation_result, ttl=1)
        
        # Should be cached immediately
        cached = await token_cache.get_cached_token(test_token)
        assert cached is not None
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired now
        cached = await token_cache.get_cached_token(test_token)
        assert cached is None, "Token should be expired"
    
    @pytest.mark.asyncio
    async def test_invalidate_cached_token_method_exists(self, token_cache):
        """Verify invalidate_cached_token method exists for cache cleanup.
        
        This is used in auth_client_core.py line 204:
        self.token_cache.invalidate_cached_token(token)
        """
        assert hasattr(token_cache, 'invalidate_cached_token'), "TokenCache must have invalidate_cached_token method"
        assert callable(getattr(token_cache, 'invalidate_cached_token', None)), "invalidate_cached_token must be callable"
    
    @pytest.mark.asyncio
    async def test_invalidate_cached_token_removes_from_cache(self, token_cache):
        """Test that invalidate_cached_token properly removes tokens from cache."""
        test_token = "token_to_invalidate"
        validation_result = {"valid": True, "user_id": "user_456"}
        
        # Cache the token
        await token_cache.cache_token(test_token, validation_result)
        
        # Verify it's cached
        cached = await token_cache.get_cached_token(test_token)
        assert cached is not None
        
        # Invalidate the token
        await token_cache.invalidate_cached_token(test_token)
        
        # Verify it's removed
        cached = await token_cache.get_cached_token(test_token)
        assert cached is None, "Token should be removed from cache"
    
    @pytest.mark.asyncio
    async def test_cache_token_overwrites_existing(self, token_cache):
        """Test that cache_token overwrites existing cached values."""
        test_token = "overwrite_token"
        first_result = {"valid": True, "user_id": "user_001", "version": 1}
        second_result = {"valid": True, "user_id": "user_001", "version": 2}
        
        # Cache first result
        await token_cache.cache_token(test_token, first_result)
        cached = await token_cache.get_cached_token(test_token)
        assert cached["version"] == 1
        
        # Overwrite with second result
        await token_cache.cache_token(test_token, second_result)
        cached = await token_cache.get_cached_token(test_token)
        assert cached["version"] == 2, "Should overwrite with new value"
    
    @pytest.mark.asyncio
    async def test_cache_token_handles_none_result(self, token_cache):
        """Test that cache_token handles None results gracefully.
        
        Based on auth_client_core.py line 216-217:
        if result:
            self.token_cache.cache_token(token, result)
        
        This test ensures the method can be called with None without errors.
        """
        test_token = "none_token"
        
        # Should not raise an error with None
        try:
            await token_cache.cache_token(test_token, None)
        except Exception as e:
            pytest.fail(f"cache_token should handle None gracefully: {e}")
        
        # Verify nothing was cached
        cached = await token_cache.get_cached_token(test_token)
        assert cached is None, "Nothing should be cached for None result"
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, token_cache):
        """Test thread-safety of cache_token with concurrent operations."""
        tokens = [f"concurrent_token_{i}" for i in range(10)]
        results = [{"valid": True, "user_id": f"user_{i}"} for i in range(10)]
        
        # Concurrent cache operations
        tasks = []
        for token, result in zip(tokens, results):
            tasks.append(token_cache.cache_token(token, result))
        
        await asyncio.gather(*tasks)
        
        # Verify all tokens were cached correctly
        for token, expected_result in zip(tokens, results):
            cached = await token_cache.get_cached_token(token)
            assert cached == expected_result, f"Token {token} should be cached correctly"
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_with_existing_methods(self, token_cache):
        """Ensure new cache_token method doesn't break existing TokenCache methods."""
        # Test existing set_cached_token method still works
        test_token = "backward_compat_token"
        token_data = {"valid": True, "user_id": "legacy_user"}
        
        await token_cache.set_cached_token(test_token, token_data, expires_in=3600)
        cached = await token_cache.get_cached_token(test_token)
        assert cached == token_data
        
        # Test existing get_token/set_token methods still work
        user_id = "test_user"
        user_token = "user_specific_token"
        
        await token_cache.set_token(user_id, user_token, expires_in=3600)
        retrieved = await token_cache.get_token(user_id)
        assert retrieved == user_token
    
    @pytest.mark.asyncio
    async def test_integration_with_auth_client_core_flow(self, token_cache):
        """Simulate the actual flow from auth_client_core to ensure compatibility.
        
        This test simulates the exact usage pattern from auth_client_core.py:
        1. Check cached result with get_cached_token (line 195)
        2. Validate token remotely if not cached
        3. Cache successful result with cache_token (line 217)
        4. Invalidate on blacklist with invalidate_cached_token (line 204)
        """
        test_token = "integration_test_token"
        
        # Step 1: Check cache (should be empty initially)
        cached = await token_cache.get_cached_token(test_token)
        assert cached is None, "Cache should be empty initially"
        
        # Step 2: Simulate successful validation
        validation_result = {
            "valid": True,
            "user_id": "integration_user",
            "email": "user@example.com",
            "permissions": ["read"],
            "exp": int(time.time()) + 3600
        }
        
        # Step 3: Cache the validation result (as done in _cache_validation_result)
        await token_cache.cache_token(test_token, validation_result)
        
        # Verify it's cached
        cached = await token_cache.get_cached_token(test_token)
        assert cached == validation_result
        
        # Step 4: Simulate token blacklisting
        await token_cache.invalidate_cached_token(test_token)
        
        # Verify it's removed
        cached = await token_cache.get_cached_token(test_token)
        assert cached is None, "Blacklisted token should be removed"


class TestTokenCacheErrorScenarios:
    """Test error scenarios and edge cases for TokenCache."""
    
    @pytest.fixture
    def token_cache(self):
        """Create TokenCache with integer TTL for backward compatibility test."""
        return TokenCache(300)  # Using integer TTL
    
    @pytest.mark.asyncio
    async def test_cache_token_with_integer_ttl_initialization(self, token_cache):
        """Test that TokenCache initialized with integer TTL still supports cache_token."""
        test_token = "int_ttl_token"
        validation_result = {"valid": True, "user_id": "ttl_user"}
        
        # Should work even when initialized with integer TTL
        await token_cache.cache_token(test_token, validation_result)
        
        cached = await token_cache.get_cached_token(test_token)
        assert cached == validation_result
    
    @pytest.mark.asyncio
    async def test_cache_token_with_invalid_token_type(self):
        """Test cache_token handles invalid token types gracefully."""
        cache = TokenCache(AuthClientCache())
        
        # Test with None token
        try:
            await cache.cache_token(None, {"valid": True})
        except TypeError:
            pass  # Expected to handle this gracefully or raise TypeError
        
        # Test with non-string token
        try:
            await cache.cache_token(12345, {"valid": True})
        except TypeError:
            pass  # Expected to handle this gracefully or raise TypeError
    
    @pytest.mark.asyncio
    async def test_cache_token_with_complex_validation_result(self):
        """Test cache_token with complex nested validation results."""
        cache = TokenCache(AuthClientCache())
        test_token = "complex_token"
        
        complex_result = {
            "valid": True,
            "user": {
                "id": "user_789",
                "email": "complex@example.com",
                "profile": {
                    "name": "Test User",
                    "roles": ["admin", "user"],
                    "metadata": {
                        "last_login": "2025-01-01T00:00:00Z",
                        "mfa_enabled": True
                    }
                }
            },
            "session": {
                "id": "session_123",
                "expires_at": int(time.time()) + 7200
            },
            "permissions": ["read", "write", "delete"],
            "token_metadata": {
                "issued_at": int(time.time()),
                "issuer": "auth_service",
                "audience": ["api", "web"]
            }
        }
        
        await cache.cache_token(test_token, complex_result)
        cached = await cache.get_cached_token(test_token)
        
        assert cached == complex_result, "Complex nested results should be cached correctly"
        assert cached["user"]["profile"]["metadata"]["mfa_enabled"] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])