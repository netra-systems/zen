"""
Real WebSocket Manager for Tests - NO MOCKS
CRITICAL: This replaces all MockWebSocketManager implementations with REAL WebSocket connections.

Business Value Justification:
- Segment: Platform/Internal - Chat infrastructure testing
- Business Goal: Ensure WebSocket functionality works in production scenarios  
- Value Impact: Tests validate real WebSocket behavior instead of mock approximations
- Strategic Impact: Prevents production failures by testing actual WebSocket integration

Per CLAUDE.md "MOCKS = Abomination" - all test WebSocket connections must be real.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

from shared.isolated_environment import get_env
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    WebSocketPerformanceMonitor,
    ensure_websocket_service_ready
)
from test_framework.test_context import TestContext, TestUserContext
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType

logger = logging.getLogger(__name__)


@dataclass
class RealWebSocketEvent:
    """Real WebSocket event captured from actual connections."""
    event_type: str
    user_id: str
    thread_id: str
    connection_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivery_confirmed: bool = False


@dataclass
class ConnectionMetrics:
    """Metrics for real WebSocket connections."""
    connection_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    events_captured: int = 0
    average_latency: float = 0.0
    connection_duration: float = 0.0


class RealWebSocketManager:
    """
    Real WebSocket Manager for tests - uses ACTUAL WebSocket connections only.
    
    CRITICAL: This manager creates and manages REAL WebSocket connections to
    actual backend services running in Docker. No mocks, no simulations.
    
    Features:
    - Real WebSocket connection management with Docker services
    - Event capture from actual WebSocket streams
    - User isolation with real connection pools
    - Performance metrics from real network operations
    - Concurrent connection testing with real resources
    """
    
    def __init__(self, backend_url: str = "http://localhost:8000", websocket_url: str = "ws://localhost:8000"):
        """Initialize real WebSocket manager."""
        self.backend_url = backend_url
        self.websocket_url = websocket_url
        self.env = get_env()
        
        # Real connection management
        self.connections: Dict[str, Any] = {}  # connection_id -> real WebSocket connection
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> list of connection_ids
        self.connection_lock = asyncio.Lock()
        
        # Event capture from real WebSocket streams
        self.captured_events: List[RealWebSocketEvent] = []
        self.event_callbacks: Dict[str, List[callable]] = {}  # event_type -> list of callbacks
        self.event_queues: Dict[str, asyncio.Queue] = {}  # thread_id -> event queue
        
        # Docker service management
        self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.SHARED)
        self.services_ready = False
        
        # Performance tracking
        self.metrics = ConnectionMetrics()
        self.performance_monitor = WebSocketPerformanceMonitor()
        self.test_start_time = time.time()
        
        # Required WebSocket events for business value
        self.required_agent_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        logger.info(f"🔗 RealWebSocketManager initialized - backend: {backend_url}, ws: {websocket_url}")
    
    async def ensure_services_ready(self) -> bool:
        """Ensure backend services are running for WebSocket connections."""
        if self.services_ready:
            return True
        
        logger.info("🚀 Starting Docker services for real WebSocket connections...")
        
        try:
            # Start required services
            await self.docker_manager.start_services_smart(
                services=["backend", "auth"],
                wait_healthy=True
            )
            
            # Verify WebSocket service is ready
            if await ensure_websocket_service_ready(base_url=self.backend_url, max_wait=30.0):
                self.services_ready = True
                logger.info("✅ Docker services ready for WebSocket connections")
                return True
            else:
                logger.error("❌ WebSocket service not ready after startup")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start Docker services: {e}")
            return False
    
    async def connect_user(self, user_id: str, websocket=None, thread_id: str = None) -> str:
        """
        Connect a user with REAL WebSocket connection.
        
        Args:
            user_id: User identifier
            websocket: Placeholder for compatibility (ignored - we create real connections)
            thread_id: Thread identifier
            
        Returns:
            Connection ID for the established real connection
        """
        if not await self.ensure_services_ready():
            raise ConnectionError("Backend services not ready for WebSocket connections")
        
        connection_id = f"real_conn_{user_id}_{uuid.uuid4().hex[:8]}"
        
        if not thread_id:
            thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        async with self.connection_lock:
            try:
                # Create REAL WebSocket connection
                self.metrics.connection_attempts += 1
                connection_start = time.time()
                
                # Create test context for this user
                user_context = TestUserContext(user_id=user_id)
                user_context.thread_id = thread_id
                
                test_context = TestContext(
                    user_context=user_context,
                    websocket_timeout=15.0,
                    event_timeout=10.0
                )
                
                # Establish real WebSocket connection
                await test_context.setup_websocket_connection(
                    endpoint="/ws/test",
                    auth_required=False
                )
                
                self.connections[connection_id] = {
                    'real_connection': test_context.websocket_connection,
                    'test_context': test_context,
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'connected_at': time.time(),
                    'status': 'connected'
                }
                
                # Track user connections
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = []
                self.user_connections[user_id].append(connection_id)
                
                # Initialize event queue for this thread
                if thread_id not in self.event_queues:
                    self.event_queues[thread_id] = asyncio.Queue(maxsize=1000)
                
                self.metrics.successful_connections += 1
                self.metrics.connection_duration = time.time() - connection_start
                
                logger.info(f"✅ Connected user {user_id} with REAL WebSocket (conn: {connection_id})")
                return connection_id
                
            except Exception as e:
                self.metrics.failed_connections += 1
                logger.error(f"❌ Failed to connect user {user_id}: {e}")
                raise ConnectionError(f"Real WebSocket connection failed: {e}")
    
    async def disconnect_user(self, user_id: str, websocket=None, thread_id: str = None):
        """Disconnect user's real WebSocket connections."""
        async with self.connection_lock:
            connections_to_remove = []
            
            for connection_id, connection_info in self.connections.items():
                if connection_info['user_id'] == user_id:
                    if thread_id is None or connection_info['thread_id'] == thread_id:
                        connections_to_remove.append(connection_id)
            
            for connection_id in connections_to_remove:
                await self._cleanup_connection(connection_id)
            
            # Clean up user connection tracking
            if user_id in self.user_connections:
                self.user_connections[user_id] = [
                    conn_id for conn_id in self.user_connections[user_id] 
                    if conn_id not in connections_to_remove
                ]
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            logger.info(f"🔌 Disconnected user {user_id}, removed {len(connections_to_remove)} connections")
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up a single real WebSocket connection."""
        if connection_id in self.connections:
            connection_info = self.connections[connection_id]
            test_context = connection_info.get('test_context')
            
            if test_context:
                try:
                    await test_context.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up connection {connection_id}: {e}")
            
            del self.connections[connection_id]
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message through REAL WebSocket connection.
        
        Args:
            thread_id: Thread identifier
            message: Message to send through real WebSocket
            
        Returns:
            True if message sent successfully through real connection
        """
        # Find real connection for this thread
        connection_info = None
        for conn_info in self.connections.values():
            if conn_info['thread_id'] == thread_id:
                connection_info = conn_info
                break
        
        if not connection_info:
            logger.error(f"❌ No real WebSocket connection found for thread {thread_id}")
            return False
        
        try:
            test_context = connection_info['test_context']
            
            # Send message through REAL WebSocket connection
            await test_context.send_message(message)
            
            # Record event capture
            event = RealWebSocketEvent(
                event_type=message.get('type', 'unknown'),
                user_id=connection_info['user_id'],
                thread_id=thread_id,
                connection_id=connection_info.get('connection_id', 'unknown'),
                payload=message
            )
            self.captured_events.append(event)
            
            # Add to thread's event queue
            if thread_id in self.event_queues:
                try:
                    self.event_queues[thread_id].put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"⚠️ Event queue full for thread {thread_id}")
            
            self.metrics.messages_sent += 1
            logger.debug(f"📤 Sent message via REAL WebSocket: {message.get('type')} -> thread {thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message via real WebSocket: {e}")
            return False
    
    async def wait_for_agent_events(
        self, 
        thread_id: str, 
        required_events: Optional[Set[str]] = None,
        timeout: float = 30.0
    ) -> bool:
        """
        Wait for required agent events from REAL WebSocket connection.
        
        Args:
            thread_id: Thread to wait for events
            required_events: Set of required event types
            timeout: Maximum wait time
            
        Returns:
            True if all required events received from real connection
        """
        if required_events is None:
            required_events = self.required_agent_events.copy()
        
        logger.info(f"⏳ Waiting for agent events from REAL WebSocket: {required_events}")
        
        # Find the test context for this thread
        connection_info = None
        for conn_info in self.connections.values():
            if conn_info['thread_id'] == thread_id:
                connection_info = conn_info
                break
        
        if not connection_info:
            logger.error(f"❌ No real connection for thread {thread_id}")
            return False
        
        test_context = connection_info['test_context']
        
        try:
            # Use the test context to wait for events from real WebSocket
            success = await test_context.wait_for_agent_events(
                required_events=required_events,
                timeout=timeout
            )
            
            if success:
                logger.info(f"✅ All required events received from REAL WebSocket for thread {thread_id}")
                
                # Update captured events from real connection
                real_events = test_context.get_captured_events()
                for event_data in real_events:
                    event = RealWebSocketEvent(
                        event_type=event_data.get('type', 'unknown'),
                        user_id=connection_info['user_id'],
                        thread_id=thread_id,
                        connection_id=connection_info.get('connection_id', 'unknown'),
                        payload=event_data,
                        delivery_confirmed=True
                    )
                    self.captured_events.append(event)
                    self.metrics.events_captured += 1
            else:
                logger.warning(f"⚠️ Not all required events received from real WebSocket for thread {thread_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error waiting for agent events from real WebSocket: {e}")
            return False
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get all events captured for a thread from REAL WebSocket connections."""
        return [
            {
                'type': event.event_type,
                'user_id': event.user_id,
                'thread_id': event.thread_id,
                'payload': event.payload,
                'timestamp': event.timestamp.isoformat(),
                'delivery_confirmed': event.delivery_confirmed
            }
            for event in self.captured_events 
            if event.thread_id == thread_id
        ]
    
    def get_required_event_compliance(self, thread_id: str) -> Dict[str, bool]:
        """Check compliance for required agent events from real connections."""
        thread_events = self.get_events_for_thread(thread_id)
        captured_types = {event['type'] for event in thread_events}
        
        return {
            event_type: event_type in captured_types 
            for event_type in self.required_agent_events
        }
    
    def get_compliance_score(self, thread_id: str) -> float:
        """Calculate compliance score (0.0-1.0) for required events."""
        compliance = self.get_required_event_compliance(thread_id)
        completed_events = sum(1 for passed in compliance.values() if passed)
        return completed_events / len(self.required_agent_events)
    
    def get_connection_metrics(self) -> Dict[str, Any]:
        """Get metrics from real WebSocket connection operations."""
        active_connections = len(self.connections)
        uptime = time.time() - self.test_start_time
        
        return {
            'backend_url': self.backend_url,
            'websocket_url': self.websocket_url,
            'active_connections': active_connections,
            'total_users': len(self.user_connections),
            'connection_attempts': self.metrics.connection_attempts,
            'successful_connections': self.metrics.successful_connections,
            'failed_connections': self.metrics.failed_connections,
            'success_rate': (
                self.metrics.successful_connections / max(self.metrics.connection_attempts, 1)
            ),
            'messages_sent': self.metrics.messages_sent,
            'messages_received': self.metrics.messages_received,
            'events_captured': self.metrics.events_captured,
            'average_latency': self.metrics.average_latency,
            'connection_duration': self.metrics.connection_duration,
            'uptime_seconds': uptime,
            'services_ready': self.services_ready
        }
    
    def clear_messages(self):
        """Clear captured events and metrics."""
        self.captured_events.clear()
        for queue in self.event_queues.values():
            # Clear queue
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        # Reset metrics
        self.metrics = ConnectionMetrics()
        self.test_start_time = time.time()
        
        logger.info("🧹 Cleared all captured events and metrics from real WebSocket connections")
    
    async def cleanup_all_connections(self):
        """Clean up all real WebSocket connections."""
        logger.info("🧹 Cleaning up ALL real WebSocket connections...")
        
        connection_ids = list(self.connections.keys())
        cleanup_tasks = [self._cleanup_connection(conn_id) for conn_id in connection_ids]
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.connections.clear()
        self.user_connections.clear()
        self.event_queues.clear()
        
        logger.info(f"✅ Cleaned up {len(connection_ids)} real WebSocket connections")
    
    @asynccontextmanager
    async def real_websocket_session(self):
        """Context manager for real WebSocket testing session."""
        logger.info("🚀 Starting REAL WebSocket testing session (no mocks)")
        
        try:
            # Ensure services are ready
            if not await self.ensure_services_ready():
                raise RuntimeError("Failed to start backend services for real WebSocket testing")
            
            yield self
            
        finally:
            # Clean up all real connections
            await self.cleanup_all_connections()
            
            logger.info("✅ Completed REAL WebSocket testing session")


# Pytest fixtures for real WebSocket manager

import pytest

@pytest.fixture
async def real_websocket_manager():
    """Pytest fixture providing RealWebSocketManager with real connections."""
    manager = RealWebSocketManager()
    
    async with manager.real_websocket_session():
        yield manager


@pytest.fixture
async def connected_real_websocket_user(real_websocket_manager):
    """Pytest fixture providing a connected user through real WebSocket."""
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
    
    connection_id = await real_websocket_manager.connect_user(
        user_id=user_id, 
        thread_id=thread_id
    )
    
    yield {
        'manager': real_websocket_manager,
        'user_id': user_id,
        'thread_id': thread_id,
        'connection_id': connection_id
    }


@pytest.fixture
async def multiple_real_websocket_users(real_websocket_manager):
    """Pytest fixture providing multiple connected users through real WebSockets."""
    users = []
    
    for i in range(3):
        user_id = f"multi_user_{i}_{uuid.uuid4().hex[:8]}"
        thread_id = f"multi_thread_{i}_{uuid.uuid4().hex[:8]}"
        
        connection_id = await real_websocket_manager.connect_user(
            user_id=user_id, 
            thread_id=thread_id
        )
        
        users.append({
            'manager': real_websocket_manager,
            'user_id': user_id,
            'thread_id': thread_id,
            'connection_id': connection_id
        })
    
    yield users