"""
Unified Test Harness - Phase 2 System Testing Infrastructure

Business Value: $200K+ MRR protection through comprehensive test coverage
Provides reusable testing utilities for authentication, WebSocket, and service flows.
"""
import asyncio
import pytest
import json
import logging
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
# CLAUDE.md compliance: No mocks allowed in e2e tests - using real services only

from tests.e2e.config import (
    TestEnvironmentConfig,
    TestEnvironmentType,
    get_test_environment_config,
)
# Import IsolatedEnvironment for proper environment management
from dev_launcher.isolated_environment import get_env

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


class HarnessState:
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


class UnifiedE2ETestHarness:
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
        self.test_data = {}
        
        # Setup isolated environment as per CLAUDE.md
        self.setup_isolated_environment()
        
        # Setup environment configuration
        self.env_config = get_test_environment_config(env_type=environment or TestEnvironmentType.LOCAL)
        self.state = HarnessState(self.env_config)
        self.state.databases.harness = self
        self.project_root = Path.cwd()
        
        logger.info(f"Test Harness initialized for {self.env_config.environment_type.value} environment")
    
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
        if self.env_config and hasattr(self.env_config, 'ws_url'):
            return self.env_config.ws_url
        
        # Fallback to backend URL conversion
        backend_url = self.get_service_url("backend")
        return backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
    def get_database_url(self) -> str:
        """Get database URL based on environment."""
        # Use IsolatedEnvironment to get database URL
        db_url = self.get_environment_variable("DATABASE_URL")
        if db_url:
            return db_url
        
        return "sqlite+aiosqlite:///:memory:"  # Default for tests
    
    def create_chat_message(self, content: str, thread_id: str = None) -> Dict:
        """Create chat message for testing"""
        return self.create_websocket_message(
            "chat_message",
            content=content,
            thread_id=thread_id or str(uuid.uuid4())
        )
    
    # Real Service Integration Support (No Mocks as per CLAUDE.md)
    def get_auth_service_client(self):
        """Get real auth service client based on environment configuration."""
        auth_url = self.get_service_url("auth_service")
        # Return real HTTP client configured for auth service
        import httpx
        return httpx.AsyncClient(base_url=auth_url, timeout=30.0)
    
    def get_backend_service_client(self):
        """Get real backend service client based on environment configuration."""
        backend_url = self.get_service_url("backend")
        # Return real HTTP client configured for backend service  
        import httpx
        return httpx.AsyncClient(base_url=backend_url, timeout=30.0)
    
    async def create_real_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a real user using the auth service."""
        client = self.get_auth_service_client()
        try:
            response = await client.post("/users", json=user_data)
            response.raise_for_status()
            return response.json()
        finally:
            await client.aclose()
    
    async def get_real_websocket_connection(self, token: str):
        """Get real WebSocket connection to backend service."""
        import websockets
        ws_url = self.get_websocket_url()
        headers = self.create_auth_headers(token)
        return await websockets.connect(ws_url, extra_headers=headers)
    
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
    
    # Environment Management using IsolatedEnvironment as per CLAUDE.md
    def setup_isolated_environment(self) -> None:
        """Setup isolated environment for testing."""
        self.env = get_env()
        self.env.enable_isolation()
        # Set test environment variables
        self.env.set("TESTING", "1", "test_harness")
        self.env.set("ENVIRONMENT", "test", "test_harness")
        self.env.set("LOG_LEVEL", "WARNING", "test_harness")
    
    def get_environment_variable(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable using IsolatedEnvironment."""
        return self.env.get(key, default)
    
    def set_environment_variable(self, key: str, value: str) -> None:
        """Set environment variable using IsolatedEnvironment."""
        self.env.set(key, value, "test_harness")
    
    # Cleanup Support
    async def cleanup(self):
        """Cleanup test resources"""
        # Close any HTTP clients
        for client_attr in ['_auth_client', '_backend_client']:
            if hasattr(self, client_attr):
                client = getattr(self, client_attr)
                if client and hasattr(client, 'aclose'):
                    try:
                        await client.aclose()
                    except Exception:
                        pass  # Best effort cleanup
        
        self.test_data.clear()
        
        # Reset isolated environment
        if hasattr(self, 'env'):
            self.env.reset_to_original()
    
    # Factory methods for creating test harnesses
    @classmethod
    async def create_test_harness(cls, test_name: str = "unified_test"):
        """Create and start a complete test harness."""
        # Import here to avoid circular imports
        from tests.e2e.harness_complete import create_test_harness
        return await create_test_harness(test_name)
    
    @classmethod 
    async def create_minimal_harness(cls, test_name: str = "minimal_test"):
        """Create a minimal test harness without test data."""
        # Import here to avoid circular imports
        from tests.e2e.harness_complete import create_minimal_harness
        return await create_minimal_harness(test_name)


