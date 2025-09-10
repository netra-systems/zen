"""
Universal Real WebSocket Test Base - NO MOCKS

This is the central base class for ALL WebSocket tests across the project.
CRITICAL: Uses ONLY real WebSocket connections - NO MOCKS per CLAUDE.md "MOCKS = Abomination"

Features:
- Real WebSocket connection management with Docker services
- Event validation for all 5 required agent events
- Concurrent connection testing (25+ sessions)
- Performance metrics collection
- Comprehensive error handling and retries

Business Value Justification:
1. Segment: Platform/Internal - Chat is King infrastructure  
2. Business Goal: Ensure WebSocket agent events deliver substantive chat value
3. Value Impact: Validates real-time AI interactions that drive 90% of platform value
4. Revenue Impact: Protects chat functionality that generates customer conversions

@compliance CLAUDE.md - WebSocket events enable substantive chat interactions
@compliance SPEC/core.xml - Real services over mocks for authentic testing
"""

import asyncio
import json
import logging
import time
import uuid
import warnings
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union, AsyncGenerator, Callable
import traceback

import pytest

# CRITICAL: Use real services - import from proper locations
from shared.isolated_environment import get_env
from test_framework.test_context import TestContext, TestUserContext
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType, ServiceHealth
from test_framework.websocket_helpers import (
    WebSocketTestHelpers, 
    WebSocketPerformanceMonitor,
    ensure_websocket_service_ready
)
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# CRITICAL: Always require real services - NO MOCKS per CLAUDE.md
def require_docker_services() -> None:
    """Require Docker services for all tests - fail fast if not available.
    
    CRITICAL: Per CLAUDE.md, MOCKS = Abomination. Tests must use real services.
    """
    try:
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        if not manager.is_docker_available():
            pytest.fail("Docker services required but not available. Start Docker and run: docker compose -f docker-compose.alpine-test.yml up -d")
    except Exception as e:
        pytest.fail(f"Docker services check failed: {e}. Ensure Docker is running.")

# Always require Docker for real tests
requires_docker = pytest.mark.usefixtures("ensure_docker_services")


# REMOVED: MockWebSocketConnection class
# Per CLAUDE.md: "MOCKS = Abomination" - Always use real services
# Tests must fail if Docker services are not available
# This ensures we test real WebSocket behavior, not mock approximations



# Suppress Docker warnings during testing
warnings.filterwarnings("ignore", message=".*docker.*", category=UserWarning)

logger = logging.getLogger(__name__)


@dataclass
class RealWebSocketTestConfig:
    """Configuration for real WebSocket tests."""
    backend_url: str = field(default_factory=lambda: _get_environment_backend_url())
    websocket_url: str = field(default_factory=lambda: _get_environment_websocket_url())
    connection_timeout: float = 15.0
    event_timeout: float = 10.0
    max_retries: int = 5


def _get_environment_backend_url() -> str:
    """Get backend URL from environment or fallback to localhost."""
    env = get_env()
    
    # Check for service orchestrator environment variables first
    test_backend_url = env.get('TEST_BACKEND_URL', None)
    if test_backend_url:
        return test_backend_url
    
    # Check for E2E environment variables
    e2e_backend_url = env.get('E2E_BACKEND_URL', None)
    if e2e_backend_url:
        return e2e_backend_url
    
    # Check for staging environment
    backend_staging_url = env.get('BACKEND_STAGING_URL', None)
    if backend_staging_url:
        return backend_staging_url
    
    # Fallback to localhost (will likely fail if services not running)
    return "http://localhost:8000"


def _get_environment_websocket_url() -> str:
    """Get WebSocket URL from environment or derive from backend URL."""
    env = get_env()
    
    # Check for service orchestrator environment variables first
    test_websocket_url = env.get('TEST_WEBSOCKET_URL', None)
    if test_websocket_url:
        return test_websocket_url
    
    # Check for E2E environment variables
    e2e_websocket_url = env.get('E2E_WEBSOCKET_URL', None)
    if e2e_websocket_url:
        return e2e_websocket_url
    
    # Derive from backend URL
    backend_url = _get_environment_backend_url()
    return backend_url.replace("http://", "ws://").replace("https://", "wss://")
    
    # Required WebSocket events for agent testing
    required_agent_events: Set[str] = field(default_factory=lambda: {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    })


