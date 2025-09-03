# CRITICAL: SSOT Violation Remediation - Multi-Agent Parallel Execution
## Mission: Eliminate ALL Single Source of Truth Violations

**SEVERITY: CRITICAL**
**IMPACT: System coherence, maintenance burden, data integrity**
**TIMELINE: Immediate - technical debt is actively accumulating**

## MANDATORY CONTEXT FOR ALL AGENTS

You are part of a specialized team fixing SSOT violations in the Netra Apex platform. The codebase has **20-30 active SSOT violations** causing WebSocket failures, data inconsistencies, and maintenance nightmares.

**CRITICAL REQUIREMENTS:**
1. **ULTRA THINK DEEPLY** - Our spacecraft depends on this working
2. **Five Whys Analysis** - Understand root causes before fixing
3. **Cross-System Impact Analysis** - Every change affects multiple systems
4. **Test MULTIPLE Times** - Run tests at least 3 times to ensure stability
5. **Self-Audit Continuously** - Verify your work against CLAUDE.md principles

## Team Composition and Missions

### 1. ID Consolidation Agent
**Mission:** Eliminate dual ID generation systems
**Context:** Two competing ID systems causing WebSocket routing failures

**Deliverables:**
```markdown
## ID Consolidation Report
### Current State Analysis
- IDManager format: run_{thread_id}_{uuid}
- run_id_generator format: thread_{thread_id}_run_{timestamp}_{uuid}
- Usage analysis: [List all files using each system]

### Five Whys Root Cause
1. Why two systems? [Your analysis]
2. Why implemented separately? [Your analysis]
3-5. [Continue analysis]

### Migration Plan
1. Choose canonical: IDManager (simpler, already in core/)
2. Deprecation strategy for run_id_generator
3. Migration steps with rollback plan

### Implementation
- [ ] Update all run_id_generator imports to IDManager
- [ ] Add compatibility layer for existing IDs
- [ ] Update WebSocket bridge to use single extraction
- [ ] Remove run_id_generator module

### Cross-System Impact
- WebSocket: Simplified routing logic
- Database: ID format migration needed
- Tests: Update ID expectations

### Validation (Run 3x)
- [ ] Run 1: python tests/unified_test_runner.py --category integration
- [ ] Run 2: python tests/mission_critical/test_websocket_agent_events_suite.py
- [ ] Run 3: python tests/e2e/test_complete_real_pipeline_e2e.py
```

**Critical Files:**
- `netra_backend/app/core/id_manager.py`
- `netra_backend/app/services/agent_websocket_bridge.py`
- All files importing run_id_generator

---

### 2. Supervisor Consolidation Agent
**Mission:** Merge dual supervisor implementations
**Context:** supervisor_consolidated.py vs supervisor/agent_execution_core.py

**Deliverables:**
```markdown
## Supervisor Consolidation Report
### MRO Analysis (MANDATORY)
[Use inspect.getmro() to document inheritance]
- SupervisorAgent hierarchy
- AgentExecutionCore hierarchy
- Method override mapping

### Current State
- supervisor_consolidated.py: UserExecutionContext pattern
- agent_execution_core.py: AgentExecutionContext + DeepAgentState
- Consumer analysis: [List all files using each]

### Five Whys Root Cause
[Complete 5 whys analysis]

### Consolidation Strategy
1. Target: supervisor_consolidated.py with UserExecutionContext
2. Migrate AgentExecutionCore functionality
3. Remove supervisor/ subdirectory completely

### Breaking Changes
- [ ] API changes documented
- [ ] All consumers updated
- [ ] Backward compatibility layer if needed

### Validation (Run 3x each)
- [ ] python tests/agents/test_supervisor_bulletproof.py (3x)
- [ ] python tests/integration/test_agent_pipeline_core.py (3x)
- [ ] python tests/agents/test_dependency_chain_execution.py (3x)
```

**Critical Files:**
- `netra_backend/app/agents/supervisor_consolidated.py`
- `netra_backend/app/agents/supervisor/` (entire directory for removal)

---

### 3. ClickHouse Unification Agent
**Mission:** Create single ClickHouseManager
**Context:** 8+ different ClickHouse implementations

