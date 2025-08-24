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
        pass
    
    def teardown_method(self):
        """Teardown method run after each test."""
        pass


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


# Re-export common testing utilities
__all__ = [
    "BaseTestCase",
    "AsyncTestCase",
    "MockBase",
    "TestFixtures",
    "create_async_mock",
    "create_mock",
]