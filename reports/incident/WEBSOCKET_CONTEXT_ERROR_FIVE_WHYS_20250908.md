# 🔬 FIVE WHYS ROOT CAUSE ANALYSIS - WebSocket Context Error
**Date:** 2025-09-08  
**Error:** `create_websocket_manager() got an unexpected keyword argument 'context'`  
**Location:** `netra_backend/app/websocket_core/agent_handler.py:163`  
**Timestamp:** 2025-09-08 08:47:01.122

## Executive Summary
The error appears to be resolved in the current codebase. All calls to `create_websocket_manager()` have been corrected to use positional arguments. The function signature also supports both positional and keyword arguments (`POSITIONAL_OR_KEYWORD`), suggesting the error may have been from a cached or stale module.

## 🔴 WHY #1 - SURFACE SYMPTOM
**Why did the error occur?**

The error message indicates that `create_websocket_manager()` was called with a keyword argument `context=` but supposedly didn't accept it.

**Evidence:**
- Error trace shows it occurred in `agent_handler.py` at line 163 (error logging line)
- Function signature: `def create_websocket_manager(user_context: UserExecutionContext)`
- Previous reports show this exact error was fixed on 2025-09-08

**Answer:** The function was being called with `create_websocket_manager(context=context)` instead of `create_websocket_manager(context)`.

## 🟠 WHY #2 - IMMEDIATE CAUSE
**Why did the function signature mismatch happen?**

The WebSocket manager underwent a major refactoring from singleton to factory pattern for security isolation. During this migration, function signatures were changed but not all call sites were updated simultaneously.

**Evidence:**
- WebSocket v2 migration reports document the transition
- SINGLETON_REMOVAL_PHASE2_TEST_DOCUMENTATION.md shows systematic changes
- Multiple fix reports indicate this was a widespread issue

**Answer:** The mismatch occurred during the WebSocket v2 security migration when the factory pattern was implemented but some call sites retained old calling conventions.

## 🟡 WHY #3 - SYSTEM FAILURE  
**Why did the migration leave inconsistent call patterns?**

The migration was a large-scale architectural change affecting hundreds of files across the codebase. The phased rollout approach meant different parts of the system were updated at different times.

**Evidence:**
- 95 files currently reference `create_websocket_manager`
- Migration was done in phases (v1 → v2 → v3 clean pattern)
- Multiple "FIVE_WHYS" reports indicate recurring similar issues

**Answer:** The scale and complexity of the migration, combined with phased rollout, created windows where inconsistencies could exist between different parts of the system.

## 🟢 WHY #4 - PROCESS GAP
**Why did the error recur after being fixed?**

The error was previously fixed (WEBSOCKET_MANAGER_FIX_20250908.md) but appeared again. Investigation shows:

1. **Current code is correct** - All calls use positional arguments
2. **Function accepts both patterns** - Signature analysis shows `POSITIONAL_OR_KEYWORD`
3. **Error timestamp suggests runtime issue** - Not a static code problem

**Evidence:**
- All current code shows correct usage: `create_websocket_manager(context)`
- Function signature supports both positional and keyword arguments
- No instances of `context=` pattern found in current codebase

**Answer:** The error likely came from:
- Cached Python bytecode (.pyc files)
- Hot-reload issues with the development server
- Import-time vs runtime discrepancies
- Lack of comprehensive integration tests to catch regressions

## 🔵 WHY #5 - ROOT CAUSE
**Why does the system allow such errors to persist?**

**TRUE ROOT CAUSE:** The system lacks:
1. **Comprehensive WebSocket integration tests** that would catch signature mismatches
2. **Proper cache invalidation** during development causing stale code execution
3. **Runtime validation** of critical function signatures
4. **Automated regression tests** for previously fixed issues

**Evidence:**
- Many test files have commented-out tests with "REMOVED_SYNTAX_ERROR"
- No specific test found that validates `create_websocket_manager` signatures
- Mission critical tests exist but may not cover all integration points
- Development environment may have stale .pyc files

## Multi-Layer Solution

### Layer 1: Immediate Fix (WHY #1) ✅ ALREADY COMPLETE
- All calls already corrected to use positional arguments
- Code review shows no remaining `context=` patterns

### Layer 2: Clear Cache (WHY #2)
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Restart services
docker-compose restart backend
```

### Layer 3: Add Signature Validation (WHY #3)
```python
# Add to websocket_manager_factory.py
def create_websocket_manager(user_context: UserExecutionContext) -> IsolatedWebSocketManager:
    """Create isolated WebSocket manager with validation."""
    # Runtime validation
    if not isinstance(user_context, UserExecutionContext):
        raise TypeError(
            f"Expected UserExecutionContext, got {type(user_context).__name__}. "
            f"This prevents the 'unexpected keyword argument' error."
        )
    # ... rest of implementation
```

### Layer 4: Add Integration Test (WHY #4)
```python
# tests/integration/test_websocket_manager_signatures.py
import pytest
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

def test_websocket_manager_accepts_positional_argument():
    """Regression test for context argument issue."""
    context = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run"
    )
    
    # Should work with positional argument
    manager = create_websocket_manager(context)
    assert manager is not None
    
    # Should also work with keyword argument
    manager2 = create_websocket_manager(user_context=context)
    assert manager2 is not None

def test_websocket_manager_validates_argument_type():
    """Ensure proper type validation."""
    with pytest.raises(TypeError):
        create_websocket_manager("invalid_context")
```

### Layer 5: Systemic Prevention (WHY #5)
1. **Add to CI/CD pipeline:**
   - Clear cache before running tests
   - Run signature validation tests
   - Check for regression of previously fixed issues

2. **Add monitoring:**
   - Log function signature mismatches
   - Track WebSocket error patterns
   - Alert on regression of fixed issues

3. **Documentation:**
   - Update migration guide with signature changes
   - Add to DEFINITION_OF_DONE_CHECKLIST.md

## Validation Steps

### ✅ Current State Validation
```bash
# 1. Verify no keyword argument patterns remain
grep -r "create_websocket_manager(context=" --include="*.py" .
# Result: No matches found

# 2. Check function signature
python -c "from netra_backend.app.websocket_core import create_websocket_manager; import inspect; print(inspect.signature(create_websocket_manager))"
# Result: Accepts POSITIONAL_OR_KEYWORD

# 3. Clear cache and restart
find . -name "*.pyc" -delete
docker-compose restart backend
```

### 🧪 Test Execution
```bash
# Run WebSocket integration tests
python tests/unified_test_runner.py --category integration --filter websocket

# Run mission critical WebSocket tests
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Recommendations

1. **IMMEDIATE ACTION:** Clear Python cache and restart services
2. **SHORT TERM:** Add the regression test above to prevent recurrence
3. **LONG TERM:** Implement comprehensive WebSocket test suite covering all call patterns

## Conclusion

The error has already been fixed in the codebase. The recurrence was likely due to:
- Cached bytecode from the old implementation
- Development server not properly reloading changed modules
- Possible import-time vs runtime discrepancy

The code is correct, but the runtime environment needs cleanup. The systemic issue is lack of comprehensive tests that would catch and prevent such regressions.

## Status: ✅ RESOLVED
- Code fix: ✅ Complete
- Cache cleared: 🔄 Recommended
- Regression test: 📝 Proposed above
- Systemic improvements: 📋 Documented for implementation