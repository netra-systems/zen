# SSOT-incomplete-migration-ExecutionEngine-Fragmentation-Blocks-Golden-Path

**GitHub Issue:** [#1146](https://github.com/netra-systems/netra-apex/issues/1146)  
**Created:** 2025-09-14  
**Priority:** P0 - Golden Path Critical  
**Business Impact:** SEVERE - $500K+ ARR Golden Path blocked by response delivery failures

## Problem Summary

**STATUS:** PARTIALLY MIGRATED - 12 execution engines exist (only 1 should exist)

### Key Violations Discovered
- **12 execution engine implementations** found (only UserExecutionEngine should exist)
- **53+ files** still importing non-SSOT execution engines  
- **Multiple factory patterns** creating different engine types for same users
- **WebSocket event fragmentation** with events delivered through multiple paths

### Business Impact
- Users execute agents but responses never reach them due to execution engine fragmentation
- Race conditions cause some users to get responses while others don't  
- WebSocket events delivered through inconsistent paths
- $500K+ ARR chat functionality failing for customers

## Critical Files Identified

### SSOT Target (What Should Exist)
- `/netra_backend/app/agents/supervisor/user_execution_engine.py` (SSOT TARGET)

### Legacy Files (To be Consolidated/Removed)
- `/netra_backend/app/agents/supervisor/execution_engine_factory.py` (partially migrated)
- `/netra_backend/app/agents/supervisor/request_scoped_execution_engine.py` (legacy)
- `/netra_backend/app/agents/supervisor/mcp_execution_engine.py` (duplicate)

### Import Violations
- **53+ files** still importing non-SSOT execution engines (to be discovered in step 1)

## Work Progress

### Step 0: SSOT Audit ✅ COMPLETE
- [x] Discovered 12 execution engine fragmentation issue
- [x] Created GitHub issue #1146
- [x] Created local tracking file
- [x] Initial documentation committed

### Step 1: Discover and Plan Test ✅ COMPLETE
- [x] **1.1 DISCOVER EXISTING:** Found comprehensive test coverage with 433+ test files
- [x] **1.2 PLAN ONLY:** Planned 80% test updates + 20% new SSOT validation tests

#### Test Discovery Results
- **Mission Critical Tests:** 12 critical test files (MUST PASS)
- **WebSocket Event Tests:** 40+ files validating all 5 critical events
- **Golden Path Tests:** 15+ files protecting $500K+ ARR functionality  
- **Integration Tests:** 25+ files for system integration
- **Total Coverage:** 433+ test files providing excellent foundation

#### Test Plan Strategy
- **80% Effort:** Update existing tests to use UserExecutionEngine only
- **20% Effort:** Create new SSOT validation tests to prevent regression
- **Risk Assessment:** LOW - Exceptional existing test coverage provides protection
- **Approach:** Phased consolidation with comprehensive validation at each step

### Step 2: Execute Test Plan (PENDING)
- [ ] Create 20% new SSOT tests for execution engine consolidation
- [ ] Validate test plan with subagent

### Step 3: Plan Remediation (PENDING)
- [ ] Plan SSOT remediation strategy
- [ ] Define phase-by-phase consolidation approach

### Step 4: Execute Remediation (PENDING)
- [ ] Execute SSOT remediation plan
- [ ] Consolidate 12 engines to single UserExecutionEngine

### Step 5: Test Fix Loop (PENDING)
- [ ] Run and fix all test cases
- [ ] Ensure system stability maintained
- [ ] Validate Golden Path functionality

### Step 6: PR and Closure (PENDING)
- [ ] Create pull request
- [ ] Cross-link to close issue #1146

## Solution Strategy

Execute Phase 3-5 of planned execution engine consolidation:
1. Systematic consolidation with comprehensive testing
2. Validate Golden Path after each change  
3. Monitor Mission Critical Tests throughout process
4. Maintain WebSocket Events (all 5 events must continue working)

## Success Criteria

- ✅ Single UserExecutionEngine as SSOT
- ✅ All 53+ files use SSOT imports
- ✅ Golden Path user flow operational
- ✅ Mission critical tests passing
- ✅ WebSocket events consistently delivered

## Notes

- Stay on develop-long-lived branch
- FIRST DO NO HARM - maintain system stability
- Focus on atomic changes that improve SSOT compliance
- All WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) must continue working