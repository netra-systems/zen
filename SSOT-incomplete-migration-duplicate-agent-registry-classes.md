# SSOT-incomplete-migration-duplicate-agent-registry-classes

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/845  
**Priority:** P0 (Critical/Blocking)  
**Focus Area:** agents  
**Status:** Discovery Complete - Moving to Testing Phase

## Problem Summary

**CRITICAL SSOT VIOLATION:** Two different `AgentRegistry` classes exist causing import conflicts and WebSocket failures that BLOCK the Golden Path (users login → get AI responses).

## Files Involved

### 1. Basic Registry (TO BE ELIMINATED)
- **File:** `/netra_backend/app/agents/registry.py:81`
- **Size:** 419 lines  
- **Description:** Basic agent registry with simple features
- **Created:** Issue #485 fix but conflicts with main implementation

### 2. Advanced Registry (SSOT CANDIDATE)  
- **File:** `/netra_backend/app/agents/supervisor/agent_registry.py:383`
- **Size:** 1,817 lines
- **Description:** Hardened implementation with user isolation and WebSocket integration
- **Status:** Main production registry, should become SSOT

### 3. Supporting Infrastructure (CORRECT)
- **File:** `/netra_backend/app/agents/supervisor/agent_class_registry.py:56` 
- **Size:** 402 lines
- **Description:** Infrastructure-only agent class storage (correctly implemented)

## Business Impact Assessment

- **Revenue Risk:** $500K+ ARR chat functionality compromised
- **Golden Path Status:** BLOCKED - Users cannot get AI responses  
- **Critical Events Affected:** All 5 WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- **System Stability:** Import conflicts causing runtime failures

## SSOT Violation Details

```python
# VIOLATION: Same class name, different implementations
# File 1: /netra_backend/app/agents/registry.py:81
class AgentRegistry:
    """Central registry for managing AI agents."""
    # 419 lines of basic implementation

# File 2: /netra_backend/app/agents/supervisor/agent_registry.py:383  
class AgentRegistry(BaseAgentRegistry):
    """ENHANCED Agent Registry with mandatory user isolation patterns."""
    # 1,817 lines of advanced implementation
```

## Process Status

### ✅ Step 0: Discovery Complete
- [x] SSOT violation identified and documented
- [x] GitHub issue created (#845)
- [x] Business impact assessed
- [x] Priority assigned (P0)
- [x] Progress tracker created

### 🔄 Step 1: Discover and Plan Test (NEXT)
- [ ] Find existing tests protecting agent registry functionality
- [ ] Plan new tests for SSOT consolidation validation
- [ ] Document test strategy in this file
- [ ] Update GitHub issue with test plan

### ⏸️ Step 2: Execute Test Plan (PENDING)
### ⏸️ Step 3: Plan Remediation (PENDING)  
### ⏸️ Step 4: Execute Remediation (PENDING)
### ⏸️ Step 5: Test Fix Loop (PENDING)
### ⏸️ Step 6: PR and Closure (PENDING)

## Remediation Strategy (PLANNED)

### Phase 1: Registry Consolidation (P0 - IMMEDIATE)
1. Choose advanced supervisor/agent_registry.py as SSOT
2. Eliminate or rename basic agents/registry.py
3. Fix all imports to use single registry source  
4. Ensure consistent interface across all consumers

### Phase 2: WebSocket Bridge Stabilization (P0 - IMMEDIATE)
1. Consolidate WebSocket bridge patterns to single interface
2. Fix mixed direct/adapter assignment patterns
3. Validate all 5 critical events work properly

### Phase 3: Factory Pattern Enforcement (P1 - HIGH)
1. Eliminate singleton violations and global instances
2. Enforce factory pattern for all agent creation
3. Complete user context isolation implementation

## Testing Requirements

### Existing Tests to Validate
- [ ] Agent registration and initialization tests
- [ ] WebSocket event delivery tests  
- [ ] User context isolation tests
- [ ] Import resolution tests

### New Tests Needed
- [ ] Registry consolidation validation test
- [ ] Interface consistency test
- [ ] Golden Path end-to-end test (login → AI responses)
- [ ] WebSocket bridge stability test

## Success Criteria

- [x] Critical SSOT violation identified and documented
- [ ] All existing agent tests pass after consolidation
- [ ] New SSOT validation tests created and passing
- [ ] Golden Path restored (users can login → get AI responses)
- [ ] All 5 WebSocket events delivered properly
- [ ] No import conflicts or namespace collisions
- [ ] User context isolation maintained
- [ ] Business functionality fully restored

---

**Next Action:** Spawn sub-agent for Step 1 - Discover and Plan Test