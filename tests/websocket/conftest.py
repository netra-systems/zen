"""WebSocket test configuration and fixtures."""

import asyncio
import pytest
import pytest_asyncio
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Test environment setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_user_data():
    """Test user data for WebSocket authentication."""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "is_active": True,
        "permissions": ["read", "write"]
    }


@pytest.fixture
def mock_auth_token():
    """Mock authentication token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


@pytest.fixture
async def test_user(test_user_data):
    """Create test user for WebSocket testing."""
    # Mock database user creation
    with patch('app.services.security_service.SecurityService') as mock_security:
        mock_security_instance = AsyncMock()
        mock_user = Mock()
        mock_user.id = test_user_data["id"]
        mock_user.email = test_user_data["email"] 
        mock_user.is_active = test_user_data["is_active"]
        
        mock_security_instance.get_user_by_id.return_value = mock_user
        mock_security.return_value = mock_security_instance
        
        yield mock_user


@pytest.fixture
async def authenticated_websocket_token(test_user_data, mock_auth_token):
    """Get authenticated WebSocket token."""
    # Mock auth client token validation
    with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
        mock_validate.return_value = {
            "valid": True,
            "user_id": test_user_data["id"],
            "email": test_user_data["email"],
            "permissions": test_user_data["permissions"]
        }
        yield mock_auth_token


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing."""
    mock_ws = Mock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_text = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.query_params = {}
    mock_ws.headers = {}
    return mock_ws


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    with patch('app.db.postgres.get_async_db') as mock_db:
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        mock_db.return_value.__aenter__.return_value = mock_session
        yield mock_session


@pytest.fixture
def websocket_test_config():
    """WebSocket test configuration."""
    return {
        "version": "1.0",
        "features": {
            "json_first": True,
            "auth_required": True,
            "heartbeat_supported": True,
            "reconnection_supported": True,
            "rate_limiting": True,
            "message_queuing": True
        },
        "endpoints": {
            "websocket": "/ws/enhanced",
            "service_discovery": "/ws/config"
        },
        "connection_limits": {
            "max_connections_per_user": 5,
            "max_message_rate": 60,
            "max_message_size": 10240,
            "heartbeat_interval": 30000
        },
        "auth": {
            "methods": ["jwt_query_param"],
            "token_validation": "auth_service",
            "session_handling": "manual"
        }
    }


@pytest.fixture
def cors_test_origins():
    """Test CORS origins configuration."""
    return [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://test.example.com"
    ]


@pytest.fixture
def mock_unified_manager():
    """Mock unified WebSocket manager."""
    with patch('app.websocket.unified.manager.get_unified_manager') as mock_manager:
        manager_instance = Mock()
        manager_instance.connect_user = AsyncMock()
        manager_instance.disconnect_user = AsyncMock()
        manager_instance.handle_message = AsyncMock(return_value=True)
        manager_instance.validate_message = Mock(return_value=True)
        manager_instance.send_message_to_user = AsyncMock(return_value=True)
        
        mock_manager.return_value = manager_instance
        yield manager_instance


@pytest.fixture
def mock_agent_service():
    """Mock agent service for WebSocket message processing."""
    with patch('app.services.agent_service_core.AgentService') as mock_service:
        service_instance = AsyncMock()
        service_instance.handle_websocket_message = AsyncMock()
        mock_service.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_security_service():
    """Mock security service for authentication."""
    with patch('app.services.security_service.SecurityService') as mock_service:
        service_instance = AsyncMock()
        service_instance.get_user_by_id = AsyncMock()
        service_instance.get_user = AsyncMock()
        mock_service.return_value = service_instance
        yield service_instance


@pytest.fixture
def clean_connection_manager():
    """Clean connection manager state between tests."""
    from app.routes.websocket_enhanced import connection_manager
    
    # Store original state
    original_sessions = connection_manager.active_sessions.copy()
    original_metadata = connection_manager.connection_metadata.copy()
    
    # Clear for test
    connection_manager.active_sessions.clear()
    connection_manager.connection_metadata.clear()
    
    yield connection_manager
    
    # Restore original state
    connection_manager.active_sessions = original_sessions
    connection_manager.connection_metadata = original_metadata


