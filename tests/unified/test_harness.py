"""
Unified Test Harness - Phase 2 System Testing Infrastructure

Business Value: $200K+ MRR protection through comprehensive test coverage
Provides reusable testing utilities for authentication, WebSocket, and service flows.
"""
import asyncio
import uuid
import time
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from pathlib import Path

from .test_environment_config import (
    get_test_environment_config,
    TestEnvironmentConfig,
    TestEnvironmentType
)

logger = logging.getLogger(__name__)


class ServiceConfig:
    """Configuration for a test service."""
    
    def __init__(self, name: str, host: str = "localhost", port: int = 8000, 
                 health_endpoint: str = "/health", startup_timeout: int = 30,
                 url: Optional[str] = None):
        self.name = name
        self.host = host
        self.port = port
        self.health_endpoint = health_endpoint
        self.startup_timeout = startup_timeout
        self.ready = False
        self.process: Optional[subprocess.Popen] = None
        self.url = url or f"http://{host}:{port}"


class DatabaseManager:
    """Manages database connections and setup for testing."""
    
    def __init__(self, harness, env_config: Optional[TestEnvironmentConfig] = None):
        self.harness = harness
        self.env_config = env_config
        self.initialized = False
    
    async def setup_databases(self) -> None:
        """Setup test databases."""
        self.initialized = True
    
    async def cleanup_databases(self) -> None:
        """Cleanup test databases."""
        self.initialized = False


class TestState:
    """State management for test harness."""
    
    def __init__(self, env_config: Optional[TestEnvironmentConfig] = None):
        self.env_config = env_config
        
        # Initialize services with environment-aware configuration
        if env_config:
            self.services: Dict[str, ServiceConfig] = {
                "auth_service": ServiceConfig(
                    "auth_service", 
                    url=env_config.services.auth
                ),
                "backend": ServiceConfig(
                    "backend", 
                    url=env_config.services.backend
                )
            }
        else:
            # Fallback to default configuration
            self.services: Dict[str, ServiceConfig] = {
                "auth_service": ServiceConfig("auth_service", port=8001),
                "backend": ServiceConfig("backend", port=8000)
            }
        
        self.databases = DatabaseManager(None, env_config)
        self.ready = False
        self.cleanup_tasks: List[callable] = []
        self.project_root = Path.cwd()


