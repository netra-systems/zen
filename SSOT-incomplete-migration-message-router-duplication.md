# SSOT-incomplete-migration-message-router-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1074
**Priority:** P0 - Golden Path Blocking
**Focus:** Message Routing SSOT Violations
**Revenue at Risk:** $500K+ ARR

## ISSUE SUMMARY

Critical SSOT violations in message routing blocking Golden Path (users login → get AI responses). Multiple routing implementations causing cross-user contamination and unreliable message delivery.

## PRIMARY VIOLATIONS IDENTIFIED

### 1. **CRITICAL: Duplicate Event Router Implementations**
- **Files:**
  - `netra_backend/app/services/websocket_event_router.py` (Legacy singleton)
  - `netra_backend/app/services/user_scoped_websocket_event_router.py` (User-scoped factory)
  - `netra_backend/app/services/websocket_broadcast_service.py` (SSOT consolidation)
- **Violation:** THREE different `broadcast_to_user()` implementations
- **Golden Path Impact:** Cross-user event leakage, inconsistent event delivery, race conditions

### 2. **HIGH: Message Handler Routing Duplication**
- **Files:**
  - `netra_backend/app/websocket_core/handlers.py` (MessageRouter class)
  - `netra_backend/app/services/websocket/quality_message_router.py` (QualityMessageRouter)
- **Violation:** TWO separate message routers with overlapping functionality
- **Golden Path Impact:** Inconsistent message handling, duplicate routing logic

### 3. **MEDIUM: WebSocket Bridge Routing Confusion**
- **File:** `netra_backend/app/services/agent_websocket_bridge.py`
- **Violation:** Incomplete singleton removal, unclear routing responsibilities
- **Golden Path Impact:** Event delivery inconsistency

## PROCESS TRACKING

### ✅ COMPLETED STEPS
- [x] **Step 0.1:** SSOT Audit completed - Critical violations identified
- [x] **Step 0.2:** GitHub issue created (#1074)
- [x] **Action:** IND created (this file)
- [x] **Action:** GCIFS (Git commit in progress)

### 🔄 CURRENT STEP: Step 1 - DISCOVER AND PLAN TEST

### 📋 UPCOMING STEPS
- [ ] **Step 1.1:** DISCOVER EXISTING tests protecting message routing
- [ ] **Step 1.2:** PLAN test creation for SSOT refactor validation
- [ ] **Step 2:** EXECUTE TEST PLAN for 20% new SSOT tests
- [ ] **Step 3:** PLAN REMEDIATION of SSOT violations
- [ ] **Step 4:** EXECUTE REMEDIATION SSOT PLAN
- [ ] **Step 5:** ENTER TEST FIX LOOP - prove stability maintained
- [ ] **Step 6:** PR AND CLOSURE

## REMEDIATION PLAN (PRIORITY ORDER)

### **P0 - IMMEDIATE (Golden Path Blocking)**
1. **CONSOLIDATE BROADCAST FUNCTIONS:**
   - Enforce use of `WebSocketBroadcastService` as ONLY broadcast implementation
   - Remove duplicate broadcast methods from router classes
   - Add deprecation warnings to legacy broadcast functions

2. **UNIFIED MESSAGE ROUTING:**
   - Make `MessageRouter` in handlers.py the SSOT for ALL message routing
   - Migrate `QualityMessageRouter` functionality into MessageRouter
   - Remove duplicate routing logic

### **P1 - HIGH (User Isolation Security)**
3. **ENFORCE USER-SCOPED ROUTING:**
   - Deprecate singleton `WebSocketEventRouter` completely
   - Force all routing through `UserScopedWebSocketEventRouter` factory pattern
   - Add validation to prevent cross-user event contamination

### **P2 - MEDIUM (Architecture Cleanup)**
4. **BRIDGE PATTERN CLARIFICATION:**
   - Complete singleton removal from AgentWebSocketBridge
   - Clearly separate bridge responsibilities from routing responsibilities
   - Establish single path for agent events

## BUSINESS IMPACT

### GOLDEN PATH FAILURES RESOLVED
- ❌ Cross-user event contamination (security/GDPR violation)
- ❌ Agent responses not reaching correct users
- ❌ Inconsistent chat functionality reliability

### EXPECTED OUTCOMES
- ✅ Single SSOT message routing implementation
- ✅ Reliable agent event delivery to correct users
- ✅ Eliminated cross-user data contamination
- ✅ Consistent chat functionality

## TEST VALIDATION COMMANDS

```bash
# Mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_message_router_ssot_enforcement.py

# SSOT validation
python tests/unit/services/test_ssot_broadcast_consolidation.py
```

## NOTES

- **SAFETY FIRST:** All changes must pass existing tests or update tests appropriately
- **ATOMIC COMMITS:** Each remediation step should be one atomic unit of change
- **USER ISOLATION:** Critical that cross-user contamination is eliminated
- **GOLDEN PATH:** Primary focus is reliable user login → AI response flow

---

**Created:** 2025-09-14
**Last Updated:** 2025-09-14
**Status:** In Progress - Step 0 Complete