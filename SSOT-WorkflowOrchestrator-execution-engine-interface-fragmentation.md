# SSOT-WorkflowOrchestrator-execution-engine-interface-fragmentation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/233  
**Status:** DISCOVERY COMPLETE  
**Priority:** P0 - Critical (Blocks Golden Path)

## Problem Summary

WorkflowOrchestrator receives inconsistent execution engine implementations due to incomplete SSOT migration, causing golden path failures where users cannot get AI responses.

## SSOT Violation Details

### Root Cause
- WorkflowOrchestrator (clean implementation) accepts ANY execution engine via dependency injection
- Multiple deprecated execution engine implementations still being passed to it
- Interface fragmentation between legacy and SSOT engines

### Impact on Golden Path
- **User Response Failures**: Different execution engines provide inconsistent behavior
- **WebSocket Event Failures**: Legacy engines don't support user-isolated events
- **User Context Leakage**: Non-SSOT engines cause user isolation failures
- **Runtime Failures**: Inconsistent execution engine interfaces

## Files Involved

### ✅ Clean SSOT Files
- `/netra_backend/app/agents/supervisor/workflow_orchestrator.py` (Primary target - clean)
- `/netra_backend/app/agents/supervisor/user_execution_engine.py` (SSOT execution engine)
- `/netra_backend/app/agents/supervisor_ssot.py` (Clean SSOT supervisor)

### 🚨 Deprecated Files (SSOT Violations)
- `/netra_backend/app/agents/supervisor/execution_engine.py` (DEPRECATED but still used)
- `/netra_backend/app/agents/execution_engine_consolidated.py` (DEPRECATED but still used)

### 🔧 Integration Points
- `/netra_backend/app/dependencies.py` (Factory patterns)
- `/netra_backend/app/agents/supervisor_consolidated.py` (Legacy supervisor)

## Progress Tracking

### ✅ COMPLETED
- [x] SSOT Audit Discovery
- [x] GitHub Issue Created (#233)
- [x] Problem Analysis Complete
- [x] Test Discovery and Planning Complete

### 📋 NEXT STEPS
- [ ] Execute new SSOT test plan (20% new tests)
- [ ] Plan SSOT remediation
- [ ] Execute SSOT remediation
- [ ] Test fix loop until all tests pass
- [ ] Create PR and close issue

## Test Discovery Results

### Existing Test Coverage
- **60+ existing tests** for WorkflowOrchestrator and related components
- **Strong coverage** in unit, integration, and E2E categories
- **Tests currently passing** but lack SSOT-specific validation

### Critical Gaps Identified
- **No validation** that WorkflowOrchestrator rejects deprecated execution engines
- **Missing interface consistency tests** between legacy and SSOT engines
- **No user isolation validation** for concurrent execution contexts
- **No failing tests** to prove current SSOT violations exist

### New Test Plan (11 new test files)
- **P0 Failing Tests** (4 files): Prove SSOT violations exist
- **Integration Tests** (4 files): UserExecutionEngine compatibility 
- **E2E Tests** (3 files): Full orchestration workflows

### Test Categories Breakdown
- **20% new SSOT tests**: 11 files focusing on interface validation
- **60% existing tests**: Current coverage with potential updates needed
- **20% validation tests**: Ensure SSOT fixes work properly

### Timeline
- **3-day sprint**: Critical failing tests implementation
- **18 days total**: Complete test implementation and validation

## Solution Strategy

1. **Interface Validation**: Add validation to WorkflowOrchestrator constructor
2. **Factory Updates**: Ensure all factories create UserExecutionEngine instances
3. **Deprecation Enforcement**: Make deprecated engines fail fast
4. **Integration Testing**: Verify supervisor → WorkflowOrchestrator flows use SSOT

---

**Created:** 2025-09-10  
**Last Updated:** 2025-09-10  
**Process:** SSOT Gardening - Step 0 Complete