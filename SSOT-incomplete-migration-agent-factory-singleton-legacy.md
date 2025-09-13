# SSOT-incomplete-migration-agent-factory-singleton-legacy

## Issue Status: CREATED
**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/709
**Priority:** P0 CRITICAL
**Impact:** Blocks Golden Path - User login → AI responses

## Problem Description
Legacy singleton patterns remain in agent factory system despite factory pattern implementation, causing:
- Cross-user state contamination
- WebSocket event delivery failures
- Race conditions in multi-user scenarios
- $500K+ ARR revenue risk from chat functionality failures

## Evidence
**Files Affected:**
- `netra_backend/app/agents/supervisor/agent_instance_factory.py` - Global singleton pattern
- `netra_backend/app/agents/supervisor/execution_engine_factory.py` - Deprecation warnings

**Code Examples:**
```python
# LEGACY SINGLETON PATTERN STILL PRESENT
_factory_instance: Optional[AgentInstanceFactory] = None

def get_agent_instance_factory() -> AgentInstanceFactory:
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = AgentInstanceFactory()
    return _factory_instance
```

## Business Impact
- **Revenue Risk:** $500K+ ARR from chat functionality
- **Golden Path Blocker:** Users cannot get AI responses if agent instantiation fails
- **User Isolation Failures:** Cross-user state contamination
- **Race Conditions:** Global state causes WebSocket event delivery failures

## Planned Remediation
1. Complete migration from singleton to proper factory pattern
2. Remove global state variables
3. Implement proper user context isolation
4. Update tests to validate user isolation
5. Remove deprecation warnings

## Test Plan
- [ ] Discover existing tests protecting agent factory functionality
- [ ] Create tests for user isolation validation
- [ ] Create tests reproducing singleton contamination issues
- [ ] Validate WebSocket event delivery per user

## Progress Log
- [2025-09-12] Issue identified via SSOT audit
- [2025-09-12] Initial analysis and documentation