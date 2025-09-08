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

"""
Mock fixtures for fast unit testing without external dependencies.

This module contains lightweight mock fixtures for:
- Redis client and manager mocks
- ClickHouse client mocks  
- WebSocket manager mocks
- Service layer mocks
- FastAPI application with mocked dependencies

Memory Impact: LOW - Simple mock objects with minimal memory allocation
Use these for unit tests that need fast execution without real services.
"""
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from shared.isolated_environment import get_env

# CRITICAL: Do NOT import heavy backend modules at module level
# This causes Docker to crash on Windows during pytest collection
# These will be imported lazily when needed inside fixtures

# Import availability checks with lazy loading
def _fastapi_available():
    """Check if FastAPI is available without importing during collection."""
    try:
        import fastapi
        import fastapi.testclient
        return True
    except ImportError:
        return False

def _lazy_import_fastapi():
    """Lazy import FastAPI components to avoid collection phase overhead."""
    if _fastapi_available():
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        return FastAPI, TestClient
    return None, None

# Memory profiling decorator
def memory_profile(description: str = "", impact: str = "LOW"):
    """Decorator to track memory usage of mock fixtures.""" 
    def decorator(func):
        func._memory_description = description
        func._memory_impact = impact
        return func
    return decorator

# =============================================================================
# REDIS MOCK FIXTURES
# Memory Impact: LOW - Simple async mock objects
# =============================================================================

@pytest.fixture
@memory_profile("Redis client mock for fast testing without network dependency", "LOW")
async def mock_redis_client():
    """Common Redis client mock for all tests with proper async cleanup.
    
    Memory Impact: LOW - Single mock object with async methods
    Use for: Unit tests requiring Redis-like interface without connection overhead
    """
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    mock.ping = AsyncMock(return_value=True)
    mock.aclose = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)
    
    try:
        yield mock
    finally:
        # Ensure proper cleanup of mock Redis resources
        try:
            await mock.aclose()
        except Exception:
            pass
        try:
            await mock.close()  
        except Exception:
            pass

@pytest.fixture
@memory_profile("Redis manager mock to prevent test interference and external dependencies", "LOW")
async def mock_redis_manager():
    """Common Redis manager mock with proper cleanup.
    
    Memory Impact: LOW - Mock manager with standard interface
    Use for: Unit tests requiring Redis caching interface without setup overhead
    """
    mock = MagicMock()
    mock.enabled = True
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    mock.close = AsyncMock(return_value=None)
    mock.cleanup = AsyncMock(return_value=None)
    
    try:
        yield mock
    finally:
        # Proper cleanup for Redis manager
        try:
            await mock.cleanup()
        except Exception:
            pass
        try:
            await mock.close()
        except Exception:
            pass

# =============================================================================
# CLICKHOUSE MOCK FIXTURES
# Memory Impact: LOW - Database interface mock
# =============================================================================

@pytest.fixture
@memory_profile("ClickHouse database mock for fast testing without external database dependency", "LOW")
def mock_clickhouse_client():
    """Common ClickHouse client mock.
    
    Memory Impact: LOW - Simple database interface mock
    Use for: Unit tests requiring analytics database interface without connection setup
    """
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value=None)
    mock.fetch = AsyncMock(return_value=[])
    mock.insert_data = AsyncMock(return_value=None)
    mock.command = AsyncMock(return_value=None)
    mock.ping = AsyncMock(return_value=True)
    return mock

# =============================================================================
# WEBSOCKET MOCK FIXTURES  
# Memory Impact: LOW - WebSocket interface mock
# =============================================================================

@pytest.fixture
@memory_profile("WebSocket infrastructure mock for unit tests without real connections", "LOW")
async def mock_websocket_manager():
    """WebSocket manager mock for unit testing.
    
    Memory Impact: LOW - WebSocket interface mock with connection tracking
    Use for: Unit tests requiring WebSocket functionality without network overhead
    """
    mock = MagicMock()
    mock.active_connections = {}
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.send_message = AsyncMock(return_value=None)
    mock.broadcast = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    mock.close_all_connections = AsyncMock(return_value=None)
    mock.cleanup = AsyncMock(return_value=None)
    
    try:
        yield mock
    finally:
        # Proper WebSocket manager cleanup
        try:
            await mock.close_all_connections()
        except Exception:
            pass
        try:
            await mock.cleanup()
        except Exception:
            pass
        try:
            await mock.shutdown()
        except Exception:
            pass

# =============================================================================
# SERVICE LAYER MOCK FIXTURES
# Memory Impact: LOW - Simple service interface mocks
# =============================================================================

