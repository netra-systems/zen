# SSOT-incomplete-migration-websocket-event-broadcasting-duplication

**GitHub Issue:** #1092 - https://github.com/netra-systems/netra-apex/issues/1092
**Priority:** P0 - Mission Critical
**Status:** DISCOVERY COMPLETE - PLANNING TESTS
**Created:** 2025-09-14

## Executive Summary

**CRITICAL SSOT VIOLATION:** Multiple WebSocket event broadcasting implementations fragmenting Golden Path ($500K+ ARR) user flow.

**Core Problem:** Legacy incomplete migration creating race conditions in real-time chat updates, authentication failures, and memory leaks.

## Technical Analysis

### Primary SSOT Violations Identified

1. **unified_emitter.py Duplication** (Lines 235-236, 259-260)
   - Multiple `emit_event` and `emit_event_batch` methods
   - Competing event broadcasting paths causing race conditions

2. **Cross-Module Broadcast Duplication**
   - `websocket_core/auth.py` - Duplicate `broadcast()` method
   - `websocket_core/handlers.py` - Another `broadcast()` method
   - `websocket_core/protocols.py` - `emit_critical_event()` duplication

3. **Legacy Factory Pattern**
   - `websocket_manager_factory.py` DEPRECATED but imported by 40+ files
   - Creates parallel WebSocket manager instances violating SSOT

### Business Impact on Golden Path

**User Experience Degradation:**
- Race conditions in chat message delivery
- Inconsistent real-time agent progress updates
- Authentication state synchronization failures
- Critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) lost or duplicated

**Technical Debt:**
- Memory leaks from multiple emitter instances
- Connection ID conflicts between managers
- Complex debugging due to multiple event paths

## Remediation Plan Overview

**Complexity: HIGH** - 40+ file dependencies requiring careful migration

### Phase 1: Event Broadcasting Consolidation
- Consolidate all event broadcasting to single SSOT method in `unified_emitter.py`
- Remove duplicate `broadcast()` methods from auth.py and handlers.py

### Phase 2: Factory Migration
- Migrate 40+ files from deprecated factory to canonical imports
- Remove `websocket_manager_factory.py` entirely

### Phase 3: Connection Management SSOT
- Unified connection lifecycle management
- Single source of truth for user connection state

## Progress Log

### 2025-09-14 - Discovery Phase Complete ✅
- [x] SSOT violation audit complete
- [x] GitHub issue #1092 created
- [x] Impact analysis on Golden Path documented
- [x] Remediation complexity assessment: HIGH
- [ ] **NEXT:** Test discovery and planning (Step 1)

## Test Strategy (Planned)

### Existing Tests to Protect (Step 1.1)
- Mission critical WebSocket event tests
- Integration tests for real-time chat functionality
- Authentication flow tests with WebSocket

### New Tests Required (Step 1.2)
- SSOT event broadcasting validation
- Race condition reproduction tests
- Memory leak detection for multiple emitters
- Connection ID conflict detection

## Files Requiring Changes

**High Impact (40+ dependencies):**
- `websocket_core/unified_emitter.py` - Primary consolidation
- `websocket_core/websocket_manager_factory.py` - REMOVAL
- All files importing deprecated factory

**Medium Impact:**
- `websocket_core/auth.py` - Remove duplicate broadcast()
- `websocket_core/handlers.py` - Remove duplicate broadcast()
- `websocket_core/protocols.py` - Remove emit_critical_event()

## Success Metrics

- [ ] Single event broadcasting path in codebase
- [ ] Zero race conditions in chat message delivery
- [ ] Memory usage stable under load
- [ ] All Golden Path events reliably delivered
- [ ] 40+ files successfully migrated from deprecated factory

## Risk Assessment

**HIGH RISK - Mission Critical System**
- Must preserve zero-downtime during migration
- Cannot break existing WebSocket connections
- User context isolation must be maintained
- All tests must pass after each phase

---
*Last Updated: 2025-09-14*
*Next Update: After test discovery and planning phase*