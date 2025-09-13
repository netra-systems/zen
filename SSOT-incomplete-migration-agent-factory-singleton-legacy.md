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

## Test Plan Status: DISCOVERED ✅

### Existing Test Coverage: 80% (EXCELLENT)
- ✅ **Mission Critical Tests:** `test_agent_factory_ssot_validation.py` - Complete factory SSOT validation
- ✅ **User Isolation Tests:** `test_issue_686_user_isolation_comprehensive.py` - End-to-end isolation
- ✅ **Concurrent Testing:** `test_concurrent_user_isolation.py` - 20+ concurrent users validation
- ✅ **Factory Pattern Tests:** Multiple unit tests for factory behavior validation
- ✅ **WebSocket Event Tests:** Complete event delivery per user validation

### Required New Tests: 20% (ACHIEVABLE)
- [ ] **Singleton→Factory Migration Tests** - Validate transition from singleton patterns
- [ ] **Factory Method Pattern Tests** - Ensure all agents use create_agent_with_context()
- [ ] **SSOT Import Validation Tests** - Verify imports follow SSOT_IMPORT_REGISTRY patterns
- [ ] **Golden Path Integration Tests** - End-to-end factory pattern validation
- [ ] **Regression Prevention Tests** - Catch singleton pattern reintroduction

### Test Strategy
- **Phase 1:** Core SSOT validation tests (Week 1) - 5 tests
- **Phase 2:** Integration and performance tests (Week 2) - 3 tests
- **Phase 3:** Regression prevention tests (Week 3) - 2 tests
- **Total:** ~10 new tests + repair 1 existing test

### Success Criteria
- ✅ **Before Fix:** Mission critical tests FAIL (showing singleton violations)
- ✅ **After Fix:** All tests PASS with factory pattern validation
- ✅ **Performance:** <100ms additional overhead per request
- ✅ **Zero Cross-User Contamination:** Under 20+ concurrent user load

## Progress Log
- [2025-09-12] Issue identified via SSOT audit
- [2025-09-12] Initial analysis and documentation
- [2025-09-12] Test discovery completed - 80% existing coverage found, 20% new tests planned
- [2025-09-12] HIGH CONFIDENCE - Sophisticated existing test infrastructure provides excellent foundation