@dataclass
class WebSocketConnectionPool:
    """Pool of real WebSocket connections for concurrent testing."""
    connections: List[Any] = field(default_factory=list)
    connection_ids: List[str] = field(default_factory=list)
    active_count: int = 0
    max_connections: int = 25
    
    async def add_connection(self, connection, connection_id: str = None):
        """Add a connection to the pool."""
        if len(self.connections) >= self.max_connections:
            raise ValueError(f"Connection pool at capacity ({self.max_connections})")
        
        if connection_id is None:
            connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        self.connections.append(connection)
        self.connection_ids.append(connection_id)
        self.active_count += 1
        
    async def remove_connection(self, connection):
        """Remove a connection from the pool."""
        if connection in self.connections:
            index = self.connections.index(connection)
            self.connections.pop(index)
            self.connection_ids.pop(index)
            self.active_count -= 1
            
            # Close the connection
            try:
                await WebSocketTestHelpers.close_test_connection(connection)
            except Exception:
                pass  # Ignore cleanup errors
    
    async def cleanup_all(self):
        """Clean up all connections in the pool."""
        cleanup_tasks = []
        for connection in self.connections:
            cleanup_tasks.append(self.remove_connection(connection))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.connections.clear()
        self.connection_ids.clear()
        self.active_count = 0


@dataclass
class EventValidationResult:
    """Results from WebSocket event validation."""
    success: bool
    events_captured: List[Dict[str, Any]]
    required_events_found: Set[str]
    missing_events: Set[str]
    extra_events: Set[str]
    total_events: int
    validation_duration: float
    error_message: Optional[str] = None


