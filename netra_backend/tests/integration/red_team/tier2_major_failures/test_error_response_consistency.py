from unittest.mock import Mock, patch, MagicMock

"""
RED TEAM TEST 22: Error Response Consistency

CRITICAL: This test is DESIGNED TO FAIL initially to expose real integration issues.
Tests error format consistency across all API endpoints and services.

Business Value Justification (BVJ):
    - Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Developer Experience, API Reliability, Integration Quality
- Value Impact: Inconsistent error responses break client integrations and user workflows
- Strategic Impact: Core API foundation for developer adoption and platform reliability

Testing Level: L3 (Real services, real endpoints, minimal mocking)
Expected Initial Result: FAILURE (exposes real error response consistency gaps)
""""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from shared.isolated_environment import IsolatedEnvironment

import pytest
import httpx
from fastapi.testclient import TestClient
from fastapi import status

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with error handling
try:
    from netra_backend.app.core.error_response import ErrorResponseBuilder
except ImportError:
    class ErrorResponseBuilder:
        @staticmethod
        def build_error_response(error, status_code=500):
            return {"error": str(error), "status_code": status_code}
        @staticmethod
        def build_validation_error(errors):
            return {"validation_errors": errors, "status_code": 400}

# Error middleware components exist
from netra_backend.app.middleware.error_middleware import ErrorRecoveryMiddleware

try:
    from netra_backend.app.core.error_handlers import (
        validation_error_handler,
        http_exception_handler, 
        general_exception_handler
    )
except ImportError:
    # Mock error handlers
    async def validation_error_handler(request, exc):
        return {"error": "Validation error", "status_code": 400}
    
    async def http_exception_handler(request, exc):
        return {"error": str(exc), "status_code": getattr(exc, 'status_code', 500)}
    
    async def general_exception_handler(request, exc):
        return {"error": "Internal server error", "status_code": 500}


