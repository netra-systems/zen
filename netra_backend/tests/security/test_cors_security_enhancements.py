"""
CORS Security Enhancements Test Suite

Tests for critical security headers and logging for CORS.
Business Value: Prevents security vulnerabilities that could lead to data breaches.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request
from starlette.responses import Response

from shared.cors_config import (
    validate_content_type,
    is_service_to_service_request,
    log_cors_security_event,
    is_origin_allowed,
    get_fastapi_cors_config
)
from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware


class TestContentTypeValidation:
    """Test CORS-012: Content-Type validation for security."""
    
    def test_valid_content_types(self):
        """Test that standard content types are allowed."""
        valid_types = [
            'application/json',
            'application/x-www-form-urlencoded',
            'text/plain',
            'text/html',
            'multipart/form-data',
            'application/json; charset=utf-8',
            'text/plain; charset=utf-8'
        ]
        
        for content_type in valid_types:
            assert validate_content_type(content_type), f"Should allow {content_type}"
    
    def test_suspicious_content_types(self):
        """Test that suspicious content types are rejected."""
        suspicious_types = [
            'application/x-msdownload',
            'application/vnd.ms-excel',
            'text/vbscript',
            'text/jscript',
            'application/x-ms-application',
            'text/x-unknown'
        ]
        
        for content_type in suspicious_types:
            assert not validate_content_type(content_type), f"Should reject {content_type}"
    
    def test_empty_content_type(self):
        """Test that empty/None content type is allowed."""
        assert validate_content_type(None)
        assert validate_content_type("")
        assert validate_content_type("   ")


class TestServiceToServiceDetection:
    """Test CORS-013: Service-to-service bypass configuration."""
    
    def test_service_header_detection(self):
        """Test detection via X-Service-Name header."""
        headers = {'x-service-name': 'auth-service'}
        assert is_service_to_service_request(headers)
        
        headers = {'x-service-name': 'backend-service'}
        assert is_service_to_service_request(headers)
        
        headers = {'x-service-name': 'unknown-service'}
        assert not is_service_to_service_request(headers)
    
    def test_user_agent_detection(self):
        """Test detection via internal user agents."""
        internal_agents = [
            'httpx/0.24.1',
            'aiohttp/3.8.1',
            'requests/2.28.1',
            'python-urllib3/1.26.12'
        ]
        
        for agent in internal_agents:
            headers = {'user-agent': agent}
            assert is_service_to_service_request(headers), f"Should detect {agent}"
    
    def test_external_user_agent(self):
        """Test that external user agents are not detected as service-to-service."""
        external_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'curl/7.68.0',
            'PostmanRuntime/7.29.0'
        ]
        
        for agent in external_agents:
            headers = {'user-agent': agent}
            assert not is_service_to_service_request(headers), f"Should not detect {agent}"


class TestOriginAllowedEnhanced:
    """Test enhanced origin validation with service-to-service bypass."""
    
    def test_service_to_service_bypass(self):
        """Test that service-to-service requests bypass CORS validation."""
        # Even invalid origins should be allowed for service-to-service
        result = is_origin_allowed(
            origin="http://invalid-origin.com",
            allowed_origins=["http://localhost:3000"],
            environment="development",
            service_to_service=True
        )
        assert result, "Service-to-service requests should bypass CORS validation"
    
    def test_normal_validation_still_works(self):
        """Test that normal CORS validation still works when not service-to-service."""
        allowed_origins = ["http://localhost:3000", "https://app.netrasystems.ai"]
        
        # Valid origin should be allowed
        assert is_origin_allowed(
            origin="http://localhost:3000",
            allowed_origins=allowed_origins,
            environment="development",
            service_to_service=False
        )
        
        # Invalid origin should be rejected
        assert not is_origin_allowed(
            origin="http://malicious-site.com",
            allowed_origins=allowed_origins,
            environment="production",
            service_to_service=False
        )


class TestCORSSecurityLogging:
    """Test SEC-002: CORS security logging functionality."""
    
    @patch('logging.getLogger')
    def test_security_event_logging(self, mock_get_logger):
        """Test that security events are logged properly."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_cors_security_event(
            event_type="cors_validation_failure",
            origin="http://malicious-site.com",
            path="/api/sensitive",
            environment="production",
            request_id="req-123",
            additional_info={"reason": "invalid_origin"}
        )
        
        # Check that warning was called twice (JSON and human-readable)
        assert mock_logger.warning.call_count == 2
        
        # Check JSON logging
        json_call = mock_logger.warning.call_args_list[0][0][0]
        assert "CORS_SECURITY_EVENT:" in json_call
        
        # Parse the JSON part
        json_part = json_call.split("CORS_SECURITY_EVENT: ")[1]
        event_data = json.loads(json_part)
        
        assert event_data["event_type"] == "cors_validation_failure"
        assert event_data["origin"] == "http://malicious-site.com"
        assert event_data["path"] == "/api/sensitive"
        assert event_data["environment"] == "production"
        assert event_data["request_id"] == "req-123"
        assert event_data["reason"] == "invalid_origin"
        
        # Check human-readable logging
        human_call = mock_logger.warning.call_args_list[1][0][0]
        assert "CORS Security Event: cors_validation_failure" in human_call
        assert "http://malicious-site.com" in human_call
        assert "/api/sensitive" in human_call


