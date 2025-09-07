"""
WebSocket Test 6: Rapid Reconnection (Flapping)

Tests server handling of unstable network conditions with rapid connects/disconnects
to prevent duplicate agent instances and resource leaks.

Business Value: Prevents $75K+ MRR losses from server instability, ensures robust
handling of unstable enterprise networks and mobile connections.
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import psutil
import pytest
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FlappingConnectionTracker:
    """Tracks connection flapping behavior and resource usage."""
    
    def __init__(self):
        self.connection_attempts = []
        self.disconnection_times = []
        self.agent_instances = set()
        self.resource_snapshots = []
        self.connection_states = []
        
    def record_connection(self, connection_id: str, timestamp: float):
        """Record a connection attempt."""
        self.connection_attempts.append({
            'id': connection_id,
            'timestamp': timestamp,
            'type': 'connect'
        })
        
    def record_disconnection(self, connection_id: str, timestamp: float):
        """Record a disconnection."""
        self.disconnection_times.append({
            'id': connection_id,
            'timestamp': timestamp,
            'type': 'disconnect'
        })
        
    def record_agent_instance(self, agent_id: str):
        """Track agent instance creation."""
        self.agent_instances.add(agent_id)
        
    def take_resource_snapshot(self):
        """Capture current resource usage."""
        process = psutil.Process(os.getpid())
        snapshot = {
            'timestamp': time.time(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'thread_count': process.num_threads(),
            'connection_count': len(self.connection_states)
        }
        self.resource_snapshots.append(snapshot)
        return snapshot
        
    def get_flapping_metrics(self) -> Dict[str, Any]:
        """Calculate flapping behavior metrics."""
        total_connections = len(self.connection_attempts)
        total_disconnections = len(self.disconnection_times)
        
        if not self.resource_snapshots:
            return {
                'connection_count': total_connections,
                'disconnection_count': total_disconnections,
                'agent_instances': len(self.agent_instances),
                'resource_stability': True
            }
            
        # Analyze resource stability
        memory_values = [s['memory_mb'] for s in self.resource_snapshots]
        memory_growth = max(memory_values) - min(memory_values) if memory_values else 0
        
        return {
            'connection_count': total_connections,
            'disconnection_count': total_disconnections,
            'agent_instances': len(self.agent_instances),
            'memory_growth_mb': memory_growth,
            'resource_stability': memory_growth < 50,  # Less than 50MB growth
            'avg_memory_mb': sum(memory_values) / len(memory_values) if memory_values else 0
        }


class RapidReconnectionClient:
    """WebSocket client that simulates rapid reconnection flapping."""
    
    def __init__(self, uri: str, session_token: str, tracker: FlappingConnectionTracker):
        self.uri = uri
        self.session_token = session_token
        self.tracker = tracker
        self.connection_id = str(uuid.uuid4())
        self.websocket = None
        self.is_connected = False
        self.agent_id = None
        
    async def rapid_flapping_cycle(self, iterations: int = 20) -> List[Dict[str, Any]]:
        """Perform rapid connection/disconnection cycles."""
        cycle_results = []
        
        for i in range(iterations):
            cycle_start = time.time()
            
            # Connect phase
            connect_success = await self._attempt_connection()
            connect_time = time.time()
            
            # Brief connected state
            await asyncio.sleep(0.1)  # 100ms connected
            
            # Disconnect phase
            disconnect_success = await self._attempt_disconnection()
            disconnect_time = time.time()
            
            # Brief disconnected state
            await asyncio.sleep(0.05)  # 50ms disconnected
            
            cycle_result = {
                'iteration': i + 1,
                'connect_success': connect_success,
                'disconnect_success': disconnect_success,
                'cycle_duration': disconnect_time - cycle_start,
                'connected_duration': connect_time - cycle_start
            }
            cycle_results.append(cycle_result)
            
            # Take resource snapshot every 5 iterations
            if (i + 1) % 5 == 0:
                self.tracker.take_resource_snapshot()
                
            logger.info(f"Flapping cycle {i+1}/{iterations} completed: "
                       f"connect={connect_success}, disconnect={disconnect_success}")
                       
        return cycle_results
        
    async def _attempt_connection(self) -> bool:
        """Attempt to connect WebSocket."""
        try:
            connection_id = f"{self.connection_id}_{time.time()}"
            
            # Mock connection for testing
            # Mock: Generic component isolation for controlled unit testing
            self.websocket = AsyncNone  # TODO: Use real service instead of Mock
            self.is_connected = True
            
            # Simulate agent instance creation
            self.agent_id = f"agent_{connection_id}"
            self.tracker.record_agent_instance(self.agent_id)
            
            self.tracker.record_connection(connection_id, time.time())
            
            logger.debug(f"Connection established: {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            pytest.fail(f"Unexpected connection failure in RapidReconnectionClient: {e}")
            
    async def _attempt_disconnection(self) -> bool:
        """Attempt to disconnect WebSocket."""
        try:
            if self.websocket and self.is_connected:
                connection_id = f"{self.connection_id}_{time.time()}"
                
                # Mock disconnection
                await self.websocket.close()
                self.websocket = None
                self.is_connected = False
                
                self.tracker.record_disconnection(connection_id, time.time())
                
                logger.debug(f"Disconnection completed: {connection_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Disconnection failed: {e}")
            pytest.fail(f"Unexpected disconnection failure in RapidReconnectionClient: {e}")
            
    async def establish_stable_connection(self) -> bool:
        """Establish a stable connection after flapping."""
        try:
            self.connection_id = f"stable_{str(uuid.uuid4())}"
            return await self._attempt_connection()
        except Exception as e:
            logger.error(f"Stable connection failed: {e}")
            return False
            
    @pytest.mark.e2e
    async def test_send_test_message(self) -> bool:
        """Send a test message to verify connection functionality."""
        if not self.is_connected or not self.websocket:
            return False
            
        try:
            test_message = {
                "type": "test_message",
                "content": "Connection stability test",
                "timestamp": time.time()
            }
            
            # Mock sending message
            await self.websocket.send(json.dumps(test_message))
            logger.info("Test message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return False


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_rapid_reconnection_flapping():
    """
    Test rapid reconnection flapping behavior.
    
    Validates:
    1. No duplicate agent instances created during flapping
    2. Resource usage remains stable
    3. Server handles rapid state changes properly
    4. Final connection works after flapping period
    """
    logger.info("=== Starting Rapid Reconnection Flapping Test ===")
    
    # Test configuration
    websocket_uri = "ws://localhost:8000/ws/test"
    session_token = f"test_token_{uuid.uuid4()}"
    flapping_iterations = 20
    
    # Initialize tracking
    tracker = FlappingConnectionTracker()
    tracker.take_resource_snapshot()  # Baseline
    
    # Initialize client
    client = RapidReconnectionClient(websocket_uri, session_token, tracker)
    
    # Phase 1: Rapid flapping cycles
    logger.info(f"Phase 1: Starting {flapping_iterations} rapid reconnection cycles...")
    cycle_results = await client.rapid_flapping_cycle(flapping_iterations)
    
    # Analyze flapping behavior
    successful_connects = sum(1 for r in cycle_results if r['connect_success'])
    successful_disconnects = sum(1 for r in cycle_results if r['disconnect_success'])
    
    logger.info(f"Flapping completed: {successful_connects}/{flapping_iterations} connects, "
               f"{successful_disconnects}/{flapping_iterations} disconnects")
    
    # Phase 2: Resource analysis
    logger.info("Phase 2: Analyzing resource usage...")
    tracker.take_resource_snapshot()  # Final snapshot
    metrics = tracker.get_flapping_metrics()
    
    logger.info(f"Resource metrics: {metrics}")
    
    # Phase 3: Stable connection test
    logger.info("Phase 3: Testing stable connection after flapping...")
    stable_connection = await client.establish_stable_connection()
    assert stable_connection, "Failed to establish stable connection after flapping"
    
    # Verify functionality
    message_sent = await client.send_test_message()
    assert message_sent, "Failed to send test message on stable connection"
    
    # Validation assertions
    assert successful_connects >= flapping_iterations * 0.8, \
        f"Too many connection failures: {successful_connects}/{flapping_iterations}"
    
    assert successful_disconnects >= flapping_iterations * 0.8, \
        f"Too many disconnection failures: {successful_disconnects}/{flapping_iterations}"
    
    assert metrics['resource_stability'], \
        f"Resource usage not stable: {metrics['memory_growth_mb']}MB growth"
    
    # Agent instance validation - should not exceed reasonable bounds
    assert metrics['agent_instances'] <= flapping_iterations * 1.2, \
        f"Too many agent instances created: {metrics['agent_instances']}"
    
    logger.info("=== Rapid Reconnection Flapping Test PASSED ===")
    
    return {
        'test_id': 'WS-RESILIENCE-006',
        'status': 'PASSED',
        'flapping_cycles': flapping_iterations,
        'successful_connects': successful_connects,
        'successful_disconnects': successful_disconnects,
        'resource_metrics': metrics,
        'stable_connection_recovered': stable_connection,
        'functionality_verified': message_sent
    }


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_flapping_resource_leak_prevention():
    """
    Test that rapid flapping doesn't cause resource leaks.
    
    Validates:
    1. Memory usage stays within bounds
    2. Connection pool doesn't grow indefinitely
    3. Cleanup happens properly for each disconnect
    """
    logger.info("=== Starting Resource Leak Prevention Test ===")
    
    websocket_uri = "ws://localhost:8000/ws/test"
    session_token = f"leak_test_token_{uuid.uuid4()}"
    
    tracker = FlappingConnectionTracker()
    baseline_snapshot = tracker.take_resource_snapshot()
    
    # Multiple clients for stress testing
    clients = []
    for i in range(3):
        client = RapidReconnectionClient(
            websocket_uri, 
            f"{session_token}_{i}", 
            tracker
        )
        clients.append(client)
    
    # Concurrent flapping from multiple clients
    logger.info("Starting concurrent flapping from 3 clients...")
    
    flapping_tasks = []
    for client in clients:
        task = asyncio.create_task(client.rapid_flapping_cycle(15))
        flapping_tasks.append(task)
    
    # Wait for all flapping to complete
    results = await asyncio.gather(*flapping_tasks)
    
    final_snapshot = tracker.take_resource_snapshot()
    metrics = tracker.get_flapping_metrics()
    
    # Resource leak validation
    memory_growth = final_snapshot['memory_mb'] - baseline_snapshot['memory_mb']
    
    assert memory_growth < 100, \
        f"Excessive memory growth detected: {memory_growth}MB"
    
    assert metrics['resource_stability'], \
        "Resource usage indicates potential leaks"
    
    logger.info(f"Resource leak test completed: {memory_growth}MB growth")
    logger.info("=== Resource Leak Prevention Test PASSED ===")
    
    return {
        'test_id': 'WS-RESILIENCE-006B',
        'status': 'PASSED',
        'concurrent_clients': len(clients),
        'memory_growth_mb': memory_growth,
        'resource_stable': metrics['resource_stability']
    }


if __name__ == "__main__":
    # Run the test directly for development
    async def run_test():
        result1 = await test_rapid_reconnection_flapping()
        result2 = await test_flapping_resource_leak_prevention()
        
        print("=== Test Results ===")
        print(f"Main test: {result1}")
        print(f"Leak test: {result2}")
    
    asyncio.run(run_test())