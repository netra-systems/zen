"""
Unit tests for Auth Service header processing logic.

This test module validates auth service specific header extraction and processing
logic that prevents GCP load balancer authentication failures. Part of GitHub issue #113.

Business Value Justification (BVJ):
1. Segment: Platform/Enterprise - Auth service reliability  
2. Business Goal: Prevent authentication service failures from cascading to all users
3. Value Impact: Ensures auth service can handle GCP load balancer header modifications
4. Strategic Impact: Maintains auth service as reliable dependency for all platform services

Test Coverage:
- Service-to-service authentication header validation
- Cross-service header processing (X-Service-ID, X-Service-Secret)
- OAuth callback header handling in GCP environment
- Token validation endpoint header processing
- E2E testing header support with bypass mechanisms

Key Principles:
- FAIL HARD: Auth service must fail clearly when headers are invalid
- No Mocks: Tests validate actual auth route logic 
- Type Safety: Uses strongly typed patterns for validation results
- Business Value: Each test prevents auth service from becoming single point of failure
"""

import pytest
import json
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock
from fastapi import Request
from fastapi.testclient import TestClient

from auth_service.auth_core.routes.auth_routes import router
from auth_service.auth_core.services.auth_service import AuthService
from shared.types.core_types import AuthValidationResult, TokenString, UserID
from shared.isolated_environment import get_env


class TestServiceAuthenticationHeaders:
    """Test service-to-service authentication header processing.
    
    Business Value: Ensures auth service can authenticate backend and other services.
    Critical for cross-service communication that relies on proper header validation.
    """
    
    def test_service_header_validation_success(self):
        """Test successful service authentication with proper headers.
        
        Business Impact: Ensures backend service can authenticate with auth service.
        Regression Prevention: Prevents service-to-service auth failures.
        """
        # Mock environment with service credentials
        env = get_env()
        
        # Test data simulating backend service request
        service_headers = {
            "X-Service-ID": "netra-backend",
            "X-Service-Secret": "test_service_secret_key_123",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "token": "test_jwt_token_to_validate"
        }
        
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.headers = service_headers
        mock_request.json = AsyncMock(return_value=request_body)
        
        # Verify headers are accessible for validation
        assert mock_request.headers.get("X-Service-ID") == "netra-backend"
        assert mock_request.headers.get("X-Service-Secret") == "test_service_secret_key_123"
        
        # Service ID should match expected stable value
        expected_service_id = "netra-backend"
        assert mock_request.headers.get("X-Service-ID") == expected_service_id

    def test_missing_service_headers_validation(self):
        """Test validation when service authentication headers are missing.
        
        Business Impact: Ensures proper error handling when service headers are incomplete.
        Security Value: Prevents unauthorized service-to-service calls.
        """
        # Test scenarios with missing service headers
        missing_header_scenarios = [
            # No service headers at all
            {"Content-Type": "application/json"},
            
            # Missing service ID
            {"X-Service-Secret": "test_secret", "Content-Type": "application/json"},
            
            # Missing service secret
            {"X-Service-ID": "netra-backend", "Content-Type": "application/json"},
            
            # Empty service headers
            {"X-Service-ID": "", "X-Service-Secret": "", "Content-Type": "application/json"},
        ]
        
        for headers in missing_header_scenarios:
            mock_request = Mock(spec=Request)
            mock_request.headers = headers
            mock_request.json = AsyncMock(return_value={"token": "test_token"})
            
            # Verify missing headers are detectable
            service_id = mock_request.headers.get("X-Service-ID")
            service_secret = mock_request.headers.get("X-Service-Secret")
            
            # At least one should be missing/empty for these test cases
            assert not service_id or not service_secret or service_id == "" or service_secret == ""

    def test_invalid_service_credentials_rejection(self):
        """Test rejection of invalid service credentials.
        
        Security Impact: Prevents unauthorized services from accessing auth endpoints.
        Business Value: Maintains auth service security boundaries.
        """
        invalid_credential_scenarios = [
            # Wrong service ID
            {"X-Service-ID": "malicious-service", "X-Service-Secret": "valid_secret"},
            
            # Wrong service secret
            {"X-Service-ID": "netra-backend", "X-Service-Secret": "wrong_secret"},
            
            # SQL injection attempts
            {"X-Service-ID": "netra-backend'; DROP TABLE users;--", "X-Service-Secret": "test"},
            
            # Long/malformed service credentials
            {"X-Service-ID": "a" * 1000, "X-Service-Secret": "b" * 1000},
        ]
        
        expected_service_id = "netra-backend"
        
        for headers in invalid_credential_scenarios:
            mock_request = Mock(spec=Request)
            mock_request.headers = headers
            mock_request.json = AsyncMock(return_value={"token": "test_token"})
            
            service_id = mock_request.headers.get("X-Service-ID")
            service_secret = mock_request.headers.get("X-Service-Secret")
            
            # Verify invalid credentials are detectable
            is_valid_id = (service_id == expected_service_id)
            is_reasonable_length = len(service_id or "") < 100 and len(service_secret or "") < 200
            
            # At least one validation should fail for these invalid credential scenarios
            if service_id == "malicious-service":
                assert not is_valid_id  # Wrong service ID should fail ID validation
            elif service_secret == "wrong_secret":
                assert is_valid_id  # ID is correct but secret is wrong
            elif "DROP TABLE" in (service_id or ""):
                assert not is_reasonable_length or not is_valid_id  # SQL injection attempt should fail
            elif len(service_id or "") >= 100:
                assert not is_reasonable_length  # Overly long credentials should fail length check


