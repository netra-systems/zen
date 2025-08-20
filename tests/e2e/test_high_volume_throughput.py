"""
Test Suite 10: High-Volume Message Throughput - E2E Implementation

This comprehensive test suite validates the Netra Apex AI platform's capability to handle 
massive message throughput while maintaining message ordering, low latency, and delivery 
guarantees. Tests flood the WebSocket server with thousands of messages per second to 
identify scalability limits and ensure system resilience under extreme load.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Platform Stability, Scalability Validation, Risk Reduction
- Value Impact: Ensures system can handle high-volume enterprise workloads during peak usage
- Strategic/Revenue Impact: Critical for enterprise contract retention and multi-tenant scaling
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import random
import threading
import gc
import psutil
import os
import statistics
import tracemalloc
import functools
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict, deque
from dataclasses import dataclass, field

# WebSocket client imports
import websockets
import httpx

# Configure logging for high-volume testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
E2E_TEST_CONFIG = {
    "websocket_url": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8765"),  # Mock server port
    "backend_url": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
    "auth_service_url": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "skip_real_services": os.getenv("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_mode": os.getenv("HIGH_VOLUME_TEST_MODE", "mock")  # mock or real
}

# High-volume test configuration
HIGH_VOLUME_CONFIG = {
    # Throughput targets
    "max_message_rate": 10000,           # messages/second
    "sustained_throughput_target": 5000, # messages/second
    "peak_throughput_target": 10000,     # messages/second
    
    # Latency requirements
    "latency_p50_target": 0.05,          # 50ms
    "latency_p95_target": 0.2,           # 200ms  
    "latency_p99_target": 0.5,           # 500ms
    
    # Connection and scaling
    "max_concurrent_connections": 500,
    "connection_scaling_steps": [1, 10, 50, 100, 250, 500],
    "message_rate_scaling_steps": [100, 500, 1000, 2500, 5000, 7500, 10000],
    
    # Test durations
    "burst_duration": 60,                # seconds
    "sustained_load_time": 30,           # seconds
    "ramp_up_time": 10,                  # seconds
    "ramp_down_time": 10,                # seconds
    "stress_test_duration": 300,         # 5 minutes
    
    # Resource limits
    "max_memory_growth_mb": 200,
    "memory_leak_threshold_mb": 50,
    "cpu_usage_threshold": 0.8,          # 80%
    
    # Reliability thresholds
    "min_delivery_ratio": 0.999,         # 99.9%
    "max_message_loss_ratio": 0.001,     # 0.1%
    "max_duplicate_ratio": 0.001,        # 0.1%
    
    # Queue and backpressure
    "queue_overflow_threshold": 10000,
    "backpressure_timeout": 5.0,
    "queue_recovery_timeout": 30.0,
    
    # Error injection
    "error_injection_rate": 0.1,         # 10%
    "connection_drop_rate": 0.05,        # 5%
    "network_failure_duration": 5.0,     # seconds
}


class ThroughputMetrics(NamedTuple):
    """Comprehensive throughput metrics."""
    messages_sent: int
    messages_received: int
    messages_failed: int
    send_rate: float  # messages/second
    receive_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    delivery_ratio: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage: float
    queue_depth: int
    backpressure_events: int


@dataclass
class LatencyMeasurement:
    """Individual latency measurement."""
    message_id: str
    send_time: float
    receive_time: float
    processing_time: float
    queue_time: float = 0.0
    
    @property
    def total_latency(self) -> float:
        """Total end-to-end latency."""
        return self.receive_time - self.send_time
    
    @property
    def server_latency(self) -> float:
        """Server processing latency."""
        return self.processing_time


@dataclass
class LoadTestResults:
    """Comprehensive load test results."""
    test_name: str
    start_time: float
    end_time: float
    total_duration: float
    
    # Throughput metrics
    peak_throughput: float = 0.0
    sustained_throughput: float = 0.0
    average_throughput: float = 0.0
    
    # Latency metrics
    latency_measurements: List[LatencyMeasurement] = field(default_factory=list)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_p999: float = 0.0
    
    # Reliability metrics
    messages_sent: int = 0
    messages_received: int = 0
    messages_failed: int = 0
    delivery_ratio: float = 0.0
    duplicate_count: int = 0
    ordering_violations: int = 0
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    memory_growth_mb: float = 0.0
    peak_cpu_usage: float = 0.0
    connection_count: int = 0
    
    # Error and recovery metrics
    error_count: int = 0
    recovery_count: int = 0
    backpressure_events: int = 0
    queue_overflow_events: int = 0
    
    # Scaling metrics
    connection_scaling_data: Dict[int, ThroughputMetrics] = field(default_factory=dict)
    rate_scaling_data: Dict[int, ThroughputMetrics] = field(default_factory=dict)


class HighVolumeWebSocketServer:
    """High-performance mock WebSocket server for throughput testing."""
    
    def __init__(self, port=8765, max_connections=1000):
        self.port = port
        self.max_connections = max_connections
        self.server = None
        self.clients = set()
        self.message_counter = 0
        self.processed_messages = {}
        self.queue_depth = 0
        self.start_time = time.time()
        
        # Performance tracking
        self.throughput_history = []
        self.latency_history = []
        self.error_count = 0
        self.backpressure_triggered = False
        
        # Resource monitoring
        self.initial_memory = psutil.Process().memory_info().rss
        self.peak_memory = self.initial_memory
        
    async def start(self):
        """Start high-performance WebSocket server."""
        self.server = await websockets.serve(
            self.handle_client,
            "localhost",
            self.port,
            max_size=2**20,  # 1MB max message size
            max_queue=1000,   # High connection queue
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        logger.info(f"High-volume WebSocket server started on ws://localhost:{self.port}")
        
        # Start background monitoring
        asyncio.create_task(self._monitor_performance())
        
    async def stop(self):
        """Stop WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("High-volume WebSocket server stopped")
            
    async def handle_client(self, websocket):
        """Handle WebSocket client connections with high throughput."""
        if len(self.clients) >= self.max_connections:
            await websocket.close(code=1013, reason="Server overloaded")
            return
            
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.debug(f"Client {client_id} connected ({len(self.clients)} total)")
        
        try:
            async for message in websocket:
                await self._process_message_high_volume(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
            self.error_count += 1
        finally:
            self.clients.discard(websocket)
            logger.debug(f"Client {client_id} disconnected ({len(self.clients)} total)")
    
    async def _process_message_high_volume(self, websocket, message):
        """Process messages with high-volume optimizations."""
        try:
            # Parse message
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            message_id = data.get("message_id", f"auto-{self.message_counter}")
            
            self.message_counter += 1
            current_time = time.time()
            
            # Check for backpressure conditions
            if self.queue_depth > HIGH_VOLUME_CONFIG["queue_overflow_threshold"]:
                if not self.backpressure_triggered:
                    self.backpressure_triggered = True
                    await self._send_backpressure_signal(websocket, data)
                    return
            else:
                self.backpressure_triggered = False
            
            # Simulate queue processing
            self.queue_depth += 1
            
            # Fast path for high-volume messages
            if message_type == "user_message":
                await self._handle_user_message_optimized(websocket, data, current_time)
            elif message_type == "throughput_test":
                await self._handle_throughput_test(websocket, data, current_time)
            elif message_type == "latency_probe":
                await self._handle_latency_probe(websocket, data, current_time)
            elif message_type == "get_performance_stats":
                await self._send_performance_stats(websocket)
            else:
                # Generic handler for other message types
                await self._handle_generic_message(websocket, data, current_time)
                
            self.queue_depth = max(0, self.queue_depth - 1)
            
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format",
                "timestamp": time.time()
            }))
            self.error_count += 1
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            self.error_count += 1
    
    async def _handle_user_message_optimized(self, websocket, data, current_time):
        """Optimized user message handling for high throughput."""
        message_id = data.get("message_id")
        
        # Idempotency check
        if message_id in self.processed_messages:
            await websocket.send(json.dumps({
                "type": "duplicate_rejected",
                "message_id": message_id,
                "original_timestamp": self.processed_messages[message_id],
                "timestamp": current_time
            }))
            return
        
        # Record processing
        self.processed_messages[message_id] = current_time
        
        # Simulate minimal processing delay
        processing_start = time.perf_counter()
        await asyncio.sleep(0.001)  # 1ms simulated processing
        processing_end = time.perf_counter()
        
        # Send response
        response = {
            "type": "ai_response",
            "message_id": message_id,
            "sequence_id": data.get("sequence_id"),
            "content": f"High-volume response to: {data.get('content', 'unknown')[:50]}...",
            "processing_time": processing_end - processing_start,
            "server_timestamp": current_time,
            "queue_depth": self.queue_depth,
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(response))
    
    async def _handle_throughput_test(self, websocket, data, current_time):
        """Handle throughput test messages with minimal overhead."""
        message_id = data.get("message_id")
        sequence_id = data.get("sequence_id", 0)
        
        # Ultra-fast response for throughput testing
        response = {
            "type": "throughput_response",
            "message_id": message_id,
            "sequence_id": sequence_id,
            "server_time": current_time,
            "queue_depth": self.queue_depth
        }
        
        await websocket.send(json.dumps(response))
    
    async def _handle_latency_probe(self, websocket, data, current_time):
        """Handle latency probe messages with precise timing."""
        message_id = data.get("message_id")
        client_send_time = data.get("send_time", current_time)
        
        # Precise timing response
        response = {
            "type": "latency_response", 
            "message_id": message_id,
            "client_send_time": client_send_time,
            "server_receive_time": current_time,
            "server_send_time": time.time(),
            "queue_depth": self.queue_depth
        }
        
        await websocket.send(json.dumps(response))
    
    async def _handle_generic_message(self, websocket, data, current_time):
        """Generic message handler for compatibility."""
        response = {
            "type": "generic_response",
            "message_id": data.get("message_id"),
            "echo": data,
            "timestamp": current_time
        }
        await websocket.send(json.dumps(response))
    
    async def _send_backpressure_signal(self, websocket, data):
        """Send backpressure signal to client."""
        response = {
            "type": "backpressure",
            "message": "Server queue overflow, please reduce message rate",
            "queue_depth": self.queue_depth,
            "max_queue": HIGH_VOLUME_CONFIG["queue_overflow_threshold"],
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(response))
    
    async def _send_performance_stats(self, websocket):
        """Send current performance statistics."""
        current_memory = psutil.Process().memory_info().rss
        uptime = time.time() - self.start_time
        
        stats = {
            "type": "performance_stats",
            "uptime": uptime,
            "message_count": self.message_counter,
            "connection_count": len(self.clients),
            "queue_depth": self.queue_depth,
            "error_count": self.error_count,
            "memory_usage_mb": current_memory / (1024 * 1024),
            "memory_growth_mb": (current_memory - self.initial_memory) / (1024 * 1024),
            "messages_per_second": self.message_counter / uptime if uptime > 0 else 0,
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(stats))
    
    async def _monitor_performance(self):
        """Background performance monitoring."""
        while self.server:
            try:
                current_memory = psutil.Process().memory_info().rss
                self.peak_memory = max(self.peak_memory, current_memory)
                
                # Record throughput snapshot
                uptime = time.time() - self.start_time
                if uptime > 0:
                    current_throughput = self.message_counter / uptime
                    self.throughput_history.append({
                        "time": time.time(),
                        "throughput": current_throughput,
                        "connections": len(self.clients),
                        "queue_depth": self.queue_depth
                    })
                
                # Cleanup old history (keep last 1000 entries)
                if len(self.throughput_history) > 1000:
                    self.throughput_history = self.throughput_history[-1000:]
                
                await asyncio.sleep(1.0)  # Monitor every second
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                break


