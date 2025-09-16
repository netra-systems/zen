"""
Helper functions for API route tests.
Provides reusable client setup, request data creation, and response assertions.
"""

from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

def create_test_client():
    """Create test client for API testing."""
    from netra_backend.app.main import app
    return TestClient(app)

def create_auth_tokens():
    """Create authentication tokens for testing."""
    return {
        "admin_token": "Bearer admin_token_123",
        "user_token": "Bearer user_token_456"
    }

def mock_admin_auth():
    """Create mock admin authentication."""
    return {"user_id": "admin", "role": "admin"}

def mock_user_auth():
    """Create mock user authentication."""
    return {"user_id": "123", "role": "user"}

def create_corpus_test_data():
    """Create test data for corpus operations."""
    return {
        "title": "Test Document",
        "content": "Test content",
        "metadata": {"category": "test"}
    }

def create_search_results():
    """Create mock search results."""
    return [
        {"id": "1", "title": "Result 1", "score": 0.9},
        {"id": "2", "title": "Result 2", "score": 0.8}
    ]

def create_llm_cache_metrics():
    """Create mock LLM cache metrics."""
    return {
        "hits": 100,
        "misses": 20,
        "hit_rate": 0.833,
        "size": 1024
    }

def create_mcp_message(message_type: str = "request", method: str = "test_method"):
    """Create MCP protocol message."""
    return {
        "type": message_type,
        "method": method,
        "params": {"key": "value"}
    }

def create_quality_metrics():
    """Create mock quality metrics."""
    return {
        "accuracy": 0.95,
        "latency_p50": 100,
        "latency_p99": 500,
        "error_rate": 0.01
    }

def create_supply_research_request():
    """Create supply chain research request."""
    return {
        "query": "GPU suppliers",
        "region": "US",
        "max_results": 10
    }

def create_supply_research_response():
    """Create supply chain research response."""
    return {
        "suppliers": [
            {"name": "Supplier A", "score": 0.9},
            {"name": "Supplier B", "score": 0.8}
        ]
    }

def create_synthetic_data_request():
    """Create synthetic data generation request."""
    return {
        "schema": {
            "user_id": "uuid",
            "name": "name",
            "age": "integer(18,65)"
        },
        "count": 100
    }

def create_synthetic_data_response():
    """Create synthetic data generation response."""
    return {
        "data": [{"user_id": "123", "name": "John", "age": 30}] * 100,
        "metadata": {"generated": 100}
    }

def create_thread_pagination_response():
    """Create thread pagination response."""
    return {
        "threads": [{"id": f"thread_{i}"} for i in range(10)],
        "total": 50,
        "page": 1,
        "per_page": 10
    }

def assert_auth_required(response):
    """Assert that endpoint requires authentication."""
    assert response.status_code == 401

def assert_admin_required(response):
    """Assert that endpoint requires admin role."""
    assert response.status_code == 403

def assert_successful_response(response, expected_status: int = 200):
    """Assert response is successful with expected status."""
    assert response.status_code == expected_status

def assert_error_response(response, expected_status: int = 500):
    """Assert response contains error with expected status."""
    assert response.status_code == expected_status
    assert "error" in response.json()

def assert_validation_error(response):
    """Assert response is validation error."""
    assert response.status_code == 422

def assert_search_results_ordered(results: List[Dict]):
    """Assert search results are ordered by score."""
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"]

def create_streaming_response() -> Generator[str, None, None]:
    """Create mock streaming response."""
    yield "Part 1"
    yield "Part 2"
    yield "Part 3"

def assert_streaming_chunks(chunks: List[str], expected_count: int):
    """Assert streaming response has expected number of chunks."""
    assert len(chunks) == expected_count

def patch_service_method(service_path: str, method_name: str, return_value: Any = None, side_effect: Any = None):
    """Create service method patch with return value or side effect."""
    full_path = f"{service_path}.{method_name}"
    if side_effect:
        # Mock: Component isolation for testing without external dependencies
        return patch(full_path, side_effect=side_effect)
    # Mock: Component isolation for testing without external dependencies
    return patch(full_path, return_value=return_value)

def create_config_update_data():
    """Create configuration update test data."""
    return {"log_level": "DEBUG", "max_retries": 5}

def create_invalid_config_data():
    """Create invalid configuration data."""
    return {"invalid_field": "value"}

def assert_metric_above_threshold(metrics: Dict, metric_name: str, threshold: float):
    """Assert metric is above threshold."""
    assert metrics[metric_name] > threshold

def create_enrichment_request():
    """Create supply data enrichment request."""
    return {
        "supplier_id": "123",
        "data_types": ["financials", "certifications"]
    }

def create_enrichment_response():
    """Create supply data enrichment response."""
    return {
        "supplier_id": "123",
        "financials": {"revenue": 1000000},
        "certifications": ["ISO9001", "ISO14001"]
    }

def assert_data_enrichment_complete(data: Dict, expected_keys: List[str]):
    """Assert data enrichment contains expected keys."""
    for key in expected_keys:
        assert key in data