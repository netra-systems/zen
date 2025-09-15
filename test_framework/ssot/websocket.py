"""
Single Source of Truth (SSOT) WebSocket Test Utility

This module provides the unified WebSocketTestUtility for ALL WebSocket testing
across the entire test suite. It eliminates WebSocket test duplication.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Ensures consistent WebSocket testing, proper event handling, and reliable cleanup.

CRITICAL: This is the ONLY source for WebSocket test utilities in the system.
ALL WebSocket tests must use WebSocketTestUtility for setup and management.
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import pytest
import websocket
import websockets
from websockets import ConnectionClosed, InvalidStatus, WebSocketException

# Import SSOT environment management
from shared.isolated_environment import get_env

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


class MockWebSocketConnection:
    """Mock WebSocket connection for testing without real servers."""
    
    def __init__(self):
        self.closed = False
        self.sent_messages = []
        self.received_messages = []
        
    async def send(self, message):
        """Mock send method."""
        if self.closed:
            raise ConnectionClosed(None, None)
        self.sent_messages.append(message)
        logger.debug(f"Mock WebSocket sent: {message}")
        
    async def recv(self):
        """Mock receive method."""
        if self.closed:
            raise ConnectionClosed(None, None)
        
        # Simulate periodic messages for testing
        await asyncio.sleep(0.1)
        mock_message = json.dumps({
            "type": "ping",
            "data": {"timestamp": time.time()},
            "message_id": str(uuid.uuid4())
        })
        self.received_messages.append(mock_message)
        return mock_message
        
    async def close(self, code=1000):
        """Mock close method."""
        self.closed = True
        logger.debug("Mock WebSocket connection closed")
        
    @property
    def closed_property(self):
        """Mock closed property."""
        return self.closed


class WebSocketEventType(Enum):
    """Standard WebSocket event types for testing."""
    __test__ = False  # Tell pytest this is not a test class
    
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETED = "agent_completed"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    THREAD_UPDATE = "thread_update"
    MESSAGE_CREATED = "message_created"
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"


@dataclass
class WebSocketMessage:
    """Structured WebSocket message for testing."""
    event_type: WebSocketEventType
    data: Dict[str, Any]
    timestamp: datetime
    message_id: str
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketMessage':
        """Create from dictionary."""
        return cls(
            event_type=WebSocketEventType(data["type"]),
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_id=data["message_id"],
            user_id=data.get("user_id"),
            thread_id=data.get("thread_id")
        )


class WebSocketTestMetrics:
    """Track WebSocket test performance and behavior metrics."""
    
    def __init__(self):
        self.connection_time = 0.0
        self.messages_sent = 0
        self.messages_received = 0
        self.events_emitted = 0
        self.connection_errors = 0
        self.message_errors = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        self.connection_duration = 0.0
        self.avg_message_latency = 0.0
        self.max_message_latency = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.events_by_type: Dict[str, int] = {}
        
    def record_connection(self, duration: float):
        """Record connection establishment time."""
        self.connection_time = duration
        
    def record_message_sent(self, size: int = 0):
        """Record a sent message."""
        self.messages_sent += 1
        self.total_bytes_sent += size
        
    def record_message_received(self, size: int = 0):
        """Record a received message."""
        self.messages_received += 1
        self.total_bytes_received += size
        
    def record_event_emitted(self, event_type: str):
        """Record an event emission."""
        self.events_emitted += 1
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
        
    def record_connection_error(self):
        """Record a connection error."""
        self.connection_errors += 1
        
    def record_message_error(self):
        """Record a message error."""
        self.message_errors += 1
        
    def record_message_latency(self, latency: float):
        """Record message latency."""
        if self.avg_message_latency == 0:
            self.avg_message_latency = latency
        else:
            # Running average
            total_messages = self.messages_sent + self.messages_received
            self.avg_message_latency = ((self.avg_message_latency * (total_messages - 1)) + latency) / total_messages
        
        self.max_message_latency = max(self.max_message_latency, latency)
        
    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)
        
    def add_warning(self, warning: str):
        """Record a warning."""
        self.warnings.append(warning)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "connection_time": self.connection_time,
            "connection_duration": self.connection_duration,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "events_emitted": self.events_emitted,
            "connection_errors": self.connection_errors,
            "message_errors": self.message_errors,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "avg_message_latency": self.avg_message_latency,
            "max_message_latency": self.max_message_latency,
            "events_by_type": self.events_by_type,
            "errors": self.errors,
            "warnings": self.warnings
        }


class WebSocketTestClient:
    """Test client for WebSocket connections with event tracking."""
    
    def __init__(self, url: str, test_id: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize WebSocket test client.
        
        Args:
            url: WebSocket server URL
            test_id: Unique test identifier
            headers: Optional headers for connection
        """
        self.url = url
        self.test_id = test_id
        self.headers = headers or {}
        
        # Connection state
        self.websocket = None
        self.is_connected = False
        self.connection_start_time = None
        
        # Message tracking
        self.sent_messages: List[WebSocketMessage] = []
        self.received_messages: List[WebSocketMessage] = []
        self.event_handlers: Dict[WebSocketEventType, List[Callable]] = {}
        self.message_queue = asyncio.Queue()
        
        # Background tasks
        self.listener_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Test utilities
        self.expected_events: List[WebSocketEventType] = []
        self.event_timeouts: Dict[WebSocketEventType, float] = {}
        self.received_events: Dict[WebSocketEventType, List[WebSocketMessage]] = {}
        
        # Mock mode support
        self._mock_mode = False
        self._mock_websocket = None
        
    async def connect(self, timeout: float = 30.0, mock_mode: bool = False, 
                    subprotocols: Optional[List[str]] = None) -> bool:
        """
        Connect to WebSocket server with subprotocol fallback strategy.
        
        Args:
            timeout: Connection timeout in seconds
            mock_mode: If True, use mock connection instead of real WebSocket
            subprotocols: Optional list of subprotocols to negotiate
            
        Returns:
            True if connected successfully
        """
        if self.is_connected:
            logger.warning(f"WebSocket client {self.test_id} already connected")
            return True
            
        self.connection_start_time = time.time()
        self._mock_mode = mock_mode
        
        if mock_mode:
            # Use mock WebSocket connection
            logger.info(f"WebSocket client {self.test_id} using mock mode")
            self._mock_websocket = MockWebSocketConnection()
            self.websocket = self._mock_websocket
            self.is_connected = True
            
            # Start mock background listener
            self.listener_task = asyncio.create_task(self._mock_listen_for_messages())
            
            logger.info(f"WebSocket client {self.test_id} connected in mock mode")
            return True
        
        # WEBSOCKET SUBPROTOCOL FALLBACK STRATEGY
        # Try multiple connection strategies for GCP Cloud Run compatibility
        connection_strategies = self._get_connection_strategies(subprotocols)
        
        for strategy_name, strategy in connection_strategies:
            try:
                logger.info(f"Attempting {strategy_name} connection strategy for {self.test_id}")
                
                # Add test identification to headers
                test_headers = self.headers.copy()
                test_headers.update({
                    "X-Test-ID": self.test_id,
                    "X-Test-Timestamp": str(int(time.time())),
                    "X-Connection-Strategy": strategy_name
                })
                
                # Apply strategy-specific connection parameters
                connection_params = {
                    "additional_headers": test_headers,
                    "ping_interval": 20,
                    "ping_timeout": 10,
                    "close_timeout": 10
                }
                connection_params.update(strategy)
                
                # Connect with timeout (Python 3.12 compatible)
                async with asyncio.timeout(timeout / len(connection_strategies)):
                    self.websocket = await websockets.connect(self.url, **connection_params)
                
                self.is_connected = True
                
                # Start background listener
                self.listener_task = asyncio.create_task(self._listen_for_messages())
                
                # Start heartbeat if configured
                if self._should_send_heartbeat():
                    self.heartbeat_task = asyncio.create_task(self._send_heartbeat())
                
                logger.info(f"WebSocket client {self.test_id} connected using {strategy_name} strategy")
                return True
                
            except Exception as e:
                error_msg = str(e).lower()
                if "no subprotocols supported" in error_msg or "subprotocol" in error_msg:
                    logger.warning(f"{strategy_name} failed due to subprotocol issues: {e}")
                elif "timeout" in error_msg:
                    logger.warning(f"{strategy_name} timed out: {e}")
                else:
                    logger.warning(f"{strategy_name} failed: {e}")
                
                # Continue to next strategy
                continue
        
        # All strategies failed
        logger.error(f"All WebSocket connection strategies failed for {self.test_id}")
        return False
    
    def _get_connection_strategies(self, subprotocols: Optional[List[str]] = None) -> List[tuple]:
        """
        Get WebSocket connection strategies in order of preference.
        
        Args:
            subprotocols: Optional list of subprotocols to negotiate
            
        Returns:
            List of (strategy_name, strategy_params) tuples
        """
        strategies = []
        
        # Strategy 1: Full RFC 6455 subprotocol negotiation (if subprotocols provided)
        if subprotocols and len(subprotocols) > 0:
            strategies.append(("RFC6455_SUBPROTOCOL", {
                "subprotocols": subprotocols
            }))
        
        # Strategy 2: JWT auth subprotocol (if Authorization header present)
        if self.headers.get("Authorization"):
            # Extract JWT token from Authorization header
            auth_header = self.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                jwt_token = auth_header[7:]  # Remove "Bearer " prefix
                strategies.append(("JWT_AUTH_SUBPROTOCOL", {
                    "subprotocols": ["jwt-auth"]
                }))
        
        # Strategy 3: Simple connection without subprotocols (GCP Cloud Run fallback)
        strategies.append(("HEADER_ONLY", {
            # No subprotocols parameter - rely only on headers
        }))
        
        # Strategy 4: Minimal connection (last resort)
        strategies.append(("MINIMAL", {
            # Minimal parameters for maximum compatibility
            "ping_interval": None,  # Disable ping
            "ping_timeout": None,   # Disable ping timeout
        }))
        
        logger.debug(f"Generated {len(strategies)} connection strategies: {[s[0] for s in strategies]}")
        return strategies
    
    async def disconnect(self):
        """Disconnect from WebSocket server with cleanup."""
        if not self.is_connected:
            return
            
        try:
            # Cancel background tasks
            if self.listener_task and not self.listener_task.done():
                self.listener_task.cancel()
                try:
                    await self.listener_task
                except asyncio.CancelledError:
                    pass
            
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Close WebSocket connection
            if self.websocket:
                await self.websocket.close()
            
            self.is_connected = False
            logger.info(f"WebSocket client {self.test_id} disconnected")
            
        except Exception as e:
            logger.error(f"WebSocket disconnect error for {self.test_id}: {e}")
    
    async def send_message(self, event_type: WebSocketEventType, data: Dict[str, Any], 
                          user_id: Optional[str] = None, thread_id: Optional[str] = None) -> WebSocketMessage:
        """
        Send a structured message to the WebSocket server.
        
        Args:
            event_type: Type of event/message
            data: Message data
            user_id: Optional user ID
            thread_id: Optional thread ID
            
        Returns:
            The sent WebSocketMessage
        """
        if not self.is_connected or not self.websocket:
            raise RuntimeError(f"WebSocket client {self.test_id} not connected")
        
        message = WebSocketMessage(
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            thread_id=thread_id
        )
        
        try:
            message_json = json.dumps(message.to_dict())
            await self.websocket.send(message_json)
            
            self.sent_messages.append(message)
            logger.debug(f"Sent WebSocket message {message.message_id}: {event_type.value}")
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket message for {self.test_id}: {e}")
            raise
    
    async def send_raw_message(self, data: Union[str, bytes]):
        """Send raw data to WebSocket server."""
        if not self.is_connected or not self.websocket:
            raise RuntimeError(f"WebSocket client {self.test_id} not connected")
        
        try:
            await self.websocket.send(data)
            logger.debug(f"Sent raw WebSocket data for {self.test_id}")
        except Exception as e:
            logger.error(f"Failed to send raw WebSocket data for {self.test_id}: {e}")
            raise
    
    async def wait_for_message(self, event_type: Optional[WebSocketEventType] = None, 
                              timeout: float = 10.0) -> WebSocketMessage:
        """
        Wait for a specific message type or any message.
        
        Args:
            event_type: Optional specific event type to wait for
            timeout: Timeout in seconds
            
        Returns:
            The received WebSocketMessage
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if we already have the message
                if event_type:
                    for message in self.received_messages:
                        if message.event_type == event_type:
                            return message
                elif self.received_messages:
                    return self.received_messages[-1]
                
                # Wait for new message
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error waiting for message: {e}")
                break
        
        raise asyncio.TimeoutError(f"No message received within {timeout}s")
    
    async def wait_for_events(self, expected_events: List[WebSocketEventType], 
                             timeout: float = 30.0) -> Dict[WebSocketEventType, List[WebSocketMessage]]:
        """
        Wait for multiple specific events.
        
        Args:
            expected_events: List of expected event types
            timeout: Total timeout for all events
            
        Returns:
            Dictionary mapping event types to received messages
        """
        start_time = time.time()
        results: Dict[WebSocketEventType, List[WebSocketMessage]] = {}
        remaining_events = set(expected_events)
        
        while remaining_events and (time.time() - start_time < timeout):
            try:
                # Check received messages for expected events
                for message in self.received_messages:
                    if message.event_type in remaining_events:
                        if message.event_type not in results:
                            results[message.event_type] = []
                        results[message.event_type].append(message)
                        remaining_events.discard(message.event_type)
                
                if not remaining_events:
                    break
                    
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error waiting for events: {e}")
                break
        
        if remaining_events:
            missing = [evt.value for evt in remaining_events]
            raise asyncio.TimeoutError(f"Missing expected events: {missing}")
        
        return results
    
    def add_event_handler(self, event_type: WebSocketEventType, handler: Callable[[WebSocketMessage], None]):
        """Add event handler for specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def get_messages_by_type(self, event_type: WebSocketEventType) -> List[WebSocketMessage]:
        """Get all received messages of a specific type."""
        return [msg for msg in self.received_messages if msg.event_type == event_type]
    
    async def _mock_listen_for_messages(self):
        """Background task to simulate listening for messages in mock mode."""
        try:
            logger.debug(f"Mock WebSocket listener started for {self.test_id}")
            
            # Simulate some common WebSocket events for testing
            mock_events = [
                ("agent_started", {"agent": "triage", "status": "starting"}),
                ("agent_thinking", {"agent": "triage", "progress": "analyzing request"}),
                ("tool_executing", {"tool": "data_query", "status": "running"}),
                ("tool_completed", {"tool": "data_query", "result": "mock_result"}),
                ("agent_completed", {"agent": "triage", "status": "completed", "result": "Mock analysis complete"})
            ]
            
            while self.is_connected and self._mock_mode:
                for event_type_name, data in mock_events:
                    if not self.is_connected:
                        break
                        
                    try:
                        # Create mock message
                        message = WebSocketMessage(
                            event_type=WebSocketEventType(event_type_name),
                            data=data,
                            timestamp=datetime.now(),
                            message_id=f"mock_{uuid.uuid4().hex[:8]}",
                            user_id="mock_user",
                            thread_id="mock_thread"
                        )
                        
                        # Store message
                        self.received_messages.append(message)
                        
                        # Add to event tracking
                        if message.event_type not in self.received_events:
                            self.received_events[message.event_type] = []
                        self.received_events[message.event_type].append(message)
                        
                        logger.debug(f"Mock WebSocket received: {message.event_type.value}")
                        
                        # Call event handlers
                        if message.event_type in self.event_handlers:
                            for handler in self.event_handlers[message.event_type]:
                                try:
                                    handler(message)
                                except Exception as e:
                                    logger.error(f"Mock event handler error: {e}")
                        
                        # Small delay between mock events
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error in mock message processing: {e}")
                
                # Wait before repeating mock sequence
                await asyncio.sleep(2.0)
                
        except asyncio.CancelledError:
            logger.info(f"Mock WebSocket listener cancelled for {self.test_id}")
        except Exception as e:
            logger.error(f"Mock WebSocket listener error for {self.test_id}: {e}")
        finally:
            logger.debug(f"Mock WebSocket listener finished for {self.test_id}")
    
    async def _listen_for_messages(self):
        """Background task to listen for incoming messages."""
        try:
            async for raw_message in self.websocket:
                try:
                    # Parse message
                    if isinstance(raw_message, bytes):
                        raw_message = raw_message.decode('utf-8')
                    
                    message_data = json.loads(raw_message)
                    message = WebSocketMessage.from_dict(message_data)
                    
                    # Store message
                    self.received_messages.append(message)
                    
                    # Call event handlers
                    if message.event_type in self.event_handlers:
                        for handler in self.event_handlers[message.event_type]:
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"Event handler error: {e}")
                    
                    # Add to event tracking
                    if message.event_type not in self.received_events:
                        self.received_events[message.event_type] = []
                    self.received_events[message.event_type].append(message)
                    
                    logger.debug(f"Received WebSocket message: {message.event_type.value}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except ConnectionClosed:
            logger.info(f"WebSocket connection closed for {self.test_id}")
        except Exception as e:
            logger.error(f"WebSocket listener error for {self.test_id}: {e}")
        finally:
            self.is_connected = False
    
    async def _send_heartbeat(self):
        """Send periodic heartbeat messages."""
        try:
            while self.is_connected:
                await self.send_message(
                    WebSocketEventType.PING,
                    {"timestamp": time.time()}
                )
                await asyncio.sleep(30)  # Send every 30 seconds
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error for {self.test_id}: {e}")
    
    def _should_send_heartbeat(self) -> bool:
        """Check if heartbeat should be enabled."""
        return True  # Enable heartbeat by default for testing


class WebSocketTestUtility:
    """
    Single Source of Truth (SSOT) utility for ALL WebSocket testing needs.
    
    This utility provides:
    - Consistent WebSocket client management
    - Event tracking and verification
    - Connection lifecycle management
    - Performance monitoring
    - Multi-client testing support
    - Agent event testing utilities
    
    Features:
    - Automatic connection management
    - Event expectation verification
    - Performance metrics collection
    - Multi-user simulation
    - Real-time event monitoring
    - Connection resilience testing
    
    Usage:
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            await client.send_message(WebSocketEventType.PING, {})
            response = await client.wait_for_message()
    """
    
    def __init__(self, base_url: Optional[str] = None, env: Optional[Any] = None):
        """
        Initialize WebSocketTestUtility.
        
        Args:
            base_url: Base WebSocket server URL
            env: Environment manager instance
        """
        self.env = env or get_env()
        self.base_url = base_url or self._get_websocket_url()
        self.test_id = f"wstest_{uuid.uuid4().hex[:8]}"
        self.metrics = WebSocketTestMetrics()
        
        # Client management
        self.active_clients: Dict[str, WebSocketTestClient] = {}
        self.client_counter = 0
        
        # Test configuration
        self.default_timeout = float(self.env.get("WEBSOCKET_TEST_TIMEOUT", "30"))
        self.connection_retry_count = int(self.env.get("WEBSOCKET_RETRY_COUNT", "3"))
        self.enable_performance_monitoring = self.env.get("WS_ENABLE_PERF_MONITORING", "true").lower() == "true"
        
        # Event testing
        self.expected_event_patterns: List[List[WebSocketEventType]] = []
        self.global_event_handlers: Dict[WebSocketEventType, List[Callable]] = {}
        
        # Mock mode tracking
        self._mock_mode = False
        
        logger.debug(f"WebSocketTestUtility initialized [{self.test_id}]")
    
    def _get_websocket_url(self) -> str:
        """Get WebSocket server URL from environment."""
        # Try different environment variables
        ws_url = (
            self.env.get("WEBSOCKET_TEST_URL") or
            self.env.get("TEST_WEBSOCKET_URL") or
            self.env.get("WEBSOCKET_URL") or
            "ws://localhost:8000/ws"
        )
        
        # Ensure it's a WebSocket URL
        if ws_url.startswith("http://"):
            ws_url = ws_url.replace("http://", "ws://")
        elif ws_url.startswith("https://"):
            ws_url = ws_url.replace("https://", "wss://")
        elif not ws_url.startswith(("ws://", "wss://")):
            ws_url = f"ws://{ws_url}"
        
        return ws_url
    
    def _should_use_mock_mode(self) -> bool:
        """Determine if WebSocket tests should run in mock mode."""
        # Check environment variables for mock mode indicators
        mock_indicators = [
            self.env.get("WEBSOCKET_MOCK_MODE", "false").lower() == "true",
            self.env.get("NO_REAL_SERVERS", "false").lower() == "true", 
            self.env.get("TEST_OFFLINE", "false").lower() == "true",
            # Check if we're running unit tests (not integration/e2e)
            "unit" in self.env.get("PYTEST_CURRENT_TEST", "").lower(),
            # Check if Docker is not available
            self.env.get("DOCKER_AVAILABLE", "true").lower() == "false",
        ]
        
        # Also check if base URL indicates local testing without real server
        is_localhost_no_docker = (
            self.base_url.startswith("ws://localhost") and 
            self.env.get("DOCKER_AVAILABLE", "true").lower() == "false"
        )
        
        mock_mode = any(mock_indicators) or is_localhost_no_docker
        
        if mock_mode:
            logger.info(f"WebSocket mock mode detected: {mock_indicators}, localhost_no_docker={is_localhost_no_docker}")
        
        return mock_mode
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize WebSocket test environment."""
        start_time = time.time()
        
        try:
            # Check if we're in a test environment without real servers
            is_mock_mode = self._should_use_mock_mode()
            
            if is_mock_mode:
                # Use mock mode - don't verify server availability
                logger.info("WebSocketTestUtility running in mock mode (no real server verification)")
                self._mock_mode = True
            else:
                # Verify WebSocket server is reachable
                await self._verify_server_availability()
                self._mock_mode = False
            
            self.metrics.record_connection(time.time() - start_time)
            logger.info(f"WebSocketTestUtility initialized in {self.metrics.connection_time:.2f}s (mock_mode={self._mock_mode})")
            
        except Exception as e:
            self.metrics.add_error(f"Initialization failed: {str(e)}")
            logger.error(f"WebSocket test utility initialization failed: {e}")
            raise
    
    async def _verify_server_availability(self):
        """Verify WebSocket server is available."""
        try:
            # Simple connection test with Python 3.12 compatible timeout
            async with asyncio.timeout(5):
                test_ws = await websockets.connect(self.base_url, ping_timeout=5)
                await test_ws.close()
            logger.debug("WebSocket server availability verified")
        except Exception as e:
            raise RuntimeError(f"WebSocket server not available at {self.base_url}: {e}")
    
    async def create_test_client(self, user_id: Optional[str] = None, 
                               headers: Optional[Dict[str, str]] = None) -> WebSocketTestClient:
        """
        Create a WebSocket test client.
        
        Args:
            user_id: Optional user ID for client identification
            headers: Optional headers for connection
            
        Returns:
            WebSocketTestClient instance
        """
        self.client_counter += 1
        client_id = f"client_{self.client_counter}_{uuid.uuid4().hex[:6]}"
        
        # Prepare headers with authentication if user_id provided
        test_headers = headers or {}
        if user_id:
            test_headers["X-User-ID"] = user_id
            # Add mock authentication header for testing
            test_headers["Authorization"] = f"Bearer test_token_{user_id}"
        
        client = WebSocketTestClient(
            url=self.base_url,
            test_id=client_id,
            headers=test_headers
        )
        
        # Automatically connect client in mock mode if utility is in mock mode
        if hasattr(self, '_mock_mode') and self._mock_mode:
            success = await client.connect(mock_mode=True)
            if not success:
                logger.warning(f"Failed to connect client {client_id} in mock mode")
        
        self.active_clients[client_id] = client
        logger.debug(f"Created WebSocket test client: {client_id} (mock_mode={getattr(self, '_mock_mode', False)})")
        
        return client
    
    async def create_authenticated_client(self, user_id: str, token: Optional[str] = None) -> WebSocketTestClient:
        """
        Create an authenticated WebSocket test client.
        
        Args:
            user_id: User ID for authentication
            token: Optional authentication token
            
        Returns:
            Authenticated WebSocketTestClient
        """
        auth_token = token or f"test_token_{user_id}_{int(time.time())}"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-User-ID": user_id
        }
        
        return await self.create_test_client(user_id=user_id, headers=headers)
    
    async def create_multi_user_clients(self, user_count: int) -> List[WebSocketTestClient]:
        """
        Create multiple authenticated clients for multi-user testing.
        
        Args:
            user_count: Number of clients to create
            
        Returns:
            List of WebSocketTestClient instances
        """
        clients = []
        
        for i in range(user_count):
            user_id = f"testuser_{i+1}_{uuid.uuid4().hex[:6]}"
            client = await self.create_authenticated_client(user_id)
            await client.connect()
            clients.append(client)
        
        logger.info(f"Created {user_count} multi-user WebSocket clients")
        return clients
    
    @asynccontextmanager
    async def connected_client(self, user_id: Optional[str] = None) -> AsyncGenerator[WebSocketTestClient, None]:
        """
        Context manager for a connected WebSocket client.
        
        Args:
            user_id: Optional user ID
            
        Yields:
            Connected WebSocketTestClient
        """
        client = await self.create_test_client(user_id=user_id)
        
        try:
            connected = await client.connect(timeout=self.default_timeout)
            if not connected:
                raise RuntimeError(f"Failed to connect WebSocket client for user {user_id}")
            
            yield client
            
        finally:
            await client.disconnect()
    
    # ========== Agent Event Testing ==========
    
    async def test_agent_event_flow(self, client: WebSocketTestClient, 
                                  expected_events: List[WebSocketEventType],
                                  timeout: float = 30.0) -> Dict[WebSocketEventType, List[WebSocketMessage]]:
        """
        Test a complete agent event flow (agent_started -> agent_thinking -> tool_executing -> etc.).
        
        Args:
            client: WebSocket test client
            expected_events: List of expected events in order
            timeout: Total timeout for all events
            
        Returns:
            Dictionary of received events by type
        """
        logger.info(f"Testing agent event flow: {[e.value for e in expected_events]}")
        
        # Clear previous messages
        client.received_messages.clear()
        
        try:
            # Wait for expected events
            results = await client.wait_for_events(expected_events, timeout)
            
            # Verify event order if needed
            self._verify_event_order(client.received_messages, expected_events)
            
            # Record metrics
            for event_type in expected_events:
                self.metrics.record_event_emitted(event_type.value)
            
            logger.info(f"Agent event flow completed successfully")
            return results
            
        except asyncio.TimeoutError as e:
            self.metrics.add_error(f"Agent event flow timeout: {str(e)}")
            logger.error(f"Agent event flow failed: {e}")
            raise
    
    def _verify_event_order(self, received_messages: List[WebSocketMessage], 
                           expected_order: List[WebSocketEventType]):
        """Verify events were received in expected order."""
        received_events = [msg.event_type for msg in received_messages if msg.event_type in expected_order]
        
        if received_events != expected_order:
            received_names = [e.value for e in received_events]
            expected_names = [e.value for e in expected_order]
            self.metrics.add_warning(f"Event order mismatch: received {received_names}, expected {expected_names}")
    
    async def simulate_agent_execution(self, client: WebSocketTestClient, 
                                     user_request: str = "Test request") -> Dict[str, Any]:
        """
        Simulate a complete agent execution flow with all expected events.
        
        Args:
            client: WebSocket test client  
            user_request: User request to simulate
            
        Returns:
            Summary of execution results
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # Expected agent execution flow
        expected_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        start_time = time.time()
        
        try:
            # Send initial request (simulate user message)
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": user_request,
                    "role": "user",
                    "thread_id": thread_id,
                    "execution_id": execution_id
                },
                thread_id=thread_id
            )
            
            # Wait for agent execution events
            results = await self.test_agent_event_flow(client, expected_events)
            
            execution_time = time.time() - start_time
            
            return {
                "execution_id": execution_id,
                "thread_id": thread_id,
                "execution_time": execution_time,
                "events_received": len(results),
                "results": results,
                "success": True
            }
            
        except Exception as e:
            self.metrics.add_error(f"Agent execution simulation failed: {str(e)}")
            return {
                "execution_id": execution_id,
                "thread_id": thread_id,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "success": False
            }
    
    # ========== Performance Testing ==========
    
    async def run_performance_test(self, client_count: int = 5, 
                                 message_count: int = 10,
                                 test_duration: float = 60.0) -> Dict[str, Any]:
        """
        Run WebSocket performance test with multiple clients.
        
        Args:
            client_count: Number of concurrent clients
            message_count: Messages per client
            test_duration: Test duration in seconds
            
        Returns:
            Performance test results
        """
        logger.info(f"Running WebSocket performance test: {client_count} clients, {message_count} messages each")
        
        start_time = time.time()
        clients = []
        results = {
            "client_count": client_count,
            "message_count": message_count,
            "test_duration": 0.0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "messages_per_second": 0.0,
            "avg_latency": 0.0,
            "max_latency": 0.0,
            "connection_success_rate": 0.0,
            "errors": []
        }
        
        try:
            # Create and connect clients
            clients = await self.create_multi_user_clients(client_count)
            connected_clients = sum(1 for c in clients if c.is_connected)
            results["connection_success_rate"] = connected_clients / client_count
            
            # Send messages from each client
            tasks = []
            for i, client in enumerate(clients):
                if client.is_connected:
                    task = asyncio.create_task(
                        self._send_test_messages(client, message_count, f"client_{i}")
                    )
                    tasks.append(task)
            
            # Wait for all messages to be sent
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait a bit for responses
            await asyncio.sleep(2.0)
            
            # Collect results
            total_sent = sum(len(c.sent_messages) for c in clients)
            total_received = sum(len(c.received_messages) for c in clients)
            test_duration = time.time() - start_time
            
            results.update({
                "test_duration": test_duration,
                "total_messages_sent": total_sent,
                "total_messages_received": total_received,
                "messages_per_second": (total_sent + total_received) / test_duration if test_duration > 0 else 0,
                "avg_latency": self.metrics.avg_message_latency,
                "max_latency": self.metrics.max_message_latency
            })
            
            logger.info(f"Performance test completed: {total_sent} sent, {total_received} received")
            
        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"Performance test failed: {e}")
        finally:
            # Cleanup clients
            for client in clients:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
        
        return results
    
    async def _send_test_messages(self, client: WebSocketTestClient, count: int, client_name: str):
        """Send test messages from a client."""
        for i in range(count):
            try:
                await client.send_message(
                    WebSocketEventType.PING,
                    {
                        "message_number": i + 1,
                        "client_name": client_name,
                        "timestamp": time.time()
                    }
                )
                await asyncio.sleep(0.1)  # Small delay between messages
            except Exception as e:
                logger.error(f"Error sending message {i+1} from {client_name}: {e}")
    
    # ========== Connection Testing ==========
    
    async def test_connection_resilience(self, client: WebSocketTestClient, 
                                       disconnect_count: int = 3) -> Dict[str, Any]:
        """
        Test WebSocket connection resilience with forced disconnections.
        
        Args:
            client: WebSocket test client
            disconnect_count: Number of disconnect/reconnect cycles
            
        Returns:
            Resilience test results
        """
        results = {
            "disconnect_count": disconnect_count,
            "successful_reconnects": 0,
            "failed_reconnects": 0,
            "avg_reconnect_time": 0.0,
            "total_test_time": 0.0
        }
        
        start_time = time.time()
        reconnect_times = []
        
        try:
            for cycle in range(disconnect_count):
                logger.info(f"Connection resilience test cycle {cycle + 1}/{disconnect_count}")
                
                # Disconnect
                await client.disconnect()
                await asyncio.sleep(1.0)  # Wait before reconnecting
                
                # Reconnect
                reconnect_start = time.time()
                success = await client.connect(timeout=10.0)
                reconnect_time = time.time() - reconnect_start
                
                if success:
                    results["successful_reconnects"] += 1
                    reconnect_times.append(reconnect_time)
                    
                    # Test that connection works
                    await client.send_message(WebSocketEventType.PING, {"cycle": cycle + 1})
                else:
                    results["failed_reconnects"] += 1
                
                await asyncio.sleep(0.5)  # Brief pause between cycles
            
            # Calculate averages
            if reconnect_times:
                results["avg_reconnect_time"] = sum(reconnect_times) / len(reconnect_times)
            
            results["total_test_time"] = time.time() - start_time
            
            logger.info(f"Connection resilience test completed: "
                       f"{results['successful_reconnects']}/{disconnect_count} successful reconnects")
            
        except Exception as e:
            logger.error(f"Connection resilience test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    # ========== Cleanup and Resource Management ==========
    
    async def disconnect_all_clients(self):
        """Disconnect all active WebSocket clients."""
        disconnect_tasks = []
        
        for client in self.active_clients.values():
            if client.is_connected:
                disconnect_tasks.append(client.disconnect())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            logger.info(f"Disconnected {len(disconnect_tasks)} WebSocket clients")
    
    async def cleanup(self):
        """Clean up all WebSocket resources."""
        start_time = time.time()
        
        try:
            # Disconnect all clients
            await self.disconnect_all_clients()
            
            # Clear client registry
            self.active_clients.clear()
            
            cleanup_time = time.time() - start_time
            logger.info(f"WebSocketTestUtility cleanup completed in {cleanup_time:.2f}s")
            
            # Log metrics if there were issues or long cleanup
            if self.metrics.errors or self.metrics.warnings or cleanup_time > 2.0:
                logger.info(f"WebSocket test metrics: {self.metrics.to_dict()}")
                
        except Exception as e:
            logger.error(f"WebSocket test utility cleanup failed: {e}")
    
    # ========== Utility Methods ==========
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all WebSocket connections."""
        return {
            "total_clients": len(self.active_clients),
            "connected_clients": sum(1 for c in self.active_clients.values() if c.is_connected),
            "base_url": self.base_url,
            "test_id": self.test_id,
            "metrics": self.metrics.to_dict()
        }


# ========== Global WebSocket Utility Management ==========

_global_websocket_utility: Optional[WebSocketTestUtility] = None


async def get_websocket_test_utility(base_url: Optional[str] = None) -> WebSocketTestUtility:
    """Get or create global WebSocket test utility."""
    global _global_websocket_utility
    if _global_websocket_utility is None:
        _global_websocket_utility = WebSocketTestUtility(base_url)
        await _global_websocket_utility.initialize()
    
    return _global_websocket_utility


async def cleanup_global_websocket_utility():
    """Clean up global WebSocket test utility."""
    global _global_websocket_utility
    if _global_websocket_utility:
        await _global_websocket_utility.cleanup()
        _global_websocket_utility = None


async def create_test_websocket_manager():
    """
    Create a mock WebSocket manager for integration testing.
    
    This function provides SSOT compatibility with legacy tests that expect
    a WebSocketManager-like object for testing WebSocket notifications.
    
    Returns:
        Mock WebSocket manager with send_to_thread and broadcast methods
    """
    from unittest.mock import AsyncMock
    
    mock_manager = AsyncMock()
    
    # Configure send_to_thread to always return True (success)
    async def mock_send_to_thread(thread_id: str, message: dict) -> bool:
        """Mock implementation of send_to_thread."""
        logger.debug(f"Mock WebSocket send_to_thread: {thread_id} -> {message.get('type', 'unknown')}")
        return True
    
    # Configure broadcast to always return True (success)  
    async def mock_broadcast(message: dict) -> bool:
        """Mock implementation of broadcast."""
        logger.debug(f"Mock WebSocket broadcast: {message.get('type', 'unknown')}")
        return True
    
    mock_manager.send_to_thread.side_effect = mock_send_to_thread
    mock_manager.broadcast.side_effect = mock_broadcast
    
    return mock_manager


# Backward compatibility aliases
RealWebSocketTestClient = WebSocketTestClient
WebSocketTestHelper = WebSocketTestUtility  # Alias for WebSocketTestUtility

# Create alias for backward compatibility and Issue #485 fix
websocket_test_utilities = WebSocketTestUtility

# Import new WebSocket infrastructure components for backward compatibility
from .websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory
from .websocket_auth_helper import WebSocketAuthHelper
from .websocket_bridge_test_helper import WebSocketBridgeTestHelper
from .communication_metrics_collector import CommunicationMetricsCollector

# Export SSOT WebSocket utilities
__all__ = [
    'WebSocketTestUtility',
    'WebSocketTestClient',
    'WebSocketTestHelper',
    'RealWebSocketTestClient',
    'WebSocketMessage', 
    'WebSocketEventType',
    'WebSocketTestMetrics',
    'get_websocket_test_utility',
    'cleanup_global_websocket_utility',
    'create_test_websocket_manager',
    'websocket_test_utilities',  # Issue #485 fix: Missing import
    # New WebSocket infrastructure components
    'WebSocketTestInfrastructureFactory',
    'WebSocketAuthHelper', 
    'WebSocketBridgeTestHelper',
    'CommunicationMetricsCollector'
]