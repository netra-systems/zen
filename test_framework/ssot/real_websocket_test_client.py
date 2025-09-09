"""
SSOT Real WebSocket Test Client - NO MOCKS

This module provides the SINGLE SOURCE OF TRUTH for real WebSocket test connections
that use actual WebSocket connections to backend services with proper authentication.

CRITICAL: Per CLAUDE.md - "MOCKS = Abomination"
- ALL WebSocket tests MUST use real connections to backend services
- ALL e2e tests MUST use authentication (JWT/OAuth) except tests directly validating auth
- Tests MUST fail hard when isolation is violated

Business Value Justification:
- Segment: Platform/Internal - Chat infrastructure testing  
- Business Goal: Ensure WebSocket events deliver substantive chat value
- Value Impact: Validates real-time AI interactions that drive 90% of platform value
- Revenue Impact: Protects chat functionality that generates customer conversions

@compliance CLAUDE.md - Real services over mocks, E2E tests require authentication
@compliance SPEC/core.xml - WebSocket events enable substantive chat interactions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

import websockets
from websockets import ConnectionClosed, InvalidStatus, WebSocketException

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, AuthenticatedUser

logger = logging.getLogger(__name__)


class WebSocketConnectionState(Enum):
    """States for real WebSocket connections."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class WebSocketEvent:
    """Represents a WebSocket event received from the server."""
    event_type: str
    data: Dict[str, Any]
    timestamp: float
    user_id: Optional[str] = None
    connection_id: Optional[str] = None
    
    @classmethod
    def from_message(cls, message: Union[str, bytes], connection_id: Optional[str] = None) -> 'WebSocketEvent':
        """Create WebSocketEvent from raw message."""
        try:
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            
            data = json.loads(message)
            event_type = data.get('type', 'unknown')
            user_id = data.get('user_id')
            
            return cls(
                event_type=event_type,
                data=data,
                timestamp=time.time(),
                user_id=user_id,
                connection_id=connection_id
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
            return cls(
                event_type="parse_error",
                data={"raw_message": str(message), "error": str(e)},
                timestamp=time.time(),
                connection_id=connection_id
            )


@dataclass
class ConnectionMetrics:
    """Metrics for a WebSocket connection."""
    connection_id: str
    user_id: str
    connection_time: float
    authentication_time: Optional[float] = None
    total_events_sent: int = 0
    total_events_received: int = 0
    last_activity: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    
    def record_sent_event(self):
        """Record a sent event."""
        self.total_events_sent += 1
        self.last_activity = time.time()
    
    def record_received_event(self):
        """Record a received event."""
        self.total_events_received += 1
        self.last_activity = time.time()
    
    def record_error(self, error: str):
        """Record an error."""
        self.errors.append(f"{time.time()}: {error}")


class RealWebSocketTestClient:
    """
    SSOT Real WebSocket Test Client for E2E Testing.
    
    CRITICAL FEATURES:
    - Real WebSocket connections to backend services (NO MOCKS)
    - Proper JWT authentication for all connections
    - Multi-user isolation validation
    - Event capture and validation
    - Connection metrics and monitoring
    - Fail-hard security validation
    
    This client is designed to FAIL HARD when:
    - Authentication is missing or invalid
    - User isolation is violated
    - Events leak between users
    - Connection security is compromised
    """
    
    def __init__(
        self,
        backend_url: str = "ws://localhost:8000",
        environment: str = "test",
        connection_timeout: float = 10.0,
        auth_required: bool = True
    ):
        """Initialize real WebSocket test client.
        
        Args:
            backend_url: WebSocket URL for backend service
            environment: Test environment ('test', 'staging', etc.)
            connection_timeout: Connection timeout in seconds
            auth_required: Whether authentication is required (default True)
        """
        self.backend_url = backend_url.rstrip('/')
        self.environment = environment
        self.connection_timeout = connection_timeout
        self.auth_required = auth_required
        
        # Initialize auth helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Connection management
        self.connection: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_id = f"ws_test_{uuid.uuid4().hex[:8]}"
        self.state = WebSocketConnectionState.DISCONNECTED
        self.authenticated_user: Optional[AuthenticatedUser] = None
        
        # Event tracking
        self.received_events: List[WebSocketEvent] = []
        self.sent_events: List[Dict[str, Any]] = []
        self.event_listeners: List[Callable[[WebSocketEvent], None]] = []
        
        # Metrics
        self.metrics = ConnectionMetrics(
            connection_id=self.connection_id,
            user_id="",
            connection_time=0.0
        )
        
        # Security validation
        self.isolation_violations: List[str] = []
        self.expected_user_id: Optional[str] = None
        
        logger.info(f"Initialized RealWebSocketTestClient: {self.connection_id}")
    
    async def authenticate_user(
        self,
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> AuthenticatedUser:
        """Authenticate a user for WebSocket testing.
        
        Args:
            user_email: User email (auto-generated if not provided)
            user_id: User ID (auto-generated if not provided)  
            permissions: User permissions (defaults to ["read", "write"])
            
        Returns:
            AuthenticatedUser instance with JWT token
            
        Raises:
            RuntimeError: If authentication fails
        """
        try:
            auth_start = time.time()
            
            self.authenticated_user = await self.auth_helper.create_authenticated_user(
                email=user_email,
                user_id=user_id,
                permissions=permissions or ["read", "write"]
            )
            
            self.expected_user_id = self.authenticated_user.user_id
            self.metrics.user_id = self.authenticated_user.user_id
            self.metrics.authentication_time = time.time() - auth_start
            
            logger.info(f"User authenticated: {self.authenticated_user.user_id}")
            return self.authenticated_user
            
        except Exception as e:
            error_msg = f"Authentication failed: {e}"
            self.metrics.record_error(error_msg)
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def connect(self, endpoint: str = "/ws", max_retries: int = 3) -> None:
        """Establish real WebSocket connection with authentication and retry logic.
        
        Args:
            endpoint: WebSocket endpoint to connect to
            max_retries: Maximum number of connection attempts (default: 3)
            
        Raises:
            RuntimeError: If connection fails after all retries
            PermissionError: If authentication is required but missing
        """
        if self.auth_required and not self.authenticated_user:
            raise PermissionError(
                "Authentication required but no authenticated user. "
                "Call authenticate_user() first."
            )
        
        self.state = WebSocketConnectionState.CONNECTING
        connection_start = time.time()
        last_error = None
        
        # Build WebSocket URL and authentication headers once
        ws_url = f"{self.backend_url}{endpoint}"
        headers = {}
        if self.authenticated_user:
            headers = self.auth_helper.get_websocket_headers(
                self.authenticated_user.jwt_token
            )
        
        logger.info(f"Connecting to {ws_url} with retry logic (max {max_retries} attempts)")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"WebSocket connection attempt {attempt + 1}/{max_retries}")
                
                # Establish connection
                self.connection = await asyncio.wait_for(
                    websockets.connect(
                        ws_url,
                        additional_headers=headers,
                        open_timeout=self.connection_timeout,
                        close_timeout=5.0
                    ),
                    timeout=self.connection_timeout
                )
                
                self.state = WebSocketConnectionState.CONNECTED
                if self.authenticated_user:
                    self.state = WebSocketConnectionState.AUTHENTICATED
                
                self.metrics.connection_time = time.time() - connection_start
                
                logger.info(f"✅ WebSocket connected on attempt {attempt + 1}: {ws_url} (State: {self.state.value})")
                return  # Success!
                
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                last_error = e
                error_msg = f"WebSocket connection attempt {attempt + 1} failed: {e}"
                logger.warning(error_msg)
                self.metrics.record_error(error_msg)
                
                # Calculate exponential backoff delay
                if attempt < max_retries - 1:  # Don't delay after the last attempt
                    backoff_delay = min(2.0 ** attempt, 8.0)  # Cap at 8 seconds
                    logger.info(f"⏳ Retrying WebSocket connection in {backoff_delay:.1f}s...")
                    await asyncio.sleep(backoff_delay)
            
            except Exception as e:
                # Non-retryable errors (e.g., authentication issues)
                last_error = e
                error_msg = f"WebSocket connection failed with non-retryable error: {e}"
                logger.error(error_msg)
                self.state = WebSocketConnectionState.ERROR
                self.metrics.record_error(error_msg)
                raise RuntimeError(error_msg)
        
        # All retries exhausted
        final_error_msg = (
            f"WebSocket connection failed after {max_retries} attempts. "
            f"Last error: {last_error}. Total time: {time.time() - connection_start:.1f}s"
        )
        self.state = WebSocketConnectionState.ERROR
        self.metrics.record_error(final_error_msg)
        logger.error(f"❌ {final_error_msg}")
        raise RuntimeError(final_error_msg)
    
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send an event through the WebSocket connection.
        
        Args:
            event_type: Type of event to send
            data: Event data
            
        Raises:
            RuntimeError: If not connected or send fails
        """
        if not self.connection or self.state not in [
            WebSocketConnectionState.CONNECTED,
            WebSocketConnectionState.AUTHENTICATED
        ]:
            raise RuntimeError("Not connected to WebSocket")
        
        # Build event message
        event_data = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connection_id": self.connection_id,
            **data
        }
        
        # Add user context if authenticated
        if self.authenticated_user:
            event_data["user_id"] = self.authenticated_user.user_id
        
        try:
            message = json.dumps(event_data)
            await self.connection.send(message)
            
            self.sent_events.append(event_data)
            self.metrics.record_sent_event()
            
            logger.debug(f"Sent WebSocket event: {event_type}")
            
        except Exception as e:
            error_msg = f"Failed to send WebSocket event: {e}"
            self.metrics.record_error(error_msg)
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def receive_event(self, timeout: float = 5.0) -> WebSocketEvent:
        """Receive an event from the WebSocket connection.
        
        Args:
            timeout: Timeout for receiving event
            
        Returns:
            WebSocketEvent received from server
            
        Raises:
            RuntimeError: If not connected or receive fails
            asyncio.TimeoutError: If timeout exceeded
        """
        if not self.connection or self.state not in [
            WebSocketConnectionState.CONNECTED,
            WebSocketConnectionState.AUTHENTICATED
        ]:
            raise RuntimeError("Not connected to WebSocket")
        
        try:
            message = await asyncio.wait_for(
                self.connection.recv(),
                timeout=timeout
            )
            
            event = WebSocketEvent.from_message(message, self.connection_id)
            self.received_events.append(event)
            self.metrics.record_received_event()
            
            # CRITICAL: Validate user isolation
            self._validate_user_isolation(event)
            
            # Notify listeners
            for listener in self.event_listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            logger.debug(f"Received WebSocket event: {event.event_type}")
            return event
            
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket receive timeout after {timeout}s")
            raise
        except ConnectionClosed as e:
            error_msg = f"WebSocket connection closed during receive: {e}"
            self.state = WebSocketConnectionState.CLOSED
            self.metrics.record_error(error_msg)
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Failed to receive WebSocket event: {e}"
            self.metrics.record_error(error_msg)
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _validate_user_isolation(self, event: WebSocketEvent) -> None:
        """CRITICAL: Validate user isolation for security.
        
        This method MUST detect when events leak between users.
        Tests will FAIL HARD when isolation is violated.
        
        Args:
            event: WebSocket event to validate
        """
        if not self.expected_user_id:
            return  # No isolation validation needed
        
        # Check if event contains user_id
        event_user_id = event.user_id or event.data.get('user_id')
        
        if event_user_id and event_user_id != self.expected_user_id:
            violation = (
                f"USER ISOLATION VIOLATION: Expected user_id '{self.expected_user_id}' "
                f"but received event for user_id '{event_user_id}'. "
                f"Event type: {event.event_type}. "
                f"This indicates cross-user data leakage!"
            )
            
            self.isolation_violations.append(violation)
            logger.error(violation)
            
            # FAIL HARD - raise exception immediately
            raise SecurityError(violation)
    
    def add_event_listener(self, listener: Callable[[WebSocketEvent], None]) -> None:
        """Add an event listener for received events.
        
        Args:
            listener: Function to call when events are received
        """
        self.event_listeners.append(listener)
    
    async def wait_for_events(
        self,
        event_types: Set[str],
        timeout: float = 30.0,
        max_events: int = 100
    ) -> List[WebSocketEvent]:
        """Wait for specific event types to be received.
        
        Args:
            event_types: Set of event types to wait for
            timeout: Maximum time to wait
            max_events: Maximum events to collect
            
        Returns:
            List of matching events received
            
        Raises:
            RuntimeError: If connection fails
            asyncio.TimeoutError: If timeout exceeded
        """
        matching_events = []
        remaining_types = event_types.copy()
        start_time = time.time()
        
        logger.info(f"Waiting for events: {event_types} (timeout: {timeout}s)")
        
        try:
            while remaining_types and len(matching_events) < max_events:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    break
                
                # Calculate remaining timeout
                remaining_timeout = timeout - elapsed
                
                try:
                    event = await self.receive_event(timeout=min(remaining_timeout, 5.0))
                    
                    if event.event_type in event_types:
                        matching_events.append(event)
                        remaining_types.discard(event.event_type)
                        
                        logger.debug(
                            f"Found matching event: {event.event_type}. "
                            f"Remaining: {remaining_types}"
                        )
                    
                except asyncio.TimeoutError:
                    continue  # Keep trying until main timeout
                
            logger.info(f"Collected {len(matching_events)} events. Missing: {remaining_types}")
            return matching_events
            
        except Exception as e:
            error_msg = f"Error waiting for events: {e}"
            self.metrics.record_error(error_msg)
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def close(self) -> None:
        """Close the WebSocket connection and cleanup."""
        if self.connection and not self.connection.closed:
            try:
                await self.connection.close()
                logger.info(f"WebSocket connection closed: {self.connection_id}")
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection: {e}")
        
        self.state = WebSocketConnectionState.CLOSED
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics and statistics.
        
        Returns:
            Dictionary with connection metrics
        """
        return {
            "connection_id": self.connection_id,
            "user_id": self.metrics.user_id,
            "state": self.state.value,
            "connection_time": self.metrics.connection_time,
            "authentication_time": self.metrics.authentication_time,
            "events_sent": self.metrics.total_events_sent,
            "events_received": self.metrics.total_events_received,
            "last_activity": self.metrics.last_activity,
            "errors": len(self.metrics.errors),
            "isolation_violations": len(self.isolation_violations),
            "backend_url": self.backend_url,
            "environment": self.environment
        }
    
    def assert_no_isolation_violations(self) -> None:
        """Assert that no user isolation violations occurred.
        
        Raises:
            AssertionError: If isolation violations were detected
        """
        if self.isolation_violations:
            violation_summary = "\n".join(self.isolation_violations)
            raise AssertionError(
                f"USER ISOLATION VIOLATIONS DETECTED ({len(self.isolation_violations)}):\n"
                f"{violation_summary}"
            )
    
    def assert_events_received(self, expected_events: Set[str]) -> None:
        """Assert that all expected events were received.
        
        Args:
            expected_events: Set of event types that should have been received
            
        Raises:
            AssertionError: If expected events are missing
        """
        received_types = {event.event_type for event in self.received_events}
        missing_events = expected_events - received_types
        
        if missing_events:
            raise AssertionError(
                f"Missing expected WebSocket events: {missing_events}. "
                f"Received: {received_types}"
            )
    
    @asynccontextmanager
    async def connection_context(
        self,
        endpoint: str = "/ws",
        authenticate: bool = True,
        user_email: Optional[str] = None
    ):
        """Context manager for WebSocket connection lifecycle.
        
        Args:
            endpoint: WebSocket endpoint to connect to
            authenticate: Whether to authenticate before connecting
            user_email: User email for authentication
        
        Yields:
            Connected RealWebSocketTestClient instance
        """
        try:
            if authenticate and self.auth_required:
                await self.authenticate_user(user_email=user_email)
            
            await self.connect(endpoint=endpoint)
            yield self
            
        finally:
            await self.close()


class SecurityError(Exception):
    """Exception raised when security violations are detected."""
    pass


# SSOT Functions for convenience

async def create_authenticated_websocket_client(
    backend_url: str = "ws://localhost:8000",
    environment: str = "test",
    user_email: Optional[str] = None,
    user_id: Optional[str] = None,
    permissions: Optional[List[str]] = None
) -> RealWebSocketTestClient:
    """Create an authenticated WebSocket test client.
    
    This is a convenience function that creates and authenticates a client.
    
    Args:
        backend_url: WebSocket URL for backend service
        environment: Test environment ('test', 'staging', etc.)
        user_email: User email (auto-generated if not provided)
        user_id: User ID (auto-generated if not provided)
        permissions: User permissions (defaults to ["read", "write"])
        
    Returns:
        Authenticated RealWebSocketTestClient
    """
    client = RealWebSocketTestClient(
        backend_url=backend_url,
        environment=environment,
        auth_required=True
    )
    
    await client.authenticate_user(
        user_email=user_email,
        user_id=user_id,
        permissions=permissions
    )
    
    return client


async def test_websocket_events_isolation(
    clients: List[RealWebSocketTestClient],
    event_types: Set[str],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Test WebSocket event isolation between multiple clients.
    
    This function validates that events sent to one client
    are NOT received by other clients (multi-user isolation).
    
    Args:
        clients: List of authenticated WebSocket clients
        event_types: Event types to test
        timeout: Test timeout
        
    Returns:
        Test results with isolation validation
        
    Raises:
        SecurityError: If isolation is violated
    """
    results = {
        "clients_tested": len(clients),
        "isolation_violations": [],
        "test_passed": True
    }
    
    # Send events from each client
    for i, client in enumerate(clients):
        test_event = f"test_isolation_event_{i}"
        await client.send_event(
            event_type=test_event,
            data={
                "test_id": f"isolation_test_{i}",
                "sender_client": client.connection_id
            }
        )
    
    # Wait for events and check isolation
    for client in clients:
        try:
            events = await client.wait_for_events(
                event_types=event_types,
                timeout=timeout / len(clients)  # Distribute timeout
            )
            
            # Validate no cross-user events received
            for event in events:
                if event.user_id != client.expected_user_id:
                    violation = (
                        f"Client {client.connection_id} received event "
                        f"for user {event.user_id} instead of {client.expected_user_id}"
                    )
                    results["isolation_violations"].append(violation)
                    results["test_passed"] = False
            
        except Exception as e:
            results["isolation_violations"].append(
                f"Client {client.connection_id} error: {e}"
            )
            results["test_passed"] = False
    
    # Collect all isolation violations
    for client in clients:
        if client.isolation_violations:
            results["isolation_violations"].extend(client.isolation_violations)
            results["test_passed"] = False
    
    if not results["test_passed"]:
        raise SecurityError(
            f"WebSocket isolation test FAILED. "
            f"Violations: {results['isolation_violations']}"
        )
    
    return results