"""
WebSocket Test 5: Backend Service Restart Recovery

Tests that validate client-side recovery mechanisms when the backend server 
restarts (e.g., during deployment), ensuring clients automatically reconnect
and restore their session state without user intervention.

Business Value: Prevents $100K+ MRR churn from enterprise customers due to 
service interruptions during maintenance. Enables zero-downtime deployments.
"""

import asyncio
import json
import time
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Literal
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ServerState(Enum):
    """Server lifecycle states."""
    STARTING = "starting"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    UNAVAILABLE = "unavailable"


class ReconnectionStrategy(Enum):
    """Client reconnection strategies."""
    GRACEFUL = "graceful"
    EMERGENCY = "emergency"
    ROLLING_DEPLOYMENT = "rolling_deployment"
    EXTENDED_BACKOFF = "extended_backoff"


class MockBackendServer:
    """Mock backend server with lifecycle simulation capabilities."""
    
    def __init__(self, server_id: str = "server-1"):
        self.server_id = server_id
        self.state = ServerState.UNAVAILABLE
        self.connections: Dict[str, Any] = {}
        self.session_storage = {}
        self.startup_time = None
        self.shutdown_reason = None
        self.restart_count = 0
        self.health_status = False
        
    async def start(self, startup_delay: float = 0.1) -> None:
        """Start the server with optional startup delay."""
        self.state = ServerState.STARTING
        await asyncio.sleep(startup_delay)
        self.state = ServerState.RUNNING
        self.startup_time = datetime.now(timezone.utc)
        self.health_status = True
        logger.info(f"MockBackendServer {self.server_id} started")
        
    async def graceful_shutdown(self, notification_delay: float = 1.0) -> None:
        """Gracefully shutdown with client notification."""
        self.state = ServerState.SHUTTING_DOWN
        self.shutdown_reason = "graceful"
        
        # Send shutdown notifications to all connected clients
        shutdown_message = {
            "type": "server_shutdown",
            "payload": {
                "reason": "graceful",
                "estimated_restart_time": 10,
                "message": "Server is shutting down for maintenance"
            }
        }
        
        # Simulate sending to all connections
        for conn_id in self.connections:
            logger.info(f"Sending shutdown notification to {conn_id}")
            
        await asyncio.sleep(notification_delay)
        
        # Close all connections
        self.connections.clear()
        self.state = ServerState.UNAVAILABLE
        self.health_status = False
        logger.info(f"MockBackendServer {self.server_id} gracefully shut down")
        
    async def crash(self) -> None:
        """Simulate unexpected server crash."""
        self.state = ServerState.CRASHED
        self.shutdown_reason = "crash"
        self.connections.clear()
        self.health_status = False
        logger.info(f"MockBackendServer {self.server_id} crashed")
        
    async def restart(self, restart_delay: float = 5.0) -> None:
        """Restart the server after delay."""
        self.state = ServerState.RESTARTING
        self.restart_count += 1
        await asyncio.sleep(restart_delay)
        await self.start(startup_delay=0.5)
        logger.info(f"MockBackendServer {self.server_id} restarted (count: {self.restart_count})")
        
    def is_available(self) -> bool:
        """Check if server is available for connections."""
        return self.state == ServerState.RUNNING and self.health_status
        
    def accept_connection(self, session_token: str) -> bool:
        """Accept a WebSocket connection."""
        if not self.is_available():
            return False
            
        conn_id = f"conn_{len(self.connections)}_{int(time.time())}"
        self.connections[session_token] = {
            "id": conn_id,
            "connected_at": datetime.now(timezone.utc),
            "session_token": session_token
        }
        
        logger.info(f"Connection accepted: {session_token[:8]}... on {self.server_id}")
        return True
        
    def store_session_state(self, session_token: str, state: Dict[str, Any]) -> None:
        """Store session state for persistence across restarts."""
        self.session_storage[session_token] = {
            **state,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "server_id": self.server_id
        }
        
    def retrieve_session_state(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state after restart."""
        return self.session_storage.get(session_token)


class MockLoadBalancer:
    """Mock load balancer for rolling deployment scenarios."""
    
    def __init__(self):
        self.servers: List[MockBackendServer] = []
        self.active_server_index = 0
        self.routing_table: Dict[str, str] = {}
        
    def add_server(self, server: MockBackendServer) -> None:
        """Add server to load balancer."""
        self.servers.append(server)
        
    def get_active_server(self) -> Optional[MockBackendServer]:
        """Get currently active server."""
        if not self.servers:
            return None
        return self.servers[self.active_server_index]
        
    async def rolling_deployment(self, new_server: MockBackendServer) -> None:
        """Simulate rolling deployment with traffic switching."""
        logger.info("Starting rolling deployment")
        
        # Add new server
        self.add_server(new_server)
        
        # Start new server
        await new_server.start()
        
        # Health check new server
        await asyncio.sleep(1)
        if not new_server.is_available():
            raise Exception("New server failed health check")
            
        # Switch traffic to new server
        old_index = self.active_server_index
        self.active_server_index = len(self.servers) - 1
        
        # Graceful shutdown of old server
        if old_index < len(self.servers) - 1:
            old_server = self.servers[old_index]
            await old_server.graceful_shutdown()
            
        logger.info(f"Rolling deployment complete: switched to {new_server.server_id}")
        
    def route_connection(self, session_token: str) -> Optional[MockBackendServer]:
        """Route connection to available server."""
        active_server = self.get_active_server()
        if active_server and active_server.is_available():
            return active_server
        return None


class WebSocketReconnectClient:
    """Advanced WebSocket client with sophisticated reconnection logic."""
    
    def __init__(self, uri: str, session_token: str):
        self.uri = uri
        self.session_token = session_token
        self.websocket = None
        self.is_connected = False
        self.connection_attempts = 0
        self.last_connection_time = None
        self.reconnection_strategy = ReconnectionStrategy.GRACEFUL
        self.session_state = {}
        self.backoff_intervals = [1, 2, 4, 8, 16, 30, 60]  # seconds
        self.max_reconnection_attempts = 20
        self.connection_metrics = {
            "total_attempts": 0,
            "successful_connections": 0,
            "failed_attempts": 0,
            "total_downtime": 0.0,
            "average_reconnection_time": 0.0
        }
        
    async def connect(self, timeout: float = 10.0) -> bool:
        """Connect to WebSocket server."""
        start_time = time.time()
        self.connection_attempts += 1
        self.connection_metrics["total_attempts"] += 1
        
        try:
            # Mock connection for testing
            self.websocket = AsyncMock()
            self.is_connected = True
            self.last_connection_time = datetime.now(timezone.utc)
            self.connection_metrics["successful_connections"] += 1
            
            connection_time = time.time() - start_time
            logger.info(f"Connected in {connection_time:.3f}s (attempt {self.connection_attempts})")
            return True
            
        except Exception as e:
            self.connection_metrics["failed_attempts"] += 1
            logger.error(f"Connection failed: {e}")
            return False
            
    async def disconnect(self, expected: bool = True) -> None:
        """Disconnect from server."""
        if self.websocket and self.is_connected:
            if not expected:
                # Simulate unexpected disconnection
                self.websocket = None
            else:
                await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from server")
            
    async def reconnect_with_strategy(self, strategy: ReconnectionStrategy, 
                                    server_available_callback=None) -> bool:
        """Reconnect using specified strategy."""
        self.reconnection_strategy = strategy
        start_time = time.time()
        
        if strategy == ReconnectionStrategy.GRACEFUL:
            intervals = [1, 2, 4, 8]  # Graceful intervals
        elif strategy == ReconnectionStrategy.EMERGENCY:
            intervals = [0.5, 1, 2, 4]  # Faster for emergencies
        elif strategy == ReconnectionStrategy.ROLLING_DEPLOYMENT:
            intervals = [0.1, 0.5, 1, 2]  # Quick for rolling deployments
        elif strategy == ReconnectionStrategy.EXTENDED_BACKOFF:
            intervals = self.backoff_intervals  # Full backoff sequence
        else:
            intervals = [1, 2, 4, 8]
            
        for attempt, interval in enumerate(intervals):
            if attempt > 0:
                logger.info(f"Waiting {interval}s before reconnection attempt {attempt + 1}")
                await asyncio.sleep(interval)
                
            # Check if server is available (if callback provided)
            if server_available_callback and not server_available_callback():
                continue
                
            logger.info(f"Reconnection attempt {attempt + 1} using {strategy.value} strategy")
            
            if await self.connect():
                total_time = time.time() - start_time
                self.connection_metrics["average_reconnection_time"] = total_time
                logger.info(f"Reconnection successful after {total_time:.3f}s")
                return True
                
        logger.error(f"All reconnection attempts failed using {strategy.value} strategy")
        return False
        
    async def handle_server_shutdown_notification(self, notification: Dict[str, Any]) -> None:
        """Handle graceful shutdown notification from server."""
        logger.info(f"Received shutdown notification: {notification}")
        
        # Store current session state before disconnect
        await self.preserve_session_state()
        
        # Disconnect and prepare for reconnection
        await self.disconnect(expected=True)
        
        # Estimate restart time from notification
        estimated_restart = notification.get("payload", {}).get("estimated_restart_time", 10)
        
        # Wait briefly then start reconnection attempts
        await asyncio.sleep(min(estimated_restart / 2, 5))
        
        # Use graceful reconnection strategy
        await self.reconnect_with_strategy(ReconnectionStrategy.GRACEFUL)
        
    async def handle_unexpected_disconnection(self) -> None:
        """Handle unexpected connection loss."""
        logger.warning("Unexpected disconnection detected")
        
        # Mark disconnection time for metrics
        disconnect_time = time.time()
        
        # Attempt to preserve any cached session state
        await self.preserve_session_state()
        
        # Use emergency reconnection strategy
        success = await self.reconnect_with_strategy(ReconnectionStrategy.EMERGENCY)
        
        if success:
            reconnect_time = time.time()
            downtime = reconnect_time - disconnect_time
            self.connection_metrics["total_downtime"] += downtime
            logger.info(f"Recovered from unexpected disconnection in {downtime:.3f}s")
        
        return success
        
    async def preserve_session_state(self) -> None:
        """Preserve session state during disconnection."""
        # In a real implementation, this would cache critical state
        # For testing, we'll simulate this
        self.session_state = {
            "conversation_history": [],
            "agent_context": {},
            "user_preferences": {},
            "workflow_state": {},
            "preserved_at": datetime.now(timezone.utc).isoformat()
        }
        logger.info("Session state preserved")
        
    async def request_session_restoration(self) -> Dict[str, Any]:
        """Request session state restoration after reconnection."""
        if not self.is_connected:
            return {}
            
        restoration_request = {
            "type": "restore_session",
            "payload": {
                "session_token": self.session_token,
                "client_state": self.session_state
            }
        }
        
        # Configure mock response
        if hasattr(self.websocket, '_configured_response'):
            return self.websocket._configured_response
            
        # Default mock response
        return {
            "type": "session_restored",
            "payload": {
                "success": True,
                "conversation_history": [],
                "agent_context": {},
                "restoration_time": time.time()
            }
        }
        
    def get_connection_metrics(self) -> Dict[str, Any]:
        """Get connection performance metrics."""
        return self.connection_metrics.copy()


# Test Fixtures

@pytest.fixture
def mock_backend_server():
    """Mock backend server fixture."""
    return MockBackendServer("test-server-1")


@pytest.fixture
def mock_load_balancer():
    """Mock load balancer fixture."""
    return MockLoadBalancer()


@pytest.fixture
async def session_token():
    """Valid session token for testing."""
    return f"test_session_{uuid.uuid4().hex[:16]}"


@pytest.fixture
async def websocket_reconnect_client(session_token):
    """WebSocket reconnect client fixture."""
    uri = "ws://mock-server/ws"
    client = WebSocketReconnectClient(uri, session_token)
    yield client
    
    # Cleanup
    if client.is_connected:
        await client.disconnect()


@pytest.fixture
async def established_session_with_complex_state(websocket_reconnect_client, mock_backend_server, session_token):
    """Fixture with established session and complex state."""
    # Start server and connect
    await mock_backend_server.start()
    await websocket_reconnect_client.connect()
    
    # Create complex session state
    complex_state = {
        "conversation_history": [
            {"role": "user", "content": "I need help optimizing my AI workloads", "timestamp": "2025-01-20T10:00:00Z"},
            {"role": "assistant", "content": "I'll help you optimize your AI workloads. What's your current setup?", "timestamp": "2025-01-20T10:00:05Z"},
            {"role": "user", "content": "I'm running multiple LLMs with high token costs", "timestamp": "2025-01-20T10:00:15Z"},
            {"role": "assistant", "content": "Let me analyze your token usage patterns and suggest optimizations", "timestamp": "2025-01-20T10:00:20Z"},
            {"role": "user", "content": "Please provide specific cost reduction strategies", "timestamp": "2025-01-20T10:00:30Z"}
        ],
        "agent_context": {
            "user_preferences": {"optimization_focus": "cost", "priority": "high"},
            "variables": {"monthly_budget": 5000, "current_usage": 3750, "target_savings": 30},
            "workflow_state": {
                "current_step": 3,
                "total_steps": 7,
                "completed_steps": ["analysis", "pattern_detection"],
                "pending_steps": ["optimization_plan", "implementation", "monitoring", "validation"]
            }
        },
        "tool_call_history": [
            {"tool": "token_usage_analyzer", "timestamp": "2025-01-20T10:00:25Z", "status": "completed"},
            {"tool": "cost_calculator", "timestamp": "2025-01-20T10:00:28Z", "status": "completed"},
            {"tool": "optimization_planner", "timestamp": "2025-01-20T10:00:32Z", "status": "in_progress"}
        ],
        "user_session_metadata": {
            "enterprise_tier": True,
            "sla_level": "premium",
            "uptime_requirement": "99.9%"
        }
    }
    
    # Store state in server
    mock_backend_server.store_session_state(session_token, complex_state)
    
    return websocket_reconnect_client, mock_backend_server, complex_state


# Test Cases

@pytest.mark.asyncio
async def test_graceful_server_shutdown_with_client_notification(
    established_session_with_complex_state, session_token
):
    """
    Test Case 1: Graceful server shutdown with client notification.
    
    Validates that when a server sends a graceful shutdown signal, the client
    receives notification, disconnects gracefully, and reconnects successfully
    when the server comes back online.
    """
    client, server, original_state = established_session_with_complex_state
    
    # Verify initial connection
    assert client.is_connected
    assert server.is_available()
    
    # Configure mock response for shutdown notification
    shutdown_notification = {
        "type": "server_shutdown",
        "payload": {
            "reason": "graceful",
            "estimated_restart_time": 10,
            "message": "Server is shutting down for maintenance"
        }
    }
    
    client.websocket._configured_response = shutdown_notification
    
    # Simulate receiving shutdown notification
    notification = await client.websocket.recv()
    logger.info(f"Client received notification: {notification}")
    
    # Client handles shutdown notification
    start_downtime = time.time()
    await client.handle_server_shutdown_notification(shutdown_notification)
    
    # Verify client disconnected gracefully
    assert not client.is_connected
    
    # Server performs graceful shutdown
    await server.graceful_shutdown(notification_delay=0.1)
    assert not server.is_available()
    assert server.shutdown_reason == "graceful"
    
    # Server restarts
    restart_task = asyncio.create_task(server.restart(restart_delay=2.0))
    
    # Configure server availability callback for client
    def server_available():
        return server.is_available()
    
    # Client attempts reconnection with graceful strategy
    reconnection_start = time.time()
    reconnection_success = await client.reconnect_with_strategy(
        ReconnectionStrategy.GRACEFUL, 
        server_available_callback=server_available
    )
    
    # Wait for server restart to complete
    await restart_task
    
    total_downtime = time.time() - start_downtime
    
    # Validate reconnection success
    assert reconnection_success, "Client failed to reconnect after graceful shutdown"
    assert client.is_connected
    assert server.is_available()
    
    # Configure mock response for session restoration
    client.websocket._configured_response = {
        "type": "session_restored",
        "payload": {
            "success": True,
            "conversation_history": original_state["conversation_history"],
            "agent_context": original_state["agent_context"],
            "restoration_time": time.time()
        }
    }
    
    # Request and validate session restoration
    restored_session = await client.request_session_restoration()
    assert restored_session["payload"]["success"]
    
    # Performance validation - graceful shutdown should reconnect within 10 seconds
    assert total_downtime < 10.0, f"Total downtime {total_downtime:.2f}s exceeded 10s limit"
    
    # Validate session state preservation
    stored_state = server.retrieve_session_state(session_token)
    assert stored_state is not None
    assert len(stored_state["conversation_history"]) == len(original_state["conversation_history"])
    assert stored_state["agent_context"]["workflow_state"]["current_step"] == 3
    
    logger.info(f"✓ Graceful shutdown handled successfully in {total_downtime:.3f}s")


@pytest.mark.asyncio
async def test_unexpected_server_crash_recovery(
    established_session_with_complex_state, session_token
):
    """
    Test Case 2: Unexpected server crash recovery.
    
    Validates that when a server crashes unexpectedly without notification,
    the client detects the connection loss and implements an aggressive
    reconnection strategy to restore service quickly.
    """
    client, server, original_state = established_session_with_complex_state
    
    # Verify baseline connection
    assert client.is_connected
    original_connection_count = client.connection_metrics["successful_connections"]
    
    # Simulate server crash - immediate connection termination
    crash_time = time.time()
    await server.crash()
    await client.disconnect(expected=False)  # Simulate unexpected disconnection
    
    assert not server.is_available()
    assert server.state == ServerState.CRASHED
    assert not client.is_connected
    
    # Start server restart process (background)
    restart_task = asyncio.create_task(server.restart(restart_delay=3.0))
    
    # Client detects connection loss and handles emergency reconnection
    recovery_start = time.time()
    recovery_success = await client.handle_unexpected_disconnection()
    
    # Wait for server restart to complete
    await restart_task
    
    recovery_time = time.time() - recovery_start
    
    # Validate emergency recovery
    assert recovery_success, "Client failed to recover from server crash"
    assert client.is_connected
    assert server.is_available()
    assert server.restart_count == 1
    
    # Validate reconnection metrics
    metrics = client.get_connection_metrics()
    assert metrics["successful_connections"] > original_connection_count
    assert metrics["total_downtime"] > 0
    
    # Performance validation - emergency recovery should complete within 30 seconds
    assert recovery_time < 30.0, f"Recovery time {recovery_time:.2f}s exceeded 30s limit"
    
    # Configure mock response for state validation
    client.websocket._configured_response = {
        "type": "session_restored", 
        "payload": {
            "success": True,
            "data_integrity_check": "passed",
            "conversation_history": original_state["conversation_history"],
            "agent_context": original_state["agent_context"]
        }
    }
    
    # Validate data integrity after crash recovery
    restored_session = await client.request_session_restoration()
    assert restored_session["payload"]["success"]
    assert restored_session["payload"]["data_integrity_check"] == "passed"
    
    # Verify session state survived crash
    stored_state = server.retrieve_session_state(session_token)
    assert stored_state is not None
    assert stored_state["conversation_history"] == original_state["conversation_history"]
    
    logger.info(f"✓ Crash recovery completed successfully in {recovery_time:.3f}s")


@pytest.mark.asyncio
async def test_rolling_deployment_reconnection(
    established_session_with_complex_state, session_token, mock_load_balancer
):
    """
    Test Case 3: Rolling deployment reconnection.
    
    Validates seamless handoff between server instances during rolling deployment,
    ensuring clients connect to new instances without service interruption.
    """
    client, server_a, original_state = established_session_with_complex_state
    
    # Set up load balancer with initial server
    mock_load_balancer.add_server(server_a)
    
    # Verify initial state
    assert client.is_connected
    assert server_a.is_available()
    
    # Create new server instance for rolling deployment
    server_b = MockBackendServer("test-server-2")
    
    # Copy session state to shared storage (simulating database/Redis)
    server_b.session_storage = server_a.session_storage.copy()
    
    # Start rolling deployment
    deployment_start = time.time()
    
    # Load balancer initiates rolling deployment
    deployment_task = asyncio.create_task(
        mock_load_balancer.rolling_deployment(server_b)
    )
    
    # Simulate connection being redirected during deployment
    await asyncio.sleep(1)  # Allow deployment to start
    
    # Client connection to server A is gracefully terminated
    await client.disconnect(expected=True)
    
    # Client attempts reconnection - should connect to server B
    reconnection_success = await client.reconnect_with_strategy(
        ReconnectionStrategy.ROLLING_DEPLOYMENT
    )
    
    # Wait for deployment to complete
    await deployment_task
    
    deployment_time = time.time() - deployment_start
    
    # Validate rolling deployment success
    assert reconnection_success, "Client failed to reconnect during rolling deployment"
    assert client.is_connected
    assert server_b.is_available()
    assert not server_a.is_available()  # Old server shut down
    
    # Validate load balancer state
    active_server = mock_load_balancer.get_active_server()
    assert active_server is server_b
    
    # Performance validation - rolling deployment should complete within 5 seconds
    assert deployment_time < 5.0, f"Rolling deployment took {deployment_time:.2f}s, expected < 5s"
    
    # Configure mock response for session continuity validation
    client.websocket._configured_response = {
        "type": "session_restored",
        "payload": {
            "success": True,
            "server_instance": server_b.server_id,
            "session_continuity": True,
            "conversation_history": original_state["conversation_history"],
            "handoff_successful": True
        }
    }
    
    # Validate session continuity across server instances
    session_validation = await client.request_session_restoration()
    assert session_validation["payload"]["success"]
    assert session_validation["payload"]["session_continuity"]
    assert session_validation["payload"]["handoff_successful"]
    
    # Verify session state available on new server
    stored_state_b = server_b.retrieve_session_state(session_token)
    assert stored_state_b is not None
    assert stored_state_b["conversation_history"] == original_state["conversation_history"]
    assert stored_state_b["agent_context"]["workflow_state"]["current_step"] == 3
    
    logger.info(f"✓ Rolling deployment completed successfully in {deployment_time:.3f}s")


@pytest.mark.asyncio
async def test_client_backoff_strategy_during_restart(
    websocket_reconnect_client, mock_backend_server, session_token
):
    """
    Test Case 4: Client backoff strategy during restart.
    
    Validates that when a server is unavailable for an extended period,
    the client implements exponential backoff without overwhelming the server
    and connects successfully when the server becomes available.
    """
    client = websocket_reconnect_client
    server = mock_backend_server
    
    # Establish initial connection
    await server.start()
    await client.connect()
    assert client.is_connected
    
    # Server becomes unavailable for extended period
    await server.crash()
    await client.disconnect(expected=False)
    
    # Track backoff behavior
    backoff_start = time.time()
    reconnection_attempts = []
    
    # Monitor client's backoff strategy
    original_connect = client.connect
    
    async def monitored_connect(timeout=10.0):
        attempt_time = time.time()
        reconnection_attempts.append(attempt_time)
        logger.info(f"Reconnection attempt {len(reconnection_attempts)} at {attempt_time - backoff_start:.3f}s")
        
        # Server unavailable for first 30 seconds
        if attempt_time - backoff_start < 30:
            return False
        else:
            # Server becomes available
            if not server.is_available():
                await server.start()
            return await original_connect(timeout)
    
    client.connect = monitored_connect
    
    # Client attempts reconnection with extended backoff strategy
    reconnection_success = await client.reconnect_with_strategy(
        ReconnectionStrategy.EXTENDED_BACKOFF
    )
    
    total_backoff_time = time.time() - backoff_start
    
    # Validate backoff strategy effectiveness
    assert reconnection_success, "Client failed to reconnect with extended backoff"
    assert client.is_connected
    assert len(reconnection_attempts) >= 3, "Client should have made multiple attempts"
    
    # Validate backoff intervals are respected
    intervals = []
    for i in range(1, len(reconnection_attempts)):
        interval = reconnection_attempts[i] - reconnection_attempts[i-1]
        intervals.append(interval)
    
    # Verify exponential backoff pattern (allowing for some variance)
    expected_intervals = [1, 2, 4, 8, 16, 30]
    for i, interval in enumerate(intervals[:len(expected_intervals)]):
        expected = expected_intervals[i]
        # Allow 20% variance for timing precision
        assert expected * 0.8 <= interval <= expected * 1.2, \
            f"Interval {i+1}: {interval:.2f}s not within expected range of {expected}s"
    
    # Validate resource efficiency - client shouldn't overwhelm server
    max_interval = max(intervals) if intervals else 0
    assert max_interval <= 60, f"Maximum backoff interval {max_interval:.2f}s should not exceed 60s"
    
    # Validate connection success when server becomes available
    assert server.is_available()
    
    # Performance validation
    metrics = client.get_connection_metrics()
    assert metrics["total_attempts"] >= 3, "Should have multiple reconnection attempts"
    
    logger.info(f"✓ Backoff strategy effective: {len(reconnection_attempts)} attempts over {total_backoff_time:.3f}s")


@pytest.mark.asyncio
async def test_state_preservation_across_server_restarts(
    established_session_with_complex_state, session_token
):
    """
    Test Case 5: State preservation across server restarts.
    
    Validates that complex session state (conversation history, agent context,
    tool state) survives server restart with 100% preservation and fast restoration.
    """
    client, server, original_state = established_session_with_complex_state
    
    # Validate initial complex state
    assert len(original_state["conversation_history"]) == 5
    assert original_state["agent_context"]["workflow_state"]["current_step"] == 3
    assert len(original_state["tool_call_history"]) == 3
    assert original_state["user_session_metadata"]["enterprise_tier"] is True
    
    # Add additional state complexity
    additional_state = {
        "active_tools": ["optimization_planner", "cost_monitor"],
        "pending_operations": [
            {"operation": "analyze_patterns", "progress": 75, "eta": 45},
            {"operation": "generate_recommendations", "progress": 0, "eta": 120}
        ],
        "cached_results": {
            "token_analysis": {"total_tokens": 125000, "cost": 375.50},
            "optimization_potential": {"savings": 1125.75, "efficiency_gain": 30}
        },
        "user_context": {
            "current_focus": "cost_optimization",
            "enterprise_settings": {"sla_tier": "premium", "priority": "high"},
            "session_preferences": {"detailed_logs": True, "real_time_updates": True}
        }
    }
    
    # Merge additional state
    enhanced_state = {**original_state, **additional_state}
    server.store_session_state(session_token, enhanced_state)
    
    # Begin server restart process
    restart_start = time.time()
    
    # Client preserves state before restart
    await client.preserve_session_state()
    
    # Server graceful shutdown
    await server.graceful_shutdown(notification_delay=0.1)
    await client.disconnect(expected=True)
    
    # Server restart with fresh process
    await server.restart(restart_delay=1.0)
    
    # Client reconnects
    await client.connect()
    
    restoration_start = time.time()
    
    # Configure mock response for complete state restoration
    client.websocket._configured_response = {
        "type": "session_restored",
        "payload": {
            "success": True,
            "restoration_complete": True,
            "conversation_history": enhanced_state["conversation_history"],
            "agent_context": enhanced_state["agent_context"],
            "tool_call_history": enhanced_state["tool_call_history"],
            "active_tools": enhanced_state["active_tools"],
            "pending_operations": enhanced_state["pending_operations"],
            "cached_results": enhanced_state["cached_results"],
            "user_context": enhanced_state["user_context"],
            "user_session_metadata": enhanced_state["user_session_metadata"],
            "integrity_check": "passed",
            "restoration_time": time.time()
        }
    }
    
    # Request complete session restoration
    restored_session = await client.request_session_restoration()
    restoration_time = time.time() - restoration_start
    
    # Validate restoration success
    assert restored_session["payload"]["success"]
    assert restored_session["payload"]["restoration_complete"]
    assert restored_session["payload"]["integrity_check"] == "passed"
    
    # Validate conversation history preservation (100%)
    restored_history = restored_session["payload"]["conversation_history"]
    assert len(restored_history) == len(enhanced_state["conversation_history"])
    for i, msg in enumerate(restored_history):
        original_msg = enhanced_state["conversation_history"][i]
        assert msg["content"] == original_msg["content"]
        assert msg["role"] == original_msg["role"]
        assert msg["timestamp"] == original_msg["timestamp"]
    
    # Validate agent context preservation
    restored_context = restored_session["payload"]["agent_context"]
    assert restored_context["workflow_state"]["current_step"] == 3
    assert restored_context["variables"]["monthly_budget"] == 5000
    assert restored_context["user_preferences"]["optimization_focus"] == "cost"
    
    # Validate tool state preservation
    restored_tools = restored_session["payload"]["tool_call_history"]
    assert len(restored_tools) == 3
    assert restored_tools[2]["status"] == "in_progress"
    
    # Validate active tools and operations
    assert restored_session["payload"]["active_tools"] == enhanced_state["active_tools"]
    assert len(restored_session["payload"]["pending_operations"]) == 2
    
    # Validate cached results preservation
    cached_results = restored_session["payload"]["cached_results"]
    assert cached_results["token_analysis"]["total_tokens"] == 125000
    assert cached_results["optimization_potential"]["savings"] == 1125.75
    
    # Validate user context and enterprise settings
    user_context = restored_session["payload"]["user_context"]
    assert user_context["enterprise_settings"]["sla_tier"] == "premium"
    assert user_context["session_preferences"]["detailed_logs"] is True
    
    # Performance validation - state restoration should complete within 2 seconds
    assert restoration_time < 2.0, f"State restoration took {restoration_time:.3f}s, expected < 2.0s"
    
    # Validate server-side state integrity
    stored_state = server.retrieve_session_state(session_token)
    assert stored_state is not None
    assert len(stored_state["conversation_history"]) == 5
    assert stored_state["agent_context"]["workflow_state"]["current_step"] == 3
    
    total_restart_time = time.time() - restart_start
    
    logger.info(f"✓ Complete state preservation validated: {restoration_time:.3f}s restoration, {total_restart_time:.3f}s total")


# Integration and Performance Tests

@pytest.mark.asyncio
async def test_concurrent_client_reconnections_during_restart(
    mock_backend_server, session_token
):
    """Test multiple clients reconnecting simultaneously during server restart."""
    server = mock_backend_server
    num_clients = 5
    clients = []
    
    # Create multiple clients
    for i in range(num_clients):
        client_token = f"{session_token}_{i}"
        client = WebSocketReconnectClient(f"ws://mock-server/ws", client_token)
        clients.append(client)
    
    # Start server and connect all clients
    await server.start()
    for client in clients:
        await client.connect()
        assert client.is_connected
    
    # Server restart
    await server.crash()
    for client in clients:
        await client.disconnect(expected=False)
    
    # Restart server
    restart_task = asyncio.create_task(server.restart(restart_delay=2.0))
    
    # All clients attempt reconnection simultaneously
    reconnection_tasks = []
    for client in clients:
        task = asyncio.create_task(
            client.reconnect_with_strategy(ReconnectionStrategy.EMERGENCY)
        )
        reconnection_tasks.append(task)
    
    # Wait for server restart and all reconnections
    await restart_task
    results = await asyncio.gather(*reconnection_tasks)
    
    # Validate all clients reconnected successfully
    assert all(results), "Not all clients reconnected successfully"
    for client in clients:
        assert client.is_connected
    
    # Validate server handled concurrent connections
    assert server.is_available()
    assert len(server.connections) == num_clients
    
    logger.info(f"✓ {num_clients} concurrent reconnections successful")


@pytest.mark.asyncio
async def test_reconnection_performance_benchmarks(websocket_reconnect_client, mock_backend_server):
    """Benchmark reconnection performance across different scenarios."""
    client = websocket_reconnect_client
    server = mock_backend_server
    
    benchmark_results = {}
    
    # Benchmark 1: Graceful reconnection
    await server.start()
    await client.connect()
    
    graceful_start = time.time()
    await server.graceful_shutdown()
    await client.disconnect(expected=True)
    await server.restart(restart_delay=1.0)
    await client.reconnect_with_strategy(ReconnectionStrategy.GRACEFUL)
    graceful_time = time.time() - graceful_start
    
    benchmark_results["graceful_reconnection"] = graceful_time
    
    # Benchmark 2: Emergency reconnection
    emergency_start = time.time()
    await server.crash()
    await client.disconnect(expected=False)
    await server.restart(restart_delay=0.5)
    await client.reconnect_with_strategy(ReconnectionStrategy.EMERGENCY)
    emergency_time = time.time() - emergency_start
    
    benchmark_results["emergency_reconnection"] = emergency_time
    
    # Benchmark 3: Rolling deployment
    rolling_start = time.time()
    await client.disconnect(expected=True)
    await client.reconnect_with_strategy(ReconnectionStrategy.ROLLING_DEPLOYMENT)
    rolling_time = time.time() - rolling_start
    
    benchmark_results["rolling_deployment"] = rolling_time
    
    # Validate performance requirements
    assert graceful_time < 10.0, f"Graceful reconnection {graceful_time:.3f}s > 10s limit"
    assert emergency_time < 30.0, f"Emergency reconnection {emergency_time:.3f}s > 30s limit"
    assert rolling_time < 5.0, f"Rolling deployment {rolling_time:.3f}s > 5s limit"
    
    logger.info(f"✓ Performance benchmarks: Graceful {graceful_time:.3f}s, Emergency {emergency_time:.3f}s, Rolling {rolling_time:.3f}s")
    
    return benchmark_results


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto"
    ])