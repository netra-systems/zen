# SSOT Agent-WebSocket Bridge Violations Test Suite - Issue #1070

This directory contains failing tests that reproduce SSOT agent-websocket bridge violations as specified in Issue #1070.

## Purpose

**Create failing tests that PROVE violations exist before implementing SSOT bridge patterns.**

These tests are designed to:
1. **FAIL initially** - proving the documented violations exist in the codebase
2. **PASS after SSOT implementation** - validating that proper bridge patterns are in place

## Test Files Created

### 1. `test_agent_websocket_direct_import_violations.py`
**Priority 1 - AST Parsing Tests**

Tests that detect direct WebSocketManager imports using AST parsing:
- `test_detect_direct_websocket_manager_imports()` - Scans agent files for direct imports
- `test_verify_known_violation_locations()` - Validates specific lines mentioned in Issue #1070
- `test_detect_websocket_singleton_patterns()` - Identifies singleton anti-patterns
- `test_websocket_bridge_interface_compliance()` - Checks for proper SSOT bridge usage

**Expected Results (Confirmed):**
- ✅ FAILS: Found 6 files with violations including exact locations from Issue #1070
- ✅ FAILS: Verified violations at lines 13 (mcp_execution_engine.py) and 30 (pipeline_executor.py)

### 2. `test_websocket_bridge_pattern_compliance.py`
**Priority 2 - Bridge Pattern Validation**

Tests that validate SSOT bridge pattern compliance:
- `test_websocket_manager_factory_isolation()` - Verifies factory patterns vs singletons
- `test_multi_user_websocket_isolation()` - Tests user isolation (some pass, some fail)
- `test_websocket_event_delivery_isolation()` - Event routing validation
- `test_agent_websocket_bridge_initialization()` - Bridge initialization patterns
- `test_websocket_state_persistence_isolation()` - State persistence across sessions

**Expected Results (Confirmed):**
- ✅ FAILS: WebSocketBridgeFactory not available (SSOT violation)
- ✅ FAILS: Agent modules using direct imports instead of bridge pattern
- ✅ Mixed results: Some isolation tests pass, proving tests work correctly

## Violations Successfully Reproduced

The test suite successfully identified and reproduced the following violations:

### Direct Import Violations (6 files)
```
app/agents/tool_dispatcher.py: [28]
app/agents/tool_executor_factory.py: [31] 
app/agents/supervisor/agent_registry.py: [43, 734, 821]
app/agents/supervisor/mcp_execution_engine.py: [13]  ← Issue #1070 target
app/agents/supervisor/pipeline_executor.py: [30]     ← Issue #1070 target
app/agents/supervisor/agent_instance_factory.py: [47]
```

### Known Violation Verification
```
mcp_execution_engine.py: Expected line 13, Actual [13] ✅ EXACT MATCH
pipeline_executor.py: Expected line 30, Actual [30] ✅ EXACT MATCH
```

## Test Execution

### Run All SSOT Violation Tests
```bash
python3 -m pytest tests/unit/ssot_violations/ -v --tb=short
```

### Run Specific Test Categories
```bash
# Direct import detection
python3 -m pytest tests/unit/ssot_violations/test_agent_websocket_direct_import_violations.py -v

# Bridge pattern compliance
python3 -m pytest tests/unit/ssot_violations/test_websocket_bridge_pattern_compliance.py -v
```

### Expected Results
- **6 tests FAIL** - Proving violations exist ✅
- **3 tests PASS** - Testing scenarios without current violations ✅

## Business Impact

**Revenue Protection:** $500K+ ARR Golden Path functionality depends on proper WebSocket event delivery through SSOT patterns that ensure:
- Multi-user isolation preventing data contamination
- Reliable event routing to correct users only
- Factory patterns preventing singleton-based race conditions

## Integration with Issue #1070

These tests serve as the **Phase 1 validation** for Issue #1070 SSOT agent-websocket bridge implementation:

1. **Phase 1 (Complete)**: Failing tests prove violations exist
2. **Phase 2 (Next)**: Implement SSOT bridge patterns 
3. **Phase 3 (Validation)**: Tests pass proving SSOT compliance

## Test Infrastructure

- **Base Class**: Uses `SSotBaseTestCase` and `SSotAsyncTestCase` from test framework
- **Markers**: `@pytest.mark.ssot_violation` and `@pytest.mark.priority_p0/p1`
- **Real Services**: No Docker required for unit tests, uses real imports and AST parsing
- **Metrics**: Tracks violation counts and locations for progress monitoring

---

**Status**: ✅ COMPLETE - Successfully created failing tests that prove SSOT violations exist  
**Next Steps**: Implement SSOT bridge patterns to make these tests pass