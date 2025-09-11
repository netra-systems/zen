# Comprehensive Test Plan for Issue #358: Complete Golden Path Failure

**CRITICAL ISSUE**: Complete system lockout preventing users from accessing AI responses
**BUSINESS IMPACT**: $500K+ ARR at risk due to complete user path blockage
**ANALYSIS SOURCE**: GOLDEN_PATH_USER_FLOW_COMPLETE.md comprehensive failure analysis

## Executive Summary

Issue #358 represents a **critical system failure** where users cannot access AI responses through ANY execution path. This test plan creates comprehensive validation of the three identified failure modes that must be reproduced and validated through failing tests that prove the business impact.

### Critical Failure Modes Identified

1. **HTTP API AttributeError** - `'RequestScopedContext' object has no attribute 'websocket_connection_id'` at dependencies.py line 960
2. **WebSocket Authentication Failures** - `unsupported subprotocol: jwt-auth` errors preventing connections  
3. **DEMO_MODE Missing Implementation** - No working bypass functionality for staging validation

## Test Categories and Strategy

### Test Requirements
- **MUST NOT require Docker** (use unit, integration non-docker, or e2e GCP staging remote)
- **MUST FAIL initially** to prove the issues exist and demonstrate business impact
- **Follow SSOT testing patterns** with real services where possible
- **Different difficulty levels** from simple reproduction to comprehensive validation
- **Focus on business impact** (users unable to get AI responses)

---

## 1. UNIT TESTS - Component-Level Failure Reproduction

### Test File: `tests/unit/golden_path/test_issue_358_component_failures.py`

**Purpose**: Reproduce specific component failures without external dependencies

#### Test Cases

##### 1.1 HTTP API RequestScopedContext Failure
```python
@pytest.mark.unit
def test_request_scoped_context_websocket_connection_id_missing():
    """
    DESIGNED TO FAIL: Reproduce AttributeError for websocket_connection_id.
    
    This test validates that RequestScopedContext objects lack the required
    websocket_connection_id attribute, causing HTTP API agent execution to fail.
    
    Business Impact: HTTP API fallback path broken, no alternative to WebSocket.
    """
```

##### 1.2 DEMO_MODE Configuration Detection
```python
@pytest.mark.unit
def test_demo_mode_environment_variable_detection():
    """
    DESIGNED TO FAIL: Prove DEMO_MODE=1 is not properly detected.
    
    This test validates that the DEMO_MODE configuration system fails to
    properly enable demo authentication bypass in isolated environments.
    
    Business Impact: Demo/staging environments cannot validate functionality.
    """
```

##### 1.3 WebSocket Protocol Format Validation
```python
@pytest.mark.unit
def test_websocket_subprotocol_format_validation():
    """
    DESIGNED TO FAIL: Reproduce unsupported subprotocol format errors.
    
    This test validates that WebSocket connections fail due to incorrect
    subprotocol format handling in authentication flow.
    
    Business Impact: Primary user interaction path (WebSocket chat) broken.
    """
```

### Expected Failure Patterns
- **AttributeError**: Missing `websocket_connection_id` property
- **Configuration Error**: DEMO_MODE detection fails
- **WebSocket Error**: Unsupported subprotocol rejection

---

## 2. INTEGRATION TESTS - Service Interaction Failures  

### Test File: `tests/integration/golden_path/test_issue_358_service_interaction_failures.py`

**Purpose**: Test service-to-service interaction failures that break Golden Path

#### Test Cases

##### 2.1 HTTP to WebSocket Bridge Failure
```python
@pytest.mark.integration
@pytest.mark.no_docker
async def test_http_api_websocket_bridge_dependency_failure():
    """
    DESIGNED TO FAIL: Demonstrate HTTP API dependency on WebSocket context.
    
    This integration test shows how HTTP API agent execution fails when
    WebSocket-specific context objects are required but unavailable.
    
    Business Impact: HTTP API cannot execute agents independently of WebSocket.
    """
```

##### 2.2 Authentication Service Context Mismatch
```python
@pytest.mark.integration
@pytest.mark.no_docker
async def test_authentication_context_websocket_dependency():
    """
    DESIGNED TO FAIL: Show authentication context assumes WebSocket connection.
    
    This test demonstrates how authentication systems fail when WebSocket
    connection context is expected but HTTP requests don't provide it.
    
    Business Impact: Authentication failures block all user access paths.
    """
```

##### 2.3 Agent Execution Context Isolation Failure
```python
@pytest.mark.integration
@pytest.mark.no_docker
async def test_agent_execution_context_creation_failure():
    """
    DESIGNED TO FAIL: Prove agent execution context creation fails without WebSocket.
    
    This test shows how UserExecutionContext creation fails when WebSocket
    connection metadata is required but unavailable via HTTP API.
    
    Business Impact: Agent execution completely blocked for HTTP requests.
    """
```

### Expected Integration Failures
- **Context Creation**: UserExecutionContext fails without WebSocket metadata
- **Authentication**: JWT validation requires WebSocket-specific context
- **Agent Execution**: Supervisor agents fail to start without proper context

---