@pytest.fixture
@memory_profile("LLM service mock for fast testing without API calls or rate limits", "LOW")
def mock_llm_manager():
    """LLM manager mock for testing without API calls.
    
    Memory Impact: LOW - Simple service interface mock
    Use for: Unit tests requiring LLM interface without external API calls
    """
    mock = TestWebSocketConnection()  # Real implementation
    mock.get_llm = MagicMock(return_value=TestWebSocketConnection())  # Real implementation
    return mock

@pytest.fixture
@memory_profile("Background task isolation to prevent real tasks during testing", "LOW")
def mock_background_task_manager():
    """Background task manager mock.
    
    Memory Impact: LOW - Task management interface mock
    Use for: Unit tests requiring background task interface without actual execution
    """
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
@memory_profile("Cryptographic key isolation for security testing without real keys", "LOW")
def mock_key_manager():
    """Key manager mock for security testing.
    
    Memory Impact: LOW - Security interface mock
    Use for: Unit tests requiring cryptographic operations without real key management
    """
    mock = MagicMock()
    mock.load_from_settings = MagicMock(return_value=mock)
    return mock

@pytest.fixture
@memory_profile("Security service mock for auth testing without real token validation", "LOW")
def mock_security_service():
    """Security service mock for authentication testing.
    
    Memory Impact: LOW - Auth interface mock
    Use for: Unit tests requiring security validation without real authentication
    """
    return MagicMock()
@pytest.fixture
@memory_profile("Tool dispatcher mock for agent testing without real tool execution", "LOW")
def mock_tool_dispatcher():
    """Tool dispatcher mock for agent testing.
    
    Memory Impact: LOW - Tool interface mock
    Use for: Unit tests requiring tool execution interface without real operations
    """
    return MagicMock()
@pytest.fixture
@memory_profile("Agent supervisor mock for testing without spawning real agents", "LOW")
def mock_agent_supervisor():
    """Agent supervisor mock for testing.
    
    Memory Impact: LOW - Agent management interface mock
    Use for: Unit tests requiring agent coordination without real agent spawning
    """
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
@memory_profile("Agent service mock for testing without LLM agent execution", "LOW")
def mock_agent_service():
    """Agent service mock for testing.
    
    Memory Impact: LOW - Agent service interface mock
    Use for: Unit tests requiring agent service interface without LLM execution
    """
    return MagicMock()
# =============================================================================
# FASTAPI APPLICATION MOCK FIXTURES
# Memory Impact: MEDIUM - Complete FastAPI app with all mocked dependencies
# =============================================================================

@pytest.fixture
@memory_profile("FastAPI application with all mocked dependencies for unit testing", "MEDIUM")
def app(
    mock_redis_manager,
    mock_clickhouse_client,
    mock_llm_manager,
    mock_websocket_manager,
    mock_background_task_manager,
    mock_key_manager,
    mock_security_service,
    mock_tool_dispatcher,
    mock_agent_supervisor,
    mock_agent_service,
):
    """FastAPI application with mocked dependencies for unit testing.
    
    Memory Impact: MEDIUM - Full FastAPI app with dependency injection
    Use for: Integration tests requiring FastAPI app without real service connections
    """
    FastAPI, TestClient = _lazy_import_fastapi()
    
    if not FastAPI:
        pytest.skip("FastAPI not available")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.redis_manager = mock_redis_manager
        app.state.clickhouse_client = mock_clickhouse_client
        app.state.llm_manager = mock_llm_manager
        app.state.background_task_manager = mock_background_task_manager
        app.state.key_manager = mock_key_manager
        app.state.security_service = mock_security_service
        app.state.tool_dispatcher = mock_tool_dispatcher
        app.state.agent_supervisor = mock_agent_supervisor
        app.state.agent_service = mock_agent_service
        yield

    app = FastAPI(lifespan=lifespan)

    # Only include routes if they can be imported
    try:
        from netra_backend.app.routes.websocket_secure import router as websockets_router
        app.include_router(websockets_router)
    except ImportError:
        pass

    try:
        from netra_backend.app.routes.auth import router as auth_router
        app.include_router(auth_router, prefix="/auth")
    except ImportError:
        pass

    return app

@pytest.fixture
@memory_profile("FastAPI test client with mocked app", "MEDIUM")
def client(app):
    """FastAPI test client for unit testing.
    
    Memory Impact: MEDIUM - HTTP test client with mocked app
    Use for: HTTP API unit tests without real service dependencies
    """
    FastAPI, TestClient = _lazy_import_fastapi()
    
    if not TestClient:
        pytest.skip("FastAPI not available")
    return TestClient(app)

# =============================================================================
# AUTHENTICATION MOCK FIXTURES
# Memory Impact: LOW - Simple auth mocks
# =============================================================================

