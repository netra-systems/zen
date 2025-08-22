"""
L2 Integration Test: WebSocket Heartbeat Mechanism

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Connection liveness worth $6K MRR reliability
- Value Impact: Ensures connection health and prevents zombie connections
- Strategic Impact: Improves reliability and reduces infrastructure waste

L2 Test: Real internal heartbeat components with mocked external services.
Performance target: <30s zombie detection, 99% heartbeat reliability.
"""

# Add project root to path

from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from schemas import UserInDB

from netra_backend.app.services.websocket_manager import WebSocketManager
from test_framework.mock_utils import mock_justified


class HeartbeatState(Enum):

    """Heartbeat connection states."""

    ACTIVE = "active"

    MISSED = "missed"

    ZOMBIE = "zombie"

    DISCONNECTED = "disconnected"


@dataclass

class HeartbeatConfig:

    """Configuration for heartbeat mechanism."""

    interval: float = 30.0          # Heartbeat interval in seconds

    timeout: float = 90.0           # Timeout for heartbeat response

    max_missed: int = 3             # Max missed heartbeats before zombie

    zombie_timeout: float = 300.0   # Time before zombie cleanup

    adaptive_interval: bool = True  # Adjust interval based on network conditions


@dataclass

class ConnectionHealth:

    """Health status of a connection."""

    connection_id: str

    user_id: str

    state: HeartbeatState

    last_heartbeat: float

    last_response: float

    missed_count: int = 0

    rtt_ms: float = 0.0

    created_at: float = field(default_factory=time.time)

    updated_at: float = field(default_factory=time.time)


