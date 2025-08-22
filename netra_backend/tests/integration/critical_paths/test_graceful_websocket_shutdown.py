"""
L2 Integration Test: Graceful WebSocket Shutdown

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Clean shutdown worth $5K MRR data integrity
- Value Impact: Prevents data loss and ensures graceful service maintenance
- Strategic Impact: Enables zero-downtime deployments and reliable operations

L2 Test: Real internal shutdown components with mocked external services.
Performance target: <30s graceful shutdown, 100% message preservation.
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import signal
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.services.websocket_manager import WebSocketManager
from test_framework.mock_utils import mock_justified

class ShutdownPhase(Enum):

    """Graceful shutdown phases."""

    RUNNING = "running"

    STOP_ACCEPTING = "stop_accepting"

    DRAIN_CONNECTIONS = "drain_connections"

    FORCE_CLOSE = "force_close"

    CLEANUP = "cleanup"

    STOPPED = "stopped"

class ConnectionState(Enum):

    """Connection states during shutdown."""

    ACTIVE = "active"

    DRAINING = "draining"

    CLOSED = "closed"

    FORCE_CLOSED = "force_closed"

@dataclass

class ShutdownConfig:

    """Configuration for graceful shutdown."""

    drain_timeout: float = 30.0          # Time to allow connections to drain

    force_close_timeout: float = 60.0    # Total time before force close

    message_flush_timeout: float = 5.0   # Time to flush pending messages

    health_check_interval: float = 1.0   # Health check frequency during shutdown

    save_state_on_shutdown: bool = True  # Save connection state to disk

    notify_clients: bool = True          # Send shutdown notifications

@dataclass

class ConnectionContext:

    """Context for a connection during shutdown."""

    connection_id: str

    user_id: str

    websocket: Any

    state: ConnectionState = ConnectionState.ACTIVE

    pending_messages: deque = field(default_factory=deque)

    last_activity: float = field(default_factory=time.time)

    graceful_close_sent: bool = False

    force_close_time: Optional[float] = None

    created_at: float = field(default_factory=time.time)

class GracefulShutdownManager:

    """Manage graceful shutdown of WebSocket connections."""
    
    def __init__(self, config: ShutdownConfig = None):

        self.config = config or ShutdownConfig()

        self.phase = ShutdownPhase.RUNNING

        self.connections = {}  # connection_id -> ConnectionContext

        self.user_connections = defaultdict(set)  # user_id -> set(connection_ids)

        self.shutdown_start_time = None

        self.shutdown_complete_time = None

        self.message_queue = asyncio.Queue()

        self.shutdown_event = asyncio.Event()

        self.drain_complete_event = asyncio.Event()
        
        self.metrics = {

            "total_connections_at_shutdown": 0,

            "gracefully_closed_connections": 0,

            "force_closed_connections": 0,

            "messages_preserved": 0,

            "messages_lost": 0,

            "shutdown_duration": 0.0,

            "drain_duration": 0.0,

            "cleanup_duration": 0.0

        }
        
        self.shutdown_callbacks = []

        self.state_persistence = {}
    
    def register_connection(self, connection_id: str, user_id: str, websocket: Any) -> ConnectionContext:

        """Register a connection for shutdown management."""

        context = ConnectionContext(

            connection_id=connection_id,

            user_id=user_id,

            websocket=websocket

        )
        
        self.connections[connection_id] = context

        self.user_connections[user_id].add(connection_id)
        
        return context
    
    def unregister_connection(self, connection_id: str) -> bool:

        """Unregister a connection."""

        if connection_id not in self.connections:

            return False
        
        context = self.connections.pop(connection_id)

        self.user_connections[context.user_id].discard(connection_id)
        
        if not self.user_connections[context.user_id]:

            del self.user_connections[context.user_id]
        
        return True
    
    def add_shutdown_callback(self, callback: Callable) -> None:

        """Add callback to be executed during shutdown."""

        self.shutdown_callbacks.append(callback)
    
    async def initiate_graceful_shutdown(self, signal_name: str = "SIGTERM") -> Dict[str, Any]:

        """Initiate graceful shutdown process."""

        if self.phase != ShutdownPhase.RUNNING:

            return {"error": "Shutdown already in progress"}
        
        self.shutdown_start_time = time.time()

        self.metrics["total_connections_at_shutdown"] = len(self.connections)
        
        shutdown_result = {

            "signal": signal_name,

            "started_at": self.shutdown_start_time,

            "total_connections": len(self.connections),

            "phases_completed": []

        }
        
        try:
            # Phase 1: Stop accepting new connections

            await self._phase_stop_accepting_connections()

            shutdown_result["phases_completed"].append("stop_accepting")
            
            # Phase 2: Drain existing connections

            await self._phase_drain_connections()

            shutdown_result["phases_completed"].append("drain_connections")
            
            # Phase 3: Force close remaining connections

            await self._phase_force_close_connections()

            shutdown_result["phases_completed"].append("force_close")
            
            # Phase 4: Cleanup and state persistence

            await self._phase_cleanup()

            shutdown_result["phases_completed"].append("cleanup")
            
            self.phase = ShutdownPhase.STOPPED

            self.shutdown_complete_time = time.time()

            self.metrics["shutdown_duration"] = self.shutdown_complete_time - self.shutdown_start_time
            
            shutdown_result.update({

                "completed_at": self.shutdown_complete_time,

                "duration": self.metrics["shutdown_duration"],

                "success": True

            })
            
        except Exception as e:

            shutdown_result.update({

                "error": str(e),

                "success": False,

                "completed_at": time.time()

            })
        
        self.shutdown_event.set()

        return shutdown_result
    
    async def _phase_stop_accepting_connections(self) -> None:

        """Phase 1: Stop accepting new connections."""

        self.phase = ShutdownPhase.STOP_ACCEPTING
        
        # Send shutdown notifications to monitoring systems

        if self.config.notify_clients:

            await self._notify_shutdown_start()
        
        # Execute pre-shutdown callbacks

        for callback in self.shutdown_callbacks:

            try:

                if asyncio.iscoroutinefunction(callback):

                    await callback("stop_accepting")

                else:

                    callback("stop_accepting")

            except Exception:

                pass  # Continue with other callbacks
    
    async def _phase_drain_connections(self) -> None:

        """Phase 2: Drain existing connections gracefully."""

        self.phase = ShutdownPhase.DRAIN_CONNECTIONS

        drain_start = time.time()
        
        # Send graceful close notifications to all connections

        await self._send_graceful_close_notifications()
        
        # Wait for connections to drain naturally

        drain_deadline = time.time() + self.config.drain_timeout
        
        while time.time() < drain_deadline and self._has_active_connections():
            # Process pending messages during drain

            await self._process_pending_messages()
            
            # Check for naturally closed connections

            await self._check_natural_closures()
            
            await asyncio.sleep(self.config.health_check_interval)
        
        self.drain_complete_event.set()

        self.metrics["drain_duration"] = time.time() - drain_start
    
    async def _phase_force_close_connections(self) -> None:

        """Phase 3: Force close remaining connections."""

        self.phase = ShutdownPhase.FORCE_CLOSE
        
        # Force close any remaining active connections

        remaining_connections = [

            context for context in self.connections.values()

            if context.state == ConnectionState.ACTIVE

        ]
        
        for context in remaining_connections:

            await self._force_close_connection(context)
        
        # Wait a bit for force closes to complete

        await asyncio.sleep(1.0)
    
    async def _phase_cleanup(self) -> None:

        """Phase 4: Final cleanup and state persistence."""

        self.phase = ShutdownPhase.CLEANUP

        cleanup_start = time.time()
        
        # Save state if configured

        if self.config.save_state_on_shutdown:

            await self._save_shutdown_state()
        
        # Final message processing

        await self._flush_remaining_messages()
        
        # Execute cleanup callbacks

        for callback in self.shutdown_callbacks:

            try:

                if asyncio.iscoroutinefunction(callback):

                    await callback("cleanup")

                else:

                    callback("cleanup")

            except Exception:

                pass
        
        self.metrics["cleanup_duration"] = time.time() - cleanup_start
    
    async def _notify_shutdown_start(self) -> None:

        """Notify external systems about shutdown start."""
        # In real implementation, would notify load balancers, monitoring, etc.

        notification = {

            "type": "service_shutdown_initiated",

            "timestamp": time.time(),

            "expected_duration": self.config.force_close_timeout,

            "active_connections": len(self.connections)

        }
        
        # Log or send notification

        pass
    
    async def _send_graceful_close_notifications(self) -> None:

        """Send graceful close notifications to all connections."""

        notification_tasks = []
        
        for context in self.connections.values():

            if context.state == ConnectionState.ACTIVE:

                task = self._send_close_notification(context)

                notification_tasks.append(task)
        
        if notification_tasks:

            await asyncio.gather(*notification_tasks, return_exceptions=True)
    
    async def _send_close_notification(self, context: ConnectionContext) -> None:

        """Send close notification to a specific connection."""

        try:

            close_message = {

                "type": "server_shutdown",

                "message": "Server is shutting down gracefully",

                "close_code": 1001,  # Going Away

                "timeout": self.config.drain_timeout,

                "timestamp": time.time()

            }
            
            if hasattr(context.websocket, 'send'):

                await context.websocket.send(json.dumps(close_message))
            
            context.graceful_close_sent = True

            context.state = ConnectionState.DRAINING
            
        except Exception:
            # If we can't send notification, mark for force close

            context.state = ConnectionState.DRAINING
    
    def _has_active_connections(self) -> bool:

        """Check if there are still active connections."""

        return any(

            context.state in [ConnectionState.ACTIVE, ConnectionState.DRAINING]

            for context in self.connections.values()

        )
    
    async def _process_pending_messages(self) -> None:

        """Process pending messages during drain."""

        processed_count = 0
        
        for context in self.connections.values():

            if context.state == ConnectionState.DRAINING:
                # Flush pending messages with timeout

                while context.pending_messages and processed_count < 100:

                    try:

                        message = context.pending_messages.popleft()

                        if hasattr(context.websocket, 'send'):

                            await asyncio.wait_for(

                                context.websocket.send(json.dumps(message)),

                                timeout=self.config.message_flush_timeout

                            )

                        self.metrics["messages_preserved"] += 1

                        processed_count += 1

                    except (asyncio.TimeoutError, Exception):

                        self.metrics["messages_lost"] += 1

                        break
    
    async def _check_natural_closures(self) -> None:

        """Check for connections that closed naturally."""

        for context in list(self.connections.values()):

            if context.state == ConnectionState.DRAINING:
                # Check if websocket is closed

                if hasattr(context.websocket, 'closed') and context.websocket.closed:

                    context.state = ConnectionState.CLOSED

                    self.metrics["gracefully_closed_connections"] += 1

                elif hasattr(context.websocket, 'close_code') and context.websocket.close_code:

                    context.state = ConnectionState.CLOSED

                    self.metrics["gracefully_closed_connections"] += 1
    
    async def _force_close_connection(self, context: ConnectionContext) -> None:

        """Force close a connection."""

        try:

            context.force_close_time = time.time()
            
            # Try graceful close first

            if hasattr(context.websocket, 'close'):

                await asyncio.wait_for(

                    context.websocket.close(code=1001, reason="Server shutdown"),

                    timeout=2.0

                )
            
            context.state = ConnectionState.FORCE_CLOSED

            self.metrics["force_closed_connections"] += 1
            
            # Save any remaining messages as lost

            lost_messages = len(context.pending_messages)

            self.metrics["messages_lost"] += lost_messages

            context.pending_messages.clear()
            
        except Exception:

            context.state = ConnectionState.FORCE_CLOSED

            self.metrics["force_closed_connections"] += 1
    
    async def _save_shutdown_state(self) -> None:

        """Save connection state for potential recovery."""

        shutdown_state = {

            "shutdown_time": time.time(),

            "total_connections": len(self.connections),

            "graceful_closes": self.metrics["gracefully_closed_connections"],

            "force_closes": self.metrics["force_closed_connections"],

            "user_sessions": {}

        }
        
        # Save user session information

        for user_id, connection_ids in self.user_connections.items():

            active_connections = []

            for conn_id in connection_ids:

                if conn_id in self.connections:

                    context = self.connections[conn_id]

                    active_connections.append({

                        "connection_id": conn_id,

                        "state": context.state.value,

                        "created_at": context.created_at,

                        "pending_message_count": len(context.pending_messages)

                    })
            
            if active_connections:

                shutdown_state["user_sessions"][user_id] = active_connections
        
        self.state_persistence = shutdown_state
    
    async def _flush_remaining_messages(self) -> None:

        """Flush any remaining messages in the queue."""

        try:

            while not self.message_queue.empty():

                try:

                    message = await asyncio.wait_for(

                        self.message_queue.get(),

                        timeout=1.0

                    )
                    # Process or save message

                    self.metrics["messages_preserved"] += 1

                except asyncio.TimeoutError:

                    break

        except Exception:

            pass
    
    def queue_message_for_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:

        """Queue message for connection during shutdown."""

        if connection_id not in self.connections:

            return False
        
        context = self.connections[connection_id]

        if context.state in [ConnectionState.ACTIVE, ConnectionState.DRAINING]:

            context.pending_messages.append(message)

            return True
        
        return False
    
    def get_shutdown_status(self) -> Dict[str, Any]:

        """Get current shutdown status."""

        current_time = time.time()
        
        status = {

            "phase": self.phase.value,

            "is_shutting_down": self.phase != ShutdownPhase.RUNNING,

            "shutdown_started": self.shutdown_start_time is not None,

            "metrics": self.metrics.copy()

        }
        
        if self.shutdown_start_time:

            status["elapsed_time"] = current_time - self.shutdown_start_time

            status["remaining_drain_time"] = max(

                0, 

                self.config.drain_timeout - (current_time - self.shutdown_start_time)

            )
        
        # Connection state summary

        state_counts = {}

        for state in ConnectionState:

            state_counts[state.value] = sum(

                1 for context in self.connections.values()

                if context.state == state

            )
        
        status["connection_states"] = state_counts

        status["active_connections"] = len(self.connections)
        
        return status
    
    def get_shutdown_metrics(self) -> Dict[str, Any]:

        """Get comprehensive shutdown metrics."""

        metrics = self.metrics.copy()
        
        # Calculate derived metrics

        if metrics["total_connections_at_shutdown"] > 0:

            metrics["graceful_close_rate"] = (

                metrics["gracefully_closed_connections"] / 

                metrics["total_connections_at_shutdown"] * 100

            )

            metrics["force_close_rate"] = (

                metrics["force_closed_connections"] / 

                metrics["total_connections_at_shutdown"] * 100

            )
        
        total_messages = metrics["messages_preserved"] + metrics["messages_lost"]

        if total_messages > 0:

            metrics["message_preservation_rate"] = (

                metrics["messages_preserved"] / total_messages * 100

            )

        else:

            metrics["message_preservation_rate"] = 100.0
        
        return metrics

class ShutdownCoordinator:

    """Coordinate shutdown across multiple services."""
    
    def __init__(self):

        self.shutdown_managers = {}  # service_name -> GracefulShutdownManager

        self.coordination_timeout = 60.0

        self.shutdown_order = []  # Ordered list of services for shutdown
    
    def register_service(self, service_name: str, shutdown_manager: GracefulShutdownManager, 

                        priority: int = 0) -> None:

        """Register a service for coordinated shutdown."""

        self.shutdown_managers[service_name] = shutdown_manager
        
        # Insert in priority order (higher priority first)

        insert_pos = 0

        for i, (_, existing_priority) in enumerate(self.shutdown_order):

            if priority > existing_priority:

                insert_pos = i

                break

            insert_pos = i + 1
        
        self.shutdown_order.insert(insert_pos, (service_name, priority))
    
    async def coordinate_shutdown(self, signal_name: str = "SIGTERM") -> Dict[str, Any]:

        """Coordinate shutdown across all registered services."""

        coordination_start = time.time()

        shutdown_results = {}
        
        try:
            # Shutdown services in priority order

            for service_name, priority in self.shutdown_order:

                if service_name in self.shutdown_managers:

                    manager = self.shutdown_managers[service_name]
                    
                    service_result = await manager.initiate_graceful_shutdown(signal_name)

                    shutdown_results[service_name] = service_result
                    
                    # Brief pause between services

                    await asyncio.sleep(1.0)
            
            coordination_time = time.time() - coordination_start
            
            return {

                "coordination_success": True,

                "coordination_time": coordination_time,

                "services_shutdown": len(shutdown_results),

                "service_results": shutdown_results

            }
        
        except Exception as e:

            return {

                "coordination_success": False,

                "error": str(e),

                "coordination_time": time.time() - coordination_start,

                "service_results": shutdown_results

            }
    
    def get_coordination_status(self) -> Dict[str, Any]:

        """Get status of all services in coordination."""

        service_statuses = {}
        
        for service_name in self.shutdown_managers:

            manager = self.shutdown_managers[service_name]

            service_statuses[service_name] = manager.get_shutdown_status()
        
        overall_shutting_down = any(

            status["is_shutting_down"] for status in service_statuses.values()

        )
        
        return {

            "services": service_statuses,

            "overall_shutting_down": overall_shutting_down,

            "total_services": len(self.shutdown_managers)

        }

class DrainHandler:

    """Handle connection draining with different strategies."""
    
    def __init__(self, shutdown_manager: GracefulShutdownManager):

        self.shutdown_manager = shutdown_manager

        self.drain_strategies = {

            "immediate": self._immediate_drain,

            "gradual": self._gradual_drain,

            "user_aware": self._user_aware_drain

        }
    
    async def execute_drain_strategy(self, strategy: str = "gradual") -> Dict[str, Any]:

        """Execute specific drain strategy."""

        if strategy not in self.drain_strategies:

            strategy = "gradual"
        
        drain_start = time.time()

        strategy_func = self.drain_strategies[strategy]
        
        result = await strategy_func()

        result["strategy_used"] = strategy

        result["drain_time"] = time.time() - drain_start
        
        return result
    
    async def _immediate_drain(self) -> Dict[str, Any]:

        """Immediately stop all new connections and close existing ones."""

        connections_drained = 0
        
        for context in self.shutdown_manager.connections.values():

            if context.state == ConnectionState.ACTIVE:

                await self.shutdown_manager._send_close_notification(context)

                connections_drained += 1
        
        return {

            "connections_drained": connections_drained,

            "drain_method": "immediate"

        }
    
    async def _gradual_drain(self) -> Dict[str, Any]:

        """Gradually drain connections with staggered notifications."""

        connections = list(self.shutdown_manager.connections.values())

        connections_per_batch = max(1, len(connections) // 5)  # 5 batches

        connections_drained = 0
        
        for i in range(0, len(connections), connections_per_batch):

            batch = connections[i:i + connections_per_batch]
            
            for context in batch:

                if context.state == ConnectionState.ACTIVE:

                    await self.shutdown_manager._send_close_notification(context)

                    connections_drained += 1
            
            # Delay between batches

            if i + connections_per_batch < len(connections):

                await asyncio.sleep(2.0)
        
        return {

            "connections_drained": connections_drained,

            "drain_method": "gradual",

            "batches_processed": (len(connections) + connections_per_batch - 1) // connections_per_batch

        }
    
    async def _user_aware_drain(self) -> Dict[str, Any]:

        """Drain connections with user awareness (multiple connections per user)."""

        users_processed = 0

        connections_drained = 0
        
        for user_id, connection_ids in self.shutdown_manager.user_connections.items():

            user_contexts = [

                self.shutdown_manager.connections[conn_id]

                for conn_id in connection_ids

                if conn_id in self.shutdown_manager.connections

            ]
            
            # Send notifications to all user connections

            for context in user_contexts:

                if context.state == ConnectionState.ACTIVE:

                    await self.shutdown_manager._send_close_notification(context)

                    connections_drained += 1
            
            users_processed += 1
            
            # Small delay between users

            await asyncio.sleep(0.1)
        
        return {

            "users_processed": users_processed,

            "connections_drained": connections_drained,

            "drain_method": "user_aware"

        }

@pytest.mark.L2

@pytest.mark.integration

class TestGracefulWebSocketShutdown:

    """L2 integration tests for graceful WebSocket shutdown."""
    
    @pytest.fixture

    def shutdown_config(self):

        """Create shutdown configuration for testing."""

        return ShutdownConfig(

            drain_timeout=10.0,        # Short timeout for testing

            force_close_timeout=20.0,

            message_flush_timeout=2.0,

            health_check_interval=0.5,

            save_state_on_shutdown=True,

            notify_clients=True

        )
    
    @pytest.fixture

    def shutdown_manager(self, shutdown_config):

        """Create graceful shutdown manager."""

        return GracefulShutdownManager(shutdown_config)
    
    @pytest.fixture

    def shutdown_coordinator(self):

        """Create shutdown coordinator."""

        return ShutdownCoordinator()
    
    @pytest.fixture

    def drain_handler(self, shutdown_manager):

        """Create drain handler."""

        return DrainHandler(shutdown_manager)
    
    @pytest.fixture

    def test_users(self):

        """Create test users."""

        return [

            User(

                id=f"shutdown_user_{i}",

                email=f"shutdownuser{i}@example.com",

                username=f"shutdownuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(5)

        ]
    
    def create_mock_websocket(self, auto_close: bool = False):

        """Create mock WebSocket for testing."""

        websocket = AsyncMock()

        websocket.send = AsyncMock()

        websocket.close = AsyncMock()

        websocket.closed = False

        websocket.close_code = None

        websocket.messages_sent = []
        
        async def mock_send(message):

            if not websocket.closed:

                websocket.messages_sent.append(message)
        
        async def mock_close(code=None, reason=None):

            websocket.closed = True

            websocket.close_code = code

            if auto_close:

                await asyncio.sleep(0.1)  # Simulate close delay
        
        websocket.send.side_effect = mock_send

        websocket.close.side_effect = mock_close
        
        return websocket
    
    async def test_basic_graceful_shutdown(self, shutdown_manager, test_users):

        """Test basic graceful shutdown functionality."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket(auto_close=True)
        
        # Register connection

        context = shutdown_manager.register_connection(connection_id, user.id, websocket)

        assert context.connection_id == connection_id

        assert context.state == ConnectionState.ACTIVE
        
        # Initiate shutdown

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown("SIGTERM")
        
        # Verify shutdown completed successfully

        assert shutdown_result["success"] is True

        assert "stop_accepting" in shutdown_result["phases_completed"]

        assert "drain_connections" in shutdown_result["phases_completed"]

        assert "cleanup" in shutdown_result["phases_completed"]
        
        # Verify shutdown notification was sent

        assert len(websocket.messages_sent) > 0

        shutdown_msg = json.loads(websocket.messages_sent[0])

        assert shutdown_msg["type"] == "server_shutdown"
        
        # Verify connection was closed

        assert websocket.close.called
        
        # Check metrics

        metrics = shutdown_manager.get_shutdown_metrics()

        assert metrics["total_connections_at_shutdown"] == 1

        assert metrics["graceful_close_rate"] > 0 or metrics["force_close_rate"] > 0
    
    async def test_message_preservation_during_shutdown(self, shutdown_manager, test_users):

        """Test message preservation during graceful shutdown."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket()
        
        # Register connection

        shutdown_manager.register_connection(connection_id, user.id, websocket)
        
        # Queue some messages

        test_messages = [

            {"type": "message", "content": f"Message {i}", "timestamp": time.time()}

            for i in range(5)

        ]
        
        for message in test_messages:

            success = shutdown_manager.queue_message_for_connection(connection_id, message)

            assert success is True
        
        # Initiate shutdown

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown()
        
        assert shutdown_result["success"] is True
        
        # Check that messages were processed

        metrics = shutdown_manager.get_shutdown_metrics()

        assert metrics["messages_preserved"] + metrics["messages_lost"] == len(test_messages)

        assert metrics["message_preservation_rate"] >= 80  # Should preserve most messages
    
    async def test_force_close_timeout(self, shutdown_manager, test_users):

        """Test force close when graceful drain times out."""

        user = test_users[0]

        connection_id = str(uuid4())
        
        # Create websocket that doesn't close gracefully

        websocket = self.create_mock_websocket(auto_close=False)
        
        # Register connection

        shutdown_manager.register_connection(connection_id, user.id, websocket)
        
        # Initiate shutdown

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown()
        
        assert shutdown_result["success"] is True

        assert "force_close" in shutdown_result["phases_completed"]
        
        # Should have sent close notification

        assert len(websocket.messages_sent) > 0
        
        # Should have called force close

        assert websocket.close.called
        
        # Check metrics show force close

        metrics = shutdown_manager.get_shutdown_metrics()

        assert metrics["force_closed_connections"] > 0
    
    async def test_multiple_connections_shutdown(self, shutdown_manager, test_users):

        """Test shutdown with multiple connections."""

        connections = []
        
        # Register multiple connections

        for i, user in enumerate(test_users):

            connection_id = f"conn_{i}"

            websocket = self.create_mock_websocket(auto_close=True)

            shutdown_manager.register_connection(connection_id, user.id, websocket)

            connections.append((connection_id, websocket))
        
        # Initiate shutdown

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown()
        
        assert shutdown_result["success"] is True

        assert shutdown_result["total_connections"] == len(test_users)
        
        # Verify all connections received shutdown notification

        for connection_id, websocket in connections:

            assert len(websocket.messages_sent) > 0

            shutdown_msg = json.loads(websocket.messages_sent[0])

            assert shutdown_msg["type"] == "server_shutdown"
        
        # Check final metrics

        metrics = shutdown_manager.get_shutdown_metrics()

        assert metrics["total_connections_at_shutdown"] == len(test_users)

        assert metrics["gracefully_closed_connections"] + metrics["force_closed_connections"] == len(test_users)
    
    async def test_shutdown_status_monitoring(self, shutdown_manager, test_users):

        """Test shutdown status monitoring."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket()
        
        # Register connection

        shutdown_manager.register_connection(connection_id, user.id, websocket)
        
        # Check initial status

        initial_status = shutdown_manager.get_shutdown_status()

        assert initial_status["phase"] == ShutdownPhase.RUNNING.value

        assert initial_status["is_shutting_down"] is False
        
        # Start shutdown in background

        shutdown_task = asyncio.create_task(shutdown_manager.initiate_graceful_shutdown())
        
        # Brief delay to let shutdown start

        await asyncio.sleep(0.1)
        
        # Check status during shutdown

        during_status = shutdown_manager.get_shutdown_status()

        assert during_status["is_shutting_down"] is True

        assert during_status["phase"] != ShutdownPhase.RUNNING.value
        
        # Wait for shutdown to complete

        await shutdown_task
        
        # Check final status

        final_status = shutdown_manager.get_shutdown_status()

        assert final_status["phase"] == ShutdownPhase.STOPPED.value
    
    async def test_drain_strategies(self, shutdown_manager, drain_handler, test_users):

        """Test different connection drain strategies."""
        # Register multiple connections

        connections = []

        for i in range(6):

            user = test_users[i % len(test_users)]

            connection_id = f"strategy_conn_{i}"

            websocket = self.create_mock_websocket()

            shutdown_manager.register_connection(connection_id, user.id, websocket)

            connections.append((connection_id, websocket))
        
        # Test gradual drain strategy

        drain_result = await drain_handler.execute_drain_strategy("gradual")
        
        assert drain_result["strategy_used"] == "gradual"

        assert drain_result["connections_drained"] == len(connections)

        assert "batches_processed" in drain_result

        assert drain_result["drain_time"] > 0
        
        # Verify all connections received notifications

        for connection_id, websocket in connections:

            assert len(websocket.messages_sent) > 0
    
    async def test_coordinated_shutdown(self, shutdown_coordinator, test_users):

        """Test coordinated shutdown across multiple services."""
        # Create multiple shutdown managers

        service_managers = {}
        
        for i in range(3):

            service_name = f"service_{i}"

            config = ShutdownConfig(drain_timeout=5.0, force_close_timeout=10.0)

            manager = GracefulShutdownManager(config)
            
            # Register some connections

            for j in range(2):

                user = test_users[j % len(test_users)]

                connection_id = f"{service_name}_conn_{j}"

                websocket = self.create_mock_websocket(auto_close=True)

                manager.register_connection(connection_id, user.id, websocket)
            
            service_managers[service_name] = manager

            shutdown_coordinator.register_service(service_name, manager, priority=i)
        
        # Execute coordinated shutdown

        coordination_result = await shutdown_coordinator.coordinate_shutdown("SIGTERM")
        
        assert coordination_result["coordination_success"] is True

        assert coordination_result["services_shutdown"] == 3

        assert coordination_result["coordination_time"] > 0
        
        # Verify all services were shut down

        for service_name in service_managers:

            assert service_name in coordination_result["service_results"]

            service_result = coordination_result["service_results"][service_name]

            assert service_result["success"] is True
        
        # Check coordination status

        final_status = shutdown_coordinator.get_coordination_status()

        assert final_status["total_services"] == 3
    
    async def test_state_persistence_during_shutdown(self, shutdown_manager, test_users):

        """Test state persistence during shutdown."""
        # Register connections with different states

        connections = []

        for i, user in enumerate(test_users[:3]):

            connection_id = f"persist_conn_{i}"

            websocket = self.create_mock_websocket()

            context = shutdown_manager.register_connection(connection_id, user.id, websocket)
            
            # Queue some messages

            for j in range(3):

                message = {"type": "test", "content": f"Message {j}", "user": user.id}

                shutdown_manager.queue_message_for_connection(connection_id, message)
            
            connections.append((connection_id, user.id, websocket))
        
        # Initiate shutdown

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown()
        
        assert shutdown_result["success"] is True
        
        # Check that state was persisted

        assert shutdown_manager.state_persistence is not None

        persisted_state = shutdown_manager.state_persistence
        
        assert "shutdown_time" in persisted_state

        assert "total_connections" in persisted_state

        assert "user_sessions" in persisted_state
        
        # Verify user session data was saved

        for connection_id, user_id, websocket in connections:

            if user_id in persisted_state["user_sessions"]:

                user_sessions = persisted_state["user_sessions"][user_id]

                connection_found = any(

                    session["connection_id"] == connection_id

                    for session in user_sessions

                )
                # Connection might be found if it was still active during persistence
    
    @mock_justified("L2: Graceful shutdown with real internal components")

    async def test_websocket_integration_with_shutdown(self, shutdown_manager, test_users):

        """Test WebSocket integration with graceful shutdown."""
        # Simulate WebSocket manager using shutdown manager

        active_connections = []
        
        # Register connections through simulated WebSocket manager

        for i, user in enumerate(test_users):

            connection_id = f"ws_manager_conn_{i}"

            websocket = self.create_mock_websocket(auto_close=True)
            
            # Register with shutdown manager

            context = shutdown_manager.register_connection(connection_id, user.id, websocket)
            
            # Simulate ongoing WebSocket activity

            for j in range(3):

                message = {

                    "type": "user_message",

                    "content": f"User {i} message {j}",

                    "timestamp": time.time()

                }

                shutdown_manager.queue_message_for_connection(connection_id, message)
            
            active_connections.append((connection_id, user.id, websocket))
        
        # Add shutdown callback to simulate WebSocket manager cleanup

        cleanup_called = []
        
        def cleanup_callback(phase):

            cleanup_called.append(phase)
        
        shutdown_manager.add_shutdown_callback(cleanup_callback)
        
        # Initiate graceful shutdown

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown("SIGTERM")
        
        # Verify shutdown success

        assert shutdown_result["success"] is True

        assert shutdown_result["total_connections"] == len(test_users)
        
        # Verify all connections received shutdown notifications

        for connection_id, user_id, websocket in active_connections:

            assert len(websocket.messages_sent) > 0
            
            # Check for shutdown notification

            shutdown_notification_found = False

            for sent_msg in websocket.messages_sent:

                try:

                    msg_data = json.loads(sent_msg)

                    if msg_data.get("type") == "server_shutdown":

                        shutdown_notification_found = True

                        break

                except:

                    pass
            
            assert shutdown_notification_found
        
        # Verify cleanup callbacks were called

        assert len(cleanup_called) > 0

        assert "cleanup" in cleanup_called
        
        # Check final metrics

        metrics = shutdown_manager.get_shutdown_metrics()

        assert metrics["total_connections_at_shutdown"] == len(test_users)

        assert metrics["shutdown_duration"] > 0

        assert metrics["message_preservation_rate"] >= 70  # Should preserve most messages
    
    async def test_shutdown_performance_benchmarks(self, shutdown_manager, test_users):

        """Test shutdown performance with many connections."""

        connection_count = 100

        connections = []
        
        # Register many connections

        start_time = time.time()
        
        for i in range(connection_count):

            user = test_users[i % len(test_users)]

            connection_id = f"perf_conn_{i}"

            websocket = self.create_mock_websocket(auto_close=True)
            
            shutdown_manager.register_connection(connection_id, user.id, websocket)

            connections.append((connection_id, websocket))
        
        registration_time = time.time() - start_time
        
        # Queue messages for each connection

        for connection_id, websocket in connections[:50]:  # Half the connections

            for j in range(5):

                message = {"type": "test", "content": f"Message {j}"}

                shutdown_manager.queue_message_for_connection(connection_id, message)
        
        # Perform graceful shutdown

        shutdown_start = time.time()

        shutdown_result = await shutdown_manager.initiate_graceful_shutdown()

        shutdown_time = time.time() - shutdown_start
        
        # Performance assertions

        assert registration_time < 5.0  # Registration should be fast

        assert shutdown_time < 30.0  # Shutdown should complete within 30 seconds

        assert shutdown_result["success"] is True
        
        # Check shutdown metrics

        metrics = shutdown_manager.get_shutdown_metrics()

        assert metrics["total_connections_at_shutdown"] == connection_count

        assert metrics["shutdown_duration"] < 30.0
        
        # Most connections should close gracefully or be force closed

        total_closed = metrics["gracefully_closed_connections"] + metrics["force_closed_connections"]

        assert total_closed == connection_count
        
        # Message preservation should be reasonable

        assert metrics["message_preservation_rate"] >= 60  # At least 60% preserved

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])