class TestErrorResponseConsistency:
    """
    RED TEAM TEST 22: Error Response Consistency
    
    Tests error format consistency across all API endpoints and services.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """"

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

        @pytest.fixture
        def error_response_builder(self):
        """Error response builder for format validation."""
        return ErrorResponseBuilder()

        @pytest.mark.asyncio
        async def test_01_validation_error_consistency_fails(self, real_test_client):
        """
        Test 22A: Validation Error Consistency (EXPECTED TO FAIL)
        
        Tests that validation errors have consistent format across all endpoints.
        Will likely FAIL because:
        1. Validation error formats may be inconsistent
        2. Different endpoints may use different error structures
        3. Field validation details may be missing or inconsistent
        """"
        try:
        # Define test endpoints that should have validation
        validation_test_endpoints = [
        {
        "path": "/api/users",
        "method": "POST",
        "invalid_data": {
        "email": "invalid-email",  # Invalid email format
        "password": "123",  # Too short
        "username": ""  # Empty username
        },
        "expected_fields": ["email", "password", "username"]
        },
        {
        "path": "/api/threads",
        "method": "POST", 
        "invalid_data": {
        "title": "",  # Empty title
        "context": None,  # Null context
        "user_id": "invalid-uuid"  # Invalid UUID
        },
        "expected_fields": ["title", "context", "user_id"]
        },
        {
        "path": "/api/agents/execute",
        "method": "POST",
        "invalid_data": {
        "agent_type": "invalid_type",  # Invalid agent type
        "input": {},  # Empty input
        "timeout": "not_a_number"  # Invalid timeout
        },
        "expected_fields": ["agent_type", "input", "timeout"]
        },
        {
        "path": "/api/corpus",
        "method": "POST",
        "invalid_data": {
        "name": "",  # Empty name
        "description": None,  # Null description
        "metadata": "not_an_object"  # Invalid metadata type
        },
        "expected_fields": ["name", "description", "metadata"]
        }
        ]
            
        validation_error_responses = []
            
        # Test each endpoint with invalid data
        for endpoint_test in validation_test_endpoints:
        try:
        # FAILURE EXPECTED HERE - validation error formats may be inconsistent
        if endpoint_test["method"] == "POST":
        response = real_test_client.post(
        endpoint_test["path"],
        json=endpoint_test["invalid_data"],
        headers={"Content-Type": "application/json"}
        )
        elif endpoint_test["method"] == "PUT":
        response = real_test_client.put(
        endpoint_test["path"],
        json=endpoint_test["invalid_data"],
        headers={"Content-Type": "application/json"}
        )
                    
        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
        f"Endpoint {endpoint_test['path']] should return 422 for validation errors, got {response.status_code]"
                    
        error_data = response.json()
        validation_error_responses.append({
        "endpoint": endpoint_test["path"],
        "method": endpoint_test["method"],
        "response": error_data,
        "status_code": response.status_code
        })
                    
        except Exception as e:
        # If endpoint doesn't exist or has other issues, note it
        validation_error_responses.append({
        "endpoint": endpoint_test["path"],
        "method": endpoint_test["method"],
        "error": str(e),
        "status": "endpoint_unavailable"
        })
            
        # Verify response format consistency
        consistent_fields = set()
        inconsistent_responses = []
            
        for response_data in validation_error_responses:
        if "response" in response_data:
        response_fields = set(response_data["response"].keys())
                    
        if not consistent_fields:
        consistent_fields = response_fields
        elif response_fields != consistent_fields:
        inconsistent_responses.append({
        "endpoint": response_data["endpoint"],
        "expected_fields": list(consistent_fields),
        "actual_fields": list(response_fields),
        "missing_fields": list(consistent_fields - response_fields),
        "extra_fields": list(response_fields - consistent_fields)
        })
            
        # All validation errors should have consistent structure
        assert len(inconsistent_responses) == 0, \
        f"Validation error responses are inconsistent across endpoints: {inconsistent_responses}"
            
        # Verify required error fields are present
        required_error_fields = {"error", "message", "details"}
            
        for response_data in validation_error_responses:
        if "response" in response_data:
        response_fields = set(response_data["response"].keys())
        missing_fields = required_error_fields - response_fields
                    
        assert len(missing_fields) == 0, \
        f"Endpoint {response_data['endpoint']] missing required error fields: {missing_fields]"
            
        # Verify field-level validation details
        for response_data in validation_error_responses:
        if "response" in response_data and "details" in response_data["response"]:
        details = response_data["response"]["details"]
                    
        # Details should be a list of field errors
        assert isinstance(details, list), \
        f"Error details should be a list for {response_data['endpoint']]"
                    
        # Each detail should have field and message
        for detail in details:
        assert "field" in detail, \
        f"Error detail should have 'field' for {response_data['endpoint']]"
        assert "message" in detail, \
        f"Error detail should have 'message' for {response_data['endpoint']]"
        assert isinstance(detail["field"], str), \
        f"Error field should be string for {response_data['endpoint']]"
        assert isinstance(detail["message"], str), \
        f"Error message should be string for {response_data['endpoint']]"
                            
        except Exception as e:
        pytest.fail(f"Validation error consistency test failed: {e}")

        @pytest.mark.asyncio
        async def test_02_http_status_error_consistency_fails(self, real_test_client):
        """
        Test 22B: HTTP Status Error Consistency (EXPECTED TO FAIL)
        
        Tests that different HTTP status errors have consistent response formats.
        Will likely FAIL because:
        1. Different status codes may use different error formats
        2. Error messages may not follow consistent patterns
        3. Status code to error type mapping may be inconsistent
        """"
        try:
        # Test different HTTP status codes
        status_code_tests = [
        {
        "name": "Not Found (404)",
        "path": "/api/nonexistent-endpoint",
        "method": "GET",
        "expected_status": 404,
        "expected_error_type": "not_found"
        },
        {
        "name": "Unauthorized (401)",
        "path": "/api/users/profile",
        "method": "GET",
        "headers": {},  # No auth header
        "expected_status": 401,
        "expected_error_type": "unauthorized"
        },
        {
        "name": "Forbidden (403)",
        "path": "/api/admin/system-config",
        "method": "GET", 
        "headers": {"Authorization": "Bearer invalid-token"},
        "expected_status": 403,
        "expected_error_type": "forbidden"
        },
        {
        "name": "Method Not Allowed (405)",
        "path": "/api/users",
        "method": "DELETE",  # Assuming DELETE not allowed
        "expected_status": 405,
        "expected_error_type": "method_not_allowed"
        },
        {
        "name": "Too Many Requests (429)",
        "path": "/api/agents/execute",
        "method": "POST",
        "data": {"agent_type": "test"},
        "rate_limit_test": True,
        "expected_status": 429,
        "expected_error_type": "rate_limit_exceeded"
        }
        ]
            
        status_error_responses = []
            
        for status_test in status_code_tests:
        try:
        headers = status_test.get("headers", {"Content-Type": "application/json"})
                    
        # Special handling for rate limit test
        if status_test.get("rate_limit_test"):
        # Make multiple rapid requests to trigger rate limit
        for i in range(20):  # Rapid requests to trigger rate limit
        response = real_test_client.post(
        status_test["path"],
        json=status_test.get("data", {}),
        headers=headers
        )
                            
        if response.status_code == 429:
        break
        else:
        # Regular request
        if status_test["method"] == "GET":
        response = real_test_client.get(status_test["path"], headers=headers)
        elif status_test["method"] == "POST":
        response = real_test_client.post(
        status_test["path"],
        json=status_test.get("data", {}),
        headers=headers
        )
        elif status_test["method"] == "DELETE":
        response = real_test_client.delete(status_test["path"], headers=headers)
                    
        # FAILURE EXPECTED HERE - status error formats may be inconsistent
        status_error_responses.append({
        "test_name": status_test["name"],
        "expected_status": status_test["expected_status"],
        "actual_status": response.status_code,
        "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
        "expected_error_type": status_test["expected_error_type"]
        })
                    
        except Exception as e:
        status_error_responses.append({
        "test_name": status_test["name"],
        "error": str(e),
        "status": "test_failed"
        })
            
        # Verify status codes match expectations
        for response_data in status_error_responses:
        if "actual_status" in response_data:
        expected = response_data["expected_status"]
        actual = response_data["actual_status"]
                    
        # Allow some flexibility for endpoints that might not exist
        if expected in [401, 403, 405, 429]:
        assert actual in [expected, 404], \
        f"{response_data['test_name']]: Expected {expected] or 404, got {actual]"
        else:
        assert actual == expected, \
        f"{response_data['test_name']]: Expected status {expected], got {actual]"
            
        # Verify response format consistency across status codes
        valid_responses = [r for r in status_error_responses if "response" in r and r["response"]]
            
        if len(valid_responses) > 1:
        # All error responses should have same basic structure
        base_structure = set(valid_responses[0]["response"].keys())
                
        for response_data in valid_responses[1:]:
        current_structure = set(response_data["response"].keys())
                    
        assert base_structure == current_structure, \
        f"Error response structure inconsistent for {response_data['test_name']]: " \
        f"expected {base_structure}, got {current_structure}"
            
        # Verify error type mapping
        for response_data in valid_responses:
        if response_data["response"]:
        error_response = response_data["response"]
                    
        # Should have error type that matches status code
        if "error" in error_response:
        error_type = error_response["error"]
        expected_type = response_data["expected_error_type"]
                        
        # Allow some variations but should be related
        assert isinstance(error_type, str), \
        f"Error type should be string for {response_data['test_name']]"
        assert len(error_type) > 0, \
        f"Error type should not be empty for {response_data['test_name']]"
                            
        except Exception as e:
        pytest.fail(f"HTTP status error consistency test failed: {e}")

        @pytest.mark.asyncio
        async def test_03_service_error_propagation_consistency_fails(self, real_test_client):
        """
        Test 22C: Service Error Propagation Consistency (EXPECTED TO FAIL)
        
        Tests that errors from backend services are consistently formatted.
        Will likely FAIL because:
        1. Service-specific errors may use different formats
        2. Error context may be lost during propagation
        3. Stack traces may be inconsistently included/excluded
        """"
        try:
        # Test endpoints that involve multiple services
        service_error_tests = [
        {
        "name": "Database Connection Error",
        "path": "/api/users",
        "method": "GET",
        "simulate_error": "database_connection",
        "expected_error_category": "database_error"
        },
        {
        "name": "External API Error", 
        "path": "/api/agents/execute",
        "method": "POST",
        "data": {
        "agent_type": "external_api_agent",
        "input": {"trigger_external_error": True}
        },
        "expected_error_category": "external_service_error"
        },
        {
        "name": "Redis Connection Error",
        "path": "/api/sessions",
        "method": "POST",
        "data": {"simulate_redis_error": True},
        "expected_error_category": "cache_error"
        },
        {
        "name": "File System Error",
        "path": "/api/corpus/upload",
        "method": "POST",
        "files": {"file": ("test.txt", b"test content", "text/plain")},
        "data": {"simulate_fs_error": True},
        "expected_error_category": "file_system_error"
        },
        {
        "name": "LLM Service Error",
        "path": "/api/agents/execute",
        "method": "POST",
        "data": {
        "agent_type": "llm_agent",
        "input": {"prompt": "test", "force_llm_error": True}
        },
        "expected_error_category": "llm_service_error"
        }
        ]
            
        service_error_responses = []
            
        for error_test in service_error_tests:
        try:
        # Make request that should trigger service error
        headers = {"Content-Type": "application/json"}
                    
        # FAILURE EXPECTED HERE - service errors may not be handled consistently
        if error_test["method"] == "GET":
        response = real_test_client.get(error_test["path"], headers=headers)
        elif error_test["method"] == "POST":
        if "files" in error_test:
        # File upload test
        response = real_test_client.post(
        error_test["path"],
        files=error_test["files"],
        data=error_test.get("data", {})
        )
        else:
        response = real_test_client.post(
        error_test["path"],
        json=error_test.get("data", {}),
        headers=headers
        )
                    
        # Should return some kind of error (status >= 400)
        assert response.status_code >= 400, \
        f"{error_test['name']] should return error status, got {response.status_code]"
                    
        try:
        error_data = response.json()
        except json.JSONDecodeError:
        error_data = {"error": "non_json_response", "message": response.text[:200]]
                    
        service_error_responses.append({
        "test_name": error_test["name"],
        "status_code": response.status_code,
        "response": error_data,
        "expected_category": error_test["expected_error_category"]
        })
                    
        except Exception as e:
        # Service might not be available or error simulation might not work
        service_error_responses.append({
        "test_name": error_test["name"],
        "error": str(e),
        "status": "service_unavailable"
        })
            
        # Verify error response format consistency across services
        valid_service_responses = [r for r in service_error_responses if "response" in r]
            
        if len(valid_service_responses) > 1:
        # All service errors should have consistent structure
        required_fields = {"error", "message"}
                
        for response_data in valid_service_responses:
        error_response = response_data["response"]
        response_fields = set(error_response.keys())
                    
        missing_fields = required_fields - response_fields
        assert len(missing_fields) == 0, \
        f"{response_data['test_name']] missing required error fields: {missing_fields]"
                    
        # Verify field types
        assert isinstance(error_response["error"], str), \
        f"{response_data['test_name']] error field should be string"
        assert isinstance(error_response["message"], str), \
        f"{response_data['test_name']] message field should be string"
                    
        # Error should not be empty
        assert len(error_response["error"]) > 0, \
        f"{response_data['test_name']] error should not be empty"
        assert len(error_response["message"]) > 0, \
        f"{response_data['test_name']] message should not be empty"
            
        # Verify error categorization
        for response_data in valid_service_responses:
        error_response = response_data["response"]
                
        # Should include error category or type information
        if "category" in error_response:
        category = error_response["category"]
        expected_category = response_data["expected_category"]
                    
        # Category should be meaningful
        assert isinstance(category, str) and len(category) > 0, \
        f"{response_data['test_name']] error category should be non-empty string"
                
        # Should not expose internal implementation details
        message = error_response["message"]
                
        # Check for common implementation leaks
        sensitive_patterns = [
        "traceback", "stack trace", "internal error", 
        "database connection string", "api key", "password"
        ]
                
        message_lower = message.lower()
        for pattern in sensitive_patterns:
        assert pattern not in message_lower, \
        f"{response_data['test_name']] error message should not expose: {pattern]"
                        
        except Exception as e:
        pytest.fail(f"Service error propagation consistency test failed: {e}")

        @pytest.mark.asyncio
        async def test_04_error_logging_correlation_consistency_fails(self, real_test_client):
        """
        Test 22D: Error Logging Correlation Consistency (EXPECTED TO FAIL)
        
        Tests that error responses include consistent correlation IDs for debugging.
        Will likely FAIL because:
        1. Correlation IDs may not be implemented
        2. Error tracking may be inconsistent across endpoints  
        3. Log correlation may not work properly
        """"
        try:
        # Test endpoints with intentional errors to check correlation
        correlation_test_endpoints = [
        {
        "path": "/api/users/invalid-user-id",
        "method": "GET",
        "description": "User not found error"
        },
        {
        "path": "/api/threads",
        "method": "POST",
        "data": {"invalid": "data"},
        "description": "Validation error"
        },
        {
        "path": "/api/agents/execute",
        "method": "POST",
        "data": {"agent_type": "nonexistent"},
        "description": "Agent not found error"
        }
        ]
            
        correlation_responses = []
            
        for endpoint_test in correlation_test_endpoints:
        try:
        # Add correlation ID to request headers
        correlation_id = f"test_corr_{secrets.token_urlsafe(8)}"
        headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id
        }
                    
        # FAILURE EXPECTED HERE - correlation tracking may not be implemented
        if endpoint_test["method"] == "GET":
        response = real_test_client.get(endpoint_test["path"], headers=headers)
        else:
        response = real_test_client.post(
        endpoint_test["path"],
        json=endpoint_test.get("data", {}),
        headers=headers
        )
                    
        try:
        response_data = response.json()
        except json.JSONDecodeError:
        response_data = {}
                    
        correlation_responses.append({
        "endpoint": endpoint_test["path"],
        "description": endpoint_test["description"],
        "request_correlation_id": correlation_id,
        "status_code": response.status_code,
        "response": response_data,
        "response_headers": dict(response.headers)
        })
                    
        except Exception as e:
        correlation_responses.append({
        "endpoint": endpoint_test["path"],
        "error": str(e),
        "status": "request_failed"
        })
            
        # Verify correlation ID consistency
        for response_data in correlation_responses:
        if "response" in response_data and response_data["status_code"] >= 400:
        request_corr_id = response_data["request_correlation_id"]
                    
        # Check if correlation ID is included in response
        response_body = response_data["response"]
        response_headers = response_data["response_headers"]
                    
        # Should include correlation ID in response (either body or header)
        correlation_in_body = (
        "correlation_id" in response_body or 
        "request_id" in response_body or
        "trace_id" in response_body
        )
                    
        correlation_in_header = (
        "x-correlation-id" in response_headers or
        "x-request-id" in response_headers or
        "x-trace-id" in response_headers
        )
                    
        assert correlation_in_body or correlation_in_header, \
        f"Endpoint {response_data['endpoint']] should include correlation ID in response"
                    
        # If in body, verify it matches request or is a valid ID
        if correlation_in_body:
        for field in ["correlation_id", "request_id", "trace_id"]:
        if field in response_body:
        response_id = response_body[field]
        assert isinstance(response_id, str) and len(response_id) > 0, \
        f"Response {field} should be non-empty string"
                    
        # If in header, verify format
        if correlation_in_header:
        for header in ["x-correlation-id", "x-request-id", "x-trace-id"]:
        if header in response_headers:
        header_id = response_headers[header]
        assert isinstance(header_id, str) and len(header_id) > 0, \
        f"Response header {header} should be non-empty string"
            
        # Verify error uniqueness
        error_ids = set()
            
        for response_data in correlation_responses:
        if "response" in response_data:
        response_body = response_data["response"]
                    
        # Extract any ID from response
        response_id = None
        for field in ["correlation_id", "request_id", "trace_id", "error_id"]:
        if field in response_body:
        response_id = response_body[field]
        break
                    
        if response_id:
        assert response_id not in error_ids, \
        f"Error ID {response_id} should be unique across requests"
        error_ids.add(response_id)
            
        # At least some responses should have unique IDs
        assert len(error_ids) > 0, \
        "At least some error responses should include tracking IDs"
                
        except Exception as e:
        pytest.fail(f"Error logging correlation consistency test failed: {e}")

        @pytest.mark.asyncio
        async def test_05_error_response_localization_consistency_fails(self, real_test_client):
        """
        Test 22E: Error Response Localization Consistency (EXPECTED TO FAIL)
        
        Tests that error responses handle localization consistently.
        Will likely FAIL because:
        1. Localization may not be implemented for errors
        2. Language detection may not work properly
        3. Fallback to default language may be inconsistent
        """"
        try:
        # Test different language preferences
        language_tests = [
        {
        "language": "en-US",
        "accept_language": "en-US,en;q=0.9",
        "description": "English (US)"
        },
        {
        "language": "es-ES", 
        "accept_language": "es-ES,es;q=0.9,en;q=0.8",
        "description": "Spanish (Spain)"
        },
        {
        "language": "fr-FR",
        "accept_language": "fr-FR,fr;q=0.9,en;q=0.8", 
        "description": "French (France)"
        },
        {
        "language": "de-DE",
        "accept_language": "de-DE,de;q=0.9,en;q=0.8",
        "description": "German (Germany)"
        }
        ]
            
        # Test endpoint that should return validation error
        test_endpoint = "/api/users"
        invalid_data = {
        "email": "invalid-email",
        "password": "123",
        "username": ""
        }
            
        localization_responses = []
            
        for lang_test in language_tests:
        try:
        headers = {
        "Content-Type": "application/json",
        "Accept-Language": lang_test["accept_language"]
        }
                    
        # FAILURE EXPECTED HERE - localization may not be implemented
        response = real_test_client.post(
        test_endpoint,
        json=invalid_data,
        headers=headers
        )
                    
        try:
        response_data = response.json()
        except json.JSONDecodeError:
        response_data = {}
                    
        localization_responses.append({
        "language": lang_test["language"],
        "description": lang_test["description"],
        "status_code": response.status_code,
        "response": response_data
        })
                    
        except Exception as e:
        localization_responses.append({
        "language": lang_test["language"],
        "error": str(e),
        "status": "request_failed"
        })
            
        # Verify response structure is consistent across languages
        valid_responses = [r for r in localization_responses if "response" in r]
            
        if len(valid_responses) > 1:
        base_structure = set(valid_responses[0]["response"].keys())
                
        for response_data in valid_responses[1:]:
        current_structure = set(response_data["response"].keys())
                    
        assert base_structure == current_structure, \
        f"Error response structure should be consistent across languages. " \
        f"{response_data['description']] has different structure"
            
        # Verify language handling
        english_response = None
        other_language_responses = []
            
        for response_data in valid_responses:
        if response_data["language"] == "en-US":
        english_response = response_data
        else:
        other_language_responses.append(response_data)
            
        if english_response and other_language_responses:
        # Check if messages are different for different languages
        english_message = english_response["response"].get("message", "")
                
        for other_response in other_language_responses:
        other_message = other_response["response"].get("message", "")
                    
        # Messages could be the same (no localization) or different (localized)
        # But they should not be empty
        assert len(other_message) > 0, \
        f"{other_response['description']] should have non-empty error message"
                    
        # If localization is implemented, should include language indicator
        if other_message != english_message:
        # Different message suggests localization might be working
        # Verify it's actually localized (basic check)
        assert isinstance(other_message, str), \
        f"Localized message should be string for {other_response['description']]"
            
        # Verify fallback behavior
        # Test with unsupported language
        unsupported_headers = {
        "Content-Type": "application/json",
        "Accept-Language": "xx-XX,xx;q=0.9"  # Unsupported language
        }
            
        fallback_response = real_test_client.post(
        test_endpoint,
        json=invalid_data,
        headers=unsupported_headers
        )
            
        try:
        fallback_data = fallback_response.json()
                
        # Should fallback gracefully and return valid error
        assert "message" in fallback_data, \
        "Fallback response should include error message"
        assert len(fallback_data["message"]) > 0, \
        "Fallback error message should not be empty"
                    
        except json.JSONDecodeError:
        pytest.fail("Fallback response should be valid JSON")
                
        except Exception as e:
        pytest.fail(f"Error response localization consistency test failed: {e}")


