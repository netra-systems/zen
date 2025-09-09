# Thread ID Consistency Test Plan

## Executive Summary

This test plan validates the thread_ID consistency issue causing WebSocket manager resource leaks. The comprehensive test implementation reproduces the exact bug scenario where isolation key mismatches prevent cleanup from finding managers, leading to resource accumulation and system instability.

## Problem Statement

**Root Cause:** WebSocket managers are indexed by isolation keys containing thread_ID values. When thread_ID values become inconsistent during the WebSocket lifecycle, cleanup operations cannot locate the correct managers for removal, causing resource leaks that eventually hit the 20-manager limit.

**Business Impact:** System becomes unresponsive when users reach the manager limit, preventing new WebSocket connections and disrupting real-time communication features.

## Test Implementation Architecture

### Core Components

#### 1. ThreadIDConsistencyTracker
**Purpose:** Monitor and validate thread_ID values throughout WebSocket operations
**Features:**
- Snapshot capture at critical lifecycle points
- Automatic violation detection for thread_ID mismatches  
- Comprehensive analysis and reporting
- Recovery scenario simulation

#### 2. ThreadIdSnapshot
**Purpose:** Point-in-time capture of thread_ID values from multiple sources
**Data Captured:**
- `thread_id_user_context`: From UserExecutionContext
- `thread_id_manager_context`: From WebSocket manager's context
- `thread_id_isolation_key`: Extracted from factory isolation key
- `thread_id_cleanup_lookup`: From simulated cleanup operations

#### 3. TestWebSocketConnection
**Purpose:** Real WebSocket component replacement (per project no-mocking requirements)
**Features:**
- Actual WebSocket message handling
- Connection state management
- Realistic network simulation

## Test Categories and Coverage

### 1. Unit Tests - Context Consistency
**Test:** `test_thread_id_consistency_user_context_creation`
**Purpose:** Validate UserExecutionContext maintains thread_ID consistency
**Scenarios:**
- Standard context creation with UnifiedIdGenerator
- Multiple contexts for same user_id (thread_ID uniqueness)
- Manual thread_ID specification and preservation
- Thread_ID extraction from run_id using UnifiedIDManager

**Expected Result:** PASS - No thread_ID violations detected
**Success Criteria:** Consistency score = 100%

### 2. Integration Tests - Bug Reproduction
**Test:** `test_thread_id_inconsistency_websocket_manager_creation`
**Purpose:** Reproduce the exact bug scenario causing resource leaks
**Bug Simulation:**
1. Create UserExecutionContext with initial thread_ID
2. Create WebSocket manager using that context
3. Extract isolation key (contains original thread_ID)
4. Simulate different UserExecutionContext with same user_id but different thread_ID
5. Attempt cleanup - demonstrates how mismatch prevents manager discovery

**Expected Result:** VIOLATIONS DETECTED - Shows bug reproduction
**Success Criteria:** thread_ID violations > 0, demonstrates exact failure scenario

### 3. Integration Tests - Lifecycle Validation
**Test:** `test_websocket_manager_lifecycle_thread_id_consistency`
**Purpose:** Validate complete WebSocket lifecycle with authentication
**Flow:**
1. Create authenticated user context using E2EAuthHelper
2. Create WebSocket manager from authenticated context
3. Add real WebSocket connection
4. Send messages through WebSocket
5. Track thread_ID consistency throughout all operations
6. Perform cleanup and validate success

**Expected Result:** PASS - Consistent thread_ID throughout lifecycle
**Success Criteria:** Cleanup successful, manager deactivated, consistency score = 100%

### 4. E2E Tests - Concurrent Operations
**Test:** `test_concurrent_websocket_operations_thread_id_isolation`
**Purpose:** Validate thread_ID isolation between concurrent users
**Scenarios:**
- 3 concurrent authenticated users
- Simultaneous WebSocket manager creation
- Concurrent message sending
- Parallel cleanup operations
- Cross-user thread_ID contamination detection

**Expected Result:** PASS - No cross-user thread_ID contamination
**Success Criteria:** All cleanups successful, unique thread_IDs match user count

### 5. Edge Case Tests - Recovery Mechanisms
**Test:** `test_thread_id_recovery_after_mismatch`
**Purpose:** Validate system recovery when thread_ID mismatches occur
**Recovery Strategies:**
1. **Strategy 1:** Cleanup with original isolation key
2. **Strategy 2:** Force cleanup by user_id when Strategy 1 fails

**Expected Result:** RECOVERY SUCCESSFUL - Prevents resource leak
**Success Criteria:** Manager deactivated after recovery, no active managers remain

## Test Execution Framework

### Environment Configuration
```python
# Local Testing
environment = "test"
auth_service_url = "http://localhost:8083"
websocket_url = "ws://localhost:8002/ws"

# Staging Testing  
environment = "staging"
auth_service_url = "https://auth-staging.netra.ai"
websocket_url = "wss://api-staging.netra.ai/ws"
```

### Authentication Requirements
**Per CLAUDE.md:** ALL integration/e2e tests MUST use real authentication
- Unit tests: Can use mock contexts for isolated testing
- Integration tests: Must use E2EAuthHelper with JWT tokens
- E2E tests: Must use full OAuth flow with staging credentials

### Real Component Usage
**Per CLAUDE.md:** NO mocking in critical tests
- WebSocket connections: TestWebSocketConnection (real component)
- Database sessions: Real async sessions where applicable
- Authentication: Real JWT tokens and validation
- Factory operations: Actual WebSocketManagerFactory instances