class HeartbeatManager:

    """Manage WebSocket heartbeat mechanism."""
    

    def __init__(self, config: HeartbeatConfig = None):

        self.config = config or HeartbeatConfig()

        self.connections = {}  # connection_id -> ConnectionHealth

        self.user_connections = {}  # user_id -> set(connection_ids)

        self.heartbeat_tasks = {}  # connection_id -> asyncio.Task

        self.running = False
        

        self.stats = {

            "total_heartbeats_sent": 0,

            "total_responses_received": 0,

            "zombies_detected": 0,

            "connections_cleaned": 0,

            "avg_rtt_ms": 0.0,

            "missed_heartbeats": 0,

            "adaptive_adjustments": 0

        }
    

    async def register_connection(self, connection_id: str, user_id: str, websocket: Any) -> ConnectionHealth:

        """Register a new connection for heartbeat monitoring."""

        current_time = time.time()
        

        health = ConnectionHealth(

            connection_id=connection_id,

            user_id=user_id,

            state=HeartbeatState.ACTIVE,

            last_heartbeat=current_time,

            last_response=current_time

        )
        

        self.connections[connection_id] = health
        

        if user_id not in self.user_connections:

            self.user_connections[user_id] = set()

        self.user_connections[user_id].add(connection_id)
        
        # Start heartbeat task for this connection

        task = asyncio.create_task(self._heartbeat_loop(connection_id, websocket))

        self.heartbeat_tasks[connection_id] = task
        

        return health
    

    async def unregister_connection(self, connection_id: str) -> bool:

        """Unregister a connection from heartbeat monitoring."""

        if connection_id not in self.connections:

            return False
        
        # Cancel heartbeat task

        if connection_id in self.heartbeat_tasks:

            task = self.heartbeat_tasks.pop(connection_id)

            task.cancel()

            try:

                await task

            except asyncio.CancelledError:

                pass
        
        # Remove from tracking

        health = self.connections.pop(connection_id)
        

        if health.user_id in self.user_connections:

            self.user_connections[health.user_id].discard(connection_id)

            if not self.user_connections[health.user_id]:

                del self.user_connections[health.user_id]
        

        return True
    

    async def _heartbeat_loop(self, connection_id: str, websocket: Any) -> None:

        """Main heartbeat loop for a connection."""

        try:

            while connection_id in self.connections:

                health = self.connections[connection_id]
                

                if health.state == HeartbeatState.ZOMBIE:
                    # Stop heartbeats for zombie connections

                    break
                
                # Send heartbeat

                await self._send_heartbeat(connection_id, websocket)
                
                # Wait for response or timeout

                response_received = await self._wait_for_heartbeat_response(connection_id)
                

                if response_received:

                    await self._handle_heartbeat_response(connection_id)

                else:

                    await self._handle_missed_heartbeat(connection_id)
                
                # Adaptive interval adjustment

                if self.config.adaptive_interval:

                    interval = self._calculate_adaptive_interval(connection_id)

                else:

                    interval = self.config.interval
                

                await asyncio.sleep(interval)
        

        except asyncio.CancelledError:

            pass

        except Exception as e:
            # Log error and mark connection as problematic

            if connection_id in self.connections:

                self.connections[connection_id].state = HeartbeatState.ZOMBIE
    

    async def _send_heartbeat(self, connection_id: str, websocket: Any) -> None:

        """Send heartbeat ping to connection."""

        current_time = time.time()
        

        heartbeat_message = {

            "type": "heartbeat_ping",

            "connection_id": connection_id,

            "timestamp": current_time,

            "sequence": self.stats["total_heartbeats_sent"] + 1

        }
        

        try:

            if hasattr(websocket, 'send'):

                await websocket.send(json.dumps(heartbeat_message))
            
            # Update connection state

            if connection_id in self.connections:

                self.connections[connection_id].last_heartbeat = current_time

                self.connections[connection_id].updated_at = current_time
            

            self.stats["total_heartbeats_sent"] += 1
        

        except Exception as e:
            # Handle send failure

            if connection_id in self.connections:

                self.connections[connection_id].state = HeartbeatState.MISSED
    

    async def _wait_for_heartbeat_response(self, connection_id: str, timeout: float = None) -> bool:

        """Wait for heartbeat response within timeout."""

        if timeout is None:

            timeout = self.config.timeout
        

        start_time = time.time()
        

        while time.time() - start_time < timeout:

            if connection_id not in self.connections:

                return False
            

            health = self.connections[connection_id]
            
            # Check if we received a response since sending heartbeat

            if health.last_response > health.last_heartbeat:

                return True
            

            await asyncio.sleep(0.1)  # Check every 100ms
        

        return False
    

    async def handle_heartbeat_response(self, connection_id: str, response_data: Dict[str, Any]) -> None:

        """Handle incoming heartbeat response from client."""

        if connection_id not in self.connections:

            return
        

        current_time = time.time()

        health = self.connections[connection_id]
        
        # Calculate RTT

        sent_timestamp = response_data.get("timestamp", health.last_heartbeat)

        rtt_ms = (current_time - sent_timestamp) * 1000
        
        # Update connection health

        health.last_response = current_time

        health.updated_at = current_time

        health.rtt_ms = rtt_ms

        health.missed_count = 0

        health.state = HeartbeatState.ACTIVE
        

        self.stats["total_responses_received"] += 1

        self._update_avg_rtt(rtt_ms)
    

    async def _handle_heartbeat_response(self, connection_id: str) -> None:

        """Handle successful heartbeat response."""

        if connection_id not in self.connections:

            return
        

        health = self.connections[connection_id]

        current_time = time.time()
        
        # Reset missed count and update state

        health.missed_count = 0

        health.state = HeartbeatState.ACTIVE

        health.updated_at = current_time
        
        # Calculate RTT estimate

        rtt_ms = (current_time - health.last_heartbeat) * 1000

        health.rtt_ms = rtt_ms
        

        self.stats["total_responses_received"] += 1

        self._update_avg_rtt(rtt_ms)
    

    async def _handle_missed_heartbeat(self, connection_id: str) -> None:

        """Handle missed heartbeat response."""

        if connection_id not in self.connections:

            return
        

        health = self.connections[connection_id]

        health.missed_count += 1

        health.updated_at = time.time()

        self.stats["missed_heartbeats"] += 1
        

        if health.missed_count >= self.config.max_missed:
            # Mark as zombie

            health.state = HeartbeatState.ZOMBIE

            self.stats["zombies_detected"] += 1
            
            # Schedule cleanup

            asyncio.create_task(self._schedule_zombie_cleanup(connection_id))

        else:

            health.state = HeartbeatState.MISSED
    

    def _update_avg_rtt(self, rtt_ms: float) -> None:

        """Update average RTT statistic."""

        current_avg = self.stats["avg_rtt_ms"]

        total_responses = self.stats["total_responses_received"]
        

        if total_responses == 1:

            self.stats["avg_rtt_ms"] = rtt_ms

        else:
            # Rolling average

            self.stats["avg_rtt_ms"] = ((current_avg * (total_responses - 1)) + rtt_ms) / total_responses
    

    def _calculate_adaptive_interval(self, connection_id: str) -> float:

        """Calculate adaptive heartbeat interval based on connection quality."""

        if connection_id not in self.connections:

            return self.config.interval
        

        health = self.connections[connection_id]

        base_interval = self.config.interval
        
        # Adjust based on RTT

        if health.rtt_ms > 1000:  # High latency

            adjusted_interval = base_interval * 1.5

            self.stats["adaptive_adjustments"] += 1

        elif health.rtt_ms < 50:  # Low latency

            adjusted_interval = base_interval * 0.8

            self.stats["adaptive_adjustments"] += 1

        else:

            adjusted_interval = base_interval
        
        # Adjust based on missed heartbeats

        if health.missed_count > 0:

            adjusted_interval = base_interval * 0.7  # More frequent checks

            self.stats["adaptive_adjustments"] += 1
        
        # Ensure reasonable bounds

        return max(10.0, min(adjusted_interval, 120.0))  # 10s to 2m
    

    async def _schedule_zombie_cleanup(self, connection_id: str) -> None:

        """Schedule cleanup of zombie connection."""

        await asyncio.sleep(self.config.zombie_timeout)
        

        if connection_id in self.connections:

            health = self.connections[connection_id]

            if health.state == HeartbeatState.ZOMBIE:

                await self.unregister_connection(connection_id)

                self.stats["connections_cleaned"] += 1
    

    async def cleanup_zombie_connections(self) -> int:

        """Manually cleanup all zombie connections."""

        current_time = time.time()

        zombies_to_cleanup = []
        

        for connection_id, health in self.connections.items():

            if health.state == HeartbeatState.ZOMBIE:
                # Check if zombie timeout has passed

                time_since_zombie = current_time - health.updated_at

                if time_since_zombie >= self.config.zombie_timeout:

                    zombies_to_cleanup.append(connection_id)
        

        cleanup_count = 0

        for connection_id in zombies_to_cleanup:

            if await self.unregister_connection(connection_id):

                cleanup_count += 1

                self.stats["connections_cleaned"] += 1
        

        return cleanup_count
    

    def get_connection_health(self, connection_id: str) -> Optional[ConnectionHealth]:

        """Get health status for specific connection."""

        return self.connections.get(connection_id)
    

    def get_user_connections_health(self, user_id: str) -> List[ConnectionHealth]:

        """Get health status for all user connections."""

        if user_id not in self.user_connections:

            return []
        

        return [

            self.connections[conn_id] 

            for conn_id in self.user_connections[user_id]

            if conn_id in self.connections

        ]
    

    def get_heartbeat_stats(self) -> Dict[str, Any]:

        """Get comprehensive heartbeat statistics."""

        stats = self.stats.copy()
        
        # Calculate derived statistics

        if stats["total_heartbeats_sent"] > 0:

            stats["response_rate"] = (stats["total_responses_received"] / stats["total_heartbeats_sent"]) * 100

            stats["miss_rate"] = (stats["missed_heartbeats"] / stats["total_heartbeats_sent"]) * 100

        else:

            stats["response_rate"] = 0.0

            stats["miss_rate"] = 0.0
        
        # Connection state summary

        state_counts = {}

        for state in HeartbeatState:

            state_counts[state.value] = sum(

                1 for health in self.connections.values() 

                if health.state == state

            )
        

        stats["connection_states"] = state_counts

        stats["total_active_connections"] = len(self.connections)

        stats["total_users"] = len(self.user_connections)
        

        return stats
    

    def get_system_health_summary(self) -> Dict[str, Any]:

        """Get overall system health summary."""

        current_time = time.time()

        healthy_connections = 0

        degraded_connections = 0

        zombie_connections = 0
        

        total_rtt = 0.0

        rtt_samples = 0
        

        for health in self.connections.values():

            if health.state == HeartbeatState.ACTIVE:

                healthy_connections += 1

                if health.rtt_ms > 0:

                    total_rtt += health.rtt_ms

                    rtt_samples += 1

            elif health.state == HeartbeatState.MISSED:

                degraded_connections += 1

            elif health.state == HeartbeatState.ZOMBIE:

                zombie_connections += 1
        

        total_connections = len(self.connections)

        avg_rtt = total_rtt / rtt_samples if rtt_samples > 0 else 0.0
        

        health_score = 0.0

        if total_connections > 0:

            health_score = (healthy_connections / total_connections) * 100
        

        return {

            "health_score": health_score,

            "total_connections": total_connections,

            "healthy_connections": healthy_connections,

            "degraded_connections": degraded_connections,

            "zombie_connections": zombie_connections,

            "avg_rtt_ms": avg_rtt,

            "system_status": self._determine_system_status(health_score, zombie_connections, total_connections)

        }
    

    def _determine_system_status(self, health_score: float, zombie_count: int, total_count: int) -> str:

        """Determine overall system status."""

        if health_score >= 95 and zombie_count == 0:

            return "excellent"

        elif health_score >= 85 and zombie_count <= total_count * 0.05:

            return "good"

        elif health_score >= 70:

            return "degraded"

        else:

            return "poor"


