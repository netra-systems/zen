# SSOT-incomplete-migration-WebSocket Factory Pattern Deprecation Violations (P0 CRITICAL)

**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/506
**Created**: 2025-09-11
**Priority**: P0 - CRITICAL BLOCKING
**Status**: 🔄 DISCOVERY PHASE

## Problem Summary
**BLOCKING GOLDEN PATH**: 49+ files using deprecated `get_websocket_manager_factory()` causing user isolation violations, log pollution, and WebSocket race conditions in GCP deployment.

## Audit Results
- **Primary violator**: `/netra_backend/app/routes/websocket_ssot.py` (lines 1394, 1425, 1451)
- **Total files affected**: 49+ using deprecated factory pattern
- **Test files affected**: 40+ requiring migration
- **Business impact**: $500K+ ARR at risk due to user context isolation failures

## SSOT Remediation Strategy
1. **Replace deprecated calls** with direct `WebSocketManager` imports
2. **Update critical routes** to use canonical implementation  
3. **Remove deprecated function** once migration complete
4. **Update test patterns** for proper manager usage

## Progress Tracking

### Phase 1: Discovery and Test Planning ⏳
- [x] SSOT audit completed
- [x] GitHub issue created (#506)
- [ ] Existing test discovery
- [ ] New test plan creation

### Phase 2: Test Implementation
- [ ] Create failing SSOT compliance tests
- [ ] Validate existing tests compatibility
- [ ] Run test baseline

### Phase 3: SSOT Remediation
- [ ] Replace factory calls in critical routes
- [ ] Update remaining 49+ file usages
- [ ] Remove deprecated factory function
- [ ] Update import patterns

### Phase 4: Validation
- [ ] All tests passing
- [ ] No deprecation warnings in logs
- [ ] Golden Path user flow functional
- [ ] GCP staging deployment clean

### Phase 5: PR and Closure
- [ ] Create pull request
- [ ] Link to issue closure
- [ ] Validate production readiness

## Next Actions
1. **SNST**: Discover existing tests protecting WebSocket factory usage
2. **SNST**: Plan new SSOT compliance tests
3. Begin systematic migration of deprecated calls

## Files Requiring Migration
- `/netra_backend/app/routes/websocket_ssot.py` (CRITICAL - lines 1394, 1425, 1451)
- 48+ additional files using `get_websocket_manager_factory()`
- 40+ test files using deprecated pattern

## Success Criteria
- ✅ All deprecated factory calls eliminated
- ✅ WebSocketManager as canonical SSOT
- ✅ User isolation maintained
- ✅ Golden Path operational
- ✅ Clean GCP deployment logs