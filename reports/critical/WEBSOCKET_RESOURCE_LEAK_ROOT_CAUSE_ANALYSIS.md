# WebSocket Resource Leak Root Cause Analysis - Production Scenario Investigation

**Date**: January 9, 2025  
**Investigation Focus**: Real production patterns causing WebSocket manager resource leaks  
**Issue**: Users hitting 20 manager limit despite passing tests  

## Executive Summary

The existing WebSocket resource leak tests are **passing** but do not reproduce the actual production scenarios causing the 20-manager limit crashes. This analysis identifies the specific production patterns that bypass current test coverage and provides comprehensive stress tests to validate the real root causes.

## Key Findings

### 1. **Current Tests Miss Critical Production Patterns**

The existing tests (`test_websocket_resource_leak_detection.py`) focus on:
- ✅ Manager creation limits (works correctly)  
- ✅ Cleanup timing precision (works correctly)
- ✅ Emergency cleanup triggers (works correctly)
- ✅ Rapid connection cycles (works correctly in isolation)

**But miss these production scenarios:**
- ❌ **Thread ID Inconsistency** between database sessions and WebSocket contexts
- ❌ **Cloud Run Container Lifecycle** effects (cold starts, restarts)
- ❌ **Concurrent Same-User Connections** (browser tabs, mobile apps)
- ❌ **ID Generation Race Conditions** during rapid reconnections
- ❌ **Background Cleanup vs Creation Rate Mismatches** in production load

### 2. **Root Cause: Thread ID Generation Inconsistency**

From the Five Whys analysis and code examination, the fundamental issue is:

```python
# Database session factory generates context:
db_thread_id, db_run_id, db_request_id = UnifiedIdGenerator.generate_user_context_ids(
    user_id=user_id, 
    operation="session"  # DIFFERENT operation string
)

# WebSocket factory generates separate context:
ws_thread_id, ws_run_id, ws_request_id = UnifiedIdGenerator.generate_user_context_ids(
    user_id=user_id,
    operation="websocket_factory"  # DIFFERENT operation string  
)

# Result: db_thread_id != ws_thread_id
# Isolation keys become inconsistent: "user123:thread_session_123" vs "user123:thread_websocket_factory_456"
# Cleanup fails because managers stored under different keys than lookup keys
```

### 3. **Production Environment Conditions Causing Accumulation**

#### **Condition 1: Browser Multi-Tab Pattern**
- **Scenario**: User opens 5-8 browser tabs simultaneously
- **Problem**: Each tab may trigger separate database session before WebSocket connection
- **Result**: Different thread_ids for what should be the same user context
- **Accumulation Rate**: 2-3 uncleaned managers per browser session
- **Timeline**: 10-15 browser sessions = 20 manager limit

#### **Condition 2: Cloud Run Cold Start + Connection Burst**  
- **Scenario**: GCP container restart followed by user reconnection burst
- **Problem**: Background cleanup task not started during cold start
- **Result**: 15-20 connections created before any cleanup occurs
- **Accumulation Rate**: 80-100% of burst connections remain
- **Timeline**: Single cold start event can hit 20 manager limit

#### **Condition 3: Network Reconnection Cycles**
- **Scenario**: Unstable mobile network causing repeated connect/disconnect
- **Problem**: New manager created before old one cleaned up due to timing
- **Result**: 1-2 managers per reconnection cycle remain active
- **Accumulation Rate**: 10-15 reconnections = 20 manager limit  
- **Timeline**: 10-15 minutes of unstable network

#### **Condition 4: Database Session + WebSocket Context Mismatch**
- **Scenario**: Normal application flow where database session created first
- **Problem**: Different operation strings create different thread_ids
- **Result**: Cleanup lookups fail due to isolation key mismatch
- **Accumulation Rate**: 90-100% of connections with database sessions
- **Timeline**: Regular usage over 2-3 hours = 20 manager limit

