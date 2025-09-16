# WebSocket Await Error Test Execution Plan

## Overview

This document provides comprehensive test execution procedures for reproducing and validating Issue #1184 - WebSocket manager await errors in three critical locations:

1. `netra_backend/app/agents/example_message_processor.py:671`
2. `netra_backend/app/services/corpus/clickhouse_operations.py:134`
3. `netra_backend/app/services/corpus/clickhouse_operations.py:174`

## Business Impact

**CRITICAL**: These await errors could break the Golden Path user flow, which delivers 90% of platform value through AI chat interactions.

## Test Categories Created

### 1. Unit Tests - Direct Error Reproduction
**Purpose**: Reproduce the exact TypeError about await expressions
**File**: `tests/unit/test_websocket_await_error_reproduction.py`

**Test Targets**:
- ✅ ExampleMessageProcessor._get_websocket_manager await error (line 671)
- ✅ ClickHouseCorpusOperations._get_websocket_manager await error (line 134)
- ✅ ClickHouseCorpusOperations._get_websocket_manager await error (line 174)
- ✅ Sync vs async factory pattern validation
- ✅ Async function detection in problematic classes

### 2. Integration Tests - Real Service Scenarios
**Purpose**: Validate WebSocket manager patterns in integration scenarios
**File**: `tests/integration/test_websocket_manager_sync_async_integration.py`

**Test Targets**:
- ✅ WebSocket manager creation using different factory patterns
- ✅ ExampleMessageProcessor integration scenarios
- ✅ ClickHouseCorpusOperations integration scenarios
- ✅ Factory pattern consistency validation
- ✅ User isolation verification

### 3. Mission Critical Tests - Business Value Protection
**Purpose**: Ensure await errors don't break core business functionality
**File**: `tests/mission_critical/test_websocket_await_error_mission_critical.py`

