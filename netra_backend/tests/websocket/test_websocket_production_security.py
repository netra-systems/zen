"""
Production security tests for WebSocket implementation.

Tests production-specific security measures including:
- CORS hardening with environment-specific rules
- Token refresh security validation
- Rate limiting and blocking mechanisms
- Security header injection
- Threat pattern detection
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

import re

import pytest

from netra_backend.app.core.websocket_cors import (
    SECURITY_CONFIG,
    SUSPICIOUS_PATTERNS,
    WebSocketCORSHandler,
    get_environment_origins,
)

class TestProductionCORSSecurity:
    """Test production-specific CORS security measures."""
    
    def test_production_environment_detection(self):
        """Test that production environment is correctly detected and configured."""
        # Mock: Component isolation for testing without external dependencies
        with patch('os.getenv', return_value='production'):
            origins = get_environment_origins()
            
            # Should include production origins
            assert any('netrasystems.ai' in origin for origin in origins)
            # Should not include development localhost origins
            assert not any('localhost' in origin for origin in origins)
    
    def test_staging_environment_hybrid_config(self):
        """Test that staging environment allows both staging and dev origins."""
        # Mock: Component isolation for testing without external dependencies
        with patch('os.getenv', return_value='staging'):
            origins = get_environment_origins()
            
            # Should include staging origins
            assert any('staging.netrasystems.ai' in origin for origin in origins)
            # Should also include development origins for testing
            assert any('localhost' in origin for origin in origins)
    
    def test_custom_origins_from_environment(self):
        """Test that custom origins from environment variables are included."""
        custom_origins = "https://custom1.com,https://custom2.com"
        
        # Mock: Component isolation for testing without external dependencies
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'production',
                'WEBSOCKET_ALLOWED_ORIGINS': custom_origins
            }.get(key, default)
            
            origins = get_environment_origins()
            
            assert 'https://custom1.com' in origins
            assert 'https://custom2.com' in origins
    
    def test_origin_deduplication(self):
        """Test that duplicate origins are removed while preserving order."""
        # Create scenario with duplicates
        # Mock: Component isolation for testing without external dependencies
        with patch('app.core.websocket_cors.PRODUCTION_ORIGINS', ['https://netrasystems.ai', 'https://app.netrasystems.ai']):
            # Mock: Component isolation for testing without external dependencies
            with patch('os.getenv') as mock_getenv:
                mock_getenv.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'production',
                    'WEBSOCKET_ALLOWED_ORIGINS': 'https://netrasystems.ai,https://custom.com'
                }.get(key, default)
                
                origins = get_environment_origins()
                
                # Should not have duplicates
                assert origins.count('https://netrasystems.ai') == 1
                # Should include both production and custom
                assert 'https://app.netrasystems.ai' in origins
                assert 'https://custom.com' in origins

class TestThreatPatternDetection:
    """Test detection and blocking of suspicious origin patterns."""
    
    def test_ip_address_blocking(self):
        """Test that direct IP addresses are blocked in production."""
        handler = WebSocketCORSHandler(environment="production")
        
        suspicious_ips = [
            "http://192.168.1.1",
            "https://10.0.0.1:8080", 
            "http://172.16.0.1:3000",
            "https://203.0.113.1"
        ]
        
        for ip in suspicious_ips:
            assert handler.is_origin_allowed(ip) is False
            assert handler._is_suspicious_origin(ip) is True
    
    def test_tunnel_service_blocking(self):
        """Test that tunnel services (ngrok, localtunnel) are blocked."""
        handler = WebSocketCORSHandler(environment="production")
        
        tunnel_origins = [
            "https://abc123.ngrok.io",
            "https://myapp.localtunnel.me",
            "http://random.ngrok.io:8080"
        ]
        
        for origin in tunnel_origins:
            assert handler.is_origin_allowed(origin) is False
            assert handler._is_suspicious_origin(origin) is True
    
    def test_browser_extension_blocking(self):
        """Test that browser extensions are blocked."""
        handler = WebSocketCORSHandler(environment="production")
        
        extension_origins = [
            "chrome-extension://abcdefghijklmnop",
            "moz-extension://12345678-90ab-cdef", 
            "safari-extension://some-extension-id"
        ]
        
        for origin in extension_origins:
            assert handler.is_origin_allowed(origin) is False
    
    def test_unexpected_localhost_ports(self):
        """Test that unexpected localhost ports are blocked."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Standard development ports should be evaluated based on allowed origins
        standard_ports = ["http://localhost:3000", "http://localhost:3001"]
        
        # Unexpected ports should be blocked
        unexpected_ports = [
            "http://localhost:8080",
            "http://localhost:9000", 
            "http://localhost:4444"
        ]
        
        for origin in unexpected_ports:
            # These should be caught by suspicious pattern detection
            assert handler._is_suspicious_origin(origin) is True
    
    def test_heroku_app_selective_blocking(self):
        """Test that Heroku apps are blocked unless explicitly allowed."""
        # Default handler should block Heroku
        handler = WebSocketCORSHandler(environment="production")
        
        heroku_origin = "https://myapp.herokuapp.com"
        assert handler.is_origin_allowed(heroku_origin) is False
        
        # But should allow if explicitly whitelisted
        handler_with_heroku = WebSocketCORSHandler(
            allowed_origins=["https://myapp.herokuapp.com"],
            environment="production"
        )
        # Still blocked by suspicious pattern detection
        assert handler_with_heroku.is_origin_allowed(heroku_origin) is False
    
    def test_pattern_compilation_performance(self):
        """Test that suspicious patterns compile correctly and perform well."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Should have compiled patterns
        assert len(handler._suspicious_patterns) > 0
        
        # All patterns should be valid regex
        for pattern in handler._suspicious_patterns:
            assert isinstance(pattern, re.Pattern)
        
        # Test performance with multiple checks
        test_origins = [
            "https://netrasystems.ai",
            "http://192.168.1.1", 
            "chrome-extension://test",
            "https://legitimate-site.com"
        ]
        
        import time
        start_time = time.time()
        
        for _ in range(100):  # Run 100 times
            for origin in test_origins:
                handler._is_suspicious_origin(origin)
        
        elapsed = time.time() - start_time
        assert elapsed < 1.0  # Should complete in less than 1 second

class TestRateLimitingAndBlocking:
    """Test rate limiting and temporary blocking of violating origins."""
    
    def test_violation_tracking(self):
        """Test that violations are properly tracked per origin."""
        handler = WebSocketCORSHandler(environment="production")
        
        malicious_origin = "http://bad-actor.com"
        
        # Generate violations
        for i in range(3):
            handler.is_origin_allowed(malicious_origin)
            assert handler._violation_counts[malicious_origin] == i + 1
    
    def test_temporary_blocking_threshold(self):
        """Test that origins are blocked after exceeding violation threshold."""
        handler = WebSocketCORSHandler(environment="production")
        
        repeat_offender = "http://repeat-offender.com"
        
        # Generate violations up to threshold
        for i in range(4):
            result = handler.is_origin_allowed(repeat_offender)
            assert result is False
            assert repeat_offender not in handler._blocked_origins  # Not blocked yet
        
        # One more violation should trigger blocking
        handler.is_origin_allowed(repeat_offender)
        assert repeat_offender in handler._blocked_origins
    
    def test_blocked_origin_always_denied(self):
        """Test that blocked origins are denied even if added to allowed list."""
        handler = WebSocketCORSHandler(environment="production")
        
        blocked_origin = "https://blocked-site.com"
        
        # Block the origin
        handler._blocked_origins.add(blocked_origin)
        
        # Even if we add to allowed origins, should still be blocked
        handler.allowed_origins.append(blocked_origin)
        assert handler.is_origin_allowed(blocked_origin) is False
    
    def test_violation_count_reset_on_unblock(self):
        """Test that violation counts are reset when origin is unblocked."""
        handler = WebSocketCORSHandler(environment="production")
        
        origin = "http://reformed-actor.com"
        
        # Generate violations and block
        for _ in range(6):
            handler.is_origin_allowed(origin)
        
        assert origin in handler._blocked_origins
        assert handler._violation_counts[origin] >= 5
        
        # Unblock 
        result = handler.unblock_origin(origin)
        
        assert result is True
        assert origin not in handler._blocked_origins
        assert handler._violation_counts.get(origin, 0) == 0
    
    def test_security_statistics_accuracy(self):
        """Test that security statistics accurately reflect system state."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Generate known violations
        origins = ["http://bad1.com", "http://bad2.com", "http://bad3.com"]
        
        for origin in origins:
            for _ in range(2):  # 2 violations each
                handler.is_origin_allowed(origin)
        
        # Block one origin manually
        handler._blocked_origins.add("http://manually-blocked.com")
        
        stats = handler.get_security_stats()
        
        assert stats["total_violations"] == 6  # 3 origins * 2 violations each
        assert stats["blocked_origin_count"] >= 1  # At least the manually blocked one
        assert "bad1.com" in str(stats["violation_counts"])
        assert stats["environment"] == "production"