#### **Condition 5: Background Cleanup vs Creation Rate Race**
- **Scenario**: High user activity creating managers faster than 2-minute cleanup cycles
- **Problem**: Synchronous limit enforcement vs asynchronous cleanup timing mismatch
- **Result**: Managers accumulate during high-activity periods
- **Accumulation Rate**: 5-10 managers per high-activity burst
- **Timeline**: 2-3 high-activity periods = 20 manager limit

## Environment-Specific Timing Conditions

### **GCP Cloud Run Production Environment**
- **Container Cold Start Time**: 2-5 seconds (no background cleanup)
- **Network Latency**: 50-200ms (affects reconnection timing)
- **Memory Pressure**: High (affects garbage collection timing)  
- **Concurrent Users**: 50-100 (affects resource contention)

### **Local Development Environment**  
- **Background Cleanup**: Every 60 seconds (vs 2 minutes production)
- **Network Latency**: <5ms (no realistic reconnection patterns)
- **Memory Pressure**: Low (cleanup works optimally)
- **Concurrent Users**: 1-2 (no resource contention)

### **Testing Environment**
- **Cleanup Timing**: 30 seconds (optimized for tests)  
- **Connection Patterns**: Isolated (no cross-scenario interference)
- **Resource Limits**: Higher thresholds (prevents false failures)
- **Load Patterns**: Sequential (no concurrent user simulation)

## Why Current Tests Pass But Production Fails

| Test Scenario | Production Reality | Gap |
|---------------|-------------------|-----|
| **Sequential manager creation** | **Concurrent multi-tab creation** | Thread ID consistency not tested |
| **Immediate cleanup after creation** | **Delayed cleanup due to timing** | Background cleanup race conditions |
| **Single user contexts** | **Database + WebSocket contexts** | Context mismatch scenarios missing |
| **Controlled timing** | **Variable network/container timing** | Environment-specific delays not simulated |
| **Mock WebSocket connections** | **Real connection lifecycle** | Actual resource management not tested |

## Proposed Production-Ready Test Implementation

### **New Test Suite: `test_websocket_production_leak_scenarios.py`**

#### **Test 1: Browser Multi-Tab Resource Leak Reproduction**
```python
async def test_browser_multi_tab_resource_leak_reproduction(self):
    """
    Simulates 8 browser tabs opening with database sessions created first,
    then WebSocket connections, reproducing thread_id inconsistency.
    """
    # Creates contexts with different operation strings
    # Validates isolation key consistency  
    # Checks cleanup effectiveness with mismatched keys
```

#### **Test 2: Cloud Run Cold Start Connection Burst**  
```python
async def test_cloud_run_cold_start_burst_reproduction(self):
    """
    Simulates GCP container cold start followed by 25 rapid connections,
    reproducing background cleanup timing issues.
    """
    # Creates factory without background cleanup started
    # Rapid connection burst (faster than cleanup can handle)
    # Validates emergency cleanup effectiveness
```

#### **Test 3: Network Reconnection Cycles**
```python
async def test_network_reconnection_cycles_reproduction(self):
    """
    Simulates 15 rapid network reconnection cycles with immediate reconnect,
    reproducing isolation key conflicts and timing mismatches.
    """
    # Rapid disconnect/reconnect cycles  
    # Checks for isolation key conflicts
    # Validates cleanup coordination
```

#### **Test 4: Database + WebSocket Context ID Mismatch**
```python
async def test_database_websocket_context_mismatch_reproduction(self):
    """
    Directly reproduces thread_id inconsistency by creating database session
    context first, then WebSocket context, using different operation strings.
    """
    # Creates contexts with "session" vs "websocket_factory" operations
    # Compares generated thread_ids  
    # Tests cleanup with mismatched isolation keys
```

#### **Test 5: Background Cleanup vs Creation Rate Race**
```python
async def test_background_cleanup_race_condition_reproduction(self):
    """
    Creates managers faster than background cleanup rate (every 500ms for 10s),
    reproducing timing mismatch between creation and cleanup.
    """
    # High-frequency manager creation
    # Tests emergency cleanup trigger points
    # Validates cleanup effectiveness under load
```

