# Test Plan: Issue #982 - SSOT Regression Duplicate Event Broadcasting Functions

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/982
**Priority:** P0 - Critical Golden Path blocker
**Business Impact:** $500K+ ARR at risk due to cross-user event leakage
**Test Strategy:** Comprehensive SSOT validation with non-docker real services

## Problem Analysis

### Duplicate Functions Identified:
1. **WebSocketEventRouter.broadcast_to_user** (websocket_event_router.py:198)
   - Parameters: `(user_id: str, event: Dict[str, Any]) -> int`
   - Purpose: Broadcast to all connections for a user via singleton router

2. **UserScopedWebSocketEventRouter.broadcast_to_user** (user_scoped_websocket_event_router.py:234)
   - Parameters: `(event: Dict[str, Any]) -> int`
   - Purpose: Broadcast to user connections via user-scoped router

3. **broadcast_user_event** (user_scoped_websocket_event_router.py:545)
   - Parameters: `(event: Dict[str, Any], user_context: UserExecutionContext) -> int`
   - Purpose: Convenience function using user-scoped router

### SSOT Violation Analysis:
- **Interface Inconsistency:** Different parameter signatures for same purpose
- **Functional Overlap:** All three functions broadcast events to user connections
- **Security Risk:** Multiple paths could lead to cross-user event leakage
- **Golden Path Impact:** Agent events may use wrong broadcast function

## Test Plan Strategy

### Test Categories (Following CLAUDE.md):
1. **Unit Tests** (non-docker) - Component isolation and interface validation
2. **Integration Tests** (non-docker, real services) - Cross-component interaction
3. **E2E Tests** (staging GCP) - Golden Path user flow validation

### Test File Structure:
```
tests/
├── unit/
│   └── websocket/
│       └── test_broadcast_function_ssot_compliance.py
├── integration/
│   └── websocket/
│       ├── test_broadcast_function_consistency.py
│       └── test_user_isolation_security.py
└── e2e/
    └── golden_path/
        └── test_agent_broadcast_delivery.py
```

---

## Test Suite 1: SSOT Compliance Detection (Unit Tests)

**File:** `tests/unit/websocket/test_broadcast_function_ssot_compliance.py`

### Test Class: TestBroadcastFunctionSSotCompliance

#### Test 1.1: test_discover_all_broadcast_functions
**Purpose:** Enumerate all broadcast functions in codebase
**Expected Behavior:** FAIL - Should detect 3+ duplicate functions
```python
def test_discover_all_broadcast_functions(self):
    """Discover all broadcast functions to ensure SSOT compliance."""
    # Scan for functions matching broadcast patterns
    # Should find exactly 3 violations initially
    # After SSOT fix, should find exactly 1 canonical function
```

#### Test 1.2: test_broadcast_function_signature_consistency
**Purpose:** Validate consistent interfaces across all broadcast functions
**Expected Behavior:** FAIL - Different signatures detected
```python
def test_broadcast_function_signature_consistency(self):
    """Ensure all broadcast functions have consistent signatures."""
    # Analyze function signatures
    # Should detect inconsistent parameter patterns
    # After SSOT fix, all should match canonical signature
```

#### Test 1.3: test_no_duplicate_implementations
**Purpose:** Detect duplicate broadcast logic implementations
**Expected Behavior:** FAIL - Multiple implementations found
```python
def test_no_duplicate_implementations(self):
    """Verify no duplicate broadcast logic exists."""
    # Static analysis of broadcast implementations
    # Should fail with current 3 duplicate functions
    # After SSOT fix, should pass with single implementation
```

#### Test 1.4: test_canonical_broadcast_function_exists
**Purpose:** Ensure single canonical broadcast function exists
**Expected Behavior:** PASS after SSOT remediation
```python
def test_canonical_broadcast_function_exists(self):
    """Verify canonical broadcast function is properly defined."""
    # Should identify the single SSOT broadcast function
    # Validate it has proper typing and documentation
```

---

## Test Suite 2: Function Consistency Integration (Integration Tests)

**File:** `tests/integration/websocket/test_broadcast_function_consistency.py`

### Test Class: TestBroadcastFunctionConsistency

#### Test 2.1: test_all_broadcast_functions_same_behavior
**Purpose:** Verify all broadcast functions produce identical results
**Expected Behavior:** FAIL - Inconsistent behavior between functions
```python
async def test_all_broadcast_functions_same_behavior(self):
    """Test that all broadcast functions produce same results."""
    # Set up test user with mock connections
    # Call all 3 broadcast functions with same parameters
    # Should detect behavioral differences
    # After SSOT fix, should be single function only
```

