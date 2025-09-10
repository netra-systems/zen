# SSOT-recent-change-WebSocket-manager-fragmentation-blocks-golden-path-chat-functionality

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/186  
**Status:** DISCOVERY PHASE  
**Created:** 2025-09-10  
**Priority:** CRITICAL - $500K+ ARR Impact

## Issue Summary
WebSocket manager fragmentation creates multiple sources of truth, causing golden path chat functionality failures through auth handshake race conditions and silent WebSocket event delivery failures.

## Affected Files Identified
- `/netra_backend/app/websocket_core/unified_manager.py` (SSOT candidate)
- `/netra_backend/app/websocket_core/websocket_manager_factory.py` (Factory pattern)
- `/netra_backend/app/websocket_core/migration_adapter.py` (Adapter pattern)
- `/netra_backend/app/websocket_core/connection_manager.py` (Connection-specific)
- Multiple test WebSocket manager implementations

## Golden Path Impact Analysis
1. **User Authentication**: WebSocket auth handshake failures due to inconsistent manager state
2. **Agent Communication**: Race conditions in agent event delivery (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)  
3. **Real-time Updates**: Silent WebSocket failures preventing users from seeing AI response progress

## Work Progress Log

### Phase 0: Discovery (COMPLETED)
- [x] Identified 3 critical SSOT violations affecting golden path
- [x] Created GitHub issue #186
- [x] Created progress tracking file
- [x] Committed initial analysis

### Phase 1: Test Discovery (NEXT)
- [ ] Find existing WebSocket tests
- [ ] Identify protection against breaking changes
- [ ] Plan test coverage for SSOT refactor

### Phase 2: New SSOT Tests (PENDING)
- [ ] Execute test plan for 20% new SSOT tests
- [ ] Validate SSOT fixes

### Phase 3: SSOT Remediation Planning (PENDING)
- [ ] Plan consolidation of WebSocket managers
- [ ] Define unified interface
- [ ] Migration strategy

### Phase 4: SSOT Remediation Execution (PENDING)
- [ ] Implement unified WebSocket manager
- [ ] Remove duplicate implementations
- [ ] Update all references

### Phase 5: Test Fix Loop (PENDING)
- [ ] Run all tests
- [ ] Fix any breaking changes
- [ ] Ensure system stability

### Phase 6: PR and Closure (PENDING)
- [ ] Create pull request
- [ ] Cross-link with issue
- [ ] Close issue on merge

## Test Strategy Planning
- Focus on unit, integration (non-docker), and e2e GCP staging tests
- ~20% validating SSOT fixes, ~60% existing tests (with updates if needed), ~20% new tests
- NO docker-dependent tests in this phase

## Next Actions
1. SPAWN SUB AGENT for Phase 1: Test Discovery
2. Find existing WebSocket test collection
3. Plan test coverage for SSOT refactor