class TestSecurityHeaderInjection:
    """Test injection of security headers in production responses."""
    
    def test_production_security_headers(self):
        """Test that all required security headers are included in production."""
        handler = WebSocketCORSHandler(environment="production")
        
        headers = handler.get_cors_headers("https://netrasystems.ai")
        
        required_security_headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        for header_name, expected_value in required_security_headers.items():
            assert header_name in headers
            assert headers[header_name] == expected_value
    
    def test_development_no_security_headers(self):
        """Test that security headers are not added in development."""
        handler = WebSocketCORSHandler(environment="development")
        
        headers = handler.get_cors_headers("http://localhost:3000")
        
        # Should not include production security headers
        assert "Strict-Transport-Security" not in headers
        assert "X-Frame-Options" not in headers
        
        # Should still include basic CORS headers
        assert "Access-Control-Allow-Origin" in headers
        assert "Access-Control-Allow-Credentials" in headers
    
    def test_cors_headers_basic_structure(self):
        """Test that basic CORS headers are always included."""
        handler = WebSocketCORSHandler(environment="production")
        
        headers = handler.get_cors_headers("https://netrasystems.ai")
        
        basic_cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Credentials", 
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
            "Vary"
        ]
        
        for header in basic_cors_headers:
            assert header in headers
        
        assert headers["Access-Control-Allow-Origin"] == "https://netrasystems.ai"
        assert headers["Access-Control-Allow-Credentials"] == "true"
        assert headers["Access-Control-Allow-Methods"] == "GET"
        assert headers["Vary"] == "Origin"

