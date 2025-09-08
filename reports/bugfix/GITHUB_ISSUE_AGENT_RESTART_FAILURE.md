# GitHub Issue: Critical - Agent Restart Failure After Initial Error

## Issue Title
🚨 CRITICAL: Agent Singleton Pattern Causes System-Wide Failures - Requests Not Isolated

## Labels
- `bug`
- `critical`
- `production-blocker`
- `architecture`
- `isolation`

## Issue Description

### Problem Summary
The chat application suffers from a critical architectural flaw where agent failures cascade across ALL users. Once an agent (especially triage) fails for one request, it doesn't restart properly for subsequent requests, getting stuck on "triage start" indefinitely. This affects the entire system's reliability.

### Business Impact
- **Severity**: CRITICAL - System-wide outage from single failure
- **Users Affected**: ALL users when any agent fails
- **Revenue Impact**: Complete service disruption
- **Customer Experience**: Chat becomes completely unresponsive

### Root Cause (5 Whys Analysis)
1. **Why don't agents restart after failure?** → Singleton pattern persists error state
2. **Why does singleton pattern cause this?** → Same instance reused for ALL requests
3. **Why does error state persist?** → No cleanup mechanism between requests
4. **Why no fresh instances per request?** → Incomplete migration to factory pattern
5. **Why incomplete migration?** → System in transition, backward compatibility maintained

### Current Behavior (BROKEN)
```
User 1 Request → Singleton Agent → FAILURE
User 2 Request → Same Agent (corrupted) → STUCK
User 3 Request → Same Agent (corrupted) → STUCK
All subsequent requests → BLOCKED
```

### Expected Behavior (ISOLATED)
```
User 1 Request → Fresh Agent Instance → May fail
User 2 Request → New Agent Instance → Works normally
User 3 Request → New Agent Instance → Works normally
Each request independent → No cascade failures
```

## Technical Details

### Affected Components
- `netra_backend/app/agents/supervisor/agent_registry.py` - Singleton storage
- `netra_backend/app/agents/base_agent.py` - Missing reset mechanism
- `netra_backend/app/orchestration/agent_execution_registry.py` - Singleton pattern
- All agent subclasses inheriting from BaseAgent

### Architecture Issues
1. **Singleton Agent Instances**: Created once, reused forever
2. **No State Cleanup**: Error states persist across requests
3. **Shared WebSocket State**: Events leak between users
4. **Database Session Sharing**: Potential connection pool exhaustion
5. **No Request Isolation**: One failure affects entire system

## Solution Implementation

### Phase 1: Immediate Mitigation (COMPLETED ✅)
- [x] Implement `reset_state()` method in BaseAgent
- [x] Update AgentRegistry to call reset before returning agents
- [x] Add comprehensive state cleanup logic

### Phase 2: Factory Pattern Migration (IN PROGRESS 🔄)
- [x] Verify AgentInstanceFactory implementation
- [ ] Migrate all agent creation to use factory
- [ ] Remove singleton storage from registry
- [ ] Implement proper resource cleanup

### Phase 3: Complete Isolation (PENDING ⏳)
- [ ] WebSocket isolation per connection
- [ ] Database session isolation verification
- [ ] Comprehensive integration testing
- [ ] Production deployment

## Related Documentation

### Analysis & Design Docs
- **Root Cause Analysis**: [`AGENT_RESTART_FAILURE_BUG_FIX_20250904.md`](./AGENT_RESTART_FAILURE_BUG_FIX_20250904.md)
- **Isolation Architecture**: [`CRITICAL_REQUEST_ISOLATION_ARCHITECTURE.md`](./CRITICAL_REQUEST_ISOLATION_ARCHITECTURE.md)
- **Implementation Summary**: [`AGENT_ERROR_FIX_SUMMARY_20250904.md`](./AGENT_ERROR_FIX_SUMMARY_20250904.md)

### Test Coverage
- **Reproduction Test**: `tests/mission_critical/test_agent_restart_after_failure.py`
- **Isolation Test Suite**: `tests/mission_critical/test_complete_request_isolation.py`

### Code Changes
- **BaseAgent Reset**: `netra_backend/app/agents/base_agent.py` (lines 511-657)
- **Registry Updates**: `netra_backend/app/agents/supervisor/agent_registry.py` (async get_agent method)

## Acceptance Criteria

### Must Have (Non-Negotiable)
- [ ] Agent failures don't affect other requests
- [ ] Each request gets fresh agent instance
- [ ] No state leakage between users
- [ ] WebSocket events properly isolated
- [ ] Database sessions request-scoped
- [ ] All tests pass in `test_complete_request_isolation.py`

### Performance Requirements
- [ ] < 10ms overhead for instance creation
- [ ] < 5ms for state reset operation
- [ ] Support 100+ concurrent isolated requests

## Testing Plan

### Unit Tests
```python
# Test agent isolation
async def test_agent_instance_isolation()
async def test_failure_isolation()
async def test_websocket_isolation()
```

### Integration Tests
```python
# Test system under load
async def test_concurrent_load_with_failures()
async def test_context_cleanup_after_request()
```

### Manual Testing
1. Start system with monitoring
2. Force agent failure for one user
3. Verify other users unaffected
4. Check resource cleanup
5. Monitor for memory leaks

## Definition of Done

- [x] Root cause identified and documented
- [x] BaseAgent reset_state() implemented
- [x] AgentRegistry updated with reset logic
- [ ] All agent creation uses factory pattern
- [ ] Zero singleton agents in production
- [ ] All isolation tests passing
- [ ] Load tested with 100+ concurrent users
- [ ] Deployed to staging and validated
- [ ] Production deployment complete
- [ ] Monitoring confirms isolation metrics

## Risk Assessment

### High Risk
- Current singleton pattern affects ALL users
- One failure can bring down entire chat system
- No workaround available for users

### Mitigation
- Phase 1 provides immediate relief
- Factory pattern ensures long-term stability
- Gradual rollout with feature flags

## Timeline

- **Phase 1**: ✅ Complete (4 hours)
- **Phase 2**: 🔄 In Progress (8 hours remaining)
- **Phase 3**: ⏳ Pending (6 hours)
- **Total**: ~18 hours to full resolution

## Dependencies

- No external dependencies
- Requires coordination with DevOps for deployment
- May need database connection pool adjustment

## Monitoring & Alerts

### Key Metrics
- Request isolation score (target: 100%)
- Failure containment rate (target: 100%)
- Agent instance creation time (target: <10ms)
- Resource leak detection (target: 0)

### Alert Conditions
- CRITICAL: Cross-request state leakage detected
- WARNING: Agent reset taking >5s
- ERROR: Singleton instance reused

## References

- Original bug report: Chat gets stuck on "triage start"
- Architecture docs: `docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md`
- Factory pattern: `netra_backend/app/agents/supervisor/agent_instance_factory.py`

## Updates Log

### 2025-09-04
- Initial issue creation
- Phase 1 implementation completed
- Comprehensive documentation added

---

**Priority**: P0 - CRITICAL
**Assignee**: Engineering Team
**Sprint**: Current
**Epic**: System Reliability

## How to Reproduce

1. Start the application
2. Send a request that causes agent failure (e.g., database error)
3. Send another request from different user
4. Observe: Second request gets stuck on "triage start"
5. All subsequent requests fail similarly

## Resolution Verification

After fix deployment:
1. Repeat reproduction steps
2. Verify second request succeeds despite first failure
3. Run isolation test suite
4. Monitor production metrics for 24 hours

---

**Note**: This is a CRITICAL production issue affecting system reliability. Each request MUST be completely isolated with ZERO impact from other request failures.