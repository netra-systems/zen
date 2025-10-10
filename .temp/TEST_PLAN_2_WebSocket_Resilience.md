# Test Plan 2: WebSocket Communication Resilience Testing
**File Under Test:** `scripts/agent_cli.py`
**Class Under Test:** `WebSocketClient`
**Lines:** 2591-3900
**Date:** 2025-10-10

## Executive Summary
The WebSocket implementation in `agent_cli.py` is the **most critical SPOF (Single Point of Failure)** in the entire system. ALL agent-backend communication flows through a single WebSocket connection. Historical bugs related to timing and thread IDs (as evidenced in test files) indicate this is a **high-risk, fear-inducing area** that requires comprehensive resilience testing.

## Why This Is the System's SPOF

### Impact Analysis: If WebSocket Goes Offline

**Immediate Failures:**
- ✗ All message sending fails (agent_cli.py:3476)
- ✗ All event receiving fails (agent_cli.py:3804)
- ✗ Authentication becomes impossible (agent_cli.py:2842-2988)
- ✗ Timeout coordination breaks (agent_cli.py:2693-2707)
- ✗ Thread ID management fails (agent_cli.py:2633)
- ✗ Telemetry collection stops
- ✗ Log aggregation halts
- ✗ ALL running agents timeout

**System-Wide Impact:**
- 100% of user requests fail
- No redundancy or failover
- No connection pooling
- No message queuing
- Complete operational halt

**Business Impact:**
- Total service outage
- All customer workflows blocked
- SLA violations
- Revenue loss

## Why This Code Is Fear-Inducing to Modify

### Historical Context
1. **Multiple timeout-related bugs:** Issues #2442, #2662, #2861, #2373
2. **Environment-specific behavior:** Different timeouts for STAGING (300s), PRODUCTION (120s), LOCAL (10s)
3. **Complex fallback chain:** Backend SSOT → Fallback timeouts → Negotiated timeouts → Defaults
4. **Cross-module dependencies:** Imports from `netra_backend.app.core.timeout_configuration`
5. **Thread ID coordination complexity:** Backend SSOT vs legacy behavior
6. **Multiple authentication methods:** Subprotocol, query parameter, header-based

### Risk Factors
- **High complexity:** 1300+ lines of WebSocket handling code
- **Timing-sensitive:** Race conditions in connect/send/receive
- **Environment-dependent:** Behavior varies by deployment
- **Limited testing:** Historical bugs suggest inadequate test coverage
- **Async complexity:** Concurrent operations and event loops
- **Stateful behavior:** Connection state, negotiated timeouts, thread IDs

## Test Categories

### 1. Connection Handshake Tests

#### 1.1 Authentication Method Tests
```python
@pytest.mark.asyncio
async def test_subprotocol_authentication_success():
    """Test successful authentication via subprotocol"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="valid_token")

    with patch('websockets.connect') as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws

        result = await client.connect()

        assert result is True
        mock_connect.assert_called_once()
        call_kwargs = mock_connect.call_args[1]
        assert 'subprotocols' in call_kwargs
        assert call_kwargs['close_timeout'] >= 10

@pytest.mark.asyncio
async def test_authentication_fallback_chain():
    """Test fallback through all authentication methods"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="valid_token")

    # Mock all three authentication methods to fail first two
    with patch.object(client, '_connect_with_subprotocol', return_value=False):
        with patch.object(client, '_connect_with_query_param', return_value=False):
            with patch.object(client, '_connect_with_header', return_value=True):
                result = await client.connect()

                assert result is True
                # All three methods should have been attempted

@pytest.mark.asyncio
async def test_all_authentication_methods_fail():
    """Test when all authentication methods fail"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="invalid_token")

    with patch.object(client, '_connect_with_subprotocol', return_value=False):
        with patch.object(client, '_connect_with_query_param', return_value=False):
            with patch.object(client, '_connect_with_header', return_value=False):
                result = await client.connect()

                assert result is False

@pytest.mark.asyncio
async def test_connection_timeout_during_handshake():
    """Test connection timeout during initial handshake"""
    config = Config(ws_url="ws://localhost:8000", environment=Environment.LOCAL)
    client = WebSocketClient(config, token="valid_token")

    with patch('websockets.connect', side_effect=asyncio.TimeoutError):
        result = await client.connect()
        assert result is False
```

