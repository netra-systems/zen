# TEST PLAN: Issue #1025 - Timeout Protection WebSocket Notification

**Issue:** `test_timeout_protection_prevents_hung_agents` fails because `notify_agent_error` is not called during timeout scenarios.

**Business Impact:** $500K+ ARR at risk - users experiencing timeouts don't receive WebSocket notifications, leading to poor user experience and perceived system failures.

**Date:** 2025-09-14  
**Focus:** Timeout protection WebSocket notification patterns  
**Test Strategy:** Unit testing without Docker, focused on timeout behavior validation

## Problem Analysis

### Current Failing Test
- **Test:** `test_timeout_protection_prevents_hung_agents`
- **File:** `netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py:265`
- **Failure:** `AssertionError: Expected 'notify_agent_error' to have been called.`
- **Execution Time:** Test passes timeout validation (0.28s < 1.0s) but fails WebSocket notification assertion

### Root Cause Analysis
**Current AgentExecutionCore Timeout Handling:**

1. **TimeoutError Path** (line 605-636): 
   - Logs timeout error with detailed context
   - Creates AgentExecutionResult with timeout error
   - **MISSING:** `notify_agent_error` call
   - **State Tracking:** Calls `agent_tracker.transition_state` to TIMEOUT phase

2. **asyncio.TimeoutError Path** (line 826-843):
   - Logs execution timeout in `_execute_with_protection`  
   - Returns AgentExecutionResult with timeout error
   - **MISSING:** `notify_agent_error` call

3. **General Exception Path** (line 851-860):
   - **PRESENT:** Has `notify_agent_error` call
   - Only triggered for non-timeout exceptions

**Key Finding:** WebSocket error notification is only sent for general exceptions, not for timeout-specific scenarios.

## Test Execution Strategy

### Phase 1: Current Failing Test Analysis

#### Test Command
```bash
python3 -m pytest netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_timeout_protection_prevents_hung_agents -v -s --tb=short
```

#### Expected Current Behavior
- ✅ **Timeout Detection:** Test should timeout correctly (< 1.0s duration)
- ✅ **Result Validation:** `result.success` should be `False`
- ✅ **Error Message:** `result.error` should contain "timeout"
- ❌ **WebSocket Notification:** `notify_agent_error` should be called (CURRENTLY FAILS)

#### Test Infrastructure Assessment
- **Mock Setup:** WebSocket bridge properly mocked with `AsyncMock`
- **Timeout Simulation:** Uses `asyncio.sleep(2)` with 0.1s timeout
- **Agent Configuration:** Properly configured slow agent with correct mock methods
- **Test Environment:** Isolated unit test environment without external dependencies

### Phase 2: Broader Timeout Test Validation

#### Additional Test Commands
```bash
# Run full test suite for AgentExecutionCore module
python3 -m pytest netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py -v --tb=short

# Run specific timeout-related tests
python3 -m pytest netra_backend/tests/unit/agents/supervisor/ -k "timeout" -v --tb=short

# Validate WebSocket notification consistency across all agent execution tests
python3 -m pytest netra_backend/tests/unit/agents/supervisor/ -k "websocket" -v --tb=short
```

#### Related Tests to Validate
1. **`test_agent_death_detection_prevents_silent_failures`** - Should verify `notify_agent_error` is called for dead agents
2. **`test_error_boundaries_provide_graceful_degradation`** - Should verify `notify_agent_error` is called for general exceptions
3. **`test_websocket_bridge_propagation_enables_user_feedback`** - Should verify WebSocket event propagation patterns
4. **`test_metrics_collection_enables_business_insights`** - Should verify execution tracking patterns

### Phase 3: Test Infrastructure Deep Validation

