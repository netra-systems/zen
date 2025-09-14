# SSOT-Testing-Direct-Environment-Access-Golden-Path-Blocker

**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/1124
**Status**: DISCOVERY COMPLETE - PLANNING PHASE
**Priority**: P0 - Blocking Golden Path functionality

## Problem Summary
Mission-critical test files are directly accessing `os.environ` instead of using the SSOT `IsolatedEnvironment` pattern, causing environment isolation failures that corrupt Golden Path testing reliability.

## Impact Assessment
- **Golden Path**: User login → AI responses workflow unreliable
- **WebSocket Chat**: 90% of platform value dependent on reliable tests  
- **Multi-User**: Factory-based isolation compromised ($500K+ ARR impact)
- **Test Infrastructure**: Race conditions between concurrent tests

## Files Identified for Remediation
### Primary Target
- `tests/mission_critical/test_websocket_bridge_critical_flows.py` (lines 92-94)
  ```python
  # VIOLATION: Direct os.environ access
  os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
  os.environ['SKIP_REAL_SERVICES'] = 'false'  
  os.environ['TEST_COLLECTION_MODE'] = '1'
  ```

### Additional Files (14+ others)
- TBD: Full scan needed to identify all violating files

## SSOT Solution Pattern
Replace direct `os.environ` access with `IsolatedEnvironment`:
```python
from shared.isolated_environment import get_env
env = get_env()
env.set('WEBSOCKET_TEST_ISOLATED', 'true', 'test_context')
env.set('SKIP_REAL_SERVICES', 'false', 'test_context')
env.set('TEST_COLLECTION_MODE', '1', 'test_context')
```

## Progress Tracking

### Step 0: SSOT Audit ✅ COMPLETE
- [x] Discovered critical SSOT violation
- [x] Created GitHub issue #1124
- [x] Created progress tracking file

### Step 1: DISCOVER AND PLAN TEST ✅ COMPLETE
- [x] 1.1 DISCOVER EXISTING: Found 3 major test suites protecting environment isolation + 15 mission-critical files
- [x] 1.2 PLAN ONLY: Planned 60% existing test validation, 20% new tests, 20% SSOT fixes

### Step 2: EXECUTE TEST PLAN ✅ COMPLETE
- [x] Created 3 new SSOT test files (35 total tests)
- [x] Detected 1,189 violations (538 critical) across 176 files
- [x] Established baseline for regression prevention

### Step 3: PLAN REMEDIATION 📋 PENDING
- [ ] Plan SSOT remediation strategy
- [ ] Identify all files requiring updates

### Step 4: EXECUTE REMEDIATION 📋 PENDING
- [ ] Replace os.environ with IsolatedEnvironment SSOT pattern
- [ ] Update imports and test contexts

### Step 5: TEST FIX LOOP 📋 PENDING
- [ ] Run and fix all tests in scope
- [ ] Ensure no breaking changes introduced
- [ ] Validate startup tests pass

### Step 6: PR AND CLOSURE 📋 PENDING
- [ ] Create Pull Request
- [ ] Link to close issue #1124

## Notes
- Focus on atomic changes that maintain system stability
- Only run non-Docker tests (unit, integration, e2e staging GCP)
- Ensure Golden Path remains operational throughout changes