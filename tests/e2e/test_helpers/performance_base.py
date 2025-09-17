"""
Performance Testing Base Utilities

Shared components for high-volume throughput testing, extracted to maintain
test file line limits while preserving functionality.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Platform Stability, Test Maintainability
- Value Impact: Enables systematic performance validation
- Strategic Impact: Supports enterprise SLAs and scaling requirements
"""

import asyncio
import functools
import gc
import json
import logging
import os
import random
import statistics
import threading
import time
import tracemalloc
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

import httpx
import psutil
import websockets

# Configure logging for high-volume testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    @staticmethod
    def calculate_performance_score(metrics: ThroughputMetrics) -> float:
        """Calculate overall performance score (0-100)."""
        throughput_score = min(100, (metrics.send_rate / HIGH_VOLUME_CONFIG["peak_throughput_target"]) * 100)
        latency_score = max(0, 100 - (metrics.latency_p95 / HIGH_VOLUME_CONFIG["latency_p95_target"]) * 100)
        reliability_score = metrics.delivery_ratio * 100
        
        return (throughput_score + latency_score + reliability_score) / 3

    @staticmethod
    def assert_throughput_requirements(metrics: ThroughputMetrics, test_name: str):
        """Assert that throughput meets minimum requirements."""
        assert metrics.delivery_ratio >= HIGH_VOLUME_CONFIG["min_delivery_ratio"], \
            f"{test_name}: Delivery ratio {metrics.delivery_ratio:.3f} below {HIGH_VOLUME_CONFIG['min_delivery_ratio']}"
        
        assert metrics.error_rate <= HIGH_VOLUME_CONFIG["max_message_loss_ratio"], \
            f"{test_name}: Error rate {metrics.error_rate:.3f} above {HIGH_VOLUME_CONFIG['max_message_loss_ratio']}"
        
        assert metrics.latency_p95 <= HIGH_VOLUME_CONFIG["latency_p95_target"], \
            f"{test_name}: P95 latency {metrics.latency_p95:.3f}s above {HIGH_VOLUME_CONFIG['latency_p95_target']}s"

    @staticmethod 
    def assert_scaling_linearity(rates: List[int], actual_rates: List[float], threshold: float = 0.95):
        """Assert that throughput scaling is approximately linear."""
        if len(rates) >= 3:
            correlation = statistics.correlation(rates, actual_rates)
            assert correlation >= threshold, \
                f"Scaling linearity {correlation:.3f} below threshold {threshold}"


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
        except websockets.ConnectionClosed:
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
        
        if message_id in self.processed_messages:
            await websocket.send(json.dumps({
                "type": "duplicate_rejected",
                "message_id": message_id,
                "original_timestamp": self.processed_messages[message_id],
                "timestamp": current_time
            }))
            return
        
        self.processed_messages[message_id] = current_time
        
        processing_start = time.perf_counter()
        await asyncio.sleep(0.001)  # 1ms simulated processing
        processing_end = time.perf_counter()
        
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
                
                uptime = time.time() - self.start_time
                if uptime > 0:
                    current_throughput = self.message_counter / uptime
                    self.throughput_history.append({
                        "time": time.time(),
                        "throughput": current_throughput,
                        "connections": len(self.clients),
                        "queue_depth": self.queue_depth
                    })
                
                if len(self.throughput_history) > 1000:
                    self.throughput_history = self.throughput_history[-1000:]
                
                await asyncio.sleep(1.0)
                
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
            if "localhost:8765" in self.websocket_uri:
                self.connection = await websockets.connect(
                    self.websocket_uri,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=2**20,
                    max_queue=1000
                )
            else:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                self.connection = await websockets.connect(
                    self.websocket_uri,
                    additional_headers=headers,
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