## 3. E2E TESTS - Complete Golden Path Validation on GCP Staging

### Test File: `tests/e2e/staging/test_issue_358_complete_golden_path_failure.py`

**Purpose**: Validate complete user journey failures in real staging environment

#### Test Cases

##### 3.1 Complete WebSocket Path Failure
```python
@pytest.mark.e2e
@pytest.mark.staging_remote
async def test_complete_websocket_authentication_failure_e2e():
    """
    DESIGNED TO FAIL: Demonstrate complete WebSocket path failure in staging.
    
    This E2E test connects to real GCP staging environment and validates
    that WebSocket connections fail with 1011 errors, blocking primary
    user interaction path.
    
    Business Impact: 90% of platform value (chat) completely inaccessible.
    """
```

##### 3.2 Complete HTTP API Path Failure  
```python
@pytest.mark.e2e
@pytest.mark.staging_remote
async def test_complete_http_api_path_failure_e2e():
    """
    DESIGNED TO FAIL: Demonstrate complete HTTP API path failure in staging.
    
    This E2E test attempts HTTP API agent execution in real staging and
    validates that AttributeError prevents any agent responses.
    
    Business Impact: Fallback execution path broken, no alternative access.
    """
```

##### 3.3 Complete System Lockout Validation
```python
@pytest.mark.e2e
@pytest.mark.staging_remote
async def test_complete_system_lockout_e2e():
    """
    DESIGNED TO FAIL: Prove complete system lockout - no working user paths.
    
    This comprehensive E2E test attempts all possible user access patterns:
    - WebSocket chat interface
    - HTTP API direct calls
    - DEMO_MODE bypass attempts
    
    Validates that ALL paths fail, proving complete system lockout.
    
    Business Impact: $500K+ ARR completely inaccessible - critical business emergency.
    """
```

##### 3.4 DEMO_MODE Staging Bypass Failure
```python
@pytest.mark.e2e
@pytest.mark.staging_remote
async def test_demo_mode_bypass_failure_staging_e2e():
    """
    DESIGNED TO FAIL: Prove DEMO_MODE bypass doesn't work in staging.
    
    This test validates that DEMO_MODE=1 configuration fails to enable
    authentication bypass in staging environment, preventing validation
    of system functionality.
    
    Business Impact: Cannot validate system health or demonstrate to prospects.
    """
```

### Expected E2E Failures
- **WebSocket 1011**: All WebSocket connections fail with internal errors
- **HTTP 500**: HTTP API requests fail with AttributeError
- **Authentication**: All authentication paths fail or timeout
- **Agent Execution**: No successful agent responses through any path

---

## 4. MISSION CRITICAL TESTS - Business Impact Validation

### Test File: `tests/mission_critical/test_issue_358_business_impact_validation.py`

**Purpose**: Validate business-critical functionality is completely broken

#### Test Cases

##### 4.1 Revenue-Generating User Flow Validation
```python
@pytest.mark.mission_critical
@pytest.mark.no_skip
async def test_revenue_generating_user_flow_completely_blocked():
    """
    MISSION CRITICAL FAILURE: Validate that revenue-generating user flows fail.
    
    This test demonstrates that the primary revenue-generating user workflow
    (user sends message -> gets AI response) is completely broken.
    
    Business Impact: $500K+ ARR functionality completely inaccessible.
    """
```

##### 4.2 Customer Experience Degradation
```python
@pytest.mark.mission_critical
@pytest.mark.no_skip
async def test_customer_experience_complete_degradation():
    """
    MISSION CRITICAL FAILURE: Validate complete customer experience failure.
    
    This test simulates customer usage patterns and validates that all
    expected interactions fail, proving complete customer experience breakdown.
    
    Business Impact: Customer retention at risk, potential churn.
    """
```

---

## 5. PERFORMANCE IMPACT TESTS - System Health Validation

### Test File: `tests/performance/test_issue_358_system_health_impact.py`

**Purpose**: Measure performance impact of failure conditions

#### Test Cases

##### 5.1 System Resource Consumption During Failures
```python
@pytest.mark.performance
async def test_system_resource_consumption_during_failures():
    """
    Performance validation of resource consumption during failure states.
    
    This test measures CPU/memory usage when system is in failure state
    to validate that failures don't cause resource leaks or cascading issues.
    """
```

##### 5.2 Error Rate and Recovery Metrics
```python
@pytest.mark.performance
async def test_error_rate_and_recovery_metrics():
    """
    Performance validation of error rates and recovery attempts.
    
    This test measures how frequently failures occur and validates
    that system doesn't enter infinite retry loops consuming resources.
    """
```

---

## Test Execution Strategy

### Phase 1: Component Failure Validation (Unit Tests)
```bash
# Run unit tests to prove component failures
python -m pytest tests/unit/golden_path/test_issue_358_component_failures.py -v --tb=short

# Expected: All tests FAIL with specific AttributeErrors and configuration issues
```

### Phase 2: Service Integration Failure Validation  
```bash
# Run integration tests without Docker dependency
python -m pytest tests/integration/golden_path/test_issue_358_service_interaction_failures.py -v --tb=short -m "no_docker"

# Expected: All tests FAIL with service interaction issues
```

