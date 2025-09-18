# WebSocket Memory Leak Detection Test Suite

## Overview

The `test_websocket_memory_leaks.py` file contains a comprehensive test suite designed to detect memory leaks and resource management issues in the WebSocket manager. These tests are designed to **FAIL** with the current implementation to demonstrate existing memory leak vulnerabilities.

## File Location
```
netra_backend/tests/unit/test_websocket_memory_leaks.py
```

## Business Justification
- **Segment:** Platform/Internal
- **Business Goal:** Stability & Risk Reduction  
- **Value Impact:** Prevents system crashes from memory exhaustion under sustained user load
- **Strategic Impact:** Ensures the chat system can handle production-scale concurrent connections

## Test Categories

### 1. Connection Limits (TestConnectionLimits)
Tests for connection limit enforcement that **SHOULD FAIL** with current implementation:

- **MAX_CONNECTIONS_PER_USER = 5**: Tests that users are limited to 5 concurrent connections
- **MAX_TOTAL_CONNECTIONS = 1000**: Tests that total system connections are limited to 1000
- **Oldest Connection Eviction**: Tests that oldest connections are removed when limits exceeded

**Expected Failures**: Current implementation has no connection limits, allowing unlimited connections per user and unlimited total connections.

### 2. TTL Cache Expiration (TestTTLCacheExpiration)
Tests for Time-To-Live connection management that **MAY FAIL**:

- **TTL_SECONDS = 300** (5 minutes): Tests that connections expire after 5 minutes of inactivity
- **Activity Refresh**: Tests that active connections have their TTL refreshed
- **Periodic Cleanup**: Tests automatic removal of expired connections

**Expected Behavior**: Current implementation has basic stale connection cleanup but may not implement proper TTL-based expiration.

### 3. Memory Leak Detection (TestMemoryLeakDetection)  
Tests for memory growth under sustained load that **SHOULD DETECT ISSUES**:

- **Sustained Load**: Creates 1500+ connections and measures memory growth
- **Rapid Connect/Disconnect**: Tests memory behavior with 500+ rapid cycles
- **Memory Profiling**: Uses `psutil` to track actual memory consumption

**Expected Detection**: Memory growth beyond acceptable thresholds indicating resource leaks.

### 4. Resource Cleanup (TestResourceCleanup)
Tests for proper cleanup of tracking dictionaries that **MAY FAIL**:

- **Comprehensive Dictionary Cleanup**: Verifies all 4 tracking dictionaries are cleaned
- **Partial Failure Handling**: Tests cleanup when some connections fail to disconnect properly
- **Race Condition Artifacts**: Detects orphaned references after disconnection

**Tracking Dictionaries Tested**:
- `connections`: Main connection storage
- `user_connections`: User-to-connection mappings  
- `room_memberships`: Room-to-connection mappings
- `run_id_connections`: Run ID-to-connection mappings

### 5. Stress and Edge Cases (TestStressAndEdgeCases)
Advanced tests for edge cases that **SHOULD REVEAL WEAKNESSES**:

- **Concurrent Operations**: 50 users with simultaneous connect/disconnect operations
- **WebSocket State Inconsistencies**: Tests handling of externally closed connections
- **Extreme Load**: 200 users × 5 connections = 1000 total connections

## Key Testing Infrastructure

### MockWebSocket Class
Provides realistic WebSocket simulation without actual network connections:
```python
class MockWebSocket:
    - send_json() - Tracks sent messages
    - close() - Simulates connection closure
    - State management - Tracks connection state
```

### MemoryProfiler Class  
Uses `psutil` for actual memory consumption tracking:
```python
class MemoryProfiler:
    - start_profiling() - Baseline memory measurement
    - sample_memory() - Periodic memory sampling
    - detect_memory_leak() - Threshold-based leak detection
```

## Constants Under Test
These constants should be enforced but currently are NOT:

