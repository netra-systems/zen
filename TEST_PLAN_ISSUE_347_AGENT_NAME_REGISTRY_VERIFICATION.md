# Test Plan: Issue #347 Agent Name Registry Mismatch Verification

## Executive Summary

Based on current analysis, **Issue #347 appears to be RESOLVED**. The agent registry correctly registers `"optimization"` agents and all tests pass. This test plan will provide comprehensive verification to confirm the resolution and prevent regressions.

## Current Analysis Results

### ✅ Registry State Verification
```
Registered agent names: ['triage', 'data', 'optimization', 'actions', 'reporting', 'goals_triage', 'data_helper', 'synthetic_data', 'corpus_admin']

Registry has "optimization": True
Registry has "apex_optimizer": False  # Correctly NOT registered
Registry has "optimizer": False       # Correctly NOT registered
```

### ✅ Test Status
- All existing Issue #347 tests **PASS** (5/5)
- Unit tests correctly verify naming consistency  
- Integration tests validate real agent creation workflows

## Comprehensive Test Strategy

### Phase 1: Unit Tests - Agent Registry Consistency ⭐ HIGH PRIORITY

**Objective**: Verify agent registry internal consistency and naming patterns

#### Test 1.1: Core Agent Registration Verification
```bash
# Test agent registry registers expected core agents
python3 -m pytest tests/unit/test_agent_name_mismatch_issue347.py::AgentNameMismatchUnitTests::test_agent_registry_registered_names -v
```

**Expected**: All core agents (`triage`, `data`, `optimization`, `actions`, `reporting`) are registered

#### Test 1.2: Negative Testing - Incorrect Names
```bash  
# Test that incorrect names properly fail
python3 -m pytest tests/unit/test_agent_name_mismatch_issue347.py::AgentNameMismatchUnitTests::test_apex_optimizer_name_expectation_fails -v
```

**Expected**: `apex_optimizer`, `optimizer` names correctly return None/fail

#### Test 1.3: Agent Lookup Consistency
```bash
# Test registry lookup patterns work correctly
python3 -m pytest tests/unit/test_agent_name_mismatch_issue347.py::AgentNamingConsistencyUnitTests::test_agent_lookup_error_handling -v
```

**Expected**: Registry correctly recognizes valid names, rejects invalid names

### Phase 2: Integration Tests - Golden Path Agent Orchestration ⭐ HIGH PRIORITY

**Objective**: Verify agent registry works in real Golden Path workflows without Docker dependencies

#### Test 2.1: Real Agent Registry Integration 
```bash
# Test real agent registry with proper service isolation
python3 -m pytest tests/integration/test_agent_registry_name_consistency_issue347.py::AgentRegistryNameConsistencyIntegrationTests::test_real_agent_registry_naming_patterns -v
```

**Expected**: Real registry matches unit test expectations

#### Test 2.2: Multi-User Agent Creation Workflow
```bash
# Test agent creation works with correct names across multiple users
python3 -m pytest tests/integration/test_agent_registry_name_consistency_issue347.py::AgentRegistryNameConsistencyIntegrationTests::test_agent_creation_workflow_with_correct_names -v
```

**Expected**: Agent creation succeeds with `optimization`, `triage`, `data` names

#### Test 2.3: Agent Creation Failure with Incorrect Names
```bash
# Test agent creation properly fails with incorrect names
python3 -m pytest tests/integration/test_agent_registry_name_consistency_issue347.py::AgentRegistryNameConsistencyIntegrationTests::test_agent_creation_workflow_with_incorrect_names -v
```

**Expected**: Agent creation fails/returns None for `apex_optimizer`, `optimizer` names

### Phase 3: E2E Tests - GCP Staging Golden Path Validation ⭐ CRITICAL

**Objective**: Verify agent naming works in real staging environment end-to-end

#### Test 3.1: E2E Golden Path Agent Discovery
```bash
# Test complete user journey on GCP staging
python3 -m pytest tests/e2e/staging/test_agent_orchestration_name_consistency_issue347.py -v --tb=short
```

**Expected**: Complete user flow works with correct agent names

#### Test 3.2: WebSocket Agent Event Integration
```bash  
# Test WebSocket events work with correct agent names
python3 -m pytest tests/e2e/staging/test_agent_orchestration_name_consistency_issue347.py::TestAgentOrchestrationNameConsistency::test_websocket_agent_events_with_correct_names -v
```

**Expected**: WebSocket events (agent_started, agent_thinking, etc.) work with `optimization` agent

#### Test 3.3: Multi-Agent Workflow Consistency  
```bash
# Test complex multi-agent workflows use consistent naming
python3 -m pytest tests/e2e/staging/test_agent_orchestration_name_consistency_issue347.py::TestAgentOrchestrationNameConsistency::test_multi_agent_workflow_naming_consistency -v
```

**Expected**: All agent handoffs use consistent registry names

### Phase 4: Regression Prevention Tests

#### Test 4.1: Agent Factory Pattern Validation
```python
# Verify factory patterns maintain naming consistency
def test_agent_factory_naming_consistency():
    """Ensure agent factories use correct registry names"""
    # Test that factories create agents with expected names
    # Verify no hardcoded incorrect names in factory methods
```

#### Test 4.2: Database Model Alignment Check
```python  
def test_database_model_agent_name_alignment():
    """Verify database models align with registry names"""
    # Test that database queries use correct agent names
    # Verify no database references to deprecated names
```

#### Test 4.3: Golden Path Message Flow Validation
```python
def test_golden_path_message_flow_agent_names():
    """Verify Golden Path uses correct agent names throughout"""
    # Test user message → triage → optimization → actions flow
    # Verify each step uses correct registry names
```