## Expected Test Output Analysis

### Successful Bug Reproduction
```
=== THREAD_ID CONSISTENCY TRACKING REPORT ===
Total Snapshots: 8
Total Violations: 2

VIOLATIONS:
  [0] thread_id_mismatch (CRITICAL)
      Operation: inconsistent_context_creation
      Thread IDs: {
        'user_context': 'different-thread-abcd1234', 
        'manager_context': 'thread_websocket_factory_1234567890_abc_def123',
        'isolation_key': 'user123_thread_websocket_factory_1234567890_abc_def123_run456'
      }

ANALYSIS:
  Consistency Score: 75.0%
  Unique Thread IDs: 2
  🔴 BUG REPRODUCED: Thread ID violations prevent cleanup
```

### Healthy System Behavior
```
=== THREAD_ID CONSISTENCY TRACKING REPORT ===
Total Snapshots: 10
Total Violations: 0

ANALYSIS:
  Consistency Score: 100.0%
  Unique Thread IDs: 1
  Thread IDs Found: ['thread_websocket_factory_1234567890_abc_def123']
  ✅ CONSISTENT: All operations use same thread_ID
```

## Critical Test Scenarios

### Scenario 1: ID Generation Inconsistency
**Setup:** Mix UnifiedIdGenerator and UnifiedIDManager for ID creation
**Test:** Create context with UnifiedIdGenerator, extract with UnifiedIDManager
**Expected:** Potential mismatch if generators produce incompatible formats

### Scenario 2: Context Recreation
**Setup:** User reconnects, creates new context for same session
**Test:** Original manager exists, new context has different thread_ID
**Expected:** Cleanup of original manager fails due to thread_ID mismatch

### Scenario 3: Concurrent User Operations  
**Setup:** Multiple users creating/cleaning WebSocket managers simultaneously
**Test:** Ensure thread_ID values don't cross-contaminate between users
**Expected:** Each user maintains isolated thread_ID space

### Scenario 4: Recovery Under Load
**Setup:** System under high load with multiple thread_ID mismatches
**Test:** Force cleanup mechanisms handle batch recovery
**Expected:** All mismatched managers eventually cleaned up

## Success Metrics

### Bug Reproduction Metrics
- **Thread_ID Violations:** > 0 violations detected in bug reproduction test
- **Isolation Key Mismatch:** Cleanup fails due to thread_ID not found in isolation key
- **Resource Accumulation:** Managers remain active after failed cleanup attempts

### System Health Metrics
- **Consistency Score:** 100% for healthy lifecycle tests
- **Cleanup Success Rate:** 100% cleanup success in normal operations
- **Recovery Success Rate:** 100% recovery success for mismatched scenarios
- **No Resource Leaks:** 0 active managers after all test cleanup

### Performance Metrics
- **Context Creation:** < 10ms per UserExecutionContext
- **Manager Lifecycle:** < 100ms from creation to cleanup
- **Concurrent Operations:** All users complete within 30s timeout
- **Recovery Time:** < 5s for force cleanup recovery

## Implementation Compliance

### CLAUDE.md Requirements
✅ **Real Components:** TestWebSocketConnection replaces mocks
✅ **E2E Authentication:** E2EAuthHelper for all integration/e2e tests  
✅ **SSOT Base Class:** SSotAsyncTestCase inheritance
✅ **Environment Isolation:** shared.isolated_environment usage
✅ **Hard Failure Mode:** All tests fail hard on errors, no silent failures

### Testing Best Practices
✅ **Comprehensive Coverage:** Unit → Integration → E2E → Edge Cases
✅ **Bug Reproduction First:** Failing tests demonstrate the problem
✅ **Real-World Scenarios:** Authenticated users, concurrent operations
✅ **Detailed Logging:** ThreadIDConsistencyTracker provides complete visibility
✅ **Resource Cleanup:** Proper teardown prevents test contamination

## Validation Checklist

### Pre-Test Setup
- [ ] WebSocketManagerFactory configured with 20-manager limit
- [ ] E2EAuthHelper configured for target environment
- [ ] ThreadIDConsistencyTracker initialized and tracking enabled
- [ ] Real WebSocket components available (no mocks)

### During Test Execution  
- [ ] Thread_ID snapshots captured at each lifecycle point
- [ ] Violation detection functioning (mismatches trigger violations)
- [ ] Authentication working for integration/e2e tests
- [ ] Resource cleanup happening in teardown

### Post-Test Analysis
- [ ] ThreadIDConsistencyTracker reports generated
- [ ] Bug reproduction tests show expected violations
- [ ] Healthy tests show 100% consistency scores
- [ ] No resource leaks detected in factory state
- [ ] Recovery mechanisms tested and validated

## Risk Mitigation

### Test Environment Risks
- **Risk:** Staging environment instability affecting e2e tests
- **Mitigation:** Fallback to local environment with staging-compatible auth

### Authentication Risks  
- **Risk:** JWT token expiration during long test execution
- **Mitigation:** Token refresh logic in E2EAuthHelper

### Resource Cleanup Risks
- **Risk:** Failed tests leave managers active, affecting subsequent tests
- **Mitigation:** Comprehensive teardown with force cleanup fallback

### Concurrency Risks
- **Risk:** Race conditions in concurrent test scenarios
- **Mitigation:** Thread-safe snapshot capture and proper async handling

This comprehensive test plan provides the foundation for identifying, reproducing, and ultimately fixing the thread_ID consistency issue causing WebSocket resource leaks in the Netra Apex platform.