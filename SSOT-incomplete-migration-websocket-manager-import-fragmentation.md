# SSOT-incomplete-migration-websocket-manager-import-fragmentation

**GitHub Issue:** [#1090](https://github.com/netra-systems/netra-apex/issues/1090)
**Priority:** P0 - Golden Path Blocker
**Created:** 2025-01-14
**Status:** 🔄 Phase 1 - Test Discovery and Planning

## Mission Critical Problem

**WebSocket Manager Import Fragmentation** is the #1 priority SSOT violation blocking the golden path:
- **Business Impact:** $500K+ ARR - Users cannot receive real-time AI responses
- **Technical Impact:** 25+ files using deprecated factory pattern causing race conditions
- **User Impact:** Golden Path broken - login → AI responses not working reliably

## Evidence

```
DeprecationWarning: netra_backend.app.websocket_core.websocket_manager_factory is DEPRECATED.
Use 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' instead.
This module will be removed in v2.0 as part of SSOT consolidation.
```

## Key Violating Files (25+ identified)

### Mission Critical Files
- `netra_backend/app/services/agent_websocket_bridge.py:3229` - **CRITICAL**
- `netra_backend/app/factories/websocket_bridge_factory.py`
- `netra_backend/app/factories/tool_dispatcher_factory.py`
- `netra_backend/app/admin/corpus/compatibility.py`

### SSOT Pattern Fix Required

```python
# ❌ VIOLATION (Deprecated - causes race conditions)
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

# ✅ CORRECT (SSOT Canonical)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
```

## Progress Tracking

### Phase 0: Discovery and Issue Creation ✅ COMPLETE
- [x] SSOT audit completed - identified WebSocket import fragmentation as #1 priority
- [x] GitHub issue #1090 created with P0 priority
- [x] Local IND tracking file created
- [x] Business impact assessment: $500K+ ARR direct golden path blocker

### Phase 1: Test Discovery and Planning 🔄 IN PROGRESS
- [ ] Discover existing WebSocket manager tests
- [ ] Identify tests protecting against import fragmentation
- [ ] Plan new SSOT validation tests (~20% of work)
- [ ] Plan test updates for existing coverage (~60% of work)
- [ ] Validate mission critical test deprecation warnings

### Phase 2: New SSOT Test Creation 🔄 PENDING
- [ ] Create failing tests reproducing import fragmentation violations
- [ ] Implement SSOT import pattern validation tests
- [ ] Run tests to confirm they fail with current deprecated imports
- [ ] Ensure tests pass with canonical SSOT imports

### Phase 3: SSOT Remediation Planning 🔄 PENDING
- [ ] Plan migration from deprecated factory to canonical imports
- [ ] Identify all 25+ files requiring WebSocket import updates
- [ ] Create atomic commit strategy for safe migration
- [ ] Plan removal of deprecated factory components

### Phase 4: SSOT Remediation Execution 🔄 PENDING
- [ ] Execute migration of all 25+ files to canonical imports
- [ ] Remove deprecated `websocket_manager_factory.py`
- [ ] Update all WebSocket factory usage patterns
- [ ] Ensure no breaking changes to existing functionality

### Phase 5: Test Fix Loop - Proof of Stability 🔄 PENDING
- [ ] Run all existing WebSocket tests - must pass
- [ ] Run mission critical test suite - no deprecation warnings
- [ ] Run startup tests - no import/factory issues
- [ ] Validate golden path: users login → receive AI responses
- [ ] Repeat until ALL tests pass (max 10 cycles)

### Phase 6: PR and Closure 🔄 PENDING
- [ ] Create pull request linking to issue #1090
- [ ] Validate all tests passing before merge
- [ ] Close issue #1090 on PR merge
- [ ] Update SSOT compliance tracking

## Business Impact Assessment

This SSOT remediation directly protects:
- **Golden Path reliability**: Users login → get real AI responses
- **Real-time chat experience**: 90% of platform value
- **WebSocket stability**: Elimination of race conditions and 1011 errors
- **System compliance**: Complete SSOT pattern adoption

## Technical Notes

- **Deprecation Timeline**: Factory pattern marked for removal in v2.0
- **Test Coverage**: Focus on non-docker tests (unit, integration no-docker, e2e gcp staging)
- **Migration Risk**: Medium - import path consolidation across many files
- **Success Metric**: Zero deprecation warnings in mission critical tests

---

**Status:** 🔄 Phase 1 In Progress - Test Discovery and Planning
**Last Updated:** 2025-01-14
**Next Action:** Spawn sub-agent for test discovery phase