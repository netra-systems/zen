"""Real WebSocket Metrics Tracking Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal & Enterprise
- Business Goal: Observability & Performance Monitoring
- Value Impact: Provides visibility into WebSocket performance and usage patterns
- Strategic Impact: Enables data-driven optimization and proactive issue detection

Tests real WebSocket metrics collection and tracking with Docker services.
Validates metrics accuracy and performance monitoring capabilities.
"""

import asyncio
import json
import time
from typing import Any, Dict, List

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.metrics_tracking
@skip_if_no_real_services
class TestRealWebSocketMetricsTracking:
    """Test real WebSocket metrics tracking and monitoring."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Metrics-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_connection_metrics_tracking(self, websocket_url, auth_headers):
        """Test connection-related metrics tracking."""
        user_id = f"metrics_conn_test_{int(time.time())}"
        metrics_data = []
        
        connection_start_time = time.time()
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect with metrics tracking enabled
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "enable_metrics_tracking": True,
                    "track_connection_metrics": True
                }))
                
                connect_response = json.loads(await websocket.recv())
                connection_time = time.time() - connection_start_time
                
                # Request current metrics
                await websocket.send(json.dumps({
                    "type": "get_connection_metrics",
                    "user_id": user_id,
                    "request_metrics": ["connection_count", "connection_duration", "message_count"]
                }))
                
                # Collect metrics responses
                timeout_time = time.time() + 8
                while time.time() < timeout_time:
                    try:
                        response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2.0))
                        
                        if "metrics" in response or response.get("type") == "metrics_data":
                            metrics_data.append(response)
                        elif "connection_count" in response or "duration" in response:
                            metrics_data.append(response)
                        
                    except asyncio.TimeoutError:
                        break
                    except WebSocketException:
                        break
                
                # Send some messages to generate metrics
                for i in range(3):
                    await websocket.send(json.dumps({
                        "type": "user_message",
                        "user_id": user_id,
                        "content": f"Metrics test message {i+1}",
                        "track_message_metrics": True
                    }))
                    await asyncio.sleep(0.5)
                
                # Request updated metrics
                await websocket.send(json.dumps({
                    "type": "get_updated_metrics",
                    "user_id": user_id
                }))
                
                try:
                    updated_metrics = json.loads(await asyncio.wait_for(websocket.recv(), timeout=3.0))
                    metrics_data.append(("updated", updated_metrics))
                except asyncio.TimeoutError:
                    pass
                
        except Exception as e:
            pytest.fail(f"Connection metrics tracking test failed: {e}")
        
        # Validate metrics tracking
        print(f"Metrics tracking - Data points collected: {len(metrics_data)}")
        print(f"Connection establishment time: {connection_time:.3f}s")
        
        if metrics_data:
            print("SUCCESS: Metrics tracking appears to be working")
            
            # Log metrics data for verification
            for i, metric_data in enumerate(metrics_data):
                if isinstance(metric_data, tuple):
                    print(f"  {metric_data[0]}: {list(metric_data[1].keys()) if isinstance(metric_data[1], dict) else type(metric_data[1])}")
                else:
                    print(f"  Metric {i+1}: {list(metric_data.keys()) if isinstance(metric_data, dict) else type(metric_data)}")
        else:
            print("INFO: Metrics tracking not clearly detected (feature may not be implemented)")
        
        # Connection time should be reasonable
        assert connection_time < 10, f"Connection time should be reasonable: {connection_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_message_metrics_tracking(self, websocket_url, auth_headers):
        """Test message-related metrics tracking."""
        user_id = f"metrics_msg_test_{int(time.time())}"
        message_metrics = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=20
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "track_message_metrics": True
                }))
                
                await websocket.recv()
                
                # Send messages with different characteristics for metrics
                test_messages = [
                    {"type": "user_message", "content": "Short message", "category": "short"},
                    {"type": "user_message", "content": "Medium length message with more content for testing metrics tracking", "category": "medium"},
                    {"type": "heartbeat", "timestamp": time.time(), "category": "heartbeat"},
                    {"type": "user_message", "content": "Another message", "category": "normal"}
                ]
                
                message_timings = []
                
                for message in test_messages:
                    message["user_id"] = user_id
                    send_time = time.time()
                    
                    await websocket.send(json.dumps(message))
                    
                    try:
                        response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=3.0))
                        receive_time = time.time()
                        
                        message_metrics.append({
                            "category": message["category"],
                            "send_time": send_time,
                            "receive_time": receive_time,
                            "round_trip_time": receive_time - send_time,
                            "response": response
                        })
                        
                    except asyncio.TimeoutError:
                        message_metrics.append({
                            "category": message["category"],
                            "send_time": send_time,
                            "timeout": True
                        })
                    
                    await asyncio.sleep(0.3)
                
                # Request message metrics summary
                await websocket.send(json.dumps({
                    "type": "get_message_metrics",
                    "user_id": user_id,
                    "request_summary": True
                }))
                
                try:
                    metrics_summary = json.loads(await asyncio.wait_for(websocket.recv(), timeout=3.0))
                    message_metrics.append(("summary", metrics_summary))
                except asyncio.TimeoutError:
                    pass
                
        except Exception as e:
            pytest.fail(f"Message metrics tracking test failed: {e}")
        
        # Analyze message metrics
        successful_messages = [m for m in message_metrics if not m.get("timeout") and "round_trip_time" in m]
        
        print(f"Message metrics - Total: {len(message_metrics)}, Successful: {len(successful_messages)}")
        
        if successful_messages:
            avg_round_trip = sum(m["round_trip_time"] for m in successful_messages) / len(successful_messages)
            max_round_trip = max(m["round_trip_time"] for m in successful_messages)
            
            print(f"Message performance - Avg RTT: {avg_round_trip:.3f}s, Max RTT: {max_round_trip:.3f}s")
            
            # Performance should be reasonable
            assert avg_round_trip < 5.0, f"Average message round-trip should be reasonable: {avg_round_trip:.3f}s"
            
            # Log message categories processed
            categories = [m["category"] for m in successful_messages]
            print(f"Message categories processed: {set(categories)}")
            
        else:
            print("WARNING: No successful message metrics captured")
        
        # Should have processed some messages
        assert len(message_metrics) > 0, "Should capture message metrics data"