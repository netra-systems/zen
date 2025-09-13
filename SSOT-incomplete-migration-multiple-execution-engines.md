# SSOT-incomplete-migration-multiple-execution-engines

**GitHub Issue**: [#759](https://github.com/netra-systems/netra-apex/issues/759)
**Priority**: P0 (Golden Path Critical)
**Status**: Step 0 Complete - Issue Created
**Branch**: develop-long-lived

## Problem Statement

Multiple execution engine implementations exist despite SSOT consolidation claims, creating race conditions and potential user context leakage that directly impacts users getting AI responses.

## Critical Evidence

### Multiple Execution Engines Found:
1. **UserExecutionEngine** - Claimed SSOT
2. **RequestScopedExecutionEngine** - 619 lines, full duplicate implementation
3. **ExecutionEngine** - Multiple redirects/adapters
4. **SupervisorExecutionEngineAdapter**
5. **ConsolidatedExecutionEngineWrapper**
6. **MCPEnhancedExecutionEngine**
7. **IsolatedExecutionEngine**

### Multiple Supervisor Agent Implementations:
- **SupervisorAgent** in `supervisor_ssot.py` (claimed SSOT)
- **SupervisorAgent** in `supervisor_consolidated.py` (duplicate class name)
- **ChatOrchestrator** extending SupervisorAgent
- Multiple workflow orchestrators

### WebSocket Event Delivery Duplication:
- **AgentWebSocketBridge** - 3,800+ lines with full event implementation
- **UnifiedWebSocketEmitter** - Another full implementation
- Multiple `notify_agent_*` methods in different classes

## Golden Path Impact

1. **User Context Isolation Failures**: Multiple execution engines could leak user data
2. **Race Conditions**: Different execution paths causing users to not receive AI responses
3. **Event Delivery Inconsistencies**: Multiple WebSocket implementations causing silent failures
4. **Response Delivery Failures**: Agents execute but responses never reach users

## Progress Tracking

- [x] **Step 0 Complete**: SSOT Audit - Critical P0 violation identified and issue created
- [x] **Step 1 Complete**: Discovered comprehensive test inventory - 12 execution engines found (only 1 should exist)
- [x] **Step 2 Complete**: Created 6 new SSOT tests - ALL FAILING as expected (proving violations exist)
- [ ] **Step 3**: Plan SSOT remediation strategy
- [ ] **Step 4**: Execute SSOT remediation plan
- [ ] **Step 5**: Test fix loop - validate system stability
- [ ] **Step 6**: Create PR and close issue

## Critical Discovery: 12 Execution Engines Found (Only 1 Should Exist)

**SSOT TARGET**: `UserExecutionEngine` (`/netra_backend/app/agents/supervisor/user_execution_engine.py`)

**VIOLATION**: 11 additional execution engine implementations found:
1. `execution_engine_consolidated.py`
2. `execution_engine_interface.py`
3. `execution_engine_legacy_adapter.py`
4. `execution_engine_unified_factory.py`
5. `supervisor/execution_engine.py` (redirect)
6. `supervisor/execution_engine_factory.py`
7. `supervisor/mcp_execution_engine.py`
8. `supervisor/request_scoped_execution_engine.py`
9. `core/managers/execution_engine_factory.py`
10. `services/unified_tool_registry/execution_engine.py`
11. `agents/unified_tool_execution.py`

## Test Plan - DISCOVERED

### Existing Tests Protecting Agent Execution (60% - Must Continue Passing):
- [x] **Mission Critical**: `test_websocket_agent_events_suite.py` - $500K+ ARR protection
- [x] **Foundation**: `test_user_execution_engine_context_isolation.py` - Multi-user security (527 lines)
- [x] **Foundation**: `test_user_execution_engine_state_management.py` - Resource management
- [x] **Factory Patterns**: `test_base_agent_factory_patterns.py` - SSOT factory compliance (503 lines)
- [x] **E2E Golden Path**: Multiple E2E tests using UserExecutionEngine SSOT
- [x] **Security**: Multi-user isolation and security vulnerability prevention tests

### Failing Tests (Prove Violation Exists):
- [x] **SSOT Enforcement**: `test_execution_engine_enforcement.py` - FAILING (12 engines found)
- [x] **Supervisor Duplication**: `test_ssot_supervisor_duplication_violations.py` - FAILING (multiple implementations)

### New Tests Created (20% - SSOT Validation Tests):
- [x] **Legacy Engine Detection**: `test_legacy_execution_engine_detection.py` - ❌ FAILING (123 classes, 112 violations)
- [x] **Import Enforcement**: `test_import_enforcement.py` - ❌ FAILING (53 files with forbidden imports)
- [x] **Factory Compliance**: `test_factory_compliance.py` - ❌ FAILING (multiple factory classes)
- [x] **Runtime Validation**: `test_runtime_validation.py` - ❌ FAILING (multiple engine types at runtime)
- [x] **WebSocket Event SSOT**: `test_websocket_event_ssot.py` - ❌ FAILING (events through multiple paths)
- [x] **Multi-User SSOT**: `test_multi_user_ssot.py` - ❌ FAILING (different users get different engines)

## Step 2 Results - New SSOT Tests Validation

### Critical Violations Detected:
- **123 execution engine classes** found (112 legacy violations beyond UserExecutionEngine SSOT)
- **53 files with forbidden imports** directly importing non-SSOT engines
- **Multiple factory implementations** creating different engine types
- **Runtime inconsistencies** with different engines used across requests
- **WebSocket event fragmentation** with events delivered through multiple paths
- **User isolation failures** with different users receiving different engine types

### Test Status (All Designed to FAIL Now, PASS After Remediation):
- **Created**: 6/6 new SSOT validation tests
- **Current Status**: ALL FAILING ❌ (proves violations exist)
- **Expected After Step 4**: ALL PASSING ✅ (validates successful consolidation)
- **Business Protection**: Tests prevent regression after SSOT consolidation

## Remediation Plan - DETAILED

### Phase 1: Pre-Remediation Validation (2 hours)
- [x] **Run Mission Critical Suite**: Must maintain 100% pass rate
- [x] **Validate Foundation Tests**: UserExecutionEngine base functionality
- [x] **Confirm Failing Tests**: Prove SSOT violations exist

### Phase 2: SSOT Consolidation (6 hours)
1. **Merge Unique Functionality**: `execution_engine_consolidated.py` → UserExecutionEngine
2. **Extract Interface**: `execution_engine_interface.py` → implement in UserExecutionEngine
3. **Remove Legacy Adapter**: `execution_engine_legacy_adapter.py` after migration
4. **Integrate MCP**: `mcp_execution_engine.py` → UserExecutionEngine MCP support
5. **Merge Request Scoping**: `request_scoped_execution_engine.py` → UserExecutionEngine
6. **Consolidate Factories**: All factories → single UserExecutionEngineFactory

### Phase 3: Post-Remediation Validation (2 hours)
- [ ] **Mission Critical Suite**: Must maintain 100% pass rate
- [ ] **SSOT Enforcement Tests**: Should change from FAILING to PASSING
- [ ] **E2E Golden Path**: Full end-to-end validation
- [ ] **Performance**: Ensure no degradation from consolidation

## Files Requiring Changes - SPECIFIC

### Execution Engines (Remove 11, Keep 1):
- **KEEP**: `/netra_backend/app/agents/supervisor/user_execution_engine.py` (SSOT)
- **REMOVE**: 11 other execution engine files listed above

### Factory Classes (Consolidate):
- Merge all factories into single `UserExecutionEngineFactory`

### Import Updates (Redirect):
- Update all imports to use UserExecutionEngine SSOT
- Add backward compatibility during transition

### WebSocket Integration:
- Ensure WebSocket events delivered through UserExecutionEngine only
- Update mocked tests to use SSOT patterns

---
*Last Updated*: 2025-01-13 | *Next Update*: Step 1 completion