class TestCORSHeaders:
    """Test CORS-005 and CORS-006: Security headers."""
    
    def test_cors_config_includes_security_headers(self):
        """Test that CORS config includes required security headers."""
        config = get_fastapi_cors_config("development")
        
        # CORS-006: Max-Age should be set
        assert config["max_age"] == 3600
        
        # CORS-005: Vary should be in expose_headers
        assert "Vary" in config["expose_headers"]
        
        # CORS-013: X-Service-Name should be in allow_headers
        assert "X-Service-Name" in config["allow_headers"]
    
    @patch('netra_backend.app.middleware.cors_fix_middleware.log_cors_security_event')
    async def test_cors_middleware_adds_vary_header(self, mock_log_event):
        """Test that CORS middleware adds Vary: Origin header."""
        middleware = CORSFixMiddleware(app=None, environment="development")
        
        # Mock request with origin
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "origin": "http://localhost:3000",
            "content-type": "application/json"
        }
        mock_request.url.path = "/api/test"
        
        # Mock response with CORS headers
        mock_response = MagicMock(spec=Response)
        mock_response.headers = {
            "access-control-allow-credentials": "true"
        }
        # Add status_code attribute for middleware compatibility
        mock_response.status_code = 200
        
        # Mock call_next to return the response
        async def mock_call_next(request):
            return mock_response
        
        # Process the request
        result = await middleware.dispatch(mock_request, mock_call_next)
        
        # Check that Vary: Origin header was added
        assert result.headers["Vary"] == "Origin"
    
    @patch('netra_backend.app.middleware.cors_fix_middleware.log_cors_security_event')
    async def test_cors_middleware_logs_suspicious_content_type(self, mock_log_event):
        """Test that suspicious content types are logged."""
        middleware = CORSFixMiddleware(app=None, environment="production")
        
        # Mock request with suspicious content type
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "origin": "http://localhost:3000",
            "content-type": "application/x-msdownload",
            "x-request-id": "req-456"
        }
        mock_request.url.path = "/api/upload"
        
        # Mock response
        mock_response = MagicMock(spec=Response)
        mock_response.headers = {}
        # Add status_code attribute for middleware compatibility
        mock_response.status_code = 200
        
        async def mock_call_next(request):
            return mock_response
        
        # Process the request
        await middleware.dispatch(mock_request, mock_call_next)
        
        # Check that security event was logged
        mock_log_event.assert_called_once()
        call_args = mock_log_event.call_args
        assert call_args[1]["event_type"] == "suspicious_content_type"
        assert call_args[1]["additional_info"]["content_type"] == "application/x-msdownload"


class TestSecurityIntegration:
    """Integration tests for CORS security enhancements."""
    
    def test_all_security_features_configured(self):
        """Test that all security features are properly configured."""
        config = get_fastapi_cors_config("staging")
        
        # Verify all required headers are present
        required_allow_headers = [
            "Authorization", "Content-Type", "X-Request-ID", 
            "X-Trace-ID", "X-Service-Name"
        ]
        for header in required_allow_headers:
            assert header in config["allow_headers"], f"Missing allow header: {header}"
        
        required_expose_headers = [
            "X-Trace-ID", "X-Request-ID", "Vary"
        ]
        for header in required_expose_headers:
            assert header in config["expose_headers"], f"Missing expose header: {header}"
        
        # Verify security settings
        assert config["allow_credentials"] is True
        assert config["max_age"] == 3600
        assert isinstance(config["allow_origins"], list)
        assert len(config["allow_origins"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])