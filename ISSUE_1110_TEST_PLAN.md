# 🧪 Issue #1110 Test Plan: UserExecutionContext Parameter Issues

**Issue:** UserExecutionContext parameter mismatches causing test failures
**Created:** 2025-09-14
**Priority:** P1 - Critical (Golden Path affecting)
**Business Impact:** $500K+ ARR dependency on SupervisorAgent functionality

## Executive Summary

This test plan focuses on reproducing, validating, and preventing UserExecutionContext parameter issues that are causing test failures across the system. Based on analysis, the issue appears to be test collection errors and parameter validation problems rather than core functionality failures.

## Current System Analysis

### ✅ VERIFIED: Core UserExecutionContext is Working
Based on investigation, the UserExecutionContext class **IS working correctly**:
- Constructor signature includes `websocket_client_id` parameter ✅
- Parameter validation tests are **PASSING** ✅
- Backward compatibility properties are present ✅

```python
# CONFIRMED WORKING SIGNATURE:
UserExecutionContext(
    user_id: str,
    thread_id: str, 
    run_id: str,
    websocket_client_id: Optional[str] = None,  # ✅ CORRECT PARAMETER
    # ... other parameters
)
```

### 🚨 IDENTIFIED: Test Collection Issues
The real issues are:
1. **Test Collection Errors**: Missing imports (`DatabaseTestManager`)
2. **Test Framework Issues**: Import path problems in five_whys tests
3. **Reproduction Test Mismatch**: Tests expecting failures that no longer occur

## Test Strategy Overview

### Phase 1: Reproduction and Validation Tests
**Goal:** Confirm the current state and validate that fixes are working

### Phase 2: Regression Prevention Tests  
**Goal:** Ensure the issues don't reoccur and catch similar problems early

### Phase 3: Integration Validation Tests
**Goal:** Validate SupervisorAgent functionality end-to-end

## Phase 1: Reproduction and Validation Tests

### Test Category: Unit Tests (No Docker Required)

#### Test 1.1: UserExecutionContext Parameter Validation
**File:** `tests/unit/test_userexecutioncontext_parameter_validation_1110.py`
**Purpose:** Validate UserExecutionContext constructor and parameters

```python
class TestUserExecutionContextParameterValidation:
    """Validate UserExecutionContext parameter handling for Issue #1110."""
    
    def test_websocket_client_id_parameter_present(self):
        """Verify websocket_client_id parameter exists (not websocket_connection_id)."""
        
    def test_constructor_parameter_compatibility(self):
        """Test constructor accepts all expected parameters."""
        
    def test_backward_compatibility_properties(self):
        """Test backward compatibility for legacy parameter names."""
        
    def test_parameter_type_validation(self):
        """Test parameter type validation and error handling."""
```

#### Test 1.2: SupervisorAgent Factory Pattern Validation
**File:** `tests/unit/test_supervisor_agent_factory_validation_1110.py`
**Purpose:** Validate SupervisorAgent creation with UserExecutionContext

```python
class TestSupervisorAgentFactoryValidation:
    """Validate SupervisorAgent factory patterns for Issue #1110."""
    
    def test_supervisor_agent_creation_with_context(self):
        """Test SupervisorAgent creation with UserExecutionContext."""
        
    def test_websocket_scoped_supervisor_parameters(self):
        """Test get_websocket_scoped_supervisor parameter handling."""
        
    def test_factory_method_parameter_forwarding(self):
        """Test factory methods properly forward UserExecutionContext."""
```

### Test Category: Integration Tests (Local Services Only)

#### Test 1.3: WebSocket Parameter Integration
**File:** `tests/integration/test_websocket_parameter_integration_1110.py`
**Purpose:** Test WebSocket manager creation with correct parameters

```python
class TestWebSocketParameterIntegration:
    """Integration tests for WebSocket parameter handling."""
    
    async def test_websocket_manager_creation_with_user_context(self):
        """Test WebSocket manager creation with UserExecutionContext."""
        
    async def test_websocket_client_id_propagation(self):
        """Test websocket_client_id properly propagated through factory chain."""
```

## Phase 2: Regression Prevention Tests

### Test Category: Contract Validation Tests

#### Test 2.1: Parameter Contract Enforcement
**File:** `tests/unit/test_parameter_contract_enforcement_1110.py`
**Purpose:** Prevent regression of parameter naming issues

```python
class TestParameterContractEnforcement:
    """Enforce parameter contracts to prevent Issue #1110 regression."""
    
    def test_userexecutioncontext_required_parameters(self):
        """Enforce required parameters in UserExecutionContext."""
        
    def test_forbidden_legacy_parameters(self):
        """Ensure legacy parameter names are not reintroduced."""
        
    def test_factory_method_signatures(self):
        """Validate factory method signatures remain consistent."""
```

