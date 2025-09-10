# SSOT-incomplete-migration-multiple-agent-health-monitors

**GitHub Issue:** #211 - https://github.com/netra-systems/netra-apex/issues/211  
**Status:** Discovery Phase  
**Priority:** Critical - Blocking Golden Path

## Problem Summary

Multiple AgentHealthMonitor implementations violate SSOT principles and block golden path chat functionality. Users experiencing inconsistent AI response delivery due to fragmented health monitoring.

## Critical SSOT Violations Identified

### Violation #1: Multiple Health Monitoring Implementations (CRITICAL)
- **Files:**
  - `/netra_backend/app/core/agent_health_monitor.py` (283 lines - Core SSOT candidate)
  - `/dev_launcher/health_monitor.py` (700 lines - Development infrastructure)
  - `/dev_launcher/enhanced_health_monitor.py` (686 lines - Enhanced version)
- **Impact:** Inconsistent agent death detection, fragmented monitoring logic
- **Golden Path Impact:** Silent agent failures, inconsistent WebSocket events

### Violation #2: Scattered Agent Status Tracking (HIGH)
- **Files:**
  - `/netra_backend/app/agents/supervisor/agent_registry.py` (AgentLifecycleManager)
  - `/netra_backend/app/core/agent_execution_tracker.py` (ExecutionRecord)
  - `/netra_backend/app/core/agent_health_monitor.py` (Health status)
- **Impact:** Race conditions, no single source for "is agent alive?"

### Violation #3: WebSocket Health Monitoring Fragmentation (HIGH)
- **Impact:** Users experience WebSocket disconnects without agent health recovery

## Remediation Strategy

### Phase 1: SSOT Core Health Monitor (PRIORITY 1)
- Designate `/netra_backend/app/core/agent_health_monitor.py` as SSOT
- Consolidate logic from dev_launcher modules
- Standardize death detection thresholds

### Phase 2: Unified Agent State Tracking (PRIORITY 2)  
- Centralize health state in AgentHealthMonitor
- Refactor AgentRegistry delegation
- Eliminate duplicate tracking

### Phase 3: WebSocket-Agent Health Integration (PRIORITY 3)
- Create unified chat experience health assessment
- Integrate WebSocket + agent health status

## Progress Tracking

- [x] Step 0: SSOT Audit Complete
- [x] GitHub Issue Created (#211)  
- [x] IND File Created
- [x] Step 1: Test Discovery and Planning Complete
- [x] Step 2: Execute Test Plan Complete ✅
- [ ] Step 3: Plan SSOT Remediation (IN PROGRESS)
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Step 1: Test Discovery Results ✅

### Existing Tests Inventory
**Critical Finding:** Multiple broken health monitoring tests requiring repair before reliable validation:

**Core Health Monitoring Tests:**
- `/netra_backend/tests/integration/test_agent_health_monitor.py` - Basic health monitoring
- `/tests/mission_critical/test_agent_lifecycle.py` - Agent lifecycle management
- `/tests/integration/test_websocket_agent_integration.py` - WebSocket health integration

**Fragmented Test Coverage:**
- Agent death detection spread across 3+ test modules
- Inconsistent timeout threshold testing (10s vs 30s vs 60s)
- WebSocket health monitoring tested separately from agent health

### Test Plan Strategy (Phase-Based Approach)

#### Phase 1: SSOT Violation Reproduction Tests (SHOULD FAIL)
1. **Multi-Implementation Inconsistency Test** - Expose different death detection thresholds
2. **Race Condition Reproduction Test** - Show scattered agent status conflicts
3. **WebSocket Health Fragmentation Test** - Demonstrate disconnected monitoring systems

#### Phase 2: SSOT Validation Tests (SHOULD PASS AFTER FIX)
1. **Unified Health Interface Test** - Validate single health monitoring entry point
2. **Consistent Death Detection Test** - Verify standardized timeout thresholds
3. **Integrated WebSocket-Agent Health Test** - Test coordinated health assessment

#### Phase 3: Golden Path Protection Tests
1. **End-to-End Health Monitoring Test** - Validate complete user journey health
2. **Performance Impact Test** - Ensure <50ms health checking overhead
3. **Failure Recovery Test** - Test graceful degradation scenarios

### Risk Assessment
- **High Risk:** Multiple health monitors could conflict during migration
- **Medium Risk:** WebSocket health integration might break during consolidation
- **Low Risk:** Performance impact from centralized health checking

### Execution Strategy
1. Create reproduction tests first (validate they fail)
2. Implement SSOT health monitor
3. Run validation tests (ensure they pass)
4. Update existing tests for SSOT compliance

## Next Actions

1. Execute Step 2: Create new SSOT validation tests (20% focus)
2. Focus on reproduction tests that expose current violations
3. Prepare test framework for SSOT remediation validation

## Business Value Justification

- **Segment:** Platform (affects all user tiers)
- **Business Goal:** Stability - ensure reliable AI response delivery  
- **Value Impact:** Consistent agent health monitoring enables 90% of chat functionality value
- **Revenue Impact:** Prevents user churn from unreliable chat experience

---
*Generated by SSOT Gardener - Agent Health Monitor Focus*