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

### Phase 1: Discovery and Test Planning ✅
- [x] SSOT audit completed  
- [x] GitHub issue created (#506)
- [x] Existing test discovery - **73+ tests identified**
- [x] New test plan creation - **4 new test files planned**

#### New SSOT Test Plan
**1. SSOT Violation Detection** (`tests/unit/ssot/test_websocket_factory_deprecation_violations.py`)
- Detects 49+ files using deprecated factory (SHOULD FAIL initially)
- Enforces WebSocketManager as canonical SSOT

**2. Migration Safety** (`tests/integration/ssot/test_websocket_manager_migration_safety.py`)  
- User isolation preservation (NO DOCKER)
- Security guarantee maintenance

**3. SSOT Compliance** (`tests/mission_critical/test_ssot_websocket_compliance.py`)
- Critical business value protection  
- SSOT compliance enforcement

**4. Golden Path Protection** (`tests/e2e/staging/test_websocket_ssot_golden_path.py`)
- Complete user login → AI response flow validation
- Real WebSocket testing in staging GCP

#### Test Discovery Results
**MISSION CRITICAL (8 files)**: Factory security, user isolation, Golden Path protection
- `tests/mission_critical/test_websocket_factory_security_validation.py` - User isolation
- `tests/e2e/golden_path/test_complete_golden_path_business_value.py` - $500K+ ARR protection
- Resource leak detection and production scenarios (4 additional files)

**HIGH RISK (17+ tests)**: Direct factory usage - WILL BREAK
- Tests using `get_websocket_manager_factory()` directly
- Require immediate migration to `WebSocketManager()` pattern

**LOW RISK (25+ tests)**: Direct WebSocketManager usage - WILL CONTINUE WORKING
- Already using canonical SSOT pattern

**MIXED IMPACT (31+ tests)**: Factory pattern validation tests
- Need updates to validate new direct instantiation pattern

### Phase 2: Test Implementation ⏳
- [x] Create failing SSOT compliance tests - **55+ violations detected!**
- [x] **Test 1/4**: `test_websocket_factory_deprecation_violations.py` ✅ (FAILING as designed)
- [ ] **Test 2/4**: `test_websocket_manager_migration_safety.py` (Integration - No Docker)
- [ ] **Test 3/4**: `test_ssot_websocket_compliance.py` (Mission Critical)
- [ ] **Test 4/4**: `test_websocket_ssot_golden_path.py` (E2E Staging)
- [ ] Validate existing tests compatibility  
- [ ] Run test baseline

#### Test 1 Results: VIOLATION DETECTION SUCCESS ✅
- **55 deprecated factory usages** found across **14 files** (exceeded estimate of 49+)
- **SSOT Compliance**: 94.3% current (Target: 100%)
- **Critical violations confirmed**: websocket_ssot.py lines 1394, 1425, 1451
- Tests FAILING as designed - ready to guide remediation

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