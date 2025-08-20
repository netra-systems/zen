"""
Shared utilities for high-volume throughput testing.
Extracted from test_high_volume_throughput.py to comply with size limits.
"""

import asyncio
import time
import uuid
import json
import logging
import statistics
import threading
import gc
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, NamedTuple
from collections import defaultdict, deque
from dataclasses import dataclass, field

import websockets
import httpx

logger = logging.getLogger(__name__)

# Environment configuration
E2E_TEST_CONFIG = {
    "websocket_url": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8765"),
    "backend_url": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
    "auth_service_url": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "skip_real_services": os.getenv("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_timeout": int(os.getenv("E2E_TEST_TIMEOUT", "300")),
}

class ThroughputMetrics(NamedTuple):
    """Core throughput measurement data structure"""
    messages_sent: int
    messages_received: int
    start_time: float
    end_time: float
    total_duration: float
    throughput_per_second: float
    success_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float

@dataclass
class LatencyMeasurement:
    """Individual message latency tracking"""
    message_id: str
    sent_timestamp: float
    received_timestamp: Optional[float] = None
    latency_ms: Optional[float] = None
    
    def calculate_latency(self) -> float:
        if self.received_timestamp:
            self.latency_ms = (self.received_timestamp - self.sent_timestamp) * 1000
        return self.latency_ms or 0.0

@dataclass
class LoadTestResults:
    """Comprehensive load test results container"""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_messages_sent: int = 0
    total_messages_received: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    latency_measurements: List[LatencyMeasurement] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def add_latency(self, measurement: LatencyMeasurement):
        self.latency_measurements.append(measurement)
    
    def calculate_metrics(self) -> ThroughputMetrics:
        if not self.end_time:
            self.end_time = datetime.now(timezone.utc)
            
        duration = (self.end_time - self.start_time).total_seconds()
        latencies = [m.latency_ms for m in self.latency_measurements if m.latency_ms]
        
        return ThroughputMetrics(
            messages_sent=self.total_messages_sent,
            messages_received=self.total_messages_received,
            start_time=self.start_time.timestamp(),
            end_time=self.end_time.timestamp(),
            total_duration=duration,
            throughput_per_second=self.total_messages_received / duration if duration > 0 else 0,
            success_rate=self.total_messages_received / self.total_messages_sent if self.total_messages_sent > 0 else 0,
            latency_p50=statistics.median(latencies) if latencies else 0,
            latency_p95=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else (max(latencies) if latencies else 0),
            latency_p99=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else (max(latencies) if latencies else 0),
        )

def create_test_message(message_id: str = None, size_bytes: int = 1024) -> Dict[str, Any]:
    """Create standardized test message with specified size"""
    msg_id = message_id or str(uuid.uuid4())
    padding = "x" * max(0, size_bytes - 200)  # Reserve space for metadata
    
    return {
        "message_id": msg_id,
        "timestamp": time.time(),
        "type": "throughput_test",
        "content": f"Test message payload {padding}",
        "metadata": {
            "test_run": "high_volume_throughput",
            "size_bytes": size_bytes
        }
    }

def measure_system_resources() -> Dict[str, float]:
    """Capture current system resource usage"""
    process = psutil.Process()
    return {
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "threads": process.num_threads(),
    }

async def wait_for_stable_connections(connections: List, max_wait: float = 30.0) -> bool:
    """Wait for all connections to be in a stable state"""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        stable_count = sum(1 for conn in connections if hasattr(conn, 'open') and conn.open)
        if stable_count == len(connections):
            return True
        await asyncio.sleep(0.1)
    return False

def analyze_latency_distribution(measurements: List[LatencyMeasurement]) -> Dict[str, float]:
    """Analyze latency distribution and return key percentiles"""
    latencies = [m.latency_ms for m in measurements if m.latency_ms is not None]
    if not latencies:
        return {}
    
    latencies.sort()
    count = len(latencies)
    
    return {
        "min": min(latencies),
        "max": max(latencies),
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p90": latencies[int(count * 0.9)] if count > 10 else max(latencies),
        "p95": latencies[int(count * 0.95)] if count > 20 else max(latencies),
        "p99": latencies[int(count * 0.99)] if count > 100 else max(latencies),
        "std_dev": statistics.stdev(latencies) if count > 1 else 0,
    }