```python
MAX_CONNECTIONS_PER_USER = 5     # Per-user connection limit
MAX_TOTAL_CONNECTIONS = 1000     # System-wide connection limit  
TTL_SECONDS = 300                # 5-minute connection TTL
```

## Running the Tests

### Run All Memory Leak Tests
```bash
python -m pytest netra_backend/tests/unit/test_websocket_memory_leaks.py -v
```

### Run Specific Test Categories
```bash
# Connection limits only
python -m pytest netra_backend/tests/unit/test_websocket_memory_leaks.py::TestConnectionLimits -v

# TTL expiration only
python -m pytest netra_backend/tests/unit/test_websocket_memory_leaks.py::TestTTLCacheExpiration -v

# Memory leak detection only
python -m pytest netra_backend/tests/unit/test_websocket_memory_leaks.py::TestMemoryLeakDetection -v

# Resource cleanup only
python -m pytest netra_backend/tests/unit/test_websocket_memory_leaks.py::TestResourceCleanup -v

# Stress tests only
python -m pytest netra_backend/tests/unit/test_websocket_memory_leaks.py::TestStressAndEdgeCases -v
```

### Run Individual Tests for Debugging
```bash
# Test connection limits enforcement
python test_websocket_memory_leaks.py limits

# Test TTL expiration
python test_websocket_memory_leaks.py ttl

# Test memory leak detection
python test_websocket_memory_leaks.py memory

# Test resource cleanup
python test_websocket_memory_leaks.py cleanup

# Test stress scenarios
python test_websocket_memory_leaks.py stress
```

## Expected Test Results

### Tests That SHOULD FAIL (Demonstrating Issues)
1. **Connection Limits**: All connection limit tests should fail
2. **Memory Growth**: Memory leak detection should trigger warnings
3. **Extreme Load**: System should show resource exhaustion symptoms

### Tests That MAY PASS (Existing Protections)
1. **Basic Dictionary Cleanup**: Proper disconnection cleanup may work
2. **Stale Connection Cleanup**: Basic cleanup mechanisms may function

### Tests That SHOULD PASS (Edge Cases)
1. **MockWebSocket Functionality**: Test infrastructure should work correctly
2. **Memory Profiler**: Memory measurement tools should function

## Interpreting Failures

### Connection Limit Failures
```
AssertionError: Expected 5 connections, got 10
```
**Meaning**: No per-user connection limits implemented

### Memory Leak Detection
```
AssertionError: Memory growth 45.2 MB exceeds acceptable threshold
```
**Meaning**: System is not properly releasing memory after disconnections

### Dictionary Cleanup Issues
```
AssertionError: 127 orphaned user_connections remain
```
**Meaning**: Tracking dictionaries have orphaned references after cleanup

## Dependencies

### Required Python Packages
- `pytest` - Testing framework
- `psutil` - System and process monitoring  
- `asyncio` - Async operations
- `unittest.mock` - Mocking utilities

### Internal Dependencies
- `netra_backend.app.websocket_core.manager.WebSocketManager` - Target class under test
- `netra_backend.app.logging_config` - Logging infrastructure

## Memory Leak Remediation

When these tests fail, they indicate specific areas requiring memory leak fixes:

1. **Connection Limits**: Implement MAX_CONNECTIONS enforcement
2. **TTL Expiration**: Add time-based connection expiration
3. **Reference Cleanup**: Ensure all tracking dictionaries are cleaned properly
4. **Race Condition Handling**: Add locks around critical cleanup sections
5. **WebSocket State Validation**: Properly detect and handle disconnected sockets

## Future Enhancements

The test suite can be extended with:
- **Rate Limiting Tests**: Connection attempt rate limiting
- **Bandwidth Testing**: Large message handling
- **Persistence Testing**: Connection recovery after network issues  
- **Authentication Testing**: Memory leaks in auth-related connection management
- **Distributed Testing**: Multi-instance memory leak detection

---

**Note**: These tests are designed to fail with the current implementation. This is intentional and demonstrates the memory leak vulnerabilities that need to be addressed for production readiness.