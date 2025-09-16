# SSOT Test Framework Event Loop Remediation Plan

## Executive Summary

**CRITICAL INFRASTRUCTURE FIX**: Replace incompatible event loop management in SSOT test framework to restore all integration and golden path tests.

**ROOT CAUSE**: Lines 388 and 1262 in `test_framework/ssot/base_test_case.py` use `loop.run_until_complete(self.asyncSetUp())` which conflicts with pytest-asyncio's active event loop.

**BUSINESS IMPACT**: Fixing this restores validation for $500K+ ARR golden path and enables deployment confidence.

## Current State Analysis

### Problematic Code Locations

**File**: `test_framework/ssot/base_test_case.py`

**Line 388** (in SSotBaseTestCase.setUp):
```python
try:
    loop.run_until_complete(self.asyncSetUp())
except Exception as e:
    logger.error(f"asyncSetUp failed in {self.__class__.__name__}: {e}")
    raise
```

**Line 1262** (in SSotAsyncTestCase.setUp - DUPLICATE):
```python
try:
    loop.run_until_complete(self.asyncSetUp())
except Exception as e:
    logger.error(f"asyncSetUp failed in {self.__class__.__name__}: {e}")
    raise
```

**Line 1067** (in SSotAsyncTestCase.asyncSetUp):
```python
if hasattr(super(), 'setUp'):
    super().setUp()  # Calls sync setUp from async context
```

### Error Pattern
```
RuntimeError: This event loop is already running
```

This occurs because pytest-asyncio already manages an event loop, but the SSOT framework attempts to run `asyncSetUp()` using `run_until_complete()` in a synchronous context.

## Technical Solution

### Phase 1: Immediate Fix (Event Loop Compatibility)

**Strategy**: Replace `run_until_complete()` with proper async/await patterns that work with existing event loops.

#### Fix for Lines 388 and 1262:

**REPLACE**:
```python
loop.run_until_complete(self.asyncSetUp())
```

**WITH**:
```python
# Check if we have an async setup method
if hasattr(self, 'asyncSetUp') and asyncio.iscoroutinefunction(self.asyncSetUp):
    try:
        # Check if event loop is already running (pytest-asyncio case)
        loop = asyncio.get_running_loop()
        # If we reach here, loop is running - schedule asyncSetUp as task
        import concurrent.futures
        import threading

        # Create a future to bridge sync/async
        future = concurrent.futures.Future()

        def run_async_setup():
            try:
                result = asyncio.run_coroutine_threadsafe(self.asyncSetUp(), loop)
                future.set_result(result.result())
            except Exception as e:
                future.set_exception(e)

        # Run in separate thread to avoid event loop conflict
        thread = threading.Thread(target=run_async_setup)
        thread.start()
        thread.join()

        # Get result or re-raise exception
        future.result()

    except RuntimeError:
        # No event loop running - safe to create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.asyncSetUp())
        finally:
            loop.close()
```

#### Fix for Line 1067:

**REPLACE**:
```python
if hasattr(super(), 'setUp'):
    super().setUp()
```

**WITH**:
```python
if hasattr(super(), 'setUp'):
    # Use sync setup - no async needed here
    # Remove this call to prevent recursive loop issues
    pass
```

### Phase 2: Code Deduplication

The duplicate setUp methods at lines ~380-400 and ~1250-1270 should be consolidated into a single implementation.

### Phase 3: Enhanced Error Handling

Add proper logging and fallback mechanisms for edge cases.

## Implementation Steps

### Step 1: Create Backup
```bash
cp test_framework/ssot/base_test_case.py test_framework/ssot/base_test_case.py.backup
```

### Step 2: Apply Fixes
1. Replace event loop management at lines 388 and 1262
2. Fix recursive setup call at line 1067
3. Consolidate duplicate setUp implementations
4. Add enhanced error handling and logging

### Step 3: Validation
1. Run unit tests on the framework itself
2. Run integration tests to verify fix
3. Run golden path tests specifically
4. Full test suite validation

## Risk Assessment