#### Test 2.2: Breaking Change Detection
**File:** `tests/unit/test_breaking_change_detection_1110.py`
**Purpose:** Detect parameter signature changes that could break consumers

```python
class TestBreakingChangeDetection:
    """Detect breaking changes in UserExecutionContext interface."""
    
    def test_interface_compatibility_validation(self):
        """Validate interface remains compatible with consumers."""
        
    def test_parameter_position_stability(self):
        """Ensure parameter positions remain stable."""
```

## Phase 3: Integration Validation Tests

### Test Category: E2E Tests (Staging Environment)

#### Test 3.1: SupervisorAgent End-to-End Validation
**File:** `tests/e2e/staging/test_supervisor_agent_e2e_validation_1110.py`
**Purpose:** Validate complete SupervisorAgent workflow in staging

```python
class TestSupervisorAgentE2EValidation:
    """End-to-end validation of SupervisorAgent for Issue #1110."""
    
    @pytest.mark.staging
    async def test_supervisor_agent_complete_workflow(self):
        """Test complete supervisor agent workflow with real WebSocket."""
        
    @pytest.mark.staging  
    async def test_websocket_events_with_supervisor_agent(self):
        """Test all 5 WebSocket events sent during supervisor execution."""
```

## Test Execution Plan

### Execution Phase 1: Immediate Validation (2-3 minutes)
**Goal:** Confirm current system state and identify real issues

```bash
# 1. Run UserExecutionContext parameter validation
python3 -m pytest tests/unit/test_userexecutioncontext_parameter_validation_1110.py -v

# 2. Run factory contract validation
python3 -m pytest tests/unit/test_factory_contract_validation.py::TestUserExecutionContextValidation -v

# 3. Check for breaking changes
python3 -m pytest tests/unit/test_breaking_change_detection_1110.py -v
```

**Expected Outcomes:**
- UserExecutionContext parameter tests: **SHOULD PASS** (core is working)
- Factory contract tests: **SHOULD PASS** (already confirmed working)
- Breaking change tests: **SHOULD PASS** (validate no regressions)

### Execution Phase 2: Integration Testing (5-10 minutes)
**Goal:** Validate system integration without Docker dependency

```bash
# 1. Run WebSocket parameter integration tests
python3 -m pytest tests/integration/test_websocket_parameter_integration_1110.py -v

# 2. Run supervisor factory validation
python3 -m pytest tests/unit/test_supervisor_agent_factory_validation_1110.py -v

# 3. Run parameter contract enforcement
python3 -m pytest tests/unit/test_parameter_contract_enforcement_1110.py -v
```

**Expected Outcomes:**
- WebSocket integration: **MAY REVEAL ISSUES** (integration points could fail)
- Supervisor factory: **SHOULD PASS** (but may reveal factory pattern issues)
- Contract enforcement: **SHOULD PASS** (validates our assumptions)

### Execution Phase 3: Staging Validation (10-15 minutes)
**Goal:** Validate complete system functionality in staging environment

```bash
# 1. Run staging E2E supervisor agent tests
python3 -m pytest tests/e2e/staging/test_supervisor_agent_e2e_validation_1110.py -v --staging-e2e

# 2. Run mission critical WebSocket events test
python3 tests/mission_critical/test_websocket_agent_events_suite.py

# 3. Validate Golden Path user flow
python3 tests/remediation/test_issue_358_golden_path_validation.py -v
```

**Expected Outcomes:**
- Staging E2E tests: **SHOULD PASS** (validates business functionality)
- Mission critical WebSocket: **MUST PASS** ($500K+ ARR dependency)
- Golden Path: **MUST PASS** (core user workflow)

## Test Creation Guidelines

### Following CLAUDE.md Testing Principles

1. **Business Value > System > Tests**
   - Every test validates actual business functionality
   - Tests serve the working system, not vice versa

2. **Real Services > Mocks**  
   - Use real UserExecutionContext instances
   - Use real WebSocket connections where possible
   - Mock only external dependencies (LLM, OAuth)

3. **SSOT Compliance**
   - Inherit from `SSotBaseTestCase` or `SSotAsyncTestCase`
   - Use `test_framework` utilities
   - Follow absolute import patterns

4. **User Context Isolation**
   - Every test validates proper user isolation
   - No shared state between test runs
   - Factory pattern compliance

### Test Implementation Standards

```python
# GOOD: Real UserExecutionContext validation
def test_userexecutioncontext_with_real_parameters(self):
    """Test UserExecutionContext with actual parameters."""
    context = UserExecutionContext(
        user_id="usr_test_123",
        thread_id="thrd_test_123", 
        run_id="run_test_123",
        websocket_client_id="ws_test_123"
    )
    assert context.websocket_client_id == "ws_test_123"

# BAD: Mock-heavy test that proves nothing
def test_userexecutioncontext_with_mocks(self):
    """Test with mocks - proves nothing about real system."""
    mock_context = Mock()
    mock_context.websocket_client_id = "mocked"
    assert mock_context.websocket_client_id == "mocked"  # Useless!
```

