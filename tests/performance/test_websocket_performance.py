class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure):"
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        '''
        WebSocket Performance Tests

        Business Value:
        - Validates system can handle 10+ concurrent users
        - Tests WebSocket throughput and latency
        - Ensures connection pool scales properly
        - Detects memory leaks and resource issues
        '''
        '''

        import asyncio
        import json
        import pytest
        import time
        import statistics
        import psutil
        import gc
        from concurrent.futures import ThreadPoolExecutor
        from datetime import datetime, timezone
        import uuid
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.services.websocket_bridge_factory import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        WebSocketConnectionPool
        


class TestWebSocketPerformance:
        """Performance tests for WebSocket system."""

        @pytest.fixture
    def factory(self):
        """Create WebSocket factory."""
        return WebSocketBridgeFactory()

        @pytest.fixture
    def mock_websockets(self, count=10):
        """Create multiple mock WebSockets."""
        pass
        websockets = []
        for _ in range(count):
        ws = Magic            ws.websocket = TestWebSocketConnection()
        ws.state = Magic            ws.state.name = "OPEN"
        websockets.append(ws)
        return websockets

@pytest.mark.asyncio
    async def test_concurrent_user_connections(self, factory):
        """Test system handles 10+ concurrent user connections."""
num_users = 15
users = []

            # Create concurrent user connections
tasks = []
for i in range(num_users):
    user_id = ""
session_id = ""

ws = Magic            ws.websocket = TestWebSocketConnection()
ws.state = Magic            ws.state.name = "OPEN"

task = factory.create_user_emitter( )
user_id=user_id,
session_id=session_id,
websocket=ws
                
tasks.append(task)
users.append((user_id, ws))

                # Create all emitters concurrently
start_time = time.time()
emitters = await asyncio.gather(*tasks)
creation_time = time.time() - start_time

                # Verify all emitters created
assert len(emitters) == num_users
assert creation_time < 5  # Should complete within 5 seconds

                # Verify pool has all connections
pool = factory.connection_pool
assert pool.total_connections == num_users

                # Send events to all users concurrently
send_tasks = []
for emitter in emitters:
    event = {"type": "test", "data": {"user: emitter.user_id}}"
send_tasks.append(emitter.emit(event))

start_time = time.time()
await asyncio.gather(*send_tasks)
send_time = time.time() - start_time

                    # Should complete quickly
assert send_time < 2  # 2 seconds for 15 users

                    # Verify all WebSockets received events
for _, ws in users:
    ws.send.assert_called()

@pytest.mark.asyncio
    async def test_event_throughput(self, factory):
        """Test WebSocket event throughput rate."""
pass
user_id = "perf-user"
num_events = 1000

                            # Create emitter with WebSocket
ws = Magic        ws.websocket = TestWebSocketConnection()
ws.state = Magic        ws.state.name = "OPEN"

emitter = await factory.create_user_emitter( )
user_id=user_id,
session_id="perf-session,"
websocket=ws
                            

                            # Send many events
events = [ ]
{"type": "", "data": {"index: i}}"
for i in range(num_events)
                            

start_time = time.time()

                            # Send all events
for event in events:
    await emitter.emit(event)

elapsed_time = time.time() - start_time
throughput = num_events / elapsed_time

                                # Should handle at least 100 events/second
assert throughput > 100

                                # Verify all events sent
assert ws.send.call_count == num_events

print("")

@pytest.mark.asyncio
    async def test_connection_pool_scaling(self, factory):
        """Test connection pool scales with users."""
pool = factory.connection_pool
measurements = []

for num_users in [5, 10, 20, 30]:
                                        # Add connections
connections = []
start_time = time.time()

for i in range(num_users):
    ws = Magic                ws.websocket = TestWebSocketConnection()
ws.state = Magic                ws.state.name = "OPEN"

conn_id = await pool.add_connection("", ws)
connections.append(conn_id)

add_time = time.time() - start_time

                                            # Broadcast to all users
start_time = time.time()

for i in range(num_users):
    await pool.broadcast_to_user("", {"type": "test})"

broadcast_time = time.time() - start_time

measurements.append({ })
"users: num_users,"
"add_time: add_time,"
"broadcast_time: broadcast_time,"
"avg_add: add_time / num_users,"
"avg_broadcast: broadcast_time / num_users"
                                                

                                                # Cleanup for next iteration
for conn_id in connections:
    await pool.remove_connection(conn_id)

                                                    # Verify scaling is reasonable (not exponential)
for i in range(1, len(measurements)):
    prev = measurements[i-1]
curr = measurements[i]

                                                        # Average times shouldn't increase dramatically'
scaling_factor = curr["avg_add"] / prev["avg_add]"
assert scaling_factor < 2  # Less than 2x increase

@pytest.mark.asyncio
    async def test_memory_usage_under_load(self, factory):
        """Test memory usage with many connections and events."""
pass
process = psutil.Process()
initial_memory = process.memory_info().rss / 1024 / 1024  # MB

num_users = 20
events_per_user = 100

                                                            # Create many user connections
emitters = []
for i in range(num_users):
    ws = Magic            ws.websocket = TestWebSocketConnection()
ws.state = Magic            ws.state.name = "OPEN"

emitter = await factory.create_user_emitter( )
user_id="",
session_id="",
websocket=ws
                                                                
emitters.append(emitter)

                                                                # Send many events
for emitter in emitters:
    for j in range(events_per_user):
        await emitter.emit({"type": "", "data": {"index: j}})"

                                                                        # Check memory after load
gc.collect()  # Force garbage collection
final_memory = process.memory_info().rss / 1024 / 1024  # MB
memory_increase = final_memory - initial_memory

                                                                        # Memory increase should be reasonable
assert memory_increase < 100  # Less than 100MB increase

                                                                        # Cleanup
for i in range(num_users):
    await factory.remove_user_emitter("")

                                                                            # Memory should be released
gc.collect()
cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB

                                                                            # Most memory should be released
assert cleanup_memory - initial_memory < 50  # Less than 50MB retained

@pytest.mark.asyncio
    async def test_event_latency(self, factory):
        """Test event delivery latency."""
user_id = "latency-user"
num_samples = 100
latencies = []

                                                                                # Create emitter
ws = MagicMock()
                                                                                # Track send times
send_times = []
async def mock_send(data):
    send_times.append(time.time())

ws.send = mock_send
ws.state = Magic        ws.state.name = "OPEN"

emitter = await factory.create_user_emitter( )
user_id=user_id,
session_id="latency-session,"
websocket=ws
    

    # Measure latency for each event
for i in range(num_samples):
    event = {"type": "", "data": {"index: i}}"

start_time = time.time()
await emitter.emit(event)

if send_times:
    latency = send_times[-1] - start_time
latencies.append(latency * 1000)  # Convert to ms

            # Calculate statistics
if latencies:
    avg_latency = statistics.mean(latencies)
median_latency = statistics.median(latencies)
p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

                # Latency should be low
assert avg_latency < 10  # Average < 10ms
assert median_latency < 5  # Median < 5ms
assert p95_latency < 50  # 95th percentile < 50ms

print("")

@pytest.mark.asyncio
    async def test_queue_performance(self, factory):
        """Test event queue performance under load."""
pass
user_id = "queue-user"
queue_sizes = [100, 500, 1000]

for queue_size in queue_sizes:
                        # Create emitter without WebSocket (forces queueing)
emitter = await factory.create_user_emitter( )
user_id=user_id,
session_id="queue-session"
                        

emitter.max_queue_size = queue_size * 2  # Ensure no overflow

                        # Queue many events
start_time = time.time()

for i in range(queue_size):
    emitter.queue_event({"type": "", "data": {"index: i}})"

queue_time = time.time() - start_time

                            # Add WebSocket
ws = Magic            ws.websocket = TestWebSocketConnection()
ws.state = Magic            ws.state.name = "OPEN"

await emitter.add_connection(ws)

                            # Flush queue
start_time = time.time()
flushed = await emitter.flush_queue()
flush_time = time.time() - start_time

assert flushed == queue_size

                            # Performance should be good
queue_rate = queue_size / queue_time
flush_rate = queue_size / flush_time

assert queue_rate > 1000  # > 1000 events/second queueing
assert flush_rate > 100   # > 100 events/second flushing

                            # Cleanup
await factory.remove_user_emitter(user_id)

@pytest.mark.asyncio
    async def test_concurrent_broadcasts(self, factory):
        """Test concurrent broadcasts to multiple users."""
num_users = 10
broadcasts_per_user = 50

                                # Create users
users = []
for i in range(num_users):
    ws = Magic            ws.websocket = TestWebSocketConnection()
ws.state = Magic            ws.state.name = "OPEN"

emitter = await factory.create_user_emitter( )
user_id="",
session_id="",
websocket=ws
                                    
users.append(("", emitter, ws))

                                    # Broadcast concurrently
start_time = time.time()

async def broadcast_to_user(user_id, emitter, count):
    for i in range(count):
        await emitter.emit({"type": "", "data": {"user: user_id}})"

tasks = [ ]
broadcast_to_user(user_id, emitter, broadcasts_per_user)
for user_id, emitter, _ in users
        

await asyncio.gather(*tasks)

elapsed_time = time.time() - start_time
total_broadcasts = num_users * broadcasts_per_user
broadcast_rate = total_broadcasts / elapsed_time

        # Should handle many concurrent broadcasts
assert broadcast_rate > 100  # > 100 broadcasts/second

        # Verify all broadcasts sent
for _, _, ws in users:
    assert ws.send.call_count == broadcasts_per_user

@pytest.mark.asyncio
    async def test_connection_cleanup_performance(self, factory):
        """Test performance of connection cleanup."""
pass
pool = factory.connection_pool
num_connections = 100

                # Add many connections
connections = []
for i in range(num_connections):
    ws = Magic            ws.websocket = TestWebSocketConnection()
ws.state = Magic            ws.state.name = "OPEN" if i % 2 == 0 else "CLOSED"

conn_id = await pool.add_connection("", ws)
connections.append((conn_id, ws))

                    # Mark half as inactive
for i, (conn_id, _) in enumerate(connections):
    if i % 2 == 1:
        pool.connections[conn_id].is_active = False

                            # Cleanup inactive connections
start_time = time.time()
removed = await pool.cleanup_inactive_connections()
cleanup_time = time.time() - start_time

assert removed == num_connections // 2
assert cleanup_time < 1  # Should complete within 1 second

                            # Verify correct connections removed
for i, (conn_id, ws) in enumerate(connections):
    if i % 2 == 1:
        assert conn_id not in pool.connections
ws.close.assert_called()
else:
    assert conn_id in pool.connections

@pytest.mark.asyncio
    async def test_stress_test_sustained_load(self, factory):
        """Test system under sustained load for extended period."""
num_users = 5
duration_seconds = 10
events_per_second = 10

                                            # Create users
emitters = []
websockets = []

for i in range(num_users):
    ws = Magic            ws.websocket = TestWebSocketConnection()
ws.state = Magic            ws.state.name = "OPEN"
websockets.append(ws)

emitter = await factory.create_user_emitter( )
user_id="",
session_id="",
websocket=ws
                                                
emitters.append(emitter)

                                                # Send events continuously
start_time = time.time()
event_count = 0
errors = 0

while time.time() - start_time < duration_seconds:
                                                    # Send events to all users
tasks = []
for emitter in emitters:
    event = { }
"type": "stress_test,"
"data: { }"
"timestamp: time.time(),"
"count: event_count"
                                                        
                                                        
tasks.append(emitter.emit(event))

                                                        # Send batch
results = await asyncio.gather(*tasks, return_exceptions=True)

                                                        # Count errors
for result in results:
    if isinstance(result, Exception):
        errors += 1
else:
    event_count += 1

                                                                    # Rate limit
await asyncio.sleep(1 / events_per_second)

                                                                    # System should remain stable
error_rate = errors / (errors + event_count) if (errors + event_count) > 0 else 0
assert error_rate < 0.1  # Less than 1% error rate

                                                                    # Verify events were sent
for ws in websockets:
    assert ws.send.call_count > 0

print("")
pass
