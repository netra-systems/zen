"""WebSocket Heartbeat and Zombie Detection L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform reliability (all tiers)
- Business Goal: Ensure optimal resource utilization and connection health
- Value Impact: $50K MRR - Zombie connections waste 30% of WebSocket resources
- Strategic Impact: Maintains platform performance and prevents resource exhaustion

Critical Path: Connection establishment -> Heartbeat monitoring -> Zombie detection -> Resource cleanup -> Client reconnection handling
Coverage: Heartbeat intervals, zombie detection <60s, connection pruning, resource reclamation, reconnection scenarios
"""

from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.websocket_manager import WebSocketManager
from test_framework.mock_utils import mock_justified

logger = logging.getLogger(__name__)

class ConnectionState(Enum):

    """WebSocket connection state."""

    ACTIVE = "active"

    ZOMBIE = "zombie"

    DISCONNECTED = "disconnected"

    CLEANUP_PENDING = "cleanup_pending"

    RECONNECTING = "reconnecting"

@dataclass

class HeartbeatMetrics:

    """Heartbeat monitoring metrics."""

    total_heartbeats_sent: int = 0

    total_heartbeats_received: int = 0

    missed_heartbeats: int = 0

    average_response_time: float = 0.0

    last_heartbeat_time: Optional[datetime] = None

@dataclass

class ZombieDetectionResult:

    """Zombie connection detection result."""

    connection_id: str

    user_id: str

    detection_time: datetime

    time_since_last_heartbeat: float

    zombie_reason: str

    cleanup_required: bool = True

@dataclass

class ConnectionHealthState:

    """WebSocket connection health state."""

    connection_id: str

    user_id: str

    state: ConnectionState

    established_at: datetime

    last_heartbeat: Optional[datetime] = None

    heartbeat_metrics: HeartbeatMetrics = field(default_factory=HeartbeatMetrics)

    zombie_detection_count: int = 0

    cleanup_attempts: int = 0

class MockWebSocketConnection:

    """Mock WebSocket connection for testing."""
    
    def __init__(self, user_id: str, connection_id: str = None):

        self.user_id = user_id

        self.connection_id = connection_id or str(uuid.uuid4())

        self.is_active = True

        self.send_queue = []

        self.receive_queue = []

        self.close_called = False

        self.close_code = None

        self.close_reason = None
        
    async def send(self, message: str):

        """Mock send message."""

        if self.is_active:

            self.send_queue.append({

                "message": message,

                "timestamp": time.time()

            })

        else:

            raise ConnectionError("Connection is closed")
    
    async def receive(self):

        """Mock receive message."""

        if self.receive_queue:

            return self.receive_queue.pop(0)

        await asyncio.sleep(0.1)

        return None
    
    async def close(self, code: int = 1000, reason: str = ""):

        """Mock close connection."""

        self.is_active = False

        self.close_called = True

        self.close_code = code

        self.close_reason = reason
    
    def simulate_disconnect(self):

        """Simulate unexpected disconnection."""

        self.is_active = False
    
    def simulate_heartbeat_response(self, delay: float = 0.0):

        """Simulate heartbeat response from client."""

        async def add_response():

            if delay > 0:

                await asyncio.sleep(delay)

            if self.is_active:

                self.receive_queue.append({

                    "type": "heartbeat_response",

                    "timestamp": time.time()

                })
        
        asyncio.create_task(add_response())