# Async test utilities
@pytest_asyncio.fixture
async def websocket_connection_context():
    """Context for WebSocket connection testing."""
    connections_to_cleanup = []
    
    async def create_connection(user_id: str, websocket=None):
        if websocket is None:
            websocket = Mock()
        
        from app.routes.websocket_enhanced import connection_manager
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, websocket, session_info)
        connections_to_cleanup.append((user_id, conn_id))
        return conn_id
    
    yield create_connection
    
    # Cleanup connections
    from app.routes.websocket_enhanced import connection_manager
    for user_id, conn_id in connections_to_cleanup:
        try:
            await connection_manager.remove_connection(user_id, conn_id)
        except:
            pass  # Ignore cleanup errors


# Test data generators
def generate_test_message(message_type: str = "ping", **kwargs) -> Dict[str, Any]:
    """Generate test WebSocket message."""
    message = {
        "type": message_type,
        "timestamp": 1640995200,  # Fixed timestamp for reproducible tests
    }
    
    if kwargs:
        message["payload"] = kwargs
    
    return message


def generate_invalid_messages() -> list:
    """Generate various invalid messages for testing."""
    return [
        "not json at all",
        '{"missing_type": true}',
        '{"type": ""}',
        '{"type": null}',
        '{"type": 123}',
        '',
        '{}',
        '{"type": "valid", "payload": "but malformed JSON syntax": invalid}',
    ]


def generate_error_response(code: str, message: str, recoverable: bool = True) -> Dict[str, Any]:
    """Generate error response message."""
    return {
        "type": "error",
        "payload": {
            "code": code,
            "error": message,
            "timestamp": 1640995200,
            "recoverable": recoverable,
            "help": f"Help text for {code}"
        }
    }


# Test environment configuration
def configure_test_environment():
    """Configure test environment variables."""
    import os
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("WEBSOCKET_ALLOWED_ORIGINS", "http://localhost:3000,https://localhost:3000")
    os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")


# Call configuration setup
configure_test_environment()


# Custom markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "websocket: WebSocket functionality tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "resilience: Resilience and recovery tests") 
    config.addinivalue_line("markers", "cors: CORS security tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "concurrent: Concurrency tests")


# Test collection and reporting
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file and function names
        if "websocket" in item.nodeid:
            item.add_marker(pytest.mark.websocket)
            
        if "integration" in item.name:
            item.add_marker(pytest.mark.integration)
            
        if "resilience" in item.name or "recovery" in item.name:
            item.add_marker(pytest.mark.resilience)
            
        if "cors" in item.name:
            item.add_marker(pytest.mark.cors)
            
        if "auth" in item.name:
            item.add_marker(pytest.mark.auth)
            
        if "concurrent" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.performance)


# Helpers for async testing
class AsyncContextManager:
    """Helper for async context management in tests."""
    
    def __init__(self, async_func):
        self.async_func = async_func
        
    async def __aenter__(self):
        return await self.async_func()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# WebSocket test utilities
class WebSocketTestUtils:
    """Utilities for WebSocket testing."""
    
    @staticmethod
    def create_mock_websocket_with_headers(headers: Dict[str, str]):
        """Create mock WebSocket with specific headers."""
        mock_ws = Mock()
        mock_ws.headers = headers
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws
        
    @staticmethod
    def create_mock_websocket_with_query_params(params: Dict[str, str]):
        """Create mock WebSocket with specific query parameters."""
        mock_ws = Mock()
        mock_ws.query_params = params
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws
        
    @staticmethod
    async def simulate_connection_lifecycle(user_id: str, connection_manager):
        """Simulate complete WebSocket connection lifecycle."""
        mock_websocket = Mock()
        session_info = {"user_id": user_id}
        
        # Connect
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        # Simulate activity
        if conn_id in connection_manager.connection_metadata:
            connection_manager.connection_metadata[conn_id]["message_count"] += 1
            
        # Disconnect
        await connection_manager.remove_connection(user_id, conn_id)
        
        return conn_id


@pytest.fixture
def websocket_test_utils():
    """Provide WebSocket test utilities."""
    return WebSocketTestUtils