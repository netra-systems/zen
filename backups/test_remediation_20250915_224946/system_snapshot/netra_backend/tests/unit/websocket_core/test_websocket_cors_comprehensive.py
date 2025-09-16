"""
Unit Tests for WebSocket CORS Handler - Security Critical Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure WebSocket connections prevent security breaches
- Value Impact: CORS violations could expose $500K+ ARR to security attacks
- Strategic Impact: MISSION CRITICAL - Security foundation for real-time communications

This test suite provides comprehensive coverage for the WebSocket CORS handler
(websocket_cors.py) which implements security controls for WebSocket connections.

COVERAGE TARGET: netra_backend/app/core/websocket_cors.py
Issue: #727 - WebSocket core coverage gaps

The WebSocket CORS handler is mission-critical because:
1. It prevents unauthorized cross-origin WebSocket connections
2. It implements environment-specific security policies
3. It provides audit logging for security violations
4. It supports development flexibility while maintaining production security

CRITICAL REQUIREMENTS:
- Production security must be enforced strictly
- Development environments must be permissive for testing
- All security violations must be logged and tracked
- Performance must be optimized for high-volume connections
- Rate limiting must prevent abuse

Test Strategy:
- CORS origin validation in different environments
- Security policy enforcement and violation handling
- Performance testing for connection validation
- Error handling and logging verification
- Environment-specific behavior validation
"""

import pytest
import re
import time
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional

# SSOT Test Framework Import
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import WebSocket mocks
from fastapi import WebSocket
from starlette.datastructures import Headers

# Import the system under test
from netra_backend.app.core.websocket_cors import (
    WebSocketCORSHandler,
    WebSocketCORSMiddleware,
    validate_websocket_origin,
    get_websocket_cors_handler,
    configure_websocket_cors,
    check_websocket_cors,
    get_websocket_cors_headers,
    get_environment_origins,
    get_environment_origins_for_environment,
    get_security_config,
    SUSPICIOUS_PATTERNS,
    _extract_origin_from_websocket
)


