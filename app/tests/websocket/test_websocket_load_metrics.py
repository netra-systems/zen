"""WebSocket Load Testing Metrics and Base Classes.

Core metrics tracking and base testing infrastructure for WebSocket load tests.
"""

import asyncio
import json
import time
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any
import websockets
from unittest.mock import AsyncMock

from app.schemas.websocket_models import WebSocketMessage


class LoadTestMetrics:
    """Tracks load test metrics."""
    
    def __init__(self):
        self.connection_times: List[float] = []
        self.message_times: List[float] = []
        self.error_count = 0
        self.successful_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.memory_usage_samples: List[float] = []
        self.start_time = time.time()
    
    def record_connection_time(self, duration: float):
        """Record connection establishment time."""
        self.connection_times.append(duration)
        self.successful_connections += 1
    
    def record_message_time(self, duration: float):
        """Record message round-trip time."""
        self.message_times.append(duration)
    
    def record_error(self):
        """Record an error."""
        self.error_count += 1
    
    def record_message_sent(self):
        """Record a message sent."""
        self.total_messages_sent += 1
    
    def record_message_received(self):
        """Record a message received."""
        self.total_messages_received += 1
    
    def record_memory_usage(self, usage_mb: float):
        """Record memory usage sample."""
        self.memory_usage_samples.append(usage_mb)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test metrics summary."""
        test_duration = time.time() - self.start_time
        
        return {
            "test_duration_seconds": test_duration,
            "successful_connections": self.successful_connections,
            "error_count": self.error_count,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "message_throughput_per_second": self._calculate_throughput(test_duration),
            "connection_times": self._get_connection_stats(),
            "message_times": self._get_message_stats(),
            "memory_usage": self._get_memory_stats()
        }
    
    def _calculate_throughput(self, test_duration: float) -> float:
        """Calculate message throughput."""
        if test_duration > 0:
            return self.total_messages_sent / test_duration
        return 0
    
    def _get_connection_stats(self) -> Dict[str, float]:
        """Get connection time statistics."""
        if not self.connection_times:
            return {"min_ms": 0, "max_ms": 0, "avg_ms": 0, "p95_ms": 0}
        
        return {
            "min_ms": min(self.connection_times) * 1000,
            "max_ms": max(self.connection_times) * 1000,
            "avg_ms": statistics.mean(self.connection_times) * 1000,
            "p95_ms": self._get_percentile(self.connection_times, 0.95) * 1000
        }
    
    def _get_message_stats(self) -> Dict[str, float]:
        """Get message time statistics."""
        if not self.message_times:
            return {"min_ms": 0, "max_ms": 0, "avg_ms": 0, "p95_ms": 0}
        
        return {
            "min_ms": min(self.message_times) * 1000,
            "max_ms": max(self.message_times) * 1000,
            "avg_ms": statistics.mean(self.message_times) * 1000,
            "p95_ms": self._get_percentile(self.message_times, 0.95) * 1000
        }
    
    def _get_memory_stats(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        if not self.memory_usage_samples:
            return {"min_mb": 0, "max_mb": 0, "avg_mb": 0}
        
        return {
            "min_mb": min(self.memory_usage_samples),
            "max_mb": max(self.memory_usage_samples),
            "avg_mb": statistics.mean(self.memory_usage_samples)
        }
    
    def _get_percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]


class WebSocketLoadTester:
    """Performs load testing on WebSocket connections."""
    
    def __init__(self, server_url: str = "ws://localhost:8000/ws"):
        self.server_url = server_url
        self.metrics = LoadTestMetrics()
    
    async def simulate_connection(self, connection_id: str, duration_seconds: int, 
                                messages_per_second: int) -> Dict[str, Any]:
        """Simulate a single WebSocket connection."""
        connection_start = time.time()
        
        try:
            websocket = await self._create_mock_websocket()
            connection_time = time.time() - connection_start
            self.metrics.record_connection_time(connection_time)
            
            await self._run_message_exchange(
                websocket, connection_id, duration_seconds, messages_per_second
            )
            
            return {"status": "success", "connection_id": connection_id}
            
        except Exception as e:
            self.metrics.record_error()
            return {"status": "error", "connection_id": connection_id, "error": str(e)}
    
    async def run_concurrent_connections_test(self, num_connections: int, 
                                            duration_seconds: int = 30,
                                            messages_per_second: int = 1) -> Dict[str, Any]:
        """Test with multiple concurrent connections."""
        print(f"Starting load test: {num_connections} connections, {duration_seconds}s duration, {messages_per_second} msg/s")
        
        tasks = []
        for i in range(num_connections):
            connection_id = f"load_test_conn_{i}"
            task = asyncio.create_task(
                self.simulate_connection(connection_id, duration_seconds, messages_per_second)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._analyze_results(results, num_connections, duration_seconds, messages_per_second)
    
    async def _create_mock_websocket(self) -> AsyncMock:
        """Create mock websocket for testing."""
        websocket = AsyncMock()
        websocket.recv = AsyncMock()
        websocket.send = AsyncMock()
        return websocket
    
    async def _run_message_exchange(self, websocket: AsyncMock, connection_id: str,
                                   duration_seconds: int, messages_per_second: int):
        """Run message exchange for connection."""
        message_interval = 1.0 / messages_per_second if messages_per_second > 0 else 1.0
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            await self._send_test_message(websocket, connection_id)
            await asyncio.sleep(message_interval)
    
    async def _send_test_message(self, websocket: AsyncMock, connection_id: str):
        """Send a single test message."""
        message_start = time.time()
        
        test_message = {
            "type": "ping",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": "x" * 100
        }
        
        await websocket.send(json.dumps(test_message))
        self.metrics.record_message_sent()
        
        await websocket.recv()
        self.metrics.record_message_received()
        
        message_time = time.time() - message_start
        self.metrics.record_message_time(message_time)
    
    def _analyze_results(self, results: List[Any], num_connections: int,
                        duration_seconds: int, messages_per_second: int) -> Dict[str, Any]:
        """Analyze test results."""
        successful_connections = sum(
            1 for r in results 
            if isinstance(r, dict) and r.get("status") == "success"
        )
        failed_connections = len(results) - successful_connections
        
        return {
            "test_config": {
                "num_connections": num_connections,
                "duration_seconds": duration_seconds,
                "messages_per_second": messages_per_second
            },
            "results": {
                "successful_connections": successful_connections,
                "failed_connections": failed_connections,
                "success_rate": successful_connections / num_connections
            },
            "metrics": self.metrics.get_summary()
        }
