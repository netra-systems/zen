class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()
"""
        """
        CRITICAL: WebSocket Performance and Load Failure Test Suite

        BUSINESS CRITICAL PERFORMANCE REQUIREMENTS:
        - Notifications MUST be delivered within 500ms under normal load
        - System MUST handle 100+ concurrent users without degradation
        - Memory usage MUST NOT grow unbounded during high notification volume
        - WebSocket connections MUST remain stable under sustained load
        - No notification loss MUST occur even during peak usage

        These tests are designed to FAIL initially to expose performance bottlenecks:
        1. Notification delivery delays exceeding acceptable thresholds
        2. Memory leaks in notification queuing and tracking systems
        3. Connection instability under high concurrent load
        4. Thread pool exhaustion during burst notification scenarios
        5. Queue overflow causing notification loss
        6. Performance degradation with increasing user count
"""
        SLA Impact: Violation of response time guarantees"""

import asyncio
import gc
import json
import os
import psutil
import sys
import time
import threading
import uuid
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
import pytest
from shared.isolated_environment import IsolatedEnvironment

            # Add project root to path
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
        sys.path.insert(0, project_root)

from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

        logger = central_logger.get_logger(__name__)


        @dataclass"""
        """Records a performance measurement."""
        timestamp: float
        metric_name: str
        value: float
        user_id: str
        context: Dict[str, Any] = field(default_factory=dict)


        @dataclass"""
        """Results from a load test scenario."""
        test_name: str
        start_time: float
        end_time: float
        total_users: int
        notifications_sent: int
        notifications_delivered: int
        notifications_lost: int
        avg_delivery_time_ms: float
        max_delivery_time_ms: float
        p95_delivery_time_ms: float
        memory_peak_mb: float
        memory_leaked_mb: float
        errors_encountered: int
        performance_violations: List[str] = field(default_factory=list)

"""
        """Monitors system performance during WebSocket notification tests."""

    def __init__(self):
        pass
        self.metrics: List[PerformanceMetric] = []
        self.delivery_times: List[float] = []
        self.memory_samples: List[float] = []
        self.start_memory_mb: float = 0
        self.notification_queue_sizes: List[int] = []
        self.connection_counts: List[int] = []
        self.error_counts: Dict[str, int] = {}
        self.lock = threading.Lock()
        self._monitoring = False
        self._monitor_task = None
"""
        """Start continuous performance monitoring."""
        if not self._monitoring:
        self._monitoring = True
        self.start_memory_mb = self._get_memory_usage_mb()
        self._monitor_task = asyncio.create_task(self._continuous_monitor())
"""
        """Stop performance monitoring."""
        pass
        self._monitoring = False
        if self._monitor_task:
        self._monitor_task.cancel()
        try:
        await self._monitor_task
        except asyncio.CancelledError:
        pass"""
        def record_metric(self, metric_name: str, value: float, user_id: str = "system",
        context: Dict[str, Any] = None):
        """Record a performance metric."""
        metric = PerformanceMetric( )
        timestamp=time.time(),
        metric_name=metric_name,
        value=value,
        user_id=user_id,
        context=context or {}
    

        with self.lock:
        self.metrics.append(metric)
