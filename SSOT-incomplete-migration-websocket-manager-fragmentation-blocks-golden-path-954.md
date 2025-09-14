# SSOT-incomplete-migration-websocket-manager-fragmentation-blocks-golden-path-954

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/954
**Created:** 2025-09-14
**Priority:** P0 - Blocks Golden Path ($500K+ ARR)
**Status:** 🔄 IN PROGRESS - Step 0 Complete

## Problem Summary
Critical SSOT violation: **280+ files** with WebSocket manager patterns indicating massive fragmentation blocking Golden Path user flow.

### Competing SSOT Implementations Discovered
1. **`netra_backend/app/websocket_core/unified_manager.py`** - Claims "SSOT for WebSocket connection management"
2. **`netra_backend/app/websocket_core/websocket_manager.py`** - Claims "SSOT for WebSocket Management"  
3. **`netra_backend/app/websocket_core/manager.py`** - "Compatibility layer" creating circular imports

### Additional SSOT Violations Found
- **112+ Agent Registry files** - Multiple AgentRegistry implementations
- **Circular Import Dependencies** - Managers import from each other
- **Test Fragmentation** - 280+ test files with different manager patterns

## Work Progress

### ✅ Step 0: Discovery COMPLETED
- [x] **SSOT Audit Completed:** Identified 280+ WebSocket manager files via comprehensive grep search
- [x] **Competing Implementations Found:** 3 different managers claiming SSOT status
- [x] **Agent Registry Duplication:** 112+ files with AgentRegistry patterns detected  
- [x] **Circular Dependencies Identified:** Import chains creating fragmentation
- [x] **GitHub Issue Created:** Issue #954 with P0/SSOT labels
- [x] **Local Progress Tracker:** Created comprehensive documentation file

### 🔄 Step 1: Test Discovery and Planning IN PROGRESS
- [ ] **SPAWN SUB-AGENT:** Discover existing tests protecting WebSocket functionality
- [ ] **Identify Critical Tests:** Tests that must pass after SSOT consolidation
- [ ] **Plan New SSOT Tests:** Create validation tests for consolidation
- [ ] **Document Test Strategy:** Execution approach for validation

### 📋 Step 2: Execute Test Plan PENDING
- [ ] Create 20% new SSOT validation tests
- [ ] Run baseline test suite to establish current state
- [ ] Document current test results and expected failures

### 📋 Step 3: Plan Remediation PENDING  
- [ ] Choose canonical WebSocket manager implementation
- [ ] Design import path consolidation strategy
- [ ] Plan compatibility preservation approach

### 📋 Step 4: Execute Remediation PENDING
- [ ] Consolidate to single SSOT implementation
- [ ] Update all import paths across codebase
- [ ] Remove duplicate implementations safely

### 📋 Step 5: Test Fix Loop PENDING
- [ ] Run all affected test suites
- [ ] Fix any breaking changes introduced
- [ ] Verify Golden Path functionality works end-to-end

### 📋 Step 6: PR and Closure PENDING
- [ ] Create comprehensive pull request
- [ ] Link PR to automatically close issue #954
- [ ] Complete SSOT Gardener process cycle

## Technical Analysis

### Business Impact Assessment
- **Golden Path Dependency:** WebSocket events are critical infrastructure for chat functionality
- **Revenue Risk:** $500K+ ARR depends on reliable real-time WebSocket communication
- **User Experience Impact:** Inconsistent WebSocket event delivery affects agent progress visibility
- **System Stability:** Multiple managers create race conditions and initialization failures

### Import Fragmentation Pattern Detected
```
manager.py → websocket_manager.py → unified_manager.py
     ↑                ↓                      ↓
  Legacy imports  SSOT claim #2         SSOT claim #1
     ↑                                      ↓
  Compatibility                   _UnifiedWebSocketManagerImplementation
```

### Files Requiring Deep Analysis
- **Core Implementations:** 3 competing WebSocket managers
- **Test Infrastructure:** 280+ files with manager references to consolidate
- **Import Dependencies:** Full codebase scan required for consolidation planning
- **Agent Integration:** 112+ AgentRegistry files may have WebSocket dependencies

### Key Questions for Investigation
1. **Which WebSocket manager is actually used in production?**
2. **What are the differences between the 3 implementations?**
3. **Which imports are legacy vs current vs deprecated?**
4. **How many tests would break with consolidation?**
5. **What's the safe consolidation path with zero downtime?**

## Next Immediate Actions
1. **SPAWN SUB-AGENT (Step 1.1):** Discover existing WebSocket test coverage and protection
2. **Focus Area:** Identify mission-critical tests that protect Golden Path functionality  
3. **Safety First:** Ensure comprehensive test coverage before any consolidation attempts
4. **Business Priority:** Maintain $500K+ ARR chat functionality throughout process

## Success Criteria
- [ ] **Single WebSocket Manager SSOT** - One canonical implementation across codebase
- [ ] **Import Path Consolidation** - All imports point to single authoritative source  
- [ ] **Golden Path Validation** - WebSocket events deliver consistently for chat
- [ ] **Test Coverage Maintained** - All existing functionality preserved and tested
- [ ] **Performance Preserved** - No degradation in WebSocket event delivery speed
- [ ] **Zero Breaking Changes** - Backward compatibility maintained during transition

## Risk Mitigation Strategy
- **Atomic Changes:** One logical consolidation unit per commit for safe rollback
- **Feature Flags:** Gradual rollout capability if needed for high-risk changes
- **Test-First:** Comprehensive test coverage before any implementation changes
- **Staging Validation:** Full Golden Path validation in GCP staging environment
- **Rollback Plan:** Clear procedures for immediate reversal if issues detected

---
*SSOT Gardener Process - Issue #954 - Step 0 Complete, Step 1 Ready*