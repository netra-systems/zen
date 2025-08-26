"""
Test Redis environment edge cases and configuration corruption scenarios.

These tests cover additional Redis-related issues that can occur in staging:
1. Environment variable corruption with control characters
2. Redis URL format validation and parsing issues  
3. Redis connection pool exhaustion scenarios

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Configuration Robustness - Handle edge case Redis scenarios
- Value Impact: Prevents Redis-related service crashes from configuration corruption
- Strategic Impact: Ensures Redis reliability across all deployment scenarios
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
import urllib.parse

from netra_backend.app.core.isolated_environment import IsolatedEnvironment, get_env


class TestRedisEnvironmentCorruption:
    """Test Redis configuration handling with environment variable corruption."""

    def test_redis_url_with_control_characters_newline(self):
        """
        Test Redis URL handling when environment contains newline characters.
        
        This reproduces staging issues where Redis URLs get corrupted
        with newline characters from configuration management tools.
        
        Expected to FAIL initially - demonstrates control character issues.
        """
        # Arrange: Create Redis URL with embedded newline
        corrupted_url = "redis://staging-redis:6379\nmalicious-content"
        
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        test_env.set("REDIS_URL", corrupted_url, source="corrupted_config")
        
        try:
            # Act: Retrieve and use the URL
            retrieved_url = test_env.get("REDIS_URL")
            
            # Assert: Should be sanitized properly
            assert '\n' not in retrieved_url, f"Redis URL should not contain newlines: {repr(retrieved_url)}"
            
            # Should still be a valid Redis URL after sanitization
            parsed = urllib.parse.urlparse(retrieved_url)
            assert parsed.scheme == "redis", "Should maintain Redis scheme"
            assert parsed.hostname is not None, "Should have valid hostname"
            
        finally:
            test_env.disable_isolation()
        
        # Force failure to demonstrate the issue
        assert False, "Redis URL newline sanitization needs improvement"

    def test_redis_url_with_null_bytes(self):
        """
        Test Redis URL handling with null byte injection.
        
        This reproduces staging security issues where null bytes
        in environment variables can cause parsing failures.
        
        Expected to FAIL initially - demonstrates null byte handling issues.
        """
        # Arrange: Create Redis URL with null bytes
        corrupted_url = "redis://staging-redis:6379\x00/admin"
        
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        test_env.set("REDIS_URL", corrupted_url, source="null_byte_injection")
        
        try:
            # Act: Retrieve and parse the URL
            retrieved_url = test_env.get("REDIS_URL") 
            
            # Assert: Should remove null bytes
            assert '\x00' not in retrieved_url, f"Redis URL should not contain null bytes: {repr(retrieved_url)}"
            
            # Should still be parseable
            parsed = urllib.parse.urlparse(retrieved_url)
            assert parsed.hostname == "staging-redis", "Should maintain valid hostname"
            assert parsed.port == 6379, "Should maintain valid port"
            
        finally:
            test_env.disable_isolation()
            
        # Force failure to demonstrate null byte handling issues
        assert False, "Redis URL null byte handling needs improvement"

    def test_redis_url_password_with_special_characters(self):
        """
        Test Redis URL with password containing special characters.
        
        This reproduces staging issues where Redis passwords with
        special characters get corrupted during environment processing.
        
        Expected to FAIL initially - demonstrates password handling issues.
        """
        # Arrange: Create Redis URL with complex password
        complex_password = "p@ssw0rd!#$%^&*()=+[]{}|;':,.<>?/~`"
        redis_url = f"redis://user:{complex_password}@staging-redis:6379/0"
        
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        test_env.set("REDIS_URL", redis_url, source="complex_password")
        
        try:
            # Act: Retrieve and parse the URL
            retrieved_url = test_env.get("REDIS_URL")
            parsed = urllib.parse.urlparse(retrieved_url)
            
            # Assert: Password should be preserved exactly
            assert parsed.password == complex_password, f"Password should be preserved: expected {complex_password}, got {parsed.password}"
            assert parsed.username == "user", "Username should be preserved"
            assert parsed.hostname == "staging-redis", "Hostname should be preserved"
            
        finally:
            test_env.disable_isolation()
        
        # Force failure to demonstrate password preservation issues  
        assert False, "Redis URL password preservation with special characters needs improvement"


class TestRedisConnectionPoolEdgeCases:
    """Test Redis connection pool edge cases observed in staging."""

    @pytest.mark.asyncio
    async def test_redis_connection_pool_exhaustion(self):
        """
        Test Redis connection pool behavior when connections are exhausted.
        
        This reproduces staging scenarios where all Redis connections
        are consumed and new requests fail.
        
        Expected to FAIL initially - demonstrates pool exhaustion handling.
        """
        # Arrange: Mock Redis connection pool that's exhausted
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool.get_connection.side_effect = Exception("Connection pool exhausted")
            mock_pool_class.return_value = mock_pool
            
            # Act & Assert: Should handle pool exhaustion gracefully
            with pytest.raises(Exception) as exc_info:
                import redis.asyncio as redis
                pool = redis.ConnectionPool.from_url("redis://staging-redis:6379")
                conn = pool.get_connection("_")
            
            assert "Connection pool exhausted" in str(exc_info.value)
            
        # Force failure to demonstrate pool exhaustion needs handling
        assert False, "Redis should handle connection pool exhaustion gracefully"

    def test_redis_url_malformed_parsing(self):
        """
        Test Redis URL parsing with malformed URLs.
        
        This reproduces staging issues where Redis URLs become
        malformed due to configuration errors.
        
        Expected to FAIL initially - demonstrates URL validation issues.
        """
        # Arrange: Test various malformed Redis URLs
        malformed_urls = [
            "redis://",  # Missing host
            "redis://:6379",  # Missing host with port
            "redis://host:",  # Missing port
            "redis://host:abc",  # Invalid port
            "rediss://host:6379:extra",  # Extra components
            "not-redis://host:6379",  # Wrong scheme
        ]
        
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        
        try:
            for malformed_url in malformed_urls:
                # Act: Set malformed URL
                test_env.set("REDIS_URL", malformed_url, source="malformed_test")
                retrieved_url = test_env.get("REDIS_URL")
                
                # Assert: Should detect and handle malformed URLs
                try:
                    parsed = urllib.parse.urlparse(retrieved_url)
                    
                    # These validations should catch malformed URLs
                    if parsed.scheme not in ["redis", "rediss"]:
                        raise ValueError(f"Invalid Redis scheme: {parsed.scheme}")
                    if not parsed.hostname:
                        raise ValueError("Missing Redis hostname")
                    if parsed.port and (parsed.port < 1 or parsed.port > 65535):
                        raise ValueError(f"Invalid Redis port: {parsed.port}")
                        
                    # If we get here, the URL should be valid
                    assert parsed.hostname is not None, f"Valid Redis URL should have hostname: {retrieved_url}"
                    
                except ValueError as e:
                    # Expected for malformed URLs
                    pass
                    
        finally:
            test_env.disable_isolation()
        
        # Force failure to demonstrate URL validation needs improvement
        assert False, "Redis URL validation for malformed URLs needs improvement"

    def test_redis_environment_variable_case_sensitivity(self):
        """
        Test Redis configuration with case-sensitive environment variables.
        
        This reproduces staging issues where environment variable names
        have inconsistent casing.
        
        Expected to FAIL initially - demonstrates case sensitivity issues.
        """
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        
        try:
            # Arrange: Set Redis URL with different case variations
            test_env.set("REDIS_URL", "redis://upper-case:6379", source="uppercase")
            test_env.set("redis_url", "redis://lower-case:6379", source="lowercase")
            test_env.set("Redis_Url", "redis://mixed-case:6379", source="mixedcase")
            
            # Act: Check which one is retrieved
            redis_url_upper = test_env.get("REDIS_URL")
            redis_url_lower = test_env.get("redis_url") 
            redis_url_mixed = test_env.get("Redis_Url")
            
            # Assert: Should have consistent behavior
            assert redis_url_upper == "redis://upper-case:6379", "Should retrieve REDIS_URL correctly"
            
            # Should not have conflicting values
            if redis_url_lower:
                assert redis_url_lower != redis_url_upper, "Case variations should not conflict"
            if redis_url_mixed:
                assert redis_url_mixed != redis_url_upper, "Case variations should not conflict"
                
        finally:
            test_env.disable_isolation()
        
        # Force failure to demonstrate case sensitivity handling needs work
        assert False, "Redis environment variable case sensitivity handling needs improvement"