#### WebSocket Bridge Mock Validation
```bash
# Test that WebSocket bridge mock setup is correct
python3 -c "
import asyncio
from unittest.mock import AsyncMock

# Verify AsyncMock behavior matches test expectations
bridge = AsyncMock()
bridge.notify_agent_error = AsyncMock(return_value=True)

async def test_mock():
    await bridge.notify_agent_error('test_run', 'test_agent', 'test_error')
    print(f'notify_agent_error called: {bridge.notify_agent_error.called}')
    print(f'call_count: {bridge.notify_agent_error.call_count}')
    print(f'call_args: {bridge.notify_agent_error.call_args}')

asyncio.run(test_mock())
"
```

#### Agent Mock Validation
```bash
# Test that agent timeout simulation works correctly
python3 -c "
import asyncio
from unittest.mock import AsyncMock

async def slow_execute(*args, **kwargs):
    await asyncio.sleep(2)
    return {'success': True, 'result': 'should not complete'}

agent = AsyncMock()
agent.execute = AsyncMock(side_effect=slow_execute)

async def test_timeout():
    start = asyncio.get_event_loop().time()
    try:
        result = await asyncio.wait_for(agent.execute(), timeout=0.1)
        print('ERROR: Should have timed out')
    except asyncio.TimeoutError:
        duration = asyncio.get_event_loop().time() - start
        print(f'SUCCESS: Timed out after {duration:.3f}s')

asyncio.run(test_timeout())
"
```

### Phase 4: Current Timeout Protection Behavior Documentation

#### Test Execution Commands
```bash
# Test current timeout behavior in isolation
python3 -c "
import asyncio
import sys
sys.path.append('.')

async def test_timeout_behavior():
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from unittest.mock import AsyncMock, Mock
    from uuid import uuid4
    
    # Create mock registry and WebSocket bridge
    registry = Mock()
    websocket_bridge = AsyncMock()
    websocket_bridge.notify_agent_error = AsyncMock(return_value=True)
    websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
    
    # Create slow agent that will timeout
    slow_agent = AsyncMock()
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(2)
        return {'success': True, 'result': 'should not complete'}
    
    slow_agent.execute = AsyncMock(side_effect=slow_execute)
    slow_agent.set_websocket_bridge = Mock()
    slow_agent.set_trace_context = Mock()
    registry.get_async = AsyncMock(return_value=slow_agent)
    
    # Create execution core
    core = AgentExecutionCore(registry, websocket_bridge)
    
    # Create execution contexts
    context = AgentExecutionContext(
        agent_name='timeout_test_agent',
        run_id=uuid4(),
        thread_id='test-thread',
        user_id='test-user',
        correlation_id='test-correlation'
    )
    
    user_context = UserExecutionContext(
        user_id='test-user',
        thread_id='test-thread',
        run_id=str(uuid4())
    )
    
    # Execute with short timeout
    try:
        result = await core.execute_agent(context, user_context, timeout=0.1)
        print(f'Result success: {result.success}')
        print(f'Result error: {result.error}')
        print(f'notify_agent_error called: {websocket_bridge.notify_agent_error.called}')
        print(f'notify_agent_error call_count: {websocket_bridge.notify_agent_error.call_count}')
        if websocket_bridge.notify_agent_error.call_args:
            print(f'notify_agent_error call_args: {websocket_bridge.notify_agent_error.call_args}')
    except Exception as e:
        print(f'Execution exception: {e}')

asyncio.run(test_timeout_behavior())
"
```

## Expected Test Outcomes

### Phase 1: Failing Test Analysis
- **Current State:** `notify_agent_error.assert_called()` fails
- **Expected Fix:** After implementing WebSocket notification in timeout paths, assertion should pass
- **Success Criteria:** Test passes completely with timeout detection AND WebSocket notification

### Phase 2: Broader Validation
- **Agent Death Test:** Should continue to pass with `notify_agent_error` called
- **General Exception Test:** Should continue to pass with `notify_agent_error` called  
- **WebSocket Bridge Test:** Should continue to pass with all WebSocket events
- **Metrics Collection Test:** Should continue to pass with execution tracking

### Phase 3: Infrastructure Validation
- **Mock Behavior:** Verify AsyncMock correctly tracks async method calls
- **Timeout Simulation:** Verify asyncio timeout mechanism works as expected
- **Test Isolation:** Verify test setup provides proper isolation without external dependencies