#### 1.2 Close Timeout Coordination Tests
```python
@pytest.mark.asyncio
async def test_close_timeout_from_negotiated_timeout():
    """Test close timeout derived from negotiated timeout"""
    config = Config(environment=Environment.STAGING)
    client = WebSocketClient(config, token="token")
    client.negotiated_timeout = 100

    close_timeout = client._get_close_timeout()

    # Should be negotiated + 2s safety margin
    assert close_timeout == 102

@pytest.mark.asyncio
async def test_close_timeout_from_configured_timeout():
    """Test close timeout from backend configuration"""
    config = Config(environment=Environment.STAGING)
    client = WebSocketClient(config, token="token")
    client.close_timeout = 302

    close_timeout = client._get_close_timeout()

    assert close_timeout == 302

@pytest.mark.asyncio
async def test_close_timeout_fallback_default():
    """Test close timeout fallback to default"""
    config = Config(environment=Environment.LOCAL)
    client = WebSocketClient(config, token="token")
    client.negotiated_timeout = None
    client.close_timeout = None

    close_timeout = client._get_close_timeout()

    assert close_timeout == 10  # Default
```

#### 1.3 Max Message Size Tests
```python
@pytest.mark.asyncio
async def test_max_message_size_enforcement():
    """Test 5MB max message size is enforced"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="valid_token")

    with patch('websockets.connect') as mock_connect:
        await client.connect()

        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs['max_size'] == 5 * 1024 * 1024  # 5 MB

@pytest.mark.asyncio
async def test_message_exceeds_max_size():
    """Test sending message that exceeds max size"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="valid_token")

    # Create oversized message (>5MB)
    large_message = "x" * (6 * 1024 * 1024)

    with pytest.raises(Exception):  # Should raise size error
        await client.send_message(large_message)
```

### 2. Message Sending Tests

#### 2.1 Payload Serialization Tests
```python
@pytest.mark.asyncio
async def test_send_message_valid_json():
    """Test sending valid JSON message"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    client.ws = AsyncMock()

    run_id = await client.send_message("Test message")

    assert run_id is not None
    assert UUID(run_id)  # Valid UUID format
    client.ws.send.assert_called_once()

@pytest.mark.asyncio
async def test_send_message_special_characters():
    """Test sending message with special characters"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    client.ws = AsyncMock()

    message = "Test with 特殊字符 and émojis 🎉"
    run_id = await client.send_message(message)

    assert run_id is not None

@pytest.mark.asyncio
async def test_send_message_without_connection():
    """Test sending message when not connected"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    client.ws = None

    with pytest.raises(RuntimeError, match="WebSocket not connected"):
        await client.send_message("Test")

@pytest.mark.asyncio
async def test_concurrent_message_sending():
    """Test sending multiple messages concurrently"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    client.ws = AsyncMock()

    # Send 10 messages concurrently
    tasks = [client.send_message(f"Message {i}") for i in range(10)]
    run_ids = await asyncio.gather(*tasks)

    assert len(run_ids) == 10
    assert len(set(run_ids)) == 10  # All unique
```

#### 2.2 Thread ID Coordination Tests
```python
@pytest.mark.asyncio
async def test_thread_id_from_backend():
    """Test thread ID obtained from backend"""
    config = Config(use_backend_threads=True)
    client = WebSocketClient(config, token="token")
    client.ws = AsyncMock()

    with patch('agent_cli.get_thread_id', return_value="backend-thread-123"):
        run_id = await client.send_message("Test")

        # Verify backend thread ID was used
        sent_payload = json.loads(client.ws.send.call_args[0][0])
        assert sent_payload['thread_id'] == "backend-thread-123"

@pytest.mark.asyncio
async def test_thread_id_legacy_mode():
    """Test thread ID in legacy mode (no backend)"""
    config = Config(use_backend_threads=False)
    client = WebSocketClient(config, token="token")
    client.ws = AsyncMock()

    run_id = await client.send_message("Test")

    sent_payload = json.loads(client.ws.send.call_args[0][0])
    # Should still have a thread ID (generated locally)
    assert 'thread_id' in sent_payload
```

### 3. Event Receiving Tests

