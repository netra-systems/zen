# SSOT-regression-deprecated-websocket-factory-imports

**GitHub Issue:** [#1066](https://github.com/netra-systems/netra-apex/issues/1066)
**Priority:** P0 - Mission Critical
**Status:** DISCOVERY COMPLETE
**Focus Area:** removing legacy

## 🚨 CRITICAL LEGACY SSOT VIOLATION

**BLOCKS GOLDEN PATH**: WebSocket factory imports causing race conditions and user isolation failures

### Files Requiring Remediation

1. **`netra_backend/tests/e2e/thread_test_fixtures.py:25`**
   - Current: `from netra_backend.app.websocket_core import create_websocket_manager`
   - Required: `from netra_backend.app.websocket_core.websocket_manager import WebSocketManager`
   - Status: ❌ PENDING

2. **`netra_backend/tests/integration/test_agent_execution_core.py:50`**
   - Current: Deprecated factory import
   - Required: Canonical WebSocket manager import
   - Status: ❌ PENDING

3. **`netra_backend/tests/websocket_core/test_send_after_close_race_condition.py:20`**
   - Current: Direct factory import
   - Required: SSOT WebSocket manager pattern
   - Status: ❌ PENDING

### Business Impact
- **Revenue Risk:** $500K+ ARR Golden Path dependency
- **Customer Experience:** Silent WebSocket failures block AI responses
- **Security:** Multi-user data contamination via factory pattern
- **Development Velocity:** Legacy patterns block SSOT migration

### Success Criteria
- [ ] All 3 files updated to canonical imports
- [ ] WebSocket authentication test: 100% consistent pass rate
- [ ] Zero WebSocket 1011 errors in staging
- [ ] Multi-user isolation vulnerabilities eliminated
- [ ] All existing tests continue to pass

### Process Status

**Step 0: DISCOVERY** ✅ COMPLETE
- ✅ Identified P0 critical violation
- ✅ GitHub issue created: #1066
- ✅ Progress tracker initiated

**Step 1: DISCOVER AND PLAN TEST** ❌ PENDING
- [ ] Discover existing WebSocket tests
- [ ] Plan test updates for SSOT compliance
- [ ] Document test coverage gaps

**Step 2: EXECUTE TEST PLAN** ❌ PENDING
- [ ] Create/update SSOT compliance tests
- [ ] Validate failing tests reproduce violation

**Step 3: PLAN REMEDIATION** ❌ PENDING
- [ ] Detailed remediation strategy
- [ ] Import replacement patterns
- [ ] Backwards compatibility plan

**Step 4: EXECUTE REMEDIATION** ❌ PENDING
- [ ] Update all 3 critical files
- [ ] Verify SSOT compliance
- [ ] Maintain test functionality

**Step 5: TEST FIX LOOP** ❌ PENDING
- [ ] Run all affected tests
- [ ] Fix any breaking changes
- [ ] Verify system stability

**Step 6: PR AND CLOSURE** ❌ PENDING
- [ ] Create pull request
- [ ] Link to issue #1066
- [ ] Verify all success criteria met

### Notes
- Legacy factory pattern violates User Context Architecture
- Factory creates import-time initialization causing race conditions
- SSOT WebSocketManager requires explicit user_context and authorization_token
- Critical for Golden Path: login → AI responses flow

**Last Updated:** 2025-01-14 Initial Discovery