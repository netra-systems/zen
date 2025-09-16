# L3 Integration Tests - WebSocket Redis Pub/Sub

## Overview

This directory contains L3 (Level 3) integration tests that use **real Redis containers** via Docker to validate WebSocket connections with Redis pub/sub functionality.

## Business Value

**BVJ (Business Value Justification):**
- **Segment:** Platform/Internal  
- **Business Goal:** Stability - Ensure WebSocket reliability for real-time features
- **Value Impact:** Critical for user experience in collaborative features and real-time updates  
- **Strategic Impact:** Reduces production incidents, improves customer retention

## L3 Testing Requirements

L3 tests validate the **Real SUT with Real Local Services (Out-of-Process)** level of the Mock-Real Spectrum:

- ✅ **Real WebSocket Manager** (production code)
- ✅ **Real Redis Container** (Docker containerized Redis 7-alpine)
- ✅ **Real Redis Client** (redis-py with async support)
- ✅ **Real Pub/Sub Channels** (actual Redis pub/sub messaging)
- ✅ **Real Network Communication** (TCP connections, serialization)

## Prerequisites

### Required Software
- **Docker:** Must be running and accessible
- **Redis Python Package:** `redis>=6.4.0` (already installed)
- **Python 3.12+** with asyncio support

### Docker Images
The tests automatically use the `redis:7-alpine` image. Ensure Docker can pull this image:

```bash
docker pull redis:7-alpine
```

## Test Structure

### Main Test File
```
app/tests/integration/test_websocket_redis_pubsub_l3.py
```

### Test Scenarios

1. **`test_websocket_redis_connection_setup`**
   - WebSocket connection establishment with Redis integration
   - Redis channel subscription and key creation
   - Connection state management

2. **`test_redis_pubsub_message_broadcasting`**
   - Message publishing to Redis channels
   - Multiple subscriber connections
   - Message routing and delivery validation

3. **`test_websocket_reconnection_with_redis_state`**
   - Connection state persistence in Redis
   - Reconnection handling and state recovery
   - Message queue replay mechanisms

4. **`test_concurrent_websocket_connections_redis_performance`**
   - 50+ concurrent WebSocket connections
   - Redis connection pool handling
   - Broadcasting performance validation

5. **`test_redis_channel_management_isolation`**
   - Dynamic channel subscription/unsubscription
   - Channel isolation between users
   - Message delivery accuracy

6. **`test_redis_failover_websocket_recovery`**
   - WebSocket resilience during Redis restarts
   - Connection recovery mechanisms
   - Service continuity validation

## Running L3 Tests

### Single Test Execution
```bash
# Run a specific L3 test
python -m pytest app/tests/integration/test_websocket_redis_pubsub_l3.py::TestWebSocketRedisPubSubL3::test_websocket_redis_connection_setup -v

# Run all L3 tests in the file
python -m pytest app/tests/integration/test_websocket_redis_pubsub_l3.py -v

# Run with L3 marker
python -m pytest -m L3 -v
```

### Integration with Test Runner
```bash
# Via unified test runner
python unified_test_runner.py --level integration --real-redis

# Include L3 tests in integration suite
python unified_test_runner.py --level integration --markers L3
```

## Test Architecture

### Redis Container Management
- **Automatic Setup:** Tests automatically start Redis containers on unique ports
- **Isolation:** Each test class gets its own Redis container to prevent interference
- **Cleanup:** Containers are automatically stopped and removed after tests
- **Port Management:** Uses dynamic ports (6381+) to avoid conflicts

### Mock Strategy (L3 Realism)
- **Real Services:** Redis container, WebSocket manager, Redis client
- **Minimal Mocks:** Only WebSocket connections (for controllable message tracking)
- **Mock Justification:** All mocks are documented with `@mock_justified` decorator

### Error Handling
- **Container Failures:** Graceful handling of Docker startup issues
- **Network Timeouts:** Configurable timeouts for Redis operations
- **Resource Cleanup:** Guaranteed cleanup even on test failures

## Performance Expectations

### Test Execution Times
- **Setup Phase:** < 10 seconds (container startup)
- **Individual Tests:** < 5 seconds each
- **Performance Test:** < 30 seconds (50 concurrent connections)
- **Cleanup Phase:** < 5 seconds

### Resource Usage
- **Memory:** ~50MB per Redis container
- **CPU:** Minimal during normal test execution
- **Network:** Localhost only (no external dependencies)

## Troubleshooting

### Common Issues

**Docker Not Available:**
```
RuntimeError: Docker is not available or not running
```
- Solution: Ensure Docker Desktop is running

**Port Conflicts:**
```
Error: Port 6381 already in use
```
- Solution: Tests use dynamic port allocation, restart if conflicts persist

**Redis Connection Timeout:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```
- Solution: Increase timeout in Redis container startup, check Docker logs

**Container Cleanup Issues:**
```
Warning: Error stopping Redis container
```
- Solution: Manual cleanup with `docker ps` and `docker rm -f <container>`

### Debugging

**Enable Verbose Logging:**
```bash
python -m pytest app/tests/integration/test_websocket_redis_pubsub_l3.py -v -s --log-cli-level=DEBUG
```

**Check Container Logs:**
```bash
# Find container name from test output, then:
docker logs <container_name>
```

**Manual Container Testing:**
```bash
# Start Redis container manually
docker run -d --name test-redis -p 6381:6379 redis:7-alpine

# Test connection
redis-cli -h localhost -p 6381 ping

# Cleanup
docker stop test-redis && docker rm test-redis
```

## Integration with CI/CD

### GitHub Actions Support
The L3 tests are designed to work in GitHub Actions with Docker support:

```yaml
- name: Run L3 Integration Tests
  run: |
    python -m pytest -m L3 --tb=short
```

### Local Development
For local development, tests can be run individually or as part of the full integration suite.

## Future Enhancements

1. **Testcontainers Integration:** Migrate to testcontainers-python for better container management
2. **Redis Cluster Testing:** Add Redis cluster mode validation
3. **Performance Benchmarks:** Add detailed performance metrics collection
4. **Stress Testing:** Extend to 1000+ concurrent connections
5. **Failover Scenarios:** Add more complex Redis failover testing

## References

- [Mock-Real Spectrum Documentation](../../../SPEC/testing.xml)
- [WebSocket Architecture](../../../app/ws_manager.py)  
- [Redis Manager](../../../app/redis_manager.py)
- [Testing Philosophy](../../../CLAUDE.md#testing)