class AuthFlowHelper:
    """Specialized helper for authentication flow testing"""
    
    def __init__(self, harness: UnifiedE2ETestHarness):
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


# ACTUAL TEST FUNCTIONS - CLAUDE.md requires tests, not just helper classes
@pytest.mark.e2e
class TestUnifiedE2ETestHarness:
    """Test the Unified E2E Test Harness functionality using real services."""
    
    @pytest.fixture
    async def harness(self):
        """Create test harness instance."""
        harness = UnifiedE2ETestHarness()
        yield harness
        # Cleanup after test
        await harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_harness_initialization(self, harness):
        """Test harness initializes correctly with isolated environment."""
        # Test initialization
        assert harness.test_session_id is not None
        assert hasattr(harness, 'env')
        assert hasattr(harness, 'env_config')
        assert hasattr(harness, 'state')
        
        # Test isolated environment setup
        assert harness.env.is_isolation_enabled()
        assert harness.get_environment_variable("TESTING") == "1"
        assert harness.get_environment_variable("ENVIRONMENT") == "test"
    
    @pytest.mark.asyncio
    async def test_environment_variable_management(self, harness):
        """Test environment variable management through IsolatedEnvironment."""
        # Test setting variables
        harness.set_environment_variable("TEST_VAR", "test_value")
        assert harness.get_environment_variable("TEST_VAR") == "test_value"
        
        # Test default values
        assert harness.get_environment_variable("NON_EXISTENT", "default") == "default"
    
    @pytest.mark.asyncio
    async def test_service_url_configuration(self, harness):
        """Test service URL configuration for different environments."""
        # Test auth service URL
        auth_url = harness.get_service_url("auth_service")
        assert auth_url.startswith("http")
        assert "auth" in auth_url or "8081" in auth_url  # Docker default port
        
        # Test backend service URL  
        backend_url = harness.get_service_url("backend")
        assert backend_url.startswith("http")
        assert "8000" in backend_url or "backend" in backend_url
        
        # Test WebSocket URL
        ws_url = harness.get_websocket_url()
        assert ws_url.startswith("ws")
    
    @pytest.mark.asyncio
    async def test_test_data_management(self, harness):
        """Test test data creation and management."""
        # Test user creation
        user_data = harness.create_test_user()
        assert "id" in user_data
        assert "email" in user_data
        assert user_data["is_active"] is True
        
        # Test token creation
        tokens = harness.create_test_tokens()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "user_id" in tokens
        
        # Test auth headers
        headers = harness.create_auth_headers(tokens["access_token"])
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
    
    @pytest.mark.asyncio
    async def test_websocket_message_creation(self, harness):
        """Test WebSocket message creation."""
        # Test generic message
        msg = harness.create_websocket_message("test_type", data="test_data")
        assert msg["type"] == "test_type"
        assert "timestamp" in msg["payload"]
        assert "session_id" in msg["payload"]
        assert msg["payload"]["data"] == "test_data"
        
        # Test chat message
        chat_msg = harness.create_chat_message("Hello, World!")
        assert chat_msg["type"] == "chat_message"
        assert chat_msg["payload"]["content"] == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_service_client_creation(self, harness):
        """Test real service client creation."""
        # Test auth service client
        auth_client = harness.get_auth_service_client()
        assert hasattr(auth_client, 'post')
        assert hasattr(auth_client, 'get')
        assert hasattr(auth_client, 'aclose')
        
        # Test backend service client
        backend_client = harness.get_backend_service_client()
        assert hasattr(backend_client, 'post')
        assert hasattr(backend_client, 'get')
        assert hasattr(backend_client, 'aclose')
    
    @pytest.mark.asyncio
    async def test_cleanup_functionality(self, harness):
        """Test cleanup functionality."""
        # Store some test data
        harness.store_test_result("test_1", "result_1")
        assert len(harness.get_test_results()) > 0
        
        # Test cleanup
        await harness.cleanup()
        assert len(harness.get_test_results()) == 0
    
    @pytest.mark.asyncio
    async def test_performance_timer(self, harness):
        """Test performance timer functionality."""
        # Test successful timing
        async with harness.performance_timer(max_duration=1.0):
            await asyncio.sleep(0.1)  # Should not raise
        
        # Test timeout detection
        with pytest.raises(AssertionError, match="Operation took"):
            async with harness.performance_timer(max_duration=0.1):
                await asyncio.sleep(0.2)  # Should raise timeout error


