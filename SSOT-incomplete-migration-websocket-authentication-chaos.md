# SSOT Gardener Progress: WebSocket Authentication Chaos

**Issue**: #1076 - SSOT-incomplete-migration-websocket-authentication-chaos  
**GitHub Link**: https://github.com/netra-systems/netra-apex/issues/1076  
**Focus**: removing legacy  
**Priority**: P0-critical (Golden Path blocker)

## Problem Summary

**CRITICAL**: Duplicate WebSocket authentication classes in same file blocking Golden Path
- **File**: `netra_backend/app/websocket_core/unified_websocket_auth.py` (2000+ lines)
- **Issue**: Two complete `UnifiedWebSocketAuthenticator` classes exist simultaneously
- **Impact**: Authentication chaos prevents users login → AI responses flow
- **Business Risk**: $500K+ ARR chat functionality unreliable

## Detailed Analysis

### Duplicate Classes Found:
1. **Primary SSOT Implementation** (Lines 288-1492): Working authenticator
2. **Legacy Duplicate** (Lines 1494-1656): Deprecated but still active

### Duplicate Functions Found:
1. **SSOT Function** (Lines 1272-1301): `authenticate_websocket_ssot()` - THE ONLY entry point
2. **Legacy Function** (Lines 1454-1491): `authenticate_websocket_connection()` - DEPRECATED wrapper

## Golden Path Impact
- ❌ **Login**: Authentication chaos prevents reliable JWT validation
- ❌ **WebSocket Connection**: Duplicate authenticators cause failures 
- ❌ **Agent Execution**: Broken auth prevents agent responses
- ❌ **Chat**: $500K+ ARR chat system fails from race conditions

## Process Status

### ✅ Step 0: SSOT Audit Complete
- [x] Critical legacy violation identified
- [x] GitHub issue created: #1076
- [x] Progress tracker created
- [x] Business impact assessed

### 🔄 Step 1: Discover and Plan Tests (NEXT)
- [ ] Find existing WebSocket authentication tests
- [ ] Plan test coverage for SSOT consolidation
- [ ] Identify tests that must continue passing
- [ ] Plan new failing tests to reproduce violation

### ⏳ Step 2: Execute Test Plan
- [ ] Create new SSOT validation tests
- [ ] Run tests without Docker
- [ ] Validate test failure patterns

### ⏳ Step 3: Plan SSOT Remediation 
- [ ] Detailed remediation plan
- [ ] Risk assessment
- [ ] Backwards compatibility strategy

### ⏳ Step 4: Execute Remediation
- [ ] Remove duplicate class (lines 1494-1656)
- [ ] Remove deprecated function (lines 1454-1491) 
- [ ] Consolidate to single SSOT entry point
- [ ] Update all imports

### ⏳ Step 5: Test Fix Loop
- [ ] Run all existing tests
- [ ] Fix any breaking changes
- [ ] Validate system stability
- [ ] Run startup tests

### ⏳ Step 6: PR and Closure
- [ ] Create pull request
- [ ] Cross-link to issue #1076
- [ ] Validate all tests passing

## Technical Details

### Files Requiring Updates:
- `netra_backend/app/websocket_core/unified_websocket_auth.py` (PRIMARY)
- Any imports of deprecated authentication methods
- Tests referencing old authentication patterns

### Key Functions to Remove:
- `UnifiedWebSocketAuthenticator` class (lines 1494-1656) - DUPLICATE
- `authenticate_websocket_connection()` (lines 1454-1491) - DEPRECATED

### SSOT Consolidation Target:
- Single `authenticate_websocket_ssot()` entry point (lines 1272-1301)
- Single `UnifiedWebSocketAuthenticator` class (lines 288-1492)

## Notes
- This is an incomplete migration where both old and new patterns coexist
- Must maintain backwards compatibility during transition
- WebSocket handshake reliability critical for Golden Path
- Authentication failures directly block chat functionality

---
**Last Updated**: 2025-09-14  
**Next Action**: Spawn sub-agent for Step 1 (Discover and Plan Tests)