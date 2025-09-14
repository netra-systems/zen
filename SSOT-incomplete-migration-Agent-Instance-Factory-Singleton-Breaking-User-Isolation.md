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

### Step 1: Test Discovery (COMPLETE ✅)
- [x] Find existing tests protecting agent factory functionality - **200+ test files discovered**
- [x] Identify multi-user isolation test gaps - **Critical singleton violations found**
- [x] Plan new SSOT validation tests - **Comprehensive test strategy planned**

### Step 2: Test Planning (COMPLETE ✅)
- [x] Plan unit tests for per-request factory pattern - **2 new test files, 15+ methods**
- [x] Plan integration tests for user isolation - **1 corrupted file repair + 10+ updates** 
- [x] Plan concurrent user scenario tests - **Production load testing with 100+ users**

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

## Test Discovery Results (Step 1 Complete)

### Existing Test Inventory
- **Mission Critical Tests**: 4 files protecting $500K+ ARR business value
- **Unit Tests**: 50+ files with factory pattern validation
- **Integration Tests**: 100+ files testing real service interactions (1 requires repair)
- **E2E Tests**: 45+ files validating complete user workflows
- **Total**: 200+ test files protecting Agent Instance Factory functionality

### Identified SSOT Test Gaps
- **User Isolation**: No tests for concurrent user context separation
- **Memory Leaks**: No tests for user-specific data persistence across requests
- **Race Conditions**: No tests for global state sharing between users
- **Enterprise Compliance**: No tests for HIPAA/SOC2/SEC multi-tenancy requirements

### Planned Test Strategy
1. **Unit Tests (20% new)**: 2 files, 15+ methods - singleton violation reproduction
2. **Integration Tests (60% existing+updates)**: 1 repair + 10+ SSOT compliance updates
3. **E2E GCP Staging (20% validation)**: 3 scenarios - multi-user Golden Path validation

## Test Results Log
(To be updated as tests are run)

## Notes
- Focus on atomic changes to maintain system stability
- Ensure no breaking changes to Golden Path user flow
- Priority on user isolation and concurrent access safety