## Regression Prevention Strategy

### 1. Automated Parameter Validation
Create tests that automatically detect parameter signature changes:

```python
def test_parameter_signature_stability(self):
    """Ensure UserExecutionContext signature remains stable."""
    sig = inspect.signature(UserExecutionContext.__init__)
    expected_params = {
        'user_id', 'thread_id', 'run_id', 'websocket_client_id'
    }
    actual_params = set(sig.parameters.keys())
    assert expected_params.issubset(actual_params)
```

### 2. Factory Pattern Validation
Validate factory methods maintain correct parameter forwarding:

```python
def test_factory_parameter_forwarding(self):
    """Ensure factory methods forward UserExecutionContext correctly."""
    # Test that factory methods accept and forward UserExecutionContext
    # without parameter name mismatches
```

### 3. Integration Point Monitoring
Monitor integration points where parameter mismatches commonly occur:

```python  
def test_websocket_manager_parameter_compatibility(self):
    """Test WebSocket manager accepts UserExecutionContext correctly."""
    # Validate that WebSocket-related factories properly handle
    # UserExecutionContext parameter naming
```

## Risk Assessment and Mitigation

### High Risk Areas
1. **WebSocket Factory Methods** - Complex parameter forwarding
2. **Supervisor Agent Creation** - Multiple factory layers
3. **Legacy Parameter Names** - Risk of reintroduction

### Mitigation Strategies
1. **Comprehensive Parameter Testing** - Test every factory method
2. **Breaking Change Detection** - Automated signature monitoring
3. **Integration Testing** - Real service integration validation

## Success Criteria

### Phase 1 Success: Validation Complete
- [ ] All UserExecutionContext parameter tests **PASS**
- [ ] Parameter naming is correct (`websocket_client_id` not `websocket_connection_id`)
- [ ] No test collection errors in parameter validation tests

### Phase 2 Success: Regression Prevention
- [ ] Contract enforcement tests **PASS**
- [ ] Breaking change detection tests **PASS**  
- [ ] Factory parameter forwarding tests **PASS**

### Phase 3 Success: Business Functionality
- [ ] SupervisorAgent E2E tests **PASS**
- [ ] Mission critical WebSocket events **PASS**
- [ ] Golden Path user flow **PASS**
- [ ] No regression in $500K+ ARR functionality

## Monitoring and Maintenance

### Continuous Monitoring
1. **Daily Parameter Validation**: Run parameter tests in CI
2. **Weekly Integration Tests**: Validate factory patterns work
3. **Release Validation**: Full E2E test suite before deployment

### Long-term Prevention
1. **Parameter Contract Registry**: Maintain authoritative parameter definitions
2. **Factory Pattern Documentation**: Document correct parameter forwarding
3. **Developer Education**: Train team on UserExecutionContext best practices

---

## Test Execution Commands Summary

```bash
# Phase 1: Core Validation (2-3 min)
python3 -m pytest tests/unit/test_userexecutioncontext_parameter_validation_1110.py -v
python3 -m pytest tests/unit/test_factory_contract_validation.py::TestUserExecutionContextValidation -v

# Phase 2: Integration Testing (5-10 min)  
python3 -m pytest tests/integration/test_websocket_parameter_integration_1110.py -v
python3 -m pytest tests/unit/test_supervisor_agent_factory_validation_1110.py -v

# Phase 3: Staging Validation (10-15 min)
python3 -m pytest tests/e2e/staging/test_supervisor_agent_e2e_validation_1110.py --staging-e2e -v
python3 tests/mission_critical/test_websocket_agent_events_suite.py

# Full Test Suite (20-30 min)
python3 tests/unified_test_runner.py --pattern "*1110*" --no-docker
```

## Expected Timeline
- **Test Creation**: 2-3 hours (following existing patterns)
- **Test Execution**: 20-30 minutes total
- **Issue Resolution**: Once tests identify root cause
- **Validation**: 1 hour for full regression testing

## Business Value Justification (BVJ)
- **Segment**: All (Free, Early, Mid, Enterprise, Platform) 
- **Business Goal**: Stability and reliability of core agent functionality
- **Value Impact**: Ensures SupervisorAgent works correctly for AI optimization
- **Strategic Impact**: Protects $500K+ ARR dependent on WebSocket agent events

---

**This test plan follows CLAUDE.md principles: Business Value > System > Tests, with focus on real services, SSOT compliance, and Golden Path protection.**