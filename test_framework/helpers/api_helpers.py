"""
API test helper functions.
Consolidates API-related helpers from across the project.
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import Mock


def create_test_api_response(
    status_code: int = 200,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Mock:
    """Create a mock API response for testing"""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = data or {"status": "success"}
    response.text = json.dumps(data or {"status": "success"})
    response.headers = headers or {"Content-Type": "application/json"}
    response.ok = 200 <= status_code < 300
    return response


def create_error_response(
    status_code: int = 400,
    error_message: str = "Bad Request",
    error_code: Optional[str] = None
) -> Mock:
    """Create a mock error response for testing"""
    error_data = {
        "error": error_message,
        "status_code": status_code
    }
    if error_code:
        error_data["error_code"] = error_code
    
    return create_test_api_response(status_code, error_data)


def assert_success_response(response, expected_status: int = 200):
    """Assert that response is successful with expected status"""
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {getattr(response, 'text', 'No text')}"
    return response.json() if hasattr(response, 'json') and callable(response.json) else None


def assert_error_response(
    response,
    expected_status: int = 400,
    expected_error: Optional[str] = None
):
    """Assert that response is an error with expected status"""
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {getattr(response, 'text', 'No text')}"
    
    if expected_error:
        if hasattr(response, 'json') and callable(response.json):
            data = response.json()
            assert expected_error in str(data), \
                f"Expected error '{expected_error}' not found in {data}"
    
    return response.json() if hasattr(response, 'json') and callable(response.json) else None


def create_paginated_response(
    items: List[Dict[str, Any]],
    page: int = 1,
    page_size: int = 10,
    total_count: Optional[int] = None
) -> Dict[str, Any]:
    """Create a paginated API response"""
    if total_count is None:
        total_count = len(items)
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]
    
    return {
        "items": page_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": end_idx < total_count,
            "has_previous": page > 1
        }
    }


def create_websocket_message(
    message_type: str = "test",
    data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a WebSocket message for testing"""
    message = {
        "type": message_type,
        "timestamp": "2025-01-01T00:00:00Z"
    }
    
    if data:
        message["data"] = data
    
    if user_id:
        message["user_id"] = user_id
    
    return message


def validate_api_response_structure(
    response_data: Dict[str, Any],
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None
) -> bool:
    """Validate API response structure"""
    # Check required fields
    for field in required_fields:
        if field not in response_data:
            raise AssertionError(f"Required field '{field}' missing from response")
    
    # Optionally check that only expected fields are present
    if optional_fields is not None:
        allowed_fields = set(required_fields + optional_fields)
        actual_fields = set(response_data.keys())
        unexpected_fields = actual_fields - allowed_fields
        
        if unexpected_fields:
            raise AssertionError(f"Unexpected fields in response: {unexpected_fields}")
    
    return True


class APITestHelpers:
    """API test helper class with common operations"""
    
    @staticmethod
    def create_auth_test_request(
        method: str = "GET",
        endpoint: str = "/api/test",
        data: Optional[Dict[str, Any]] = None,
        user_id: str = "test-user-123"
    ) -> Dict[str, Any]:
        """Create an authenticated test request"""
        from test_framework.helpers.auth_helpers import create_test_auth_headers
        
        request = {
            "method": method,
            "endpoint": endpoint,
            "headers": create_test_auth_headers(user_id=user_id)
        }
        
        if data:
            request["data"] = data
        
        return request
    
    @staticmethod
    def create_bulk_api_requests(
        count: int = 10,
        base_endpoint: str = "/api/test"
    ) -> List[Dict[str, Any]]:
        """Create multiple API requests for testing"""
        return [
            {
                "method": "POST",
                "endpoint": f"{base_endpoint}/{i}",
                "data": {"test_data": f"request_{i}"}
            }
            for i in range(count)
        ]
    
    @staticmethod
    def simulate_rate_limiting() -> Mock:
        """Simulate rate limiting response"""
        return create_error_response(
            status_code=429,
            error_message="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED"
        )
    
    @staticmethod
    def simulate_server_error() -> Mock:
        """Simulate server error response"""
        return create_error_response(
            status_code=500,
            error_message="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
    
    @staticmethod
    def create_upload_test_data() -> Dict[str, Any]:
        """Create file upload test data"""
        return {
            "filename": "test_file.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "content": b"fake file content for testing"
        }


def assert_api_performance(response_time: float, max_time: float = 1.0):
    """Assert API response time is within limits"""
    assert response_time <= max_time, \
        f"API response took {response_time:.3f}s (max: {max_time}s)"


def assert_content_type(response, expected_type: str = "application/json"):
    """Assert response content type"""
    content_type = response.headers.get("Content-Type", "")
    assert expected_type in content_type, \
        f"Expected content type '{expected_type}', got '{content_type}'"


def create_health_check_response(healthy: bool = True) -> Dict[str, Any]:
    """Create health check response"""
    return {
        "status": "healthy" if healthy else "unhealthy",
        "checks": {
            "database": "healthy" if healthy else "unhealthy",
            "redis": "healthy" if healthy else "unhealthy",
            "external_apis": "healthy" if healthy else "unhealthy"
        },
        "timestamp": "2025-01-01T00:00:00Z"
    }


def create_metrics_response() -> Dict[str, Any]:
    """Create metrics API response"""
    return {
        "metrics": {
            "requests_total": 1000,
            "requests_per_second": 10.5,
            "avg_response_time": 0.25,
            "error_rate": 0.01,
            "active_connections": 50
        },
        "timestamp": "2025-01-01T00:00:00Z"
    }


# Utility functions for common API test patterns

def mock_external_api_call(
    url: str,
    response_data: Optional[Dict[str, Any]] = None,
    status_code: int = 200
):
    """Mock an external API call"""
    from unittest.mock import patch
    
    mock_response = create_test_api_response(status_code, response_data)
    
    # Mock both requests and httpx
    patches = []
    try:
        patches.append(patch('requests.get', return_value=mock_response))
        patches.append(patch('requests.post', return_value=mock_response))
        patches.append(patch('httpx.AsyncClient.get', return_value=mock_response))
        patches.append(patch('httpx.AsyncClient.post', return_value=mock_response))
    except ImportError:
        pass  # Libraries not available
    
    return patches


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Basic JSON schema validation (simplified)"""
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return True
    except ImportError:
        # Fallback to basic validation if jsonschema not available
        required_fields = schema.get("required", [])
        return all(field in data for field in required_fields)
    except Exception as e:
        raise AssertionError(f"JSON schema validation failed: {e}")


def create_cors_test_headers() -> Dict[str, str]:
    """Create CORS test headers"""
    return {
        "Origin": "https://example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization"
    }