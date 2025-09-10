# SSOT WebSocket Routes Massive Duplication - Blocking Golden Path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/185
**Status:** DISCOVERED - Ready for test discovery and planning
**Priority:** P0 - CRITICAL - BLOCKING golden path user flow

## Problem Summary

**CRITICAL SSOT VIOLATION:** 4 competing WebSocket route implementations with 4,206 total lines of duplicated code blocking reliable user connections for golden path (login → AI responses).

### Competing Route Files
1. **Primary Route:** `/netra_backend/app/routes/websocket.py` - 3,166 lines (40,453 tokens!)
2. **Factory Route:** `/netra_backend/app/routes/websocket_factory.py` - 615 lines  
3. **Isolated Route:** `/netra_backend/app/routes/websocket_isolated.py` - 410 lines
4. **Unified Shim:** `/netra_backend/app/routes/websocket_unified.py` - 15 lines (backward compatibility)

## Business Impact
- **Revenue Risk:** $500K+ ARR chat functionality blocked
- **User Experience:** Connection routing confusion causes login failures
- **Maintenance Burden:** 4,206 lines of duplicate code across 4 files
- **Development Velocity:** Multiple competing implementations slow bug fixes

## Golden Path Blocking Issues
- Multiple WebSocket endpoints create routing confusion
- Race conditions during connection establishment
- Inconsistent connection handling patterns
- Authentication flow differences between routes

## Discovery Status: ✅ COMPLETE

### SSOT Violations Found:
- [x] WebSocket Route Duplication (P0 - CRITICAL)
- [x] Authentication Chaos (97 files) 
- [x] Agent Event Duplication (85 files)
- [x] Manager Class Proliferation (11+ classes)
- [x] Send Pattern Inconsistency (65 files)

## Next Steps

### 1. DISCOVER AND PLAN TEST (In Progress)
- [ ] Find existing tests protecting WebSocket routes
- [ ] Plan test updates for SSOT consolidation
- [ ] Design failing tests to reproduce SSOT violations

### 2. EXECUTE TEST PLAN
- [ ] Create new SSOT validation tests
- [ ] Validate test failures demonstrate SSOT issues

### 3. PLAN REMEDIATION
- [ ] Design SSOT WebSocket route consolidation
- [ ] Plan feature flag approach for different behaviors
- [ ] Design migration strategy

### 4. EXECUTE REMEDIATION
- [ ] Implement SSOT WebSocket route
- [ ] Migrate functionality from 4 routes to 1
- [ ] Update all references and imports

### 5. TEST FIX LOOP
- [ ] Validate all existing tests pass
- [ ] Fix any regressions introduced
- [ ] Ensure golden path functionality restored

### 6. PR AND CLOSURE  
- [ ] Create pull request
- [ ] Link to close this issue
- [ ] Deploy and validate in staging

## Progress Log

**2025-09-10:** Issue discovered and created. Massive 4,206 lines of duplicate WebSocket route code identified as P0 blocker for golden path user flow.