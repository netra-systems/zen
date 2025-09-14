# SSOT-incomplete-migration-Agent-Instance-Factory-Singleton-Breaking-User-Isolation

**GitHub Issue:** [#1102](https://github.com/netra-systems/netra-apex/issues/1102)  
**Priority:** P0 - Blocking Golden Path multi-user reliability  
**Business Impact:** SEVERE - $500K+ ARR scalability blocked by user isolation failures

## Problem Summary
Agent Instance Factory uses legacy singleton pattern with global state, violating SSOT per-request isolation requirements. This causes user context contamination between concurrent requests.

## Critical Files Identified
1. `/netra_backend/app/agents/supervisor/agent_instance_factory.py:1128` - Primary violation
2. `/netra_backend/app/services/thread_run_registry.py:83` - Similar pattern
3. `/netra_backend/app/websocket_core/websocket_manager_factory.py:83` - Similar pattern
4. `/netra_backend/app/agents/supervisor/execution_engine_factory.py:613` - Similar pattern

## Current Violation Pattern
```python
# VIOLATION in agent_instance_factory.py:1128
_factory_instance: Optional[AgentInstanceFactory] = None

def get_agent_instance_factory() -> AgentInstanceFactory:
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = AgentInstanceFactory()
    return _factory_instance
```

## Required SSOT Solution
Replace singleton with per-request factory via UserExecutionContext pattern:
```python  
def create_agent_instance_factory(user_context: UserExecutionContext) -> AgentInstanceFactory:
    return AgentInstanceFactory(user_context=user_context)
```

## Progress Tracking

### Step 1: Test Discovery (PENDING)
- [ ] Find existing tests protecting agent factory functionality
- [ ] Identify multi-user isolation test gaps
- [ ] Plan new SSOT validation tests

### Step 2: Test Planning (PENDING)
- [ ] Plan unit tests for per-request factory pattern
- [ ] Plan integration tests for user isolation
- [ ] Plan concurrent user scenario tests

### Step 3: Test Implementation (PENDING)
- [ ] Create failing tests reproducing singleton violation
- [ ] Implement SSOT compliance validation tests
- [ ] Test multi-user concurrent access scenarios

### Step 4: Remediation Planning (PENDING)
- [ ] Plan singleton removal from AgentInstanceFactory
- [ ] Plan UserExecutionContext integration
- [ ] Plan backward compatibility during migration

### Step 5: Remediation Execution (PENDING)
- [ ] Implement per-request factory pattern
- [ ] Remove global singleton state
- [ ] Update all factory consumers
- [ ] Maintain system stability

### Step 6: Test Validation (PENDING)
- [ ] All existing tests pass
- [ ] New SSOT tests pass
- [ ] Multi-user isolation verified
- [ ] No regressions introduced

### Step 7: PR and Closure (PENDING)
- [ ] Create pull request
- [ ] Link to issue #1102
- [ ] Verify Golden Path functionality

## Test Results Log
(To be updated as tests are run)

## Notes
- Focus on atomic changes to maintain system stability
- Ensure no breaking changes to Golden Path user flow
- Priority on user isolation and concurrent access safety