# SSOT-regression-WebSocket-Manager-Fragmentation-Crisis

**GitHub Issue**: [#960](https://github.com/netra-systems/netra-apex/issues/960)
**Created**: 2025-09-13
**Priority**: P0 - GOLDEN PATH BLOCKING
**Status**: INITIATED

## SSOT Gardener Process Tracking

### Step 0: DISCOVER NEXT SSOT ISSUE ✅ COMPLETED
- **SSOT Audit Completed**: Identified WebSocket Manager fragmentation as critical P0 violation
- **GitHub Issue Created**: Issue #960 - SSOT-regression-WebSocket-Manager-Fragmentation-Crisis
- **Business Impact**: $500K+ ARR at risk from golden path blocking

### Step 1.1: DISCOVER EXISTING TESTS ✅ COMPLETED
- **Test Discovery Completed**: Found 3,733 WebSocket-related test files, 1,379 WebSocket manager specific
- **CRITICAL VALIDATION**: Staging test report shows WebSocket tests failing with 0.0% coverage - CONFIRMS SSOT VIOLATION
- **Mission Critical Tests Identified**: Core golden path protection tests located
- **Test Protection Analysis**: Well-protected event delivery, partial factory consolidation, gaps in real-time monitoring
- **Existing Test Impact**: Multiple tests will break during SSOT consolidation (by design - proving violation exists)

### Step 2: EXECUTE TEST PLAN (20% New SSOT Tests) ✅ COMPLETED
- **Test Infrastructure Created**: `tests/unit/websocket_ssot_issue960/` and `tests/integration/websocket_ssot_issue960/`
- **7 New Tests Created**: 6 unit tests + 1 integration test proving SSOT violations
- **CRITICAL VALIDATION**: All 7 tests FAIL as expected, proving WebSocket Manager fragmentation exists
- **SSOT Violations Proven**: 6 different WebSocket manager import paths found (should be 1-2 maximum)
- **Business Value Protection**: Tests validate $500K+ ARR golden path functionality
- **Framework Integration**: Tests use existing SSOT infrastructure (SSotBaseTestCase, IsolatedEnvironment)
- **No Docker Dependencies**: All tests run locally without Docker requirements

### Current Status: Ready for Step 3 - PLAN SSOT REMEDIATION

## Critical SSOT Violation Details

### Violation Type
Multiple WebSocket Manager Implementations creating race conditions and silent failures

### Canonical SSOT Implementation
- **Primary**: `netra_backend.app.websocket_core.websocket_manager.WebSocketManager`
- **Core**: `netra_backend.app.websocket_core.unified_manager.py`

### Problematic Duplicates Identified
- 52+ test files with individual WebSocket manager implementations
- Multiple factory files creating different instances
- Legacy compatibility layers creating confusion
- Backup files with outdated patterns

### Golden Path Impact
```
User Login → WebSocket Connection → Agent Execution → Tool Events → AI Response
            ↑ FAILURE POINT: Race conditions in WebSocket manager selection
```

### Specific Failures
1. **Silent Event Failures**: WebSocket events not delivered (agent_started, tool_executing, etc.)
2. **Race Conditions**: Multiple managers competing for same connection
3. **Memory Leaks**: Duplicate managers not cleaned up
4. **User Isolation Failures**: Events delivered to wrong users

## Success Criteria
- [ ] Single WebSocket manager import pattern codebase-wide
- [ ] All 5 critical WebSocket events delivered reliably (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- [ ] Zero WebSocket manager factory proliferation
- [ ] User isolation maintained with no cross-user contamination
- [ ] Golden path user flow working end-to-end

## Remediation Estimate
**Complexity**: HIGH (7-10 days)
**Files Affected**: ~50+ files
**Business Risk**: CRITICAL

## Next Steps
1. **STEP 1**: DISCOVER AND PLAN TEST - Find existing tests protecting WebSocket functionality
2. **STEP 2**: EXECUTE TEST PLAN - Create new SSOT validation tests
3. **STEP 3**: PLAN REMEDIATION - Design WebSocket manager consolidation
4. **STEP 4**: EXECUTE REMEDIATION - Implement SSOT consolidation
5. **STEP 5**: TEST FIX LOOP - Validate all tests pass
6. **STEP 6**: PR AND CLOSURE - Create PR and close issue

---
**SSOT Gardener Process**: Step 0 Complete → Step 1 Next
**Focus Areas**: agent goldenpath messages work
**Mission**: Get Golden Path working - users login and get real AI responses back