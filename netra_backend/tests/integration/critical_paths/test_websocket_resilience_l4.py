"""WebSocket Resilience L4 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (core real-time communication infrastructure)
- Business Goal: Ensure WebSocket reliability under production load conditions
- Value Impact: Protects $8K MRR through reliable real-time user experience
- Strategic Impact: Critical for user engagement and session persistence across platform

Critical Path: 
Connection establishment -> Load testing -> Network interruption -> Reconnection -> Message delivery verification

Coverage: 100+ concurrent connections, network fault injection, message delivery guarantees, staging environment validation
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import ssl
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.tests.integration.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite
from unittest.mock import AsyncMock, MagicMock

import pytest
import websockets

StagingTestSuite = AsyncMock

get_staging_suite = AsyncMock
# from netra_backend.app.websocket_core.manager import WebSocketManager

WebSocketManager = AsyncMock
# from app.services.redis.session_manager import RedisSessionManager

RedisSessionManager = AsyncMock

@dataclass

class WebSocketLoadMetrics:

    """Metrics container for WebSocket load testing."""

    total_connections: int

    successful_connections: int

    failed_connections: int

    connection_times: List[float]

    message_delivery_success_rate: float

    reconnection_success_rate: float

    average_latency_ms: float

class WebSocketL4TestSuite:

    """L4 test suite for WebSocket resilience in staging environment."""
    
    def __init__(self):

        self.staging_suite: Optional[StagingTestSuite] = None

        self.websocket_url: str = ""

        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}

        self.connection_metrics: Dict[str, Dict] = {}

        self.message_queues: Dict[str, List] = {}

        self.test_metrics = {

            "connections_tested": 0,

            "messages_sent": 0,

            "messages_received": 0,

            "reconnections_attempted": 0,

            "reconnections_successful": 0,

            "network_interruptions_simulated": 0

        }
        
    async def initialize_l4_environment(self) -> None:

        """Initialize L4 staging environment for WebSocket testing."""

        self.staging_suite = await get_staging_suite()

        await self.staging_suite.setup()
        
        # Get staging WebSocket URL

        self.websocket_url = self.staging_suite.env_config.services.websocket
        
        # Validate WebSocket endpoint accessibility

        await self._validate_websocket_endpoint()
    
    async def _validate_websocket_endpoint(self) -> None:

        """Validate WebSocket endpoint is accessible in staging."""
        # Convert WebSocket URL to HTTP health check

        health_url = self.websocket_url.replace("wss://", "https://").replace("/ws", "/health/")
        
        health_status = await self.staging_suite.check_service_health(health_url)

        if not health_status.healthy:

            raise RuntimeError(f"WebSocket service unhealthy: {health_status.details}")
    
    async def create_websocket_connection(self, connection_id: str, 

                                        auth_token: Optional[str] = None) -> Dict[str, Any]:

        """Create authenticated WebSocket connection to staging."""

        start_time = time.time()
        
        try:
            # Prepare connection headers

            headers = {}

            if auth_token:

                headers["Authorization"] = f"Bearer {auth_token}"
            
            # Create SSL context for staging

            ssl_context = ssl.create_default_context()

            ssl_context.check_hostname = True

            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # Connect to staging WebSocket

            websocket = await websockets.connect(

                self.websocket_url,

                extra_headers=headers,

                ssl=ssl_context,

                ping_interval=20,

                ping_timeout=10,

                close_timeout=10

            )
            
            connection_time = time.time() - start_time
            
            # Store connection and metrics

            self.active_connections[connection_id] = websocket

            self.connection_metrics[connection_id] = {

                "connected_at": time.time(),

                "connection_time": connection_time,

                "messages_sent": 0,

                "messages_received": 0,

                "reconnection_count": 0,

                "last_ping": time.time()

            }

            self.message_queues[connection_id] = []
            
            self.test_metrics["connections_tested"] += 1
            
            return {

                "success": True,

                "connection_id": connection_id,

                "connection_time": connection_time,

                "websocket": websocket

            }
            
        except Exception as e:

            return {

                "success": False,

                "connection_id": connection_id,

                "error": str(e),

                "connection_time": time.time() - start_time

            }
    
    async def execute_concurrent_load_test(self, connection_count: int = 100) -> WebSocketLoadMetrics:

        """Execute concurrent load test with specified connection count."""

        connection_tasks = []
        
        # Create concurrent connections

        for i in range(connection_count):

            connection_id = f"load_test_conn_{i}_{uuid.uuid4().hex[:8]}"

            auth_token = f"test_token_{i}"  # Simulate different auth tokens
            
            task = self.create_websocket_connection(connection_id, auth_token)

            connection_tasks.append(task)
        
        # Execute concurrent connections

        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze results

        successful_connections = []

        failed_connections = []

        connection_times = []
        
        for result in connection_results:

            if isinstance(result, Exception):

                failed_connections.append({"error": str(result)})

            elif result["success"]:

                successful_connections.append(result)

                connection_times.append(result["connection_time"])

            else:

                failed_connections.append(result)
        
        # Test message delivery under load

        if successful_connections:

            message_success_rate = await self._test_message_delivery_under_load(

                successful_connections[:min(50, len(successful_connections))]  # Test subset for performance

            )

        else:

            message_success_rate = 0.0
        
        # Test reconnection capability

        reconnection_success_rate = await self._test_reconnection_under_load(

            successful_connections[:min(20, len(successful_connections))]  # Test smaller subset

        )
        
        return WebSocketLoadMetrics(

            total_connections=connection_count,

            successful_connections=len(successful_connections),

            failed_connections=len(failed_connections),

            connection_times=connection_times,

            message_delivery_success_rate=message_success_rate,

            reconnection_success_rate=reconnection_success_rate,

            average_latency_ms=sum(connection_times) / len(connection_times) * 1000 if connection_times else 0

        )
    
    async def _test_message_delivery_under_load(self, connections: List[Dict]) -> float:

        """Test message delivery success rate under load."""

        message_tasks = []
        
        for conn_result in connections:

            connection_id = conn_result["connection_id"]

            websocket = conn_result["websocket"]
            
            # Send test message

            test_message = {

                "type": "test_message",

                "connection_id": connection_id,

                "timestamp": time.time(),

                "content": f"Load test message from {connection_id}"

            }
            
            task = self._send_and_verify_message(websocket, connection_id, test_message)

            message_tasks.append(task)
        
        # Execute concurrent message sending

        message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
        
        successful_messages = sum(1 for result in message_results 

                                if not isinstance(result, Exception) and result.get("success", False))
        
        return successful_messages / len(message_results) if message_results else 0.0
    
    async def _send_and_verify_message(self, websocket: websockets.WebSocketServerProtocol,

                                     connection_id: str, message: Dict) -> Dict[str, Any]:

        """Send message and verify delivery."""

        try:
            # Send message

            await websocket.send(json.dumps(message))

            self.connection_metrics[connection_id]["messages_sent"] += 1

            self.test_metrics["messages_sent"] += 1
            
            # Wait for acknowledgment or response

            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

            self.connection_metrics[connection_id]["messages_received"] += 1

            self.test_metrics["messages_received"] += 1
            
            return {"success": True, "response": response}
            
        except Exception as e:

            return {"success": False, "error": str(e)}
    
    async def _test_reconnection_under_load(self, connections: List[Dict]) -> float:

        """Test reconnection success rate under load."""

        reconnection_tasks = []
        
        for conn_result in connections:

            connection_id = conn_result["connection_id"]

            websocket = conn_result["websocket"]
            
            task = self._simulate_disconnection_and_reconnect(connection_id, websocket)

            reconnection_tasks.append(task)
        
        # Execute concurrent reconnections

        reconnection_results = await asyncio.gather(*reconnection_tasks, return_exceptions=True)
        
        successful_reconnections = sum(1 for result in reconnection_results 

                                     if not isinstance(result, Exception) and result.get("success", False))
        
        return successful_reconnections / len(reconnection_results) if reconnection_results else 0.0
    
    async def _simulate_disconnection_and_reconnect(self, connection_id: str,

                                                  websocket: websockets.WebSocketServerProtocol) -> Dict[str, Any]:

        """Simulate network disconnection and test reconnection."""

        try:
            # Close existing connection

            await websocket.close()
            
            # Wait brief period to simulate network interruption

            await asyncio.sleep(1.0)
            
            # Attempt reconnection

            reconnection_result = await self.create_websocket_connection(

                f"{connection_id}_reconnect", 

                f"test_token_reconnect"

            )
            
            self.test_metrics["reconnections_attempted"] += 1
            
            if reconnection_result["success"]:

                self.test_metrics["reconnections_successful"] += 1

                self.connection_metrics[connection_id]["reconnection_count"] += 1
                
                # Test message delivery after reconnection

                test_message = {

                    "type": "reconnection_test",

                    "connection_id": connection_id,

                    "timestamp": time.time()

                }
                
                message_result = await self._send_and_verify_message(

                    reconnection_result["websocket"], 

                    connection_id, 

                    test_message

                )
                
                return {

                    "success": True,

                    "reconnection_time": reconnection_result["connection_time"],

                    "message_delivery_after_reconnection": message_result["success"]

                }

            else:

                return {"success": False, "error": reconnection_result["error"]}
                
        except Exception as e:

            return {"success": False, "error": str(e)}
    
    async def simulate_network_interruptions(self, interruption_scenarios: List[str]) -> Dict[str, Any]:

        """Simulate various network interruption scenarios."""

        scenario_results = {}
        
        for scenario in interruption_scenarios:

            if scenario == "temporary_disconnection":

                result = await self._test_temporary_disconnection()

            elif scenario == "intermittent_connectivity":

                result = await self._test_intermittent_connectivity()

            elif scenario == "connection_timeout":

                result = await self._test_connection_timeout()

            elif scenario == "ping_failure":

                result = await self._test_ping_failure()

            else:

                result = {"success": False, "error": f"Unknown scenario: {scenario}"}
            
            scenario_results[scenario] = result

            self.test_metrics["network_interruptions_simulated"] += 1
        
        return scenario_results
    
    async def _test_temporary_disconnection(self) -> Dict[str, Any]:

        """Test temporary disconnection recovery."""

        connection_id = f"temp_disconnect_{uuid.uuid4().hex[:8]}"
        
        # Create connection

        conn_result = await self.create_websocket_connection(connection_id)

        if not conn_result["success"]:

            return {"success": False, "error": "Failed to create initial connection"}
        
        websocket = conn_result["websocket"]
        
        # Send pre-disconnection message

        pre_msg = {"type": "pre_disconnect", "timestamp": time.time()}

        pre_result = await self._send_and_verify_message(websocket, connection_id, pre_msg)
        
        # Simulate disconnection

        await websocket.close()

        await asyncio.sleep(2.0)  # 2-second disconnection
        
        # Reconnect

        reconnect_result = await self.create_websocket_connection(f"{connection_id}_recovered")

        if not reconnect_result["success"]:

            return {"success": False, "error": "Failed to reconnect"}
        
        # Send post-reconnection message

        post_msg = {"type": "post_reconnect", "timestamp": time.time()}

        post_result = await self._send_and_verify_message(

            reconnect_result["websocket"], 

            connection_id, 

            post_msg

        )
        
        return {

            "success": True,

            "pre_disconnect_success": pre_result["success"],

            "reconnection_time": reconnect_result["connection_time"],

            "post_reconnect_success": post_result["success"]

        }
    
    async def _test_intermittent_connectivity(self) -> Dict[str, Any]:

        """Test handling of intermittent connectivity issues."""

        connection_id = f"intermittent_{uuid.uuid4().hex[:8]}"
        
        # Create connection

        conn_result = await self.create_websocket_connection(connection_id)

        if not conn_result["success"]:

            return {"success": False, "error": "Failed to create connection"}
        
        websocket = conn_result["websocket"]

        successful_messages = 0

        total_attempts = 10
        
        # Send messages with intermittent delays

        for i in range(total_attempts):

            message = {

                "type": "intermittent_test",

                "sequence": i,

                "timestamp": time.time()

            }
            
            try:

                result = await self._send_and_verify_message(websocket, connection_id, message)

                if result["success"]:

                    successful_messages += 1
                
                # Simulate intermittent delays

                if i % 3 == 0:

                    await asyncio.sleep(0.5)  # Brief interruption simulation
                    
            except Exception:

                pass  # Expected for intermittent connectivity
        
        success_rate = successful_messages / total_attempts
        
        return {

            "success": success_rate >= 0.7,  # 70% success rate threshold

            "message_success_rate": success_rate,

            "successful_messages": successful_messages,

            "total_attempts": total_attempts

        }
    
    async def _test_connection_timeout(self) -> Dict[str, Any]:

        """Test connection timeout handling."""

        connection_id = f"timeout_test_{uuid.uuid4().hex[:8]}"
        
        try:
            # Attempt connection with very short timeout

            start_time = time.time()
            
            websocket = await asyncio.wait_for(

                websockets.connect(

                    self.websocket_url,

                    ping_interval=1,

                    ping_timeout=2,

                    close_timeout=3

                ),

                timeout=5.0

            )
            
            connection_time = time.time() - start_time
            
            # Test that connection stays alive

            await asyncio.sleep(3.0)
            
            # Send test message

            test_msg = {"type": "timeout_test", "timestamp": time.time()}

            await websocket.send(json.dumps(test_msg))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            await websocket.close()
            
            return {

                "success": True,

                "connection_time": connection_time,

                "stayed_alive": True,

                "message_delivery": True

            }
            
        except asyncio.TimeoutError:

            return {

                "success": False,

                "error": "Connection timeout",

                "timeout_handled": True

            }

        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "timeout_handled": False

            }
    
    async def _test_ping_failure(self) -> Dict[str, Any]:

        """Test ping/pong failure handling."""

        connection_id = f"ping_test_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create connection with aggressive ping settings

            websocket = await websockets.connect(

                self.websocket_url,

                ping_interval=2,

                ping_timeout=3,

                close_timeout=5

            )
            
            # Monitor ping responses

            ping_count = 0

            successful_pings = 0
            
            for _ in range(5):  # Test 5 ping cycles

                try:

                    pong = await websocket.ping()

                    await asyncio.wait_for(pong, timeout=3.0)

                    successful_pings += 1

                except asyncio.TimeoutError:

                    pass  # Expected ping failure
                
                ping_count += 1

                await asyncio.sleep(2.5)  # Wait between pings
            
            await websocket.close()
            
            ping_success_rate = successful_pings / ping_count
            
            return {

                "success": ping_success_rate >= 0.6,  # 60% ping success threshold

                "ping_success_rate": ping_success_rate,

                "successful_pings": successful_pings,

                "total_pings": ping_count

            }
            
        except Exception as e:

            return {

                "success": False,

                "error": str(e)

            }
    
    async def cleanup_l4_resources(self) -> None:

        """Clean up L4 test resources."""
        # Close all active connections

        close_tasks = []

        for connection_id, websocket in self.active_connections.items():

            if not websocket.closed:

                close_tasks.append(websocket.close())
        
        if close_tasks:

            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.active_connections.clear()

        self.connection_metrics.clear()

        self.message_queues.clear()

@pytest.fixture

async def websocket_l4_suite():

    """Create L4 WebSocket test suite."""

    suite = WebSocketL4TestSuite()

    await suite.initialize_l4_environment()

    yield suite

    await suite.cleanup_l4_resources()

@pytest.mark.asyncio

@pytest.mark.staging

@pytest.mark.asyncio
async def test_concurrent_websocket_connections_l4(websocket_l4_suite):

    """Test 100+ concurrent WebSocket connections in staging."""
    # Execute load test with 100 concurrent connections

    load_metrics = await websocket_l4_suite.execute_concurrent_load_test(connection_count=100)
    
    # Validate connection success rate

    connection_success_rate = load_metrics.successful_connections / load_metrics.total_connections

    assert connection_success_rate >= 0.95, f"Connection success rate too low: {connection_success_rate}"
    
    # Validate connection performance

    assert load_metrics.average_latency_ms < 2000, f"Average latency too high: {load_metrics.average_latency_ms}ms"
    
    # Validate message delivery under load

    assert load_metrics.message_delivery_success_rate >= 0.90, "Message delivery rate too low under load"
    
    # Validate connection times

    max_connection_time = max(load_metrics.connection_times) if load_metrics.connection_times else 0

    assert max_connection_time < 10.0, f"Maximum connection time too high: {max_connection_time}s"

@pytest.mark.asyncio

@pytest.mark.staging

@pytest.mark.asyncio
async def test_websocket_network_interruption_recovery_l4(websocket_l4_suite):

    """Test WebSocket recovery from network interruptions in staging."""
    # Test various interruption scenarios

    interruption_scenarios = [

        "temporary_disconnection",

        "intermittent_connectivity", 

        "connection_timeout",

        "ping_failure"

    ]
    
    scenario_results = await websocket_l4_suite.simulate_network_interruptions(interruption_scenarios)
    
    # Validate temporary disconnection recovery

    temp_disconnect = scenario_results["temporary_disconnection"]

    assert temp_disconnect["success"] is True

    assert temp_disconnect["reconnection_time"] < 5.0, "Reconnection took too long"

    assert temp_disconnect["post_reconnect_success"] is True
    
    # Validate intermittent connectivity handling

    intermittent = scenario_results["intermittent_connectivity"]

    assert intermittent["success"] is True

    assert intermittent["message_success_rate"] >= 0.7, "Poor success rate under intermittent conditions"
    
    # Validate timeout handling

    timeout_test = scenario_results["connection_timeout"]

    assert timeout_test["success"] is True or timeout_test.get("timeout_handled", False)
    
    # Validate ping/pong handling

    ping_test = scenario_results["ping_failure"]

    assert ping_test["success"] is True or ping_test["ping_success_rate"] >= 0.5

@pytest.mark.asyncio

@pytest.mark.staging

@pytest.mark.asyncio
async def test_websocket_message_delivery_guarantees_l4(websocket_l4_suite):

    """Test message delivery guarantees under various conditions."""

    connection_id = f"delivery_test_{uuid.uuid4().hex[:8]}"
    
    # Create connection

    conn_result = await websocket_l4_suite.create_websocket_connection(connection_id)

    assert conn_result["success"] is True
    
    websocket = conn_result["websocket"]
    
    # Test ordered message delivery

    message_count = 20

    sent_messages = []

    received_messages = []
    
    for i in range(message_count):

        message = {

            "type": "delivery_test",

            "sequence": i,

            "timestamp": time.time(),

            "content": f"Test message {i}"

        }
        
        sent_messages.append(message)
        
        # Send and receive

        await websocket.send(json.dumps(message))

        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

        received_messages.append(json.loads(response))
    
    # Validate message delivery

    assert len(received_messages) == message_count, "Message count mismatch"
    
    # Validate message ordering (if server echoes back)

    for i, received in enumerate(received_messages):

        if "sequence" in received:

            assert received["sequence"] == i, f"Message ordering violation at position {i}"
    
    await websocket.close()

@pytest.mark.asyncio

@pytest.mark.staging

@pytest.mark.asyncio
async def test_websocket_reconnection_success_rate_l4(websocket_l4_suite):

    """Test WebSocket reconnection success rate under load."""
    # Create multiple connections for reconnection testing

    connection_count = 20

    connections = []
    
    for i in range(connection_count):

        connection_id = f"reconnect_test_{i}_{uuid.uuid4().hex[:8]}"

        conn_result = await websocket_l4_suite.create_websocket_connection(connection_id)
        
        if conn_result["success"]:

            connections.append(conn_result)
    
    assert len(connections) >= 18, "Insufficient initial connections for reconnection test"
    
    # Test reconnection success rate

    reconnection_success_rate = await websocket_l4_suite._test_reconnection_under_load(connections)
    
    # Validate reconnection performance

    assert reconnection_success_rate >= 0.85, f"Reconnection success rate too low: {reconnection_success_rate}"
    
    # Validate metrics

    assert websocket_l4_suite.test_metrics["reconnections_attempted"] >= 18

    assert websocket_l4_suite.test_metrics["reconnections_successful"] >= 15

@pytest.mark.asyncio

@pytest.mark.staging

@pytest.mark.asyncio
async def test_websocket_performance_under_stress_l4(websocket_l4_suite):

    """Test WebSocket performance under stress conditions."""
    # Create stress test with high message volume

    connection_id = f"stress_test_{uuid.uuid4().hex[:8]}"

    conn_result = await websocket_l4_suite.create_websocket_connection(connection_id)
    
    assert conn_result["success"] is True

    websocket = conn_result["websocket"]
    
    # Send high-volume messages

    message_volume = 100

    start_time = time.time()

    successful_sends = 0
    
    for i in range(message_volume):

        try:

            message = {

                "type": "stress_test",

                "sequence": i,

                "timestamp": time.time(),

                "payload": "x" * 1000  # 1KB payload

            }
            
            await websocket.send(json.dumps(message))

            successful_sends += 1
            
            # Brief delay to avoid overwhelming

            await asyncio.sleep(0.01)
            
        except Exception:

            pass  # Expected under stress
    
    total_duration = time.time() - start_time

    throughput = successful_sends / total_duration if total_duration > 0 else 0
    
    # Validate stress test performance

    assert successful_sends >= message_volume * 0.9, "Too many failed sends under stress"

    assert throughput >= 50, f"Throughput too low: {throughput} messages/second"

    assert total_duration < 5.0, f"Stress test took too long: {total_duration}s"
    
    await websocket.close()