class WebSocketCORSHandlerTests(SSotBaseTestCase):
    """
    Comprehensive unit tests for WebSocket CORS handler.
    
    Targeting: netra_backend/app/core/websocket_cors.py
    Issue: #727 - websocket-core coverage gaps
    Priority: CRITICAL - Security infrastructure
    """
    
    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)
        
        # Common test origins for different environments
        self.dev_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://frontend:3000"
        ]
        
        self.staging_origins = [
            "https://staging.netrasystems.ai",
            "https://netra-staging.appspot.com",
            "http://localhost:3000"  # Still allow localhost in staging
        ]
        
        self.production_origins = [
            "https://app.netrasystems.ai",
            "https://netra-production.appspot.com"
        ]

    def test_cors_handler_initialization_development(self):
        """
        Test CORS handler initialization in development environment.
        
        Business Critical: Development must be permissive for productivity.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=self.dev_origins,
            environment="development"
        )
        
        # Verify initialization
        assert handler.environment == "development"
        assert handler.allowed_origins == self.dev_origins
        assert not handler.security_config["block_suspicious_patterns"]
        assert not handler.security_config["require_https_production"]
        
        # Verify patterns compiled
        assert len(handler._origin_patterns) == len(self.dev_origins)
        assert len(handler._suspicious_patterns) == 0  # None in dev mode

    def test_cors_handler_initialization_production(self):
        """
        Test CORS handler initialization in production environment.
        
        Business Critical: Production must enforce strict security.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=self.production_origins,
            environment="production"
        )
        
        # Verify strict security configuration
        assert handler.environment == "production"
        assert handler.security_config["block_suspicious_patterns"]
        assert handler.security_config["require_https_production"]
        assert handler.security_config["rate_limit_violations"]
        
        # Verify suspicious patterns are compiled
        assert len(handler._suspicious_patterns) > 0

    def test_cors_handler_origin_validation_allowed_exact_match(self):
        """
        Test origin validation with exact matches.
        
        Business Critical: Allowed origins must be accepted reliably.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Exact match should be allowed
        assert handler.is_origin_allowed("https://app.netrasystems.ai") is True
        
        # With trailing slash should also be allowed
        assert handler.is_origin_allowed("https://app.netrasystems.ai/") is True
        
        # Different origin should be denied
        assert handler.is_origin_allowed("https://evil.com") is False

    def test_cors_handler_origin_validation_wildcard_patterns(self):
        """
        Test origin validation with wildcard patterns.
        
        Business Critical: Wildcard patterns must work correctly for subdomains.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://*.netrasystems.ai"],
            environment="production"
        )
        
        # Subdomain should be allowed
        assert handler.is_origin_allowed("https://app.netrasystems.ai") is True
        assert handler.is_origin_allowed("https://staging.netrasystems.ai") is True
        
        # Different domain should be denied
        assert handler.is_origin_allowed("https://app.evil.com") is False
        assert handler.is_origin_allowed("https://netrasystems.ai.evil.com") is False

    def test_cors_handler_development_permissive_mode(self):
        """
        Test that development mode is very permissive.
        
        Business Critical: Development productivity requires flexible origins.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["http://localhost:3000"],
            environment="development"
        )
        
        # Development should allow almost any reasonable origin
        test_origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://frontend:3000",
            "http://172.18.0.1:3000",  # Docker bridge IP
            "https://localhost:3000",  # HTTPS localhost
        ]
        
        for origin in test_origins:
            assert handler.is_origin_allowed(origin) is True, f"Development should allow {origin}"

    def test_cors_handler_production_security_enforcement(self):
        """
        Test strict security enforcement in production.
        
        Business Critical: Production must block unauthorized origins.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Should block suspicious patterns
        suspicious_origins = [
            "http://app.netrasystems.ai",  # HTTP in production
            "https://evil.com",  # Not in allowed list
            "https://192.168.1.1:3000",  # Direct IP
            "https://abc123.ngrok.io",  # Ngrok tunnel
            "chrome-extension://abc123"  # Browser extension
        ]
        
        for origin in suspicious_origins:
            assert handler.is_origin_allowed(origin) is False, f"Production should block {origin}"

    def test_cors_handler_rate_limiting_and_blocking(self):
        """
        Test rate limiting and temporary blocking of violating origins.
        
        Business Critical: Prevents abuse and DoS attacks via CORS violations.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        malicious_origin = "https://evil.com"
        
        # First few violations should be denied but not blocked
        for i in range(4):
            assert handler.is_origin_allowed(malicious_origin) is False
            
        # Should not be blocked yet
        assert malicious_origin not in handler._blocked_origins
        
        # 5th violation should trigger blocking
        assert handler.is_origin_allowed(malicious_origin) is False
        assert malicious_origin in handler._blocked_origins
        
        # Subsequent attempts should be blocked immediately
        assert handler.is_origin_allowed(malicious_origin) is False

    def test_cors_handler_manual_unblocking(self):
        """
        Test manual unblocking of origins for administrative purposes.
        
        Business Critical: Administrators must be able to unblock false positives.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Block an origin first
        test_origin = "https://test.com"
        handler._blocked_origins.add(test_origin)
        handler._violation_counts[test_origin] = 5
        
        # Verify it's blocked
        assert test_origin in handler._blocked_origins
        
        # Unblock it
        result = handler.unblock_origin(test_origin)
        assert result is True
        assert test_origin not in handler._blocked_origins
        assert test_origin not in handler._violation_counts
        
        # Unblocking non-blocked origin should return False
        result = handler.unblock_origin("https://never-blocked.com")
        assert result is False

    def test_cors_handler_security_statistics(self):
        """
        Test security statistics collection for monitoring.
        
        Business Critical: Security monitoring requires accurate statistics.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Generate some violations
        handler.is_origin_allowed("https://evil1.com")
        handler.is_origin_allowed("https://evil2.com")
        handler.is_origin_allowed("https://evil1.com")  # Repeat
        
        stats = handler.get_security_stats()
        
        # Verify statistics structure
        assert "violation_counts" in stats
        assert "blocked_origins" in stats
        assert "total_violations" in stats
        assert "environment" in stats
        
        # Verify counts
        assert stats["violation_counts"]["https://evil1.com"] == 2
        assert stats["violation_counts"]["https://evil2.com"] == 1
        assert stats["total_violations"] == 3
        assert stats["environment"] == "production"

    def test_cors_handler_cors_headers_generation(self):
        """
        Test CORS headers generation for responses.
        
        Business Critical: Proper CORS headers ensure browser compatibility.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        origin = "https://app.netrasystems.ai"
        headers = handler.get_cors_headers(origin)
        
        # Verify required CORS headers
        assert headers["Access-Control-Allow-Origin"] == origin
        assert headers["Access-Control-Allow-Credentials"] == "true"
        assert headers["Access-Control-Allow-Methods"] == "GET"
        assert "Authorization" in headers["Access-Control-Allow-Headers"]
        
        # Verify security headers in production
        assert "Strict-Transport-Security" in headers
        assert "X-Content-Type-Options" in headers

    def test_cors_handler_none_origin_handling(self):
        """
        Test handling of None origin (common for mobile/desktop apps).
        
        Business Critical: None origins are legitimate for native applications.
        """
        dev_handler = WebSocketCORSHandler(
            allowed_origins=["http://localhost:3000"],
            environment="development"
        )
        
        prod_handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Development should allow None origin
        assert dev_handler.is_origin_allowed(None) is True
        
        # Production should deny None origin
        assert prod_handler.is_origin_allowed(None) is False

    def test_suspicious_patterns_detection(self):
        """
        Test detection of suspicious origin patterns.
        
        Business Critical: Must block known attack vectors and tunnels.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Test various suspicious patterns
        suspicious_origins = [
            "https://192.168.1.1:3000",  # Direct IP
            "https://abc123.ngrok.io",  # Ngrok tunnel
            "https://test.localtunnel.me",  # Local tunnel
            "chrome-extension://abc123def456",  # Browser extension
            "moz-extension://abc123def456",  # Firefox extension
            "https://malicious.herokuapp.com",  # Heroku app
        ]
        
        for origin in suspicious_origins:
            is_suspicious = handler._is_suspicious_origin(origin)
            assert is_suspicious is True, f"Should detect {origin} as suspicious"

    def test_localhost_docker_patterns_in_development(self):
        """
        Test that localhost and Docker patterns are not suspicious in development.
        
        Business Critical: Development environments use local and Docker origins.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["http://localhost:3000"],
            environment="development"
        )
        
        # These should NOT be suspicious in development
        development_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://frontend:3000",
            "http://backend:8000",
            "http://172.18.0.1:3000",  # Docker bridge IP
        ]
        
        for origin in development_origins:
            is_suspicious = handler._is_suspicious_origin(origin)
            assert is_suspicious is False, f"Should NOT be suspicious in dev: {origin}"


