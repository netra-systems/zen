"""
Test helpers for network and pagination utilities testing.
Provides setup, assertion, and fixture functions for network and pagination utility tests.
"""

import asyncio
from typing import Any, Callable, Dict, Tuple
from unittest.mock import AsyncMock

class NetworkTestHelpers:
    """Helper functions for network utility testing."""
    
    @staticmethod
    def mock_successful_response():
        """Mock successful HTTP response."""
        # Mock: Generic component isolation for controlled unit testing
        mock_response = AsyncMock()
        mock_response.status = 200
        # Mock: Async component isolation for testing without real async operations
        mock_response.json = AsyncMock(return_value={"success": True})
        return mock_response
    
    @staticmethod
    def create_failing_request(max_attempts: int) -> Tuple[Callable, Callable]:
        """Create request that fails then succeeds."""
        call_count = 0
        
        async def failing_get(url: str, **request_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < max_attempts:
                raise Exception("Network error")
            return NetworkTestHelpers.mock_successful_response()
        
        return failing_get, lambda: call_count

class PaginationTestHelpers:
    """Helper functions for pagination utility testing."""
    
    @staticmethod
    def create_cursor_data() -> Dict[str, Any]:
        """Create cursor data for testing."""
        return {"id": 123, "timestamp": "2025-01-01T00:00:00Z"}
    
    @staticmethod
    def assert_pagination_metadata(metadata: Dict[str, Any], expected: Dict[str, Any]):
        """Assert pagination metadata matches expected values."""
        for key, value in expected.items():
            assert metadata[key] == value