### LOW RISK
- **Backwards Compatibility**: Maintained for both unittest and pytest patterns
- **SSOT Architecture**: No changes to SSOT principles
- **Existing Tests**: No changes required to test implementations

### MEDIUM RISK
- **Event Loop Edge Cases**: Complex async/sync bridging may have edge cases
- **Threading Overhead**: Slight performance impact from thread-based solution

### MITIGATION STRATEGIES
1. **Comprehensive Testing**: Test all async/sync combinations
2. **Gradual Rollout**: Test individual components before full suite
3. **Monitoring**: Add detailed logging for event loop operations
4. **Rollback Plan**: Keep backup file for immediate revert if needed

## Validation Plan

### Pre-Fix Validation
```bash
# Confirm current failure state
python tests/unified_test_runner.py --category integration --fast-fail
python -m pytest tests/e2e/golden_path/ -v
```

### Post-Fix Validation

#### Phase 1: Framework Tests
```bash
# Test the SSOT framework itself
python -m pytest test_framework/tests/ -v
```

#### Phase 2: Integration Tests
```bash
# Run integration tests without fast-fail to see all results
python tests/unified_test_runner.py --category integration
```

#### Phase 3: Golden Path Tests
```bash
# Run specific golden path validation
python -m pytest tests/e2e/golden_path/ -v
python tests/mission_critical/test_websocket_agent_events_suite.py
```

#### Phase 4: Full Test Suite
```bash
# Complete test suite validation
python tests/unified_test_runner.py --real-services
```

### Success Metrics

**MUST ACHIEVE**:
- [ ] 0 event loop runtime errors in integration tests
- [ ] Golden path tests execute successfully
- [ ] Mission critical WebSocket tests pass
- [ ] Integration test category shows > 90% pass rate
- [ ] No regression in existing unit tests

**BUSINESS VALIDATION**:
- [ ] Can validate $500K+ ARR user workflows
- [ ] Deployment confidence restored
- [ ] Staging environment validation works

## Timeline

### IMMEDIATE (Next 2 hours)
1. **Code Implementation**: Apply the event loop compatibility fixes
2. **Basic Validation**: Test framework functionality and basic integration tests
3. **Golden Path Test**: Verify critical user workflow validation works

### SHORT TERM (Next 4 hours)
1. **Comprehensive Testing**: Run full test suite validation
2. **Edge Case Testing**: Test various async/sync combinations
3. **Performance Validation**: Ensure no significant performance regression

### FOLLOW-UP (Next 24 hours)
1. **Production Validation**: Deploy to staging and validate end-to-end
2. **Documentation Updates**: Update SSOT framework documentation
3. **Monitoring Setup**: Add alerts for future event loop issues

## Rollback Strategy

### If Fix Fails
1. **Immediate Revert**:
   ```bash
   cp test_framework/ssot/base_test_case.py.backup test_framework/ssot/base_test_case.py
   ```

2. **Alternative Approach**:
   - Temporarily disable pytest-asyncio
   - Use simpler event loop management
   - Create emergency bypass for critical tests

3. **Emergency Validation**:
   - Manual golden path validation scripts
   - Direct API testing without test framework
   - Staging environment manual verification

## Long-term Improvements

### Architecture Enhancements
1. **Event Loop Management**: Centralized async/sync compatibility layer
2. **Test Framework Hardening**: Comprehensive async/await pattern validation
3. **CI/CD Detection**: Add pipeline checks for event loop conflicts

### Process Improvements
1. **Infrastructure Review**: Require architecture review for critical infrastructure changes
2. **Test Coverage**: Add tests for the test framework itself
3. **Documentation**: Create async/sync compatibility guidelines

## Dependencies and Impact

### UNBLOCKS
- Integration test execution
- Golden path user workflow validation
- E2E business functionality testing
- Staging deployment validation
- Production deployment confidence

### ENABLES
- Quality assurance processes
- Development velocity
- Customer value delivery validation
- System stability verification

---

**CRITICAL SUCCESS FACTOR**: This fix must restore 100% integration test functionality to enable business-critical golden path validation and deployment confidence.

**NEXT ACTION**: Implement the event loop compatibility fixes immediately to restore test infrastructure functionality.