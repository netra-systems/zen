[BUG] Concurrent agent execution test fails - all 5 executions raise exceptions preventing user isolation validation

## Impact
**CRITICAL**: This test validates $500K+ ARR chat functionality by ensuring concurrent agent execution maintains proper user isolation. Failure indicates potential user data bleeding or execution interference that could affect multiple users simultaneously using the AI platform.

## Current Behavior
Test `TestAgentExecutionCoreConcurrency::test_concurrent_agent_execution_isolation` fails with:
- **Error**: `AssertionError: Expected 5 successful executions, got 0`
- **Root Cause**: All 5 concurrent `execution_core.execute_agent(context, state)` calls raise exceptions
- **Hidden Failures**: Exceptions are caught in try-catch blocks, masking the actual error details

## Expected Behavior
All 5 concurrent agent executions should complete successfully, demonstrating:
- Proper user isolation between concurrent executions
- No shared state interference 
- Unique correlation IDs for each execution
- Successful WebSocket event delivery for each user

## Reproduction Steps
1. Run: `python -m pytest /netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_concurrent_agent_execution_isolation -v`
2. Observe: Test fails with 0 successful executions
3. Result: All concurrent agent executions raise exceptions

## Technical Details
- **File**: `/netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py:380`
- **Test Method**: `test_concurrent_agent_execution_isolation` (line 328)
- **Error**: `AssertionError: Expected 5 successful executions, got 0`
- **Environment**: Unit test environment

## Investigation Required
**Five Whys Analysis Needed:**
1. **What specific exceptions** are being raised during `execute_agent` calls?
2. **Are timeout_manager, state_tracker, execution_tracker** properly initialized in test fixtures?
3. **Do `create_test_context()` and `create_test_state()` methods** create valid objects?
4. **Are there missing dependencies** (WebSocket bridge, registry setup) in test environment?
5. **Is the AgentExecutionCore** expecting external services that aren't mocked?

## Root Cause Investigation Plan
- [ ] Add exception logging to reveal actual error messages
- [ ] Verify all AgentExecutionCore dependencies are properly mocked
- [ ] Check if `async_fixture("execution_core")` creates fully functional mock
- [ ] Validate test context and state creation methods
- [ ] Review recent changes to AgentExecutionCore or dependencies

## Acceptance Criteria
- [ ] All 5 concurrent agent executions succeed  
- [ ] Test demonstrates proper user isolation
- [ ] No exceptions raised during agent execution
- [ ] WebSocket events delivered correctly for each execution
- [ ] Correlation IDs are unique across concurrent executions

## Business Value
**Segment**: All (Free/Early/Mid/Enterprise)  
**Goal**: Stability - prevent user experience failures under concurrent load  
**Revenue Impact**: Protects $500K+ ARR by ensuring chat functionality works for multiple simultaneous users