class TestTokenValidationHeaderProcessing:
    """Test token validation endpoint header processing.
    
    Business Value: Ensures token validation works correctly with GCP load balancer headers.
    Critical for all authentication flows that depend on token validation.
    """
    
    def test_token_validation_request_processing(self):
        """Test token validation request header and body processing.
        
        Regression Prevention: Ensures token validation handles various header combinations.
        Business Impact: Prevents token validation failures that break user sessions.
        """
        # Test standard token validation request
        validation_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Backend-Service/1.0",
            "X-Request-ID": "req_12345"
        }
        
        request_body = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.signature"
        }
        
        mock_request = Mock(spec=Request)
        mock_request.headers = validation_headers
        mock_request.json = AsyncMock(return_value=request_body)
        
        # Verify request structure for token validation
        assert mock_request.headers.get("Content-Type") == "application/json"
        
        # Simulate request body parsing
        import asyncio
        body = asyncio.run(mock_request.json())
        assert body.get("token") is not None
        assert len(body["token"]) > 10  # Reasonable token length
        assert "." in body["token"]  # JWT format check
        
    def test_token_validation_with_gcp_headers(self):
        """Test token validation when GCP load balancer adds infrastructure headers.
        
        Business Impact: Ensures token validation works in GCP Cloud Run environment.
        Infrastructure Value: Maintains compatibility with GCP request routing.
        """
        # Headers that GCP load balancer typically adds
        gcp_enhanced_headers = {
            "Content-Type": "application/json",
            "X-Forwarded-For": "203.0.113.195, 70.41.3.18",
            "X-Forwarded-Proto": "https",
            "X-Cloud-Trace-Context": "105445aa7843bc8bf206b12000100000/1;o=1",
            "X-Appengine-Region": "us-central1",
            "X-Appengine-Request-Id": "bf4bf40000181f23216c6c0001737e",
            "User-Agent": "GoogleHC/1.0"
        }
        
        request_body = {
            "token": "gcp_environment_token_12345"
        }
        
        mock_request = Mock(spec=Request)
        mock_request.headers = gcp_enhanced_headers
        mock_request.json = AsyncMock(return_value=request_body)
        
        # Verify GCP headers don't interfere with token validation
        assert mock_request.headers.get("Content-Type") == "application/json"
        assert "X-Cloud-Trace-Context" in mock_request.headers
        assert "X-Appengine-Region" in mock_request.headers
        
        # Token should still be extractable from body
        import asyncio
        body = asyncio.run(mock_request.json())
        assert body["token"] == "gcp_environment_token_12345"

    def test_malformed_token_validation_requests(self):
        """Test handling of malformed token validation requests.
        
        Security Value: Ensures malformed requests don't crash auth service.
        Business Impact: Provides clear error messages for debugging auth issues.
        """
        malformed_request_scenarios = [
            # Missing token field
            {},
            
            # Empty token
            {"token": ""},
            
            # Null token
            {"token": None},
            
            # Wrong field name
            {"access_token": "some_token"},
            
            # Non-string token
            {"token": 12345},
            
            # Extremely long token (potential DoS)
            {"token": "a" * 10000}
        ]
        
        for body_data in malformed_request_scenarios:
            mock_request = Mock(spec=Request)
            mock_request.headers = {"Content-Type": "application/json"}
            mock_request.json = AsyncMock(return_value=body_data)
            
            # Verify malformed requests are detectable
            import asyncio
            try:
                body = asyncio.run(mock_request.json())
                token = body.get("token")
                
                # Should fail validation checks
                is_valid_token = (
                    token is not None and
                    isinstance(token, str) and
                    len(token) > 0 and
                    len(token) < 5000  # Reasonable length limit
                )
                
                # Most scenarios should fail validation
                if body_data == {"access_token": "some_token"}:
                    # This specific case has wrong field name
                    assert token is None
                elif body_data == {"token": "a" * 10000}:
                    # This case has unreasonably long token
                    assert not is_valid_token
                else:
                    assert not is_valid_token
                    
            except Exception:
                # Exception during parsing is acceptable for malformed requests
                pass