**Deliverables:**
```markdown
## ClickHouse Unification Report
### Duplicate Analysis
Found implementations:
1. db/clickhouse.py - [Purpose]
2. db/clickhouse_initializer.py - [Purpose]
3. db/clickhouse_schema.py - [Purpose]
4. db/clickhouse_trace_writer.py - [Purpose]
5. services/clickhouse_service.py - [Purpose]
6. core/clickhouse_connection_manager.py - [Purpose]
7. factories/clickhouse_factory.py - [Purpose]
8. agents/data_sub_agent/clickhouse_operations.py - [Purpose]

### Five Whys Root Cause
[Complete analysis]

### Unification Design
```python
# Single ClickHouseManager in db/clickhouse.py
class ClickHouseManager:
    """SSOT for all ClickHouse operations"""
    def __init__(self):
        # Connection pooling
        # Circuit breaker
        # Schema management
        # Query execution
        # Trace writing
```

### Migration Steps
1. Create comprehensive ClickHouseManager
2. Add deprecation warnings to old modules
3. Update all imports systematically
4. Remove deprecated modules

### Performance Impact
- Connection pooling benefits
- Reduced memory footprint
- Simplified debugging

### Validation (Run 3x each)
- [ ] python tests/critical/test_clickhouse_fixes_comprehensive.py (3x)
- [ ] python tests/db/test_clickhouse_schema.py (3x)
- [ ] Performance: python scripts/verify_performance_metrics.py
```

**Critical Files:**
- All files in pattern `*clickhouse*.py`
- Create mega class exception if needed

---

### 4. Execution Context Agent
**Mission:** Complete UserExecutionContext migration
**Context:** Multiple execution context patterns coexist

**Deliverables:**
```markdown
## Execution Context Migration Report
### Context Proliferation Analysis
- AgentExecutionContext usage: [List files]
- UserExecutionContext usage: [List files]
- DeepAgentState usage: [List files]

### Five Whys Root Cause
[Complete analysis]

### Migration to UserExecutionContext
1. Pattern standardization
2. Data migration strategy
3. Test coverage for migration

### Removal Plan
- [ ] Remove AgentExecutionContext
- [ ] Remove DeepAgentState
- [ ] Update all imports
- [ ] Verify no context leakage

### User Isolation Verification
- Factory pattern compliance
- No shared state between users
- Thread safety guaranteed

### Validation (Run 3x each)
- [ ] python tests/critical/test_assistant_foreign_key_violation.py (3x)
- [ ] python tests/integration/test_redis_session_performance.py (3x)
- [ ] Concurrency: Run with 10 parallel users
```

---

### 5. WebSocket Simplification Agent
**Mission:** Remove adapter pattern layers
**Context:** Manager → Bridge → Adapter excessive indirection

**Deliverables:**
```markdown
## WebSocket Simplification Report
### Layer Analysis
- WebSocketManager: Core functionality
- AgentWebSocketBridge: Wraps Manager
- WebSocketBridgeAdapter: Wraps Bridge
- Unnecessary complexity identified

### Five Whys Root Cause
[Complete analysis]

### Simplification Plan
1. Direct WebSocketBridge usage
2. Remove adapter pattern
3. Consistent API across all callers

### API Consolidation
- send_message vs send_to_thread resolved
- Single method signature
- Clear documentation

### WebSocket Event Verification
CRITICAL: Must maintain all agent events:
- [ ] agent_started
- [ ] agent_thinking
- [ ] tool_executing
- [ ] tool_completed
- [ ] agent_completed

### Validation (Run 5x - CRITICAL PATH)
- [ ] python tests/mission_critical/test_websocket_agent_events_suite.py (5x)
- [ ] python tests/integration/test_websocket_thread_routing.py (3x)
- [ ] Manual: Connect frontend and verify events
```

---

### 6. Test Validation Agent
**Mission:** Ensure ALL fixes work together
**Context:** System-wide validation required

**Deliverables:**
```markdown
## System-Wide Validation Report
### Pre-Fix Baseline
- [ ] Capture current test failures
- [ ] Document current SSOT violation count
- [ ] Measure performance metrics

### Integration Test Suite
```python
def test_ssot_fixes_integrated():
    """Verify all SSOT fixes work together"""
    # 1. Test new ID system globally
    # 2. Test supervisor consolidation
    # 3. Test ClickHouse unification
    # 4. Test execution context migration
    # 5. Test WebSocket simplification
    # All must pass together
