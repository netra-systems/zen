"""

Shared utilities for high-volume throughput testing.

Extracted from test_high_volume_throughput.py to comply with size limits.

"""



from shared.isolated_environment import get_env

import asyncio

import time

import uuid

import json

import logging

import statistics

import psutil

import os

from typing import Dict, List, Optional, Any



# Import metrics and data structures

from tests.e2e.fixtures.throughput_metrics import (

    ThroughputMetrics, LatencyMeasurement, LoadTestResults,

    ThroughputAnalyzer, HIGH_VOLUME_CONFIG

)



# Import server infrastructure

from tests.e2e.test_helpers.high_volume_server import HighVolumeWebSocketServer, HighVolumeThroughputClient



logger = logging.getLogger(__name__)



# Environment configuration

E2E_TEST_CONFIG = {

    "websocket_url": get_env().get("E2E_WEBSOCKET_URL", "ws://localhost:8765"),

    "backend_url": get_env().get("E2E_BACKEND_URL", "http://localhost:8000"),

    "auth_service_url": get_env().get("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),

    "skip_real_services": get_env().get("SKIP_REAL_SERVICES", "true").lower() == "true",

    "test_timeout": int(get_env().get("E2E_TEST_TIMEOUT", "300")),

}



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