"""
        if metric_name == "notification_delivery_time_ms":
        self.delivery_times.append(value)
        elif metric_name == "memory_usage_mb":
        self.memory_samples.append(value)
        elif metric_name == "notification_queue_size":
        self.notification_queue_sizes.append(int(value))
        elif metric_name == "active_connections":
        self.connection_counts.append(int(value))
        elif metric_name.startswith("error_"):
        error_type = metric_name[6:]  # Remove "error_" prefix
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        await asyncio.sleep(0)
        return process.memory_info().rss / 1024 / 1024
"""
        """Continuously monitor system resources."""
        while self._monitoring:
        try:
            # Record memory usage"""
        self.record_metric("memory_usage_mb", memory_mb)

            # Record GC stats
        gc_stats = gc.get_stats()
        if gc_stats:
        self.record_metric("gc_collections", sum(stat['collections'] for stat in gc_stats))

        await asyncio.sleep(0.1)  # Sample every 100ms
        except Exception as e:
        logger.warning("formatted_string")

        def get_load_test_result(self, test_name: str, start_time: float, end_time: float,
        total_users: int, notifications_sent: int,
        notifications_delivered: int) -> LoadTestResult:
        """Generate load test result summary."""
        pass
        notifications_lost = notifications_sent - notifications_delivered

    # Calculate delivery time statistics
        avg_delivery = statistics.mean(self.delivery_times) if self.delivery_times else 0
        max_delivery = max(self.delivery_times) if self.delivery_times else 0
        p95_delivery = statistics.quantiles(self.delivery_times, n=20)[18] if len(self.delivery_times) > 20 else max_delivery

    # Calculate memory metrics
        peak_memory = max(self.memory_samples) if self.memory_samples else self.start_memory_mb
        memory_leaked = peak_memory - self.start_memory_mb

    # Identify performance violations
        violations = []"""
        violations.append("formatted_string")
        if p95_delivery > 1000:  # 1s threshold for P95
        violations.append("formatted_string")
        if memory_leaked > 100:  # 100MB leak threshold
        violations.append("formatted_string")
        if notifications_lost > 0:
        violations.append("formatted_string")

        await asyncio.sleep(0)
        return LoadTestResult( )
        test_name=test_name,
        start_time=start_time,
        end_time=end_time,
        total_users=total_users,
        notifications_sent=notifications_sent,
        notifications_delivered=notifications_delivered,
        notifications_lost=notifications_lost,
        avg_delivery_time_ms=avg_delivery,
        max_delivery_time_ms=max_delivery,
        p95_delivery_time_ms=p95_delivery,
        memory_peak_mb=peak_memory,
        memory_leaked_mb=memory_leaked,
        errors_encountered=sum(self.error_counts.values()),
        performance_violations=violations
        


        @pytest.fixture
    async def performance_monitor():
        """Fixture providing performance monitoring."""
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        yield monitor
        await monitor.stop_monitoring()

"""
        """Test notification delivery performance under various loads."""

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.slow"""
"""CRITICAL: Test notification delivery latency degrades with load."""
        # This test SHOULD FAIL initially"""
test_name = "notification_latency_degradation"
num_users = 50
notifications_per_user = 20

        # Simulate WebSocket manager with performance issues
mock_websocket_manager = Magic        notification_queue = asyncio.Queue(maxsize=100)  # Limited queue size

sent_notifications = 0
delivered_notifications = 0

async def slow_notification_delivery(user_id: str, notification_data: Dict[str, Any]):
"""Simulate slow notification delivery that degrades with load."""
pass
nonlocal sent_notifications, delivered_notifications

sent_notifications += 1
delivery_start = time.time()

try:
        # Queue size affects delivery time (performance issue!)
queue_size = notification_queue.qsize()
        # Put notification in queue
await notification_queue.put((user_id, notification_data, delivery_start))

        # Simulate processing delay that increases with load
await asyncio.sleep(delivery_delay)

        Remove from queue (delivery complete)
await notification_queue.get()

delivery_end = time.time()
delivered_notifications += 1

        # Record delivery time"""
"notification_delivery_time_ms",
delivery_time_ms,
user_id,
{"queue_size": queue_size, "load_factor": load_factor}
        

        # Record queue size
performance_monitor.record_metric("notification_queue_size", queue_size, user_id)

await asyncio.sleep(0)
return True

except asyncio.QueueFull:
            # Queue overflow - notification lost!
performance_monitor.record_metric("error_queue_overflow", 1, user_id)
return False
except Exception as e:
performance_monitor.record_metric("error_delivery_failure", 1, user_id)
return False

                # Generate concurrent load
start_time = time.time()

tasks = []
for user_num in range(num_users):
user_id = "formatted_string"

for notification_num in range(notifications_per_user):
notification_data = {"type": "tool_progress",, "progress": notification_num * 5,, "tool_name": "formatted_string",, "timestamp": time.time()}
tasks.append(slow_notification_delivery(user_id, notification_data))

                        # Execute all notifications concurrently
results = await asyncio.gather(*tasks, return_exceptions=True)

end_time = time.time()

                        # Generate test result
load_test_result = performance_monitor.get_load_test_result( )
test_name, start_time, end_time, num_users, sent_notifications, delivered_notifications
                        

                        # Verify performance degradation occurred
assert load_test_result.avg_delivery_time_ms > 50, "formatted_string"
assert load_test_result.p95_delivery_time_ms > 100, "formatted_string"

                        # Check for performance violations
assert len(load_test_result.performance_violations) > 0, "Expected performance violations"

                        # Verify delivery times increased with queue size
delivery_metrics = [item for item in []]
high_load_deliveries = [item for item in []]
low_load_deliveries = [item for item in []]

