# SSOT-incomplete-migration-lifecycle-manager-naming-violation

**GitHub Issue:** #202  
**Status:** Test Strategy Planning Complete  
**Created:** 2025-09-10

## Issue Summary
UnifiedLifecycleManager violates business-focused naming conventions. Should be renamed to SystemLifecycle per Manager Renaming Plan.

## Impact Analysis
- **Files affected:** ~42 imports across services
- **Business Impact:** Confusing "Manager" terminology affects developer clarity and maintenance velocity
- **SSOT Tier:** Tier 2 Critical (8-9/10) - Major functionality broken without this class
- **Class Size:** 1950 lines (well within 4000 line mega class limit)

## Test Strategy Discovery Complete ✅

### Existing Test Infrastructure Found
**Strong Foundation:** 4 comprehensive test suites with 79+ test cases:
- `test_unified_lifecycle_manager_real.py` - 79 tests, 100% critical path coverage
- `test_unified_lifecycle_manager_comprehensive.py` - Business value focus, WebSocket events  
- `test_unified_lifecycle_manager_race_conditions.py` - Concurrency testing
- `test_unified_lifecycle_manager.py` - Standard functionality

**Critical Dependencies:** 9 files require import updates across validation scripts and lifecycle components.

### Test Strategy Plan
**60% Existing Test Updates:** Preserve all current test coverage while updating naming conventions  
**20% New SSOT Tests:** Validate business-focused naming compliance and architecture  
**20% Migration Validation:** Ensure zero breaking changes during transition

### Success Metrics Defined
1. **Technical Compliance:** All 79 existing tests pass with new naming
2. **Business Value Preservation:** Chat service startup <30s, deployment downtime <2s  
3. **WebSocket Integrity:** All 5 critical events fire correctly
4. **SSOT Compliance:** Zero duplicate lifecycle implementations
5. **Multi-User Isolation:** Factory pattern maintains user separation for chat functionality

### Critical Requirements
- **No Docker Dependency:** All tests run without Docker
- **Real Services Policy:** Maintain existing NO MOCKS approach  
- **Backward Compatibility:** Both old and new imports work during transition
- **Zero Downtime:** Gradual migration prevents service interruption

### Execution Order Planned
1. **Pre-Migration Baseline** (Establish current test pass rates)
2. **Backward Compatibility Setup** (Create import aliases)  
3. **Class & Factory Renaming** (Core migration implementation)
4. **Test Migration & Validation** (Update all test suites)
5. **Integration Validation** (Cross-service dependency testing)

## Next Steps
- [ ] Execute test plan for 20% new SSOT tests
- [ ] Plan SSOT remediation approach
- [ ] Execute remediation with backward compatibility
- [ ] Run test validation loop until all pass
- [ ] Create PR when tests are green