#### Test 2.2: test_broadcast_function_error_handling_consistency
**Purpose:** Ensure consistent error handling across functions
**Expected Behavior:** FAIL - Different error handling patterns
```python
async def test_broadcast_function_error_handling_consistency(self):
    """Verify consistent error handling across broadcast functions."""
    # Test error scenarios with all functions
    # Should detect inconsistent error handling
    # After SSOT fix, single error handling pattern
```

#### Test 2.3: test_broadcast_function_performance_consistency
**Purpose:** Validate consistent performance characteristics
**Expected Behavior:** May FAIL - Performance differences detected
```python
async def test_broadcast_function_performance_consistency(self):
    """Test performance consistency across broadcast functions."""
    # Benchmark all broadcast functions
    # Should detect performance variations
    # After SSOT fix, single optimized implementation
```

---

## Test Suite 3: User Isolation Security (Integration Tests)

**File:** `tests/integration/websocket/test_user_isolation_security.py`

### Test Class: TestUserIsolationSecurity

#### Test 3.1: test_cross_user_event_isolation_all_functions
**Purpose:** Ensure no cross-user event leakage with any broadcast function
**Expected Behavior:** FAIL - Risk of cross-user leakage with multiple functions
```python
async def test_cross_user_event_isolation_all_functions(self):
    """Test user isolation with all broadcast functions."""
    # Set up multiple users with separate connections
    # Test each broadcast function for cross-user leakage
    # Should detect potential security vulnerabilities
    # After SSOT fix, guaranteed isolation with single function
```

#### Test 3.2: test_concurrent_broadcast_isolation
**Purpose:** Test isolation under concurrent broadcast scenarios
**Expected Behavior:** FAIL - Race conditions with multiple functions
```python
async def test_concurrent_broadcast_isolation(self):
    """Test isolation during concurrent broadcasts."""
    # Concurrent broadcasts using different functions
    # Should detect race conditions and isolation failures
    # After SSOT fix, thread-safe single implementation
```

#### Test 3.3: test_user_context_validation_consistency
**Purpose:** Ensure consistent user context validation
**Expected Behavior:** FAIL - Inconsistent validation across functions
```python
async def test_user_context_validation_consistency(self):
    """Test user context validation consistency."""
    # Test user context handling with all functions
    # Should detect validation inconsistencies
    # After SSOT fix, single validation pattern
```

---

## Test Suite 4: Golden Path Integration (E2E Tests)

**File:** `tests/e2e/golden_path/test_agent_broadcast_delivery.py`

### Test Class: TestAgentBroadcastDelivery

#### Test 4.1: test_agent_events_reach_correct_user_all_functions
**Purpose:** Validate agent events reach correct users with all broadcast methods
**Expected Behavior:** FAIL - Inconsistent delivery with multiple functions
```python
async def test_agent_events_reach_correct_user_all_functions(self):
    """Test agent event delivery via all broadcast functions."""
    # Real staging environment test
    # Send agent events via each broadcast function
    # Verify events reach only intended users
    # Should detect delivery inconsistencies
```

#### Test 4.2: test_golden_path_websocket_events_ssot
**Purpose:** Validate Golden Path works with canonical broadcast function
**Expected Behavior:** FAIL initially, PASS after SSOT remediation
```python
async def test_golden_path_websocket_events_ssot(self):
    """Test complete Golden Path with SSOT broadcast function."""
    # End-to-end user flow in staging
    # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
    # Should use single canonical broadcast function
    # Must pass for Golden Path functionality
```

#### Test 4.3: test_multi_user_agent_execution_isolation
**Purpose:** Test multi-user scenarios with agent broadcast events
**Expected Behavior:** FAIL - Cross-user contamination risk
```python
async def test_multi_user_agent_execution_isolation(self):
    """Test multi-user agent execution isolation."""
    # Multiple users with concurrent agent executions
    # Verify events only reach correct users
    # Should detect cross-user contamination
    # After SSOT fix, guaranteed isolation
```

---

## Test Suite 5: Broadcast Function Discovery (Unit Tests)

**File:** `tests/unit/websocket/test_broadcast_function_discovery.py`

### Test Class: TestBroadcastFunctionDiscovery

