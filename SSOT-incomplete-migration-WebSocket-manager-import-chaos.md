# SSOT WebSocket Manager Import Chaos - Issue #996

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/996
**Priority:** P0 - Golden Path Blocker
**Status:** Discovery Complete - Starting Test Planning

## Problem Summary
Multiple competing WebSocket manager imports causing initialization failures and blocking Golden Path chat functionality ($500K+ ARR impact).

## SSOT Violations Identified
1. **Import Chaos**: Multiple import paths for WebSocket managers
2. **SSOT Bypass**: Legacy direct imports bypassing `unified_manager.py`
3. **Inconsistent Usage**: Mixed usage of SSOT vs legacy patterns

## Discovery Phase Complete ✅
- Audit completed by sub-agent
- Top priority legacy violation identified
- GitHub issue created and tracked

## Next Steps
1. **Step 1**: Discover existing tests protecting WebSocket functionality
2. **Step 1.2**: Plan new SSOT tests to validate consolidation
3. **Step 2**: Execute test plan
4. **Step 3**: Plan SSOT remediation
5. **Step 4**: Execute remediation
6. **Step 5**: Test fix loop until all pass
7. **Step 6**: Create PR and close issue

## Work Log
- **2025-09-14**: Issue discovered and GitHub issue #996 created
- **Next**: Spawning sub-agent for test discovery and planning