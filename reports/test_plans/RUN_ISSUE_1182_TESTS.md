# Issue #1182 WebSocket Manager SSOT Migration - Test Execution Guide

## Executive Summary

This document provides the comprehensive test plan and execution guide for **Issue #1182: WebSocket Manager SSOT Migration**. These tests validate the elimination of 3 competing WebSocket manager implementations and ensure proper SSOT consolidation while protecting the $500K+ ARR Golden Path functionality.

## Critical Context

### Problem Statement
- **Issue #1182**: 3 competing WebSocket manager implementations causing SSOT violations
- **Issue #1209**: DemoWebSocketBridge interface failure (regression from SSOT violations)
- **Business Impact**: $500K+ ARR Golden Path functionality at risk

### Current State Analysis
Based on analysis of the codebase, the following competing implementations exist:
1. `/netra_backend/app/websocket_core/manager.py` - Compatibility layer
2. `/netra_backend/app/websocket_core/websocket_manager.py` - Primary SSOT interface
3. `/netra_backend/app/websocket_core/unified_manager.py` - Implementation layer

## Test Strategy Overview

### Phase 1: Unit Tests (Non-Docker) - **SHOULD FAIL INITIALLY**
These tests detect current SSOT violations and race conditions.

### Phase 2: Integration Tests (Non-Docker) - **SHOULD FAIL INITIALLY** 
These tests validate cross-service integration and interface compatibility.

### Phase 3: E2E Staging Tests (GCP Remote) - **SHOULD PASS**
These tests validate Golden Path functionality remains protected.

### Phase 4: Mission Critical Tests - **SHOULD FAIL INITIALLY**
These tests detect violations and protect business value.

## Test Execution Commands

### 1. Run Unit Tests for SSOT Violation Detection

```bash
# Test 1: Manager consolidation validation (SHOULD FAIL - 3 implementations detected)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_manager_consolidation_validation.py::TestWebSocketManagerConsolidationValidation::test_single_websocket_manager_implementation_exists -v

# Test 2: Import path consolidation (SHOULD FAIL - multiple paths found)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_manager_consolidation_validation.py::TestWebSocketManagerConsolidationValidation::test_import_path_consolidation_complete -v

# Test 3: Interface consistency (SHOULD FAIL - inconsistencies detected)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_manager_consolidation_validation.py::TestWebSocketManagerConsolidationValidation::test_websocket_manager_interface_consistency -v

# Test 4: DemoWebSocketBridge compatibility (SHOULD FAIL - Issue #1209)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_manager_consolidation_validation.py::TestWebSocketManagerConsolidationValidation::test_demo_websocket_bridge_compatibility_validation -v

# Run all unit tests for Issue #1182
python -m pytest tests/unit/websocket_ssot_migration/ -v
```

### 2. Run Race Condition Detection Tests

```bash
# Test 1: Concurrent initialization safety (SHOULD FAIL - race conditions detected)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_race_condition_detection.py::TestWebSocketManagerRaceConditionDetection::test_concurrent_manager_initialization_safety -v

# Test 2: User isolation factory patterns (SHOULD FAIL - singleton violations)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_race_condition_detection.py::TestWebSocketManagerRaceConditionDetection::test_user_isolation_factory_pattern_consistency -v

# Test 3: Event delivery race conditions (SHOULD FAIL - delivery race conditions)
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_race_condition_detection.py::TestWebSocketManagerRaceConditionDetection::test_websocket_event_delivery_race_conditions -v

# Run all race condition tests
python -m pytest tests/unit/websocket_ssot_migration/test_issue_1182_race_condition_detection.py -v
```

### 3. Run Integration Tests for Cross-Service Validation

