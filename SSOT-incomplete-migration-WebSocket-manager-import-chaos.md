# SSOT WebSocket Manager Import Chaos - Issue #996

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/996
**Priority:** P0 - Golden Path Blocker
**Status:** Discovery Complete - Starting Test Planning

## Problem Summary
Multiple competing WebSocket manager imports causing initialization failures and blocking Golden Path chat functionality ($500K+ ARR impact).

## SSOT Violations Identified
1. **Import Chaos**: Multiple import paths for WebSocket managers
2. **SSOT Bypass**: Legacy direct imports bypassing `unified_manager.py`
3. **Inconsistent Usage**: Mixed usage of SSOT vs legacy patterns

## Discovery Phase Complete ✅
- Audit completed by sub-agent
- Top priority legacy violation identified
- GitHub issue created and tracked

## Test Discovery & Planning Complete ✅

### Existing Test Coverage Found
- **Mission Critical**: 169 tests protecting $500K+ ARR (websocket_agent_events_suite.py)
- **SSOT Framework**: WebSocket test utilities and validation
- **Integration Tests**: 50+ WebSocket files across multiple categories
- **Unit Tests**: 30+ WebSocket-specific test files
- **E2E Tests**: 25+ WebSocket staging tests for Golden Path

### Tests That Will Break (Expected)
- **High Risk**: Import path dependency tests (expected failures)
- **Medium Risk**: Configuration-dependent tests
- **Low Risk**: SSOT-compliant tests (should continue working)

### New SSOT Tests Planned
- **Unit Tests**: 4 new files for SSOT validation
- **Integration Tests**: 2 new files for system integration
- **E2E GCP Staging**: 1 new file for Golden Path validation
- **Validation Tests**: 3 files to confirm migration success

### Test Strategy
- ~20% new SSOT tests (7 files)
- ~60% update existing tests (15-20 files)
- ~20% validation tests (3 files)

## Next Steps
1. **Step 2**: Execute test plan - Create new SSOT tests
2. **Step 3**: Plan SSOT remediation
3. **Step 4**: Execute remediation
4. **Step 5**: Test fix loop until all pass
5. **Step 6**: Create PR and close issue

## Work Log
- **2025-09-14**: Issue discovered and GitHub issue #996 created
- **2025-09-14**: Test discovery and planning completed
- **Next**: Executing test plan with sub-agent