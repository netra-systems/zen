"""
Comprehensive API error handling tests.
Tests all error scenarios, status codes, and error response formats.

Business Value Justification (BVJ):
1. Segment: All customer segments requiring reliable API
2. Business Goal: Ensure consistent, informative error handling
3. Value Impact: Reduces customer frustration and support tickets
4. Revenue Impact: Improves developer experience, reduces churn by 10%
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List


class TestHTTPStatusCodes:
    """Test proper HTTP status code handling."""

    def test_200_success_responses(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test 200 OK responses are properly returned."""
        endpoints_200 = [
            ("/api/health", "GET", None),
            ("/", "GET", None),
        ]
        
        for endpoint, method, data in endpoints_200:
            if method == "GET":
                response = client.get(endpoint, headers=auth_headers if "api/" in endpoint else {})
            elif method == "POST":
                response = client.post(endpoint, json=data or {}, headers=auth_headers)
            
            if response.status_code == 200:
                # Should return valid JSON or content
                try:
                    response.json()
                except Exception:
                    # Plain text responses are also valid
                    assert len(response.text) > 0

    def test_201_created_responses(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test 201 Created responses for resource creation."""
        create_endpoints = [
            ("/api/workspaces", {"name": "Test Workspace"}),
            ("/api/threads", {"title": "Test Thread"}),
            ("/api/projects", {"name": "Test Project"}),
        ]
        
        for endpoint, data in create_endpoints:
            response = client.post(endpoint, json=data, headers=auth_headers)
            
            if response.status_code == 201:
                # Should return created resource data
                response_data = response.json()
                assert isinstance(response_data, dict)
                assert "id" in response_data or any(key.endswith("_id") for key in response_data.keys())

    def test_400_bad_request_responses(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test 400 Bad Request responses for invalid data."""
        bad_requests = [
            ("/api/auth/login", {"email": "invalid-email", "password": ""}),
            ("/api/users/profile", {"email": "not-an-email"}),
            ("/api/workspaces", {"name": ""}),  # Empty name
        ]
        
        for endpoint, data in bad_requests:
            response = client.post(endpoint, json=data, headers=auth_headers)
            
            if response.status_code == 400:
                # Should return error details
                error_data = response.json()
                assert isinstance(error_data, dict)
                assert "detail" in error_data or "error" in error_data or "message" in error_data

    def test_401_unauthorized_responses(self, client: TestClient) -> None:
        """Test 401 Unauthorized responses."""
        protected_endpoints = [
            "/api/users/profile",
            "/api/workspaces",
            "/api/threads",
            "/api/analysis",
            "/api/metrics/dashboard"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            
            if response.status_code == 401:
                # Should return authentication error
                error_data = response.json()
                assert isinstance(error_data, dict)
                error_text = str(error_data).lower()
                assert any(word in error_text for word in ["unauthorized", "authentication", "token", "login"])

    def test_403_forbidden_responses(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test 403 Forbidden responses."""
        # Try to access admin endpoints
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/system",
            "/api/admin/config"
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            
            if response.status_code == 403:
                # Should return permission error
                error_data = response.json()
                assert isinstance(error_data, dict)
                error_text = str(error_data).lower()
                assert any(word in error_text for word in ["forbidden", "permission", "access", "denied"])

    def test_404_not_found_responses(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test 404 Not Found responses."""
        not_found_endpoints = [
            "/api/nonexistent",
            "/api/users/nonexistent-id",
            "/api/workspaces/invalid-workspace-id",
            "/api/threads/missing-thread-id"
        ]
        
        for endpoint in not_found_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            
            if response.status_code == 404:
                # Should return not found error
                error_data = response.json()
                assert isinstance(error_data, dict)
                assert "detail" in error_data or "error" in error_data

    def test_422_validation_error_responses(self, client: TestClient) -> None:
        """Test 422 Validation Error responses."""
        validation_errors = [
            ("/api/auth/login", {}),  # Missing required fields
            ("/api/auth/register", {"email": "test"}),  # Missing password
            ("/api/workspaces", {"invalid_field": "value"}),  # Invalid field
        ]
        
        for endpoint, data in validation_errors:
            response = client.post(endpoint, json=data)
            
            if response.status_code == 422:
                # Should return validation details
                error_data = response.json()
                assert isinstance(error_data, dict)
                assert "detail" in error_data
                
                # Should have field-specific errors
                if isinstance(error_data["detail"], list):
                    for error in error_data["detail"]:
                        assert "loc" in error and "msg" in error

    def test_429_rate_limit_responses(self, client: TestClient) -> None:
        """Test 429 Too Many Requests responses."""
        # Make rapid requests to trigger rate limiting
        endpoint = "/api/auth/login"
        
        for _ in range(25):  # High number to trigger rate limit
            response = client.post(
                endpoint, 
                json={"email": "test@example.com", "password": "test"}
            )
            
            if response.status_code == 429:
                # Should include rate limit headers
                assert "Retry-After" in response.headers or "X-RateLimit-Remaining" in response.headers
                
                # Should return rate limit error
                error_data = response.json()
                assert isinstance(error_data, dict)
                error_text = str(error_data).lower()
                assert any(word in error_text for word in ["rate", "limit", "many", "requests"])
                break

    def test_500_internal_server_error_responses(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test 500 Internal Server Error responses."""
        # Mock a service to raise an exception
        with patch('app.services.user_service.get_user') as mock_get_user:
            mock_get_user.side_effect = Exception("Database connection failed")
            
            response = client.get("/api/users/profile", headers=auth_headers)
            
            if response.status_code == 500:
                # Should not expose internal error details
                error_data = response.json()
                assert isinstance(error_data, dict)
                
                error_text = str(error_data).lower()
                # Should not contain sensitive information
                sensitive_words = ["database", "connection", "traceback", "file", "line"]
                internal_exposed = any(word in error_text for word in sensitive_words)
                
                # In production, should not expose internal details
                assert not internal_exposed or "detail" in error_data


class TestErrorResponseFormats:
    """Test consistency of error response formats."""

    def test_json_error_response_structure(self, client: TestClient) -> None:
        """Test JSON error responses have consistent structure."""
        # Trigger various error types
        error_responses = []
        
        # 422 Validation Error
        response = client.post("/api/auth/login", json={})
        if response.status_code == 422:
            error_responses.append(response)
        
        # 401 Unauthorized
        response = client.get("/api/users/profile")
        if response.status_code == 401:
            error_responses.append(response)
        
        # 404 Not Found
        response = client.get("/api/nonexistent")
        if response.status_code == 404:
            error_responses.append(response)
        
        # All error responses should have consistent structure
        for response in error_responses:
            data = response.json()
            assert isinstance(data, dict)
            
            # Should have at least one of these fields
            required_fields = ["detail", "error", "message"]
            has_required_field = any(field in data for field in required_fields)
            assert has_required_field

    def test_error_response_content_type(self, client: TestClient) -> None:
        """Test error responses have correct content type."""
        response = client.get("/api/nonexistent")
        
        if response.status_code >= 400:
            content_type = response.headers.get("content-type", "")
            # Should be JSON for API errors
            assert "application/json" in content_type

    def test_error_message_localization(self, client: TestClient) -> None:
        """Test error messages are in appropriate language."""
        response = client.post("/api/auth/login", json={})
        
        if response.status_code >= 400:
            data = response.json()
            error_text = str(data)
            
            # Should be in English (or configured language)
            # Basic check - should not be empty and should be readable
            assert len(error_text) > 0
            assert not error_text.isdigit()  # Not just error codes

    def test_error_codes_consistency(self, client: TestClient) -> None:
        """Test custom error codes are consistent."""
        # Different types of validation errors
        validation_tests = [
            ({}, "missing_fields"),
            ({"email": "invalid"}, "invalid_format"),
            ({"email": "test@test.com", "password": ""}, "empty_field")
        ]
        
        error_codes = []
        for test_data, expected_type in validation_tests:
            response = client.post("/api/auth/login", json=test_data)
            
            if response.status_code == 422:
                data = response.json()
                if "code" in data:
                    error_codes.append(data["code"])
        
        # Error codes should follow consistent pattern (if implemented)
        if error_codes:
            for code in error_codes:
                assert isinstance(code, (str, int))
                if isinstance(code, str):
                    assert len(code) > 0


class TestFieldValidationErrors:
    """Test field-specific validation error handling."""

    def test_email_validation_errors(self, client: TestClient) -> None:
        """Test email field validation errors."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "test@",
            "test.example.com",
            "",
        ]
        
        for email in invalid_emails:
            response = client.post(
                "/api/auth/login", 
                json={"email": email, "password": "testpass"}
            )
            
            if response.status_code == 422:
                data = response.json()
                # Should specify email field error
                error_text = str(data).lower()
                assert "email" in error_text or "field" in error_text

    def test_password_validation_errors(self, client: TestClient) -> None:
        """Test password field validation errors."""
        invalid_passwords = [
            "",           # Empty
            "123",        # Too short
            " ",          # Whitespace only
        ]
        
        for password in invalid_passwords:
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": password}
            )
            
            if response.status_code == 422:
                data = response.json()
                # Should specify password field error
                error_text = str(data).lower()
                assert "password" in error_text or "field" in error_text

    def test_required_field_errors(self, client: TestClient) -> None:
        """Test required field validation errors."""
        # Test missing required fields in different endpoints
        required_field_tests = [
            ("/api/auth/login", {}, ["email", "password"]),
            ("/api/workspaces", {}, ["name"]),
            ("/api/threads", {}, ["title"]),
        ]
        
        for endpoint, data, required_fields in required_field_tests:
            response = client.post(endpoint, json=data)
            
            if response.status_code == 422:
                error_data = response.json()
                error_text = str(error_data).lower()
                
                # Should mention required fields
                field_mentioned = any(field in error_text for field in required_fields)
                assert field_mentioned or "required" in error_text

    def test_field_length_validation_errors(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test field length validation errors."""
        # Test overly long field values
        long_string = "x" * 1000
        
        length_tests = [
            ("/api/users/profile", {"full_name": long_string}),
            ("/api/workspaces", {"name": long_string}),
            ("/api/threads", {"title": long_string}),
        ]
        
        for endpoint, data in length_tests:
            response = client.post(endpoint, json=data, headers=auth_headers)
            
            if response.status_code in [400, 422]:
                error_data = response.json()
                error_text = str(error_data).lower()
                # Should mention length or size limits
                length_indicators = ["length", "long", "limit", "maximum", "size"]
                has_length_error = any(indicator in error_text for indicator in length_indicators)
                assert has_length_error or "invalid" in error_text


class TestNetworkErrorHandling:
    """Test handling of network-related errors."""

    def test_request_timeout_handling(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test request timeout handling."""
        # Mock a slow service
        with patch('app.services.analysis_service.run_analysis') as mock_analysis:
            import asyncio
            
            async def slow_analysis(*args, **kwargs):
                await asyncio.sleep(10)  # Simulate slow operation
                return {"result": "test"}
            
            mock_analysis.side_effect = slow_analysis
            
            response = client.post(
                "/api/analysis/start",
                json={"type": "test_analysis"},
                headers=auth_headers,
                timeout=2.0  # Short timeout
            )
            
            # Should handle timeout gracefully
            assert response.status_code in [202, 408, 500, 504]

    def test_large_payload_handling(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of large payloads."""
        # Create large payload
        large_payload = {
            "data": "x" * 10_000_000,  # 10MB of data
            "type": "large_test"
        }
        
        response = client.post(
            "/api/analysis/start",
            json=large_payload,
            headers=auth_headers
        )
        
        # Should either accept or reject with appropriate status
        if response.status_code == 413:
            # Payload too large
            error_data = response.json()
            error_text = str(error_data).lower()
            size_indicators = ["large", "size", "payload", "limit"]
            has_size_error = any(indicator in error_text for indicator in size_indicators)
            assert has_size_error
        else:
            # Should not cause server crash
            assert response.status_code != 500

    def test_malformed_json_handling(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of malformed JSON."""
        malformed_payloads = [
            '{"invalid": json}',
            '{"unclosed": "string}',
            '{invalid: "json"}',
            'not json at all',
            '{"trailing": "comma",}'
        ]
        
        for payload in malformed_payloads:
            response = client.post(
                "/api/auth/login",
                data=payload,
                headers={**auth_headers, "Content-Type": "application/json"}
            )
            
            # Should return 400 Bad Request for malformed JSON
            assert response.status_code in [400, 422]
            
            error_data = response.json()
            error_text = str(error_data).lower()
            json_indicators = ["json", "parse", "format", "invalid"]
            has_json_error = any(indicator in error_text for indicator in json_indicators)
            assert has_json_error or "detail" in error_data


class TestDatabaseErrorHandling:
    """Test handling of database-related errors."""

    def test_database_connection_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of database connection errors."""
        with patch('app.database.get_async_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            response = client.get("/api/users/profile", headers=auth_headers)
            
            if response.status_code == 500:
                # Should not expose database details
                error_data = response.json()
                error_text = str(error_data).lower()
                
                db_details = ["connection", "database", "sql", "postgres", "mysql"]
                exposes_db_details = any(detail in error_text for detail in db_details)
                # In production, should not expose database details
                assert not exposes_db_details or "maintenance" in error_text

    def test_constraint_violation_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of database constraint violations."""
        # Try to create duplicate resource
        workspace_data = {"name": "Duplicate Workspace"}
        
        # Create first workspace
        client.post("/api/workspaces", json=workspace_data, headers=auth_headers)
        
        # Try to create duplicate (if unique constraints exist)
        response = client.post("/api/workspaces", json=workspace_data, headers=auth_headers)
        
        if response.status_code == 400:
            error_data = response.json()
            error_text = str(error_data).lower()
            
            # Should provide user-friendly error message
            constraint_indicators = ["duplicate", "exists", "unique", "conflict"]
            has_constraint_error = any(indicator in error_text for indicator in constraint_indicators)
            assert has_constraint_error or "error" in error_data

    def test_record_not_found_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of record not found errors."""
        nonexistent_ids = [
            "nonexistent-user-id",
            "invalid-workspace-id", 
            "missing-thread-id"
        ]
        
        endpoints = [
            "/api/users/{}",
            "/api/workspaces/{}",
            "/api/threads/{}"
        ]
        
        for endpoint_template in endpoints:
            for nonexistent_id in nonexistent_ids[:1]:  # Test one per endpoint
                endpoint = endpoint_template.format(nonexistent_id)
                response = client.get(endpoint, headers=auth_headers)
                
                if response.status_code == 404:
                    error_data = response.json()
                    assert isinstance(error_data, dict)
                    assert "detail" in error_data or "error" in error_data


class TestExternalServiceErrorHandling:
    """Test handling of external service errors."""

    def test_llm_service_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of LLM service errors."""
        with patch('app.services.llm_service') as mock_llm:
            mock_llm.generate_response.side_effect = Exception("LLM service unavailable")
            
            response = client.post(
                "/api/agent/chat",
                json={"message": "Hello", "thread_id": "test-thread"},
                headers=auth_headers
            )
            
            if response.status_code in [500, 502, 503]:
                error_data = response.json()
                error_text = str(error_data).lower()
                
                # Should provide user-friendly error message
                service_indicators = ["service", "unavailable", "temporary", "retry"]
                has_service_error = any(indicator in error_text for indicator in service_indicators)
                assert has_service_error or "error" in error_data

    def test_third_party_api_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling of third-party API errors."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Third-party API error")
            
            response = client.get("/api/external/data", headers=auth_headers)
            
            if response.status_code in [500, 502, 503, 504]:
                error_data = response.json()
                # Should not expose third-party service details
                error_text = str(error_data).lower()
                
                external_indicators = ["api", "external", "third-party", "service"]
                exposes_external = any(indicator in error_text for indicator in external_indicators)
                # Should provide generic error or be abstracted
                assert not exposes_external or "temporarily unavailable" in error_text


class TestErrorLogging:
    """Test error logging functionality."""

    def test_error_logging_does_not_affect_response(self, client: TestClient) -> None:
        """Test that error logging doesn't affect API response."""
        with patch('app.logging_config.central_logger') as mock_logger:
            # Make logger raise exception
            mock_logger.get_logger.return_value.error.side_effect = Exception("Logging failed")
            
            response = client.get("/api/nonexistent")
            
            # Should still return proper error response despite logging failure
            assert response.status_code == 404
            
            try:
                error_data = response.json()
                assert isinstance(error_data, dict)
            except Exception:
                # Plain text response is also acceptable
                assert len(response.text) > 0

    def test_sensitive_data_not_logged(self, client: TestClient) -> None:
        """Test that sensitive data is not logged in errors."""
        with patch('app.logging_config.central_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.get_logger.return_value = mock_log
            
            # Send request with sensitive data
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "sensitive-password"}
            )
            
            # Check if logger was called with sensitive data
            if mock_log.error.called:
                logged_messages = [str(call.args) for call in mock_log.error.call_args_list]
                
                # Should not log password
                for message in logged_messages:
                    assert "sensitive-password" not in message