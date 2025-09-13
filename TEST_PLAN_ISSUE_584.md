# Test Plan for Issue #584: Thread ID Run ID Generation Inconsistency

## Overview
Create comprehensive tests to reproduce and validate fix for ID generation inconsistencies in demo_websocket.py and other components.

## Test Strategy

### 1. Unit Tests (Reproduce the Problem)
- **test_demo_websocket_id_inconsistency.py** - Enhance existing test to be more comprehensive
- **test_unified_id_manager_compliance.py** - Test SSOT compliance patterns
- **test_id_correlation_failures.py** - Test WebSocket cleanup correlation issues

### 2. Integration Tests (System Impact)
- **test_websocket_id_cleanup_integration.py** - Test WebSocket resource cleanup with mixed ID patterns
- **test_id_extraction_consistency.py** - Test thread_id extraction from run_id across different patterns

### 3. Non-Docker Tests Only
All tests will be designed to run without Docker dependency since we're focusing on non-Docker execution.

## Test Categories

### Category 1: SSOT Violation Detection
- Detect when code bypasses UnifiedIDManager
- Validate consistent ID patterns across system
- Test ID format validation

### Category 2: Correlation Logic Testing
- Test thread_id extraction from run_id
- Test WebSocket cleanup correlation
- Test debugging and tracing correlation

### Category 3: Remediation Validation
- Test that UnifiedIDManager methods work correctly
- Validate consistent ID generation after fix
- Test backward compatibility during migration

## Test Files to Create/Update

### 1. Enhanced Unit Test
File: `tests/issue_584/test_demo_websocket_id_inconsistency.py` (enhance existing)
- Test current problematic patterns
- Test SSOT patterns
- Test correlation logic failures

### 2. New Integration Test
File: `tests/integration/test_id_generation_ssot_compliance.py`
- Test system-wide ID generation compliance
- Test mixed ID pattern detection
- Test cleanup correlation with mixed patterns

### 3. New Validation Test
File: `tests/unit/test_unified_id_manager_demo_compliance.py`
- Test UnifiedIDManager methods for demo use cases
- Test thread_id/run_id correlation
- Test ID format consistency

## Expected Test Outcomes

### Before Fix (Tests Should FAIL)
- Mixed ID patterns detected in system
- Correlation logic fails with prefixed IDs
- SSOT compliance violations found

### After Fix (Tests Should PASS)
- All IDs generated through UnifiedIDManager
- Consistent ID patterns throughout system
- Correlation logic works correctly
- No SSOT violations detected

## Implementation Plan

1. **Enhance existing test** with more comprehensive scenarios
2. **Create integration test** for system-wide impact
3. **Create validation test** for UnifiedIDManager compliance
4. **Run tests** to confirm they fail (reproduce issue)
5. **Fix code** to use UnifiedIDManager SSOT
6. **Re-run tests** to confirm they pass