# SSOT-incomplete-migration-duplicate-agent-registry-implementations.md

**GitHub Issue:** [#929](https://github.com/netra-systems/netra-apex/issues/929)
**Priority:** P0 - Blocks Golden Path
**Status:** DISCOVERED
**Created:** 2025-09-14

## Summary
Critical SSOT violation with duplicate AgentRegistry implementations blocking Golden Path functionality.

## Issue Details
- **Simple Registry:** `/netra_backend/app/agents/registry.py` (Lines 81-406) 
- **Enhanced Registry:** `/netra_backend/app/agents/supervisor/agent_registry.py` (Lines 286-1700)
- **Impact:** Test failures, runtime issues, no user isolation
- **Files Affected:** 875+ import references

## Progress Tracker

### Step 0: Discovery ✅ COMPLETE
- [x] SSOT audit completed
- [x] GitHub issue #929 created
- [x] Progress tracker created

### Step 1: Test Discovery & Planning 
- [ ] Find existing tests protecting agent registry functionality
- [ ] Plan new SSOT validation tests
- [ ] Update progress

### Step 2: Execute New Test Plan
- [ ] Create SSOT agent registry tests
- [ ] Validate test execution
- [ ] Update progress

### Step 3: Plan SSOT Remediation
- [ ] Design consolidation approach
- [ ] Plan import migration strategy
- [ ] Update progress

### Step 4: Execute SSOT Remediation
- [ ] Consolidate registries
- [ ] Update imports
- [ ] Update progress

### Step 5: Test Fix Loop
- [ ] Run all tests
- [ ] Fix failing tests
- [ ] Validate stability

### Step 6: PR & Closure
- [ ] Create pull request
- [ ] Link to issue #929
- [ ] Close issue on merge

## Notes
- Focus on minimal changes to maintain system stability
- Prioritize Golden Path functionality
- Ensure user isolation maintained