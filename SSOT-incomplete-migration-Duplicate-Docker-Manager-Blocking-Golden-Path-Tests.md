# SSOT-incomplete-migration-Duplicate Docker Manager Blocking Golden Path Tests

## 🚨 CRITICAL SSOT VIOLATION - Golden Path Blocker

**Impact:** Tests using mock Docker instead of real services, breaking WebSocket events and agent execution

### Problem
Two Docker Manager implementations exist:
- **Real:** `/test_framework/unified_docker_manager.py`
- **Mock:** `/test_framework/docker/unified_docker_manager.py`

### Evidence
Mission critical tests importing from wrong location:
```python
# VIOLATION - gets mock instead of real services
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
```

### Golden Path Impact
- WebSocket events may not be delivered (mock services)
- Agent execution failures (no real LLM/database connections)
- Auth failures (mock auth service)
- **$500K+ ARR functionality at risk**

### Required Actions
1. Remove `/test_framework/docker/unified_docker_manager.py` mock
2. Fix all imports to use real implementation
3. Update mission critical tests to use real services
4. Verify Golden Path tests pass with real Docker services

**Priority:** P0 - Critical Golden Path blocker
**Affects:** WebSocket, Agent, Auth testing infrastructure

## Work Progress Tracker

### Step 0: AUDIT COMPLETE ✅
- [x] Identified critical SSOT violation
- [x] Created issue tracking document
- [x] Initial assessment complete

### Step 1: TEST DISCOVERY AND PLANNING ✅
- [x] Discover existing tests protecting Docker Manager functionality
- [x] Plan test updates for SSOT compliance
- [x] Document test coverage gaps

**FINDINGS:**
- **245/372 tests already use correct SSOT Docker Manager** ✅
- **51 tests use mock Docker Manager** (need fixing) ❌
- Mission critical WebSocket tests already work correctly ✅
- Need focused remediation on 51 problematic test files

**TEST PLAN:**
- 20% new SSOT validation tests (prove violation, validate fix)
- 60% fix existing 51 tests to use real Docker Manager
- 20% coverage gaps for infrastructure stability

### Step 2: CREATE NEW SSOT TESTS
- [ ] Create failing tests reproducing SSOT violation
- [ ] Add tests validating SSOT Docker Manager usage
- [ ] Validate tests against existing functionality

### Step 3: PLAN REMEDIATION
- [ ] Plan removal of duplicate Docker Manager
- [ ] Plan import fixes across codebase
- [ ] Plan migration strategy for affected tests

### Step 4: EXECUTE REMEDIATION
- [ ] Remove duplicate Docker Manager mock
- [ ] Fix all non-SSOT imports
- [ ] Update mission critical tests

### Step 5: TEST FIX LOOP
- [ ] Run and fix all affected tests
- [ ] Verify startup tests pass
- [ ] Confirm Golden Path functionality

### Step 6: PR AND CLOSURE
- [ ] Create PR with fixes
- [ ] Link to this issue for closure
- [ ] Verify all tests passing

## Files Identified for Remediation

### Duplicate Files to Remove
- `/test_framework/docker/unified_docker_manager.py` (mock implementation)

### Files with Import Violations
- Mission critical tests importing wrong Docker Manager
- Various test files throughout services

### Critical Tests to Update
- WebSocket tests needing real services
- Agent execution tests requiring real LLM
- Auth tests needing real auth service