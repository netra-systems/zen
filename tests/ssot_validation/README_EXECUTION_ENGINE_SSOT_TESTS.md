# Execution Engine SSOT Validation Tests

## Overview

These tests are designed to validate the SSOT (Single Source of Truth) consolidation of WorkflowOrchestrator execution engines for GitHub Issue #208. They follow the 20% strategy of creating new tests that are **DESIGNED TO FAIL** before consolidation and **PASS** afterward.

## Test Files Created

### 1. Unit-Level SSOT Violation Detection
**File:** `/tests/unit/ssot_validation/test_consolidated_execution_engine_ssot_enforcement.py`

**Purpose:** Detect current SSOT violations that should FAIL before consolidation and PASS after

**Key Tests:**
- `test_multiple_execution_engine_implementations_detected()` - Detects multiple execution engine implementations violating SSOT
- `test_deprecated_import_patterns_still_functional()` - Detects deprecated import patterns that should be blocked  
- `test_factory_pattern_enforcement_incomplete()` - Detects non-exclusive factory pattern enforcement

**Expected Behavior:**
- **BEFORE consolidation:** Tests FAIL, demonstrating SSOT violations exist
- **AFTER consolidation:** Tests PASS, showing single canonical implementation

### 2. Integration-Level Factory Pattern Validation  
**File:** `/tests/integration/ssot_validation/test_execution_engine_factory_consolidation.py`

**Purpose:** Validate factory pattern works correctly with real services post-consolidation

**Key Tests:**
- `test_concurrent_user_factory_isolation_maintained()` - Validates user isolation with real multi-user scenarios
- `test_websocket_event_delivery_factory_integration()` - Tests WebSocket events delivered correctly post-consolidation
- `test_factory_creation_performance_baseline()` - Measures performance to detect regressions

**Expected Behavior:**
- **BEFORE consolidation:** Tests may FAIL due to isolation issues or WebSocket integration problems
- **AFTER consolidation:** Tests PASS, demonstrating proper factory patterns with real services

## Test Strategy & Design

### Business Impact
- **$500K+ ARR at risk** from execution engine inconsistencies  
- **60% reduction** in duplicated execution logic needed
- **User isolation** critical for multi-user agent execution

### Test Design Principles
- **Real Services:** Use real services where possible, avoid mocks
- **Thread-based Context:** Use UserExecutionContext with thread_id/run_id pattern (not session_id/connection_id) 
- **SSOT Compliance:** Follow existing patterns from test_framework.ssot modules
- **No Docker Dependencies:** Tests run without requiring Docker orchestration
- **Comprehensive Logging:** Include detailed logging for debugging SSOT issues

### Key Validation Points

#### SSOT Violations Detected:
1. **Multiple Implementations:** SupervisorExecutionEngine vs ConsolidatedExecutionEngine vs CoreExecutionEngine
2. **Deprecated Imports:** Old import paths still functional instead of redirecting to SSOT
3. **Factory Pattern Issues:** Direct instantiation possible instead of factory-only creation
4. **User Isolation Failures:** Shared state between concurrent user contexts
5. **WebSocket Integration:** Events not properly routed through factory-created engines

#### Expected Post-Consolidation State:
1. **Single Implementation:** One canonical ExecutionEngine implementation
2. **Blocked Imports:** Deprecated imports fail or redirect with deprecation warnings
3. **Factory Enforcement:** Only factory pattern allows engine creation
4. **Complete Isolation:** Zero shared state between user contexts
5. **Reliable WebSocket:** All events properly delivered to correct users

## Execution Instructions

### Running the Tests

#### Unit Tests (SSOT Violation Detection)
```bash
# Run unit SSOT validation tests
python tests/unified_test_runner.py --category unit --filter "ssot_validation"

# Run specific unit test
pytest tests/unit/ssot_validation/test_consolidated_execution_engine_ssot_enforcement.py -v

# Run with detailed output
pytest tests/unit/ssot_validation/test_consolidated_execution_engine_ssot_enforcement.py -v -s --tb=long
```

