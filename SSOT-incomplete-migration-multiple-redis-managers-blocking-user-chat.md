# SSOT Gardener Progress: Multiple Redis Managers Blocking User Chat

**GitHub Issue:** [#190 - SSOT-incomplete-migration-multiple-redis-managers-blocking-user-chat](https://github.com/netra-systems/netra-apex/issues/190)

**Created:** 2025-09-10  
**Status:** IN PROGRESS  
**Severity:** CRITICAL - $500K+ ARR at risk  
**Business Impact:** Chat functionality failures and 1011 WebSocket errors blocking user AI interactions

## Problem Summary

**SSOT Violation:** 4 competing Redis manager implementations creating connection chaos, memory leaks, and inconsistent agent state caching.

### Competing Implementations Identified
1. **Primary SSOT**: `/netra_backend/app/redis_manager.py` (734 lines) - Main implementation with full feature set
2. **VIOLATION 1**: `/netra_backend/app/db/redis_manager.py` - Wrapper causing import confusion
3. **VIOLATION 2**: `/netra_backend/app/cache/redis_cache_manager.py` (576 lines) - Duplicate Redis operations  
4. **VIOLATION 3**: `/auth_service/auth_core/redis_manager.py` (401 lines) - Auth-specific Redis duplication

### Critical Impact on Golden Path
- **1011 WebSocket errors** from Redis connection readiness race conditions
- **Agent state persistence failures** affecting chat response delivery
- **76 files importing** different redis_manager implementations creating chaos
- **Memory leaks** from multiple connection pools
- **Connection instability** preventing reliable user chat experience

## Work Progress Tracker

### ✅ Step 0: SSOT Audit - COMPLETED
- [x] Discovered 4 competing Redis manager implementations
- [x] Identified direct connection to Golden Path user flow failures
- [x] Created GitHub issue #190
- [x] Created this progress tracking file

### 🔄 Step 1: Discover and Plan Tests - IN PROGRESS
- [ ] **1.1 DISCOVER EXISTING:** Find existing tests protecting Redis functionality
- [ ] **1.2 PLAN ONLY:** Plan unit/integration/e2e tests for SSOT Redis manager consolidation

### 📋 Step 2: Execute Test Plan - PENDING
- [ ] Create new SSOT tests (20% of effort)
- [ ] Validate with existing test framework

### 📋 Step 3: Plan SSOT Remediation - PENDING
- [ ] Plan consolidation strategy for 4→1 Redis manager
- [ ] Identify migration path for 76 importing files

### 📋 Step 4: Execute SSOT Remediation - PENDING
- [ ] Implement Redis manager consolidation
- [ ] Update all imports to use primary SSOT

### 📋 Step 5: Test Fix Loop - PENDING  
- [ ] Prove system stability maintained
- [ ] Run all tests until 100% pass

### 📋 Step 6: PR and Closure - PENDING
- [ ] Create pull request
- [ ] Close GitHub issue #190

## Technical Notes

### Files Requiring Attention
- **Primary SSOT to preserve**: `/netra_backend/app/redis_manager.py`
- **Violations to eliminate**: 
  - `/netra_backend/app/db/redis_manager.py` (wrapper elimination)
  - `/netra_backend/app/cache/redis_cache_manager.py` (merge operations into primary)
  - `/auth_service/auth_core/redis_manager.py` (auth-specific considerations)

### Golden Path Connection
This SSOT violation directly connects to:
- [`docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md`](docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md) findings
- WebSocket 1011 errors blocking chat functionality
- Redis readiness validation race conditions
- Agent state persistence failures

### Success Criteria
- [ ] Single Redis manager handling ALL Redis operations
- [ ] Zero 1011 WebSocket errors related to Redis connectivity
- [ ] All 76 importing files use primary SSOT Redis manager
- [ ] Chat functionality delivers reliable user AI interactions
- [ ] Memory usage reduced from eliminating duplicate connection pools

## Next Action
Spawn sub-agent to discover existing Redis tests and plan test strategy for SSOT consolidation.