class UnifiedTestHarness:
    """
    Unified test harness for comprehensive system testing.
    Supports authentication, WebSocket, and service integration testing.
    Now with environment-aware configuration for test, dev, and staging.
    """
    
    def __init__(self, environment: Optional[TestEnvironmentType] = None):
        """Initialize unified test harness.
        
        Args:
            environment: Optional environment override (test, dev, staging)
        """
        self.test_session_id = str(uuid.uuid4())
        self.mock_services = {}
        self.test_data = {}
        
        # Setup environment configuration
        self.env_config = get_test_environment_config(environment=environment)
        self.state = TestState(self.env_config)
        self.state.databases.harness = self
        self.project_root = Path.cwd()
        
        logger.info(f"Test Harness initialized for {self.env_config.environment.value} environment")
    
    # Authentication Testing Support
    def create_test_user(self, user_id: str = None) -> Dict[str, str]:
        """Create test user data"""
        return {
            "id": user_id or str(uuid.uuid4()),
            "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "name": "Test User",
            "is_active": True
        }
    
    def create_test_tokens(self, user_id: str = None) -> Dict[str, str]:
        """Generate realistic test JWT tokens"""
        user_id = user_id or str(uuid.uuid4())
        return {
            "access_token": f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-{uuid.uuid4().hex[:16]}",
            "refresh_token": f"refresh-{uuid.uuid4().hex[:24]}",
            "user_id": user_id,
            "expires_in": 900
        }
    
    def create_auth_headers(self, token: str) -> Dict[str, str]:
        """Create authorization headers"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    # WebSocket Testing Support
    def create_websocket_message(self, msg_type: str, **payload) -> Dict:
        """Create standardized WebSocket test message"""
        return {
            "type": msg_type,
            "payload": {
                "timestamp": time.time(),
                "session_id": self.test_session_id,
                **payload
            }
        }
    
    def get_service_url(self, service_name: str) -> str:
        """Get URL for specific service based on environment."""
        service_config = self.state.services.get(service_name)
        if service_config:
            return service_config.url
        
        # Environment-aware fallback
        if self.env_config:
            service_urls_map = {
                "backend": self.env_config.services.backend,
                "auth": self.env_config.services.auth,
                "auth_service": self.env_config.services.auth,
                "frontend": self.env_config.services.frontend
            }
            if service_name in service_urls_map:
                return service_urls_map[service_name]
        
        raise ValueError(f"Service {service_name} not configured")
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL based on environment."""
        if self.env_config:
            return self.env_config.services.websocket
        
        # Fallback to backend URL conversion
        backend_url = self.get_service_url("backend")
        return backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
    def get_database_url(self) -> str:
        """Get database URL based on environment."""
        if self.env_config:
            return self.env_config.database.url
        
        return "sqlite+aiosqlite:///:memory:"  # Default for tests
    
    def create_chat_message(self, content: str, thread_id: str = None) -> Dict:
        """Create chat message for testing"""
        return self.create_websocket_message(
            "chat_message",
            content=content,
            thread_id=thread_id or str(uuid.uuid4())
        )
    
    # Service Mocking Support
    def setup_auth_service_mock(self) -> MagicMock:
        """Setup comprehensive auth service mock"""
        mock_service = MagicMock()
        self._configure_auth_methods(mock_service)
        self.mock_services["auth"] = mock_service
        return mock_service
    
    def _configure_auth_methods(self, mock_service):
        """Configure auth service methods - under 8 lines"""
        mock_service.validate_token = AsyncMock(return_value=True)
        mock_service.refresh_tokens = AsyncMock()
        mock_service.logout = AsyncMock(return_value=True)
        mock_service.get_user = AsyncMock()
    
    def setup_websocket_manager_mock(self) -> MagicMock:
        """Setup WebSocket manager mock"""
        mock_manager = MagicMock()
        self._configure_websocket_methods(mock_manager)
        self.mock_services["websocket"] = mock_manager
        return mock_manager
    
    def _configure_websocket_methods(self, mock_manager):
        """Configure WebSocket manager methods"""
        mock_manager.connect_user = AsyncMock()
        mock_manager.disconnect_user = AsyncMock()
        mock_manager.send_message = AsyncMock()
        mock_manager.broadcast = AsyncMock()
    
    # Performance Testing Support
    @asynccontextmanager
    async def performance_timer(self, max_duration: float = 5.0):
        """Context manager for performance testing"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if duration > max_duration:
                raise AssertionError(f"Operation took {duration}s, max {max_duration}s")
    
    def assert_fast_execution(self, start_time: float, max_seconds: float = 5.0):
        """Assert operation completed within time limit"""
        duration = time.time() - start_time
        assert duration < max_seconds, f"Execution took {duration}s, max {max_seconds}s"
    
    # Error Simulation Support
    def simulate_auth_failure(self, error_type: str = "invalid_token"):
        """Simulate authentication failure scenarios"""
        error_configs = {
            "invalid_token": ValueError("Invalid token"),
            "expired_token": ValueError("Token expired"),
            "network_error": ConnectionError("Network timeout"),
            "service_unavailable": Exception("Auth service unavailable")
        }
        return error_configs.get(error_type, Exception("Unknown error"))
    
    def simulate_websocket_error(self, error_type: str = "connection_lost"):
        """Simulate WebSocket error scenarios"""
        error_configs = {
            "connection_lost": ConnectionError("WebSocket connection lost"),
            "invalid_message": json.JSONDecodeError("Invalid JSON", "", 0),
            "auth_timeout": TimeoutError("Authentication timeout"),
            "server_error": Exception("WebSocket server error")
        }
        return error_configs.get(error_type, Exception("WebSocket error"))
    
    # Test Data Management
    def store_test_result(self, test_name: str, result: Any):
        """Store test result for analysis"""
        self.test_data[test_name] = {
            "result": result,
            "timestamp": time.time(),
            "session": self.test_session_id
        }
    
    def get_test_results(self) -> Dict[str, Any]:
        """Get all test results from session"""
        return self.test_data.copy()
    
    # Cleanup Support
    async def cleanup(self):
        """Cleanup test resources"""
        for service_name, mock_service in self.mock_services.items():
            if hasattr(mock_service, 'cleanup'):
                try:
                    await mock_service.cleanup()
                except Exception:
                    pass  # Best effort cleanup
        
        self.mock_services.clear()
        self.test_data.clear()


class AuthFlowTestHelper:
    """Specialized helper for authentication flow testing"""
    
    def __init__(self, harness: UnifiedTestHarness):
        self.harness = harness
        self.auth_scenarios = []
    
    def create_login_scenario(self, user_email: str = None) -> Dict:
        """Create complete login test scenario"""
        user_data = self.harness.create_test_user()
        if user_email:
            user_data["email"] = user_email
        
        tokens = self.harness.create_test_tokens(user_data["id"])
        headers = self.harness.create_auth_headers(tokens["access_token"])
        
        return {
            "user": user_data,
            "tokens": tokens,
            "headers": headers,
            "scenario_id": str(uuid.uuid4())
        }
    
    def create_multi_tab_scenario(self, tab_count: int = 2) -> List[Dict]:
        """Create multi-tab authentication scenario"""
        base_user = self.harness.create_test_user()
        scenarios = []
        
        for i in range(tab_count):
            tokens = self.harness.create_test_tokens(base_user["id"])
            headers = self.harness.create_auth_headers(tokens["access_token"])
            scenarios.append({
                "user": base_user,
                "tokens": tokens,
                "headers": headers,
                "tab_id": f"tab-{i+1}"
            })
        
        return scenarios


class WebSocketTestHelper:
    """Specialized helper for WebSocket testing"""
    
    def __init__(self, harness: UnifiedTestHarness):
        self.harness = harness
        self.connection_scenarios = []
    
    def create_connection_scenario(self, user_tokens: Dict) -> Dict:
        """Create WebSocket connection test scenario"""
        return {
            "ws_url": self.harness.get_websocket_url(),
            "headers": self.harness.create_auth_headers(user_tokens["access_token"]),
            "test_messages": [
                self.harness.create_chat_message("Hello"),
                self.harness.create_chat_message("Test message"),
                self.harness.create_websocket_message("ping")
            ]
        }
    
    def create_concurrent_scenario(self, user_count: int = 3) -> List[Dict]:
        """Create concurrent connection test scenario"""
        scenarios = []
        
        for i in range(user_count):
            user_data = self.harness.create_test_user()
            tokens = self.harness.create_test_tokens(user_data["id"])
            scenario = self.create_connection_scenario(tokens)
            scenario["user_id"] = user_data["id"]
            scenario["connection_id"] = f"conn-{i+1}"
            scenarios.append(scenario)
        
        return scenarios