```bash
# Test 1: AgentWebSocketBridge integration (SHOULD FAIL - integration inconsistencies)
python -m pytest tests/integration/websocket_ssot_migration/test_issue_1182_cross_service_integration.py::TestWebSocketCrossServiceIntegration::test_agent_websocket_bridge_integration_consistency -v

# Test 2: Demo service compatibility (SHOULD FAIL - Issue #1209 regression)
python -m pytest tests/integration/websocket_ssot_migration/test_issue_1182_cross_service_integration.py::TestWebSocketCrossServiceIntegration::test_demo_websocket_service_compatibility -v

# Test 3: Interface contracts (SHOULD FAIL - contract violations)
python -m pytest tests/integration/websocket_ssot_migration/test_issue_1182_cross_service_integration.py::TestWebSocketCrossServiceIntegration::test_cross_service_interface_contracts -v

# Run all integration tests
python -m pytest tests/integration/websocket_ssot_migration/ -v
```

### 4. Run E2E Staging Tests for Golden Path Protection

```bash
# Test 1: Complete user journey (SHOULD PASS - Golden Path protected)
python -m pytest tests/e2e/staging/test_issue_1182_golden_path_websocket_validation.py::TestGoldenPathWebSocketValidation::test_complete_user_journey_with_websocket_events -v

# Test 2: Five critical events (SHOULD PASS - business value protected)
python -m pytest tests/e2e/staging/test_issue_1182_golden_path_websocket_validation.py::TestGoldenPathWebSocketValidation::test_websocket_five_critical_events_delivered -v

# Test 3: Production readiness (SHOULD PASS - scalability validated)
python -m pytest tests/e2e/staging/test_issue_1182_golden_path_websocket_validation.py::TestGoldenPathWebSocketValidation::test_production_readiness_concurrent_users -v

# Run all E2E staging tests
python -m pytest tests/e2e/staging/test_issue_1182_golden_path_websocket_validation.py -v
```

### 5. Run Mission Critical Tests

```bash
# Mission critical Issue #1182 validation (SHOULD FAIL - violations detected)
python -m pytest tests/mission_critical/test_websocket_ssot_multiple_managers_violation_detection.py::TestWebSocketSSotMultipleManagersViolationDetection::test_issue_1182_websocket_manager_ssot_consolidation -v

# All mission critical WebSocket tests
python -m pytest tests/mission_critical/test_websocket_ssot_multiple_managers_violation_detection.py -v
```

### 6. Comprehensive Test Suite Execution

```bash
# Run all Issue #1182 tests in order
python -m pytest \
  tests/unit/websocket_ssot_migration/ \
  tests/integration/websocket_ssot_migration/ \
  tests/e2e/staging/test_issue_1182_golden_path_websocket_validation.py \
  tests/mission_critical/test_websocket_ssot_multiple_managers_violation_detection.py::test_issue_1182_websocket_manager_ssot_consolidation \
  -v --tb=short

# Run with detailed output for analysis
python -m pytest \
  tests/unit/websocket_ssot_migration/ \
  tests/integration/websocket_ssot_migration/ \
  -v --tb=long --capture=no
```

## Expected Test Outcomes

### Phase 1: Unit Tests Results
- ❌ **FAIL**: `test_single_websocket_manager_implementation_exists` - 3 implementations detected
- ❌ **FAIL**: `test_import_path_consolidation_complete` - Multiple import paths found
- ✅ **PASS**: `test_legacy_compatibility_layer_functions` - Compatibility maintained
- ❌ **FAIL**: `test_websocket_manager_interface_consistency` - Interface mismatches detected
- ❌ **FAIL**: `test_demo_websocket_bridge_compatibility_validation` - Issue #1209 interface mismatch
- ❌ **FAIL**: `test_concurrent_manager_initialization_safety` - Race conditions detected
- ❌ **FAIL**: `test_user_isolation_factory_pattern_consistency` - Singleton violations detected
- ❌ **FAIL**: `test_websocket_event_delivery_race_conditions` - Event delivery race conditions

### Phase 2: Integration Tests Results
- ❌ **FAIL**: `test_agent_websocket_bridge_integration_consistency` - Integration issues
- ❌ **FAIL**: `test_demo_websocket_service_compatibility` - DemoWebSocketBridge issues
- ❌ **FAIL**: `test_cross_service_interface_contracts` - Interface contract violations