if high_load_deliveries and low_load_deliveries:
avg_high_load = statistics.mean(m.value for m in high_load_deliveries)
avg_low_load = statistics.mean(m.value for m in low_load_deliveries)
assert avg_high_load > avg_low_load * 1.5, "formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.slow
    async def test_memory_leak_under_sustained_load(self, performance_monitor):
"""CRITICAL: Test memory leaks under sustained notification load."""
                                # This test SHOULD FAIL initially"""
test_name = "memory_leak_sustained_load"
duration_seconds = 30  # 30 second test
notifications_per_second = 20

                                # Simulate notification system with memory leaks
notification_history = {}  # This will leak memory!
user_contexts = {}  # This will also leak!
pending_deliveries = {}  # And this!

sent_notifications = 0
delivered_notifications = 0

async def leaky_notification_system(user_id: str, notification_data: Dict[str, Any]):
"""Notification system that leaks memory."""
pass
nonlocal sent_notifications, delivered_notifications"""
notification_id = "formatted_string"
sent_notifications += 1

    # Store notification in memory (MEMORY LEAK!)
notification_history[notification_id] = { )
"user_id": user_id,
"data": notification_data,
"timestamp": time.time(),
"delivery_attempts": [],
"metadata": { )
"created_at": datetime.now(),
"user_agent": "test_client",
"ip_address": "formatted_string",
"session_context": { )
"session_id": "formatted_string",
"user_preferences": {"theme": "dark", "lang": "en"},
"cached_data": ["x"] * 100  # More memory usage
    
    
    

    # Store user context (MEMORY LEAK!)
if user_id not in user_contexts:
user_contexts[user_id] = { )
"user_id": user_id,
"notification_history": [],
"connection_metadata": { )
"connected_at": time.time(),
"user_agent": "WebSocket Client",
"cached_responses": {}
        
        

user_contexts[user_id]["notification_history"].append(notification_id)
user_contexts[user_id]["connection_metadata"]["cached_responses"][notification_id] = notification_data

        # Add to pending deliveries (MEMORY LEAK!)
pending_deliveries[notification_id] = { )
"notification": notification_data,
"user_context": user_contexts[user_id],
"retry_count": 0,
"delivery_queue": [notification_data] * 5  # Duplicate storage!
        

        # Simulate delivery delay
await asyncio.sleep(random.uniform(0.001, 0.01))

delivered_notifications += 1

        # Don't clean up memory! (The bug)
        Should remove from pending_deliveries but doesn't

await asyncio.sleep(0)
return True

        # Run sustained load test
start_time = time.time()
while time.time() - start_time < duration_seconds:
            # Generate notifications for random users
user_id = "formatted_string"

notification_data = {"type": "tool_update",, "content": "formatted_string",, "timestamp": time.time(),, "large_data": ["x"] * 1000  # Add bulk data}
task = asyncio.create_task(leaky_notification_system(user_id, notification_data))
tasks.append(task)

            # Wait to maintain desired rate
await asyncio.sleep(1.0 / notifications_per_second)

            # Wait for all notifications to complete
await asyncio.gather(*tasks)

end_time = time.time()

            # Generate test result
load_test_result = performance_monitor.get_load_test_result( )
test_name, start_time, end_time, 10, sent_notifications, delivered_notifications
            

            # Verify memory leak occurred
assert load_test_result.memory_leaked_mb > 10, "formatted_string"

            # Check memory growth pattern
memory_metrics = [item for item in []]
if len(memory_metrics) > 10:
early_memory = statistics.mean(m.value for m in memory_metrics[:5])
late_memory = statistics.mean(m.value for m in memory_metrics[-5:])
memory_growth = late_memory - early_memory

assert memory_growth > 5, "formatted_string"

                # Verify data structures are leaking
notification_count = len(notification_history)
user_context_count = len(user_contexts)
pending_count = len(pending_deliveries)

assert notification_count > 100, "formatted_string"
assert pending_count > 50, "formatted_string"

                # Check for memory violation
memory_violations = [item for item in []]
assert len(memory_violations) > 0, "Expected memory leak violation"

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.slow
    async def test_connection_instability_under_load(self, performance_monitor):
"""CRITICAL: Test WebSocket connection instability under high load."""
                    # This test SHOULD FAIL initially"""
test_name = "connection_instability_load"
max_concurrent_connections = 100
connection_churn_rate = 0.1  # 10% connections drop/reconnect per second
test_duration_seconds = 20

                    # Simulate unstable connection pool
connection_pool = {}
connection_health = {}  # Track connection health
dropped_connections = 0
reconnection_attempts = 0

