## Priority: P2 (Medium - Agent Test Infrastructure)

**Status:** Test collection and discovery issues affecting agent-focused testing infrastructure

**FAILING TEST GARDENER 2025-09-14:** Issue #3 - Test Collection/Discovery Issues in agent-focused tests

## Problem Description

Multiple test collection and discovery issues are affecting the reliability of agent-related testing:

1. **TestWebSocketConnection Constructor Warning:** pytest cannot collect test class due to __init__ constructor
2. **File Discovery Inconsistency:** Git status shows files that may have discovery issues

## Error Details

### 1. TestWebSocketConnection Constructor Warning
```
PytestCollectionWarning: cannot collect test class 'TestWebSocketConnection' because it has a __init__ constructor
Location: tests/critical/test_agent_websocket_bridge_multiuser_isolation.py:1
```

**Root Cause Analysis:**
- TestWebSocketConnection is a utility class for real WebSocket testing (not mocking)
- Class has __init__ constructor but pytest tries to collect it as test class
- Named with "Test" prefix triggering pytest collection attempt

### 2. Agent Test File Discovery Issues
**File Location:** `tests/integration/test_issue_971_websocket_manager_alias.py`
- File exists in filesystem but mentioned in failing test gardener as potentially missing
- Could indicate git tracking or test discovery inconsistencies
- Affects WebSocket manager alias testing for agents

## Impact Assessment

**Business Impact:** P2 (Medium)
- **Agent Test Coverage Gaps:** Risk of missing critical agent functionality tests
- **CI/CD Reliability:** Potential for regression tests not running properly
- **Development Confidence:** Uncertainty in agent testing infrastructure

**Technical Impact:**
- Test collection warnings in critical agent isolation tests
- Potential missing test coverage for Issue #971 (WebSocket manager alias)
- Risk of pytest missing important agent-focused tests
- Infrastructure reliability concerns for multi-user agent isolation

## Test Evidence

**Affected Files:**
- `tests/critical/test_agent_websocket_bridge_multiuser_isolation.py`
- `tests/integration/test_issue_971_websocket_manager_alias.py`

**Collection Warning:**
```
tests/critical/test_agent_websocket_bridge_multiuser_isolation.py:1: PytestCollectionWarning: cannot collect test class 'TestWebSocketConnection' because it has a __init__ constructor
```

**Agent Focus:**
- Multi-user WebSocket isolation testing (critical for $500K+ ARR)
- Agent WebSocket bridge functionality
- Real WebSocket connections vs mocking patterns

## Root Cause Analysis

### TestWebSocketConnection Issue
```python
class TestWebSocketConnection:  # <-- Pytest tries to collect this
    def __init__(self):           # <-- Constructor prevents collection
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
```

**Analysis:**
- Class is a test utility for real WebSocket connections (not a test class)
- Purpose: Replace mocks with real connections for better test accuracy
- Naming convention confuses pytest collector

### File Discovery Inconsistency
- Git tracking may be inconsistent for issue-specific test files
- Test runner may have different discovery patterns than git status
- Could affect CI/CD pipeline test execution

## Recommended Resolution

### TestWebSocketConnection Fix (Priority 1)
**Option A: Rename Class (Recommended)**
```python
# BEFORE (problematic)
class TestWebSocketConnection:  # <-- Confuses pytest

# AFTER (fixed)
class MockWebSocketConnection:  # or WebSocketTestConnection
    def __init__(self):
```

**Option B: Move to Utilities Module**
- Move to `test_framework/utilities/websocket_connection.py`
- Import as utility, not part of test file

### File Discovery Fix (Priority 2)
- Verify git tracking status of all issue-specific test files
- Ensure test discovery patterns match git repository contents
- Validate CI/CD test execution includes all agent-focused tests

## Business Value Context

**Segment:** Platform (Agent Testing Infrastructure)
**Goal:** Test Coverage and CI/CD Reliability
**Value Impact:** Ensures agent functionality tests run properly, protects Golden Path
**Strategic Impact:** Prevents regression in agent systems protecting $500K+ ARR

## Agent Focus Impact

**Critical Agent Systems Affected:**
- WebSocket agent bridge multi-user isolation
- Agent execution context validation
- Real-time agent communication testing
- Cross-user event leakage prevention

**Risk to Golden Path:**
- Agent functionality regressions could go undetected
- Multi-user isolation failures could affect customer security
- WebSocket communication issues could break chat functionality

## Related Issues

**Related Infrastructure:**
- Issue #868: Test collection warnings (TestContext constructor)
- Issue #971: WebSocket manager alias issues (potentially this file discovery issue)
- Issue #987: SSOT infrastructure testing
- Issue #420: Docker infrastructure dependencies

**Agent-Focused Issues:**
- Issue #714: BaseAgent test coverage
- Issue #762: Agent WebSocket bridge test coverage
- Issue #870: Agent integration test coverage

## Definition of Done

- [ ] TestWebSocketConnection renamed to avoid pytest collection
- [ ] All issue-specific test files properly discoverable by pytest
- [ ] No pytest collection warnings in agent-focused tests
- [ ] Test coverage verification for affected agent tests
- [ ] CI/CD pipeline properly executes all agent isolation tests
- [ ] Git tracking consistent for all agent test files
- [ ] Agent WebSocket bridge isolation tests run without warnings

## Priority Justification

**P2 (Medium) Priority:**
- Affects critical agent testing infrastructure
- Risk of missing important agent functionality tests
- Could impact $500K+ ARR Golden Path protection
- CI/CD reliability concerns for agent systems
- Security implications (multi-user isolation testing)

---

**Discovery:** Failing Test Gardener Issue #3 - Test Collection/Discovery Issues
**Generated:** 2025-09-14
**Context:** Agent-focused test infrastructure reliability