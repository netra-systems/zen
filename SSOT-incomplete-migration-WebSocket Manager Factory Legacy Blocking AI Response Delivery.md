# SSOT-incomplete-migration-WebSocket Manager Factory Legacy Blocking AI Response Delivery

**GitHub Issue:** [#1098](https://github.com/netra-systems/netra-apex/issues/1098)
**Status:** STEP 0 COMPLETE - Issue Created
**Priority:** P0 - Critical Golden Path Blocker

## 🎯 MISSION
Remove legacy WebSocket Manager factory pattern blocking AI response delivery to users.

## 📊 IMPACT ASSESSMENT
- **Golden Path Impact:** CRITICAL - Prevents AI responses reaching users
- **Business Value:** $500K+ ARR chat functionality at risk
- **Files Affected:** 732+ files with deprecated patterns
- **Legacy Code:** 588 lines in websocket_manager_factory.py

## 🔍 VIOLATION DETAILS

### Legacy Pattern (DEPRECATED)
```python
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
```

### SSOT Pattern (CANONICAL)
```python
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
```

### Critical Files Identified
1. `/netra_backend/app/websocket_core/websocket_manager_factory.py` (588 lines - REMOVE)
2. `/test_framework/fixtures/websocket_manager_mock.py` (deprecated mocks)
3. 732+ files with legacy imports

### WebSocket Events at Risk
- agent_started
- agent_thinking  
- tool_executing
- tool_completed
- agent_completed

## 📋 SSOT GARDENER PROCESS TRACKER

### COMPLETED ✅
- [x] **STEP 0:** SSOT Audit - Issue Discovery and GitHub Issue Creation

### IN PROGRESS 🔄
- [ ] **STEP 1:** DISCOVER AND PLAN TEST
- [ ] **STEP 2:** EXECUTE TEST PLAN (20% new SSOT tests)
- [ ] **STEP 3:** PLAN REMEDIATION OF SSOT
- [ ] **STEP 4:** EXECUTE REMEDIATION SSOT PLAN  
- [ ] **STEP 5:** TEST FIX LOOP
- [ ] **STEP 6:** PR AND CLOSURE

## 📝 DETAILED WORK LOG

### 2025-09-14 - STEP 0 COMPLETE
- ✅ SSOT Audit identified WebSocket Manager as #1 critical violation
- ✅ GitHub Issue #1098 created with full context
- ✅ Progress tracker initialized

### NEXT: STEP 1 - DISCOVER AND PLAN TEST
- Discover existing WebSocket tests protecting against breaking changes
- Plan new SSOT validation tests for WebSocket migration
- Focus on Golden Path WebSocket event delivery validation

## 🧪 TESTING REQUIREMENTS
- Mission Critical: `python tests/mission_critical/test_websocket_agent_events_suite.py`
- WebSocket SSOT: New tests for factory migration validation
- Golden Path: End-to-end WebSocket event delivery
- Integration: Real service WebSocket communication (no docker needed)

## 🚀 SUCCESS CRITERIA
- [ ] All 732+ files migrated to SSOT WebSocket manager
- [ ] Legacy factory code (588 lines) completely removed
- [ ] All 5 critical WebSocket events working end-to-end
- [ ] Golden Path chat functionality restored
- [ ] Mission critical tests passing
- [ ] No breaking changes introduced

## 📚 REFERENCE
- **CLAUDE.md Section 6:** WebSocket Agent Events (CRITICAL)
- **Golden Path:** `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md`
- **SSOT Registry:** `SSOT_IMPORT_REGISTRY.md`