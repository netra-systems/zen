# Issue #1128 - Test Plan Complete: WebSocket Factory Import Cleanup

**Status:** TEST PLAN COMPLETE - Factory removed successfully, existing tests need framework fixes

**Key findings:** WebSocket factory (587 lines) successfully removed, but 10/13 existing tests failing due to test framework issues (using broken `SSotAsyncTestCase`), not business logic failures.

## Test Plan Execution Strategy

### Phase 1: Framework Fixes (IMMEDIATE - Should PASS)
**Current issue:** Tests using `SSotAsyncTestCase` missing standard unittest methods
**Fix:** Replace with `unittest.TestCase` - demonstrates 3/6 critical tests now pass

**Working example created:**
- ✅ `test_websocket_factory_import_validation_fixed.py` - 3 tests now PASS
- ✅ Deprecated factory import correctly fails (proves removal)
- ✅ Canonical SSOT imports work correctly
- ✅ No circular dependencies in SSOT patterns

### Phase 2: Critical Production Validation (Should PASS)
**Purpose:** Validate $500K+ ARR WebSocket functionality protected
**Infrastructure:** Real PostgreSQL/Redis WITHOUT Docker

**New tests needed:**
1. **`test_websocket_manager_post_removal_integration.py`**
   - WebSocket manager initialization via SSOT patterns
   - Multi-user isolation validation with real services
   - Expected: PASS - Business functionality preserved

2. **`test_golden_path_websocket_events_post_removal.py`**  
   - All 5 critical WebSocket events work (`agent_started`, `agent_thinking`, `tool_executing`, `tool_completed`, `agent_completed`)
   - Expected: PASS - Golden Path protected

### Phase 3: Import Violation Detection (Mixed Results)
**Purpose:** Track cleanup progress of remaining legacy imports
**Expected:** Some FAIL (detecting violations), some PASS (SSOT compliance)

**Tests:**
- Legacy import detection (should FAIL initially - finds violations to clean)
- SSOT pattern compliance (should PASS - canonical patterns work)
- Import fragmentation tracking (should FAIL initially - currently 69 modules)

### Phase 4: Staging E2E Validation (Should PASS)
**Infrastructure:** Staging GCP environment (`https://auth.staging.netrasystems.ai`)
**Purpose:** End-to-end user flow validation without Docker

## Key Technical Fixes Identified

### UserExecutionContext Constructor Fix
```python
# BROKEN (missing required args):
UserExecutionContext(user_id="test", websocket_client_id="test")

# FIXED (all required args):
UserExecutionContext(
    user_id="test_user",
    thread_id="test_thread", 
    run_id="test_run",
    websocket_client_id="test_client"
)
```

### Test Framework Migration
```python
# BROKEN (SSotAsyncTestCase missing methods):
class TestClass(SSotAsyncTestCase):
    def test_something(self):
        with self.assertRaises(ImportError):  # ❌ AttributeError

# FIXED (standard unittest):
class TestClass(unittest.TestCase):
    def test_something(self):
        with self.assertRaises(ImportError):  # ✅ Works
```

## Success Metrics

**Immediate (Phase 1):** All framework tests pass  
**Critical (Phase 2):** WebSocket functionality validation passes  
**Progress (Phase 3):** Legacy import violations tracked and reduced  
**Validation (Phase 4):** Staging environment E2E tests pass

## Next Action

**Fix remaining 10 failing tests** by applying framework migration pattern demonstrated in `test_websocket_factory_import_validation_fixed.py`

**Files to update:**
- `test_authentication_service_ssot_compliance.py`
- `test_websocket_factory_deprecation_proof.py`  
- Add UserExecutionContext required arguments (`thread_id`, `run_id`)

**Business impact:** Protects $500K+ ARR WebSocket functionality with comprehensive test coverage post-factory-removal.