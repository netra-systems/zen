"""
Test Context Module - WebSocket Testing and User Context Simulation

This module provides the TestContext class that was missing and blocking WebSocket tests.
Provides comprehensive utilities for:
- WebSocket connection management and testing
- User context simulation and isolation  
- Agent event tracking and validation
- Async test context management

MISSION CRITICAL: Enables WebSocket agent event testing which is core to chat value delivery.

@compliance CLAUDE.md - Chat is King, WebSocket events are critical infrastructure
@compliance SPEC/core.xml - Test framework integration points
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union, AsyncGenerator, Callable
from shared.isolated_environment import IsolatedEnvironment

import pytest

from shared.isolated_environment import get_env
from test_framework.websocket_helpers import WebSocketTestHelpers, WebSocketPerformanceMonitor


@dataclass
class TestUserContext:
    """Test user context for simulation and isolation."""
    user_id: str
    email: str = ""
    name: str = ""
    role: str = "user"
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    jwt_token: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize defaults."""
        if not self.email:
            self.email = f"{self.user_id}@test.com"
        if not self.name:
            self.name = f"Test User {self.user_id}"
        if not self.thread_id:
            self.thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        if not self.session_id:
            self.session_id = f"session_{uuid.uuid4().hex[:8]}"


@dataclass
class WebSocketEventCapture:
    """Captures and validates WebSocket events during testing."""
    events: List[Dict[str, Any]] = field(default_factory=list)
    event_types: Set[str] = field(default_factory=set)
    event_counts: Dict[str, int] = field(default_factory=dict)
    start_time: Optional[float] = None
    
    def capture_event(self, event: Dict[str, Any]) -> None:
        """Capture a WebSocket event."""
        event_type = event.get("type", "unknown")
        timestamp = time.time()
        
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = timestamp
            
        self.events.append(event)
        self.event_types.add(event_type)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        if not self.start_time:
            self.start_time = timestamp
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [event for event in self.events if event.get("type") == event_type]
    
    def has_required_events(self, required_events: Set[str]) -> bool:
        """Check if all required events were captured."""
        return required_events.issubset(self.event_types)
    
    def get_missing_events(self, required_events: Set[str]) -> Set[str]:
        """Get missing required events."""
        return required_events - self.event_types
    
    def clear(self) -> None:
        """Clear all captured events."""
        self.events.clear()
        self.event_types.clear()
        self.event_counts.clear()
        self.start_time = None