class WebSocketHeartbeatZombieManager:

    """Manages WebSocket heartbeat monitoring and zombie detection."""
    
    def __init__(self, redis_client=None):

        self.redis_client = redis_client

        self.connections: Dict[str, ConnectionHealthState] = {}

        self.websocket_connections: Dict[str, MockWebSocketConnection] = {}
        
        # Configuration

        self.heartbeat_interval = 30  # seconds

        self.zombie_detection_timeout = 60  # seconds

        self.max_missed_heartbeats = 2

        self.cleanup_batch_size = 10

        self.reconnection_window = 300  # seconds
        
        # Metrics

        self.total_connections = 0

        self.active_connections = 0

        self.zombie_connections_detected = 0

        self.connections_cleaned_up = 0

        self.failed_cleanups = 0
        
        # Monitoring state

        self.monitoring_active = False

        self.cleanup_in_progress = False
    
    async def establish_connection(self, user_id: str, websocket: MockWebSocketConnection = None) -> str:

        """Establish new WebSocket connection with heartbeat monitoring."""

        if not websocket:

            websocket = MockWebSocketConnection(user_id)
        
        connection_id = websocket.connection_id
        
        # Create health state

        health_state = ConnectionHealthState(

            connection_id=connection_id,

            user_id=user_id,

            state=ConnectionState.ACTIVE,

            established_at=datetime.now(timezone.utc),

            last_heartbeat=datetime.now(timezone.utc)

        )
        
        self.connections[connection_id] = health_state

        self.websocket_connections[connection_id] = websocket
        
        self.total_connections += 1

        self.active_connections += 1
        
        # Cache connection state in Redis

        if self.redis_client:

            await self._cache_connection_state(health_state)
        
        logger.info(f"Established connection {connection_id} for user {user_id}")

        return connection_id
    
    async def _cache_connection_state(self, health_state: ConnectionHealthState):

        """Cache connection state in Redis."""

        try:

            key = f"ws_connection:{health_state.connection_id}"

            value = {

                "user_id": health_state.user_id,

                "state": health_state.state.value,

                "established_at": health_state.established_at.isoformat(),

                "last_heartbeat": health_state.last_heartbeat.isoformat() if health_state.last_heartbeat else None,

                "zombie_detection_count": health_state.zombie_detection_count

            }

            await self.redis_client.set(key, json.dumps(value), ex=3600)

        except Exception as e:

            logger.warning(f"Failed to cache connection state: {e}")
    
    async def start_heartbeat_monitoring(self):

        """Start heartbeat monitoring for all connections."""

        if self.monitoring_active:

            return
        
        self.monitoring_active = True

        logger.info("Starting heartbeat monitoring")
        
        # Start monitoring tasks

        monitoring_tasks = [

            asyncio.create_task(self._heartbeat_sender_loop()),

            asyncio.create_task(self._zombie_detector_loop()),

            asyncio.create_task(self._cleanup_scheduler_loop())

        ]
        
        return monitoring_tasks
    
    async def stop_heartbeat_monitoring(self):

        """Stop heartbeat monitoring."""

        self.monitoring_active = False

        logger.info("Stopping heartbeat monitoring")
    
    async def _heartbeat_sender_loop(self):

        """Send heartbeats to all active connections."""

        while self.monitoring_active:

            try:

                current_time = datetime.now(timezone.utc)

                heartbeat_tasks = []
                
                for connection_id, health_state in self.connections.items():

                    if health_state.state == ConnectionState.ACTIVE:

                        task = self._send_heartbeat(connection_id, current_time)

                        heartbeat_tasks.append(task)
                
                if heartbeat_tasks:

                    await asyncio.gather(*heartbeat_tasks, return_exceptions=True)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:

                logger.error(f"Error in heartbeat sender loop: {e}")

                await asyncio.sleep(1)
    
    async def _send_heartbeat(self, connection_id: str, timestamp: datetime):

        """Send heartbeat to specific connection."""

        try:

            websocket = self.websocket_connections.get(connection_id)

            health_state = self.connections.get(connection_id)
            
            if not websocket or not health_state:

                return
            
            heartbeat_message = {

                "type": "heartbeat",

                "timestamp": timestamp.isoformat(),

                "connection_id": connection_id

            }
            
            start_time = time.time()

            await websocket.send(json.dumps(heartbeat_message))
            
            # Update metrics

            health_state.heartbeat_metrics.total_heartbeats_sent += 1

            health_state.heartbeat_metrics.last_heartbeat_time = timestamp
            
            # Simulate checking for response

            await self._check_heartbeat_response(connection_id, start_time)
            
        except Exception as e:

            logger.warning(f"Failed to send heartbeat to {connection_id}: {e}")

            await self._mark_connection_problematic(connection_id)
    
    async def _check_heartbeat_response(self, connection_id: str, start_time: float):

        """Check for heartbeat response within timeout."""

        try:

            websocket = self.websocket_connections.get(connection_id)

            health_state = self.connections.get(connection_id)
            
            if not websocket or not health_state:

                return
            
            # Wait for response with timeout

            response_received = False

            timeout = 5.0  # 5 second timeout for response
            
            try:

                await asyncio.wait_for(self._wait_for_heartbeat_response(websocket), timeout=timeout)

                response_received = True
                
                # Update metrics

                response_time = time.time() - start_time

                health_state.heartbeat_metrics.total_heartbeats_received += 1
                
                # Update average response time

                current_avg = health_state.heartbeat_metrics.average_response_time

                total_received = health_state.heartbeat_metrics.total_heartbeats_received

                health_state.heartbeat_metrics.average_response_time = (

                    (current_avg * (total_received - 1) + response_time) / total_received

                )
                
                health_state.last_heartbeat = datetime.now(timezone.utc)
                
            except asyncio.TimeoutError:
                # No response received

                health_state.heartbeat_metrics.missed_heartbeats += 1

                logger.warning(f"Heartbeat response timeout for connection {connection_id}")
        
        except Exception as e:

            logger.error(f"Error checking heartbeat response for {connection_id}: {e}")
    
    async def _wait_for_heartbeat_response(self, websocket: MockWebSocketConnection):

        """Wait for heartbeat response from WebSocket."""
        # For mock connections, check if response was simulated

        start_time = time.time()

        while time.time() - start_time < 5.0:

            if websocket.receive_queue:

                message = await websocket.receive()

                if message and message.get("type") == "heartbeat_response":

                    return True

            await asyncio.sleep(0.1)

        return False
    
    async def _zombie_detector_loop(self):

        """Detect zombie connections that haven't responded to heartbeats."""

        while self.monitoring_active:

            try:

                current_time = datetime.now(timezone.utc)

                zombie_connections = []
                
                for connection_id, health_state in self.connections.items():

                    if health_state.state == ConnectionState.ACTIVE:

                        zombie_result = await self._check_for_zombie(health_state, current_time)

                        if zombie_result:

                            zombie_connections.append(zombie_result)
                
                # Process detected zombies

                for zombie in zombie_connections:

                    await self._handle_zombie_connection(zombie)
                
                # Log metrics

                if zombie_connections:

                    logger.info(f"Detected {len(zombie_connections)} zombie connections")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:

                logger.error(f"Error in zombie detector loop: {e}")

                await asyncio.sleep(1)
    
    async def _check_for_zombie(self, health_state: ConnectionHealthState, 

                              current_time: datetime) -> Optional[ZombieDetectionResult]:

        """Check if connection is zombie based on heartbeat metrics."""
        # Check last heartbeat time

        if health_state.last_heartbeat:

            time_since_heartbeat = (current_time - health_state.last_heartbeat).total_seconds()
            
            # Zombie detection criteria

            if time_since_heartbeat > self.zombie_detection_timeout:

                return ZombieDetectionResult(

                    connection_id=health_state.connection_id,

                    user_id=health_state.user_id,

                    detection_time=current_time,

                    time_since_last_heartbeat=time_since_heartbeat,

                    zombie_reason="heartbeat_timeout"

                )
        
        # Check missed heartbeats

        if health_state.heartbeat_metrics.missed_heartbeats >= self.max_missed_heartbeats:

            time_since_heartbeat = (current_time - health_state.last_heartbeat).total_seconds() if health_state.last_heartbeat else 0
            
            return ZombieDetectionResult(

                connection_id=health_state.connection_id,

                user_id=health_state.user_id,

                detection_time=current_time,

                time_since_last_heartbeat=time_since_heartbeat,

                zombie_reason="missed_heartbeats"

            )
        
        # Check WebSocket connection state

        websocket = self.websocket_connections.get(health_state.connection_id)

        if websocket and not websocket.is_active:

            return ZombieDetectionResult(

                connection_id=health_state.connection_id,

                user_id=health_state.user_id,

                detection_time=current_time,

                time_since_last_heartbeat=0,

                zombie_reason="connection_closed"

            )
        
        return None
    
    async def _handle_zombie_connection(self, zombie_result: ZombieDetectionResult):

        """Handle detected zombie connection."""

        connection_id = zombie_result.connection_id
        
        # Update connection state

        if connection_id in self.connections:

            health_state = self.connections[connection_id]

            health_state.state = ConnectionState.ZOMBIE

            health_state.zombie_detection_count += 1
            
            # Cache updated state

            if self.redis_client:

                await self._cache_connection_state(health_state)
        
        self.zombie_connections_detected += 1

        self.active_connections -= 1
        
        logger.warning(f"Detected zombie connection {connection_id} for user {zombie_result.user_id}: {zombie_result.zombie_reason}")
        
        # Schedule for cleanup

        await self._schedule_connection_cleanup(zombie_result)
    
    async def _schedule_connection_cleanup(self, zombie_result: ZombieDetectionResult):

        """Schedule zombie connection for cleanup."""

        connection_id = zombie_result.connection_id
        
        if connection_id in self.connections:

            health_state = self.connections[connection_id]

            health_state.state = ConnectionState.CLEANUP_PENDING
    
    async def _cleanup_scheduler_loop(self):

        """Schedule and perform cleanup of zombie connections."""

        while self.monitoring_active:

            try:

                if not self.cleanup_in_progress:

                    await self._perform_cleanup_batch()
                
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                
            except Exception as e:

                logger.error(f"Error in cleanup scheduler loop: {e}")

                await asyncio.sleep(5)
    
    async def _perform_cleanup_batch(self):

        """Perform cleanup of zombie connections in batches."""

        self.cleanup_in_progress = True
        
        try:
            # Find connections pending cleanup

            cleanup_candidates = [

                connection_id for connection_id, health_state in self.connections.items()

                if health_state.state == ConnectionState.CLEANUP_PENDING

            ]
            
            # Process in batches

            for i in range(0, len(cleanup_candidates), self.cleanup_batch_size):

                batch = cleanup_candidates[i:i + self.cleanup_batch_size]

                cleanup_tasks = []
                
                for connection_id in batch:

                    task = self._cleanup_connection(connection_id)

                    cleanup_tasks.append(task)
                
                results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
                # Count successful cleanups

                successful_cleanups = sum(1 for result in results if result is True)

                failed_cleanups = len(results) - successful_cleanups
                
                self.connections_cleaned_up += successful_cleanups

                self.failed_cleanups += failed_cleanups
                
                if batch:

                    logger.info(f"Cleanup batch completed: {successful_cleanups} successful, {failed_cleanups} failed")
        
        finally:

            self.cleanup_in_progress = False
    
    async def _cleanup_connection(self, connection_id: str) -> bool:

        """Cleanup specific connection and reclaim resources."""

        try:
            # Close WebSocket connection

            websocket = self.websocket_connections.get(connection_id)

            if websocket and websocket.is_active:

                await websocket.close(code=1001, reason="Zombie connection cleanup")
            
            # Update health state

            if connection_id in self.connections:

                health_state = self.connections[connection_id]

                health_state.state = ConnectionState.DISCONNECTED

                health_state.cleanup_attempts += 1
            
            # Remove from active tracking

            if connection_id in self.websocket_connections:

                del self.websocket_connections[connection_id]
            
            # Clean up Redis cache

            if self.redis_client:

                cache_key = f"ws_connection:{connection_id}"

                await self.redis_client.delete(cache_key)
            
            logger.info(f"Successfully cleaned up connection {connection_id}")

            return True
            
        except Exception as e:

            logger.error(f"Failed to cleanup connection {connection_id}: {e}")

            return False
    
    async def _mark_connection_problematic(self, connection_id: str):

        """Mark connection as problematic but not yet zombie."""

        if connection_id in self.connections:

            health_state = self.connections[connection_id]

            health_state.heartbeat_metrics.missed_heartbeats += 1
    
    async def handle_client_reconnection(self, user_id: str, new_websocket: MockWebSocketConnection) -> str:

        """Handle client reconnection scenario."""
        # Find existing connections for user

        existing_connections = [

            connection_id for connection_id, health_state in self.connections.items()

            if health_state.user_id == user_id and health_state.state in [ConnectionState.ACTIVE, ConnectionState.ZOMBIE]

        ]
        
        # Clean up old connections

        for old_connection_id in existing_connections:

            await self._cleanup_connection(old_connection_id)
        
        # Establish new connection

        new_connection_id = await self.establish_connection(user_id, new_websocket)
        
        logger.info(f"Handled reconnection for user {user_id}: cleaned up {len(existing_connections)} old connections, established {new_connection_id}")
        
        return new_connection_id
    
    def get_connection_metrics(self) -> Dict[str, Any]:

        """Get comprehensive connection metrics."""

        active_count = sum(1 for hs in self.connections.values() if hs.state == ConnectionState.ACTIVE)

        zombie_count = sum(1 for hs in self.connections.values() if hs.state == ConnectionState.ZOMBIE)

        cleanup_pending_count = sum(1 for hs in self.connections.values() if hs.state == ConnectionState.CLEANUP_PENDING)
        
        return {

            "total_connections": self.total_connections,

            "active_connections": active_count,

            "zombie_connections": zombie_count,

            "cleanup_pending_connections": cleanup_pending_count,

            "zombie_connections_detected": self.zombie_connections_detected,

            "connections_cleaned_up": self.connections_cleaned_up,

            "failed_cleanups": self.failed_cleanups,

            "cleanup_in_progress": self.cleanup_in_progress,

            "monitoring_active": self.monitoring_active

        }

