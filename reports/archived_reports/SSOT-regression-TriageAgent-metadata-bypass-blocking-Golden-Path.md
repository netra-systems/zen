# SSOT-regression-TriageAgent-metadata-bypass-blocking-Golden-Path

**GitHub Issue:** [#700](https://github.com/netra-systems/netra-apex/issues/700)
**Priority:** P0 - CRITICAL BLOCKING
**Impact:** Golden Path broken - affects $500K+ ARR chat functionality
**Type:** SSOT Regression - incomplete migration to SSOT patterns

## Problem Summary
Multiple TriageAgent sub-agents are bypassing SSOT metadata management by directly assigning to context.metadata instead of using the canonical store_metadata_result() method.

## Affected Files Identified
- `netra_backend/app/agents/optimizations_core_sub_agent.py:154` (2 direct assignments lines 154, 156)
- `netra_backend/app/agents/synthetic_data_sub_agent.py:199, 181, 183` (4 direct assignments lines 181, 182, 183, 199)
- `netra_backend/app/agents/tool_discovery_sub_agent.py`
- `netra_backend/app/agents/summary_extractor_sub_agent.py`

## Impact on Golden Path
❌ Inconsistent state management
❌ Agent coordination failures
❌ Incomplete AI responses to users
❌ Missing audit trail for metadata changes

## SSOT Violation Pattern
```python
# ❌ WRONG: Direct assignment bypassing SSOT
context.metadata['optimizations_result'] = result
context.metadata['synthetic_data_result'] = result
context.metadata['approval_message'] = approval_message
context.metadata['workload_profile'] = safe_json_dumps(profile)
```

## Expected Fix Pattern
```python
# ✅ CORRECT: SSOT method (from UnifiedTriageAgent)
self.store_metadata_result(exec_context, 'triage_result', triage_result.__dict__)
self.store_metadata_result(exec_context, 'triage_category', triage_result.category)
self.store_metadata_result(exec_context, 'data_sufficiency', triage_result.data_sufficiency)
```

## Process Status

### Step 0: ✅ COMPLETED - SSOT AUDIT
- [x] Discovered SSOT violations in TriageAgent ecosystem
- [x] Created GitHub Issue #700
- [x] Created local tracking file

### Step 1: ✅ COMPLETED - DISCOVER AND PLAN TEST
- [x] 1.1 Discover existing tests protecting against breaking changes
- [x] 1.2 Plan required test updates/creation for SSOT refactor validation

**DISCOVERY RESULTS:**
- **✅ Working Foundation:** ~4 key metadata contract tests provide solid foundation
- **❌ Broken Infrastructure:** ~2 mission critical tests have syntax errors and need rebuilding
- **✅ Integration Coverage:** ~25+ integration tests depend on proper metadata handling

**TEST STRATEGY PLANNED:**
- **~20% New Tests:** Specific SSOT compliance validation tests
- **~40% Rebuild:** Fix broken mission critical tests with syntax errors
- **~40% Validation:** Ensure existing working tests continue to pass
- **Primary Execution:** Non-Docker tests (unit, staging integration, GCP E2E)

**NEW TEST DELIVERABLE:** `test_ssot_metadata_compliance_issue_700.py`

### Step 2: 🔄 IN PROGRESS - EXECUTE TEST PLAN
- [ ] Create/update 20% new SSOT tests
- [ ] Run test validation (non-docker only)

### Step 3: ⏳ PENDING - PLAN REMEDIATION
- [ ] Plan SSOT remediation strategy

### Step 4: ⏳ PENDING - EXECUTE REMEDIATION
- [ ] Implement SSOT metadata fixes

### Step 5: ⏳ PENDING - TEST FIX LOOP
- [ ] Prove changes maintain system stability
- [ ] Fix any test failures

### Step 6: ⏳ PENDING - PR AND CLOSURE
- [ ] Create PR linking to this issue
- [ ] Close issue on successful merge

## Verification Commands
```bash
# Test SSOT compliance after fixes
python tests/mission_critical/test_ssot_compliance_suite.py

# Test WebSocket event delivery
python tests/mission_critical/test_websocket_agent_events_suite.py

# New test for Issue #700
python tests/mission_critical/test_ssot_metadata_compliance_issue_700.py
```

## Notes
- This is blocking the critical Golden Path: users login → get AI responses
- Must maintain backwards compatibility during SSOT migration
- Focus on atomic commits with minimal scope per fix
- Root issue: Bypassing SSOT `store_metadata_result()` method from BaseAgent