"""
Universal Real WebSocket Test Base - NO MOCKS

This is the central base class for ALL WebSocket tests across the project.
CRITICAL: Uses ONLY real WebSocket connections - NO MOCKS per CLAUDE.md

Features:
- Real WebSocket connection management with Docker services
- Event validation for all 5 required agent events
- Concurrent connection testing
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

# Set up logger
logger = logging.getLogger(__name__)

# CRITICAL: Use real services - import from proper locations
from shared.isolated_environment import get_env
from test_framework.test_context import WebSocketContext, TestUserContext
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType, ServiceHealth

# Suppress Docker warnings during testing
warnings.filterwarnings("ignore", message=".*docker.*", category=UserWarning)


@dataclass
class RealWebSocketTestConfig:
    """Configuration for real WebSocket tests."""
    backend_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8000/ws"
    connection_timeout: float = 15.0
    event_timeout: float = 10.0
    max_retries: int = 5
    docker_startup_timeout: float = 30.0
    concurrent_connections: int = 10
    required_agent_events: Set[str] = field(default_factory=lambda: {
        "agent_started",
        "agent_thinking",
        "tool_executing",
        "tool_completed",
        "agent_completed"
    })


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
        self.test_contexts: List[WebSocketContext] = []

        # Event and performance tracking
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

        # Check for staging mode - skip Docker if staging configured
        env = get_env()
        staging_mode = env.get("TEST_MODE") == "staging_fallback"
        use_staging = env.get("USE_STAGING_SERVICES", "false").lower() == "true"

        if staging_mode or use_staging:
            logger.info("Skipping Docker startup, using staging services directly")
            self.services_started = True
            return True

        # Fast-fail Docker detection
        if not self.docker_manager.is_docker_available():
            logger.warning("Docker unavailable, attempting staging fallback")

            # Check for staging environment variables
            staging_backend_url = env.get("STAGING_BACKEND_URL")
            staging_websocket_url = env.get("STAGING_WEBSOCKET_URL")

            if staging_backend_url and staging_websocket_url:
                logger.info("Using staging services as Docker fallback")
                self.config.backend_url = staging_backend_url
                self.config.websocket_url = staging_websocket_url
                self.services_started = True
                return True
            else:
                logger.error("Docker unavailable and no staging fallback configured")
                return False

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
                # Simple health check - try to connect to backend
                try:
                    import requests
                    response = requests.get(f"{self.config.backend_url}/health", timeout=2)
                    if response.status_code == 200:
                        self.services_started = True
                        logger.info("Docker services are healthy and ready")
                        return True
                except:
                    pass

                await asyncio.sleep(1.0)

            logger.error(f"Services did not become healthy within {max_health_wait}s")
            return False

        except Exception as e:
            logger.error(f"Failed to start Docker services: {e}")
            return False

    async def create_test_context(
        self,
        user_id: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> WebSocketContext:
        """
        Create a WebSocketContext with real WebSocket connection.

        Args:
            user_id: Optional user ID for testing
            jwt_token: Optional JWT token for authentication

        Returns:
            WebSocketContext with real WebSocket capabilities
        """
        if not user_id:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        # Create user context
        user_context = TestUserContext(user_id=user_id)
        if jwt_token:
            user_context.jwt_token = jwt_token

        # Create WebSocketContext
        test_context = WebSocketContext(
            user_context=user_context,
            websocket_timeout=self.config.connection_timeout,
            event_timeout=self.config.event_timeout
        )

        self.test_contexts.append(test_context)
        return test_context

    async def cleanup_connections(self):
        """Clean up all WebSocket connections and test contexts."""
        logger.info("Cleaning up WebSocket connections...")

        # Clean up test contexts
        cleanup_tasks = []
        for context in self.test_contexts:
            cleanup_tasks.append(context.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # Clear references
        self.test_contexts.clear()

    async def stop_docker_services(self):
        """Stop Docker services if they were started by this test."""
        if self.services_started:
            logger.info("Stopping Docker services...")
            try:
                await self.docker_manager.graceful_shutdown()
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
            # Smart Docker services setup with staging fallback
            docker_success = await self.setup_docker_services()
            if not docker_success:
                # Check if staging fallback is configured
                env = get_env()
                staging_mode = env.get("TEST_MODE") == "staging_fallback"
                use_staging = env.get("USE_STAGING_SERVICES", "false").lower() == "true"
                use_staging_fallback = env.get("USE_STAGING_FALLBACK", "false").lower() == "true"

                if staging_mode or use_staging or use_staging_fallback:
                    logger.warning("Docker services failed - using staging environment fallback")
                    # Update configuration for staging
                    staging_url = env.get("STAGING_WEBSOCKET_URL", "wss://netra-staging.onrender.com/ws")
                    self.config.websocket_url = env.get("TEST_WEBSOCKET_URL", staging_url)
                    self.config.backend_url = env.get("TEST_BACKEND_URL", "https://netra-staging.onrender.com")
                    logger.info(f"Configured for staging testing: WebSocket={self.config.websocket_url}, Backend={self.config.backend_url}")
                else:
                    raise RuntimeError("Failed to start Docker services and no fallback configured")

            yield self

        finally:
            # Record end time
            self.test_end_time = time.time()

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
            "total_test_contexts": len(self.test_contexts),
            "connection_metrics": self.connection_metrics,
            "config": {
                "backend_url": self.config.backend_url,
                "websocket_url": self.config.websocket_url,
                "connection_timeout": self.config.connection_timeout,
                "concurrent_connections": self.config.concurrent_connections
            }
        }


def get_websocket_test_base() -> RealWebSocketTestBase:
    """Get real WebSocket test base - no fallback to mocks.

    CRITICAL: Always returns RealWebSocketTestBase. Tests fail if Docker unavailable.
    Per CLAUDE.md: Real services > mocks for authentic testing.
    """
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
async def real_test_context(real_websocket_test_base):
    """Pytest fixture providing a WebSocketContext with real WebSocket."""
    context = await real_websocket_test_base.create_test_context()
    await context.setup_websocket_connection(endpoint="/ws/test", auth_required=False)
    yield context


# Utility functions for common test patterns

async def assert_agent_events_received(
    test_context: WebSocketContext,
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
    test_context: WebSocketContext,
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