# CRITICAL AGENT TESTING EXPANSION PLAN

## Executive Summary
**CRITICAL**: Major gaps in agent workflow testing identified. Current tests passing but production showing 15+ critical errors in basic user flow.

## ROOT CAUSE ANALYSIS

### 1. Pydantic Validation Failures
**Issue**: LLM returning strings instead of dictionaries for nested fields
```
tool_recommendations.0.parameters
  Input should be a valid dictionary [type=dict_type, input_value='{ "performance_goal": "3...raint": "no_increase" }', input_type=str]
```
**Root Cause**: LLM structured generation returning JSON strings instead of parsed objects
**Impact**: Complete agent workflow failure, fallback mechanisms also failing

### 2. Database Session Errors
**Issue**: `'async_sessionmaker' object has no attribute 'execute'`
**Root Cause**: Incorrect database session usage in state persistence service
**Impact**: Cannot save/load agent state between runs

### 3. Serialization Errors
**Issue**: `Object of type datetime is not JSON serializable`
**Root Cause**: Missing datetime serialization in WebSocket broadcast
**Impact**: Cannot send updates to user, breaks real-time feedback

### 4. LLMResponse Not Fully Defined
**Issue**: `LLMResponse is not fully defined; you should define LLMProvider`
**Root Cause**: Circular dependency or missing model rebuild
**Impact**: Structured generation completely broken

### 5. WebSocket Message Validation
**Issue**: `Invalid message type: thread_created`
**Root Cause**: Message type not in allowed enum values
**Impact**: Cannot create new threads, breaks conversation flow

## CRITICAL TEST GAPS

### Gap 1: No LLM Response Validation Testing
- **Missing**: Tests for structured generation with actual LLM response patterns
- **Required**: Mock LLM responses that match real patterns (strings vs dicts)
- **Priority**: CRITICAL

### Gap 2: No State Persistence Integration Testing
- **Missing**: Tests for save/load with actual database sessions
- **Required**: Full database integration tests with async sessions
- **Priority**: CRITICAL

### Gap 3: No WebSocket Message Serialization Testing
- **Missing**: Tests for datetime and complex object serialization
- **Required**: End-to-end message flow with all field types
- **Priority**: CRITICAL

### Gap 4: No Fallback Mechanism Testing
- **Missing**: Tests ensuring fallbacks work when primary fails
- **Required**: Cascading failure scenarios with recovery validation
- **Priority**: HIGH

### Gap 5: No Circuit Breaker State Testing
- **Missing**: Tests for circuit breaker opening/closing behavior
- **Required**: Load testing with failure injection
- **Priority**: HIGH

## COMPREHENSIVE TEST EXPANSION PLAN

### Phase 1: IMMEDIATE (Week 1)
1. **Create Pydantic Validation Test Suite**
   - Test all agent response models with real LLM patterns
   - Include string-to-dict conversion scenarios
   - Validate all nested field types
   - Files: `test_agent_pydantic_validation.py`

2. **Create State Persistence Test Suite**
   - Test async session usage patterns
   - Test state save/load with all field types
   - Test datetime serialization
   - Files: `test_state_persistence_integration.py`

3. **Create WebSocket Message Test Suite**
   - Test all message types and validation
   - Test serialization of complex objects
   - Test broadcast with datetime fields
   - Files: `test_websocket_serialization.py`

### Phase 2: CRITICAL (Week 2)
4. **Create Agent Orchestration E2E Suite**
   - Test complete user flow from request to response
   - Test all agent handoffs and state passing
   - Test with real database and WebSocket
   - Files: `test_agent_orchestration_e2e.py`

5. **Create LLM Integration Test Suite**
   - Test structured generation with real responses
   - Test fallback JSON extraction
   - Test retry mechanisms
   - Files: `test_llm_integration_real.py`

6. **Create Reliability Test Suite**
   - Test circuit breaker behavior
   - Test retry with exponential backoff
   - Test timeout handling
   - Files: `test_reliability_mechanisms.py`

### Phase 3: COMPREHENSIVE (Week 3)
7. **Create Load and Stress Test Suite**
   - Test concurrent agent requests
   - Test resource isolation
   - Test performance degradation
   - Files: `test_agent_load_stress.py`

8. **Create Error Recovery Test Suite**
   - Test cascading failures
   - Test partial success scenarios
   - Test rollback mechanisms
   - Files: `test_error_recovery_scenarios.py`

9. **Create Data Validation Test Suite**
   - Test all input validation paths
   - Test output format compliance
   - Test schema evolution
   - Files: `test_data_validation_comprehensive.py`