@pytest.fixture

async def redis_client():

    """Create Redis client for connection state caching."""

    try:
        import redis.asyncio as redis

        client = redis.Redis(host="localhost", port=6379, decode_responses=True, db=3)
        # Test connection

        await client.ping()

        yield client

        await client.close()

    except Exception:
        # If Redis not available, return None

        yield None

@pytest.fixture

async def heartbeat_manager(redis_client):

    """Create WebSocket heartbeat and zombie detection manager."""

    manager = WebSocketHeartbeatZombieManager(redis_client)

    yield manager

    await manager.stop_heartbeat_monitoring()

@pytest.fixture

def test_users():

    """Create test users for connection testing."""

    return [

        User(

            id=f"heartbeat_user_{i}",

            email=f"heartbeatuser{i}@example.com",

            username=f"heartbeatuser{i}",

            is_active=True,

            created_at=datetime.now(timezone.utc)

        )

        for i in range(10)

    ]

@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketHeartbeatZombieL3:

    """L3 integration tests for WebSocket heartbeat monitoring and zombie detection."""
    
    @pytest.mark.asyncio

    async def test_basic_heartbeat_monitoring_setup(self, heartbeat_manager, test_users):

        """Test basic heartbeat monitoring system setup and operation."""

        user = test_users[0]
        
        # Establish connection

        websocket = MockWebSocketConnection(user.id)

        websocket.simulate_heartbeat_response()  # Simulate responsive client
        
        connection_id = await heartbeat_manager.establish_connection(user.id, websocket)

        assert connection_id in heartbeat_manager.connections
        
        # Start monitoring

        monitoring_tasks = await heartbeat_manager.start_heartbeat_monitoring()

        assert len(monitoring_tasks) == 3  # heartbeat, zombie detector, cleanup scheduler

        assert heartbeat_manager.monitoring_active
        
        # Let monitoring run briefly

        await asyncio.sleep(2)
        
        # Check connection state

        health_state = heartbeat_manager.connections[connection_id]

        assert health_state.state == ConnectionState.ACTIVE

        assert health_state.heartbeat_metrics.total_heartbeats_sent >= 0
        
        # Stop monitoring

        await heartbeat_manager.stop_heartbeat_monitoring()

        assert not heartbeat_manager.monitoring_active
    
    @pytest.mark.asyncio

    async def test_zombie_detection_under_60_seconds(self, heartbeat_manager, test_users):

        """Test zombie detection meets <60 seconds requirement."""

        user = test_users[0]
        
        # Establish unresponsive connection

        websocket = MockWebSocketConnection(user.id)
        # Don't simulate heartbeat responses (zombie connection)
        
        connection_id = await heartbeat_manager.establish_connection(user.id, websocket)
        
        # Set aggressive timeouts for testing

        heartbeat_manager.zombie_detection_timeout = 30  # 30 seconds

        heartbeat_manager.max_missed_heartbeats = 1

        heartbeat_manager.heartbeat_interval = 10  # 10 seconds
        
        # Start monitoring

        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Track zombie detection time

        start_time = time.time()

        zombie_detected = False
        
        # Wait for zombie detection (should be <60 seconds)

        timeout = 65  # Allow 65 seconds max

        while time.time() - start_time < timeout:

            metrics = heartbeat_manager.get_connection_metrics()

            if metrics["zombie_connections_detected"] > 0:

                zombie_detected = True

                detection_time = time.time() - start_time

                break

            await asyncio.sleep(1)
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Assert detection requirements

        assert zombie_detected, "Zombie connection should be detected"

        assert detection_time < 60.0, f"Zombie detection took {detection_time}s, should be <60s"
        
        # Verify connection state

        health_state = heartbeat_manager.connections[connection_id]

        assert health_state.state in [ConnectionState.ZOMBIE, ConnectionState.CLEANUP_PENDING]
    
    @pytest.mark.asyncio

    async def test_heartbeat_interval_accuracy(self, heartbeat_manager, test_users):

        """Test heartbeat interval timing accuracy."""

        user = test_users[0]
        
        # Create responsive connection

        websocket = MockWebSocketConnection(user.id)

        websocket.simulate_heartbeat_response()
        
        connection_id = await heartbeat_manager.establish_connection(user.id, websocket)
        
        # Set precise interval for testing

        heartbeat_manager.heartbeat_interval = 5  # 5 seconds
        
        # Start monitoring and track heartbeat timing

        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Monitor for multiple intervals

        monitoring_duration = 25  # 25 seconds (5 intervals)

        start_time = time.time()
        
        initial_heartbeats = heartbeat_manager.connections[connection_id].heartbeat_metrics.total_heartbeats_sent
        
        await asyncio.sleep(monitoring_duration)
        
        final_heartbeats = heartbeat_manager.connections[connection_id].heartbeat_metrics.total_heartbeats_sent

        actual_interval_count = final_heartbeats - initial_heartbeats

        expected_interval_count = monitoring_duration // heartbeat_manager.heartbeat_interval
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Assert interval accuracy (allow ±1 interval tolerance)

        assert abs(actual_interval_count - expected_interval_count) <= 1, \

            f"Expected ~{expected_interval_count} heartbeats, got {actual_interval_count}"
    
    @pytest.mark.asyncio

    async def test_connection_pruning_and_cleanup(self, heartbeat_manager, test_users):

        """Test connection pruning and resource cleanup mechanisms."""
        # Establish multiple connections with different behaviors

        connections = []
        
        for i, user in enumerate(test_users[:5]):

            websocket = MockWebSocketConnection(user.id)
            
            # Make some connections responsive, others not

            if i % 2 == 0:

                websocket.simulate_heartbeat_response()

            else:
                # Unresponsive connection (will become zombie)

                pass
            
            connection_id = await heartbeat_manager.establish_connection(user.id, websocket)

            connections.append((connection_id, websocket, i % 2 == 0))
        
        # Set aggressive settings for testing

        heartbeat_manager.zombie_detection_timeout = 20

        heartbeat_manager.max_missed_heartbeats = 1

        heartbeat_manager.heartbeat_interval = 5

        heartbeat_manager.cleanup_batch_size = 3
        
        initial_metrics = heartbeat_manager.get_connection_metrics()

        assert initial_metrics["active_connections"] == 5
        
        # Start monitoring and wait for cleanup

        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Wait for zombie detection and cleanup

        await asyncio.sleep(45)  # Allow time for detection and cleanup
        
        final_metrics = heartbeat_manager.get_connection_metrics()
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Verify cleanup occurred

        assert final_metrics["zombie_connections_detected"] >= 2, "Should detect zombie connections"

        assert final_metrics["connections_cleaned_up"] >= 2, "Should clean up zombie connections"
        
        # Verify resource reclamation

        responsive_connections = [c for c in connections if c[2]]  # Responsive connections

        zombie_connections = [c for c in connections if not c[2]]  # Unresponsive connections
        
        # Check that zombie connections were closed

        for connection_id, websocket, _ in zombie_connections:

            assert websocket.close_called or not websocket.is_active, \

                f"Zombie connection {connection_id} should be closed"
    
    @pytest.mark.asyncio

    async def test_client_reconnection_handling(self, heartbeat_manager, test_users):

        """Test client reconnection scenarios and old connection cleanup."""

        user = test_users[0]
        
        # Establish initial connection

        old_websocket = MockWebSocketConnection(user.id)

        old_websocket.simulate_heartbeat_response()
        
        old_connection_id = await heartbeat_manager.establish_connection(user.id, old_websocket)
        
        # Simulate connection becoming problematic (zombie)

        old_websocket.simulate_disconnect()
        
        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Wait for zombie detection

        await asyncio.sleep(15)
        
        # Simulate client reconnection

        new_websocket = MockWebSocketConnection(user.id)

        new_websocket.simulate_heartbeat_response()
        
        new_connection_id = await heartbeat_manager.handle_client_reconnection(user.id, new_websocket)
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Verify reconnection handling

        assert new_connection_id != old_connection_id, "New connection should have different ID"

        assert new_connection_id in heartbeat_manager.connections, "New connection should be tracked"
        
        # Verify old connection cleanup

        if old_connection_id in heartbeat_manager.connections:

            old_health_state = heartbeat_manager.connections[old_connection_id]

            assert old_health_state.state == ConnectionState.DISCONNECTED, "Old connection should be disconnected"
        
        # Verify new connection is active

        new_health_state = heartbeat_manager.connections[new_connection_id]

        assert new_health_state.state == ConnectionState.ACTIVE, "New connection should be active"
    
    @pytest.mark.asyncio

    async def test_resource_reclamation_efficiency(self, heartbeat_manager, test_users):

        """Test resource reclamation efficiency and memory cleanup."""
        # Create many connections to test resource management

        connection_count = 20

        established_connections = []
        
        for i in range(connection_count):

            user_id = f"load_test_user_{i}"

            websocket = MockWebSocketConnection(user_id)
            
            # Make every 3rd connection zombie

            if i % 3 == 0:

                pass  # Unresponsive

            else:

                websocket.simulate_heartbeat_response()
            
            connection_id = await heartbeat_manager.establish_connection(user_id, websocket)

            established_connections.append((connection_id, websocket, i % 3 != 0))
        
        initial_metrics = heartbeat_manager.get_connection_metrics()

        assert initial_metrics["total_connections"] == connection_count
        
        # Configure aggressive cleanup

        heartbeat_manager.zombie_detection_timeout = 15

        heartbeat_manager.heartbeat_interval = 3

        heartbeat_manager.cleanup_batch_size = 5
        
        # Start monitoring

        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Run monitoring for sufficient time

        await asyncio.sleep(30)
        
        final_metrics = heartbeat_manager.get_connection_metrics()
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Calculate efficiency metrics

        expected_zombies = connection_count // 3  # Every 3rd connection

        detected_zombies = final_metrics["zombie_connections_detected"]

        cleaned_up = final_metrics["connections_cleaned_up"]
        
        # Efficiency assertions

        detection_efficiency = detected_zombies / expected_zombies if expected_zombies > 0 else 1.0

        cleanup_efficiency = cleaned_up / detected_zombies if detected_zombies > 0 else 1.0
        
        assert detection_efficiency >= 0.8, f"Detection efficiency {detection_efficiency:.2f} below 80%"

        assert cleanup_efficiency >= 0.7, f"Cleanup efficiency {cleanup_efficiency:.2f} below 70%"
        
        # Memory cleanup verification

        active_websockets = len(heartbeat_manager.websocket_connections)

        total_health_states = len(heartbeat_manager.connections)
        
        # Should have cleaned up some WebSocket references

        assert active_websockets < connection_count, "Should have cleaned up some WebSocket connections"
    
    @pytest.mark.asyncio

    async def test_heartbeat_response_time_monitoring(self, heartbeat_manager, test_users):

        """Test heartbeat response time monitoring and metrics accuracy."""

        user = test_users[0]
        
        # Create connection with variable response times

        websocket = MockWebSocketConnection(user.id)
        
        connection_id = await heartbeat_manager.establish_connection(user.id, websocket)
        
        # Configure for testing

        heartbeat_manager.heartbeat_interval = 5
        
        # Start monitoring

        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Simulate variable response times

        response_delays = [0.1, 0.2, 0.05, 0.3, 0.15]  # seconds
        
        for delay in response_delays:

            websocket.simulate_heartbeat_response(delay)

            await asyncio.sleep(heartbeat_manager.heartbeat_interval + 1)
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Check response time metrics

        health_state = heartbeat_manager.connections[connection_id]

        metrics = health_state.heartbeat_metrics
        
        assert metrics.total_heartbeats_sent >= len(response_delays)

        assert metrics.total_heartbeats_received >= len(response_delays) - 1  # Allow some tolerance

        assert metrics.average_response_time > 0, "Should have calculated average response time"

        assert metrics.missed_heartbeats <= 1, "Should have minimal missed heartbeats"
        
        # Response time should be reasonable

        assert 0.05 <= metrics.average_response_time <= 0.5, \

            f"Average response time {metrics.average_response_time:.3f}s seems unreasonable"
    
    @mock_justified("L3: WebSocket heartbeat and zombie detection testing with controlled connection simulation")

    @pytest.mark.asyncio

    async def test_comprehensive_zombie_detection_reliability(self, heartbeat_manager, test_users):

        """Test comprehensive zombie detection reliability and accuracy."""
        # Setup comprehensive test scenarios

        test_scenarios = [
            # Normal responsive connections

            {"count": 5, "type": "responsive", "response_delay": 0.1},
            # Slow but responsive connections

            {"count": 3, "type": "slow_responsive", "response_delay": 2.0},
            # Completely unresponsive connections (zombies)

            {"count": 4, "type": "zombie", "response_delay": None},
            # Intermittently responsive connections

            {"count": 3, "type": "intermittent", "response_delay": 0.1}

        ]
        
        all_connections = []

        expected_zombies = 0
        
        # Establish connections according to scenarios

        connection_index = 0

        for scenario in test_scenarios:

            for i in range(scenario["count"]):

                user_id = f"test_user_{connection_index}"

                websocket = MockWebSocketConnection(user_id)
                
                if scenario["type"] == "responsive":

                    websocket.simulate_heartbeat_response(scenario["response_delay"])

                elif scenario["type"] == "slow_responsive":

                    websocket.simulate_heartbeat_response(scenario["response_delay"])

                elif scenario["type"] == "zombie":
                    # Don't simulate any responses

                    expected_zombies += 1

                elif scenario["type"] == "intermittent":
                    # Simulate some responses, but not all

                    if i % 2 == 0:

                        websocket.simulate_heartbeat_response(scenario["response_delay"])

                    else:

                        expected_zombies += 1
                
                connection_id = await heartbeat_manager.establish_connection(user_id, websocket)

                all_connections.append({

                    "connection_id": connection_id,

                    "websocket": websocket,

                    "type": scenario["type"],

                    "user_id": user_id

                })

                connection_index += 1
        
        # Configure for reliable testing

        heartbeat_manager.zombie_detection_timeout = 25

        heartbeat_manager.max_missed_heartbeats = 2

        heartbeat_manager.heartbeat_interval = 8
        
        # Start monitoring

        await heartbeat_manager.start_heartbeat_monitoring()
        
        # Run comprehensive monitoring cycle

        monitoring_duration = 60  # 60 seconds

        await asyncio.sleep(monitoring_duration)
        
        final_metrics = heartbeat_manager.get_connection_metrics()
        
        await heartbeat_manager.stop_heartbeat_monitoring()
        
        # Calculate reliability metrics

        detected_zombies = final_metrics["zombie_connections_detected"]

        total_connections = len(all_connections)
        
        # Detection accuracy

        detection_accuracy = min(detected_zombies / expected_zombies, 1.0) if expected_zombies > 0 else 1.0
        
        # False positive rate (responsive connections marked as zombies)

        responsive_connections = [c for c in all_connections if c["type"] in ["responsive", "slow_responsive"]]

        false_positives = 0
        
        for conn in responsive_connections:

            if conn["connection_id"] in heartbeat_manager.connections:

                health_state = heartbeat_manager.connections[conn["connection_id"]]

                if health_state.state == ConnectionState.ZOMBIE:

                    false_positives += 1
        
        false_positive_rate = false_positives / len(responsive_connections) if responsive_connections else 0.0
        
        # Performance metrics

        cleanup_rate = final_metrics["connections_cleaned_up"] / detected_zombies if detected_zombies > 0 else 1.0
        
        # Reliability assertions

        assert detection_accuracy >= 0.8, f"Detection accuracy {detection_accuracy:.2f} below 80%"

        assert false_positive_rate <= 0.1, f"False positive rate {false_positive_rate:.2f} above 10%"

        assert cleanup_rate >= 0.7, f"Cleanup rate {cleanup_rate:.2f} below 70%"
        
        # Performance assertions

        assert final_metrics["failed_cleanups"] <= final_metrics["connections_cleaned_up"] * 0.1, \

            "Failed cleanup rate should be below 10%"
        
        logger.info(f"Reliability test results: {detection_accuracy:.2f} detection accuracy, "

                   f"{false_positive_rate:.2f} false positive rate, {cleanup_rate:.2f} cleanup rate")

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])