class WebSocketCORSMiddlewareTests(SSotBaseTestCase):
    """
    Unit tests for WebSocket CORS ASGI middleware.
    
    Tests the middleware integration for CORS handling at the ASGI level.
    """
    
    def test_cors_middleware_initialization(self):
        """
        Test CORS middleware initialization with custom handler.
        
        Business Critical: Middleware must initialize correctly for ASGI apps.
        """
        mock_app = Mock()
        custom_handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        middleware = WebSocketCORSMiddleware(mock_app, custom_handler)
        
        assert middleware.app is mock_app
        assert middleware.cors_handler is custom_handler

    def test_cors_middleware_initialization_default_handler(self):
        """
        Test CORS middleware initialization with default handler.
        
        Business Critical: Default configuration must work out of the box.
        """
        mock_app = Mock()
        
        with patch('netra_backend.app.core.websocket_cors.get_environment_origins') as mock_get_origins:
            mock_get_origins.return_value = ["http://localhost:3000"]
            
            middleware = WebSocketCORSMiddleware(mock_app)
            
            assert middleware.app is mock_app
            assert middleware.cors_handler is not None
            assert isinstance(middleware.cors_handler, WebSocketCORSHandler)

    async def test_cors_middleware_websocket_scope_handling(self):
        """
        Test middleware handles WebSocket scopes correctly.
        
        Business Critical: WebSocket connections must be validated by CORS.
        """
        mock_app = Mock()
        
        # Create middleware with test handler
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        middleware = WebSocketCORSMiddleware(mock_app, handler)
        
        # Mock WebSocket scope with allowed origin
        scope = {
            "type": "websocket",
            "headers": [(b"origin", b"https://app.netrasystems.ai")]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Mock the app to verify it gets called
        middleware.app = AsyncMock()
        
        # Call middleware
        await middleware(scope, receive, send)
        
        # Verify app was called (origin was allowed)
        middleware.app.assert_called_once_with(scope, receive, send)
        
        # Verify origin was added to scope
        assert scope["websocket_cors_origin"] == "https://app.netrasystems.ai"

    async def test_cors_middleware_websocket_scope_rejection(self):
        """
        Test middleware rejects WebSocket connections with invalid origins.
        
        Business Critical: Invalid origins must be rejected to prevent attacks.
        """
        mock_app = Mock()
        
        # Create middleware with restrictive handler
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        middleware = WebSocketCORSMiddleware(mock_app, handler)
        
        # Mock WebSocket scope with invalid origin
        scope = {
            "type": "websocket",
            "headers": [(b"origin", b"https://evil.com")]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Mock the app (should not be called)
        middleware.app = AsyncMock()
        
        # Call middleware
        await middleware(scope, receive, send)
        
        # Verify app was NOT called
        middleware.app.assert_not_called()
        
        # Verify WebSocket was closed with policy violation
        send.assert_called_once_with({
            "type": "websocket.close",
            "code": 1008,  # Policy violation
            "reason": "Origin not allowed"
        })

    async def test_cors_middleware_non_websocket_passthrough(self):
        """
        Test middleware passes through non-WebSocket requests.
        
        Business Critical: HTTP requests should not be affected by WebSocket CORS.
        """
        mock_app = AsyncMock()
        
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        middleware = WebSocketCORSMiddleware(mock_app, handler)
        
        # Mock HTTP scope
        scope = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()
        
        # Call middleware
        await middleware(scope, receive, send)
        
        # Verify app was called directly (passthrough)
        mock_app.assert_called_once_with(scope, receive, send)


class WebSocketCORSUtilityFunctionsTests(SSotBaseTestCase):
    """
    Unit tests for WebSocket CORS utility functions.
    
    Tests standalone utility functions for CORS validation and configuration.
    """
    
    def test_extract_origin_from_websocket_single_header(self):
        """
        Test origin extraction with single origin header.
        
        Business Critical: Origin extraction must be reliable.
        """
        # Mock WebSocket with origin header
        mock_websocket = Mock()
        mock_websocket.headers.items.return_value = [
            ("origin", "https://app.netrasystems.ai"),
            ("user-agent", "Mozilla/5.0")
        ]
        
        origin = _extract_origin_from_websocket(mock_websocket)
        assert origin == "https://app.netrasystems.ai"

    def test_extract_origin_from_websocket_multiple_identical_headers(self):
        """
        Test origin extraction with multiple identical origin headers.
        
        Business Critical: Multiple identical headers should not cause issues.
        """
        mock_websocket = Mock()
        mock_websocket.headers.items.return_value = [
            ("origin", "https://app.netrasystems.ai"),
            ("origin", "https://app.netrasystems.ai"),  # Duplicate
            ("user-agent", "Mozilla/5.0")
        ]
        
        origin = _extract_origin_from_websocket(mock_websocket)
        assert origin == "https://app.netrasystems.ai"

    def test_extract_origin_from_websocket_multiple_different_headers(self):
        """
        Test origin extraction with multiple different origin headers.
        
        Business Critical: Multiple different origins indicate security issue.
        """
        mock_websocket = Mock()
        mock_websocket.headers.items.return_value = [
            ("origin", "https://app.netrasystems.ai"),
            ("origin", "https://evil.com"),  # Different!
            ("user-agent", "Mozilla/5.0")
        ]
        
        with patch('netra_backend.app.core.websocket_cors.get_unified_config') as mock_config:
            mock_config.return_value = type('Config', (), {'environment': 'production'})()
            
            # Production should reject multiple different origins
            origin = _extract_origin_from_websocket(mock_websocket)
            assert origin is None

    def test_extract_origin_from_websocket_case_insensitive(self):
        """
        Test origin extraction is case-insensitive for header names.
        
        Business Critical: HTTP headers are case-insensitive per RFC.
        """
        mock_websocket = Mock()
        mock_websocket.headers.items.return_value = [
            ("Origin", "https://app.netrasystems.ai"),  # Capital O
            ("USER-AGENT", "Mozilla/5.0")
        ]
        
        origin = _extract_origin_from_websocket(mock_websocket)
        assert origin == "https://app.netrasystems.ai"

    def test_validate_websocket_origin_success(self):
        """
        Test successful WebSocket origin validation.
        
        Business Critical: Valid origins must be accepted consistently.
        """
        mock_websocket = Mock()
        mock_websocket.headers.items.return_value = [
            ("origin", "https://app.netrasystems.ai")
        ]
        
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        result = validate_websocket_origin(mock_websocket, handler)
        assert result is True

    def test_validate_websocket_origin_failure(self):
        """
        Test failed WebSocket origin validation.
        
        Business Critical: Invalid origins must be rejected consistently.
        """
        mock_websocket = Mock()
        mock_websocket.headers.items.return_value = [
            ("origin", "https://evil.com")
        ]
        
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        result = validate_websocket_origin(mock_websocket, handler)
        assert result is False

    def test_get_environment_origins_fallback(self):
        """
        Test environment origins detection with fallback.
        
        Business Critical: Configuration failures should not prevent startup.
        """
        with patch('netra_backend.app.core.websocket_cors.get_unified_config') as mock_config:
            mock_config.side_effect = Exception("Config unavailable")
            
            with patch('netra_backend.app.core.websocket_cors.CORSConfigurationBuilder') as mock_cors:
                mock_builder = Mock()
                mock_builder.environment = "development"
                mock_cors.return_value = mock_builder
                
                # Should not raise exception
                result = get_environment_origins()
                
                # Should use fallback configuration
                mock_cors.assert_called()

    def test_get_websocket_cors_handler_caching(self):
        """
        Test that global CORS handler is cached appropriately.
        
        Business Critical: Handler caching improves performance.
        """
        # Clear any existing global handler
        import netra_backend.app.core.websocket_cors as cors_module
        cors_module._global_cors_handler = None
        
        with patch('netra_backend.app.core.websocket_cors.get_environment_origins_for_environment') as mock_get_origins:
            mock_get_origins.return_value = ["http://localhost:3000"]
            
            # First call should create handler
            handler1 = get_websocket_cors_handler("development")
            
            # Second call should return same handler
            handler2 = get_websocket_cors_handler("development")
            
            assert handler1 is handler2
            
            # Should only call get_origins once (caching)
            assert mock_get_origins.call_count == 1

    def test_get_websocket_cors_handler_environment_change(self):
        """
        Test that handler is recreated when environment changes.
        
        Business Critical: Environment changes must trigger new configuration.
        """
        # Clear any existing global handler
        import netra_backend.app.core.websocket_cors as cors_module
        cors_module._global_cors_handler = None
        
        with patch('netra_backend.app.core.websocket_cors.get_environment_origins_for_environment') as mock_get_origins:
            mock_get_origins.return_value = ["http://localhost:3000"]
            
            # Create handler for development
            handler1 = get_websocket_cors_handler("development")
            
            # Create handler for production (should be different)
            handler2 = get_websocket_cors_handler("production")
            
            assert handler1 is not handler2
            assert handler1.environment == "development"
            assert handler2.environment == "production"


class WebSocketCORSPerformanceTests(SSotBaseTestCase):
    """
    Performance tests for WebSocket CORS functionality.
    
    Ensures CORS validation is fast enough for high-volume WebSocket connections.
    """
    
    def test_origin_validation_performance(self):
        """
        Test that origin validation is fast enough for production load.
        
        Business Critical: Slow CORS validation affects connection establishment.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=[
                "https://app.netrasystems.ai",
                "https://staging.netrasystems.ai",
                "https://*.internal.netrasystems.ai"
            ],
            environment="production"
        )
        
        # Test many validation calls
        test_origins = [
            "https://app.netrasystems.ai",
            "https://staging.netrasystems.ai", 
            "https://api.internal.netrasystems.ai",
            "https://evil.com",
            "https://another-evil.com"
        ]
        
        start_time = time.time()
        
        # Perform many validations
        for _ in range(1000):
            for origin in test_origins:
                handler.is_origin_allowed(origin)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be very fast (< 1 second for 5000 validations)
        assert total_time < 1.0, f"CORS validation too slow: {total_time}s for 5000 validations"
        
        # Calculate average time per validation
        avg_time = total_time / 5000
        assert avg_time < 0.0002, f"Average validation time too slow: {avg_time}s"

    def test_security_statistics_performance(self):
        """
        Test that security statistics collection doesn't impact performance.
        
        Business Critical: Security monitoring should not slow down connections.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Generate many violations
        for i in range(100):
            handler.is_origin_allowed(f"https://evil{i}.com")
        
        start_time = time.time()
        
        # Get statistics many times
        for _ in range(100):
            stats = handler.get_security_stats()
            assert "violation_counts" in stats
        
        end_time = time.time()
        stats_time = end_time - start_time
        
        # Should be very fast
        assert stats_time < 0.1, f"Statistics collection too slow: {stats_time}s"

    def test_memory_usage_with_many_violations(self):
        """
        Test memory usage remains reasonable with many security violations.
        
        Business Critical: Memory leaks could crash the system under attack.
        """
        handler = WebSocketCORSHandler(
            allowed_origins=["https://app.netrasystems.ai"],
            environment="production"
        )
        
        # Generate violations from many different origins
        for i in range(1000):
            handler.is_origin_allowed(f"https://attack{i}.com")
        
        # Check violation tracking size
        violation_count = len(handler._violation_counts)
        blocked_count = len(handler._blocked_origins)
        
        # Should track violations but not grow unbounded
        assert violation_count <= 1000, f"Too many tracked violations: {violation_count}"
        
        # Some origins should be blocked after multiple violations
        assert blocked_count > 0, "No origins were blocked despite violations"
        
        # But not all should be blocked (rate limiting threshold)
        assert blocked_count < violation_count, "All violating origins were blocked immediately"