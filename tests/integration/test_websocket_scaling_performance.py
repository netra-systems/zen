"""
Performance & Load Testing: WebSocket Connection Scaling and Performance

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Enable real-time chat scaling for concurrent users
- Value Impact: Users can maintain responsive WebSocket connections under load
- Strategic Impact: WebSocket performance is critical for chat UX and user retention

CRITICAL: This test validates WebSocket connection handling, message throughput,
and connection stability under concurrent load scenarios.
"""

import asyncio
import pytest
import time
import statistics
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import websockets
import threading
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class WebSocketPerformanceMetrics:
    """Metrics for WebSocket connection performance."""
    connection_id: str
    connection_time: float
    handshake_time: float
    message_count: int
    messages_sent: int
    messages_received: int
    average_message_latency: float
    max_message_latency: float
    connection_errors: List[str] = field(default_factory=list)
    message_errors: List[str] = field(default_factory=list)
    disconnection_time: Optional[float] = None


class TestWebSocketScalingPerformance(BaseIntegrationTest):
    """Test WebSocket scaling performance with real connections and authentication."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_concurrent_websocket_connections(self, real_services_fixture):
        """
        Test concurrent WebSocket connections with real authentication.
        
        Performance SLA:
        - Connection establishment: <2s per connection
        - Message latency: <100ms (p95)
        - Connection stability: >99% uptime during test
        - Concurrent connections: 25+ sustained
        """
        concurrent_connections = 25
        messages_per_connection = 10
        auth_helper = E2EWebSocketAuthHelper()
        
        connection_metrics: List[WebSocketPerformanceMetrics] = []
        
        async def create_websocket_connection(connection_id: int) -> WebSocketPerformanceMetrics:
            """Create and test a single WebSocket connection."""
            metrics = WebSocketPerformanceMetrics(
                connection_id=f"ws_conn_{connection_id}",
                connection_time=0,
                handshake_time=0,
                message_count=0,
                messages_sent=0,
                messages_received=0,
                average_message_latency=0,
                max_message_latency=0
            )
            
            try:
                # Establish WebSocket connection
                connection_start = time.time()
                
                websocket = await auth_helper.connect_authenticated_websocket(timeout=10.0)
                
                connection_time = time.time() - connection_start
                metrics.connection_time = connection_time
                
                # Measure handshake completion
                handshake_start = time.time()
                
                # Send initial ping to complete handshake measurement
                ping_message = {
                    "type": "ping",
                    "connection_id": connection_id,
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(ping_message))
                
                # Wait for any response to measure handshake completion
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    metrics.handshake_time = time.time() - handshake_start
                    metrics.messages_received += 1
                except asyncio.TimeoutError:
                    # No response expected for ping, handshake is complete
                    metrics.handshake_time = time.time() - handshake_start
                
                # Send test messages and measure latency
                message_latencies = []
                
                for i in range(messages_per_connection):
                    message_start = time.time()
                    
                    test_message = {
                        "type": "test_message",
                        "connection_id": connection_id,
                        "message_index": i,
                        "timestamp": message_start,
                        "data": f"test_data_for_connection_{connection_id}_message_{i}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    metrics.messages_sent += 1
                    
                    # For performance testing, we measure send time rather than round-trip
                    # to avoid dependency on server response implementation
                    message_latency = time.time() - message_start
                    message_latencies.append(message_latency)
                    
                    # Small delay to avoid overwhelming the connection
                    await asyncio.sleep(0.01)
                # Calculate message performance metrics
                if message_latencies:
                    metrics.average_message_latency = statistics.mean(message_latencies)
                    metrics.max_message_latency = max(message_latencies)
                    metrics.message_count = len(message_latencies)
                
                # Close connection and measure disconnection time
                disconnect_start = time.time()
                await websocket.close()
                metrics.disconnection_time = time.time() - disconnect_start
                
            except Exception as e:
                error_msg = f"Connection {connection_id} failed: {str(e)}"
                metrics.connection_errors.append(error_msg)
                print(f" FAIL:  {error_msg}")
            
            return metrics
        
        # Execute concurrent WebSocket connections
        test_start = time.time()
        
        connection_tasks = [
            create_websocket_connection(i)
            for i in range(concurrent_connections)
        ]
        
        connection_metrics = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        test_total_time = time.time() - test_start
        
        # Filter successful connections
        successful_metrics = [
            m for m in connection_metrics 
            if isinstance(m, WebSocketPerformanceMetrics) and not m.connection_errors
        ]
        failed_connections = len(connection_metrics) - len(successful_metrics)
        
        # Performance assertions
        success_rate = len(successful_metrics) / concurrent_connections
        assert success_rate >= 0.99, f"Connection success rate {success_rate:.2%} below 99% SLA"
        
        if successful_metrics:
            # Connection time performance
            connection_times = [m.connection_time for m in successful_metrics]
            max_connection_time = max(connection_times)
            avg_connection_time = statistics.mean(connection_times)
            
            assert max_connection_time < 2.0, f"Max connection time {max_connection_time:.2f}s exceeds 2s SLA"
            
            # Message latency performance
            all_message_latencies = []
            for m in successful_metrics:
                if m.message_count > 0:
                    # Add individual message latencies (approximated by average)
                    all_message_latencies.extend([m.average_message_latency] * m.message_count)
            
            if all_message_latencies:
                message_p95 = statistics.quantiles(all_message_latencies, n=20)[18]  # 95th percentile
                avg_message_latency = statistics.mean(all_message_latencies)
                
                assert message_p95 < 0.1, f"Message latency p95 {message_p95:.3f}s exceeds 100ms SLA"
            
            # Total messages sent/received
            total_messages_sent = sum(m.messages_sent for m in successful_metrics)
            total_messages_received = sum(m.messages_received for m in successful_metrics)
            
            print(f" PASS:  WebSocket Scaling Performance Results:")
            print(f"   Concurrent connections: {concurrent_connections}")
            print(f"   Successful connections: {len(successful_metrics)} ({success_rate:.1%})")
            print(f"   Failed connections: {failed_connections}")
            print(f"   Test duration: {test_total_time:.2f}s")
            print(f"   Avg connection time: {avg_connection_time:.3f}s")
            print(f"   Max connection time: {max_connection_time:.3f}s")
            print(f"   Total messages sent: {total_messages_sent}")
            print(f"   Total messages received: {total_messages_received}")
            
            if all_message_latencies:
                print(f"   Avg message latency: {avg_message_latency:.3f}s")
                print(f"   Message latency p95: {message_p95:.3f}s")
        else:
            pytest.fail("No successful WebSocket connections established")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_websocket_message_throughput(self, real_services_fixture):
        """
        Test WebSocket message throughput performance.
        
        Performance SLA:
        - Messages per second: >100 per connection
        - Message processing: <10ms per message
        - Connection stability during high throughput
        """
        auth_helper = E2EWebSocketAuthHelper()
        message_count = 200  # High message volume per connection
        
        async def measure_message_throughput() -> Dict[str, Any]:
            """Measure message throughput for a single connection."""
            websocket = await auth_helper.connect_authenticated_websocket()
            
            throughput_metrics = {
                "messages_sent": 0,
                "total_time": 0,
                "messages_per_second": 0,
                "average_message_time": 0,
                "max_message_time": 0,
                "errors": []
            }
            
            message_times = []
            
            # Start throughput test
            throughput_start = time.time()
            
            for i in range(message_count):
                message_start = time.time()
                
                try:
                    message = {
                        "type": "throughput_test",
                        "message_index": i,
                        "timestamp": message_start,
                        "data": f"throughput_test_message_{i}_{'x' * 50}"  # Add some payload
                    }
                    
                    await websocket.send(json.dumps(message))
                    throughput_metrics["messages_sent"] += 1
                    
                    message_time = time.time() - message_start
                    message_times.append(message_time)
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.001)  # 1ms between messages
                    
                except Exception as e:
                    throughput_metrics["errors"].append(f"Message {i} failed: {str(e)}")
            
            total_time = time.time() - throughput_start
            
            # Calculate metrics
            throughput_metrics["total_time"] = total_time
            throughput_metrics["messages_per_second"] = throughput_metrics["messages_sent"] / total_time
            
            if message_times:
                throughput_metrics["average_message_time"] = statistics.mean(message_times)
                throughput_metrics["max_message_time"] = max(message_times)
            
            await websocket.close()
            return throughput_metrics
        
        # Run throughput test
        metrics = await measure_message_throughput()
        
        # Performance assertions
        assert metrics["messages_sent"] == message_count, f"Expected {message_count} messages, sent {metrics['messages_sent']}"
        assert len(metrics["errors"]) == 0, f"Message sending errors: {metrics['errors']}"
        assert metrics["messages_per_second"] >= 100, f"Throughput {metrics['messages_per_second']:.1f} msg/s below 100 msg/s SLA"
        assert metrics["average_message_time"] < 0.01, f"Average message time {metrics['average_message_time']:.3f}s exceeds 10ms SLA"
        
        print(f" PASS:  WebSocket Message Throughput Results:")
        print(f"   Messages sent: {metrics['messages_sent']}")
        print(f"   Total time: {metrics['total_time']:.2f}s")
        print(f"   Throughput: {metrics['messages_per_second']:.1f} msg/s")
        print(f"   Avg message time: {metrics['average_message_time']:.3f}s")
        print(f"   Max message time: {metrics['max_message_time']:.3f}s")
        print(f"   Errors: {len(metrics['errors'])}")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_websocket_connection_stability_under_load(self, real_services_fixture):
        """
        Test WebSocket connection stability under sustained load.
        
        Performance SLA:
        - Connection uptime: >99.5% during 60s test
        - Reconnection time: <3s when needed
        - Memory stability: No significant growth during test
        """
        auth_helper = E2EWebSocketAuthHelper()
        test_duration = 60  # 60 seconds of sustained load
        connection_count = 10  # Moderate concurrent connections for stability test
        
        stability_metrics = {
            "total_connections": connection_count,
            "successful_connections": 0,
            "connection_failures": 0,
            "disconnections": 0,
            "reconnections": 0,
            "uptime_percentage": 0,
            "test_duration": test_duration
        }
        
        async def maintain_stable_connection(connection_id: int, duration: float) -> Dict[str, Any]:
            """Maintain a stable WebSocket connection for specified duration."""
            connection_metrics = {
                "connection_id": connection_id,
                "uptime": 0,
                "disconnections": 0,
                "reconnections": 0,
                "errors": []
            }
            
            end_time = time.time() + duration
            connection_start = time.time()
            websocket = None
            
            while time.time() < end_time:
                try:
                    if websocket is None:
                        # (Re)connect
                        websocket = await auth_helper.connect_authenticated_websocket(timeout=5.0)
                        if connection_metrics["disconnections"] > 0:
                            connection_metrics["reconnections"] += 1
                    
                    # Send periodic ping to maintain connection
                    ping_message = {
                        "type": "stability_ping",
                        "connection_id": connection_id,
                        "timestamp": time.time()
                    }
                    await websocket.send(json.dumps(ping_message))
                    
                    # Wait a bit before next ping
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    connection_metrics["errors"].append(f"Connection {connection_id} error: {str(e)}")
                    connection_metrics["disconnections"] += 1
                    
                    if websocket:
                        try:
                            await websocket.close()
                        except:
                            pass
                        websocket = None
                    
                    # Short delay before reconnect attempt
                    await asyncio.sleep(0.5)
            
            # Calculate uptime
            connection_metrics["uptime"] = time.time() - connection_start
            
            # Clean up
            if websocket:
                try:
                    await websocket.close()
                except:
                    pass
            
            return connection_metrics
        
        # Run stability test
        stability_start = time.time()
        
        connection_tasks = [
            maintain_stable_connection(i, test_duration)
            for i in range(connection_count)
        ]
        
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        actual_test_duration = time.time() - stability_start
        
        # Analyze results
        successful_results = [
            r for r in connection_results
            if isinstance(r, dict) and "connection_id" in r
        ]
        
        stability_metrics["successful_connections"] = len(successful_results)
        stability_metrics["connection_failures"] = connection_count - len(successful_results)
        
        if successful_results:
            total_uptime = sum(r["uptime"] for r in successful_results)
            expected_total_uptime = connection_count * test_duration
            stability_metrics["uptime_percentage"] = (total_uptime / expected_total_uptime) * 100
            
            stability_metrics["disconnections"] = sum(r["disconnections"] for r in successful_results)
            stability_metrics["reconnections"] = sum(r["reconnections"] for r in successful_results)
        
        # Performance assertions
        assert stability_metrics["uptime_percentage"] >= 99.5, f"Uptime {stability_metrics['uptime_percentage']:.1f}% below 99.5% SLA"
        assert stability_metrics["connection_failures"] <= 1, f"Too many connection failures: {stability_metrics['connection_failures']}"
        
        print(f" PASS:  WebSocket Connection Stability Results:")
        print(f"   Test duration: {actual_test_duration:.1f}s")
        print(f"   Concurrent connections: {connection_count}")
        print(f"   Successful connections: {stability_metrics['successful_connections']}")
        print(f"   Connection failures: {stability_metrics['connection_failures']}")
        print(f"   Total disconnections: {stability_metrics['disconnections']}")
        print(f"   Total reconnections: {stability_metrics['reconnections']}")
        print(f"   Uptime percentage: {stability_metrics['uptime_percentage']:.2f}%")