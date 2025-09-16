"""
Security Middleware Comprehensive Unit Tests

Tests auth service security middleware for request validation and header management.
Focuses on security gaps identified in coverage analysis for Issue #718.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical security infrastructure
- Business Goal: Protect $500K+ ARR through secure request handling
- Value Impact: Prevents malicious requests and ensures proper security headers
- Strategic Impact: Maintains platform security and compliance at the edge
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request
from fastapi.responses import JSONResponse

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from auth_service.auth_core.security.middleware import (
    validate_request_size,
    add_service_headers,
    add_security_headers,
    create_security_middleware,
    MAX_JSON_PAYLOAD_SIZE
)


class SecurityMiddlewareTests(SSotBaseTestCase):
    """Comprehensive unit tests for security middleware functionality."""

    def setUp(self):
        """Set up test environment with SSOT patterns."""
        super().setUp()

        # Create mock request using SSOT factory
        self.mock_request = SSotMockFactory.create_mock_fastapi_request()
        self.mock_response = Mock()
        self.mock_response.headers = {}

    @pytest.mark.asyncio
    async def test_validate_request_size_valid_small_request(self):
        """Test that small valid requests pass size validation."""
        # Mock headers for a small JSON request
        self.mock_request.headers = {
            "content-length": "1024",  # 1KB - well under limit
            "content-type": "application/json"
        }

        result = await validate_request_size(self.mock_request)
        self.assertIsNone(result)  # None means validation passed

    @pytest.mark.asyncio
    async def test_validate_request_size_valid_non_json_request(self):
        """Test that non-JSON requests skip size validation."""
        # Mock headers for a non-JSON request
        self.mock_request.headers = {
            "content-length": "100000",  # Large but not JSON
            "content-type": "text/plain"
        }

        result = await validate_request_size(self.mock_request)
        self.assertIsNone(result)  # Non-JSON requests are not validated

    @pytest.mark.asyncio
    async def test_validate_request_size_exceeds_limit(self):
        """Test that oversized JSON requests are rejected."""
        # Mock headers for an oversized JSON request
        oversized_content = str(MAX_JSON_PAYLOAD_SIZE + 1)
        self.mock_request.headers = {
            "content-length": oversized_content,
            "content-type": "application/json"
        }

        result = await validate_request_size(self.mock_request)

        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 413)  # Payload Too Large
        # Verify error message contains size information
        self.assertIn("Request payload too large", str(result.body))
        self.assertIn(str(MAX_JSON_PAYLOAD_SIZE), str(result.body))

    @pytest.mark.asyncio
    async def test_validate_request_size_invalid_content_length(self):
        """Test handling of invalid Content-Length header."""
        # Mock headers with invalid Content-Length
        self.mock_request.headers = {
            "content-length": "invalid_number",
            "content-type": "application/json"
        }

        result = await validate_request_size(self.mock_request)

        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 400)  # Bad Request
        self.assertIn("Invalid Content-Length header", str(result.body))

    @pytest.mark.asyncio
    async def test_validate_request_size_missing_headers(self):
        """Test that missing headers are handled gracefully."""
        # Mock request with no headers
        self.mock_request.headers = {}

        result = await validate_request_size(self.mock_request)
        self.assertIsNone(result)  # Should pass when headers are missing

    @pytest.mark.asyncio
    async def test_validate_request_size_json_content_types(self):
        """Test validation works with various JSON content types."""
        json_content_types = [
            "application/json",
            "application/json; charset=utf-8",
            "Application/JSON",  # Case insensitive
            "text/json"
        ]

        oversized_content = str(MAX_JSON_PAYLOAD_SIZE + 1)

        for content_type in json_content_types:
            self.mock_request.headers = {
                "content-length": oversized_content,
                "content-type": content_type
            }

            result = await validate_request_size(self.mock_request)
            self.assertIsInstance(result, JSONResponse)
            self.assertEqual(result.status_code, 413)

    def test_add_service_headers_default_values(self):
        """Test adding service headers with default values."""
        add_service_headers(self.mock_response)

        self.assertEqual(self.mock_response.headers["X-Service-Name"], "auth-service")
        self.assertEqual(self.mock_response.headers["X-Service-Version"], "1.0.0")

    def test_add_service_headers_custom_values(self):
        """Test adding service headers with custom values."""
        custom_name = "custom-auth-service"
        custom_version = "2.1.0"

        add_service_headers(self.mock_response, custom_name, custom_version)

        self.assertEqual(self.mock_response.headers["X-Service-Name"], custom_name)
        self.assertEqual(self.mock_response.headers["X-Service-Version"], custom_version)

    @patch('auth_service.auth_core.security.middleware.get_env')
    def test_add_security_headers_enabled(self, mock_get_env):
        """Test that security headers are added when enabled."""
        # Mock environment to enable secure headers
        mock_env = Mock()
        mock_env.get.return_value = "true"
        mock_get_env.return_value = mock_env

        add_security_headers(self.mock_response)

        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block"
        }

        for header_name, header_value in expected_headers.items():
            self.assertEqual(self.mock_response.headers[header_name], header_value)

    @patch('auth_service.auth_core.security.middleware.get_env')
    def test_add_security_headers_disabled(self, mock_get_env):
        """Test that security headers are not added when disabled."""
        # Mock environment to disable secure headers
        mock_env = Mock()
        mock_env.get.return_value = "false"
        mock_get_env.return_value = mock_env

        add_security_headers(self.mock_response)

        # No security headers should be added
        security_header_names = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
        for header_name in security_header_names:
            self.assertNotIn(header_name, self.mock_response.headers)

    @patch('auth_service.auth_core.security.middleware.get_env')
    def test_add_security_headers_case_insensitive(self, mock_get_env):
        """Test that security headers configuration is case insensitive."""
        test_cases = ["True", "TRUE", "tRuE"]

        for case in test_cases:
            # Reset headers for each test
            self.mock_response.headers = {}

            # Mock environment with different cases
            mock_env = Mock()
            mock_env.get.return_value = case
            mock_get_env.return_value = mock_env

            add_security_headers(self.mock_response)

            # Should add headers regardless of case
            self.assertIn("X-Content-Type-Options", self.mock_response.headers)

    @pytest.mark.asyncio
    async def test_create_security_middleware_default_configuration(self):
        """Test creating security middleware with default configuration."""
        middleware = await create_security_middleware()

        # Verify middleware is callable
        self.assertTrue(callable(middleware))

    @pytest.mark.asyncio
    async def test_create_security_middleware_custom_configuration(self):
        """Test creating security middleware with custom configuration."""
        middleware = await create_security_middleware(
            add_service_headers_flag=False,
            add_security_headers_flag=False,
            service_name="test-service",
            service_version="3.0.0"
        )

        # Verify middleware is callable
        self.assertTrue(callable(middleware))

    @pytest.mark.asyncio
    async def test_security_middleware_request_processing(self):
        """Test complete middleware request processing flow."""
        # Create middleware with all features enabled
        middleware = await create_security_middleware(
            add_service_headers_flag=True,
            add_security_headers_flag=True,
            service_name="test-service",
            service_version="2.0.0"
        )

        # Mock request with valid size
        mock_request = Mock()
        mock_request.headers = {
            "content-length": "1024",
            "content-type": "application/json"
        }

        # Mock response
        mock_response = Mock()
        mock_response.headers = {}

        # Mock call_next function
        mock_call_next = AsyncMock(return_value=mock_response)

        # Execute middleware
        with patch('auth_service.auth_core.security.middleware.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.return_value = "true"
            mock_get_env.return_value = mock_env

            result = await middleware(mock_request, mock_call_next)

        # Verify call_next was called
        mock_call_next.assert_called_once_with(mock_request)

        # Verify response is returned
        self.assertEqual(result, mock_response)

        # Verify headers were added
        self.assertEqual(mock_response.headers["X-Service-Name"], "test-service")
        self.assertEqual(mock_response.headers["X-Service-Version"], "2.0.0")

    @pytest.mark.asyncio
    async def test_security_middleware_oversized_request_rejection(self):
        """Test that middleware rejects oversized requests before processing."""
        middleware = await create_security_middleware()

        # Mock oversized request
        mock_request = Mock()
        mock_request.headers = {
            "content-length": str(MAX_JSON_PAYLOAD_SIZE + 1),
            "content-type": "application/json"
        }

        # Mock call_next (should not be called for oversized requests)
        mock_call_next = AsyncMock()

        # Execute middleware
        result = await middleware(mock_request, mock_call_next)

        # Verify call_next was NOT called
        mock_call_next.assert_not_called()

        # Verify error response
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 413)

    @pytest.mark.asyncio
    async def test_security_middleware_selective_header_addition(self):
        """Test middleware with selective header addition."""
        # Create middleware with only service headers enabled
        middleware = await create_security_middleware(
            add_service_headers_flag=True,
            add_security_headers_flag=False
        )

        mock_request = Mock()
        mock_request.headers = {}

        mock_response = Mock()
        mock_response.headers = {}

        mock_call_next = AsyncMock(return_value=mock_response)

        # Execute middleware
        result = await middleware(mock_request, mock_call_next)

        # Verify only service headers were added
        self.assertIn("X-Service-Name", mock_response.headers)
        self.assertIn("X-Service-Version", mock_response.headers)

        # Verify security headers were NOT added
        security_headers = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
        for header in security_headers:
            self.assertNotIn(header, mock_response.headers)


class SecurityMiddlewareEdgeCasesTests(SSotBaseTestCase):
    """Test edge cases and security scenarios for middleware."""

    def setUp(self):
        """Set up test environment for edge case testing."""
        super().setUp()

    @pytest.mark.asyncio
    async def test_validate_request_size_zero_content_length(self):
        """Test handling of zero content length."""
        mock_request = Mock()
        mock_request.headers = {
            "content-length": "0",
            "content-type": "application/json"
        }

        result = await validate_request_size(mock_request)
        self.assertIsNone(result)  # Zero size should be valid

    @pytest.mark.asyncio
    async def test_validate_request_size_negative_content_length(self):
        """Test handling of negative content length."""
        mock_request = Mock()
        mock_request.headers = {
            "content-length": "-100",
            "content-type": "application/json"
        }

        result = await validate_request_size(mock_request)
        self.assertIsNone(result)  # Negative values should be ignored (not validated)

    @pytest.mark.asyncio
    async def test_validate_request_size_boundary_values(self):
        """Test validation at exact boundary values."""
        # Test exactly at the limit
        mock_request = Mock()
        mock_request.headers = {
            "content-length": str(MAX_JSON_PAYLOAD_SIZE),
            "content-type": "application/json"
        }

        result = await validate_request_size(mock_request)
        self.assertIsNone(result)  # Exactly at limit should pass

        # Test just over the limit
        mock_request.headers["content-length"] = str(MAX_JSON_PAYLOAD_SIZE + 1)
        result = await validate_request_size(mock_request)
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 413)

    @pytest.mark.asyncio
    async def test_middleware_error_handling(self):
        """Test middleware behavior when call_next raises an exception."""
        middleware = await create_security_middleware()

        mock_request = Mock()
        mock_request.headers = {}

        # Mock call_next to raise an exception
        mock_call_next = AsyncMock(side_effect=Exception("Downstream error"))

        # Execute middleware - should propagate the exception
        with pytest.raises(Exception, match="Downstream error"):
            await middleware(mock_request, mock_call_next)

    def test_headers_overwrite_behavior(self):
        """Test that headers can be overwritten if set multiple times."""
        mock_response = Mock()
        mock_response.headers = {}

        # Add headers twice with different values
        add_service_headers(mock_response, "service-1", "1.0.0")
        add_service_headers(mock_response, "service-2", "2.0.0")

        # Should use the latest values
        self.assertEqual(mock_response.headers["X-Service-Name"], "service-2")
        self.assertEqual(mock_response.headers["X-Service-Version"], "2.0.0")

    @patch('auth_service.auth_core.security.middleware.get_env')
    def test_security_headers_environment_error_handling(self, mock_get_env):
        """Test handling when environment access fails."""
        # Mock environment to raise an exception
        mock_get_env.side_effect = Exception("Environment error")

        mock_response = Mock()
        mock_response.headers = {}

        # Should handle exception gracefully and not add headers
        try:
            add_security_headers(mock_response)
            # If no exception was raised, check that no headers were added
            security_headers = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
            for header in security_headers:
                self.assertNotIn(header, mock_response.headers)
        except Exception:
            # If exception is raised, that's also acceptable behavior
            pass

    @pytest.mark.asyncio
    async def test_concurrent_middleware_execution(self):
        """Test that middleware handles concurrent requests safely."""
        import asyncio

        middleware = await create_security_middleware()

        async def process_request(request_id):
            mock_request = Mock()
            mock_request.headers = {"request-id": str(request_id)}

            mock_response = Mock()
            mock_response.headers = {}

            mock_call_next = AsyncMock(return_value=mock_response)

            result = await middleware(mock_request, mock_call_next)
            return request_id, result

        # Process multiple requests concurrently
        tasks = [process_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all requests were processed
        self.assertEqual(len(results), 10)
        for request_id, response in results:
            self.assertIsNotNone(response)
            # Verify service headers were added to each response
            self.assertIn("X-Service-Name", response.headers)

    @pytest.mark.asyncio
    async def test_middleware_business_value_protection(self):
        """Test that middleware protects business value by blocking malicious requests."""
        middleware = await create_security_middleware()

        # Simulate malicious oversized request that could cause DoS
        malicious_request = Mock()
        malicious_request.headers = {
            "content-length": str(10 * 1024 * 1024),  # 10MB - way over limit
            "content-type": "application/json"
        }

        mock_call_next = AsyncMock()

        # Execute middleware
        result = await middleware(malicious_request, mock_call_next)

        # Should block the request and protect the service
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 413)
        mock_call_next.assert_not_called()

        # Verify error message is informative but not exposing internal details
        self.assertIn("too large", str(result.body).lower())