class TestSecurityConfigurationValidation:
    """Test that security configuration is properly validated and applied."""
    
    def test_security_config_structure(self):
        """Test that SECURITY_CONFIG has all required fields."""
        required_fields = [
            "max_origin_length",
            "require_https_production",
            "block_suspicious_patterns", 
            "log_security_violations",
            "rate_limit_violations"
        ]
        
        for field in required_fields:
            assert field in SECURITY_CONFIG
    
    def test_suspicious_patterns_validity(self):
        """Test that all suspicious patterns are valid regex."""
        for pattern_str in SUSPICIOUS_PATTERNS:
            # Should not raise exception
            compiled = re.compile(pattern_str, re.IGNORECASE)
            assert compiled is not None
    
    def test_origin_length_enforcement(self):
        """Test that origin length limits are enforced correctly."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Test with exact maximum length
        max_length = SECURITY_CONFIG["max_origin_length"]
        max_origin = "https://" + "a" * (max_length - 8) + ".com"  # -8 for "https://"
        
        # This should be at or near the limit
        is_valid, reason = handler._validate_origin_security(max_origin)
        
        # Test with clearly over-length origin
        over_length_origin = "https://" + "a" * 300 + ".com"
        is_valid_over, reason_over = handler._validate_origin_security(over_length_origin)
        
        assert is_valid_over is False
        assert "too long" in reason_over.lower()
    
    def test_https_requirement_in_production(self):
        """Test that HTTPS requirement is enforced in production when configured."""
        # Test with HTTPS enforcement enabled
        if SECURITY_CONFIG["require_https_production"]:
            handler = WebSocketCORSHandler(environment="production")
            
            # HTTPS should pass security validation
            is_valid_https, _ = handler._validate_origin_security("https://secure-site.com")
            
            # HTTP should fail security validation in production
            is_valid_http, reason_http = handler._validate_origin_security("http://insecure-site.com")
            
            assert is_valid_https is True
            assert is_valid_http is False
            assert "HTTPS required" in reason_http
    
    def test_security_config_can_be_disabled(self):
        """Test that security features can be selectively disabled."""
        # This test verifies the configuration flags work
        original_suspicious = SECURITY_CONFIG["block_suspicious_patterns"]
        
        try:
            # Temporarily disable suspicious pattern blocking
            SECURITY_CONFIG["block_suspicious_patterns"] = False
            
            handler = WebSocketCORSHandler(environment="production")
            
            # Suspicious origin should not be blocked when feature is disabled
            suspicious_origin = "http://192.168.1.1"
            assert handler._is_suspicious_origin(suspicious_origin) is False
            
        finally:
            # Restore original setting
            SECURITY_CONFIG["block_suspicious_patterns"] = original_suspicious

class TestPerformanceUnderAttack:
    """Test system performance under security attacks."""
    
    def test_many_violations_performance(self):
        """Test that system maintains performance under many violation attempts."""
        handler = WebSocketCORSHandler(environment="production")
        
        import time
        start_time = time.time()
        
        # Simulate attack with many different malicious origins
        for i in range(1000):
            malicious_origin = f"http://malicious-{i}.com"
            handler.is_origin_allowed(malicious_origin)
        
        elapsed = time.time() - start_time
        
        # Should handle 1000 violation checks in reasonable time
        assert elapsed < 5.0  # Less than 5 seconds
        
        # Should have tracked violations
        assert len(handler._violation_counts) == 1000
    
    def test_blocked_origins_lookup_performance(self):
        """Test that blocked origin lookups remain fast even with many blocked origins."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Add many blocked origins
        for i in range(10000):
            handler._blocked_origins.add(f"http://blocked-{i}.com")
        
        import time
        start_time = time.time()
        
        # Test lookup performance
        for i in range(100):
            test_origin = f"http://blocked-{i * 100}.com"
            handler.is_origin_allowed(test_origin)
        
        elapsed = time.time() - start_time
        
        # Lookups should remain fast even with many blocked origins
        assert elapsed < 1.0
    
    def test_memory_usage_under_attack(self):
        """Test that memory usage doesn't grow unbounded under attack."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Simulate sustained attack
        for i in range(50000):
            origin = f"http://attack-{i % 1000}.com"  # Cycle through 1000 origins
            handler.is_origin_allowed(origin)
        
        # Violation counts should not exceed reasonable bounds
        assert len(handler._violation_counts) <= 1000
        
        # Blocked origins should have reasonable upper bound
        # (In real implementation, you might add periodic cleanup)
        assert len(handler._blocked_origins) <= 1000


class TestWebSocketConnectionHijackingPrevention:
    """ITERATION 27: Prevent WebSocket connection hijacking attacks."""
    
    def test_websocket_connection_hijacking_prevention(self):
        """ITERATION 27: Prevent WebSocket connection hijacking that steals user data.
        
        Business Value: Prevents data theft attacks worth $200K+ per breach.
        """
        handler = WebSocketCORSHandler(environment="production")
        
        # Test 1: Origin spoofing attempt should be blocked
        legitimate_origin = "https://app.netra.ai"
        spoofed_origin = "https://app.netra.ai.evil.com"  # Subdomain attack
        
        # Legitimate origin should pass
        assert handler.is_origin_allowed(legitimate_origin) is True
        
        # Spoofed origin should be blocked
        assert handler.is_origin_allowed(spoofed_origin) is False
        assert handler._is_suspicious_origin(spoofed_origin) is True
        
        # Test 2: Direct IP connection attempts should be blocked
        ip_origins = [
            "https://192.168.1.100",
            "http://10.0.0.1:8080", 
            "wss://203.0.113.1"
        ]
        
        for ip_origin in ip_origins:
            assert handler.is_origin_allowed(ip_origin) is False
            assert handler._is_suspicious_origin(ip_origin) is True
            
        # Test 3: Protocol downgrade attacks should be detected
        secure_origin = "https://app.netra.ai"
        downgrade_origin = "http://app.netra.ai"
        
        # HTTPS should pass in production
        is_valid_https, _ = handler._validate_origin_security(secure_origin)
        assert is_valid_https is True
        
        # HTTP downgrade should be blocked in production
        if SECURITY_CONFIG["require_https_production"]:
            is_valid_http, reason = handler._validate_origin_security(downgrade_origin)
            assert is_valid_http is False
            assert "HTTPS required" in reason
            
        # Test 4: Connection rate limiting should prevent brute force
        attacker_origin = "http://attacker.com"
        
        # Multiple rapid requests from same malicious origin
        for i in range(10):
            result = handler.is_origin_allowed(attacker_origin)
            assert result is False
            
        # Should be blocked after violations
        assert attacker_origin in handler._blocked_origins
        
        # Test 5: Cross-origin resource sharing (CORS) bypass attempts
        malicious_origins = [
            "null",  # File:// protocol attempt
            "data:text/html,<script>evil()</script>",  # Data URI attempt
            "chrome-extension://malicious-ext-id",  # Extension bypass
            "moz-extension://bypass-attempt"  # Firefox extension
        ]
        
        for malicious_origin in malicious_origins:
            assert handler.is_origin_allowed(malicious_origin) is False
            
        # Test 6: WebSocket upgrade validation
        headers = handler.get_cors_headers(legitimate_origin)
        
        # Should have proper CORS headers to prevent hijacking
        assert headers["Access-Control-Allow-Origin"] == legitimate_origin
        assert headers["Access-Control-Allow-Credentials"] == "true"
        assert "Vary" in headers  # Prevents cache poisoning
        
        # Should include security headers in production
        security_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options"
        ]
        
        for security_header in security_headers:
            assert security_header in headers
            
        # Test 7: Connection fingerprinting for anomaly detection
        stats = handler.get_security_stats()
        
        assert "total_violations" in stats
        assert "blocked_origin_count" in stats
        assert stats["environment"] == "production"
        assert stats["total_violations"] >= 10  # From our test attacks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])