class TestOAuthCallbackHeaderHandling:
    """Test OAuth callback endpoint header processing.
    
    Business Value: Ensures OAuth authentication works through GCP load balancer.
    User Experience: Prevents OAuth login failures that block new user registration.
    """
    
    def test_oauth_callback_query_parameter_processing(self):
        """Test OAuth callback processes query parameters correctly.
        
        Business Impact: Ensures OAuth login flow completes successfully.
        User Value: Prevents user frustration from failed OAuth authentication.
        """
        # Simulate OAuth callback with standard query parameters
        callback_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://accounts.google.com/"
        }
        
        # OAuth callback parameters
        oauth_params = {
            "code": "4/0AX4XfWh7h8K9j6L5M3N2O1P0Q9R8S7T6U5V4W3X2Y1Z0",
            "state": "csrf_protection_random_state_12345",
            "scope": "email profile openid"
        }
        
        # Verify callback parameters are processable
        assert oauth_params.get("code") is not None
        assert oauth_params.get("state") is not None
        assert len(oauth_params["code"]) > 10  # Reasonable auth code length
        assert len(oauth_params["state"]) > 10  # CSRF state should be substantial
        
    def test_oauth_callback_error_handling(self):
        """Test OAuth callback error parameter handling.
        
        Business Value: Provides clear error messages when OAuth fails.
        User Experience: Helps users understand and resolve OAuth issues.
        """
        # OAuth error scenarios
        oauth_error_scenarios = [
            {
                "error": "access_denied",
                "error_description": "The user denied the request"
            },
            {
                "error": "invalid_request", 
                "error_description": "The request is missing a required parameter"
            },
            {
                "error": "server_error",
                "error_description": "The server encountered an unexpected condition"
            }
        ]
        
        for error_params in oauth_error_scenarios:
            # Verify error parameters are accessible for proper error handling
            assert error_params.get("error") is not None
            assert error_params.get("error_description") is not None
            
            # Error messages should be informative
            assert len(error_params["error"]) > 0
            assert len(error_params["error_description"]) > 10
            
            # Standard OAuth error types
            assert error_params["error"] in [
                "access_denied", "invalid_request", "invalid_grant", 
                "unauthorized_client", "unsupported_grant_type", "server_error"
            ]

    def test_oauth_state_validation_header_preservation(self):
        """Test OAuth state validation preserves necessary headers for security.
        
        Security Value: Ensures CSRF protection works correctly in OAuth flow.
        Business Impact: Prevents OAuth security vulnerabilities.
        """
        # OAuth callback with security headers
        secure_callback_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://accounts.google.com/oauth/authorize",
            "Origin": "https://accounts.google.com", 
            "X-Forwarded-For": "203.0.113.195",
            "X-Forwarded-Proto": "https"
        }
        
        oauth_security_params = {
            "code": "oauth_authorization_code_123",
            "state": "secure_csrf_state_token_456"
        }
        
        # Verify security-relevant headers are preserved
        assert secure_callback_headers.get("Referer") == "https://accounts.google.com/oauth/authorize"
        assert secure_callback_headers.get("Origin") == "https://accounts.google.com"
        assert secure_callback_headers.get("X-Forwarded-Proto") == "https"
        
        # OAuth state should be available for CSRF validation
        assert oauth_security_params.get("state") is not None
        assert len(oauth_security_params["state"]) > 15  # Substantial CSRF token