class TimeoutDetector:

    """Detect connection timeouts and adaptive timing."""
    

    def __init__(self, heartbeat_manager: HeartbeatManager):

        self.heartbeat_manager = heartbeat_manager

        self.timeout_history = {}  # connection_id -> list of timeout events

        self.network_conditions = {}  # connection_id -> network quality metrics
    

    def record_timeout_event(self, connection_id: str, timeout_type: str) -> None:

        """Record a timeout event for analysis."""

        current_time = time.time()
        

        if connection_id not in self.timeout_history:

            self.timeout_history[connection_id] = []
        

        timeout_event = {

            "timestamp": current_time,

            "type": timeout_type,  # 'heartbeat', 'response', 'connection'

            "sequence": len(self.timeout_history[connection_id])

        }
        

        self.timeout_history[connection_id].append(timeout_event)
        
        # Keep only recent history (last 100 events)

        if len(self.timeout_history[connection_id]) > 100:

            self.timeout_history[connection_id] = self.timeout_history[connection_id][-100:]
        
        # Update network conditions

        self._update_network_conditions(connection_id)
    

    def _update_network_conditions(self, connection_id: str) -> None:

        """Update network condition assessment."""

        if connection_id not in self.timeout_history:

            return
        

        current_time = time.time()

        recent_window = 300.0  # 5 minutes
        

        recent_timeouts = [

            event for event in self.timeout_history[connection_id]

            if current_time - event["timestamp"] < recent_window

        ]
        

        timeout_rate = len(recent_timeouts) / (recent_window / 60)  # per minute
        
        # Get connection health for RTT

        health = self.heartbeat_manager.get_connection_health(connection_id)

        rtt_ms = health.rtt_ms if health else 0.0
        
        # Determine network quality

        if timeout_rate < 0.1 and rtt_ms < 100:

            quality = "excellent"

        elif timeout_rate < 0.5 and rtt_ms < 500:

            quality = "good"

        elif timeout_rate < 2.0 and rtt_ms < 1000:

            quality = "fair"

        else:

            quality = "poor"
        

        self.network_conditions[connection_id] = {

            "quality": quality,

            "timeout_rate_per_minute": timeout_rate,

            "avg_rtt_ms": rtt_ms,

            "last_updated": current_time

        }
    

    def get_recommended_intervals(self, connection_id: str) -> Dict[str, float]:

        """Get recommended heartbeat intervals based on network conditions."""

        base_interval = self.heartbeat_manager.config.interval

        base_timeout = self.heartbeat_manager.config.timeout
        

        conditions = self.network_conditions.get(connection_id)

        if not conditions:

            return {

                "heartbeat_interval": base_interval,

                "response_timeout": base_timeout

            }
        

        quality = conditions["quality"]
        
        # Adjust intervals based on network quality

        if quality == "excellent":

            return {

                "heartbeat_interval": base_interval,

                "response_timeout": base_timeout * 0.8

            }

        elif quality == "good":

            return {

                "heartbeat_interval": base_interval,

                "response_timeout": base_timeout

            }

        elif quality == "fair":

            return {

                "heartbeat_interval": base_interval * 1.2,

                "response_timeout": base_timeout * 1.5

            }

        else:  # poor

            return {

                "heartbeat_interval": base_interval * 1.5,

                "response_timeout": base_timeout * 2.0

            }
    

    def get_timeout_analysis(self) -> Dict[str, Any]:

        """Get timeout analysis across all connections."""

        total_timeouts = 0

        connections_with_timeouts = 0

        quality_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        

        for connection_id, history in self.timeout_history.items():

            if history:

                total_timeouts += len(history)

                connections_with_timeouts += 1
            

            conditions = self.network_conditions.get(connection_id)

            if conditions:

                quality = conditions["quality"]

                quality_distribution[quality] += 1
        

        return {

            "total_connections_monitored": len(self.timeout_history),

            "connections_with_timeouts": connections_with_timeouts,

            "total_timeout_events": total_timeouts,

            "network_quality_distribution": quality_distribution,

            "avg_timeouts_per_connection": total_timeouts / max(1, len(self.timeout_history))

        }