class HighVolumeThroughputClient:
    """High-performance WebSocket client for throughput testing."""
    
    def __init__(self, websocket_uri: str, auth_token: str, client_id: str):
        self.websocket_uri = websocket_uri
        self.auth_token = auth_token
        self.client_id = client_id
        self.connection = None
        
        # Performance tracking
        self.sent_messages = []
        self.received_messages = []
        self.latency_measurements = []
        self.error_count = 0
        self.start_time = None
        
    async def connect(self):
        """Establish high-performance WebSocket connection."""
        try:
            # For mock server, don't use auth headers
            if "localhost:8765" in self.websocket_uri:
                self.connection = await websockets.connect(
                    self.websocket_uri,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=2**20,  # 1MB max message size
                    max_queue=1000   # High message queue
                )
            else:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                self.connection = await websockets.connect(
                    self.websocket_uri,
                    extra_headers=headers,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=2**20,
                    max_queue=1000
                )
            
            self.start_time = time.time()
            logger.debug(f"Client {self.client_id} connected to {self.websocket_uri}")
            return self.connection
            
        except Exception as e:
            logger.error(f"Client {self.client_id} connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close WebSocket connection."""
        if self.connection:
            await self.connection.close()
            logger.debug(f"Client {self.client_id} disconnected")
    
    async def send_throughput_burst(self, message_count: int, rate_limit: Optional[float] = None) -> List[Dict]:
        """Send high-throughput message burst."""
        if not self.connection:
            await self.connect()
        
        results = []
        start_time = time.perf_counter()
        
        # Calculate inter-message delay for rate limiting
        delay = (1.0 / rate_limit) if rate_limit else 0.0
        
        for i in range(message_count):
            message = {
                "type": "throughput_test",
                "message_id": f"{self.client_id}-{i}",
                "sequence_id": i,
                "content": f"Throughput test message {i}",
                "client_id": self.client_id,
                "send_time": time.time()
            }
            
            try:
                send_start = time.perf_counter()
                await self.connection.send(json.dumps(message))
                send_duration = time.perf_counter() - send_start
                
                result = {
                    "message": message,
                    "send_time": send_start,
                    "send_duration": send_duration,
                    "status": "sent"
                }
                results.append(result)
                self.sent_messages.append(result)
                
                # Rate limiting
                if delay > 0:
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                result = {
                    "message": message,
                    "error": str(e),
                    "status": "failed"
                }
                results.append(result)
                self.error_count += 1
        
        total_duration = time.perf_counter() - start_time
        actual_rate = message_count / total_duration if total_duration > 0 else 0
        
        logger.info(f"Client {self.client_id}: Sent {message_count} messages in {total_duration:.3f}s "
                   f"({actual_rate:.1f} msg/sec)")
        
        return results
    
    async def send_latency_probes(self, probe_count: int, interval: float = 1.0) -> List[LatencyMeasurement]:
        """Send latency probe messages with precise timing."""
        if not self.connection:
            await self.connect()
        
        measurements = []
        
        for i in range(probe_count):
            send_time = time.perf_counter()
            message = {
                "type": "latency_probe",
                "message_id": f"{self.client_id}-probe-{i}",
                "send_time": send_time,
                "probe_id": i
            }
            
            try:
                await self.connection.send(json.dumps(message))
                
                # Wait for response with timeout
                response = await asyncio.wait_for(
                    self.connection.recv(),
                    timeout=5.0
                )
                
                receive_time = time.perf_counter()
                response_data = json.loads(response)
                
                if response_data.get("type") == "latency_response":
                    measurement = LatencyMeasurement(
                        message_id=message["message_id"],
                        send_time=send_time,
                        receive_time=receive_time,
                        processing_time=response_data.get("server_processing_time", 0),
                        queue_time=response_data.get("queue_time", 0)
                    )
                    measurements.append(measurement)
                    self.latency_measurements.append(measurement)
                
                if interval > 0:
                    await asyncio.sleep(interval)
                    
            except asyncio.TimeoutError:
                logger.warning(f"Client {self.client_id}: Latency probe {i} timeout")
                self.error_count += 1
            except Exception as e:
                logger.error(f"Client {self.client_id}: Latency probe {i} error: {e}")
                self.error_count += 1
        
        return measurements
    
    async def receive_responses(self, expected_count: int, timeout: float = 60.0) -> List[Dict]:
        """Receive responses with high-volume optimizations."""
        responses = []
        start_time = time.time()
        
        try:
            while len(responses) < expected_count and (time.time() - start_time) < timeout:
                try:
                    remaining_time = timeout - (time.time() - start_time)
                    response = await asyncio.wait_for(
                        self.connection.recv(),
                        timeout=min(5.0, remaining_time)
                    )
                    
                    response_data = json.loads(response)
                    response_data["receive_time"] = time.time()
                    responses.append(response_data)
                    self.received_messages.append(response_data)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Client {self.client_id}: Response receive error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Client {self.client_id}: Error in receive_responses: {e}")
        
        logger.debug(f"Client {self.client_id}: Received {len(responses)} responses")
        return responses
    
    async def get_performance_stats(self) -> Dict:
        """Get server performance statistics."""
        if not self.connection:
            return {"error": "Not connected"}
        
        stats_request = {
            "type": "get_performance_stats",
            "timestamp": time.time()
        }
        
        try:
            await self.connection.send(json.dumps(stats_request))
            response = await asyncio.wait_for(self.connection.recv(), timeout=5.0)
            return json.loads(response)
        except Exception as e:
            return {"error": f"Failed to get stats: {e}"}


class ThroughputAnalyzer:
    """Analyzes throughput test results and generates comprehensive metrics."""
    
    @staticmethod
    def analyze_latency_distribution(measurements: List[LatencyMeasurement]) -> Dict[str, float]:
        """Analyze latency measurements and calculate percentiles."""
        if not measurements:
            return {"error": "No latency measurements available"}
        
        latencies = [m.total_latency for m in measurements]
        latencies.sort()
        
        def percentile(data: List[float], p: float) -> float:
            index = int(len(data) * p / 100.0)
            return data[min(index, len(data) - 1)]
        
        return {
            "count": len(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "std_dev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "p50": percentile(latencies, 50),
            "p90": percentile(latencies, 90),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "p999": percentile(latencies, 99.9) if len(latencies) >= 1000 else max(latencies)
        }
    
    @staticmethod
    def calculate_throughput_metrics(sent_count: int, received_count: int, 
                                   duration: float) -> ThroughputMetrics:
        """Calculate comprehensive throughput metrics."""
        send_rate = sent_count / duration if duration > 0 else 0
        receive_rate = received_count / duration if duration > 0 else 0
        delivery_ratio = received_count / sent_count if sent_count > 0 else 0
        error_rate = (sent_count - received_count) / sent_count if sent_count > 0 else 0
        
        # Get current system metrics
        memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        cpu_percent = psutil.cpu_percent()
        
        return ThroughputMetrics(
            messages_sent=sent_count,
            messages_received=received_count,
            messages_failed=sent_count - received_count,
            send_rate=send_rate,
            receive_rate=receive_rate,
            latency_p50=0.0,  # To be filled by caller
            latency_p95=0.0,  # To be filled by caller
            latency_p99=0.0,  # To be filled by caller
            delivery_ratio=delivery_ratio,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage=cpu_percent,
            queue_depth=0,    # To be filled by caller
            backpressure_events=0  # To be filled by caller
        )
    
    @staticmethod
    def validate_message_ordering(responses: List[Dict]) -> Dict[str, Any]:
        """Validate message ordering integrity."""
        validation_result = {
            "total_messages": len(responses),
            "ordering_violations": [],
            "duplicate_sequences": [],
            "missing_sequences": [],
            "out_of_order_count": 0
        }
        
        # Group by client/thread
        by_client = defaultdict(list)
        for response in responses:
            client_id = response.get("client_id", "unknown")
            sequence_id = response.get("sequence_id")
            if sequence_id is not None:
                by_client[client_id].append((sequence_id, response))
        
        # Check ordering within each client
        for client_id, messages in by_client.items():
            messages.sort(key=lambda x: x[0])  # Sort by sequence_id
            expected_sequence = 0
            
            for sequence_id, response in messages:
                if sequence_id != expected_sequence:
                    if sequence_id < expected_sequence:
                        validation_result["out_of_order_count"] += 1
                        validation_result["ordering_violations"].append({
                            "client_id": client_id,
                            "expected": expected_sequence,
                            "received": sequence_id,
                            "type": "out_of_order"
                        })
                    else:
                        # Missing sequences
                        for missing in range(expected_sequence, sequence_id):
                            validation_result["missing_sequences"].append({
                                "client_id": client_id,
                                "sequence_id": missing
                            })
                
                expected_sequence = sequence_id + 1
        
        return validation_result


# Test Fixtures

@pytest.fixture
async def high_volume_server():
    """High-volume WebSocket server fixture."""
    if E2E_TEST_CONFIG["test_mode"] != "mock":
        yield None
        return
        
    server = HighVolumeWebSocketServer()
    await server.start()
    
    # Allow server startup time
    await asyncio.sleep(1.0)
    
    yield server
    await server.stop()


@pytest.fixture
async def test_user_token():
    """Create test user and return auth token."""
    if E2E_TEST_CONFIG["test_mode"] == "real":
        # Use real authentication service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{E2E_TEST_CONFIG['auth_service_url']}/auth/test-user",
                    json={"email": f"throughput-test-{uuid.uuid4().hex[:8]}@example.com"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    token_data = response.json()
                    return {
                        "user_id": token_data["user_id"],
                        "token": token_data["token"],
                        "email": token_data["email"]
                    }
        except Exception as e:
            logger.warning(f"Real auth failed, using mock: {e}")
    
    # Fallback to mock authentication
    test_user_id = f"throughput-user-{uuid.uuid4().hex[:8]}"
    return {
        "user_id": test_user_id,
        "token": f"mock-token-{uuid.uuid4().hex}",
        "email": f"{test_user_id}@example.com"
    }


@pytest.fixture
async def throughput_client(test_user_token, high_volume_server):
    """High-volume throughput client fixture."""
    websocket_uri = E2E_TEST_CONFIG["websocket_url"]
    client = HighVolumeThroughputClient(websocket_uri, test_user_token["token"], "primary-client")
    
    # Establish connection with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await client.connect()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                pytest.skip(f"WebSocket connection failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1.0)
    
    yield client
    
    # Cleanup
    try:
        await client.disconnect()
    except Exception as e:
        logger.warning(f"Client cleanup error: {e}")


# Test Cases Implementation

class TestLinearThroughputScaling:
    """Test Case 1: Linear Throughput Scaling"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)  # 5 minute timeout
    async def test_linear_throughput_scaling(self, throughput_client, high_volume_server):
        """
        Validate system performance scales linearly with increasing message rates.
        Tests scaling from 100 to 10,000 messages/second.
        """
        test_results = LoadTestResults(
            test_name="linear_throughput_scaling",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        scaling_results = {}
        
        # Test each scaling step
        for rate in HIGH_VOLUME_CONFIG["message_rate_scaling_steps"]:
            logger.info(f"Testing throughput at {rate} msg/sec...")
            
            # Send messages at target rate for 30 seconds
            message_count = rate * 30  # 30 seconds worth
            
            start_time = time.perf_counter()
            results = await throughput_client.send_throughput_burst(
                message_count=message_count,
                rate_limit=rate
            )
            send_duration = time.perf_counter() - start_time
            
            # Collect responses
            responses = await throughput_client.receive_responses(
                expected_count=message_count,
                timeout=60.0
            )
            
            # Calculate metrics
            sent_count = len([r for r in results if r["status"] == "sent"])
            received_count = len(responses)
            actual_send_rate = sent_count / send_duration if send_duration > 0 else 0
            
            metrics = ThroughputAnalyzer.calculate_throughput_metrics(
                sent_count, received_count, send_duration
            )
            
            scaling_results[rate] = {
                "target_rate": rate,
                "actual_send_rate": actual_send_rate,
                "delivery_ratio": metrics.delivery_ratio,
                "memory_usage_mb": metrics.memory_usage_mb,
                "cpu_usage": metrics.cpu_usage,
                "sent_count": sent_count,
                "received_count": received_count
            }
            
            test_results.rate_scaling_data[rate] = metrics
            
            # Performance assertions for each scaling step
            assert actual_send_rate >= rate * 0.9, \
                f"Send rate too low at {rate} msg/sec: {actual_send_rate:.1f}"
            
            assert metrics.delivery_ratio >= 0.95, \
                f"Delivery ratio too low at {rate} msg/sec: {metrics.delivery_ratio:.3f}"
            
            # Allow system to stabilize between tests
            await asyncio.sleep(2.0)
        
        # Analysis of scaling characteristics
        rates = list(scaling_results.keys())
        actual_rates = [scaling_results[r]["actual_send_rate"] for r in rates]
        delivery_ratios = [scaling_results[r]["delivery_ratio"] for r in rates]
        
        # Validate linear scaling (up to system limits)
        linear_threshold = 5000  # Expected linear scaling up to 5000 msg/sec
        linear_rates = [r for r in rates if r <= linear_threshold]
        linear_actual = [scaling_results[r]["actual_send_rate"] for r in linear_rates]
        
        if len(linear_rates) >= 3:
            # Check if scaling is approximately linear
            correlation = statistics.correlation(linear_rates, linear_actual)
            assert correlation >= 0.95, \
                f"Linear scaling correlation too low: {correlation:.3f}"
        
        # Validate graceful degradation beyond limits
        high_load_rates = [r for r in rates if r > linear_threshold]
        if high_load_rates:
            for rate in high_load_rates:
                delivery_ratio = scaling_results[rate]["delivery_ratio"]
                # Should still maintain reasonable delivery ratio
                assert delivery_ratio >= 0.8, \
                    f"Delivery ratio degraded too much at {rate} msg/sec: {delivery_ratio:.3f}"
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        test_results.peak_throughput = max(actual_rates)
        test_results.sustained_throughput = max([
            r for i, r in enumerate(actual_rates) 
            if rates[i] <= linear_threshold
        ]) if linear_rates else 0
        
        logger.info(f"Linear scaling test completed: Peak throughput {test_results.peak_throughput:.1f} msg/sec")


class TestMessageOrderingPreservation:
    """Test Case 2: Message Ordering Preservation Under Flood"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(180)  # 3 minute timeout
    async def test_message_ordering_preservation_flood(self, throughput_client, high_volume_server):
        """
        Ensure strict message ordering is maintained during high-volume bursts.
        Tests with 10,000 numbered messages sent at maximum rate.
        """
        test_results = LoadTestResults(
            test_name="message_ordering_preservation",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        # Single connection flood test
        message_count = 10000
        
        logger.info(f"Flooding server with {message_count} ordered messages...")
        
        # Generate sequentially numbered messages
        start_time = time.perf_counter()
        results = await throughput_client.send_throughput_burst(
            message_count=message_count,
            rate_limit=1000  # 1000 msg/sec rate
        )
        send_duration = time.perf_counter() - start_time
        
        # Collect responses
        responses = await throughput_client.receive_responses(
            expected_count=message_count,
            timeout=120.0
        )
        
        # Validate ordering
        ordering_validation = ThroughputAnalyzer.validate_message_ordering(responses)
        
        # Test with multiple concurrent connections
        logger.info("Testing ordering with concurrent connections...")
        
        concurrent_clients = []
        concurrent_tasks = []
        
        try:
            # Create 10 concurrent clients
            for i in range(10):
                client = HighVolumeThroughputClient(
                    E2E_TEST_CONFIG["websocket_url"],
                    "mock-token",
                    f"concurrent-client-{i}"
                )
                await client.connect()
                concurrent_clients.append(client)
                
                # Each client sends 1000 messages
                task = asyncio.create_task(
                    client.send_throughput_burst(1000, rate_limit=100)
                )
                concurrent_tasks.append(task)
            
            # Wait for all clients to finish sending
            concurrent_results = await asyncio.gather(*concurrent_tasks)
            
            # Collect responses from all clients
            all_concurrent_responses = []
            for client in concurrent_clients:
                client_responses = await client.receive_responses(1000, timeout=60.0)
                all_concurrent_responses.extend(client_responses)
            
            # Validate ordering for concurrent test
            concurrent_ordering = ThroughputAnalyzer.validate_message_ordering(all_concurrent_responses)
            
        finally:
            # Clean up concurrent clients
            for client in concurrent_clients:
                try:
                    await client.disconnect()
                except:
                    pass
        
        # Assertions
        
        # Single connection ordering
        assert len(ordering_validation["ordering_violations"]) == 0, \
            f"Ordering violations in single connection: {ordering_validation['ordering_violations']}"
        
        assert len(ordering_validation["missing_sequences"]) == 0, \
            f"Missing sequences: {ordering_validation['missing_sequences']}"
        
        assert ordering_validation["out_of_order_count"] == 0, \
            f"Out of order messages: {ordering_validation['out_of_order_count']}"
        
        # Concurrent connection ordering
        assert len(concurrent_ordering["ordering_violations"]) == 0, \
            f"Concurrent ordering violations: {concurrent_ordering['ordering_violations']}"
        
        # Delivery ratio validation
        delivery_ratio = len(responses) / message_count
        assert delivery_ratio >= 0.99, \
            f"Delivery ratio too low: {delivery_ratio:.3f}"
        
        concurrent_delivery_ratio = len(all_concurrent_responses) / (10 * 1000)
        assert concurrent_delivery_ratio >= 0.95, \
            f"Concurrent delivery ratio too low: {concurrent_delivery_ratio:.3f}"
        
        test_results.messages_sent = message_count + 10000  # Single + concurrent
        test_results.messages_received = len(responses) + len(all_concurrent_responses)
        test_results.ordering_violations = (
            len(ordering_validation["ordering_violations"]) +
            len(concurrent_ordering["ordering_violations"])
        )
        test_results.delivery_ratio = test_results.messages_received / test_results.messages_sent
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Message ordering test completed: {test_results.ordering_violations} violations, "
                   f"{test_results.delivery_ratio:.3f} delivery ratio")


class TestDeliveryGuaranteeValidation:
    """Test Case 3: Delivery Guarantee Validation"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(240)  # 4 minute timeout
    async def test_delivery_guarantee_validation(self, throughput_client, high_volume_server):
        """
        Validate at-least-once delivery guarantees under network stress.
        Tests with network failures, connection drops, and retry mechanisms.
        """
        test_results = LoadTestResults(
            test_name="delivery_guarantee_validation",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        message_count = 5000
        expected_duplicates = 0
        recovery_events = 0
        
        logger.info(f"Testing delivery guarantees with {message_count} messages under network stress...")
        
        # Phase 1: Normal delivery baseline
        baseline_results = await throughput_client.send_throughput_burst(
            message_count=1000,
            rate_limit=500
        )
        baseline_responses = await throughput_client.receive_responses(1000, timeout=30.0)
        baseline_delivery_ratio = len(baseline_responses) / 1000
        
        # Phase 2: Delivery with artificial connection instability
        stress_clients = []
        stress_tasks = []
        all_stress_responses = []
        
        try:
            # Create 5 clients that will experience "network issues"
            for i in range(5):
                client = HighVolumeThroughputClient(
                    E2E_TEST_CONFIG["websocket_url"],
                    "mock-token",
                    f"stress-client-{i}"
                )
                await client.connect()
                stress_clients.append(client)
            
            # Send messages with simulated connection drops
            for i, client in enumerate(stress_clients):
                async def send_with_drops(client, client_id):
                    messages_sent = 0
                    messages_to_send = 1000
                    reconnect_count = 0
                    
                    while messages_sent < messages_to_send:
                        try:
                            # Send a batch of messages
                            batch_size = min(100, messages_to_send - messages_sent)
                            batch_results = await client.send_throughput_burst(
                                message_count=batch_size,
                                rate_limit=200
                            )
                            messages_sent += batch_size
                            
                            # Simulate connection drop (10% chance)
                            if random.random() < 0.1:
                                logger.debug(f"Simulating connection drop for client {client_id}")
                                await client.disconnect()
                                await asyncio.sleep(1.0)  # Network outage duration
                                await client.connect()
                                reconnect_count += 1
                                recovery_events += 1
                            
                        except Exception as e:
                            logger.warning(f"Client {client_id} error: {e}")
                            try:
                                await client.connect()
                                reconnect_count += 1
                            except:
                                break
                    
                    return {"client_id": client_id, "sent": messages_sent, "reconnects": reconnect_count}
                
                task = asyncio.create_task(send_with_drops(client, f"stress-{i}"))
                stress_tasks.append(task)
            
            # Wait for all stress clients to complete
            stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            # Collect responses from stress test
            for client in stress_clients:
                try:
                    client_responses = await client.receive_responses(1000, timeout=60.0)
                    all_stress_responses.extend(client_responses)
                except Exception as e:
                    logger.warning(f"Error collecting stress responses: {e}")
            
        finally:
            # Clean up stress clients
            for client in stress_clients:
                try:
                    await client.disconnect()
                except:
                    pass
        
        # Phase 3: Test duplicate detection and idempotency
        logger.info("Testing duplicate detection...")
        
        duplicate_test_message = {
            "type": "user_message",
            "message_id": f"duplicate-test-{uuid.uuid4().hex}",
            "content": "Duplicate detection test message",
            "send_time": time.time()
        }
        
        # Send the same message 5 times
        duplicate_responses = []
        for i in range(5):
            try:
                await throughput_client.connection.send(json.dumps(duplicate_test_message))
                response = await asyncio.wait_for(
                    throughput_client.connection.recv(),
                    timeout=5.0
                )
                duplicate_responses.append(json.loads(response))
            except Exception as e:
                logger.warning(f"Duplicate test error: {e}")
        
        # Analysis
        total_sent = 1000 + sum([
            r["sent"] if isinstance(r, dict) else 0 
            for r in stress_results
        ])
        total_received = len(baseline_responses) + len(all_stress_responses)
        
        # Count duplicate rejections in duplicate test
        duplicate_rejections = len([
            r for r in duplicate_responses 
            if r.get("type") == "duplicate_rejected"
        ])
        
        # Assertions
        
        # Baseline delivery should be near perfect
        assert baseline_delivery_ratio >= 0.99, \
            f"Baseline delivery ratio too low: {baseline_delivery_ratio:.3f}"
        
        # Stress test should maintain reasonable delivery despite network issues
        stress_delivery_ratio = len(all_stress_responses) / (5 * 1000) if all_stress_responses else 0
        assert stress_delivery_ratio >= 0.9, \
            f"Stress delivery ratio too low: {stress_delivery_ratio:.3f}"
        
        # Recovery events should be detected
        assert recovery_events > 0, "No recovery events detected during stress test"
        
        # Duplicate detection should work
        assert duplicate_rejections >= 3, \
            f"Insufficient duplicate rejections: {duplicate_rejections}"
        
        # No silent message loss
        overall_delivery_ratio = total_received / total_sent if total_sent > 0 else 0
        assert overall_delivery_ratio >= HIGH_VOLUME_CONFIG["min_delivery_ratio"], \
            f"Overall delivery ratio below threshold: {overall_delivery_ratio:.3f}"
        
        test_results.messages_sent = total_sent
        test_results.messages_received = total_received
        test_results.delivery_ratio = overall_delivery_ratio
        test_results.recovery_count = recovery_events
        test_results.duplicate_count = duplicate_rejections
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Delivery guarantee test completed: {overall_delivery_ratio:.3f} delivery ratio, "
                   f"{recovery_events} recoveries, {duplicate_rejections} duplicate rejections")


class TestBackpressureMechanismTesting:
    """Test Case 4: Backpressure Mechanism Testing"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(180)  # 3 minute timeout  
    async def test_backpressure_mechanism_testing(self, throughput_client, high_volume_server):
        """
        Validate queue overflow protection and backpressure signaling.
        Tests overwhelming system with messages beyond processing capacity.
        """
        test_results = LoadTestResults(
            test_name="backpressure_mechanism_testing",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        logger.info("Testing backpressure mechanisms with queue overflow...")
        
        # Phase 1: Establish baseline performance
        baseline_count = 1000
        baseline_results = await throughput_client.send_throughput_burst(
            message_count=baseline_count,
            rate_limit=500  # Moderate rate
        )
        baseline_responses = await throughput_client.receive_responses(baseline_count, timeout=30.0)
        baseline_rate = len(baseline_responses) / 30.0  # responses per second
        
        # Phase 2: Overwhelm system to trigger backpressure
        overflow_count = 15000  # Much more than queue can handle
        backpressure_signals = []
        queue_full_responses = []
        
        logger.info(f"Sending {overflow_count} messages to trigger backpressure...")
        
        # Send messages as fast as possible to trigger overflow
        start_time = time.perf_counter()
        overflow_results = await throughput_client.send_throughput_burst(
            message_count=overflow_count,
            rate_limit=None  # No rate limiting - send as fast as possible
        )
        send_duration = time.perf_counter() - start_time
        
        # Monitor for backpressure signals
        backpressure_start = time.time()
        overflow_responses = []
        
        while time.time() - backpressure_start < 60.0:  # Monitor for 60 seconds
            try:
                response = await asyncio.wait_for(
                    throughput_client.connection.recv(),
                    timeout=1.0
                )
                response_data = json.loads(response)
                overflow_responses.append(response_data)
                
                # Check for backpressure signals
                if response_data.get("type") == "backpressure":
                    backpressure_signals.append(response_data)
                elif response_data.get("type") == "queue_full":
                    queue_full_responses.append(response_data)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Error monitoring backpressure: {e}")
                break
        
        # Phase 3: Test priority message preservation during overflow
        priority_messages = []
        priority_responses = []
        
        logger.info("Testing priority message preservation during overflow...")
        
        for i in range(10):
            priority_message = {
                "type": "user_message",
                "message_id": f"priority-{i}",
                "content": f"High priority message {i}",
                "priority": "high",
                "timestamp": time.time()
            }
            
            try:
                await throughput_client.connection.send(json.dumps(priority_message))
                priority_messages.append(priority_message)
                
                # Try to get immediate response
                response = await asyncio.wait_for(
                    throughput_client.connection.recv(),
                    timeout=5.0
                )
                priority_responses.append(json.loads(response))
                
            except Exception as e:
                logger.warning(f"Priority message {i} error: {e}")
        
        # Phase 4: Test queue recovery
        logger.info("Testing queue recovery after load reduction...")
        
        # Wait for queue to drain
        recovery_start = time.time()
        queue_recovered = False
        
        while time.time() - recovery_start < HIGH_VOLUME_CONFIG["queue_recovery_timeout"]:
            # Get server stats to check queue depth
            stats = await throughput_client.get_performance_stats()
            if isinstance(stats, dict) and stats.get("queue_depth", float('inf')) < 100:
                queue_recovered = True
                break
            await asyncio.sleep(1.0)
        
        # Test normal operation after recovery
        if queue_recovered:
            post_recovery_results = await throughput_client.send_throughput_burst(
                message_count=500,
                rate_limit=300
            )
            post_recovery_responses = await throughput_client.receive_responses(500, timeout=20.0)
            post_recovery_rate = len(post_recovery_responses) / 20.0
        else:
            post_recovery_rate = 0
        
        # Analysis and Assertions
        
        # Should have triggered backpressure
        assert len(backpressure_signals) > 0 or len(queue_full_responses) > 0, \
            "No backpressure signals detected despite queue overflow"
        
        # Backpressure should trigger quickly
        if backpressure_signals:
            first_backpressure_time = min(s.get("timestamp", float('inf')) for s in backpressure_signals)
            backpressure_delay = first_backpressure_time - (start_time + time.time() - time.perf_counter())
            assert backpressure_delay < 5.0, \
                f"Backpressure triggered too late: {backpressure_delay:.2f}s"
        
        # System should handle overflow gracefully
        total_responses_during_overflow = len(overflow_responses)
        assert total_responses_during_overflow > 0, \
            "No responses received during overflow test"
        
        # Priority messages should be preserved
        priority_preservation_ratio = len(priority_responses) / len(priority_messages) if priority_messages else 0
        assert priority_preservation_ratio >= 0.8, \
            f"Priority preservation too low: {priority_preservation_ratio:.2f}"
        
        # Queue should recover
        assert queue_recovered, \
            f"Queue did not recover within {HIGH_VOLUME_CONFIG['queue_recovery_timeout']} seconds"
        
        # Performance should return to baseline after recovery
        if post_recovery_rate > 0:
            recovery_ratio = post_recovery_rate / baseline_rate if baseline_rate > 0 else 0
            assert recovery_ratio >= 0.8, \
                f"Performance did not recover adequately: {recovery_ratio:.2f}"
        
        test_results.messages_sent = baseline_count + overflow_count + len(priority_messages) + 500
        test_results.messages_received = (
            len(baseline_responses) + total_responses_during_overflow + 
            len(priority_responses) + (len(post_recovery_responses) if 'post_recovery_responses' in locals() else 0)
        )
        test_results.backpressure_events = len(backpressure_signals) + len(queue_full_responses)
        test_results.queue_overflow_events = len(queue_full_responses)
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Backpressure test completed: {test_results.backpressure_events} backpressure events, "
                   f"queue recovered: {queue_recovered}")


class TestLatencyPercentileDistribution:
    """Test Case 5: Latency Percentile Distribution Analysis"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(420)  # 7 minute timeout (5 min test + overhead)
    async def test_latency_percentile_distribution(self, throughput_client, high_volume_server):
        """
        Measure detailed latency characteristics under sustained high load.
        Tests with 5000 msg/sec sustained rate for 5 minutes.
        """
        test_results = LoadTestResults(
            test_name="latency_percentile_distribution",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        target_rate = 5000  # messages per second
        test_duration = 300  # 5 minutes
        total_messages = target_rate * test_duration
        
        logger.info(f"Starting sustained latency test: {target_rate} msg/sec for {test_duration} seconds...")
        
        # Start memory tracking
        tracemalloc.start()
        initial_memory = psutil.Process().memory_info().rss
        
        # Phase 1: Establish baseline latency
        baseline_measurements = await throughput_client.send_latency_probes(
            probe_count=100,
            interval=0.1  # Every 100ms
        )
        
        baseline_latency = ThroughputAnalyzer.analyze_latency_distribution(baseline_measurements)
        
        # Phase 2: Sustained high-load latency testing
        latency_measurements = []
        throughput_samples = []
        
        # Send messages in chunks to maintain rate and collect latency data
        chunk_size = 1000
        chunk_duration = chunk_size / target_rate  # Time per chunk
        chunks_to_send = total_messages // chunk_size
        
        sustained_start = time.perf_counter()
        
        for chunk_i in range(chunks_to_send):
            chunk_start = time.perf_counter()
            
            # Send chunk of messages
            chunk_results = await throughput_client.send_throughput_burst(
                message_count=chunk_size,
                rate_limit=target_rate
            )
            
            # Collect chunk responses
            chunk_responses = await throughput_client.receive_responses(
                expected_count=chunk_size,
                timeout=chunk_duration + 5.0
            )
            
            chunk_end = time.perf_counter()
            chunk_actual_duration = chunk_end - chunk_start
            
            # Calculate latencies for this chunk
            for response in chunk_responses:
                message_id = response.get("message_id", "")
                if message_id.startswith(throughput_client.client_id):
                    # Find corresponding sent message
                    send_time = response.get("server_timestamp", chunk_start)
                    receive_time = response.get("receive_time", chunk_end)
                    
                    if receive_time > send_time:
                        measurement = LatencyMeasurement(
                            message_id=message_id,
                            send_time=send_time,
                            receive_time=receive_time,
                            processing_time=response.get("processing_time", 0)
                        )
                        latency_measurements.append(measurement)
            
            # Record throughput sample
            chunk_throughput = len(chunk_responses) / chunk_actual_duration if chunk_actual_duration > 0 else 0
            throughput_samples.append({
                "time": chunk_end,
                "throughput": chunk_throughput,
                "sent": len(chunk_results),
                "received": len(chunk_responses),
                "target_rate": target_rate
            })
            
            # Monitor every 30 seconds
            if chunk_i % 30 == 0:
                elapsed = time.perf_counter() - sustained_start
                logger.info(f"Sustained test progress: {elapsed:.1f}s / {test_duration}s, "
                           f"avg throughput: {chunk_throughput:.1f} msg/sec")
            
            # Rate control - wait for next chunk time
            target_chunk_end = sustained_start + (chunk_i + 1) * chunk_duration
            current_time = time.perf_counter()
            if current_time < target_chunk_end:
                await asyncio.sleep(target_chunk_end - current_time)
        
        sustained_end = time.perf_counter()
        actual_test_duration = sustained_end - sustained_start
        
        # Phase 3: Final latency analysis
        logger.info("Analyzing latency distribution...")
        
        # Get final memory usage
        final_memory = psutil.Process().memory_info().rss
        memory_growth = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Analyze latency distribution
        if latency_measurements:
            latency_analysis = ThroughputAnalyzer.analyze_latency_distribution(latency_measurements)
            
            # Time-series analysis - check for latency degradation over time
            time_buckets = 10  # Divide test into 10 buckets
            bucket_duration = actual_test_duration / time_buckets
            bucket_latencies = [[] for _ in range(time_buckets)]
            
            for measurement in latency_measurements:
                bucket_index = min(
                    int((measurement.receive_time - sustained_start) / bucket_duration),
                    time_buckets - 1
                )
                bucket_latencies[bucket_index].append(measurement.total_latency)
            
            # Calculate latency trend
            bucket_p95s = []
            for bucket in bucket_latencies:
                if bucket:
                    bucket.sort()
                    p95_index = int(len(bucket) * 0.95)
                    bucket_p95s.append(bucket[p95_index])
            
            # Check for latency degradation
            if len(bucket_p95s) >= 5:
                first_half = bucket_p95s[:len(bucket_p95s)//2]
                second_half = bucket_p95s[len(bucket_p95s)//2:]
                first_avg = statistics.mean(first_half)
                second_avg = statistics.mean(second_half)
                latency_degradation = (second_avg - first_avg) / first_avg if first_avg > 0 else 0
            else:
                latency_degradation = 0
        else:
            latency_analysis = {"error": "No latency measurements collected"}
            latency_degradation = float('inf')
        
        # Calculate overall throughput metrics
        total_sent = sum(sample["sent"] for sample in throughput_samples)
        total_received = sum(sample["received"] for sample in throughput_samples)
        average_throughput = total_received / actual_test_duration if actual_test_duration > 0 else 0
        
        # Assertions
        
        # Sustained throughput should meet target
        throughput_ratio = average_throughput / target_rate
        assert throughput_ratio >= 0.9, \
            f"Sustained throughput too low: {average_throughput:.1f} msg/sec (target: {target_rate})"
        
        # Latency requirements
        if "p50" in latency_analysis:
            assert latency_analysis["p50"] <= HIGH_VOLUME_CONFIG["latency_p50_target"], \
                f"P50 latency too high: {latency_analysis['p50']:.3f}s"
            
            assert latency_analysis["p95"] <= HIGH_VOLUME_CONFIG["latency_p95_target"], \
                f"P95 latency too high: {latency_analysis['p95']:.3f}s"
            
            assert latency_analysis["p99"] <= HIGH_VOLUME_CONFIG["latency_p99_target"], \
                f"P99 latency too high: {latency_analysis['p99']:.3f}s"
        
        # Memory growth should be bounded
        assert memory_growth <= HIGH_VOLUME_CONFIG["max_memory_growth_mb"], \
            f"Memory growth too high: {memory_growth:.1f}MB"
        
        # Latency should not degrade significantly over time
        assert latency_degradation <= 0.2, \
            f"Latency degraded too much over time: {latency_degradation:.2%}"
        
        # Latency variance should be reasonable
        if "std_dev" in latency_analysis and "mean" in latency_analysis:
            if latency_analysis["mean"] > 0:
                variance_coefficient = latency_analysis["std_dev"] / latency_analysis["mean"]
                assert variance_coefficient <= 0.5, \
                    f"Latency variance too high: {variance_coefficient:.3f}"
        
        # Update test results
        test_results.latency_measurements = latency_measurements
        if "p50" in latency_analysis:
            test_results.latency_p50 = latency_analysis["p50"]
            test_results.latency_p95 = latency_analysis["p95"]
            test_results.latency_p99 = latency_analysis["p99"]
            test_results.latency_p999 = latency_analysis.get("p999", latency_analysis["p99"])
        
        test_results.messages_sent = total_sent
        test_results.messages_received = total_received
        test_results.sustained_throughput = average_throughput
        test_results.memory_growth_mb = memory_growth
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Latency distribution test completed: "
                   f"P50={latency_analysis.get('p50', 0):.3f}s, "
                   f"P95={latency_analysis.get('p95', 0):.3f}s, "
                   f"P99={latency_analysis.get('p99', 0):.3f}s, "
                   f"throughput={average_throughput:.1f} msg/sec")


class TestConcurrentConnectionScalability:
    """Test Case 6: Concurrent Connection Scalability"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(480)  # 8 minute timeout
    async def test_concurrent_connection_scalability(self, test_user_token, high_volume_server):
        """
        Validate system performance with hundreds of concurrent connections.
        Tests scaling from 1 to 500 concurrent WebSocket connections.
        """
        test_results = LoadTestResults(
            test_name="concurrent_connection_scalability",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        connection_scaling_results = {}
        
        # Test each connection scaling step
        for conn_count in HIGH_VOLUME_CONFIG["connection_scaling_steps"]:
            if conn_count > 250:  # Limit for test environment
                logger.info(f"Skipping {conn_count} connections (exceeds test environment limits)")
                continue
                
            logger.info(f"Testing with {conn_count} concurrent connections...")
            
            clients = []
            connection_tasks = []
            
            try:
                # Create concurrent clients
                for i in range(conn_count):
                    client = HighVolumeThroughputClient(
                        E2E_TEST_CONFIG["websocket_url"],
                        test_user_token["token"],
                        f"scale-client-{i}"
                    )
                    clients.append(client)
                    
                    # Connect asynchronously
                    task = asyncio.create_task(client.connect())
                    connection_tasks.append(task)
                
                # Wait for all connections to establish
                await asyncio.gather(*connection_tasks, return_exceptions=True)
                
                # Count successful connections
                connected_clients = [c for c in clients if c.connection and not c.connection.closed]
                actual_connections = len(connected_clients)
                
                logger.info(f"Established {actual_connections}/{conn_count} connections")
                
                # Each client sends messages at 100 msg/sec
                messages_per_client = 100
                test_duration = 30  # 30 seconds
                target_rate_per_client = messages_per_client / test_duration
                
                # Start coordinated message sending
                send_tasks = []
                for client in connected_clients:
                    task = asyncio.create_task(
                        client.send_throughput_burst(
                            message_count=messages_per_client,
                            rate_limit=target_rate_per_client
                        )
                    )
                    send_tasks.append(task)
                
                # Wait for all sending to complete
                send_start = time.perf_counter()
                send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
                send_duration = time.perf_counter() - send_start
                
                # Collect responses from all clients
                receive_tasks = []
                for client in connected_clients:
                    task = asyncio.create_task(
                        client.receive_responses(messages_per_client, timeout=45.0)
                    )
                    receive_tasks.append(task)
                
                receive_results = await asyncio.gather(*receive_tasks, return_exceptions=True)
                
                # Analyze results
                total_sent = 0
                total_received = 0
                successful_sends = 0
                
                for i, (send_result, receive_result) in enumerate(zip(send_results, receive_results)):
                    if isinstance(send_result, list):
                        client_sent = len([r for r in send_result if r.get("status") == "sent"])
                        total_sent += client_sent
                        successful_sends += 1 if client_sent > 0 else 0
                    
                    if isinstance(receive_result, list):
                        total_received += len(receive_result)
                
                # Calculate per-connection metrics
                avg_latency_per_connection = 0
                if connected_clients:
                    total_latency = 0
                    latency_count = 0
                    
                    for client in connected_clients:
                        if client.latency_measurements:
                            client_latencies = [m.total_latency for m in client.latency_measurements]
                            total_latency += sum(client_latencies)
                            latency_count += len(client_latencies)
                    
                    avg_latency_per_connection = total_latency / latency_count if latency_count > 0 else 0
                
                # Resource usage
                memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
                cpu_percent = psutil.cpu_percent(interval=1.0)
                
                # Store results
                metrics = ThroughputMetrics(
                    messages_sent=total_sent,
                    messages_received=total_received,
                    messages_failed=total_sent - total_received,
                    send_rate=total_sent / send_duration if send_duration > 0 else 0,
                    receive_rate=total_received / send_duration if send_duration > 0 else 0,
                    latency_p50=avg_latency_per_connection,
                    latency_p95=avg_latency_per_connection * 1.5,  # Estimate
                    latency_p99=avg_latency_per_connection * 2.0,  # Estimate
                    delivery_ratio=total_received / total_sent if total_sent > 0 else 0,
                    error_rate=(total_sent - total_received) / total_sent if total_sent > 0 else 0,
                    memory_usage_mb=memory_mb,
                    cpu_usage=cpu_percent,
                    queue_depth=0,
                    backpressure_events=0
                )
                
                connection_scaling_results[conn_count] = {
                    "target_connections": conn_count,
                    "actual_connections": actual_connections,
                    "connection_success_rate": actual_connections / conn_count,
                    "metrics": metrics,
                    "per_connection_throughput": total_received / actual_connections if actual_connections > 0 else 0,
                    "per_connection_latency": avg_latency_per_connection
                }
                
                test_results.connection_scaling_data[conn_count] = metrics
                
                # Assertions for this scaling step
                connection_success_rate = actual_connections / conn_count
                assert connection_success_rate >= 0.95, \
                    f"Connection success rate too low at {conn_count} connections: {connection_success_rate:.2%}"
                
                delivery_ratio = metrics.delivery_ratio
                assert delivery_ratio >= 0.9, \
                    f"Delivery ratio too low at {conn_count} connections: {delivery_ratio:.3f}"
                
                per_conn_latency = avg_latency_per_connection
                if per_conn_latency > 0:
                    assert per_conn_latency <= 0.2, \
                        f"Per-connection latency too high at {conn_count} connections: {per_conn_latency:.3f}s"
                
                logger.info(f"Connection scaling {conn_count}: {actual_connections} connected, "
                           f"{delivery_ratio:.3f} delivery ratio, {per_conn_latency:.3f}s latency")
            
            finally:
                # Clean up all clients
                cleanup_tasks = []
                for client in clients:
                    try:
                        task = asyncio.create_task(client.disconnect())
                        cleanup_tasks.append(task)
                    except:
                        pass
                
                if cleanup_tasks:
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
                # Allow system to stabilize
                await asyncio.sleep(2.0)
        
        # Overall scaling analysis
        if len(connection_scaling_results) >= 3:
            connection_counts = list(connection_scaling_results.keys())
            throughputs = [connection_scaling_results[c]["metrics"].receive_rate for c in connection_counts]
            
            # Check for linear scaling (should scale approximately linearly with connections)
            if len(connection_counts) >= 3:
                # Calculate correlation between connection count and total throughput
                correlation = statistics.correlation(connection_counts, throughputs)
                assert correlation >= 0.8, \
                    f"Connection scaling correlation too low: {correlation:.3f}"
            
            # Check resource efficiency
            max_connections = max(connection_counts)
            max_memory = connection_scaling_results[max_connections]["metrics"].memory_usage_mb
            memory_per_connection = max_memory / max_connections
            assert memory_per_connection <= 2.0, \
                f"Memory per connection too high: {memory_per_connection:.1f}MB"
        
        test_results.connection_count = max(connection_scaling_results.keys()) if connection_scaling_results else 0
        test_results.peak_memory_mb = max([
            r["metrics"].memory_usage_mb for r in connection_scaling_results.values()
        ]) if connection_scaling_results else 0
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Connection scalability test completed: max {test_results.connection_count} connections, "
                   f"peak memory {test_results.peak_memory_mb:.1f}MB")


class TestMemoryEfficiencyUnderLoad:
    """Test Case 7: Memory Efficiency Under Load"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(720)  # 12 minute timeout (10 min test + overhead)
    async def test_memory_efficiency_under_load(self, throughput_client, high_volume_server):
        """
        Validate memory usage patterns and prevent memory leaks during high throughput.
        Tests with 10,000 msg/sec for 10 minutes and monitors memory efficiency.
        """
        test_results = LoadTestResults(
            test_name="memory_efficiency_under_load",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        target_rate = 10000  # messages per second
        test_duration = 600   # 10 minutes
        monitoring_interval = 10  # Monitor every 10 seconds
        
        logger.info(f"Starting memory efficiency test: {target_rate} msg/sec for {test_duration} seconds...")
        
        # Start memory tracking
        tracemalloc.start()
        gc.collect()  # Force garbage collection before starting
        
        # Baseline memory measurement
        baseline_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        logger.info(f"Baseline memory usage: {baseline_memory:.1f}MB")
        
        # Memory monitoring data
        memory_samples = []
        gc_stats = []
        
        # Start background memory monitoring
        async def monitor_memory():
            """Background memory monitoring task."""
            while True:
                try:
                    memory_info = psutil.Process().memory_info()
                    memory_sample = {
                        "timestamp": time.time(),
                        "rss_mb": memory_info.rss / (1024 * 1024),
                        "vms_mb": memory_info.vms / (1024 * 1024),
                        "gc_counts": gc.get_count(),
                        "gc_stats": gc.get_stats() if hasattr(gc, 'get_stats') else []
                    }
                    memory_samples.append(memory_sample)
                    
                    # Force garbage collection every 60 seconds
                    if len(memory_samples) % 6 == 0:  # Every 6th sample (60 seconds)
                        collected = gc.collect()
                        gc_stats.append({
                            "timestamp": time.time(),
                            "collected": collected,
                            "memory_after_gc": psutil.Process().memory_info().rss / (1024 * 1024)
                        })
                    
                    await asyncio.sleep(monitoring_interval)
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    break
        
        monitoring_task = asyncio.create_task(monitor_memory())
        
        try:
            # Phase 1: High-volume message sending
            messages_sent = 0
            messages_received = 0
            start_time = time.perf_counter()
            
            # Send messages in batches to maintain rate
            batch_size = 1000
            batch_interval = batch_size / target_rate  # Time per batch
            batches_to_send = (target_rate * test_duration) // batch_size
            
            logger.info(f"Sending {batches_to_send} batches of {batch_size} messages each...")
            
            for batch_i in range(batches_to_send):
                batch_start = time.perf_counter()
                
                # Send batch
                batch_results = await throughput_client.send_throughput_burst(
                    message_count=batch_size,
                    rate_limit=target_rate
                )
                
                # Count successful sends
                batch_sent = len([r for r in batch_results if r.get("status") == "sent"])
                messages_sent += batch_sent
                
                # Collect responses (non-blocking)
                try:
                    batch_responses = await asyncio.wait_for(
                        throughput_client.receive_responses(batch_size, timeout=batch_interval + 2.0),
                        timeout=batch_interval + 5.0
                    )
                    messages_received += len(batch_responses)
                except asyncio.TimeoutError:
                    # Continue even if some responses are slow
                    pass
                
                # Log progress every 60 batches
                if batch_i % 60 == 0:
                    elapsed = time.perf_counter() - start_time
                    current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
                    logger.info(f"Progress: {elapsed:.1f}s, sent: {messages_sent}, "
                               f"received: {messages_received}, memory: {current_memory:.1f}MB")
                
                # Rate control
                target_batch_end = start_time + (batch_i + 1) * batch_interval
                current_time = time.perf_counter()
                if current_time < target_batch_end:
                    await asyncio.sleep(target_batch_end - current_time)
            
            actual_duration = time.perf_counter() - start_time
            logger.info(f"Message sending completed in {actual_duration:.1f}s")
            
            # Phase 2: Continue monitoring for additional period to observe memory behavior
            logger.info("Monitoring memory behavior post-load...")
            post_load_start = time.time()
            
            # Collect any remaining responses
            try:
                remaining_responses = await asyncio.wait_for(
                    throughput_client.receive_responses(messages_sent - messages_received, timeout=60.0),
                    timeout=60.0
                )
                messages_received += len(remaining_responses)
            except asyncio.TimeoutError:
                pass
            
            # Force garbage collection and monitor memory recovery
            gc.collect()
            recovery_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            # Monitor for 120 more seconds to observe memory recovery
            while time.time() - post_load_start < 120:
                await asyncio.sleep(10)
            
        finally:
            # Stop memory monitoring
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Analysis
        if memory_samples:
            memory_values = [sample["rss_mb"] for sample in memory_samples]
            peak_memory = max(memory_values)
            final_memory = memory_values[-1] if memory_values else baseline_memory
            memory_growth = peak_memory - baseline_memory
            memory_recovery = peak_memory - final_memory
            
            # Calculate memory growth rate
            if len(memory_samples) > 1:
                time_span = memory_samples[-1]["timestamp"] - memory_samples[0]["timestamp"]
                growth_rate = memory_growth / (time_span / 60.0)  # MB per minute
            else:
                growth_rate = 0
            
            # Analyze memory usage per message
            if messages_sent > 0:
                memory_per_message = (memory_growth * 1024 * 1024) / messages_sent  # bytes per message
            else:
                memory_per_message = 0
            
            # Check for memory leaks (growth should stabilize)
            if len(memory_values) >= 10:
                last_10_percent = memory_values[-len(memory_values)//10:]
                first_10_percent = memory_values[:len(memory_values)//10]
                
                last_avg = statistics.mean(last_10_percent)
                first_avg = statistics.mean(first_10_percent)
                
                if first_avg > 0:
                    leak_indicator = (last_avg - first_avg) / first_avg
                else:
                    leak_indicator = 0
            else:
                leak_indicator = 0
            
            # GC effectiveness
            gc_effectiveness = 0
            if gc_stats:
                total_collected = sum(stat["collected"] for stat in gc_stats)
                gc_effectiveness = total_collected / len(gc_stats) if gc_stats else 0
        else:
            peak_memory = baseline_memory
            memory_growth = 0
            memory_recovery = 0
            memory_per_message = 0
            growth_rate = 0
            leak_indicator = 0
            gc_effectiveness = 0
        
        # Assertions
        
        # Memory growth should be bounded
        assert memory_growth <= HIGH_VOLUME_CONFIG["max_memory_growth_mb"] * 2, \
            f"Memory growth too high: {memory_growth:.1f}MB"
        
        # Memory usage per message should be reasonable
        assert memory_per_message <= 1024, \
            f"Memory per message too high: {memory_per_message:.0f} bytes"
        
        # Should have good memory recovery after load
        recovery_ratio = memory_recovery / memory_growth if memory_growth > 0 else 1.0
        assert recovery_ratio >= 0.7, \
            f"Memory recovery too low: {recovery_ratio:.2%}"
        
        # Growth rate should not be excessive
        assert growth_rate <= 50.0, \
            f"Memory growth rate too high: {growth_rate:.1f} MB/min"
        
        # Should not have obvious memory leaks
        assert leak_indicator <= 0.1, \
            f"Potential memory leak detected: {leak_indicator:.2%} growth"
        
        # Delivery ratio should be reasonable despite high load
        delivery_ratio = messages_received / messages_sent if messages_sent > 0 else 0
        assert delivery_ratio >= 0.8, \
            f"Delivery ratio too low during memory test: {delivery_ratio:.3f}"
        
        # Update test results
        test_results.messages_sent = messages_sent
        test_results.messages_received = messages_received
        test_results.delivery_ratio = delivery_ratio
        test_results.peak_memory_mb = peak_memory
        test_results.memory_growth_mb = memory_growth
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Memory efficiency test completed: "
                   f"peak memory {peak_memory:.1f}MB, "
                   f"growth {memory_growth:.1f}MB, "
                   f"recovery {recovery_ratio:.1%}, "
                   f"delivery ratio {delivery_ratio:.3f}")


class TestErrorRecoveryAndResilience:
    """Test Case 8: Error Recovery and Resilience"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)  # 5 minute timeout
    async def test_error_recovery_and_resilience(self, throughput_client, high_volume_server):
        """
        Test system recovery from errors during high-volume operations.
        Tests error isolation, recovery mechanisms, and graceful degradation.
        """
        test_results = LoadTestResults(
            test_name="error_recovery_and_resilience",
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
        
        baseline_rate = 3000  # messages per second
        error_injection_rate = HIGH_VOLUME_CONFIG["error_injection_rate"]  # 10%
        
        logger.info(f"Starting error recovery test with {baseline_rate} msg/sec baseline...")
        
        # Phase 1: Establish baseline performance
        baseline_count = 1000
        baseline_results = await throughput_client.send_throughput_burst(
            message_count=baseline_count,
            rate_limit=baseline_rate
        )
        baseline_responses = await throughput_client.receive_responses(baseline_count, timeout=30.0)
        baseline_throughput = len(baseline_responses) / 30.0  # responses per second
        baseline_delivery_ratio = len(baseline_responses) / baseline_count
        
        logger.info(f"Baseline established: {baseline_throughput:.1f} msg/sec, "
                   f"{baseline_delivery_ratio:.3f} delivery ratio")
        
        # Phase 2: Error injection testing
        error_scenarios = [
            {
                "name": "connection_drops",
                "description": "Simulate random connection drops",
                "duration": 60,
                "error_rate": 0.05
            },
            {
                "name": "server_overload",
                "description": "Simulate server processing delays",
                "duration": 45,
                "error_rate": 0.1
            },
            {
                "name": "network_partitions",
                "description": "Simulate network connectivity issues",
                "duration": 30,
                "error_rate": 0.15
            }
        ]
        
        error_results = {}
        total_recovery_events = 0
        
        for scenario in error_scenarios:
            logger.info(f"Testing error scenario: {scenario['name']}")
            
            scenario_start = time.time()
            scenario_clients = []
            scenario_results = {
                "messages_sent": 0,
                "messages_received": 0,
                "errors_injected": 0,
                "recovery_attempts": 0,
                "successful_recoveries": 0,
                "throughput_impact": 0.0
            }
            
            try:
                # Create multiple clients for this scenario
                for i in range(5):
                    client = HighVolumeThroughputClient(
                        E2E_TEST_CONFIG["websocket_url"],
                        "mock-token",
                        f"{scenario['name']}-client-{i}"
                    )
                    await client.connect()
                    scenario_clients.append(client)
                
                # Simulate errors while sending messages
                messages_per_client = int(baseline_rate * scenario["duration"] / len(scenario_clients))
                
                async def send_with_error_injection(client, client_id, message_count):
                    """Send messages with injected errors."""
                    sent = 0
                    received = 0
                    errors = 0
                    recoveries = 0
                    
                    while sent < message_count:
                        try:
                            # Inject errors based on scenario
                            if random.random() < scenario["error_rate"]:
                                errors += 1
                                scenario_results["errors_injected"] += 1
                                
                                if scenario["name"] == "connection_drops":
                                    # Simulate connection drop
                                    await client.disconnect()
                                    await asyncio.sleep(random.uniform(1.0, 3.0))
                                    await client.connect()
                                    recoveries += 1
                                    
                                elif scenario["name"] == "server_overload":
                                    # Simulate processing delay by sending burst
                                    burst_size = min(50, message_count - sent)
                                    burst_results = await client.send_throughput_burst(
                                        burst_size, rate_limit=None  # No rate limit = overload
                                    )
                                    sent += burst_size
                                    
                                elif scenario["name"] == "network_partitions":
                                    # Simulate network issue with timeout
                                    try:
                                        timeout_message = {
                                            "type": "user_message",
                                            "message_id": f"{client_id}-timeout-{sent}",
                                            "content": "Timeout test message"
                                        }
                                        await asyncio.wait_for(
                                            client.connection.send(json.dumps(timeout_message)),
                                            timeout=0.1  # Very short timeout
                                        )
                                        sent += 1
                                    except asyncio.TimeoutError:
                                        errors += 1
                            else:
                                # Normal message sending
                                batch_size = min(10, message_count - sent)
                                batch_results = await client.send_throughput_burst(
                                    batch_size, rate_limit=baseline_rate / len(scenario_clients)
                                )
                                sent += batch_size
                            
                        except Exception as e:
                            logger.warning(f"Error in {client_id}: {e}")
                            errors += 1
                            
                            # Attempt recovery
                            try:
                                await client.disconnect()
                                await asyncio.sleep(1.0)
                                await client.connect()
                                recoveries += 1
                                scenario_results["recovery_attempts"] += 1
                            except:
                                break  # Give up on this client
                    
                    # Collect responses
                    try:
                        responses = await client.receive_responses(sent, timeout=30.0)
                        received = len(responses)
                    except:
                        received = 0
                    
                    return {
                        "sent": sent,
                        "received": received,
                        "errors": errors,
                        "recoveries": recoveries
                    }
                
                # Run error injection for all clients
                client_tasks = []
                for i, client in enumerate(scenario_clients):
                    task = asyncio.create_task(
                        send_with_error_injection(client, f"{scenario['name']}-{i}", messages_per_client)
                    )
                    client_tasks.append(task)
                
                # Wait for scenario completion
                client_results = await asyncio.gather(*client_tasks, return_exceptions=True)
                
                # Aggregate results
                for result in client_results:
                    if isinstance(result, dict):
                        scenario_results["messages_sent"] += result["sent"]
                        scenario_results["messages_received"] += result["received"]
                        scenario_results["recovery_attempts"] += result["recoveries"]
                        if result["received"] > 0:
                            scenario_results["successful_recoveries"] += 1
                
                scenario_duration = time.time() - scenario_start
                scenario_throughput = scenario_results["messages_received"] / scenario_duration
                scenario_results["throughput_impact"] = (baseline_throughput - scenario_throughput) / baseline_throughput
                
                error_results[scenario["name"]] = scenario_results
                total_recovery_events += scenario_results["recovery_attempts"]
                
                logger.info(f"Scenario {scenario['name']} completed: "
                           f"{scenario_results['messages_received']}/{scenario_results['messages_sent']} delivered, "
                           f"{scenario_results['recovery_attempts']} recoveries, "
                           f"{scenario_results['throughput_impact']:.1%} throughput impact")
            
            finally:
                # Clean up scenario clients
                for client in scenario_clients:
                    try:
                        await client.disconnect()
                    except:
                        pass
                
                # Allow system to stabilize
                await asyncio.sleep(5.0)
        
        # Phase 3: Recovery validation
        logger.info("Testing system recovery after error scenarios...")
        
        # Test if system returns to baseline performance
        recovery_count = 1000
        recovery_results = await throughput_client.send_throughput_burst(
            message_count=recovery_count,
            rate_limit=baseline_rate
        )
        recovery_responses = await throughput_client.receive_responses(recovery_count, timeout=30.0)
        recovery_throughput = len(recovery_responses) / 30.0
        recovery_delivery_ratio = len(recovery_responses) / recovery_count
        
        # Calculate overall metrics
        total_sent = baseline_count + sum(r["messages_sent"] for r in error_results.values()) + recovery_count
        total_received = len(baseline_responses) + sum(r["messages_received"] for r in error_results.values()) + len(recovery_responses)
        overall_delivery_ratio = total_received / total_sent if total_sent > 0 else 0
        
        # Assertions
        
        # Baseline should be good
        assert baseline_delivery_ratio >= 0.95, \
            f"Baseline delivery ratio too low: {baseline_delivery_ratio:.3f}"
        
        # Each error scenario should have reasonable impact
        for scenario_name, results in error_results.items():
            scenario_delivery_ratio = results["messages_received"] / results["messages_sent"] if results["messages_sent"] > 0 else 0
            
            # Should maintain some level of service during errors
            assert scenario_delivery_ratio >= 0.5, \
                f"Delivery ratio too low during {scenario_name}: {scenario_delivery_ratio:.3f}"
            
            # Throughput impact should not be catastrophic
            assert results["throughput_impact"] <= 0.7, \
                f"Throughput impact too high during {scenario_name}: {results['throughput_impact']:.1%}"
            
            # Should have attempted recovery
            if results["errors_injected"] > 0:
                assert results["recovery_attempts"] > 0, \
                    f"No recovery attempts during {scenario_name}"
        
        # System should recover to near baseline performance
        recovery_ratio = recovery_throughput / baseline_throughput if baseline_throughput > 0 else 0
        assert recovery_ratio >= 0.8, \
            f"System did not recover adequately: {recovery_ratio:.2%} of baseline"
        
        # Overall delivery ratio should be acceptable
        assert overall_delivery_ratio >= 0.8, \
            f"Overall delivery ratio too low: {overall_delivery_ratio:.3f}"
        
        # Should have detected and handled errors
        total_errors = sum(r["errors_injected"] for r in error_results.values())
        assert total_errors > 0, "No errors were injected during error testing"
        
        # Update test results
        test_results.messages_sent = total_sent
        test_results.messages_received = total_received
        test_results.delivery_ratio = overall_delivery_ratio
        test_results.error_count = total_errors
        test_results.recovery_count = total_recovery_events
        
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
        
        logger.info(f"Error recovery test completed: "
                   f"{overall_delivery_ratio:.3f} overall delivery ratio, "
                   f"{total_recovery_events} recovery events, "
                   f"{recovery_ratio:.1%} performance recovery")


# Performance Benchmark Test

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.timeout(600)  # 10 minute timeout
async def test_high_volume_throughput_benchmark(throughput_client, high_volume_server):
    """
    Comprehensive high-volume throughput benchmark.
    Provides baseline metrics for performance regression testing.
    """
    benchmark_results = LoadTestResults(
        test_name="high_volume_throughput_benchmark",
        start_time=time.time(),
        end_time=0,
        total_duration=0
    )
    
    logger.info("Starting comprehensive high-volume throughput benchmark...")
    
    # Benchmark configuration
    benchmark_phases = [
        {"name": "warmup", "rate": 1000, "duration": 30, "messages": 30000},
        {"name": "ramp_up", "rate": 5000, "duration": 60, "messages": 300000},
        {"name": "sustained", "rate": 7500, "duration": 120, "messages": 900000},
        {"name": "peak", "rate": 10000, "duration": 60, "messages": 600000},
        {"name": "cool_down", "rate": 2000, "duration": 30, "messages": 60000}
    ]
    
    phase_results = {}
    all_latency_measurements = []
    
    for phase in benchmark_phases:
        logger.info(f"Benchmark phase: {phase['name']} - {phase['rate']} msg/sec for {phase['duration']}s")
        
        phase_start = time.perf_counter()
        
        # Send messages for this phase
        phase_sent_results = await throughput_client.send_throughput_burst(
            message_count=phase["messages"],
            rate_limit=phase["rate"]
        )
        
        # Collect responses
        phase_responses = await throughput_client.receive_responses(
            expected_count=phase["messages"],
            timeout=phase["duration"] + 30
        )
        
        phase_duration = time.perf_counter() - phase_start
        
        # Calculate phase metrics
        sent_count = len([r for r in phase_sent_results if r.get("status") == "sent"])
        received_count = len(phase_responses)
        
        phase_metrics = ThroughputAnalyzer.calculate_throughput_metrics(
            sent_count, received_count, phase_duration
        )
        
        # Collect latency measurements for this phase
        phase_latencies = []
        for response in phase_responses:
            send_time = response.get("send_time", 0)
            receive_time = response.get("receive_time", 0)
            if receive_time > send_time:
                latency = receive_time - send_time
                measurement = LatencyMeasurement(
                    message_id=response.get("message_id", ""),
                    send_time=send_time,
                    receive_time=receive_time,
                    processing_time=response.get("processing_time", 0)
                )
                phase_latencies.append(measurement)
                all_latency_measurements.append(measurement)
        
        # Analyze phase latency
        if phase_latencies:
            phase_latency_analysis = ThroughputAnalyzer.analyze_latency_distribution(phase_latencies)
            phase_metrics = phase_metrics._replace(
                latency_p50=phase_latency_analysis["p50"],
                latency_p95=phase_latency_analysis["p95"],
                latency_p99=phase_latency_analysis["p99"]
            )
        
        phase_results[phase["name"]] = {
            "target_rate": phase["rate"],
            "actual_rate": phase_metrics.send_rate,
            "throughput": phase_metrics.receive_rate,
            "latency_p50": phase_metrics.latency_p50,
            "latency_p95": phase_metrics.latency_p95,
            "latency_p99": phase_metrics.latency_p99,
            "delivery_ratio": phase_metrics.delivery_ratio,
            "duration": phase_duration,
            "messages_sent": sent_count,
            "messages_received": received_count
        }
        
        logger.info(f"Phase {phase['name']} completed: "
                   f"{phase_metrics.receive_rate:.1f} msg/sec throughput, "
                   f"P95 latency: {phase_metrics.latency_p95:.3f}s")
        
        # Brief pause between phases
        await asyncio.sleep(2.0)
    
    # Overall benchmark analysis
    total_sent = sum(p["messages_sent"] for p in phase_results.values())
    total_received = sum(p["messages_received"] for p in phase_results.values())
    
    # Calculate peak and sustained metrics
    benchmark_results.peak_throughput = max(p["throughput"] for p in phase_results.values())
    sustained_phases = ["ramp_up", "sustained"]
    benchmark_results.sustained_throughput = statistics.mean([
        phase_results[p]["throughput"] for p in sustained_phases if p in phase_results
    ])
    benchmark_results.average_throughput = total_received / sum(p["duration"] for p in phase_results.values())
    
    # Overall latency analysis
    if all_latency_measurements:
        overall_latency = ThroughputAnalyzer.analyze_latency_distribution(all_latency_measurements)
        benchmark_results.latency_p50 = overall_latency["p50"]
        benchmark_results.latency_p95 = overall_latency["p95"]
        benchmark_results.latency_p99 = overall_latency["p99"]
        benchmark_results.latency_p999 = overall_latency.get("p999", overall_latency["p99"])
    
    benchmark_results.messages_sent = total_sent
    benchmark_results.messages_received = total_received
    benchmark_results.delivery_ratio = total_received / total_sent if total_sent > 0 else 0
    
    # Resource utilization
    final_memory = psutil.Process().memory_info().rss / (1024 * 1024)
    benchmark_results.peak_memory_mb = final_memory
    benchmark_results.peak_cpu_usage = psutil.cpu_percent()
    
    benchmark_results.end_time = time.time()
    benchmark_results.total_duration = benchmark_results.end_time - benchmark_results.start_time
    
    # Performance assertions
    assert benchmark_results.peak_throughput >= HIGH_VOLUME_CONFIG["sustained_throughput_target"], \
        f"Peak throughput below target: {benchmark_results.peak_throughput:.1f} < {HIGH_VOLUME_CONFIG['sustained_throughput_target']}"
    
    assert benchmark_results.sustained_throughput >= HIGH_VOLUME_CONFIG["sustained_throughput_target"] * 0.9, \
        f"Sustained throughput below target: {benchmark_results.sustained_throughput:.1f}"
    
    assert benchmark_results.latency_p95 <= HIGH_VOLUME_CONFIG["latency_p95_target"], \
        f"P95 latency above target: {benchmark_results.latency_p95:.3f}s"
    
    assert benchmark_results.delivery_ratio >= HIGH_VOLUME_CONFIG["min_delivery_ratio"], \
        f"Delivery ratio below target: {benchmark_results.delivery_ratio:.3f}"
    
    logger.info("High-volume throughput benchmark completed successfully!")
    logger.info(f"Peak throughput: {benchmark_results.peak_throughput:.1f} msg/sec")
    logger.info(f"Sustained throughput: {benchmark_results.sustained_throughput:.1f} msg/sec")
    logger.info(f"P95 latency: {benchmark_results.latency_p95:.3f}s")
    logger.info(f"Delivery ratio: {benchmark_results.delivery_ratio:.3f}")
    
    return benchmark_results


if __name__ == "__main__":
    # Allow running individual test cases for debugging
    pytest.main([__file__, "-v", "--tb=short", "-x"])