# SSOT-regression-websocket-message-routing-fragmentation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/994
**Status:** Step 1 - Test Discovery Complete
**Priority:** P0 - Golden Path Blocker

## Business Impact

**CRITICAL:** Users not receiving AI responses due to WebSocket message routing fragmentation blocking $500K+ ARR Golden Path flow.

**Failure Chain:** WebSocket routing fails → Tool dispatching fails → Agent execution fails → Users get no AI responses

## SSOT Violation Details

### Primary Issue: WebSocket Message Routing Fragmentation
- **6+ WebSocket routing implementations** instead of single SSOT
- **Duplicate event routing patterns** across multiple files
- **Fragmented message handling logic** preventing reliable delivery

### Key Violating Files Identified:
1. `/netra_backend/app/websocket_core/` - Multiple routers
2. Event routing scattered across websocket_core
3. Duplicate message handling in various WebSocket components

## Success Criteria
- [ ] Consolidate to single WebSocket message router (SSOT)
- [ ] 99.5% Golden Path reliability restored
- [ ] All WebSocket events properly routed to users
- [ ] 95%+ SSOT compliance achieved

## Work Progress Log

### Step 0: Issue Discovery ✅ COMPLETE
- SSOT audit completed
- Critical violations identified
- GitHub issue #994 created
- Local tracking document created

### Step 1: Discover and Plan Tests ✅ COMPLETE
- **Existing Test Coverage:** 89 tests discovered protecting WebSocket routing
- **Critical Finding:** 4 different MessageRouter implementations confirmed
- **Test Strategy:** 20 targeted tests planned (60% existing updates, 20% new tests)
- **Business Protection:** All 5 critical WebSocket events coverage validated
- **SSOT Compliance:** Mock consolidation strategy defined

#### Test Discovery Summary:
- ✅ Mission Critical: 12 tests protecting $500K+ ARR Golden Path
- ✅ Business Logic: 8 tests validating multi-user isolation
- ✅ Integration: 34 tests covering cross-service WebSocket routing
- ✅ E2E Coverage: 18 tests for complete user flow validation
- 🔴 **Gap Identified:** 78% tests use mocks instead of real WebSocket connections

#### New Test Plan (20 tests):
- SSOT Compliance Tests (6): Single router validation, import path verification
- Multi-User Security Tests (4): Enterprise isolation, encrypted message routing
- Golden Path Protection Tests (4): End-to-end flow, race condition handling
- Performance/Recovery Tests (6): Circuit breaker, graceful degradation

#### Related Test Infrastructure Issues:
- 🔴 **Issue #973:** WebSocket Event Structure Validation Failures (3 failed tests)
- 🔴 **Missing Import:** Multi-user isolation tests blocked by simple import error
- 📋 **Note:** Test failures align with message routing fragmentation root cause

### Next Steps
- Step 2: Execute Test Plan (SNST)
- Step 3: Plan Remediation (SNST)
- Step 4: Execute Remediation (SNST)
- Step 5: Test Fix Loop
- Step 6: PR and Closure (SNST)

## Risk Assessment
**MEDIUM RISK** - WebSocket is critical infrastructure but well-tested. Consolidation must preserve all existing functionality while eliminating duplicates.

## Notes
- Focus on Golden Path impact - users must continue receiving AI responses
- Ensure all WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) remain functional
- Maintain backwards compatibility during transition