# SSOT-ID-Generation-Incomplete-Migration-Authentication-WebSocket-Factories

**GitHub Issue**: #841
**Priority**: P0 - BLOCKS GOLDEN PATH
**Status**: In Progress - Step 0 Complete

## Issue Summary
20+ critical files still using `uuid.uuid4()` instead of UnifiedIdGenerator SSOT, causing race conditions, ID collisions, and user isolation failures in Golden Path.

## Critical Files Identified
1. `netra_backend/app/auth_integration/auth.py:160` - Session ID generation
2. `netra_backend/app/websocket_core/unified_websocket_auth.py:1303` - Connection ID generation
3. `netra_backend/app/factories/redis_factory.py:594` - Client ID generation
4. `netra_backend/app/factories/clickhouse_factory.py:522` - Client ID generation
5. `netra_backend/app/schemas/audit_models.py:41` - Audit record IDs

## Business Impact
- **Revenue Risk**: $500K+ ARR at risk
- **Security**: Potential cross-user data leakage from ID collisions
- **User Experience**: Authentication and WebSocket connection failures

## Progress Log

### Step 0 - SSOT Audit Complete ✅
- [x] Discovered critical SSOT violation
- [x] Created GitHub issue #841
- [x] Created tracking file
- [x] Ready for step 1 - Test Discovery

### Step 1 - Discover and Plan Tests (PENDING)
- [ ] Find existing tests protecting against SSOT ID generation changes
- [ ] Plan new tests to validate SSOT compliance
- [ ] Update tracking file

### Step 2 - Execute New Test Plan (PENDING)
- [ ] Create new SSOT validation tests
- [ ] Run non-docker tests only
- [ ] Verify tests fail appropriately before fix

### Step 3 - Plan SSOT Remediation (PENDING)
- [ ] Plan UnifiedIdGenerator migration strategy
- [ ] Identify all uuid.uuid4() usage
- [ ] Plan atomic commit strategy

### Step 4 - Execute Remediation (PENDING)
- [ ] Replace uuid.uuid4() calls with UnifiedIdGenerator
- [ ] Validate user isolation maintained
- [ ] Run all tests

### Step 5 - Test Fix Loop (PENDING)
- [ ] Run all affected tests
- [ ] Fix any breaking changes
- [ ] Verify Golden Path functionality

### Step 6 - PR and Closure (PENDING)
- [ ] Create pull request
- [ ] Link to issue #841 for auto-close
- [ ] Merge after review

## Definition of Done
- [ ] All uuid.uuid4() calls replaced with UnifiedIdGenerator
- [ ] User isolation tests passing
- [ ] Golden Path authentication flow working
- [ ] WebSocket connections using consistent ID generation
- [ ] No cross-user data leakage in tests