### Phase 3: E2E Staging Tests Results
- ✅ **PASS**: `test_complete_user_journey_with_websocket_events` - Golden Path protected
- ✅ **PASS**: `test_websocket_five_critical_events_delivered` - Business value protected
- ✅ **PASS**: `test_production_readiness_concurrent_users` - Scalability validated

### Phase 4: Mission Critical Tests Results
- ❌ **FAIL**: `test_issue_1182_websocket_manager_ssot_consolidation` - SSOT violations detected

## Success Criteria

### ✅ SSOT Migration Complete When:
1. **Single Implementation**: Only 1 WebSocket manager implementation exists
2. **Import Consolidation**: All import paths resolve to same class
3. **Interface Consistency**: All signatures match across implementations
4. **User Isolation**: Enterprise-grade multi-user separation working
5. **Golden Path Protection**: Complete user journey working end-to-end
6. **Race Condition Elimination**: No initialization race conditions detected
7. **DemoWebSocketBridge Fixed**: Issue #1209 interface compatibility resolved

### 🚨 Business Value Protection:
- $500K+ ARR Golden Path functionality maintained throughout migration
- All 5 critical WebSocket events delivered: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Zero regression in user experience or system performance
- Enterprise-grade user isolation for HIPAA/SOC2/SEC compliance readiness

## Interpreting Test Results

### Initial State (Before SSOT Migration)
```
Unit Tests:      8/10 FAIL (80% failure rate) - EXPECTED
Integration:     3/3 FAIL (100% failure rate) - EXPECTED  
E2E Staging:     3/3 PASS (100% success rate) - REQUIRED
Mission Critical: 1/1 FAIL (100% failure rate) - EXPECTED
```

### Target State (After SSOT Migration)
```
Unit Tests:      10/10 PASS (100% success rate) - TARGET
Integration:     3/3 PASS (100% success rate) - TARGET
E2E Staging:     3/3 PASS (100% success rate) - MAINTAINED
Mission Critical: 1/1 PASS (100% success rate) - TARGET
```

## Troubleshooting Common Issues

### Import Errors
```bash
# If import errors occur, ensure project root is in Python path
export PYTHONPATH=/Users/anthony/Desktop/netra-apex:$PYTHONPATH
```

### Test Framework Dependencies
```bash
# Ensure test framework dependencies are available
python -c "from test_framework.ssot.base_test_case import SSotBaseTestCase; print('✓ SSOT test framework available')"
python -c "from test_framework.ssot.base_test_case import BaseIntegrationTest; print('✓ Integration test framework available')"
```

### Staging Environment Access
```bash
# Test staging environment connectivity
curl -I https://backend.staging.netrasystems.ai/health
```

## Post-Migration Validation

After completing the SSOT migration, run the complete test suite to verify:

```bash
# Comprehensive post-migration validation
python -m pytest \
  tests/unit/websocket_ssot_migration/ \
  tests/integration/websocket_ssot_migration/ \
  tests/e2e/staging/test_issue_1182_golden_path_websocket_validation.py \
  tests/mission_critical/test_websocket_ssot_multiple_managers_violation_detection.py \
  --tb=short -v

# Expected result: ALL tests should PASS
# If any tests still FAIL, SSOT migration is incomplete
```

## Documentation References

- **Issue #1182**: WebSocket Manager SSOT Migration (GitHub)
- **Issue #1209**: DemoWebSocketBridge interface failure (GitHub)  
- **CLAUDE.md**: Prime directives and SSOT requirements
- **USER_CONTEXT_ARCHITECTURE.md**: Factory patterns and user isolation
- **GOLDEN_PATH_USER_FLOW_COMPLETE.md**: Complete user journey documentation

---

**Remember**: These tests are designed to FAIL initially to prove the current SSOT violations exist. Success comes from systematically resolving each violation until all tests PASS, ensuring robust WebSocket SSOT consolidation while protecting critical business functionality.