@pytest.mark.e2e 
class TestAuthFlowHelper:
    """Test AuthFlowHelper functionality."""
    
    @pytest.fixture
    async def harness(self):
        """Create test harness instance."""
        harness = UnifiedE2ETestHarness()
        yield harness
        await harness.cleanup()
    
    @pytest.fixture 
    def auth_helper(self, harness):
        """Create auth flow helper."""
        return AuthFlowHelper(harness)
    
    @pytest.mark.asyncio
    async def test_login_scenario_creation(self, auth_helper):
        """Test login scenario creation."""
        scenario = auth_helper.create_login_scenario()
        
        assert "user" in scenario
        assert "tokens" in scenario
        assert "headers" in scenario
        assert "scenario_id" in scenario
        
        # Test user data
        assert scenario["user"]["is_active"] is True
        assert "@" in scenario["user"]["email"]
        
        # Test tokens
        assert scenario["tokens"]["access_token"].startswith("eyJ")
        assert scenario["tokens"]["refresh_token"].startswith("refresh-")
        
        # Test headers
        assert scenario["headers"]["Authorization"].startswith("Bearer ")
    
    @pytest.mark.asyncio
    async def test_multi_tab_scenario(self, auth_helper):
        """Test multi-tab scenario creation."""
        scenarios = auth_helper.create_multi_tab_scenario(tab_count=3)
        
        assert len(scenarios) == 3
        
        # All scenarios should have the same user but different tokens
        user_id = scenarios[0]["user"]["id"]
        for scenario in scenarios:
            assert scenario["user"]["id"] == user_id
            assert "tab_id" in scenario
            assert scenario["tokens"]["access_token"] is not None


class WebSocketHelper:
    """Specialized helper for WebSocket testing"""
    
    def __init__(self, harness: UnifiedE2ETestHarness):
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


@pytest.mark.e2e
class TestWebSocketHelperClass:
    """Test WebSocketHelper functionality."""
    
    @pytest.fixture
    async def harness(self):
        """Create test harness instance."""
        harness = UnifiedE2ETestHarness()
        yield harness
        await harness.cleanup()
    
    @pytest.fixture 
    def websocket_helper(self, harness):
        """Create websocket helper."""
        return WebSocketHelper(harness)
    
    @pytest.mark.asyncio
    async def test_connection_scenario_creation(self, websocket_helper):
        """Test WebSocket connection scenario creation."""
        # Create user tokens
        user_tokens = websocket_helper.harness.create_test_tokens()
        scenario = websocket_helper.create_connection_scenario(user_tokens)
        
        assert "ws_url" in scenario
        assert "headers" in scenario
        assert "test_messages" in scenario
        
        # Test WebSocket URL format
        assert scenario["ws_url"].startswith("ws")
        
        # Test headers
        assert "Authorization" in scenario["headers"]
        assert scenario["headers"]["Authorization"].startswith("Bearer ")
        
        # Test messages
        assert len(scenario["test_messages"]) == 3
        for msg in scenario["test_messages"]:
            assert "type" in msg
            assert "payload" in msg
    
    @pytest.mark.asyncio
    async def test_concurrent_scenario_creation(self, websocket_helper):
        """Test concurrent WebSocket scenario creation."""
        scenarios = websocket_helper.create_concurrent_scenario(user_count=2)
        
        assert len(scenarios) == 2
        
        for scenario in scenarios:
            assert "ws_url" in scenario
            assert "headers" in scenario
            assert "test_messages" in scenario
            assert "user_id" in scenario
            assert "connection_id" in scenario
        
        # Each scenario should have unique connection IDs
        connection_ids = [s["connection_id"] for s in scenarios]
        assert len(set(connection_ids)) == len(connection_ids)
