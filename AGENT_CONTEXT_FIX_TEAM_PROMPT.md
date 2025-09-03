# CRITICAL: Agent Execution Context Propagation Fix
## Multi-Agent Team Mission

**SEVERITY: HIGH**
**IMPACT: Agent cascade failures, broken dependency chains, incomplete workflows**
**TIMELINE: Fix after WebSocket and ClickHouse issues resolved**

## Team Composition

### 1. Dependency Resolution Agent
**Mission:** Fix agent dependency validation and injection
**Context:** Agents failing with "Missing required dependencies: ['plan']"
**Deliverables:**
- Audit agent dependency declarations
- Fix dependency validation logic
- Implement dependency auto-resolution

### 2. Context Propagation Agent
**Mission:** Ensure execution context flows through agent hierarchy
**Context:** Child agents losing parent context, WebSocket manager not propagating
**Deliverables:**
- Fix context inheritance in supervisor
- Ensure WebSocket manager propagates to all agents
- Implement context validation at each level

### 3. State Management Agent
**Mission:** Fix agent state transitions and result passing
**Context:** Agent results not properly captured or passed to dependent agents
**Deliverables:**
- Fix result extraction from agent responses
- Ensure state persistence across retries
- Implement result validation

### 4. Error Recovery Agent
**Mission:** Implement graceful degradation and recovery
**Context:** Single agent failure causes entire workflow to fail
**Deliverables:**
- Implement partial success handling
- Add retry logic with exponential backoff
- Create fallback strategies for critical agents

## Critical Files to Investigate

```
netra_backend/app/agents/supervisor/agent_execution_core.py - Execution orchestration
netra_backend/app/agents/supervisor/execution_context.py - Context management
netra_backend/app/agents/supervisor_consolidated.py - Main supervisor logic
netra_backend/app/agents/base_agent.py - Base agent implementation
netra_backend/app/core/execution_tracker.py - Execution state tracking
```

## Root Cause Analysis

1. **Dependency Issues:**
   - Hardcoded dependency names don't match actual agent outputs
   - No validation of dependency availability before execution
   - Missing dependency injection framework

2. **Context Loss:**
   - WebSocket manager not passed to child agents
   - User context not maintained through execution chain
   - Thread context lost during async operations

3. **State Problems:**
   - Agent results stored in wrong format
   - State not persisted between retries
   - No transaction rollback on partial failure

## Test Requirements

1. **Unit Tests:**
   - Test dependency resolution with missing deps
   - Test context propagation through 3+ levels
   - Test state recovery after failure

2. **Integration Tests:**
   - Multi-agent workflow with dependencies
   - Context preservation across async boundaries
   - Partial failure recovery scenarios

3. **Stress Tests:**
   - 10+ concurrent agent executions
   - Deep nesting (5+ levels) of agents
   - Random failure injection

## Implementation Strategy

### Phase 1: Stabilization
```python
# Fix immediate breaks
- Add null checks for dependencies
- Implement context cloning
- Add comprehensive logging
```

### Phase 2: Robustness
```python
# Add resilience
- Implement retry logic
- Add circuit breakers per agent
- Create dependency graph validation
```

### Phase 3: Optimization
```python
# Improve performance
- Cache agent results
- Parallelize independent agents
- Implement lazy dependency resolution
```

## Success Criteria

- [ ] Zero dependency validation errors
- [ ] Context available at all execution levels
- [ ] 95% agent execution success rate
- [ ] Graceful degradation on partial failure
- [ ] Complete execution traces available

## Coordination Protocol

1. Dependency Agent maps ALL agent dependencies
2. Context Agent fixes propagation paths
3. State Agent implements persistence
4. Error Recovery Agent adds resilience
5. All agents validate with workflow tests

## Critical Validation

```python
# Test multi-agent workflow
def test_complex_workflow():
    # Setup
    supervisor = SupervisorAgent()
    context = ExecutionContext(
        user_id="test",
        websocket_manager=mock_ws,
        dependencies={}
    )
    
    # Execute
    result = supervisor.execute_workflow(
        agents=["research", "planning", "optimization"],
        context=context
    )
    
    # Validate
    assert all(agent.completed for agent in result.agents)
    assert context.websocket_manager is not None
    assert len(result.errors) == 0
```

## Monitoring Requirements

- Add metrics for dependency resolution time
- Track context propagation depth
- Monitor agent failure rates by type
- Alert on cascade failure patterns