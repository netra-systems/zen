# SSOT-incomplete-migration-duplicate-supervisor-agents

**GitHub Issue:** #800 - https://github.com/netra-systems/netra-apex/issues/800  
**Priority:** P0 - CRITICAL  
**Status:** DISCOVERING AND PLANNING TESTS  
**Created:** 2025-09-13

## SSOT Violation Summary

**P0 CRITICAL:** Duplicate SupervisorAgent implementations blocking Golden Path user flow (login → AI responses).

### Files in Conflict:
- ✅ **SSOT Target:** `netra_backend/app/agents/supervisor_ssot.py` (lines 45-468)
- ❌ **Legacy Remove:** `netra_backend/app/agents/supervisor_consolidated.py` (lines 49-1504)

### Critical Issues:
1. **Runtime Import Conflicts**: System uncertain which SupervisorAgent to instantiate
2. **WebSocket Event Duplication**: Both emit agent_started/agent_thinking/agent_completed 
3. **UserExecutionContext Conflicts**: Different isolation patterns
4. **Execution Engine Confusion**: Multiple orchestration approaches

## Business Impact
**$500K+ ARR at risk**: Core chat functionality unreliable when supervisor selection is non-deterministic.

## Work Progress

### ✅ Step 0: DISCOVER NEXT SSOT ISSUE (COMPLETED)
- [x] SSOT audit completed by sub-agent
- [x] Top 3 P0 violations identified
- [x] GitHub issue #800 created
- [x] Local progress tracker (IND) created

### 🔄 Step 1: DISCOVER AND PLAN TEST (IN PROGRESS)
#### 1.1 DISCOVER EXISTING TESTS
- [ ] Find tests protecting SupervisorAgent functionality
- [ ] Identify WebSocket event tests for supervisor
- [ ] Locate agent orchestration integration tests
- [ ] Check user execution context isolation tests

#### 1.2 PLAN TESTS
- [ ] Plan unit tests for SSOT SupervisorAgent
- [ ] Plan integration tests (non-docker)
- [ ] Plan e2e GCP staging tests
- [ ] Plan failing tests to reproduce SSOT violation

### ⏳ Step 2: EXECUTE TEST PLAN (PENDING)
### ⏳ Step 3: PLAN REMEDIATION (PENDING)
### ⏳ Step 4: EXECUTE REMEDIATION (PENDING)
### ⏳ Step 5: TEST FIX LOOP (PENDING)
### ⏳ Step 6: PR AND CLOSURE (PENDING)

## Immediate Remediation Plan
1. **Remove** `supervisor_consolidated.py` 
2. **Establish** `supervisor_ssot.py` as single source of truth
3. **Update** all imports to use SSOT implementation
4. **Validate** WebSocket events work correctly with unified supervisor

## Testing Requirements
- Mission critical WebSocket events suite must pass
- All supervisor-dependent tests must use SSOT implementation  
- User isolation validation required

## Notes
- System system-reminder indicated supervisor_ssot.py was recently modified (intentional)
- Focus on keeping existing functionality while eliminating duplication
- Ensure Golden Path (users login → get AI responses) remains operational