### Phase 4: Behavior Documentation
- **Current Behavior:** Document exact timeout execution path and WebSocket notification gaps
- **Missing Notifications:** Identify all scenarios where `notify_agent_error` should be called but isn't
- **State Tracking:** Verify `agent_tracker.transition_state` calls are working correctly

## Test Commands Summary

### Critical Test Execution
```bash
# 1. Run the specific failing test
python3 -m pytest netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_timeout_protection_prevents_hung_agents -v -s --tb=short

# 2. Run full agent execution core test suite
python3 -m pytest netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py -v --tb=short

# 3. Run all timeout-related tests
python3 -m pytest netra_backend/tests/unit/agents/supervisor/ -k "timeout" -v --tb=short

# 4. Run all WebSocket-related tests  
python3 -m pytest netra_backend/tests/unit/agents/supervisor/ -k "websocket" -v --tb=short

# 5. Run all agent execution core related tests
python3 -m pytest netra_backend/tests/unit/agents/supervisor/ -v --tb=short
```

### Validation Commands
```bash
# Test mock infrastructure
python3 -c "from unittest.mock import AsyncMock; import asyncio; bridge = AsyncMock(); print('Mock setup test:', bridge.notify_agent_error.return_value)"

# Test timeout mechanism
python3 -c "import asyncio; async def test(): await asyncio.wait_for(asyncio.sleep(1), timeout=0.1); asyncio.run(test())" 2>/dev/null || echo "Timeout test: PASS"

# Test current AgentExecutionCore behavior (requires implementing test script above)
```

## Success Criteria

### Test Passing Criteria
1. **Timeout Detection:** `result.success` is `False` and contains timeout error message
2. **WebSocket Notification:** `notify_agent_error.assert_called()` passes
3. **Duration Validation:** Test completes quickly (< 1.0s) confirming timeout was enforced
4. **Error Context:** Timeout error message includes relevant user and execution context
5. **State Tracking:** `agent_tracker.transition_state` called with TIMEOUT phase

### Regression Prevention
1. **Existing Tests:** All other agent execution tests continue to pass
2. **WebSocket Pattern:** Other WebSocket notification patterns remain consistent
3. **Error Handling:** General exception error notifications continue to work
4. **Performance:** Test execution time remains under acceptable limits

### Business Value Protection
1. **User Experience:** Timeout scenarios provide clear WebSocket error feedback
2. **System Reliability:** Timeout protection prevents hung agent processes
3. **Observability:** Proper error notification enables user feedback and support
4. **$500K+ ARR Protection:** Chat functionality gracefully handles timeout scenarios

## Implementation Guidance

### Required Fix Location
**File:** `netra_backend/app/agents/supervisor/agent_execution_core.py`

**TimeoutError Path (line 605-636):** Add `notify_agent_error` call after state transition:
```python
except TimeoutError as e:
    # ... existing timeout logging ...
    
    # Transition to timeout phase  
    await self.agent_tracker.transition_state(...)
    
    # MISSING: Add WebSocket error notification
    if self.websocket_bridge:
        await self.websocket_bridge.notify_agent_error(
            run_id=context.run_id,
            agent_name=context.agent_name,
            error=str(e)
        )
    
    # ... existing result creation ...
```

**asyncio.TimeoutError Path (line 826-843):** Add `notify_agent_error` call in `_execute_with_protection`:
```python  
except asyncio.TimeoutError:
    # ... existing timeout logging ...
    
    # MISSING: Add WebSocket error notification
    if self.websocket_bridge:
        await self.websocket_bridge.notify_agent_error(
            context.run_id,
            context.agent_name, 
            f"Agent '{context.agent_name}' execution timeout after {timeout_seconds}s"
        )
    
    # ... existing result creation ...
```

This TEST PLAN provides comprehensive validation of Issue #1025 timeout protection WebSocket notification requirements while following CLAUDE.md testing principles and protecting business value.