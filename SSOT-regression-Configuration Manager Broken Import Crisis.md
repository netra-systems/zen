# SSOT-regression-Configuration Manager Broken Import Crisis

**GitHub Issue:** [#932](https://github.com/netra-systems/netra-apex/issues/932)  
**Priority:** P0 - Blocks Golden Path  
**Created:** 2025-09-14

## Problem Summary

Mission-critical configuration tests are using dead import paths preventing validation of the configuration system that underpins the Golden Path user flow.

**Broken Import:** `netra_backend.app.core.managers.unified_configuration_manager`

## Business Impact
- Blocks validation of $500K+ ARR Golden Path functionality
- Configuration system validation failures prevent confidence in user login → AI response flow  
- Dead imports indicate incomplete SSOT migration leaving system in unstable state

## Work Progress

### Step 0: Discovery ✅
- [x] SSOT audit completed
- [x] Critical violation identified: Configuration Manager broken imports
- [x] GitHub issue created: #932
- [x] Local tracking file created

### Step 1: Discover and Plan Test ✅
- [x] **1.1 DISCOVER EXISTING:** Find existing tests protecting configuration SSOT ✅
  - **Key Finding:** 28 test files use broken import path BY DESIGN for SSOT validation
  - **Mission Critical:** 169 tests protect core business functionality ($500K+ ARR)
  - **Sophisticated Testing:** Tests designed to fail during SSOT violations, pass after remediation
- [x] **1.2 PLAN TEST STRATEGY:** Plan test updates and new SSOT validation tests ✅
  - **Test Strategy:** 60% existing (478 tests), 20% new SSOT (9 suites), 20% validation (6 suites)  
  - **Current Status:** Tests failing with expected `ModuleNotFoundError` - correct for SSOT validation
  - **Success Criteria:** 60% → 95%+ pass rate expected after SSOT remediation
  - **Execution:** Non-Docker strategy (unit/integration/e2e staging) defined

### Step 2: Execute Test Plan  
- [ ] Create/update SSOT configuration tests

### Step 3: Plan SSOT Remediation
- [ ] Plan configuration import fixes

### Step 4: Execute SSOT Remediation
- [ ] Fix broken configuration imports
- [ ] Update all affected files

### Step 5: Test Fix Loop
- [ ] Validate all tests pass
- [ ] Run startup tests
- [ ] Fix any remaining issues

### Step 6: PR and Closure
- [ ] Create pull request
- [ ] Link issue for auto-closure

## Technical Details

### Files to Investigate
- Configuration test files using broken imports
- SSOT_IMPORT_REGISTRY.md for correct import paths
- Configuration SSOT classes in `/netra_backend/app/core/configuration/`

### Expected SSOT Import Path
Likely should be: `netra_backend.app.core.configuration.base` or similar

## Notes
- Related to Configuration Manager SSOT consolidation (Issue #667)
- Part of ongoing SSOT compliance improvements
- Must maintain backward compatibility during fix