### Phase 4: CONTINUOUS (Ongoing)
10. **Create Monitoring and Alerting Tests**
    - Test metric collection accuracy
    - Test alert triggering conditions
    - Test dashboard data flow
    - Files: `test_monitoring_alerting.py`

## TEST IMPLEMENTATION REQUIREMENTS

### 1. Real Data Patterns
```python
# WRONG - Current approach
llm_manager.ask_structured_llm = AsyncMock(return_value=mock_triage_result)

# RIGHT - What we need
llm_manager.ask_structured_llm = AsyncMock(side_effect=[
    # First call returns string instead of dict (real pattern)
    ValidationError("parameters: Input should be a valid dictionary"),
    # Retry returns correct format
    mock_triage_result
])
```

### 2. Database Session Patterns
```python
# Test actual async session usage
async with get_db_session() as session:
    # Test session.execute() not session() directly
    result = await session.execute(select(AgentState))
    # Test commit/rollback behavior
    await session.commit()
```

### 3. Serialization Patterns
```python
# Test datetime serialization
test_data = {
    "timestamp": datetime.now(),  # This will fail
    "data": {"nested": datetime.now()}  # This too
}
# Must test with proper JSON encoder
json.dumps(test_data, cls=DateTimeEncoder)
```

## ASSERTIONS REQUIRED PER WORKFLOW STEP

### User Request → Triage
1. Assert request validation passes
2. Assert triage result has all required fields
3. Assert category is valid enum value
4. Assert tool_recommendations have dict parameters
5. Assert confidence score in range [0, 1]

### Triage → Data Analysis
1. Assert state passed correctly
2. Assert data sources accessed
3. Assert metrics extracted
4. Assert analysis results structured
5. Assert no data loss in handoff

### Data → Optimization
1. Assert recommendations list of strings
2. Assert cost_savings is numeric
3. Assert performance_improvement percentage
4. Assert metadata timestamps valid
5. Assert fallback returns valid structure

### Optimization → Actions
1. Assert action plan has steps
2. Assert each step has required fields
3. Assert dependencies resolved
4. Assert resources identified
5. Assert timeline realistic

### Actions → Report
1. Assert report sections present
2. Assert content not empty
3. Assert formatting valid
4. Assert attachments accessible
5. Assert delivery successful

### Report → User
1. Assert WebSocket message sent
2. Assert serialization successful
3. Assert user receives complete data
4. Assert no truncation or loss
5. Assert real-time updates work

## METRICS FOR SUCCESS

### Coverage Targets
- Line coverage: 95% (currently ~60%)
- Branch coverage: 90% (currently ~40%)
- Integration coverage: 100% critical paths

### Performance Targets
- Test suite runtime: < 10 minutes
- Individual test: < 2 seconds
- E2E test: < 30 seconds

### Quality Targets
- Zero flaky tests
- All tests deterministic
- No test interdependencies

## IMPLEMENTATION PRIORITY

### IMMEDIATE (Next 24 Hours)
1. Fix Pydantic validation in triage_sub_agent
2. Fix OptimizationsResult recommendations field
3. Fix datetime serialization in WebSocket
4. Add integration tests for these fixes

### HIGH (Next 3 Days)
1. Implement Phase 1 test suites
2. Fix state persistence database session
3. Add circuit breaker tests
4. Validate all fallback paths

### CRITICAL (Next Week)
1. Complete Phase 2 test suites
2. Run full E2E validation
3. Load test with 100 concurrent users
4. Document all findings

## PREVENTION MEASURES

### 1. Mandatory Test Requirements
- No PR merged without tests for new agent code
- Integration tests required for agent changes
- E2E tests required for workflow changes

### 2. Continuous Validation
- Run E2E tests every 4 hours in staging
- Monitor production error rates
- Alert on validation error spikes

### 3. Type Safety Enforcement
- Strict Pydantic validation
- No Any types in agent interfaces
- Runtime type checking in production

## RESOURCES REQUIRED

### Team
- 2 Senior Engineers for test implementation
- 1 QA Engineer for test design
- 1 DevOps for CI/CD integration

### Timeline
- Week 1: Phase 1 + Critical Fixes
- Week 2: Phase 2 + Integration
- Week 3: Phase 3 + Load Testing
- Week 4: Phase 4 + Documentation

### Tools
- pytest-asyncio for async testing
- hypothesis for property testing
- locust for load testing
- pytest-benchmark for performance

## CONCLUSION

**CRITICAL**: The agent system is fundamentally broken in production despite passing tests. This plan addresses all identified gaps with specific, actionable test implementations. Immediate action required to prevent further production issues.

**KEY INSIGHT**: Current tests mock at too high a level, missing actual integration points where failures occur. New tests must validate actual data flow, not just function calls.