sent_notifications = 0
delivered_notifications = 0
failed_deliveries = 0

async def unstable_websocket_connection(user_id: str, connection_id: str):
"""Simulate unstable WebSocket connection."""
pass
nonlocal dropped_connections, reconnection_attempts

    # Create connection with random stability
connection_stability = random.uniform(0.7, 1.0)  # 70-100% stability"""
"user_id": user_id,
"created_at": time.time(),
"stability": connection_stability,
"message_count": 0,
"last_activity": time.time()
    
connection_health[connection_id] = True

try:
        # Connection lifetime affected by stability
max_lifetime = connection_stability * 30  # Max 30 seconds for stable connections
connection_start = time.time()

while (time.time() - connection_start) < max_lifetime:
            # Random chance of connection dropping
if random.random() < (1 - connection_stability) * 0.1:
                # Connection dropped!
connection_health[connection_id] = False
dropped_connections += 1
performance_monitor.record_metric("error_connection_dropped", 1, user_id)
break

                # Update last activity
connection_pool[connection_id]["last_activity"] = time.time()

await asyncio.sleep(0.1)

except Exception as e:
connection_health[connection_id] = False
performance_monitor.record_metric("error_connection_exception", 1, user_id)
finally:
                        # Clean up connection
if connection_id in connection_pool:
del connection_pool[connection_id]
if connection_id in connection_health:
del connection_health[connection_id]

async def send_notification_to_unstable_connection(user_id: str, notification: Dict[str, Any]):
"""Send notification to potentially unstable connection."""
nonlocal sent_notifications, delivered_notifications, failed_deliveries

sent_notifications += 1

    # Find user's connection
user_connections = [ )"""
if conn_data["user_id"] == user_id
    

if not user_connections:
        # No connection available
failed_deliveries += 1
performance_monitor.record_metric("error_no_connection", 1, user_id)
await asyncio.sleep(0)
return False

connection_id = user_connections[0]

        # Check connection health
if not connection_health.get(connection_id, False):
            # Connection is unhealthy
failed_deliveries += 1
performance_monitor.record_metric("error_unhealthy_connection", 1, user_id)
return False

try:
                # Simulate sending notification
delivery_start = time.time()

                # Delivery may fail due to connection instability
connection_stability = connection_pool[connection_id]["stability"]
if random.random() > connection_stability:
                    # Delivery failed due to instability
failed_deliveries += 1
performance_monitor.record_metric("error_delivery_failed_instability", 1, user_id)
return False

                    # Simulate network delay
network_delay = (1 - connection_stability) * 0.1  # Up to 100ms delay for unstable connections
await asyncio.sleep(network_delay)

                    # Update connection activity
connection_pool[connection_id]["message_count"] += 1
connection_pool[connection_id]["last_activity"] = time.time()

delivery_end = time.time()
delivered_notifications += 1
performance_monitor.record_metric("notification_delivery_time_ms", delivery_time_ms, user_id)

return True

except Exception as e:
failed_deliveries += 1
performance_monitor.record_metric("error_send_exception", 1, user_id)
return False

                        # Start test
start_time = time.time()

                        # Create initial connections
connection_tasks = []
for i in range(max_concurrent_connections):
user_id = "formatted_string"  # 20 users with multiple connections each
connection_id = "formatted_string"

connection_task = asyncio.create_task( )
unstable_websocket_connection(user_id, connection_id)
                            
connection_tasks.append(connection_task)

                            # Send notifications during test period
notification_tasks = []

while time.time() - start_time < test_duration_seconds:
                                # Record current connection count
performance_monitor.record_metric("active_connections", len(connection_pool))

                                # Send notifications to random users
active_users = list(set( ))
conn_data["user_id"] for conn_data in connection_pool.values()
                                

if active_users:
target_user = random.choice(active_users)
notification = {"type": "tool_progress",, "content": "formatted_string",, "timestamp": time.time()}
notification_task = asyncio.create_task( )
send_notification_to_unstable_connection(target_user, notification)
                                    
notification_tasks.append(notification_task)

await asyncio.sleep(0.05)  # 20 notifications per second

                                    # Wait for remaining notifications
if notification_tasks:
await asyncio.gather(*notification_tasks, return_exceptions=True)

                                        # Cancel connection tasks
for task in connection_tasks:
task.cancel()

end_time = time.time()

                                            # Generate test result
load_test_result = performance_monitor.get_load_test_result( )
test_name, start_time, end_time, 20, sent_notifications, delivered_notifications
                                            

                                            # Verify connection instability caused issues
assert dropped_connections > 5, "formatted_string"
assert failed_deliveries > 10, "formatted_string"

                                            # Check delivery success rate
success_rate = delivered_notifications / sent_notifications if sent_notifications > 0 else 0
assert success_rate < 0.9, "formatted_string"

                                            # Verify performance violations
notification_loss_violations = [item for item in []]
assert len(notification_loss_violations) > 0, "Expected notification loss violations"

                                            # Check error metrics
total_errors = sum(performance_monitor.error_counts.values())
assert total_errors > 20, "formatted_string"


class TestConcurrentUserPerformance:
        """Test performance under concurrent user scenarios."""

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.slow"""
"""CRITICAL: Test thread pool exhaustion during notification bursts."""
        # This test SHOULD FAIL initially"""