@pytest.fixture
@memory_profile("Mock auth headers for testing without real token validation", "LOW")
def auth_headers(test_user):
    """Mock authentication headers for testing.
    
    Memory Impact: LOW - Simple header dict
    Use for: Unit tests requiring auth headers without JWT token validation
    """
    try:
        # Use proper JWT test helpers instead of direct auth imports
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        jwt_helper = JWTTestHelper()
        token = jwt_helper.create_access_token(test_user.id, test_user.email)
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        # Return mock headers if test helpers not available
        return {"Authorization": "Bearer mock-token"}

@pytest.fixture
@memory_profile("Mock auth headers with realistic token", "LOW") 
def auth_headers_v2(test_user_v2):
    """Enhanced auth headers fixture with realistic tokens.
    
    Memory Impact: LOW - Auth header dict with UUID-based token
    Use for: Unit tests requiring more realistic auth tokens
    """
    try:
        # Use proper JWT test helpers instead of direct auth imports
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        jwt_helper = JWTTestHelper()
        token = jwt_helper.create_access_token(test_user_v2.id, test_user_v2.email)
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        # Return mock headers with more realistic token
        import uuid
        mock_token = f"test_token_{uuid.uuid4().hex[:16]}"
        return {"Authorization": f"Bearer {mock_token}"}

# =============================================================================
# MEMORY TRACKING FOR MOCK FIXTURES
# Memory Impact: LOW - Simple tracking utility
# =============================================================================

@pytest.fixture
@memory_profile("Memory tracker for mock fixture performance testing", "LOW")
async def mock_memory_tracker():
    """Create memory tracker for mock fixture performance testing.
    
    This fixture provides a simple memory tracking utility for monitoring
    mock fixture overhead and ensuring they remain lightweight.
    
    Memory Impact: LOW - Simple tracking without real process monitoring
    
    Yields:
        MockMemoryTracker: Mock memory tracking utility
    """
    class MockMemoryTracker:
        def __init__(self):
            self.initial_memory = 0
            self.measurements = []
            self.mock_mode = True
            
        def start_tracking(self):
            """Start memory tracking (mocked)."""
            self.initial_memory = 10.0  # Mock initial memory (MB)
                
        def measure(self, label: str = "") -> float:
            """Take memory measurement (mocked)."""
            # Simulate small memory increase for mocks
            current = self.initial_memory + len(self.measurements) * 0.1
            delta = current - self.initial_memory
            self.measurements.append({'label': label, 'memory_mb': current, 'delta_mb': delta})
            return current
            
        def get_memory_increase(self) -> float:
            """Get total memory increase since tracking started (mocked)."""
            # Mock fixtures should have minimal memory increase
            return len(self.measurements) * 0.1
    
    tracker = MockMemoryTracker()
    tracker.start_tracking()
    yield tracker

# =============================================================================
# CONCURRENT TESTING WITH MOCKS
# Memory Impact: LOW - Simple concurrent test utility
# =============================================================================

@pytest.fixture
@memory_profile("Mock concurrent isolation test environment", "LOW") 
async def mock_concurrent_isolation_test():
    """Create mock environment for testing concurrent user isolation.
    
    This fixture sets up a mock environment for testing that multiple users
    can operate concurrently without data leakage or interference.
    
    Memory Impact: LOW - Mock concurrent testing without real resources
    
    Yields:
        Callable: Function to run mock concurrent isolation tests
    """
    async def run_mock_concurrent_test(
        user_count: int = 3,
        operations_per_user: int = 5,
        test_function: callable = None
    ):
        """Run concurrent test with mocked users.
        
        Args:
            user_count: Number of concurrent users
            operations_per_user: Operations per user
            test_function: Test function to run for each user
            
        Returns:
            List: Results from all concurrent operations
        """
        if not test_function:
            # Default mock test function
            async def default_mock_test(user_context, operation_id):
                # Simulate some async work
                await asyncio.sleep(0.01) 
                return {
                    'user_id': user_context.user_id,
                    'operation_id': operation_id,
                    'success': True,
                    'mock': True
                }
            test_function = default_mock_test
        
        # Import user context from base
        from tests.conftest_base import UserExecutionContext
        import uuid
        
        # Create mock user contexts
        user_contexts = []
        for i in range(user_count):
            context = UserExecutionContext(
                user_id=f"mock_concurrent_test_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"mock_thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"mock_run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"mock_req_{i}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(context)
        
        # Run concurrent operations with mocks
        tasks = []
        for user_context in user_contexts:
            for op_id in range(operations_per_user):
                task = asyncio.create_task(
                    test_function(user_context, op_id)
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            raise Exception(f"Mock concurrent test failed with exceptions: {exceptions}")
        
        return results
    
    yield run_mock_concurrent_test