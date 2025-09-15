# SSOT-incomplete-migration-WebSocket Manager Import Fragmentation Blocking Golden Path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1063
**Status:** DISCOVERY PHASE
**Priority:** P0 - Golden Path Blocker

## Problem Summary
- 25+ production files using legacy `UnifiedWebSocketManager` imports instead of SSOT `WebSocketManager`
- Directly blocks Golden Path: users login → AI responses
- $500K+ ARR at risk due to WebSocket functionality fragmentation

## Progress Tracker

### ✅ COMPLETED
- [x] Step 0: SSOT Audit Complete - WebSocket Manager import fragmentation identified as #1 priority
- [x] GitHub Issue Created: #1063
- [x] Progress Tracker (IND) Created

### 🔄 IN PROGRESS

### 📋 TODO
- [ ] Step 1: DISCOVER AND PLAN TEST
  - [ ] 1.1: Find existing WebSocket tests protecting against breaking changes
  - [ ] 1.2: Plan SSOT migration tests (20% new, 60% existing validation, 20% SSOT-specific)
- [ ] Step 2: Execute test plan for new SSOT tests
- [ ] Step 3: Plan SSOT remediation strategy
- [ ] Step 4: Execute SSOT remediation
- [ ] Step 5: Test fix loop - ensure all tests pass
- [ ] Step 6: PR and closure

## Key Files Identified
- Core WebSocket infrastructure in `netra_backend/app/`
- Legacy import patterns throughout codebase
- SSOT WebSocketManager implementation location TBD

## Business Impact
- **Golden Path Impact:** Direct blocker for user AI interaction flow
- **Revenue Risk:** $500K+ ARR dependent on WebSocket functionality
- **System Stability:** Import fragmentation creates maintenance burden

## Next Actions
1. Spawn sub-agent for Step 1: DISCOVER AND PLAN TEST
2. Identify exact legacy import locations and SSOT target
3. Plan migration strategy with test protection

---
**Last Updated:** 2025-09-14
**Next Review:** After Step 1 completion