test_name = "thread_pool_exhaustion"
max_threads = 20  # Limited thread pool
burst_size = 100  # More tasks than threads
burst_interval = 0.1  # 100ms between bursts

        # Simulate limited thread pool
thread_pool = ThreadPoolExecutor(max_workers=max_threads)
active_tasks = set()
queued_tasks = []

sent_notifications = 0
delivered_notifications = 0
thread_exhaustion_errors = 0

def blocking_notification_processing(user_id: str, notification_data: Dict[str, Any]) -> Tuple[bool, float]:
"""CPU-intensive notification processing that blocks threads."""
pass
start_time = time.time()

    # Simulate CPU-intensive work (blocking operation)"""
for i in range(10000):  # CPU work that can"t be awaited
result_data.append("formatted_string")

    # Simulate I/O delay
time.sleep(random.uniform(0.01, 0.05))

end_time = time.time()
await asyncio.sleep(0)
return True, processing_time_ms

async def send_notification_with_thread_pool(user_id: str, notification_data: Dict[str, Any]):
"""Send notification using thread pool."""
nonlocal sent_notifications, delivered_notifications, thread_exhaustion_errors

sent_notifications += 1

try:
        # Submit to thread pool (may block if pool is exhausted)
loop = asyncio.get_event_loop()
thread_pool,
blocking_notification_processing,
user_id,
notification_data
        

        # Wait for processing with timeout
success, processing_time = await asyncio.wait_for(future, timeout=5.0)

if success:
delivered_notifications += 1"""
"notification_processing_time_ms",
processing_time,
user_id
            

await asyncio.sleep(0)
return success

except asyncio.TimeoutError:
                # Thread pool task timed out (thread exhaustion!)
thread_exhaustion_errors += 1
performance_monitor.record_metric("error_thread_exhaustion_timeout", 1, user_id)
return False

except Exception as e:
performance_monitor.record_metric("error_thread_pool_exception", 1, user_id)
return False

                    # Generate burst loads
start_time = time.time()

burst_tasks = []
for burst_num in range(5):  # 5 bursts
                    # Create burst of notifications
burst_start = time.time()

for i in range(burst_size):
user_id = "formatted_string"
notification_data = {"type": "tool_result",, "burst_num": burst_num,, "item_num": i,, "processing_required": True,, "timestamp": time.time()}
task = asyncio.create_task( )
send_notification_with_thread_pool(user_id, notification_data)
                        
burst_tasks.append(task)

                        # Record thread pool utilization
performance_monitor.record_metric( )
"thread_pool_utilization",
len(active_tasks),
context={"burst_num": burst_num}
                        

                        # Wait between bursts
await asyncio.sleep(burst_interval)

                        # Wait for all burst processing to complete
results = await asyncio.gather(*burst_tasks, return_exceptions=True)

                        # Shutdown thread pool
thread_pool.shutdown(wait=True)

end_time = time.time()

                        # Generate test result
total_users = 10  # Users involved in bursts
load_test_result = performance_monitor.get_load_test_result( )
test_name, start_time, end_time, total_users, sent_notifications, delivered_notifications
                        

                        # Verify thread exhaustion occurred
assert thread_exhaustion_errors > 0, "formatted_string"

                        # Check processing time degradation
processing_metrics = [item for item in []]
if len(processing_metrics) > 10:
early_processing = statistics.mean(m.value for m in processing_metrics[:10])
late_processing = statistics.mean(m.value for m in processing_metrics[-10:])

                            # Processing should slow down due to thread contention
assert late_processing > early_processing * 1.5, "formatted_string"

                            # Check delivery success rate
success_rate = delivered_notifications / sent_notifications if sent_notifications > 0 else 0
assert success_rate < 0.8, "formatted_string"

                            # Verify timeout errors
timeout_errors = performance_monitor.error_counts.get("thread_exhaustion_timeout", 0)
assert timeout_errors > 10, "formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.slow
    async def test_notification_queue_overflow_under_high_volume(self, performance_monitor):
"""CRITICAL: Test notification queue overflow under high volume."""
pass
                                # This test SHOULD FAIL initially"""