class WebSocketContext:
    """
    Main WebSocketTestContext class for WebSocket testing and user context simulation.

    Provides comprehensive utilities for testing WebSocket agent interactions,
    user context isolation, and event validation.
    """
    
    # Required WebSocket events for agent testing
    REQUIRED_AGENT_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(
        self,
        user_context: Optional[TestUserContext] = None,
        websocket_timeout: float = 10.0,
        event_timeout: float = 5.0
    ):
        """
        Initialize TestContext.
        
        Args:
            user_context: Test user context for simulation
            websocket_timeout: Timeout for WebSocket operations
            event_timeout: Timeout for event capture
        """
        self.user_context = user_context or self._create_default_user_context()
        self.websocket_timeout = websocket_timeout
        self.event_timeout = event_timeout
        
        # WebSocket connection management
        self.websocket_connection: Optional[Any] = None
        self.websocket_url: Optional[str] = None
        
        # Event tracking
        self.event_capture = WebSocketEventCapture()
        self.performance_monitor = WebSocketPerformanceMonitor()
        
        # Test execution tracking
        self.test_id = f"test_{uuid.uuid4().hex[:8]}"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        # Environment configuration with enhanced Windows support (Issue #860)
        self.env = get_env()
        self.frontend_url = self.env.get('FRONTEND_URL', 'http://localhost:3000')

        # Enhanced backend URL detection with Windows support
        self.backend_url = self._get_enhanced_backend_url()
        self.websocket_base_url = self._get_enhanced_websocket_base_url()
    
    def _create_default_user_context(self) -> TestUserContext:
        """Create a default test user context."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        return TestUserContext(user_id=user_id)

    def _get_enhanced_backend_url(self) -> str:
        """Get backend URL with enhanced Windows support (Issue #860)."""
        import platform

        # Priority 1: Explicit TEST_BACKEND_URL override
        test_backend_url = self.env.get('TEST_BACKEND_URL')
        if test_backend_url:
            return test_backend_url

        # Priority 2: Environment variable fallback priority
        backend_url = self.env.get('BACKEND_URL')
        if not backend_url:  # None or empty string
            backend_url = self.env.get('NETRA_BACKEND_URL')

        if backend_url:
            return backend_url

        # Priority 3: Windows mock server detection
        is_windows = platform.system() == 'Windows'
        if is_windows and self.env.get('USE_MOCK_WEBSOCKET', 'false').lower() == 'true':
            return 'http://localhost:8001'  # Mock server backend equivalent

        # Priority 4: Staging environment
        staging_base_url = self.env.get('STAGING_BASE_URL')
        use_staging = self.env.get('USE_STAGING_SERVICES', 'false').lower() == 'true'
        if staging_base_url and use_staging:
            return staging_base_url

        # Priority 5: Default fallback
        return 'http://localhost:8000'

    def _get_enhanced_websocket_base_url(self) -> str:
        """Get WebSocket base URL with enhanced Windows support (Issue #860)."""
        import platform

        # Priority 1: Explicit TEST_WEBSOCKET_URL override
        test_websocket_url = self.env.get('TEST_WEBSOCKET_URL')
        if test_websocket_url:
            # Extract base URL without endpoint
            return test_websocket_url.replace('/ws', '').replace('/chat', '')

        # Priority 2: Mock WebSocket server for Windows
        is_windows = platform.system() == 'Windows'
        mock_websocket_url = self.env.get('MOCK_WEBSOCKET_URL')
        use_mock = self.env.get('USE_MOCK_WEBSOCKET', 'false').lower() == 'true'

        if is_windows and (mock_websocket_url or use_mock):
            mock_url = mock_websocket_url or 'ws://localhost:8001/ws'
            return mock_url.replace('/ws', '')

        # Priority 3: Staging WebSocket URL
        staging_websocket_url = self.env.get('STAGING_WEBSOCKET_URL')
        use_staging = self.env.get('USE_STAGING_SERVICES', 'false').lower() == 'true'

        if staging_websocket_url and use_staging:
            return staging_websocket_url.replace('/ws', '')

        # Priority 4: Derive from backend URL
        backend_url = self._get_enhanced_backend_url()
        websocket_base_url = backend_url.replace('http://', 'ws://').replace('https://', 'wss://')

        return websocket_base_url
    
    async def setup_websocket_connection(
        self,
        endpoint: str = "/ws/chat",
        auth_required: bool = True
    ) -> None:
        """
        Set up WebSocket connection for testing with enhanced Windows support (Issue #860).

        Args:
            endpoint: WebSocket endpoint to connect to
            auth_required: Whether authentication is required
        """
        import platform

        # Enhanced URL construction with Windows mock server support
        is_windows = platform.system() == 'Windows'
        use_mock = self.env.get('USE_MOCK_WEBSOCKET', 'false').lower() == 'true'

        # For mock server, always use /ws endpoint regardless of requested endpoint
        if is_windows and use_mock:
            self.websocket_url = f"{self.websocket_base_url}/ws"
        else:
            self.websocket_url = f"{self.websocket_base_url}{endpoint}"

        headers = {}
        if auth_required and self.user_context.jwt_token:
            headers["Authorization"] = f"Bearer {self.user_context.jwt_token}"

        try:
            # Use WebSocketTestHelpers with enhanced fallback support
            self.websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                self.websocket_url,
                headers=headers if headers else None,
                timeout=self.websocket_timeout,
                max_retries=3,
                user_id=self.user_context.user_id
            )

            # Log connection details for debugging
            print(f"🔗 WebSocket connection established: {self.websocket_url}")
            if is_windows and use_mock:
                print(f"🪟 Windows mock server connection active")

        except Exception as e:
            # Enhanced error handling for Windows
            if is_windows and "connection refused" in str(e).lower():
                print(f"🪟 Windows connection refused detected - trying to start mock server")

                # Try to start mock server as fallback
                try:
                    from tests.mission_critical.websocket_real_test_base import setup_mock_websocket_environment
                    import asyncio
                    await setup_mock_websocket_environment()

                    # Update URL to mock server
                    self.websocket_url = self.env.get('MOCK_WEBSOCKET_URL', 'ws://localhost:8001/ws')

                    # Retry connection
                    self.websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                        self.websocket_url,
                        headers=headers if headers else None,
                        timeout=self.websocket_timeout,
                        max_retries=3,
                        user_id=self.user_context.user_id
                    )
                    print(f"✅ Mock WebSocket server fallback successful: {self.websocket_url}")
                    return

                except Exception as mock_error:
                    print(f"❌ Mock WebSocket server fallback failed: {mock_error}")

            raise ConnectionError(f"Failed to setup WebSocket connection: {e}")
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message through the WebSocket connection.
        
        Args:
            message: Message to send
        """
        if not self.websocket_connection:
            raise RuntimeError("WebSocket connection not established. Call setup_websocket_connection first.")
        
        # Add user context to message if not present
        if "user_id" not in message:
            message["user_id"] = self.user_context.user_id
        if "thread_id" not in message:
            message["thread_id"] = self.user_context.thread_id
        
        await WebSocketTestHelpers.send_test_message(
            self.websocket_connection,
            message,
            timeout=self.websocket_timeout
        )
    
    async def send_raw_message(self, raw_message: str) -> None:
        """
        Send a raw string message through the WebSocket connection.
        Used for testing malformed JSON messages.
        
        Args:
            raw_message: Raw string message to send
        """
        if not self.websocket_connection:
            raise RuntimeError("WebSocket connection not established. Call setup_websocket_connection first.")
        
        await WebSocketTestHelpers.send_raw_test_message(
            self.websocket_connection,
            raw_message,
            timeout=self.websocket_timeout
        )
    
    async def receive_message(self) -> Dict[str, Any]:
        """
        Receive a message from the WebSocket connection.
        
        Returns:
            Received message as dictionary
        """
        if not self.websocket_connection:
            raise RuntimeError("WebSocket connection not established. Call setup_websocket_connection first.")
        
        return await WebSocketTestHelpers.receive_test_message(
            self.websocket_connection,
            timeout=self.websocket_timeout
        )
    
    async def listen_for_events(
        self,
        duration: float = 5.0,
        capture_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Listen for WebSocket events for a specified duration.
        
        Args:
            duration: How long to listen for events
            capture_callback: Optional callback for each captured event
            
        Returns:
            List of captured events
        """
        if not self.websocket_connection:
            raise RuntimeError("WebSocket connection not established. Call setup_websocket_connection first.")
        
        events = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                try:
                    # Set a short timeout to allow periodic checking
                    event = await WebSocketTestHelpers.receive_test_message(
                        self.websocket_connection,
                        timeout=0.5
                    )
                    
                    events.append(event)
                    self.event_capture.capture_event(event)
                    
                    if capture_callback:
                        capture_callback(event)
                        
                except asyncio.TimeoutError:
                    # Continue listening
                    continue
                except Exception as e:
                    # Log error but continue
                    print(f"Error receiving event: {e}")
                    break
                    
        except Exception as e:
            print(f"Event listening stopped: {e}")
        
        return events
    
    async def wait_for_agent_events(
        self,
        required_events: Optional[Set[str]] = None,
        timeout: float = 30.0
    ) -> bool:
        """
        Wait for required agent events to be received.
        
        Args:
            required_events: Set of required event types (defaults to REQUIRED_AGENT_EVENTS)
            timeout: Maximum time to wait for events
            
        Returns:
            True if all required events were received
        """
        if required_events is None:
            required_events = self.REQUIRED_AGENT_EVENTS.copy()
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.event_capture.has_required_events(required_events):
                return True
            
            try:
                # Listen for more events
                await self.listen_for_events(duration=1.0)
            except Exception:
                # Continue waiting
                pass
        
        return False
    
    async def get_received_events(self, timeout: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get all currently available received events without blocking.
        
        Args:
            timeout: Maximum time to wait for each event
            
        Returns:
            List of all available events
        """
        events = []
        
        if not self.websocket_connection:
            return events
        
        while True:
            try:
                event = await asyncio.wait_for(
                    WebSocketTestHelpers.receive_test_message(
                        self.websocket_connection,
                        timeout=timeout
                    ),
                    timeout=timeout
                )
                events.append(event)
                self.event_capture.capture_event(event)
            except asyncio.TimeoutError:
                # No more events available - break
                break
            except Exception as e:
                # Error receiving event - break
                print(f"Error receiving event: {e}")
                break
        
        return events
    
    def get_captured_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get captured events, optionally filtered by type.
        
        Args:
            event_type: Optional event type to filter by
            
        Returns:
            List of captured events
        """
        if event_type:
            return self.event_capture.get_events_by_type(event_type)
        return self.event_capture.events.copy()
    
    def validate_agent_events(self, required_events: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Validate that required agent events were captured.
        
        Args:
            required_events: Set of required event types
            
        Returns:
            Validation results dictionary
        """
        if required_events is None:
            required_events = self.REQUIRED_AGENT_EVENTS.copy()
        
        captured_types = self.event_capture.event_types
        missing_events = required_events - captured_types
        extra_events = captured_types - required_events
        
        return {
            "valid": len(missing_events) == 0,
            "required_events": required_events,
            "captured_events": captured_types,
            "missing_events": missing_events,
            "extra_events": extra_events,
            "event_counts": self.event_capture.event_counts.copy(),
            "total_events": len(self.event_capture.events)
        }
    
    def simulate_user_message(self, content: str, message_type: str = "chat") -> Dict[str, Any]:
        """
        Simulate a user message for testing.
        
        Args:
            content: Message content
            message_type: Type of message
            
        Returns:
            Simulated message dictionary
        """
        return {
            "type": message_type,
            "content": content,
            "user_id": self.user_context.user_id,
            "thread_id": self.user_context.thread_id,
            "session_id": self.user_context.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "test_id": self.test_id,
                "test_context": True
            }
        }
    
    def create_isolated_user_context(self, user_id: Optional[str] = None) -> TestUserContext:
        """
        Create an isolated user context for testing user isolation.
        
        Args:
            user_id: Optional specific user ID
            
        Returns:
            New isolated user context
        """
        if not user_id:
            user_id = f"isolated_user_{uuid.uuid4().hex[:8]}"
        
        return TestUserContext(user_id=user_id)
    
    async def cleanup(self) -> None:
        """Clean up WebSocket connections and resources."""
        if self.websocket_connection:
            try:
                await WebSocketTestHelpers.close_test_connection(self.websocket_connection)
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                self.websocket_connection = None
        
        # Record end time
        self.end_time = time.time()
    
    @asynccontextmanager
    async def websocket_session(self, endpoint: str = "/ws/chat", auth_required: bool = True):
        """
        Async context manager for WebSocket session management.
        
        Args:
            endpoint: WebSocket endpoint
            auth_required: Whether authentication is required
        """
        try:
            await self.setup_websocket_connection(endpoint, auth_required)
            self.start_time = time.time()
            yield self
        finally:
            await self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the test session."""
        duration = None
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
        elif self.start_time:
            duration = time.time() - self.start_time
        
        return {
            "duration_seconds": duration,
            "total_events_captured": len(self.event_capture.events),
            "unique_event_types": len(self.event_capture.event_types),
            "event_counts": self.event_capture.event_counts.copy(),
            "events_per_second": len(self.event_capture.events) / duration if duration and duration > 0 else 0,
            "websocket_url": self.websocket_url,
            "user_context": {
                "user_id": self.user_context.user_id,
                "thread_id": self.user_context.thread_id,
                "session_id": self.user_context.session_id
            }
        }
    
    # Convenience methods for common test scenarios
    
    async def send_chat_message(self, content: str) -> None:
        """Send a chat message through WebSocket."""
        message = self.simulate_user_message(content, "chat")
        await self.send_message(message)
    
    async def trigger_agent_execution(
        self,
        agent_name: str,
        task: str,
        wait_for_completion: bool = True,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Trigger agent execution and optionally wait for completion.
        
        Args:
            agent_name: Name of agent to execute
            task: Task for the agent
            wait_for_completion: Whether to wait for completion
            timeout: Timeout for completion
            
        Returns:
            Execution results
        """
        # Send agent execution request
        request = {
            "type": "agent_request",
            "agent_name": agent_name,
            "task": task,
            "user_id": self.user_context.user_id,
            "thread_id": self.user_context.thread_id
        }
        
        await self.send_message(request)
        
        if wait_for_completion:
            # Wait for agent events
            success = await self.wait_for_agent_events(timeout=timeout)
            return {
                "success": success,
                "events_captured": self.get_captured_events(),
                "validation": self.validate_agent_events()
            }
        
        return {"success": True, "request_sent": True}


# Class alias for backward compatibility
TestContext = WebSocketContext

# Convenience factory functions

def create_test_context(
    user_id: Optional[str] = None,
    jwt_token: Optional[str] = None,
    websocket_timeout: float = 10.0
) -> WebSocketContext:
    """
    Factory function to create a TestContext with common defaults.
    
    Args:
        user_id: Optional user ID
        jwt_token: Optional JWT token for authentication
        websocket_timeout: WebSocket operation timeout
        
    Returns:
        Configured TestContext instance
    """
    if not user_id:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    user_context = TestUserContext(user_id=user_id)
    if jwt_token:
        user_context.jwt_token = jwt_token
    
    return WebSocketContext(
        user_context=user_context,
        websocket_timeout=websocket_timeout
    )


def create_isolated_test_contexts(count: int = 2) -> List[WebSocketContext]:
    """
    Create multiple isolated test contexts for concurrent testing.
    
    Args:
        count: Number of contexts to create
        
    Returns:
        List of isolated WebSocketContext instances
    """
    contexts = []
    for i in range(count):
        user_id = f"isolated_user_{i}_{uuid.uuid4().hex[:8]}"
        context = create_test_context(user_id=user_id)
        contexts.append(context)
    
    return contexts


# Pytest fixtures

@pytest.fixture
async def test_context():
    """Pytest fixture for TestContext."""
    context = create_test_context()
    try:
        yield context
    finally:
        await context.cleanup()


@pytest.fixture
async def authenticated_test_context():
    """Pytest fixture for authenticated TestContext."""
    # This would integrate with your JWT generation logic
    # For now, we'll create a mock token
    jwt_token = "test_jwt_token_placeholder"
    
    context = create_test_context(jwt_token=jwt_token)
    try:
        yield context
    finally:
        await context.cleanup()


@pytest.fixture
async def multiple_test_contexts():
    """Pytest fixture for multiple isolated test contexts."""
    contexts = create_isolated_test_contexts(count=3)
    try:
        yield contexts
    finally:
        # Cleanup all contexts
        cleanup_tasks = [context.cleanup() for context in contexts]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


# Type alias for backwards compatibility with mission critical tests
WebSocketTestContext = WebSocketContext