#### Integration Tests (Factory Pattern Validation)
```bash
# Run integration SSOT validation tests  
python tests/unified_test_runner.py --category integration --filter "ssot_validation"

# Run specific integration test
pytest tests/integration/ssot_validation/test_execution_engine_factory_consolidation.py -v

# Run with real services (recommended)
python tests/unified_test_runner.py --category integration --filter "ssot_validation" --real-services
```

#### Complete SSOT Validation Suite
```bash
# Run all SSOT validation tests together
pytest tests/unit/ssot_validation/test_consolidated_execution_engine_ssot_enforcement.py tests/integration/ssot_validation/test_execution_engine_factory_consolidation.py -v

# Run with comprehensive reporting
python tests/unified_test_runner.py --category unit integration --filter "ssot_validation" --real-services --detailed-report
```

### Expected Test Results

#### Before SSOT Consolidation
```
FAILURES:
- test_multiple_execution_engine_implementations_detected FAILED - Multiple implementations detected
- test_deprecated_import_patterns_still_functional FAILED - Deprecated imports still work  
- test_factory_pattern_enforcement_incomplete FAILED - Factory patterns not enforced
- test_concurrent_user_factory_isolation_maintained FAILED - User isolation violations
- test_websocket_event_delivery_factory_integration FAILED - WebSocket integration issues
```

#### After SSOT Consolidation
```
PASSED:
- test_multiple_execution_engine_implementations_detected PASSED - Single implementation found
- test_deprecated_import_patterns_still_functional PASSED - Deprecated imports blocked
- test_factory_pattern_enforcement_incomplete PASSED - Factory patterns enforced
- test_concurrent_user_factory_isolation_maintained PASSED - User isolation maintained
- test_websocket_event_delivery_factory_integration PASSED - WebSocket integration working
```

### Debugging Failed Tests

#### Common Debug Commands
```bash
# Check current execution engine implementations
python -c "
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine as SE
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine as CE  
print('SupervisorExecutionEngine:', SE.__module__ if SE else 'Not found')
print('ConsolidatedExecutionEngine:', CE.__module__ if CE else 'Not found')
"

# Test factory imports
python -c "
try:
    from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory as SF
    print('SupervisorFactory available')
except ImportError as e:
    print('SupervisorFactory import failed:', e)
    
try:
    from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory as CF
    print('ConsolidatedFactory available') 
except ImportError as e:
    print('ConsolidatedFactory import failed:', e)
"

# Check user context patterns
python -c "
from netra_backend.app.services.user_execution_context import UserExecutionContext
import uuid
ctx = UserExecutionContext(user_id=str(uuid.uuid4()), thread_id=str(uuid.uuid4()), run_id=str(uuid.uuid4()))
print('UserExecutionContext created successfully:', ctx.user_id[:8])
"
```

#### Log Analysis
Tests include comprehensive logging with these patterns:
- `SSOT Violation #N:` - Specific SSOT violations detected
- `Factory Enforcement Violation #N:` - Factory pattern issues
- `User Isolation Violation #N:` - User isolation problems  
- `WebSocket Integration Violation #N:` - WebSocket delivery issues

### Integration with Existing Test Framework

These tests integrate with the existing SSOT test infrastructure:
- **Base Class:** `SSotAsyncTestCase` from `test_framework.ssot.base_test_case`
- **Environment:** Uses `IsolatedEnvironment` for environment access
- **Metrics:** Records detailed metrics for debugging and analysis
- **User Context:** Uses `UserExecutionContext` following established patterns

### Notes

1. **Test Timing:** These tests should be run before and after SSOT consolidation to validate the fix
2. **Real Services:** Integration tests prefer real services over mocks for accurate validation
3. **Performance:** Performance baselines help detect regressions during consolidation
4. **Documentation:** All violations are logged with clear descriptions for debugging

The tests serve as both validation tools and documentation of the current SSOT violation state, making them valuable for tracking consolidation progress.