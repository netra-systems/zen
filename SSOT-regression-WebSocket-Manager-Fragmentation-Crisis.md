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

### Current Status: Ready for Step 1 - DISCOVER AND PLAN TEST

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