#### 3.1 Event Deserialization Tests
```python
@pytest.mark.asyncio
async def test_receive_valid_event():
    """Test receiving and parsing valid event"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = iter([
        json.dumps({"type": "test", "data": {"key": "value"}})
    ])
    client.ws = mock_ws

    events = []
    async def callback(event):
        events.append(event)

    await client.receive_events(callback)

    assert len(events) == 1
    assert events[0]['type'] == 'test'

@pytest.mark.asyncio
async def test_receive_malformed_json():
    """Test receiving malformed JSON event"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = iter([
        "{invalid json}",
        json.dumps({"type": "valid", "data": {}})
    ])
    client.ws = mock_ws

    events = []
    async def callback(event):
        events.append(event)

    await client.receive_events(callback)

    # Should skip malformed and process valid
    assert len(events) == 1
    assert events[0]['type'] == 'valid'

@pytest.mark.asyncio
async def test_receive_incomplete_message():
    """Test receiving incomplete/truncated message"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = iter([
        '{"type": "incomplete", "data": {"key":'  # Incomplete JSON
    ])
    client.ws = mock_ws

    events = []
    async def callback(event):
        events.append(event)

    # Should handle gracefully without crashing
    await client.receive_events(callback)
    assert len(events) == 0

@pytest.mark.asyncio
async def test_receive_events_without_connection():
    """Test receiving events when not connected"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    client.ws = None

    with pytest.raises(RuntimeError, match="WebSocket not connected"):
        await client.receive_events()
```

#### 3.2 Event Ordering Tests
```python
@pytest.mark.asyncio
async def test_event_ordering_preserved():
    """Test that events are received in correct order"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    events_sequence = [
        json.dumps({"type": "event", "seq": i})
        for i in range(100)
    ]

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = iter(events_sequence)
    client.ws = mock_ws

    received = []
    async def callback(event):
        received.append(event['seq'])

    await client.receive_events(callback)

    # Verify order preserved
    assert received == list(range(100))
```

### 4. Timeout Coordination Tests

#### 4.1 Environment-Specific Timeout Tests
```python
@pytest.mark.asyncio
async def test_staging_timeout_configuration():
    """Test STAGING environment timeout values"""
    config = Config(environment=Environment.STAGING)
    client = WebSocketClient(config, token="token")

    assert client.websocket_recv_timeout == 300
    assert client.close_timeout == 302

@pytest.mark.asyncio
async def test_production_timeout_configuration():
    """Test PRODUCTION environment timeout values"""
    config = Config(environment=Environment.PRODUCTION)
    client = WebSocketClient(config, token="token")

    assert client.websocket_recv_timeout == 120
    assert client.close_timeout == 122

@pytest.mark.asyncio
async def test_local_timeout_configuration():
    """Test LOCAL environment timeout values"""
    config = Config(environment=Environment.LOCAL)
    client = WebSocketClient(config, token="token")

    assert client.websocket_recv_timeout == 10
    assert client.close_timeout == 12

@pytest.mark.asyncio
async def test_timeout_backend_ssot_override():
    """Test backend SSOT overrides fallback timeouts"""
    config = Config(environment=Environment.STAGING, client_environment="test")
    client = WebSocketClient(config, token="token")

    # Mock backend timeout configuration
    with patch('agent_cli.get_websocket_recv_timeout', return_value=150):
        client._initialize_timeouts()

        # Should use backend value, not fallback
        assert client.websocket_recv_timeout == 150
        assert client.close_timeout == 152  # +2s safety
```

#### 4.2 Timeout Validation Tests
```python
@pytest.mark.asyncio
async def test_timeout_validation_passes():
    """Test timeout validation when configuration is valid"""
    config = Config(environment=Environment.PRODUCTION)
    client = WebSocketClient(config, token="token")

    with patch('agent_cli.get_agent_execution_timeout', return_value=100):
        result = await client._validate_timeout_configuration()

        # websocket_timeout (120) > agent_timeout (100) - VALID
        assert result is True

@pytest.mark.asyncio
async def test_timeout_validation_fails():
    """Test timeout validation when websocket timeout is too short"""
    config = Config(environment=Environment.LOCAL)
    client = WebSocketClient(config, token="token")
    client.websocket_recv_timeout = 5  # Very short

    with patch('agent_cli.get_agent_execution_timeout', return_value=100):
        result = await client._validate_timeout_configuration()

        # websocket_timeout (5) < agent_timeout (100) - INVALID
        assert result is False

@pytest.mark.asyncio
async def test_timeout_validation_skip():
    """Test timeout validation skip when requested"""
    config = Config(environment=Environment.LOCAL)
    client = WebSocketClient(config, token="token")

    result = await client._validate_timeout_configuration(skip=True)

    assert result is True  # Always passes when skipped
```

### 5. Network Condition Simulation Tests

