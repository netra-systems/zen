# SSOT-incomplete-migration-WebSocket-Factory-Pattern-Deprecation-Violations

**GitHub Issue**: [#541](https://github.com/netra-systems/netra-apex/issues/541)  
**Priority**: P0 - CRITICAL (Blocking Golden Path)  
**Created**: 2025-09-12  
**Status**: 🚨 **ACTIVE** - Blocking $500K+ ARR  

## 📊 Executive Summary

**Business Impact**: WebSocket Factory Pattern deprecation violations are blocking the Golden Path (users login → get AI responses) affecting $500K+ ARR due to user isolation failures.

**Core Problem**: 49+ files still using deprecated `get_websocket_manager_factory()` causing WebSocket race conditions in GCP deployment and preventing users from receiving AI responses.

---

## 🎯 Current Phase: Step 0 - Issue Discovery & Planning

### ✅ COMPLETED WORK

#### 0) Discover Next SSOT Issue (SSOT AUDIT)
- [x] **SSOT Audit Complete** - Identified critical P0 violation
- [x] **GitHub Issue Created** - Issue #541 created with critical label
- [x] **Progress Tracker Created** - This document (IND) established

**Key Findings from Audit**:
- **49+ files** using deprecated `get_websocket_manager_factory()` pattern
- **Primary violation location**: `netra_backend/app/routes/websocket_ssot.py` lines 1394, 1425, 1451
- **Business impact**: User context isolation failures causing WebSocket race conditions
- **Golden Path impact**: Prevents users from receiving AI responses (90% of platform value)

---

## 🔍 Technical Details

### Deprecated Pattern (CURRENT - BROKEN):
```python
# DEPRECATED - CAUSES USER ISOLATION FAILURES
manager_factory = get_websocket_manager_factory()
manager = manager_factory.create_for_user(user_context)
```

### SSOT Pattern (TARGET - WORKING):
```python
# SSOT - PROPER USER ISOLATION  
from netra_backend.app.websocket_core.unified_manager import WebSocketManager
manager = WebSocketManager.create_for_user(user_context)
```

### Files Requiring Migration (49+ identified):
- `netra_backend/app/routes/websocket_ssot.py` (lines 1394, 1425, 1451) **PRIMARY TARGET**
- 46+ additional files across codebase (detailed list to be generated)

---

## 📋 SSOT Gardener Process Status

### Phase 0: ✅ COMPLETE - Issue Discovery 
- [x] SSOT Audit conducted
- [x] GitHub Issue #540 created
- [x] Priority P0 assigned (blocking Golden Path)
- [x] Progress tracker (IND) established

### Phase 1: 🔄 NEXT - Discover and Plan Tests
**Tasks**:
- [ ] **DISCOVER EXISTING**: Find current tests protecting WebSocket functionality
- [ ] **PLAN TEST UPDATES**: Design tests for SSOT refactor validation
- [ ] **IDENTIFY GAPS**: Plan new tests to reproduce SSOT violation (failing tests)

### Phase 2: 📋 PENDING - Execute Test Plan
- [ ] Create new SSOT validation tests (20% of effort)
- [ ] Audit and review existing tests (60% of effort)  
- [ ] Run test validation (20% of effort)

### Phase 3: 📋 PENDING - Plan SSOT Remediation
- [ ] Plan migration strategy for 49+ files
- [ ] Identify atomic units for safe refactoring
- [ ] Design rollback strategy

### Phase 4: 📋 PENDING - Execute SSOT Remediation
- [ ] Execute planned migration
- [ ] Replace deprecated factory calls
- [ ] Verify user isolation working

### Phase 5: 📋 PENDING - Test Validation Loop
- [ ] Prove system stability maintained
- [ ] Fix any breaking changes introduced
- [ ] Ensure all tests pass

### Phase 6: 📋 PENDING - PR and Closure
- [ ] Create pull request
- [ ] Cross-link with issue #540
- [ ] Close issue on PR merge

---

## 🧪 Test Strategy

### Existing Tests to Protect:
- Mission critical WebSocket tests: `python tests/mission_critical/test_websocket_agent_events_suite.py`
- WebSocket state regression: `python netra_backend/tests/critical/test_websocket_state_regression.py`
- E2E WebSocket connection: `python tests/e2e/test_websocket_dev_docker_connection.py`

### New Tests Required:
- Factory deprecation validation tests
- User isolation verification tests  
- WebSocket race condition reproduction tests (failing → passing)

### Test Execution Constraints:
- **NO DOCKER REQUIRED** - Use staging GCP environment for E2E
- Focus on unit, integration (non-docker), and E2E staging tests
- Follow `reports/testing/TEST_CREATION_GUIDE.md`

---

## 💼 Business Value Protection

**Revenue at Risk**: $500K+ ARR
**Core Value Impact**: Chat functionality = 90% of platform value
**User Experience**: Golden Path (login → AI responses) currently broken
**Deployment Impact**: WebSocket race conditions preventing reliable GCP deployment

---

## 🔗 Related Documentation

- **CLAUDE.md**: SSOT compliance requirements
- **Definition of Done**: `reports/DEFINITION_OF_DONE_CHECKLIST.md` - WebSocket module
- **Master Status**: `reports/MASTER_WIP_STATUS.md` - WebSocket health tracking
- **GitHub Style Guide**: `@GITHUB_STYLE_GUIDE.md` for issue updates

---

## 📝 Process Log

### 2025-09-12 14:00 - Issue Discovery Phase Complete
- SSOT audit identified critical P0 violation
- GitHub Issue #540 created successfully  
- Progress tracker established
- **NEXT**: Spawn sub-agent for test discovery and planning

---

**Last Updated**: 2025-09-12 14:00  
**Next Update**: After test discovery phase completion