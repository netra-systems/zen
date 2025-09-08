"""
Frontend Tests Configuration

Configures pytest for frontend integration tests with proper environment setup,
fixtures, and test categorization following SSOT patterns.
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["NODE_ENV"] = "test"

# Default test environment configuration
TEST_ENV_DEFAULTS = {
    "NEXT_PUBLIC_API_URL": "http://localhost:8000",
    "NEXT_PUBLIC_WS_URL": "ws://localhost:8000/ws", 
    "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081",
    "NEXT_PUBLIC_ENVIRONMENT": "test"
}

# Set default environment variables if not already set
for key, value in TEST_ENV_DEFAULTS.items():
    if key not in os.environ:
        os.environ[key] = value


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment for frontend integration tests."""
    # Ensure test environment is properly configured
    assert os.environ.get("TESTING") == "true", "Test environment not properly configured"
    
    yield
    
    # Cleanup after tests
    pass


@pytest.fixture
def frontend_api_base():
    """Provide frontend API base URL for tests."""
    return os.environ.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")


@pytest.fixture
def frontend_ws_url():
    """Provide frontend WebSocket URL for tests.""" 
    return os.environ.get("NEXT_PUBLIC_WS_URL", "ws://localhost:8000/ws")


@pytest.fixture
def frontend_auth_base():
    """Provide frontend auth service URL for tests."""
    return os.environ.get("NEXT_PUBLIC_AUTH_URL", "http://localhost:8081")


# Test markers for categorization
pytest_plugins = []

def pytest_configure(config):
    """Configure test markers."""
    config.addinivalue_line("markers", "frontend_integration: Frontend integration tests")
    config.addinivalue_line("markers", "api_integration: API integration tests")
    config.addinivalue_line("markers", "websocket_integration: WebSocket integration tests")
    config.addinivalue_line("markers", "auth_integration: Authentication integration tests")
    config.addinivalue_line("markers", "routing_integration: Routing integration tests")
    config.addinivalue_line("markers", "session_integration: Session management integration tests")
    config.addinivalue_line("markers", "realtime_integration: Real-time messaging integration tests")
    config.addinivalue_line("markers", "ux_integration: User experience integration tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their module and class names."""
    for item in items:
        # Mark all frontend tests
        if "frontend" in item.fspath.basename:
            item.add_marker(pytest.mark.frontend_integration)
        
        # Mark specific integration types
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api_integration)
        elif "websocket" in item.name.lower():
            item.add_marker(pytest.mark.websocket_integration)
        elif "auth" in item.name.lower():
            item.add_marker(pytest.mark.auth_integration)
        elif "routing" in item.name.lower():
            item.add_marker(pytest.mark.routing_integration)
        elif "session" in item.name.lower():
            item.add_marker(pytest.mark.session_integration)
        elif "realtime" in item.name.lower() or "message" in item.name.lower():
            item.add_marker(pytest.mark.realtime_integration)
        elif "ux" in item.name.lower() or "experience" in item.name.lower():
            item.add_marker(pytest.mark.ux_integration)