#### 5.1 Latency Simulation
```python
@pytest.mark.asyncio
@pytest.mark.parametrize("latency_ms", [10, 50, 100, 500, 1000, 2000])
async def test_various_latency_levels(latency_ms):
    """Test WebSocket behavior under various latency conditions"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    async def delayed_send(data):
        await asyncio.sleep(latency_ms / 1000)
        return None

    mock_ws = AsyncMock()
    mock_ws.send = delayed_send
    client.ws = mock_ws

    start = time.time()
    await client.send_message("Test message")
    duration = time.time() - start

    # Should complete despite latency
    assert duration >= latency_ms / 1000

@pytest.mark.asyncio
async def test_high_latency_timeout():
    """Test that high latency triggers timeout"""
    config = Config(environment=Environment.LOCAL)  # 10s timeout
    client = WebSocketClient(config, token="token")

    async def very_slow_send(data):
        await asyncio.sleep(15)  # Exceeds timeout

    mock_ws = AsyncMock()
    mock_ws.send = very_slow_send
    client.ws = mock_ws

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            client.send_message("Test"),
            timeout=client.websocket_recv_timeout
        )
```

#### 5.2 Connection Drop Simulation
```python
@pytest.mark.asyncio
async def test_connection_drop_during_send():
    """Test connection dropping mid-send"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    async def send_then_disconnect(data):
        raise websockets.exceptions.ConnectionClosed(1006, "Connection lost")

    mock_ws = AsyncMock()
    mock_ws.send = send_then_disconnect
    client.ws = mock_ws

    with pytest.raises(websockets.exceptions.ConnectionClosed):
        await client.send_message("Test")

@pytest.mark.asyncio
async def test_connection_drop_during_receive():
    """Test connection dropping mid-receive"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    async def receive_then_disconnect():
        yield json.dumps({"type": "event1", "data": {}})
        raise websockets.exceptions.ConnectionClosed(1006, "Connection lost")

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = receive_then_disconnect()
    client.ws = mock_ws

    events = []
    async def callback(event):
        events.append(event)

    with pytest.raises(websockets.exceptions.ConnectionClosed):
        await client.receive_events(callback)

    # Should have received first event before disconnect
    assert len(events) == 1

@pytest.mark.asyncio
async def test_connection_drop_at_handshake():
    """Test connection dropping during handshake"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    with patch('websockets.connect', side_effect=websockets.exceptions.ConnectionClosed(1006, "")):
        result = await client.connect()

        assert result is False
```

#### 5.3 Packet Loss Simulation
```python
@pytest.mark.asyncio
@pytest.mark.parametrize("loss_rate", [0.01, 0.05, 0.10, 0.25])
async def test_packet_loss_simulation(loss_rate):
    """Test behavior under various packet loss rates"""
    import random

    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    sent_messages = []
    async def lossy_send(data):
        sent_messages.append(data)
        if random.random() < loss_rate:
            raise websockets.exceptions.ConnectionClosed(1006, "Packet lost")

    mock_ws = AsyncMock()
    mock_ws.send = lossy_send
    client.ws = mock_ws

    successes = 0
    failures = 0

    for i in range(100):
        try:
            await client.send_message(f"Message {i}")
            successes += 1
        except websockets.exceptions.ConnectionClosed:
            failures += 1

    # Should have some failures proportional to loss rate
    expected_failures = 100 * loss_rate
    assert abs(failures - expected_failures) < 20  # Allow variance
```

#### 5.4 Bandwidth Throttling Simulation
```python
@pytest.mark.asyncio
@pytest.mark.parametrize("bandwidth_kbps", [56, 256, 1024])
async def test_bandwidth_throttling(bandwidth_kbps):
    """Test behavior under various bandwidth constraints"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    message_size = 10 * 1024  # 10 KB message
    message = "x" * message_size

    async def throttled_send(data):
        # Simulate bandwidth limit
        bytes_per_second = (bandwidth_kbps * 1024) / 8
        delay = len(data) / bytes_per_second
        await asyncio.sleep(delay)

    mock_ws = AsyncMock()
    mock_ws.send = throttled_send
    client.ws = mock_ws

    start = time.time()
    await client.send_message(message)
    duration = time.time() - start

    # Should take time proportional to bandwidth
    expected_duration = message_size / ((bandwidth_kbps * 1024) / 8)
    assert duration >= expected_duration * 0.9  # Allow 10% variance
```