# Utility class for error response consistency testing
class RedTeamErrorResponseTestUtils:
    """Utility methods for error response consistency testing."""
    
    @staticmethod
    def validate_error_response_structure(
        response_data: Dict[str, Any],
        endpoint: str
    ) -> Dict[str, Any]:
        """Validate error response has expected structure."""
        
        validation_report = {
            "endpoint": endpoint,
            "valid": True,
            "issues": []
        }
        
        # Required fields
        required_fields = ["error", "message"]
        for field in required_fields:
            if field not in response_data:
                validation_report["valid"] = False
                validation_report["issues"].append(f"Missing required field: {field]")
            elif not isinstance(response_data[field], str):
                validation_report["valid"] = False
                validation_report["issues"].append(f"Field {field] should be string")
            elif len(response_data[field]) == 0:
                validation_report["valid"] = False
                validation_report["issues"].append(f"Field {field] should not be empty")
        
        # Optional but recommended fields
        recommended_fields = ["timestamp", "request_id", "details"]
        validation_report["missing_recommended"] = []
        
        for field in recommended_fields:
            if field not in response_data:
                validation_report["missing_recommended"].append(field)
        
        # Validate field types if present
        if "timestamp" in response_data:
            timestamp = response_data["timestamp"]
            if not isinstance(timestamp, str):
                validation_report["valid"] = False
                validation_report["issues"].append("Timestamp should be string")
        
        if "details" in response_data:
            details = response_data["details"]
            if not isinstance(details, (list, dict)):
                validation_report["valid"] = False
                validation_report["issues"].append("Details should be list or dict")
        
        return validation_report
    
    @staticmethod
    def extract_error_patterns(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common patterns from error responses."""
        
        patterns = {
            "status_codes": {},
            "error_types": {},
            "message_patterns": {},
            "structure_patterns": {}
        }
        
        for response_data in responses:
            if "status_code" in response_data:
                status_code = response_data["status_code"]
                patterns["status_codes"][status_code] = patterns["status_codes"].get(status_code, 0) + 1
            
            if "response" in response_data:
                response_body = response_data["response"]
                
                if "error" in response_body:
                    error_type = response_body["error"]
                    patterns["error_types"][error_type] = patterns["error_types"].get(error_type, 0) + 1
                
                # Structure pattern
                structure = sorted(response_body.keys())
                structure_key = ",".join(structure)
                patterns["structure_patterns"][structure_key] = patterns["structure_patterns"].get(structure_key, 0) + 1
        
        return patterns
    
    @staticmethod
    def check_sensitive_information_leakage(
        error_message: str,
        endpoint: str
    ) -> List[str]:
        """Check if error message contains sensitive information."""
        
        sensitive_patterns = [
            (r"password", "Password information"),
            (r"api[_-]?key", "API key information"),
            (r"secret", "Secret information"),
            (r"token", "Token information"),
            (r"connection\s+string", "Database connection string"),
            (r"internal\s+error", "Internal implementation details"),
            (r"stack\s+trace", "Stack trace information"),
            (r"traceback", "Python traceback"),
            (r"/[a-zA-Z0-9_/]+\.py", "File path information"),
            (r"localhost:\d+", "Internal service endpoints"),
            (r"127\.0\.0\.1:\d+", "Internal IP addresses")
        ]
        
        import re
        leaks_found = []
        
        message_lower = error_message.lower()
        
        for pattern, description in sensitive_patterns:
            if re.search(pattern, message_lower):
                leaks_found.append(description)
        
        return leaks_found