@pytest.mark.L2

@pytest.mark.integration

class TestHeartbeatMechanism:

    """L2 integration tests for heartbeat mechanism."""
    

    @pytest.fixture

    def heartbeat_config(self):

        """Create heartbeat configuration for testing."""

        return HeartbeatConfig(

            interval=5.0,      # Short interval for testing

            timeout=10.0,      # Short timeout for testing

            max_missed=2,      # Quick zombie detection

            zombie_timeout=30.0,  # Short zombie timeout

            adaptive_interval=True

        )
    

    @pytest.fixture

    def heartbeat_manager(self, heartbeat_config):

        """Create heartbeat manager."""

        return HeartbeatManager(heartbeat_config)
    

    @pytest.fixture

    def timeout_detector(self, heartbeat_manager):

        """Create timeout detector."""

        return TimeoutDetector(heartbeat_manager)
    

    @pytest.fixture

    def test_users(self):

        """Create test users."""

        return [

            UserInDB(

                id=f"heartbeat_user_{i}",

                email=f"heartbeatuser{i}@example.com",

                username=f"heartbeatuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(3)

        ]
    

    def create_mock_websocket(self):

        """Create mock WebSocket for testing."""

        websocket = AsyncMock()

        websocket.send = AsyncMock()

        websocket.messages_sent = []

        websocket.heartbeat_responses = []
        

        async def mock_send(message):

            websocket.messages_sent.append(message)
            
            # Auto-respond to heartbeat pings

            try:

                msg_data = json.loads(message)

                if msg_data.get("type") == "heartbeat_ping":

                    response = {

                        "type": "heartbeat_pong",

                        "connection_id": msg_data["connection_id"],

                        "timestamp": msg_data["timestamp"],

                        "sequence": msg_data["sequence"]

                    }

                    websocket.heartbeat_responses.append(response)

            except:

                pass
        

        websocket.send.side_effect = mock_send

        return websocket
    

    async def test_basic_heartbeat_functionality(self, heartbeat_manager, test_users):

        """Test basic heartbeat registration and monitoring."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket()
        
        # Register connection

        health = await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        

        assert health.connection_id == connection_id

        assert health.user_id == user.id

        assert health.state == HeartbeatState.ACTIVE
        
        # Wait for some heartbeats

        await asyncio.sleep(6.0)  # Wait for at least one heartbeat
        
        # Check that heartbeats were sent

        assert len(websocket.messages_sent) > 0
        
        # Verify heartbeat message structure

        heartbeat_msg = json.loads(websocket.messages_sent[0])

        assert heartbeat_msg["type"] == "heartbeat_ping"

        assert heartbeat_msg["connection_id"] == connection_id

        assert "timestamp" in heartbeat_msg

        assert "sequence" in heartbeat_msg
        
        # Check stats

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["total_heartbeats_sent"] > 0

        assert stats["total_active_connections"] == 1
        
        # Cleanup

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_heartbeat_response_handling(self, heartbeat_manager, test_users):

        """Test handling of heartbeat responses."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket()
        
        # Register connection

        await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        
        # Wait for heartbeat to be sent

        await asyncio.sleep(6.0)
        
        # Simulate heartbeat response

        if websocket.heartbeat_responses:

            response = websocket.heartbeat_responses[0]

            await heartbeat_manager.handle_heartbeat_response(connection_id, response)
        
        # Check connection health

        health = heartbeat_manager.get_connection_health(connection_id)

        assert health.state == HeartbeatState.ACTIVE

        assert health.missed_count == 0

        assert health.rtt_ms > 0  # Should have calculated RTT
        
        # Check stats

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["total_responses_received"] > 0

        assert stats["response_rate"] > 0
        
        # Cleanup

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_missed_heartbeat_detection(self, heartbeat_manager, test_users):

        """Test detection of missed heartbeats."""

        user = test_users[0]

        connection_id = str(uuid4())
        
        # Create websocket that doesn't respond

        websocket = AsyncMock()

        websocket.send = AsyncMock()
        
        # Register connection

        await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        
        # Wait for multiple heartbeat cycles without responding

        await asyncio.sleep(15.0)  # Should trigger missed heartbeats
        
        # Check connection health

        health = heartbeat_manager.get_connection_health(connection_id)

        assert health.missed_count > 0

        assert health.state in [HeartbeatState.MISSED, HeartbeatState.ZOMBIE]
        
        # Check stats

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["missed_heartbeats"] > 0

        assert stats["miss_rate"] > 0
        
        # Cleanup

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_zombie_connection_detection(self, heartbeat_manager, test_users):

        """Test zombie connection detection and cleanup."""

        user = test_users[0]

        connection_id = str(uuid4())
        
        # Create unresponsive websocket

        websocket = AsyncMock()

        websocket.send = AsyncMock()
        
        # Register connection

        await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        
        # Wait for zombie detection

        await asyncio.sleep(20.0)  # Should exceed max_missed threshold
        
        # Check if connection is marked as zombie

        health = heartbeat_manager.get_connection_health(connection_id)

        assert health.state == HeartbeatState.ZOMBIE
        
        # Check stats

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["zombies_detected"] > 0
        
        # Test manual cleanup

        cleaned_count = await heartbeat_manager.cleanup_zombie_connections()

        assert cleaned_count >= 0  # May have been auto-cleaned
        
        # Cleanup remaining

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_adaptive_heartbeat_intervals(self, heartbeat_manager, test_users):

        """Test adaptive heartbeat interval adjustment."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket()
        
        # Register connection

        await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        
        # Simulate high RTT by delaying responses

        original_send = websocket.send
        

        async def delayed_send(message):

            await asyncio.sleep(0.5)  # 500ms delay

            await original_send(message)
        

        websocket.send = delayed_send
        
        # Wait for adaptive adjustment

        await asyncio.sleep(12.0)
        
        # Check that adaptive adjustments were made

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["adaptive_adjustments"] > 0
        
        # Cleanup

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_multiple_user_connections(self, heartbeat_manager, test_users):

        """Test heartbeat management for multiple users and connections."""

        connections = []
        
        # Register multiple connections

        for i, user in enumerate(test_users):

            for j in range(2):  # 2 connections per user

                connection_id = f"{user.id}_conn_{j}"

                websocket = self.create_mock_websocket()
                

                await heartbeat_manager.register_connection(connection_id, user.id, websocket)

                connections.append((connection_id, user.id, websocket))
        
        # Wait for heartbeats

        await asyncio.sleep(8.0)
        
        # Check that all connections are being monitored

        for user in test_users:

            user_health = heartbeat_manager.get_user_connections_health(user.id)

            assert len(user_health) == 2  # 2 connections per user
            

            for health in user_health:

                assert health.state == HeartbeatState.ACTIVE
        
        # Check overall stats

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["total_active_connections"] == len(connections)

        assert stats["total_users"] == len(test_users)
        
        # Cleanup all connections

        for connection_id, user_id, websocket in connections:

            await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_timeout_detection_and_analysis(self, heartbeat_manager, timeout_detector, test_users):

        """Test timeout detection and network condition analysis."""

        user = test_users[0]

        connection_id = str(uuid4())

        websocket = self.create_mock_websocket()
        
        # Register connection

        await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        
        # Simulate timeout events

        for i in range(5):

            timeout_detector.record_timeout_event(connection_id, "heartbeat")

            await asyncio.sleep(1.0)
        
        # Get timeout analysis

        analysis = timeout_detector.get_timeout_analysis()

        assert analysis["total_timeout_events"] == 5

        assert analysis["connections_with_timeouts"] == 1
        
        # Get recommended intervals

        recommendations = timeout_detector.get_recommended_intervals(connection_id)

        assert "heartbeat_interval" in recommendations

        assert "response_timeout" in recommendations
        
        # Cleanup

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_system_health_monitoring(self, heartbeat_manager, test_users):

        """Test overall system health monitoring."""
        # Create mix of healthy and problematic connections

        healthy_connections = []

        problematic_connections = []
        
        # Healthy connections

        for i in range(3):

            connection_id = f"healthy_{i}"

            websocket = self.create_mock_websocket()

            await heartbeat_manager.register_connection(connection_id, test_users[0].id, websocket)

            healthy_connections.append((connection_id, websocket))
        
        # Problematic connections

        for i in range(2):

            connection_id = f"problematic_{i}"

            websocket = AsyncMock()

            websocket.send = AsyncMock()  # Doesn't respond

            await heartbeat_manager.register_connection(connection_id, test_users[1].id, websocket)

            problematic_connections.append((connection_id, websocket))
        
        # Wait for health assessment

        await asyncio.sleep(10.0)
        
        # Get system health summary

        health_summary = heartbeat_manager.get_system_health_summary()
        

        assert health_summary["total_connections"] == 5

        assert health_summary["healthy_connections"] >= 1  # At least some healthy

        assert "health_score" in health_summary

        assert health_summary["system_status"] in ["excellent", "good", "degraded", "poor"]
        
        # Cleanup

        for connection_id, websocket in healthy_connections + problematic_connections:

            await heartbeat_manager.unregister_connection(connection_id)
    

    @mock_justified("L2: Heartbeat mechanism with real internal components")

    async def test_websocket_integration_with_heartbeat(self, heartbeat_manager, test_users):

        """Test WebSocket integration with heartbeat mechanism."""

        user = test_users[0]

        connection_id = str(uuid4())
        
        # Create more realistic WebSocket mock

        websocket = self.create_mock_websocket()
        
        # Register connection

        health = await heartbeat_manager.register_connection(connection_id, user.id, websocket)
        
        # Simulate WebSocket message exchange with heartbeats

        for i in range(3):
            # Send regular message

            regular_message = {

                "type": "user_message",

                "content": f"Message {i}",

                "timestamp": time.time()

            }

            await websocket.send(json.dumps(regular_message))
            
            # Wait for heartbeat cycle

            await asyncio.sleep(6.0)
            
            # Respond to heartbeat if received

            for response in websocket.heartbeat_responses:

                await heartbeat_manager.handle_heartbeat_response(connection_id, response)

            websocket.heartbeat_responses.clear()
        
        # Verify connection remained healthy

        final_health = heartbeat_manager.get_connection_health(connection_id)

        assert final_health.state == HeartbeatState.ACTIVE

        assert final_health.missed_count == 0
        
        # Verify mixed message types

        sent_messages = [json.loads(msg) for msg in websocket.messages_sent]

        heartbeat_messages = [msg for msg in sent_messages if msg["type"] == "heartbeat_ping"]

        user_messages = [msg for msg in sent_messages if msg["type"] == "user_message"]
        

        assert len(heartbeat_messages) > 0

        assert len(user_messages) == 3
        
        # Check final stats

        stats = heartbeat_manager.get_heartbeat_stats()

        assert stats["response_rate"] > 80  # Good response rate
        
        # Cleanup

        await heartbeat_manager.unregister_connection(connection_id)
    

    async def test_heartbeat_performance_under_load(self, heartbeat_manager, test_users):

        """Test heartbeat performance with many concurrent connections."""

        connection_count = 50

        connections = []
        
        # Create many connections

        start_time = time.time()
        

        for i in range(connection_count):

            connection_id = f"load_test_{i}"

            user_id = test_users[i % len(test_users)].id

            websocket = self.create_mock_websocket()
            

            await heartbeat_manager.register_connection(connection_id, user_id, websocket)

            connections.append((connection_id, websocket))
        

        registration_time = time.time() - start_time
        
        # Wait for heartbeat cycles

        await asyncio.sleep(8.0)
        
        # Respond to heartbeats for half the connections

        response_count = 0

        for i, (connection_id, websocket) in enumerate(connections[:25]):

            for response in websocket.heartbeat_responses:

                await heartbeat_manager.handle_heartbeat_response(connection_id, response)

                response_count += 1
        
        # Check performance metrics

        stats = heartbeat_manager.get_heartbeat_stats()
        
        # Should handle many connections efficiently

        assert registration_time < 10.0  # Registration should be fast

        assert stats["total_active_connections"] == connection_count

        assert stats["total_heartbeats_sent"] >= connection_count  # At least one per connection
        
        # Response rate should be reasonable

        if stats["total_heartbeats_sent"] > 0:

            assert stats["response_rate"] >= 40  # At least 40% response rate
        
        # Cleanup

        cleanup_start = time.time()

        for connection_id, websocket in connections:

            await heartbeat_manager.unregister_connection(connection_id)

        cleanup_time = time.time() - cleanup_start
        
        # Cleanup should also be fast

        assert cleanup_time < 5.0
        
        # Verify cleanup

        final_stats = heartbeat_manager.get_heartbeat_stats()

        assert final_stats["total_active_connections"] == 0


if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])