#### 5.5 Jitter Simulation
```python
@pytest.mark.asyncio
async def test_network_jitter():
    """Test behavior with variable latency (jitter)"""
    import random

    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    async def jittery_send(data):
        # Random latency between 0-200ms
        latency = random.uniform(0, 0.2)
        await asyncio.sleep(latency)

    mock_ws = AsyncMock()
    mock_ws.send = jittery_send
    client.ws = mock_ws

    # Send multiple messages and measure variance
    durations = []
    for i in range(50):
        start = time.time()
        await client.send_message(f"Message {i}")
        durations.append(time.time() - start)

    # Should have high variance due to jitter
    import statistics
    stdev = statistics.stdev(durations)
    assert stdev > 0.05  # Significant variance
```

### 6. Race Condition Tests

#### 6.1 Concurrent Operation Tests
```python
@pytest.mark.asyncio
async def test_concurrent_connect_attempts():
    """Test multiple concurrent connect attempts"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    with patch('websockets.connect') as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws

        # Try to connect multiple times concurrently
        tasks = [client.connect() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle gracefully without crashes
        assert all(isinstance(r, (bool, Exception)) for r in results)

@pytest.mark.asyncio
async def test_send_during_disconnect():
    """Test sending message while disconnecting"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    client.ws = AsyncMock()

    async def slow_disconnect():
        await asyncio.sleep(0.1)
        client.ws = None

    # Start disconnect and immediately try to send
    disconnect_task = asyncio.create_task(slow_disconnect())
    send_task = asyncio.create_task(client.send_message("Test"))

    await asyncio.gather(disconnect_task, send_task, return_exceptions=True)

    # Should handle race condition gracefully

@pytest.mark.asyncio
async def test_multiple_close_calls():
    """Test calling close() multiple times"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    mock_ws = AsyncMock()
    client.ws = mock_ws

    # Close multiple times
    await client.close()
    await client.close()
    await client.close()

    # Should handle gracefully without errors

@pytest.mark.asyncio
async def test_timeout_during_close():
    """Test timeout occurring during close operation"""
    config = Config(environment=Environment.LOCAL)
    client = WebSocketClient(config, token="token")

    async def slow_close():
        await asyncio.sleep(20)  # Exceeds timeout

    mock_ws = AsyncMock()
    mock_ws.close = slow_close
    client.ws = mock_ws

    # Close should complete even if it takes too long
    await client.close()
```

### 7. Error Recovery Tests

#### 7.1 Reconnection Tests
```python
@pytest.mark.asyncio
async def test_reconnect_after_connection_lost():
    """Test reconnecting after connection is lost"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")

    # First connection succeeds
    with patch('websockets.connect') as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws

        assert await client.connect() is True

        # Simulate connection loss
        client.ws = None

        # Reconnect should succeed
        assert await client.connect() is True

@pytest.mark.asyncio
async def test_no_retry_on_auth_failure():
    """Test that authentication failures don't trigger retries"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="invalid_token")

    with patch('websockets.connect', side_effect=websockets.exceptions.InvalidStatusCode(401, "")):
        result = await client.connect()

        assert result is False
        # Should fail fast on auth errors
```

## Test Execution Strategy

### Test Infrastructure

#### WebSocket Test Server
```python
# tests/fixtures/websocket_server.py
import asyncio
import websockets

async def test_websocket_server(port=8000):
    """Simple WebSocket server for testing"""
    async def handler(websocket, path):
        try:
            async for message in websocket:
                # Echo back
                await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass

    async with websockets.serve(handler, "localhost", port):
        await asyncio.Future()  # Run forever

@pytest.fixture
async def websocket_server():
    """Fixture providing test WebSocket server"""
    server_task = asyncio.create_task(test_websocket_server())
    await asyncio.sleep(0.1)  # Let server start
    yield
    server_task.cancel()
```

#### Network Simulator
```python
# tests/fixtures/network_simulator.py
class NetworkSimulator:
    """Simulate various network conditions"""

    def __init__(self, latency_ms=0, packet_loss=0.0, bandwidth_kbps=None):
        self.latency_ms = latency_ms
        self.packet_loss = packet_loss
        self.bandwidth_kbps = bandwidth_kbps

    async def send_with_conditions(self, ws, data):
        """Send data with simulated network conditions"""
        # Simulate latency
        if self.latency_ms:
            await asyncio.sleep(self.latency_ms / 1000)

        # Simulate packet loss
        if random.random() < self.packet_loss:
            raise websockets.exceptions.ConnectionClosed(1006, "Packet lost")

        # Simulate bandwidth throttling
        if self.bandwidth_kbps:
            bytes_per_second = (self.bandwidth_kbps * 1024) / 8
            delay = len(data) / bytes_per_second
            await asyncio.sleep(delay)

        await ws.send(data)
```

