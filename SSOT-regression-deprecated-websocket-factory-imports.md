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

**Step 1: DISCOVER AND PLAN TEST** ✅ COMPLETE
- ✅ Discover existing WebSocket tests (Step 1.1 COMPLETE)
- ✅ Plan test updates for SSOT compliance (Step 1.2 COMPLETE)
- ✅ Document test coverage gaps

### Step 1.1 Discovery Results ✅
**Existing Test Infrastructure Found:**
- **SSOT BaseTestCase:** Unified test framework ready
- **WebSocket Test Utilities:** Real service testing patterns established
- **Mission Critical Suite:** Business value protection tests operational
- **SSOT Import Registry:** Authoritative import mappings documented

**Current Test Success Rates:**
- WebSocket Integration: ~50% (due to deprecated imports)
- Target Post-SSOT: 90%+ success rate
- Mission Critical: Must achieve 100% for deployment

**Test Categories Identified:**
- Unit Tests: WebSocket manager component tests
- Integration Tests: WebSocket + Agent workflow (non-docker)
- E2E Tests: Complete event flow (GCP staging)
- Mission Critical: WebSocket event suite tests

### Step 1.2 Test Plan ✅
**SSOT Compliance Test Strategy (Following TEST_CREATION_GUIDE.md):**

**~60% Existing Tests (Update Required):**
- `netra_backend/tests/e2e/thread_test_fixtures.py` - Update import pattern
- `netra_backend/tests/integration/test_agent_execution_core.py` - Replace factory calls
- `netra_backend/tests/websocket_core/test_send_after_close_race_condition.py` - Canonical imports
- All tests using deprecated `create_websocket_manager()` function

**~20% New SSOT Tests (Create):**
- **Factory Migration Validation:** Test deprecated vs canonical patterns
- **User Context Test Helpers:** Simplified context creation utilities
- **SSOT Import Compliance:** Automated import pattern verification
- **Multi-User Isolation:** Validate factory pattern elimination prevents cross-user contamination

**~20% Validation Tests (Execute):**
- Mission Critical WebSocket Event Suite
- WebSocket Authentication Test (target: 100% pass rate)
- Integration tests without Docker
- Unit tests for component isolation

**Test Execution Strategy:**
- **NO DOCKER TESTS:** Unit, Integration (non-docker), E2E GCP staging only
- **Real Services First:** Follow SSOT principle - no mocks for integration/e2e
- **Success Criteria:** 90%+ pass rate post-SSOT update
- **Business Protection:** Mission Critical tests must achieve 100%

**Coverage Gaps Identified:**
- Missing factory migration validation tests
- Insufficient user context isolation testing
- Need automated SSOT import pattern compliance checks

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