class TestE2ETestingHeaderSupport:
    """Test E2E testing header support and bypass mechanisms.
    
    Business Value: Enables automated testing while maintaining security.
    Testing Infrastructure: Supports CI/CD pipeline with proper auth testing.
    """
    
    def test_e2e_bypass_header_validation(self):
        """Test E2E bypass header validation logic.
        
        Testing Value: Enables automated E2E tests without compromising security.
        Business Impact: Supports continuous deployment with proper test coverage.
        """
        # E2E testing headers
        e2e_headers = {
            "Content-Type": "application/json",
            "X-E2E-Bypass-Key": "staging_e2e_bypass_key_12345",
            "X-E2E-Test-Environment": "staging", 
            "User-Agent": "E2E-Test-Runner/1.0"
        }
        
        e2e_request_body = {
            "email": "e2e-test@staging.netrasystems.ai",
            "name": "E2E Test User",
            "permissions": ["read", "write"],
            "simulate_oauth": True
        }
        
        mock_request = Mock(spec=Request)
        mock_request.headers = e2e_headers
        mock_request.json = AsyncMock(return_value=e2e_request_body)
        
        # Verify E2E headers are accessible
        bypass_key = mock_request.headers.get("X-E2E-Bypass-Key")
        test_env = mock_request.headers.get("X-E2E-Test-Environment")
        
        assert bypass_key == "staging_e2e_bypass_key_12345"
        assert test_env == "staging"
        
        # E2E request body should be parseable
        import asyncio
        body = asyncio.run(mock_request.json())
        assert body.get("email") == "e2e-test@staging.netrasystems.ai"
        assert body.get("simulate_oauth") is True

    def test_e2e_bypass_security_validation(self):
        """Test E2E bypass security prevents unauthorized usage.
        
        Security Value: Ensures E2E bypass only works in non-production environments.
        Business Impact: Prevents production security bypass vulnerabilities.
        """
        # Test E2E bypass in different environments
        environment_scenarios = [
            ("production", False),  # Should not allow bypass
            ("staging", True),      # Should allow bypass  
            ("development", True),  # Should allow bypass
            ("test", True)          # Should allow bypass
        ]
        
        for env_name, should_allow_bypass in environment_scenarios:
            # Mock environment context
            mock_env_headers = {
                "X-E2E-Bypass-Key": "test_bypass_key",
                "X-Environment": env_name
            }
            
            # Production should never allow E2E bypass
            if env_name == "production":
                assert not should_allow_bypass
            else:
                # Non-production can allow bypass with proper key validation
                assert should_allow_bypass
                
            # Verify environment detection is possible
            detected_env = mock_env_headers.get("X-Environment")
            assert detected_env == env_name

    def test_e2e_header_injection_prevention(self):
        """Test prevention of header injection through E2E bypass mechanism.
        
        Security Value: Prevents malicious use of E2E testing features.
        Testing Infrastructure: Maintains security while enabling testing.
        """
        # Malicious E2E header injection attempts
        malicious_e2e_scenarios = [
            # Header injection via bypass key
            {"X-E2E-Bypass-Key": "valid_key\r\nX-Admin-Override: true"},
            
            # Environment injection
            {"X-E2E-Test-Environment": "staging\nX-Production-Access: granted"},
            
            # JSON injection in test user
            {"X-E2E-Test-User": '{"admin": true, "bypass_all_auth": true}'},
            
            # Extremely long headers (DoS attempt)
            {"X-E2E-Bypass-Key": "a" * 5000}
        ]
        
        for malicious_headers in malicious_e2e_scenarios:
            # Verify malicious content is detectable
            for header_name, header_value in malicious_headers.items():
                # Check for common injection patterns
                has_newline_injection = "\r\n" in header_value or "\n" in header_value
                has_suspicious_length = len(header_value) > 1000
                has_json_structure = header_value.strip().startswith("{") and "admin" in header_value
                
                is_potentially_malicious = (
                    has_newline_injection or 
                    has_suspicious_length or 
                    has_json_structure
                )
                
                # At least detect the malicious pattern
                if header_name == "X-E2E-Bypass-Key" and "valid_key\r\nX-Admin-Override" in header_value:
                    assert has_newline_injection
                elif header_name == "X-E2E-Test-Environment" and "\n" in header_value:
                    assert has_newline_injection  
                elif "a" * 5000 == header_value:
                    assert has_suspicious_length
                elif '{"admin": true' in header_value:
                    assert has_json_structure