class RealWebSocketTestBase:
    """
    Universal base class for ALL WebSocket tests - uses ONLY real connections.
    
    CRITICAL FEATURES:
    - Automatic Docker service management
    - Real WebSocket connection establishment
    - Event validation for agent interactions
    - Concurrent connection testing
    - Performance metrics collection
    - Comprehensive error handling
    
    NO MOCKS - validates actual WebSocket functionality.
    """
    
    def __init__(self, config: Optional[RealWebSocketTestConfig] = None):
        """Initialize the real WebSocket test base."""
        self.config = config or RealWebSocketTestConfig()
        self.env = get_env()
        
        # Docker and service management
        self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        self.services_started = False
        
        # Connection management
        self.connection_pool = WebSocketConnectionPool()
        self.test_contexts: List[TestContext] = []
        
        # Event and performance tracking
        self.performance_monitor = WebSocketPerformanceMonitor()
        self.test_id = f"websocket_test_{uuid.uuid4().hex[:8]}"
        self.test_start_time: Optional[float] = None
        self.test_end_time: Optional[float] = None
        
        # Health and metrics
        self.service_health: Dict[str, ServiceHealth] = {}
        self.connection_metrics: Dict[str, Any] = {}
        
        logger.info(f"Initialized RealWebSocketTestBase with test_id: {self.test_id}")
    
    async def setup_docker_services(self) -> bool:
        """
        Set up Docker services for testing.
        
        Returns:
            True if services started successfully
        """
        if self.services_started:
            return True
        
        logger.info("Starting Docker services for WebSocket testing...")
        
        try:
            # Start backend and auth services
            services_to_start = ["backend", "auth"]
            
            await self.docker_manager.start_services_smart(
                services=services_to_start,
                wait_healthy=True
            )
            
            # Wait for services to be healthy
            max_health_wait = self.config.docker_startup_timeout
            health_start = time.time()
            
            while time.time() - health_start < max_health_wait:
                if await ensure_websocket_service_ready(
                    base_url=self.config.backend_url,
                    max_wait=10.0
                ):
                    self.services_started = True
                    logger.info("Docker services are healthy and ready")
                    return True
                
                await asyncio.sleep(2.0)
            
            logger.error(f"Services did not become healthy within {max_health_wait}s")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start Docker services: {e}")
            return False
    
    async def create_real_websocket_connection(
        self,
        endpoint: str = "/ws/test",
        headers: Optional[Dict[str, str]] = None,
        user_context: Optional[TestUserContext] = None
    ) -> Any:
        """
        Create a real WebSocket connection to the backend.
        
        Args:
            endpoint: WebSocket endpoint to connect to
            headers: Optional headers for authentication
            user_context: Optional user context for isolated testing
            
        Returns:
            Real WebSocket connection object
        """
        url = f"{self.config.websocket_url}{endpoint}"
        
        # Use authentication if provided
        if user_context and user_context.jwt_token:
            if not headers:
                headers = {}
            headers["Authorization"] = f"Bearer {user_context.jwt_token}"
        
        try:
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=url,
                headers=headers,
                timeout=self.config.connection_timeout,
                max_retries=self.config.max_retries
            )
            
            await self.connection_pool.add_connection(connection)
            logger.info(f"Created real WebSocket connection to {url}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create real WebSocket connection: {e}")
            raise ConnectionError(f"Could not establish real WebSocket connection: {e}")
    
    async def create_test_context(
        self,
        user_id: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> TestContext:
        """
        Create a TestContext with real WebSocket connection.
        
        Args:
            user_id: Optional user ID for testing
            jwt_token: Optional JWT token for authentication
            
        Returns:
            TestContext with real WebSocket capabilities
        """
        if not user_id:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Create user context
        user_context = TestUserContext(user_id=user_id)
        if jwt_token:
            user_context.jwt_token = jwt_token
        
        # Create TestContext
        test_context = TestContext(
            user_context=user_context,
            websocket_timeout=self.config.connection_timeout,
            event_timeout=self.config.event_timeout
        )
        
        self.test_contexts.append(test_context)
        return test_context
    
    async def validate_agent_events(
        self,
        test_context: TestContext,
        required_events: Optional[Set[str]] = None,
        timeout: float = 30.0
    ) -> EventValidationResult:
        """
        Validate that required agent events are received through real WebSocket.
        
        Args:
            test_context: TestContext to validate events for
            required_events: Set of required event types
            timeout: Maximum time to wait for events
            
        Returns:
            EventValidationResult with validation details
        """
        if required_events is None:
            required_events = self.config.required_agent_events.copy()
        
        start_time = time.time()
        
        try:
            # Wait for agent events through real WebSocket connection
            success = await test_context.wait_for_agent_events(
                required_events=required_events,
                timeout=timeout
            )
            
            validation_duration = time.time() - start_time
            captured_events = test_context.get_captured_events()
            
            # Analyze captured events
            captured_event_types = {event.get("type") for event in captured_events if event.get("type")}
            missing_events = required_events - captured_event_types
            extra_events = captured_event_types - required_events
            
            return EventValidationResult(
                success=success and len(missing_events) == 0,
                events_captured=captured_events,
                required_events_found=captured_event_types & required_events,
                missing_events=missing_events,
                extra_events=extra_events,
                total_events=len(captured_events),
                validation_duration=validation_duration
            )
            
        except Exception as e:
            validation_duration = time.time() - start_time
            logger.error(f"Agent event validation failed: {e}")
            
            return EventValidationResult(
                success=False,
                events_captured=[],
                required_events_found=set(),
                missing_events=required_events,
                extra_events=set(),
                total_events=0,
                validation_duration=validation_duration,
                error_message=str(e)
            )
    
    async def test_concurrent_connections(self, connection_count: int = 25) -> Dict[str, Any]:
        """
        Test multiple concurrent WebSocket connections.
        
        Args:
            connection_count: Number of concurrent connections to create
            
        Returns:
            Results dictionary with connection metrics
        """
        logger.info(f"Testing {connection_count} concurrent WebSocket connections")
        
        connection_tasks = []
        connection_results = []
        start_time = time.time()
        
        # Create concurrent connections
        for i in range(connection_count):
            task = asyncio.create_task(self._create_single_concurrent_connection(i))
            connection_tasks.append(task)
        
        # Wait for all connections to complete
        try:
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    connection_results.append({
                        "success": False,
                        "error": str(result)
                    })
                else:
                    connection_results.append(result)
        
        except Exception as e:
            logger.error(f"Concurrent connection test failed: {e}")
        
        total_duration = time.time() - start_time
        successful_connections = sum(1 for result in connection_results if result.get("success"))
        
        return {
            "total_connections": connection_count,
            "successful_connections": successful_connections,
            "failed_connections": connection_count - successful_connections,
            "success_rate": successful_connections / connection_count if connection_count > 0 else 0,
            "total_duration": total_duration,
            "average_connection_time": total_duration / connection_count if connection_count > 0 else 0,
            "connection_results": connection_results
        }
    
    async def _create_single_concurrent_connection(self, index: int) -> Dict[str, Any]:
        """Create a single connection for concurrent testing."""
        connection_start = time.time()
        
        try:
            # Create unique user context
            user_id = f"concurrent_user_{index}_{uuid.uuid4().hex[:6]}"
            test_context = await self.create_test_context(user_id=user_id)
            
            # Establish WebSocket connection
            await test_context.setup_websocket_connection(
                endpoint="/ws/test",
                auth_required=False
            )
            
            # Send a test message
            test_message = {
                "type": "ping",
                "user_id": user_id,
                "timestamp": time.time(),
                "test_id": self.test_id
            }
            
            await test_context.send_message(test_message)
            
            # Try to receive response
            try:
                response = await test_context.receive_message()
                message_received = True
            except asyncio.TimeoutError:
                response = None
                message_received = False
            
            connection_duration = time.time() - connection_start
            
            return {
                "success": True,
                "index": index,
                "user_id": user_id,
                "connection_duration": connection_duration,
                "message_received": message_received,
                "response": response
            }
            
        except Exception as e:
            connection_duration = time.time() - connection_start
            logger.error(f"Concurrent connection {index} failed: {e}")
            
            return {
                "success": False,
                "index": index,
                "connection_duration": connection_duration,
                "error": str(e)
            }
    
    async def cleanup_connections(self):
        """Clean up all WebSocket connections and test contexts."""
        logger.info("Cleaning up WebSocket connections...")
        
        # Clean up test contexts
        cleanup_tasks = []
        for context in self.test_contexts:
            cleanup_tasks.append(context.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clean up connection pool
        await self.connection_pool.cleanup_all()
        
        # Clear references
        self.test_contexts.clear()
    
    async def stop_docker_services(self):
        """Stop Docker services if they were started by this test."""
        if self.services_started:
            logger.info("Stopping Docker services...")
            try:
                await self.docker_manager.stop_services()
                self.services_started = False
            except Exception as e:
                logger.warning(f"Error stopping Docker services: {e}")
    
    @asynccontextmanager
    async def real_websocket_test_session(self):
        """
        Context manager for complete real WebSocket test session.
        
        Automatically handles:
        - Docker service startup
        - WebSocket connection management  
        - Performance monitoring
        - Cleanup
        """
        self.test_start_time = time.time()
        logger.info(f"Starting real WebSocket test session: {self.test_id}")
        
        try:
            # Start Docker services
            if not await self.setup_docker_services():
                raise RuntimeError("Failed to start Docker services for WebSocket testing")
            
            # Start performance monitoring
            self.performance_monitor.start_monitoring(self.test_id)
            
            yield self
            
        finally:
            # Record end time
            self.test_end_time = time.time()
            
            # Stop performance monitoring
            metrics = self.performance_monitor.stop_monitoring(self.test_id)
            if metrics:
                self.connection_metrics = metrics
            
            # Clean up connections
            await self.cleanup_connections()
            
            # Stop Docker services
            await self.stop_docker_services()
            
            logger.info(f"Completed real WebSocket test session: {self.test_id}")
    
    def get_test_metrics(self) -> Dict[str, Any]:
        """Get comprehensive test metrics."""
        duration = None
        if self.test_start_time and self.test_end_time:
            duration = self.test_end_time - self.test_start_time
        
        return {
            "test_id": self.test_id,
            "duration_seconds": duration,
            "services_started": self.services_started,
            "total_connections_created": self.connection_pool.active_count,
            "total_test_contexts": len(self.test_contexts),
            "connection_metrics": self.connection_metrics,
            "config": {
                "backend_url": self.config.backend_url,
                "websocket_url": self.config.websocket_url,
                "connection_timeout": self.config.connection_timeout,
                "concurrent_connections": self.config.concurrent_connections
            }
        }


# REMOVED: MockWebSocketTestBase class (lines 576-803)
# Per CLAUDE.md: "MOCKS = Abomination" - all tests must use real services
# Tests will fail if Docker services are not available (expected behavior)
# 
# The MockWebSocketTestBase class and MockWebSocketConnection have been completely removed.
# All tests must use RealWebSocketTestBase with actual Docker services.
# This ensures we validate real WebSocket behavior, not mock approximations.

# Note: If you see import errors for MockWebSocketTestBase, update your imports to use
# RealWebSocketTestBase directly, or call require_docker_services() to fail fast.


def get_websocket_test_base() -> RealWebSocketTestBase:
    """Get real WebSocket test base - no fallback to mocks.
    
    CRITICAL: Always returns RealWebSocketTestBase. Tests fail if Docker unavailable.
    Per CLAUDE.md: Real services > mocks for authentic testing.
    """
    require_docker_services()  # Fail fast if Docker not available
    logger.info("Using RealWebSocketTestBase with real Docker services")
    return RealWebSocketTestBase()


# Pytest fixtures for real WebSocket testing

@pytest.fixture
async def real_websocket_test_base():
    """Pytest fixture providing RealWebSocketTestBase instance."""
    test_base = RealWebSocketTestBase()
    
    async with test_base.real_websocket_test_session():
        yield test_base


@pytest.fixture
async def real_websocket_connection(real_websocket_test_base):
    """Pytest fixture providing a single real WebSocket connection."""
    connection = await real_websocket_test_base.create_real_websocket_connection()
    yield connection


@pytest.fixture
async def real_test_context(real_websocket_test_base):
    """Pytest fixture providing a TestContext with real WebSocket."""
    context = await real_websocket_test_base.create_test_context()
    await context.setup_websocket_connection(endpoint="/ws/test", auth_required=False)
    yield context


@pytest.fixture
async def multiple_real_test_contexts(real_websocket_test_base):
    """Pytest fixture providing multiple TestContexts with real WebSockets."""
    contexts = []
    for i in range(3):
        context = await real_websocket_test_base.create_test_context(
            user_id=f"multi_user_{i}_{uuid.uuid4().hex[:6]}"
        )
        await context.setup_websocket_connection(endpoint="/ws/test", auth_required=False)
        contexts.append(context)
    
    yield contexts


# Utility functions for common test patterns

async def assert_agent_events_received(
    test_context: TestContext,
    required_events: Optional[Set[str]] = None,
    timeout: float = 30.0
) -> None:
    """
    Assert that all required agent events are received.
    
    Args:
        test_context: TestContext to check
        required_events: Set of required events
        timeout: Timeout for waiting
    """
    if required_events is None:
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
    
    success = await test_context.wait_for_agent_events(
        required_events=required_events,
        timeout=timeout
    )
    
    if not success:
        validation = test_context.validate_agent_events(required_events)
        missing = validation["missing_events"]
        captured = validation["captured_events"]
        
        raise AssertionError(
            f"Missing required agent events: {missing}. "
            f"Captured events: {captured}"
        )


async def send_test_agent_request(
    test_context: TestContext,
    agent_name: str = "test_agent",
    task: str = "Perform a simple test task"
) -> Dict[str, Any]:
    """
    Send a test agent request and return the message sent.
    
    Args:
        test_context: TestContext to use
        agent_name: Name of the agent
        task: Task description
        
    Returns:
        The message that was sent
    """
    message = {
        "type": "agent_request",
        "agent_name": agent_name,
        "task": task,
        "user_id": test_context.user_context.user_id,
        "thread_id": test_context.user_context.thread_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await test_context.send_message(message)
    return message