test_name = "notification_queue_overflow"
max_queue_size = 200
notification_rate = 50  # 50 per second
slow_processing_rate = 10  # Only 10 per second processing
test_duration_seconds = 15

                                # Simulate notification queue with overflow
notification_queue = asyncio.Queue(maxsize=max_queue_size)

sent_notifications = 0
delivered_notifications = 0
queue_overflow_errors = 0

async def queue_processor():
"""Slow queue processor that can't keep up with incoming rate."""
nonlocal delivered_notifications

while True:
try:
            # Process at slow rate
user_id, notification_data, enqueue_time = await asyncio.wait_for( )
notification_queue.get(), timeout=1.0
            

            # Simulate slow processing
processing_delay = 1.0 / slow_processing_rate  # Processing bottleneck
await asyncio.sleep(processing_delay)

delivered_notifications += 1

            # Record queue processing metrics
processing_time_ms = (time.time() - enqueue_time) * 1000
queue_size = notification_queue.qsize()
"""
"queue_processing_time_ms",
processing_time_ms,
user_id
            

performance_monitor.record_metric( )
"notification_queue_size",
queue_size,
user_id
            

            # Mark task done
notification_queue.task_done()

except asyncio.TimeoutError:
break  # No more items to process
except Exception as e:
performance_monitor.record_metric("error_queue_processing", 1)

async def enqueue_notification(user_id: str, notification_data: Dict[str, Any]):
"""Enqueue notification for processing."""
pass
nonlocal sent_notifications, queue_overflow_errors

sent_notifications += 1
enqueue_time = time.time()

try:
        # Try to add to queue (may overflow!)
notification_queue.put_nowait((user_id, notification_data, enqueue_time))
await asyncio.sleep(0)
return True

except asyncio.QueueFull:
            # Queue overflow!"""
performance_monitor.record_metric("error_queue_overflow", 1, user_id)
return False
except Exception as e:
performance_monitor.record_metric("error_enqueue_exception", 1, user_id)
return False

                # Start queue processor
processor_task = asyncio.create_task(queue_processor())

                # Generate high-volume notifications
start_time = time.time()

enqueue_tasks = []
notification_interval = 1.0 / notification_rate

while time.time() - start_time < test_duration_seconds:
user_id = "formatted_string"
notification_data = {"type": "high_volume_update",, "sequence": sent_notifications,, "timestamp": time.time(),, "data": ["x"] * 100  # Some bulk data}
task = asyncio.create_task(enqueue_notification(user_id, notification_data))
enqueue_tasks.append(task)

await asyncio.sleep(notification_interval)

                    # Wait for enqueuing to complete
await asyncio.gather(*enqueue_tasks, return_exceptions=True)

                    # Wait a bit more for processing
await asyncio.sleep(2.0)

                    # Stop processor
processor_task.cancel()

end_time = time.time()

                    # Generate test result
total_users = 20
load_test_result = performance_monitor.get_load_test_result( )
test_name, start_time, end_time, total_users, sent_notifications, delivered_notifications
                    

                    # Verify queue overflow occurred
assert queue_overflow_errors > 0, "formatted_string"

                    # Check that queue reached capacity
max_queue_size_observed = max( )
(m.value for m in performance_monitor.metrics if m.metric_name == "notification_queue_size"),
default=0
                    
assert max_queue_size_observed >= max_queue_size * 0.8, "formatted_string"

                    # Verify processing couldn't keep up with input rate
expected_deliveries = slow_processing_rate * test_duration_seconds
assert delivered_notifications <= expected_deliveries * 1.2, "formatted_string"

                    # Check for significant notification loss
notifications_lost = sent_notifications - delivered_notifications
loss_percentage = notifications_lost / sent_notifications if sent_notifications > 0 else 0

assert loss_percentage > 0.3, "formatted_string"

                    # Verify overflow violations
overflow_violations = [item for item in []]
assert len(overflow_violations) > 0, "Expected overflow/loss violations"


if __name__ == "__main__":
                        # Run the test suite
pytest.main([__file__, "-v", "--tb=short", "-m", "critical"])