**Test Targets**:
- ✅ Golden Path WebSocket manager availability
- ✅ Critical WebSocket events delivery (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- ✅ Agent message processing resilience
- ✅ Corpus operations resilience
- ✅ Factory pattern Golden Path compliance
- ✅ Comprehensive impact assessment

### 4. E2E Staging Tests - Complete User Journey
**Purpose**: Validate end-to-end user experience on staging infrastructure
**File**: `tests/e2e/test_websocket_await_error_golden_path_staging.py`

**Test Targets**:
- ✅ WebSocket connection establishment on staging.netrasystems.ai
- ✅ Complete agent message flow validation
- ✅ Corpus operations E2E testing
- ✅ Golden Path resilience assessment
- ✅ Error recovery mechanisms

## Test Execution Commands

### Quick Error Reproduction (Unit Tests)
```bash
# Run unit tests to reproduce the specific await errors
python tests/unified_test_runner.py --category unit --filter websocket_await_error

# Or run directly with pytest
python -m pytest tests/unit/test_websocket_await_error_reproduction.py -v --tb=short
```

### Integration Validation (No Docker Required)
```bash
# Run integration tests with real services
python tests/unified_test_runner.py --category integration --filter websocket_manager_sync_async

# Or run directly
python -m pytest tests/integration/test_websocket_manager_sync_async_integration.py -v --tb=short
```

### Mission Critical Validation
```bash
# Run mission critical tests
python tests/unified_test_runner.py --category mission_critical --filter websocket_await_error

# Or run directly
python -m pytest tests/mission_critical/test_websocket_await_error_mission_critical.py -v --tb=short
```

### E2E Staging Validation
```bash
# Run E2E tests on staging GCP (no Docker)
python tests/unified_test_runner.py --category e2e --env staging --filter websocket_await_error

# Or run directly
python -m pytest tests/e2e/test_websocket_await_error_golden_path_staging.py -v --tb=short
```

### Complete Test Suite Execution
```bash
# Run all WebSocket await error tests
python tests/unified_test_runner.py --execution-mode comprehensive --filter websocket_await_error

# Run with real services and detailed output
python tests/unified_test_runner.py --real-services --execution-mode nightly --filter websocket_await_error --no-fast-fail
```

## Expected Test Results

### 🚨 FAILING TESTS (Expected to Expose Issues)

**Unit Tests**:
- `test_example_message_processor_await_error_line_671` - Should FAIL with TypeError
- `test_clickhouse_operations_await_error_line_134` - Should FAIL with TypeError
- `test_clickhouse_operations_await_error_line_174` - Should FAIL with TypeError
- `test_websocket_manager_factory_sync_vs_async_patterns` - Should FAIL demonstrating incorrect await usage

**Expected Error Messages**:
```
TypeError: object NoneType can't be used in 'await' expression
TypeError: object WebSocketManager can't be used in 'await' expression
TypeError: 'get_websocket_manager' object is not awaitable
```

### ✅ PASSING TESTS (Should Validate Workarounds)

**Integration Tests**:
- WebSocket manager creation patterns should work with correct sync/async usage
- User isolation should remain functional
- Factory consistency should be maintained

**Mission Critical Tests**:
- Basic WebSocket manager availability should work
- Critical event delivery should have fallback mechanisms
- Golden Path should remain partially functional

## Validation Procedures

### 1. Error Confirmation Procedure
```bash
# Step 1: Run unit tests to confirm errors exist
python -m pytest tests/unit/test_websocket_await_error_reproduction.py::TestWebSocketManagerAwaitErrorReproduction::test_example_message_processor_await_error_line_671 -v

# Step 2: Verify specific error messages
python -m pytest tests/unit/test_websocket_await_error_reproduction.py -v | grep -i "TypeError\|await\|awaitable"

# Step 3: Check impact on integration
python -m pytest tests/integration/test_websocket_manager_sync_async_integration.py -v --tb=short
```

### 2. Business Impact Assessment
```bash
# Run mission critical tests to assess Golden Path impact
python -m pytest tests/mission_critical/test_websocket_await_error_mission_critical.py::TestWebSocketAwaitErrorMissionCritical::test_websocket_await_error_impact_assessment -v -s

# Check for impact report in output
```

### 3. Staging Environment Validation
```bash
# Test on staging to validate real-world impact
python -m pytest tests/e2e/test_websocket_await_error_golden_path_staging.py::TestWebSocketAwaitErrorGoldenPathStaging::test_golden_path_resilience_assessment_staging -v -s

# Look for resilience assessment in output
```

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# If you get import errors, check SSOT test framework
python -c "from test_framework.ssot.base_test_case import SSotAsyncTestCase; print('SSOT framework available')"
```

**WebSocket Connection Failures**:
```bash
# Test basic WebSocket connectivity
python -c "import asyncio, websockets; print('WebSocket client available')"
```

**Environment Issues**:
```bash
# Verify environment configuration
python scripts/query_string_literals.py validate "staging.netrasystems.ai"
```

### Debug Procedures

**Detailed Error Analysis**:
```bash
# Run with maximum verbosity and no fast-fail
python -m pytest tests/unit/test_websocket_await_error_reproduction.py -v -s --tb=long --no-header

# Capture output to file for analysis
python -m pytest tests/unit/test_websocket_await_error_reproduction.py -v -s --tb=long > websocket_await_error_debug.log 2>&1
```

**Interactive Debugging**:
```bash
# Run single test with debugger
python -m pytest tests/unit/test_websocket_await_error_reproduction.py::TestWebSocketManagerAwaitErrorReproduction::test_example_message_processor_await_error_line_671 -v -s --pdb
```

## Integration with Existing Test Suites

### Run Alongside Mission Critical Tests
```bash
# Include in existing mission critical test runs
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_websocket_await_error_mission_critical.py
```

### Include in Regression Testing
```bash
# Add to regression test pipeline
python tests/unified_test_runner.py --categories mission_critical unit integration --filter websocket
```

## Success Criteria

### Error Reproduction Success
- [ ] Unit tests successfully reproduce TypeError in all 3 locations
- [ ] Error messages clearly indicate await expression issues
- [ ] Tests provide clear line number references

### Business Impact Assessment Success
- [ ] Mission critical tests identify which functionality remains working
- [ ] Impact assessment provides actionable data
- [ ] Golden Path resilience is quantified

### Staging Validation Success
- [ ] E2E tests demonstrate real-world impact
- [ ] Resilience assessment shows system capability
- [ ] Recovery mechanisms are validated

## Next Steps After Test Execution

1. **Analyze Results**: Review test output to confirm issue reproduction
2. **Prioritize Fixes**: Use impact assessment to prioritize which errors to fix first
3. **Implement Solutions**: Create fixes for the highest-impact await errors
4. **Validate Fixes**: Re-run test suite to confirm fixes work
5. **Update Documentation**: Document the resolution approach

## Related Documentation

- **[Issue #1184](https://github.com/netra-systems/netra-apex/issues/1184)** - Original issue report
- **[WebSocket Infrastructure](../websocket_infrastructure.md)** - WebSocket architecture
- **[Golden Path Documentation](../GOLDEN_PATH_USER_FLOW_COMPLETE.md)** - Complete user flow
- **[Test Creation Guide](../../reports/testing/TEST_CREATION_GUIDE.md)** - General testing guidelines
- **[CLAUDE.md](../../CLAUDE.md)** - Development principles and priorities