## Test Execution Commands

### Quick Verification (5 minutes)
```bash
# Run core Issue #347 tests to verify current state
python3 -m pytest tests/unit/test_agent_name_mismatch_issue347.py tests/integration/test_agent_registry_name_consistency_issue347.py -v --tb=short
```

### Comprehensive Testing (15 minutes)  
```bash
# Run all agent naming related tests
python3 -m pytest tests/ -k "agent_name_mismatch or agent_registry_name_consistency or agent_orchestration_name_consistency" -v --tb=short
```

### Golden Path Integration (30 minutes)
```bash
# Test complete Golden Path workflows with real services (no Docker)
python3 tests/unified_test_runner.py --category integration --tags agent_registry,golden_path --no-docker --real-services
```

### Full E2E Staging Validation (60 minutes)
```bash
# Complete end-to-end testing on GCP staging
python3 tests/unified_test_runner.py --category e2e --env staging --tags golden_path,agent_orchestration --real-llm
```

## Success Criteria

### ✅ Must Pass: Core Functionality
1. **Agent Registry Consistency**: All core agents registered with correct names
2. **Agent Creation Success**: Agents create successfully with `optimization`, `triage`, `data` names  
3. **Agent Creation Failure**: Agents properly fail with `apex_optimizer`, `optimizer` names
4. **Golden Path Flow**: Complete user workflow works end-to-end

### ✅ Must Pass: Integration Quality
1. **Multi-User Isolation**: Agent naming consistent across concurrent users
2. **WebSocket Events**: All 5 critical events work with correct agent names
3. **Real Services**: Tests work with real LLM, database, and WebSocket services
4. **Staging Environment**: Tests pass on actual GCP staging infrastructure

### ✅ Must Pass: Regression Prevention  
1. **Factory Patterns**: Agent factories use correct registry names
2. **Database Alignment**: Database models reference correct agent names
3. **Configuration Consistency**: All config files use correct agent names
4. **Documentation Accuracy**: Docs reflect actual registry behavior

## Risk Assessment

### 🟢 LOW RISK: Issue Appears Resolved
- **Current Evidence**: All tests pass, registry state is correct
- **Likelihood of Problems**: Low - naming is consistent throughout codebase
- **Impact if Problems Found**: Medium - would affect agent discovery/creation

### 🟡 MEDIUM RISK: Configuration Drift
- **Risk**: Environment-specific configs might have incorrect names
- **Mitigation**: Test across all environments (dev, staging, prod)
- **Detection**: E2E tests on real infrastructure

### 🟡 MEDIUM RISK: New Code Regression
- **Risk**: Future code might introduce incorrect agent names
- **Mitigation**: Comprehensive test suite prevents regressions
- **Detection**: Unit and integration tests catch naming issues early

## Expected Outcomes

### If Issue #347 is Truly Resolved ✅
- **All tests PASS**: Registry works correctly with `optimization` name
- **Golden Path Works**: Complete user flow operates normally  
- **No Action Needed**: Issue can be marked as resolved
- **Monitoring**: Continue running tests to prevent regression

### If Hidden Issues Discovered ⚠️
- **Specific Test Failures**: Identify exact failure points
- **Root Cause Analysis**: Determine why naming inconsistency persists
- **Targeted Fixes**: Address specific areas where incorrect names are used
- **Re-verification**: Run tests again after fixes

### If Infrastructure Issues Found 🔧
- **Environment-Specific**: Problems only in certain environments
- **Configuration Updates**: Update configs to use correct names
- **Deployment Verification**: Ensure staging/prod match development

## Test Implementation Priority

### 🚀 IMMEDIATE (Hours 0-2)
1. **Unit Test Verification**: Confirm all existing tests pass
2. **Integration Test Run**: Verify real agent creation works
3. **Quick Golden Path Check**: Basic user flow validation

### 🎯 HIGH PRIORITY (Hours 2-8) 
1. **E2E Staging Tests**: Comprehensive staging environment validation
2. **Multi-User Testing**: Verify concurrent user scenarios
3. **WebSocket Integration**: Confirm agent events work correctly

### 📋 STANDARD PRIORITY (Hours 8-24)
1. **Regression Prevention**: Add additional safeguard tests  
2. **Documentation Verification**: Ensure docs match reality
3. **Performance Testing**: Verify naming doesn't impact performance

### 🔄 ONGOING MONITORING
1. **Daily Test Runs**: Include agent naming tests in CI/CD
2. **Environment Checks**: Verify consistency across all environments
3. **New Feature Testing**: Ensure new agents follow naming patterns

## Conclusion

**Issue #347 appears to be RESOLVED** based on current analysis. The test plan above will provide comprehensive verification to:

1. **Confirm Resolution**: Verify the issue is truly fixed
2. **Prevent Regression**: Ensure the issue doesn't reoccur  
3. **Golden Path Protection**: Ensure agent naming doesn't break user workflows
4. **Production Readiness**: Validate staging and production environments

The test strategy follows the CLAUDE.md guidelines by:
- ✅ **Using Real Services**: Integration/E2E tests use real LLM, database, WebSocket
- ✅ **No Mocks in Integration**: E2E tests use actual staging infrastructure
- ✅ **E2E Auth Mandatory**: All tests use real authentication flow
- ✅ **Golden Path Focus**: Tests prioritize user login → AI response workflow
- ✅ **Business Value**: Tests verify substantive AI chat functionality works

Execute the **Quick Verification** tests first to confirm the current state, then proceed with comprehensive testing based on results.