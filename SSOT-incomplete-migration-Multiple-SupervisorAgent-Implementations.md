# SSOT-incomplete-migration-Multiple-SupervisorAgent-Implementations

**GitHub Issue:** [#821](https://github.com/netra-systems/netra-apex/issues/821)
**Priority:** P0 - Critical
**Created:** 2025-09-13
**Status:** DISCOVERY PHASE

## Problem Summary
**3 different SupervisorAgent implementations** exist, violating SSOT principles and blocking Golden Path (users login → AI responses).

## Locations Identified
1. `/netra_backend/app/agents/supervisor_ssot.py:45` - ✅ **SSOT SupervisorAgent** (should be the only one)
2. `/backups/supervisor_migration_issue_800/supervisor_consolidated.py:49` - ⚠️ **Legacy SupervisorAgent** (should be removed)
3. Additional implementations referenced in tests (to be identified)

## Business Impact
- **$500K+ ARR at risk** - Users cannot get AI responses
- WebSocket events not properly routed
- Multi-user isolation failures
- Agent coordination breakdowns

## Process Status
- [x] **STEP 0:** SSOT Issue Discovery - COMPLETE
  - [x] Audit completed by sub-agent
  - [x] GitHub issue #821 created
  - [x] Local progress file created
- [ ] **STEP 1:** Discover and Plan Test
- [ ] **STEP 2:** Execute Test Plan (20% new SSOT tests)
- [ ] **STEP 3:** Plan Remediation
- [ ] **STEP 4:** Execute Remediation
- [ ] **STEP 5:** Test Fix Loop
- [ ] **STEP 6:** PR and Closure

## Detailed Findings

### SupervisorAgent SSOT Violations
- **SSOT Path:** `/netra_backend/app/agents/supervisor_ssot.py` (should be canonical)
- **Legacy Path:** `/backups/supervisor_migration_issue_800/supervisor_consolidated.py`
- **Import Confusion:** Different parts of system may import different implementations

### Related SSOT Issues Discovered
- **4 different AgentRegistry implementations** (secondary P0 issue)
- **Dual WebSocket interfaces** causing adapter complexity (P1 issue)
- **15+ agent factory patterns** (P2 issue)

## Next Actions
1. **SPAWN SUB-AGENT:** Discover existing tests protecting SupervisorAgent functionality
2. **PLAN TESTS:** Create failing tests that reproduce SSOT violations
3. **REMEDIATE:** Consolidate to single SupervisorAgent SSOT implementation
4. **VALIDATE:** Ensure Golden Path: users login → receive AI responses works

## Success Criteria
- [ ] Only ONE SupervisorAgent implementation active system-wide
- [ ] All imports use SSOT path `/netra_backend/app/agents/supervisor_ssot.py`
- [ ] Golden Path validation passes: users login → receive AI responses
- [ ] All existing tests continue to pass
- [ ] WebSocket events properly route through unified supervisor

## Test Plan (TBD in Step 1)
- Existing tests protecting SupervisorAgent: TBD
- New SSOT violation reproduction tests: TBD
- Golden Path integration tests: TBD

## Notes
- This is the **most critical** SSOT violation blocking Golden Path
- Part of larger agent SSOT consolidation effort
- Must maintain backwards compatibility during migration