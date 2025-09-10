# SSOT Tool Dispatcher Registry Violations - Progress Tracker

**GitHub Issue:** [#205](https://github.com/netra-systems/netra-apex/issues/205)  
**Created:** 2025-01-09  
**Focus:** UniversalRegistry SSOT compliance for tool dispatcher patterns  
**Business Impact:** $500K+ ARR chat functionality at risk

## SSOT Audit Results

### Critical Violations Identified
1. **P0 - GOLDEN PATH BREAKING:**
   - Multiple competing ToolDispatcher implementations
   - `netra_backend/app/core/tools/tool_dispatcher_core.py:38-100`
   - `netra_backend/app/core/tools/request_scoped_tool_dispatcher.py:58-80`
   - Canonical SSOT: `netra_backend/app/core/tools/unified_tool_dispatcher.py`

2. **P0 - IMPORT VIOLATIONS:**
   - 25+ files bypassing SSOT with direct AgentRegistry imports
   - Legacy registry wrappers creating duplicate instances

3. **P1 - ARCHITECTURE DEBT:**
   - Admin dispatcher parallel hierarchies
   - Legacy compatibility layers with composition instead of inheritance

### Actual SSOT Compliance: ~85% (not 99%+ as reported)

## Process Status
- [x] Step 0: SSOT Audit - COMPLETED
- [x] GitHub Issue Created: #205
- [x] Step 1: Test Discovery & Planning - COMPLETED
- [ ] Step 2: Test Execution  
- [ ] Step 3: Remediation Planning
- [ ] Step 4: Remediation Execution
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR & Closure

## Test Discovery Results (Step 1)

### Existing Test Coverage
- **147 existing test files** protect tool dispatcher systems
- **Mission Critical:** WebSocket agent events suite ($500K+ ARR protection)
- **Factory Isolation:** Multi-user context separation tests
- **Risk:** High risk to mission critical WebSocket tests during refactor

### Test Plan Summary
- **Existing Tests (60%):** Update 147 tests to use UniversalRegistry SSOT
- **New SSOT Tests (20%):** Create failing tests that reproduce violations
- **Edge Cases (20%):** WebSocket consistency, performance validation

### Key Files to Test
- `tool_dispatcher_core.py` - Factory-enforced but not SSOT
- `request_scoped_tool_dispatcher.py` - Per-request isolation
- `unified_tool_dispatcher.py` - SSOT consolidation attempt

## Work Log
- **2025-01-09:** Initial SSOT audit completed via subagent
- **2025-01-09:** Created GitHub issue #205 and progress tracker
- **2025-01-09:** Test discovery and planning completed - 147 tests identified