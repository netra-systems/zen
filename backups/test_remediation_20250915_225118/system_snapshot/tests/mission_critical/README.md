# Mission Critical Tests - WebSocket Agent Events

## Overview

This directory contains **MISSION CRITICAL** tests that MUST pass before ANY deployment. These tests validate that WebSocket events are properly sent during agent execution, which is essential for basic chat functionality.

## Why This Is Critical

Without these WebSocket events, the chat UI appears "frozen" and users cannot see:
- Agent thinking/reasoning
- Tool execution progress
- Partial results as they're generated
- Final completion status

**Business Impact**: $500K+ ARR at risk if basic chat is broken

## Test Structure

### Core Tests

1. **test_final_validation.py**
   - Validates AgentRegistry enhances tool dispatcher
   - Ensures WebSocket manager is properly set
   - Tests complete integration flow
   - **MUST PASS** before deployment

2. **test_websocket_agent_events_suite.py**
   - Unit tests for individual components
   - Integration tests for event flow
   - E2E tests for full agent execution
   - Regression prevention tests

3. **test_websocket_events_advanced.py**
   - Event ordering validation
   - Failure injection testing
   - Performance benchmarks (500+ events/sec)
   - Security and edge cases

### Agent Golden Path Coverage (Issue #872) - **NEW**

4. **Agent Golden Path Integration Tests**
   - **Status**: Phase 1 Complete - 100% success rate (4/4 tests passing)
   - **Coverage**: Core agent execution, WebSocket integration, SSOT validation
   - **Business Impact**: $500K+ ARR golden path functionality protected
   - **SSOT Enhancements**: ExecutionEngineFactory validation methods
   - **Multi-User Isolation**: Enhanced concurrent user session security
   - **Performance Metrics**: Factory creation timing and baseline establishment

## Required Events

The following events MUST be sent during agent execution:

1. **agent_started** - Indicates processing has begun
2. **agent_thinking** - Shows reasoning/planning steps
3. **tool_executing** - Tool is being invoked
4. **tool_completed** - Tool execution finished
5. **agent_completed** - Final completion status

## Running Tests

### Quick Validation (< 5 seconds)
```bash
python -m pytest tests/mission_critical/test_final_validation.py -v
```

### Full Test Suite
```bash
python -m pytest tests/mission_critical/ -v
```

### Agent Golden Path Tests (Issue #872)
```bash
# Core golden path tests - 100% success rate
python tests/unit/golden_path/test_agent_execution_core_golden_path.py
python tests/unit/golden_path/test_golden_path_business_value_protection.py

# SSOT validation tests
python tests/unit/ssot_validation/test_golden_path_logging_disconnection_reproduction.py
```

### Regression Prevention Only
```bash
python -m pytest tests/mission_critical/test_websocket_agent_events_suite.py::TestRegressionPrevention -v
```

### Performance Benchmarks
```bash
python -m pytest tests/mission_critical/test_websocket_events_advanced.py::TestPerformanceBenchmarks -v
```

## Integration with Deployment

These tests are automatically run by:

1. **deploy_to_gcp.py** - Runs before any GCP deployment
2. **unified_test_runner.py** - Included in "mission_critical" category
3. **CI/CD Pipeline** - Blocks merge if tests fail

## Troubleshooting

### Tests Failing?

1. Check if `AgentRegistry.set_websocket_manager()` is enhancing the tool dispatcher
2. Verify `enhance_tool_dispatcher_with_notifications()` is being called
3. Ensure WebSocketNotifier methods are sending events correctly

### Key Files to Check

- `netra_backend/app/agents/supervisor/agent_registry.py` (Lines 126-141)
- `netra_backend/app/agents/enhanced_tool_execution.py`
- `netra_backend/app/agents/supervisor/websocket_notifier.py`

### Related Documentation

- [WebSocket Integration Learning](../../SPEC/learnings/websocket_agent_integration_critical.xml)
- [Deployment Checklist](../../DEPLOYMENT_CHECKLIST.md)
- [CLAUDE.md Requirements](../../CLAUDE.md#6-mission-critical-websocket-agent-events)

## Test Markers

All tests use pytest markers:
- `@pytest.mark.critical` - Critical functionality
- `@pytest.mark.mission_critical` - Deployment blocking
- `@pytest.mark.asyncio` - Async test functions

## Performance Requirements

- Event throughput: > 500 events/second
- Event latency: < 50ms per event
- Memory usage: < 100MB for 10,000 events
- No event loss under normal conditions

## Rollback Criteria

If these tests fail in production:
1. IMMEDIATELY rollback deployment
2. Check WebSocket event flow in staging
3. Verify tool dispatcher enhancement
4. Run full regression suite before re-deploying

## Contact

For issues with these tests, check:
- SPEC/learnings/websocket_agent_integration_critical.xml
- Recent commits to agent_registry.py
- WebSocket infrastructure changes