### Phase 3: Complete System Validation (E2E Staging)
```bash
# Run E2E tests against real GCP staging environment
python -m pytest tests/e2e/staging/test_issue_358_complete_golden_path_failure.py -v --tb=short -m "staging_remote"

# Expected: All tests FAIL proving complete system lockout
```

### Phase 4: Business Impact Assessment (Mission Critical)
```bash
# Run mission critical tests to validate business impact
python -m pytest tests/mission_critical/test_issue_358_business_impact_validation.py -v --tb=short

# Expected: All tests FAIL proving $500K+ ARR impact
```

---

## Success Criteria (After Fixes)

### Unit Test Success Criteria
- RequestScopedContext has proper `websocket_connection_id` property or fallback
- DEMO_MODE environment variable detection works correctly
- WebSocket subprotocol format validation passes

### Integration Test Success Criteria  
- HTTP API can execute agents without WebSocket dependency
- Authentication context works for both HTTP and WebSocket paths
- Agent execution context creation succeeds for all execution paths

### E2E Test Success Criteria
- WebSocket connections succeed with proper authentication
- HTTP API provides working fallback when WebSocket fails
- DEMO_MODE bypass works in staging/demo environments
- At least one complete user execution path works end-to-end

### Business Impact Success Criteria
- Revenue-generating user flows work (user gets AI responses)
- Customer experience shows clear progress and completion
- System demonstrates business value delivery

---

## Test Infrastructure Requirements

### Environment Configuration
```bash
# Required environment variables for testing
export NETRA_TEST_MODE=1
export DEMO_MODE=1  # For demo mode testing
export STAGING_REMOTE_TESTING=1  # For E2E staging tests
export TEST_TIMEOUT=60  # Extended timeout for failure scenarios
```

### Test Dependencies
- **No Docker Required**: All tests designed for local/CI execution
- **Real Service Access**: E2E tests require GCP staging access
- **SSOT Test Framework**: All tests inherit from SSot test base classes
- **Isolated Environment**: All tests use IsolatedEnvironment for config

### Test Markers
```python
# Test markers for categorization
@pytest.mark.unit           # Component-level tests
@pytest.mark.integration    # Service interaction tests  
@pytest.mark.e2e           # End-to-end validation
@pytest.mark.mission_critical  # Business-critical validation
@pytest.mark.no_docker     # No Docker dependency required
@pytest.mark.staging_remote # Requires GCP staging access
@pytest.mark.no_skip       # Must never be skipped
```

---

## Expected Business Impact Documentation

### Pre-Fix State (All Tests Should FAIL)
- **WebSocket Path**: 0% success rate (1011 errors)
- **HTTP API Path**: 0% success rate (AttributeError)  
- **DEMO_MODE Path**: 0% success rate (not implemented)
- **Overall System**: 0% success rate (complete lockout)
- **Business Impact**: $500K+ ARR completely inaccessible

### Post-Fix State (Tests Should PASS)
- **WebSocket Path**: >95% success rate
- **HTTP API Path**: >90% success rate (fallback working)
- **DEMO_MODE Path**: 100% success rate in demo environments
- **Overall System**: >95% success rate (redundant paths)
- **Business Impact**: $500K+ ARR restored and protected

---

## Implementation Timeline

### Week 1: Test Creation and Validation
- [ ] Create unit tests for component failures
- [ ] Create integration tests for service interaction failures  
- [ ] Validate all tests FAIL as expected (proving issues exist)

### Week 2: E2E and Mission Critical Testing
- [ ] Create E2E tests for complete system validation
- [ ] Create mission critical tests for business impact validation
- [ ] Document complete failure patterns and business impact

### Week 3: Test Infrastructure and Automation
- [ ] Integrate tests into CI/CD pipeline  
- [ ] Create automated reporting for failure patterns
- [ ] Establish test success criteria and monitoring

### Week 4: Post-Fix Validation  
- [ ] Validate tests pass after fixes implemented
- [ ] Confirm business impact restoration
- [ ] Document lessons learned and prevention strategies

---

## Risk Mitigation

### Test Execution Risks
- **Staging Environment Availability**: E2E tests require stable staging access
- **Authentication Dependencies**: Tests may require valid staging credentials  
- **Resource Consumption**: Performance tests may impact system resources

### Business Risk Documentation
- **Revenue Impact**: Document exact revenue calculations affected
- **Customer Impact**: Track customer experience degradation metrics
- **Competitive Impact**: Assess impact on competitive positioning

---

## Conclusion

This comprehensive test plan provides systematic validation of Issue #358 through multiple test categories, proving the complete Golden Path failure and its $500K+ ARR business impact. The tests are designed to:

1. **FAIL initially** - Proving the critical issues exist
2. **Cover all failure modes** - HTTP API, WebSocket, and DEMO_MODE issues  
3. **Validate business impact** - Demonstrating complete user lockout
4. **Provide success criteria** - Clear metrics for when issues are resolved

The test plan follows CLAUDE.md requirements with SSOT compliance, no Docker dependencies for most tests, and focus on business value validation through real service testing where possible.