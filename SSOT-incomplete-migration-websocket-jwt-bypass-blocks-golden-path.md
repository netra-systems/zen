# SSOT-incomplete-migration-websocket-jwt-bypass-blocks-golden-path

**GitHub Issue:** [#300](https://github.com/netra-systems/netra-apex/issues/300)
**Status:** Discovery Complete - Planning Phase
**Priority:** CRITICAL - Golden Path Blocker
**Business Impact:** $500K+ ARR at risk

## SSOT Violation Summary

**Root Issue:** WebSocket auth bypasses UnifiedAuthInterface SSOT pattern, creating auth inconsistency that blocks Golden Path chat functionality.

**Critical Files Identified:**
- `netra_backend/app/websocket_core/user_context_extractor.py:45-67` - Direct JWT decoding bypass
- `netra_backend/app/websocket_core/auth.py` - Duplicate auth validation patterns
- `netra_backend/app/auth_integration/auth.py` - SSOT UnifiedAuthInterface implementation

**Violation Type:** incomplete-migration
**Pattern:** Legacy auth code coexists with SSOT implementation

## Discovery Phase Results

### SSOT Audit Findings:
1. **WebSocket JWT Bypass (CRITICAL)** - Lines 45-67 in user_context_extractor.py bypass auth service
2. **Duplicate Auth Validation** - Multiple auth handlers implementing same logic
3. **Legacy Integration Patterns** - Old auth patterns still active alongside SSOT

### Business Impact:
- Blocks Golden Path user login → AI responses flow
- Creates security inconsistency between WebSocket and HTTP auth
- Affects chat reliability (90% of platform value)

## Next Phase: Test Discovery and Planning

**Status:** In Progress
**Next Steps:** 
1. Discover existing tests protecting auth integration ✓ (Spawning sub-agent)
2. Plan SSOT migration test suite
3. Execute remediation plan

## Tracking Log
- 2025-09-10: Issue created, SSOT audit complete
- 2025-09-10: Critical violation identified in WebSocket auth flow
- 2025-09-10: Starting test discovery phase