```

### Regression Prevention
- [ ] Add pre-commit hook for SSOT violations
- [ ] Update CI/CD pipeline
- [ ] Document in SPEC/learnings/

### Final Validation Checklist
Run ALL tests 3 times minimum:
- [ ] Unit tests: 100% pass (3x)
- [ ] Integration tests: 100% pass (3x)
- [ ] E2E tests: 100% pass (3x)
- [ ] Mission critical: 100% pass (5x)
- [ ] Performance: No degradation

### Compliance Verification
```bash
# Must show ZERO violations after fixes
python scripts/check_architecture_compliance.py

# Must show improved metrics
python scripts/verify_performance_metrics.py
```
```

---

## Coordination Protocol

### Phase 1: Analysis (Parallel)
All agents work simultaneously on:
1. Five Whys analysis
2. Current state documentation
3. Impact assessment
4. MRO/dependency analysis

### Phase 2: Planning (Synchronized)
1. **Dependency Check:** Identify interdependencies
2. **Conflict Resolution:** Resolve overlapping changes
3. **Migration Order:** Determine safe sequence

### Phase 3: Implementation (Coordinated)
Order of execution (some parallel possible):
1. ID Consolidation (standalone)
2. Execution Context (prerequisite for supervisor)
3. Supervisor Consolidation (depends on context)
4. ClickHouse Unification (standalone)
5. WebSocket Simplification (depends on ID)

### Phase 4: Validation (All Together)
1. Individual component tests (parallel)
2. Integration tests (sequential)
3. E2E validation (sequential)
4. Performance validation (final)

## Critical Success Factors

### 1. Architecture Compliance
```python
# Before starting work
compliance_before = check_architecture_compliance()

# After completing work
compliance_after = check_architecture_compliance()

# Must show improvement
assert compliance_after.violations < compliance_before.violations
assert compliance_after.violations == 0  # Target
```

### 2. Test Coverage
- Critical paths: 100% coverage required
- New consolidated modules: 95% minimum
- Integration tests: Cover all migrations

### 3. Performance
- No degradation allowed
- Memory usage must decrease (fewer duplicates)
- Connection count must decrease (pooling)

### 4. Documentation
- Update SPEC/learnings/ssot_consolidation_[date].xml
- Update SPEC/mega_class_exceptions.xml if needed
- Update LLM_MASTER_INDEX.md with new structure

## Emergency Protocols

### If Breaking Changes Detected
1. STOP immediately
2. Document the breaking change
3. Assess impact across all services
4. Create compatibility layer
5. Test with ALL consumers

### If Tests Fail After Fix
1. DO NOT proceed to next fix
2. Run tests individually to isolate
3. Check for race conditions
4. Verify environment variables
5. Rollback if necessary

### If Performance Degrades
1. Profile before and after
2. Check for N+1 queries
3. Verify connection pooling
4. Review circuit breaker settings
5. Consider phased rollout

## Definition of Done

### Per Agent
- [ ] Five Whys analysis complete
- [ ] Implementation complete
- [ ] All tests pass 3x minimum
- [ ] No new SSOT violations introduced
- [ ] Documentation updated
- [ ] Learnings recorded

### System-Wide
- [ ] ZERO SSOT violations remain
- [ ] All mission-critical tests pass 5x
- [ ] Performance improved or maintained
- [ ] Frontend chat works end-to-end
- [ ] No regression in any feature
- [ ] Compliance check shows 100%

## Final Validation Commands

```bash
# Run in this exact order
# 1. Clean environment
docker-compose down -v
docker-compose up -d

# 2. Run compliance check
python scripts/check_architecture_compliance.py | tee compliance_report.txt

# 3. Run all tests with real services
python tests/unified_test_runner.py --all --real-services --real-llm | tee test_report.txt

# 4. Run mission critical 5 times
for i in {1..5}; do
    echo "Run $i"
    python tests/mission_critical/test_websocket_agent_events_suite.py
done

# 5. Performance validation
python scripts/verify_performance_metrics.py | tee performance_report.txt

# 6. Manual validation
# - Connect to frontend
# - Send chat message
# - Verify agent response received
# - Check all WebSocket events in browser console
```

## Remember: ULTRA THINK DEEPLY

This is spacecraft-critical code. Every decision matters. Take time to:
1. Understand the full system impact
2. Test thoroughly and repeatedly  
3. Document everything
4. Validate assumptions
5. Ensure backward compatibility

**Ship Value, Not Bugs. Our lives depend on this working.**

---
*Mission Start: Immediately*
*Mission Critical: ALL SSOT violations must be eliminated*
*Success Metric: Zero violations, 100% test pass rate, improved performance*