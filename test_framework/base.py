"""Base test framework module for backward compatibility.

This module provides base test classes and utilities that were previously
scattered across different test directories.
"""

import asyncio
import pytest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock


class BaseTestCase:
    """Base test case class for all tests."""
    
    def setup_method(self):
        """Setup method run before each test."""
        # Initialize metrics for each test method
        self._metrics: Dict[str, Any] = {}
    
    def teardown_method(self):
        """Teardown method run after each test."""
        pass
    
    def record_metric(self, name: str, value: Any) -> None:
        """Record a performance metric.
        
        Args:
            name: The name of the metric
            value: The value to record
        """
        # Initialize metrics if not already done (defensive programming)
        if not hasattr(self, '_metrics'):
            self._metrics = {}
        self._metrics[name] = value
    
    def get_metric(self, name: str) -> Any:
        """Get a recorded metric.
        
        Args:
            name: The name of the metric
            
        Returns:
            The metric value or None if not found
        """
        if not hasattr(self, '_metrics'):
            return None
        return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics.
        
        Returns:
            Dictionary of all metrics
        """
        if not hasattr(self, '_metrics'):
            return {}
        return self._metrics.copy()


class AsyncTestCase(BaseTestCase):
    """Base test case for async tests."""
    
    @pytest.fixture
    def event_loop(self):
        """Provide event loop for async tests."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()


class MockBase:
    """Base class for creating mock objects."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestFixtures:
    """Common test fixtures."""
    
    @staticmethod
    def create_mock_user(user_id: str = "test-user") -> Dict[str, Any]:
        """Create a mock user object."""
        return {
            "id": user_id,
            "email": f"{user_id}@test.com",
            "name": f"Test User {user_id}",
            "is_active": True,
        }
    
    @staticmethod
    def create_mock_session(session_id: str = "test-session") -> Dict[str, Any]:
        """Create a mock session object."""
        return {
            "id": session_id,
            "user_id": "test-user",
            "token": f"token-{session_id}",
            "expires_at": "2025-12-31T23:59:59Z",
        }


# Export commonly used fixtures
def create_async_mock(**kwargs) -> AsyncMock:
    """Create an async mock with specified attributes."""
    mock = AsyncMock()
    for key, value in kwargs.items():
        setattr(mock, key, value)
    return mock


def create_mock(**kwargs) -> Mock:
    """Create a mock with specified attributes."""
    mock = Mock()
    for key, value in kwargs.items():
        setattr(mock, key, value)
    return mock


# Import SSOT base test classes for cross-compatibility
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Add missing BaseUnitTest alias that tests are expecting
BaseUnitTest = SSotBaseTestCase

# Re-export common testing utilities
__all__ = [
    "BaseTestCase",
    "AsyncTestCase", 
    "BaseUnitTest",  # Added for backward compatibility
    "MockBase",
    "TestFixtures",
    "create_async_mock",
    "create_mock",
]