#### Test 5.1: test_static_code_analysis_broadcast_functions
**Purpose:** Use static analysis to discover all broadcast implementations
**Expected Behavior:** FAIL - Detects 3+ duplicate functions
```python
def test_static_code_analysis_broadcast_functions(self):
    """Static analysis to discover broadcast function duplicates."""
    # Scan codebase for broadcast pattern implementations
    # Should find WebSocketEventRouter.broadcast_to_user
    # Should find UserScopedWebSocketEventRouter.broadcast_to_user
    # Should find broadcast_user_event function
    # After SSOT fix, should find single canonical function
```

#### Test 5.2: test_import_path_analysis_broadcast
**Purpose:** Analyze import paths to detect duplicate broadcast access
**Expected Behavior:** FAIL - Multiple import paths for broadcast functionality
```python
def test_import_path_analysis_broadcast(self):
    """Analyze import paths for broadcast function access."""
    # Scan for imports of broadcast functions
    # Should detect multiple ways to access broadcast functionality
    # After SSOT fix, single canonical import path
```

---

## Expected Test Results

### Pre-SSOT Remediation (All tests should FAIL):
- **SSOT Compliance Tests:** FAIL - 3 duplicate functions detected
- **Function Consistency Tests:** FAIL - Inconsistent signatures and behavior
- **User Isolation Tests:** FAIL - Multiple security risk vectors
- **Golden Path Tests:** FAIL - Inconsistent event delivery
- **Discovery Tests:** FAIL - Multiple implementations found

### Post-SSOT Remediation (All tests should PASS):
- **SSOT Compliance Tests:** PASS - Single canonical function
- **Function Consistency Tests:** PASS - Consistent single implementation
- **User Isolation Tests:** PASS - Guaranteed isolation with single function
- **Golden Path Tests:** PASS - Reliable event delivery via canonical function
- **Discovery Tests:** PASS - Single implementation discovered

## Test Execution Commands

### Unit Tests (Non-Docker):
```bash
# Individual test suites
python -m pytest tests/unit/websocket/test_broadcast_function_ssot_compliance.py -v
python -m pytest tests/unit/websocket/test_broadcast_function_discovery.py -v

# All unit tests for broadcast SSOT
python -m pytest tests/unit/websocket/ -k "broadcast" -v
```

### Integration Tests (Non-Docker, Real Services):
```bash
# Individual integration test suites
python -m pytest tests/integration/websocket/test_broadcast_function_consistency.py -v --real-services
python -m pytest tests/integration/websocket/test_user_isolation_security.py -v --real-services

# All integration tests for broadcast
python -m pytest tests/integration/websocket/ -k "broadcast" -v --real-services
```

### E2E Tests (Staging GCP):
```bash
# Golden Path broadcast tests
python -m pytest tests/e2e/golden_path/test_agent_broadcast_delivery.py -v --env staging

# Full E2E validation
python -m pytest tests/e2e/ -k "broadcast" -v --env staging
```

### Complete Test Suite:
```bash
# Run all broadcast SSOT tests
python -m pytest -k "broadcast" -v --real-services
```

## Success Criteria

### Phase 1: Test Creation (Current Step)
- [x] Comprehensive test plan documented
- [ ] All 5 test suites created with failing tests
- [ ] Tests properly categorized (unit, integration, e2e)
- [ ] Non-docker real services configuration validated

### Phase 2: SSOT Remediation Validation
- [ ] All pre-remediation tests FAIL as expected
- [ ] SSOT consolidation implemented
- [ ] All post-remediation tests PASS
- [ ] Golden Path functionality confirmed operational

### Phase 3: Production Readiness
- [ ] Staging environment tests 100% PASS
- [ ] Performance benchmarks maintained or improved
- [ ] Security isolation validated
- [ ] Business value protection confirmed ($500K+ ARR)

---

## Risk Mitigation

### Test Infrastructure Risks:
- **Risk:** Test collection failures due to syntax issues
- **Mitigation:** Follow TEST_EXECUTION_GUIDE.md for proper test structure

### Business Continuity Risks:
- **Risk:** Golden Path disruption during testing
- **Mitigation:** Use staging environment for disruptive tests

### Security Testing Risks:
- **Risk:** Actual cross-user data exposure during testing
- **Mitigation:** Use synthetic test data only, never production user data

---

**Last Updated:** 2025-01-14
**Next Action:** Create test files implementing this comprehensive test plan
**Estimated Test Count:** 15+ individual test methods across 5 test suites