### CI/CD Integration
```yaml
# .github/workflows/test_websocket_resilience.yml
name: WebSocket Resilience Tests

on: [push, pull_request]

jobs:
  test-resilience:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [LOCAL, STAGING, PRODUCTION]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pytest pytest-asyncio websockets
      - name: Run resilience tests
        run: |
          pytest tests/test_websocket_resilience.py \
            --environment=${{ matrix.environment }} \
            -v --tb=short
        env:
          TEST_ENVIRONMENT: ${{ matrix.environment }}
```

### Performance Benchmarks
```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_connection_establishment_speed(benchmark):
    """Benchmark connection establishment time"""
    config = Config(ws_url="ws://localhost:8000")

    async def setup_and_connect():
        client = WebSocketClient(config, token="token")
        await client.connect()
        await client.close()

    result = await benchmark(setup_and_connect)

    # Should complete in <100ms
    assert result < 0.1

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_message_throughput(benchmark):
    """Benchmark message sending throughput"""
    config = Config(ws_url="ws://localhost:8000")
    client = WebSocketClient(config, token="token")
    await client.connect()

    async def send_batch():
        for i in range(100):
            await client.send_message(f"Message {i}")

    result = await benchmark(send_batch)

    # Should handle 100 messages in <1s
    assert result < 1.0

    await client.close()
```

## Success Criteria

### Functional Requirements
- ✅ All authentication methods tested and functional
- ✅ Timeout coordination works across all environments
- ✅ Message sending/receiving handles errors gracefully
- ✅ Race conditions don't cause crashes or data corruption

### Performance Requirements
- ✅ Connection establishment: <100ms (LOCAL), <500ms (PRODUCTION)
- ✅ Message sending: <50ms per message
- ✅ Event receiving: <10ms processing time
- ✅ Handles 100 messages/second throughput

### Resilience Requirements
- ✅ Survives 10% packet loss without data loss
- ✅ Handles 2000ms latency without timeout (with appropriate config)
- ✅ Recovers from connection drops within 5 seconds
- ✅ No memory leaks after 10,000 messages

### Coverage Requirements
- ✅ Line coverage: >95% for WebSocketClient class
- ✅ Branch coverage: >90% for all timeout logic
- ✅ Integration tests with real WebSocket server

## Risk Mitigation

### High-Risk Code Sections

**Most Dangerous to Modify:**
1. **`_initialize_timeouts()` (lines 2627-2691)**: Environment-specific timeout logic
   - Mitigation: Comprehensive timeout tests for each environment
   - Mitigation: Integration tests with backend SSOT
   - Mitigation: Canary deployments for timeout changes

2. **`_get_close_timeout()` (lines 2693-2707)**: Timeout precedence logic
   - Mitigation: Test all precedence combinations
   - Mitigation: Document fallback chain clearly
   - Mitigation: Add runtime validation

3. **`connect()` (lines 2842-2988)**: Authentication fallback chain
   - Mitigation: Test each auth method independently
   - Mitigation: Test all failure combinations
   - Mitigation: Add timeout guards

### Recommended Safeguards
1. **Feature flags:** Ability to disable WebSocket entirely for fallback
2. **Circuit breaker:** Automatic fallback after N failures
3. **Connection pooling:** Multiple WebSocket connections for redundancy
4. **Message queue:** Buffer messages during transient failures
5. **Health checks:** Proactive connection monitoring
6. **Telemetry:** Comprehensive metrics on connection health

## Next Steps

### Immediate (High Priority)
1. Implement connection establishment tests
2. Implement timeout coordination tests
3. Add network simulation framework
4. Set up CI pipeline for resilience tests

### Short Term (Medium Priority)
1. Implement race condition tests
2. Add performance benchmarks
3. Create chaos engineering test suite
4. Document WebSocket failure modes

### Long Term (Low Priority)
1. Implement connection pooling
2. Add message queueing system
3. Create WebSocket health dashboard
4. Develop automated chaos testing

## Conclusion

The WebSocket implementation is the **single most critical component** in the system. Any failure here causes complete system outage. The complexity of timeout coordination, multiple authentication methods, and environment-specific behavior makes this code **fear-inducing to modify**. Comprehensive resilience testing is **essential** before making any changes to this code.