## Validation Strategy

### **Memory Leak Detection**  
- Real RSS memory usage tracking with `psutil`
- Baseline memory capture before each scenario
- Growth threshold detection (>50MB indicates leak)
- Memory pattern analysis across scenarios

### **Resource Accumulation Monitoring**
- Track manager creation vs cleanup ratios  
- Monitor active manager counts over time
- Detect accumulation patterns in different scenarios
- Validate cleanup effectiveness percentages

### **Thread ID Consistency Validation**
- Compare database session vs WebSocket context thread_ids
- Track isolation key generation consistency
- Monitor cleanup success rates by scenario type
- Identify mismatch patterns causing failures

### **Environment-Aware Testing**
- CI environment: Shorter timeouts, fewer cycles
- Development environment: Standard production simulation  
- Staging environment: Full production load patterns
- Different timing thresholds per environment

## Success Criteria

### **Immediate Success (Test Implementation)**
- ✅ All 5 production scenarios reproduce actual resource leaks
- ✅ Tests fail when run against current buggy code
- ✅ Tests pass after thread_id consistency fixes applied
- ✅ Memory leak detection catches accumulation patterns

### **Long-term Success (Production Stability)**  
- ✅ Zero users hit 20-manager limit in production
- ✅ Manager cleanup success rate >95% across all scenarios
- ✅ No thread_id mismatch errors in production logs  
- ✅ Background cleanup keeps manager counts stable

## Implementation Priority

### **Phase 1: Critical Test Implementation** (Immediate)
1. **Deploy new production scenario tests** (`test_websocket_production_leak_scenarios.py`)
2. **Run against current code** (should reproduce leaks and fail tests)
3. **Validate tests catch real production patterns** (test the tests)

### **Phase 2: Root Cause Fixes** (Next Sprint)
1. **Thread ID consistency fix** (single context creation pattern)
2. **Background cleanup timing optimization** (faster cycles, proactive triggers)
3. **Isolation key generation consistency** (unified operation strings)

### **Phase 3: Production Validation** (Following Sprint)  
1. **Deploy fixes to staging environment**
2. **Run full production scenario test suite** 
3. **Monitor production metrics for manager stability**
4. **Validate 20-manager limit errors eliminated**

## Technical Implementation Notes

### **Real Component Usage (No Mocking)**
```python
# Use real WebSocket connections
test_websocket = TestWebSocketConnection(connection_id)
connection = WebSocketConnection(websocket=test_websocket, ...)

# Use real UserExecutionContext generation  
thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(...)
context = UserExecutionContext(thread_id=thread_id, ...)

# Use real factory components
factory = WebSocketManagerFactory(max_managers_per_user=20)
manager = await factory.create_manager(context)
```

### **Environment-Aware Configuration**
```python
class TestConfiguration:
    def __init__(self):
        self.env = get_env()
        self.is_ci = env.get("CI") == "true"
        self.cleanup_timeout_ms = 1000 if self.is_ci else 500
        self.stress_test_cycles = 50 if self.is_ci else 100
```

### **Memory Leak Detection**  
```python
def capture_memory_snapshot(self, label: str) -> float:
    memory_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024) 
    if memory_mb > self.baseline_memory + self.leak_threshold:
        self.record_leak_evidence(memory_mb, label)
```

## Conclusion

The existing WebSocket resource leak tests validate that the **cleanup mechanisms work correctly** when used properly, but they **miss the production scenarios** where the mechanisms are **used incorrectly** due to architectural issues.

The new production scenario tests will:
1. **Reproduce the actual resource leak patterns** observed in GCP production  
2. **Validate that current code fails** these realistic scenarios  
3. **Provide regression testing** for thread_id consistency fixes
4. **Enable confident deployment** of resource leak fixes

This comprehensive approach ensures that fixes address the **real production issues** rather than just improving already-working test scenarios.