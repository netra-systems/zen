"""Memory Leak Detection Utilities - Supporting Classes for Memory Leak Tests
Business Value: $50K MRR - System stability via modular memory leak detection
Supporting utilities to maintain <300 line limit in main test file
ARCHITECTURAL COMPLIANCE: <300 lines, <8 lines per function
"""

import asyncio
import gc
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot with leak indicators"""
    timestamp: datetime
    memory_mb: float
    memory_percent: float
    connection_count: int
    thread_count: int
    websocket_connections: int


@dataclass
class MemoryLeakMetrics:
    """Memory leak detection metrics"""
    snapshots: List[MemorySnapshot] = field(default_factory=list)
    leak_detected: bool = False
    memory_growth_rate: float = 0.0
    connection_leaks: int = 0
    max_memory_mb: float = 0.0
    test_duration_minutes: float = 0.0


class UserActivitySimulator:
    """Simulates continuous user activity for memory testing"""
    
    def __init__(self, harness):
        self.harness = harness
        self.active_users: List[Dict[str, Any]] = []
        self.simulation_running = False
    
    async def start_continuous_activity(self, user_count: int = 5):
        """Start continuous user activity simulation"""
        self.active_users = await self._create_test_users(user_count)
        self.simulation_running = True
        tasks = [self._simulate_user_activity(user) for user in self.active_users]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _create_test_users(self, count: int) -> List[Dict[str, Any]]:
        """Create authenticated test users with WebSocket connections"""
        users = []
        for i in range(count):
            user = await self.harness.create_test_user(f"memtest_{i}@test.com")
            ws_conn = await self.harness.create_websocket_connection(user)
            users.append({"user": user, "websocket": ws_conn})
        return users
    
    async def _simulate_user_activity(self, user_data: Dict[str, Any]):
        """Simulate realistic user activity patterns"""
        user, websocket = user_data["user"], user_data["websocket"]
        message_count = 0
        while self.simulation_running:
            await self._send_user_message(user, websocket, message_count)
            await asyncio.sleep(3.0)  # 20 messages per minute per user
            message_count += 1
    
    async def _send_user_message(self, user, websocket, count: int):
        """Send realistic message via WebSocket"""
        message = {
            "type": "chat_message",
            "content": f"Memory test message {count} from {user.email}",
            "thread_id": user.email.replace("@", "_")
        }
        try:
            await websocket.send_message(message)
        except Exception:
            pass  # Continue simulation despite individual failures
    
    def stop_simulation(self):
        """Stop user activity simulation"""
        self.simulation_running = False


class MemoryLeakDetector:
    """Detects memory leaks in sustained load conditions"""
    
    def __init__(self):
        self.metrics = MemoryLeakMetrics()
        self.monitoring_active = False
        self.memory_threshold_mb = 500.0
        self.leak_growth_threshold = 2.0  # MB per hour
    
    async def monitor_memory_usage(self, duration_minutes: float):
        """Monitor memory usage for specified duration"""
        self.monitoring_active = True
        start_time = time.time()
        
        while self.monitoring_active and self._should_continue_monitoring(start_time, duration_minutes):
            snapshot = self._capture_memory_snapshot()
            self.metrics.snapshots.append(snapshot)
            await asyncio.sleep(30.0)  # Sample every 30 seconds
        
        self.metrics.test_duration_minutes = (time.time() - start_time) / 60.0
        self._analyze_memory_patterns()
    
    def _should_continue_monitoring(self, start_time: float, duration_minutes: float) -> bool:
        """Check if monitoring should continue"""
        elapsed_minutes = (time.time() - start_time) / 60.0
        return elapsed_minutes < duration_minutes
    
    def _capture_memory_snapshot(self) -> MemorySnapshot:
        """Capture current memory usage snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()
        connection_count = self._get_connection_count(process)
        
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            memory_mb=memory_info.rss / 1024 / 1024,
            memory_percent=process.memory_percent(),
            connection_count=connection_count,
            thread_count=process.num_threads(),
            websocket_connections=self._estimate_websocket_connections()
        )
    
    def _get_connection_count(self, process) -> int:
        """Get network connection count safely"""
        try:
            return len(process.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return 0
    
    def _estimate_websocket_connections(self) -> int:
        """Estimate WebSocket connection count"""
        # Simplified estimation based on open connections
        return 5  # Placeholder for actual WebSocket counting
    
    def _analyze_memory_patterns(self):
        """Analyze memory usage patterns for leaks"""
        if len(self.metrics.snapshots) < 10:
            return
        
        self._calculate_memory_growth_rate()
        self._detect_connection_leaks()
        self._update_leak_detection_status()
    
    def _calculate_memory_growth_rate(self):
        """Calculate memory growth rate per hour"""
        snapshots = self.metrics.snapshots
        start_memory = snapshots[0].memory_mb
        end_memory = snapshots[-1].memory_mb
        duration_hours = self.metrics.test_duration_minutes / 60.0
        
        if duration_hours > 0:
            self.metrics.memory_growth_rate = (end_memory - start_memory) / duration_hours
        self.metrics.max_memory_mb = max(s.memory_mb for s in snapshots)
    
    def _detect_connection_leaks(self):
        """Detect connection leaks from snapshots"""
        snapshots = self.metrics.snapshots
        start_connections = snapshots[0].connection_count
        end_connections = snapshots[-1].connection_count
        self.metrics.connection_leaks = max(0, end_connections - start_connections - 5)
    
    def _update_leak_detection_status(self):
        """Update overall leak detection status"""
        growth_leak = self.metrics.memory_growth_rate > self.leak_growth_threshold
        memory_leak = self.metrics.max_memory_mb > self.memory_threshold_mb
        connection_leak = self.metrics.connection_leaks > 10
        
        self.metrics.leak_detected = growth_leak or memory_leak or connection_leak
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring_active = False
