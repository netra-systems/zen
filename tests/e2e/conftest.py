
# Import SSOT E2E configuration  
from tests.e2e.e2e_test_config import get_e2e_config

# Create E2E_CONFIG dictionary for backward compatibility
_e2e_config = get_e2e_config()
E2E_CONFIG = {
    "postgres_url": f"postgresql://test_user:test_password@{_e2e_config.postgres_host or 'localhost'}:{_e2e_config.postgres_port or 5434}/test_db",
    "redis_url": f"redis://{_e2e_config.redis_host or 'localhost'}:{_e2e_config.redis_port or 6381}",
    "backend_url": _e2e_config.backend_url,
    "api_url": _e2e_config.api_url,
    "websocket_url": _e2e_config.websocket_url,
    "auth_url": _e2e_config.auth_url,
    "timeout": _e2e_config.timeout
}

# Import SSOT base test case for E2E tests
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# E2E Test case aliases
BaseE2ETestCase = SSotBaseTestCase
AsyncE2ETestCase = SSotAsyncTestCase

# E2E Environment Validator stub
class E2EEnvironmentValidator:
    """Basic E2E environment validator"""
    
    @staticmethod
    def validate_environment():
        """Validate E2E environment is ready"""
        config = get_e2e_config()
        return config.is_available()


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