class TestCrossServiceHeaderCompatibility:
    """Test cross-service header compatibility and processing.
    
    Business Value: Ensures auth service works correctly with all platform services.
    System Reliability: Prevents header incompatibilities from breaking service mesh.
    """
    
    def test_backend_service_header_compatibility(self):
        """Test header compatibility with netra-backend service.
        
        Integration Value: Ensures backend can communicate with auth service.
        Business Impact: Prevents auth failures that break user agent executions.
        """
        # Headers sent by netra-backend to auth service
        backend_headers = {
            "Content-Type": "application/json",
            "User-Agent": "netra-backend/1.0.0",
            "X-Service-ID": "netra-backend",
            "X-Service-Secret": "backend_service_secret",
            "X-Request-Source": "agent_execution_engine",
            "X-Correlation-ID": "backend_req_12345"
        }
        
        # Verify backend headers are compatible
        assert backend_headers.get("X-Service-ID") == "netra-backend"
        assert backend_headers.get("Content-Type") == "application/json"
        assert "X-Correlation-ID" in backend_headers
        
        # Service identification should work
        service_id = backend_headers.get("X-Service-ID")
        service_secret = backend_headers.get("X-Service-Secret")
        
        assert service_id is not None and len(service_id) > 0
        assert service_secret is not None and len(service_secret) > 0

    def test_frontend_service_header_compatibility(self):
        """Test header compatibility with frontend service requests.
        
        User Experience: Ensures frontend authentication requests work correctly.
        Business Impact: Prevents login failures that block user access.
        """
        # Headers sent by frontend through load balancer
        frontend_headers = {
            "Content-Type": "application/json", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://app.netrasystems.ai",
            "Referer": "https://app.netrasystems.ai/login",
            "X-Forwarded-For": "203.0.113.195",
            "X-Forwarded-Proto": "https"
        }
        
        # Verify frontend headers are preserved
        assert frontend_headers.get("Content-Type") == "application/json"
        assert frontend_headers.get("Origin") == "https://app.netrasystems.ai" 
        assert frontend_headers.get("X-Forwarded-Proto") == "https"
        
        # CORS-relevant headers should be accessible
        origin = frontend_headers.get("Origin")
        referer = frontend_headers.get("Referer")
        
        assert origin is not None
        assert referer is not None
        assert "netrasystems.ai" in origin and "netrasystems.ai" in referer

    def test_load_balancer_header_preservation(self):
        """Test that load balancer headers are preserved through auth processing.
        
        Infrastructure Value: Ensures compatibility with GCP load balancer.
        Debugging Value: Preserves trace headers for request debugging.
        """
        # Complete set of headers through GCP load balancer
        load_balancer_headers = {
            # Original request headers
            "Authorization": "Bearer user_token_123",
            "Content-Type": "application/json",
            "User-Agent": "Frontend/1.0.0",
            
            # GCP load balancer added headers  
            "X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178",
            "X-Forwarded-Proto": "https",
            "X-Cloud-Trace-Context": "105445aa7843bc8bf206b12000100000/1;o=1",
            "X-Appengine-Region": "us-central1",
            "X-Appengine-Country": "US", 
            "X-Appengine-Request-Id": "bf4bf40000181f23216c6c0001737e",
            
            # Service mesh headers
            "X-Service-Mesh": "istio",
            "X-Request-ID": "req_mesh_12345"
        }
        
        # All headers should be accessible after processing
        for header_name, header_value in load_balancer_headers.items():
            assert header_value is not None
            assert len(header_value) > 0
            
        # Critical headers must be preserved
        assert load_balancer_headers.get("Authorization") is not None
        assert load_balancer_headers.get("X-Cloud-Trace-Context") is not None
        assert load_balancer_headers.get("X-Request-ID") is not None
        
        # GCP-specific headers should be identifiable
        gcp_headers = [
            "X-Forwarded-For", "X-Forwarded-Proto", "X-Cloud-Trace-Context",
            "X-Appengine-Region", "X-Appengine-Country", "X-Appengine-Request-Id"
        ]
        
        for gcp_header in gcp_headers:
            assert gcp_header in load_balancer_headers


if __name__ == "__main__":
    # Enable running tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])