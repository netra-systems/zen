"""
Test Base Classes: Foundation for critical path integration tests.

This module provides base classes and common functionality for critical path
integration tests, ensuring consistency and reducing code duplication.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Quality Assurance)
- Business Goal: Reduce test development time by 40%, improve test reliability
- Value Impact: Faster test development enables more comprehensive coverage
- Revenue Impact: Prevents $20K+ loss from bugs reaching production
"""

import asyncio
import pytest
from typing import Any, Dict, List, Optional
from unittest import TestCase
from unittest.mock import MagicMock, patch

from netra_backend.app.core.config import get_settings
from netra_backend.app.schemas.registry import User, Message, Thread


class BaseCriticalPathTest(TestCase):
    """Base class for critical path integration tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_user = User(
            id="test_user_123",
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
        
        self.mock_thread = Thread(
            id="test_thread_123",
            user_id="test_user_123",
            title="Test Thread"
        )
        
        self.mock_message = Message(
            id="test_message_123",
            thread_id="test_thread_123",
            role="user",
            content="Test message content"
        )
    
    def tearDown(self):
        """Clean up after test."""
        pass
    
    def create_mock_user(self, **kwargs) -> User:
        """Create a mock user with default or custom attributes."""
        defaults = {
            "id": "test_user_123",
            "email": "test@example.com", 
            "full_name": "Test User",
            "is_active": True
        }
        defaults.update(kwargs)
        return User(**defaults)
    
    def create_mock_thread(self, **kwargs) -> Thread:
        """Create a mock thread with default or custom attributes."""
        defaults = {
            "id": "test_thread_123",
            "user_id": "test_user_123",
            "title": "Test Thread"
        }
        defaults.update(kwargs)
        return Thread(**defaults)
    
    def create_mock_message(self, **kwargs) -> Message:
        """Create a mock message with default or custom attributes."""
        defaults = {
            "id": "test_message_123",
            "thread_id": "test_thread_123",
            "role": "user",
            "content": "Test message"
        }
        defaults.update(kwargs)
        return Message(**defaults)


class AsyncBaseCriticalPathTest:
    """Base class for async critical path integration tests."""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Set up async test environment."""
        self.mock_user = User(
            id="test_user_123",
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
        
        self.mock_thread = Thread(
            id="test_thread_123",
            user_id="test_user_123",
            title="Test Thread"
        )
        
        self.mock_message = Message(
            id="test_message_123",
            thread_id="test_thread_123",
            role="user",
            content="Test message content"
        )
    
    async def create_mock_user(self, **kwargs) -> User:
        """Create a mock user with default or custom attributes."""
        defaults = {
            "id": "test_user_123",
            "email": "test@example.com",
            "full_name": "Test User", 
            "is_active": True
        }
        defaults.update(kwargs)
        return User(**defaults)
    
    async def create_mock_thread(self, **kwargs) -> Thread:
        """Create a mock thread with default or custom attributes."""
        defaults = {
            "id": "test_thread_123",
            "user_id": "test_user_123",
            "title": "Test Thread"
        }
        defaults.update(kwargs)
        return Thread(**defaults)
    
    async def create_mock_message(self, **kwargs) -> Message:
        """Create a mock message with default or custom attributes."""
        defaults = {
            "id": "test_message_123",
            "thread_id": "test_thread_123",
            "role": "user",
            "content": "Test message"
        }
        defaults.update(kwargs)
        return Message(**defaults)


class MockServiceManager:
    """Mock service manager for testing service interactions."""
    
    def __init__(self):
        self._services: Dict[str, MagicMock] = {}
    
    def mock_service(self, service_name: str) -> MagicMock:
        """Get or create a mock service."""
        if service_name not in self._services:
            # Mock: Generic component isolation for controlled unit testing
            self._services[service_name] = MagicMock()
        return self._services[service_name]
    
    def reset_all_mocks(self) -> None:
        """Reset all mock services."""
        for mock in self._services.values():
            mock.reset_mock()
    
    def get_service_call_count(self, service_name: str, method_name: str) -> int:
        """Get call count for a specific service method."""
        if service_name in self._services:
            method = getattr(self._services[service_name], method_name, None)
            if method:
                return method.call_count
        return 0


class DatabaseMockMixin:
    """Mixin for database-related test mocking."""
    
    @pytest.fixture(autouse=True)
    async def mock_database(self):
        """Mock database operations."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.db.postgres.get_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            self.mock_db_session = mock_session
            try:
                yield session
            finally:
                if hasattr(session, "close"):
                    await session.close()
    
    def setup_db_query_result(self, result: Any) -> None:
        """Set up mock database query result."""
        self.mock_db_session.execute.return_value.scalar_one_or_none.return_value = result
    
    def setup_db_query_all_result(self, results: List[Any]) -> None:
        """Set up mock database query all results."""
        self.mock_db_session.execute.return_value.scalars.return_value.all.return_value = results


class AuthMockMixin:
    """Mixin for authentication-related test mocking."""
    
    @pytest.fixture(autouse=True)
    def mock_auth(self):
        """Mock authentication services."""
        # Mock: Authentication service isolation for testing without real auth flows
        with patch('netra_backend.app.services.user_auth_service.get_current_user') as mock_auth:
            mock_auth.return_value = self.mock_user
            self.mock_auth_service = mock_auth
            yield mock_auth
    
    def setup_auth_user(self, user: Optional[User] = None) -> None:
        """Set up authenticated user for tests."""
        self.mock_auth_service.return_value = user or self.mock_user
    
    def setup_auth_failure(self, exception: Exception) -> None:
        """Set up authentication failure."""
        self.mock_auth_service.side_effect = exception


class WebSocketMockMixin:
    """Mixin for WebSocket-related test mocking."""
    
    @pytest.fixture(autouse=True)
    def mock_websocket(self):
        """Mock WebSocket services."""
        # Mock: WebSocket connection isolation for testing without network overhead
        with patch('netra_backend.app.services.websocket_manager.WebSocketManager') as mock_ws:
            # Mock: Generic component isolation for controlled unit testing
            mock_ws_instance = MagicMock()
            mock_ws.return_value = mock_ws_instance
            self.mock_websocket_manager = mock_ws_instance
            yield mock_ws_instance
    
    def setup_websocket_connection(self, user_id: str, connected: bool = True) -> None:
        """Set up WebSocket connection state."""
        self.mock_websocket_manager.is_connected.return_value = connected
        self.mock_websocket_manager.get_user_connections.return_value = [user_id] if connected else []


class FullIntegrationTestBase(BaseCriticalPathTest, DatabaseMockMixin, AuthMockMixin, WebSocketMockMixin):
    """Full integration test base with all common mocking."""
    
    def setUp(self):
        """Set up full integration test environment."""
        super().setUp()
        self.service_manager = MockServiceManager()
    
    def tearDown(self):
        """Clean up full integration test."""
        super().tearDown()
        self.service_manager.reset_all_mocks()


# Common test fixtures
@pytest.fixture
def mock_user():
    """Provide a mock user for tests."""
    return User(
        id="test_user_123",
        email="test@example.com",
        full_name="Test User",
        is_active=True
    )


@pytest.fixture
def mock_thread():
    """Provide a mock thread for tests."""
    return Thread(
        id="test_thread_123", 
        user_id="test_user_123",
        title="Test Thread"
    )


@pytest.fixture
def mock_message():
    """Provide a mock message for tests."""
    return Message(
        id="test_message_123",
        thread_id="test_thread_123",
        role="user", 
        content="Test message"
    )


@pytest.fixture
def service_manager():
    """Provide a mock service manager."""
    return MockServiceManager()


# Test utilities
def assert_response_success(response: Dict[str, Any], expected_status: int = 200) -> None:
    """Assert that response indicates success."""
    assert response.get("status_code", 200) == expected_status
    assert "error" not in response or not response["error"]


def assert_response_error(response: Dict[str, Any], expected_status: int = 400) -> None:
    """Assert that response indicates error."""
    assert response.get("status_code", 400) >= 400
    assert "error" in response and response["error"]


def create_test_config(**overrides) -> Dict[str, Any]:
    """Create test configuration with optional overrides."""
    base_config = {
        "environment": "test",
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/1",
        "jwt_secret": "test_secret_key_for_testing_only"
    }
    base_config.update(overrides)
    return base_config


class CriticalPathMetrics:
    """Metrics collection for critical path testing."""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = None
        self.end_time = None
    
    def start_timing(self):
        """Start timing measurement."""
        import time
        self.start_time = time.time()
    
    def end_timing(self):
        """End timing measurement.""" 
        import time
        self.end_time = time.time()
    
    def get_duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def add_metric(self, name: str, value: Any):
        """Add a metric value."""
        self.metrics[name] = value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()


class L4StagingCriticalPathTestBase:
    """Base class for L4 staging critical path tests."""
    
    def __init__(self):
        self.metrics = CriticalPathMetrics()
        self.staging_config = {}
    
    async def setUp(self):
        """Set up L4 staging test environment."""
        self.metrics.start_timing()
        # Initialize staging environment
        pass
    
    async def tearDown(self):
        """Clean up L4 staging test environment."""
        self.metrics.end_timing()
        # Clean up staging resources
        pass
    
    def get_staging_config(self) -> Dict[str, Any]:
        """Get staging configuration."""
        return self.staging_config
    
    def set_staging_config(self, config: Dict[str, Any]):
        """Set staging configuration."""
        self.staging_config.update(config)