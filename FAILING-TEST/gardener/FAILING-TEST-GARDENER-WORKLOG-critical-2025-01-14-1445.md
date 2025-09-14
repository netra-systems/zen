# Failing Test Gardener Worklog - Critical Tests
**Test Focus:** Critical Tests
**Date:** 2025-01-14 14:45
**Status:** Initial Discovery Phase

## Executive Summary
Initial discovery of critical test failures and collection issues across mission critical test suite.

## Issues Discovered

### Issue 1: WebSocket Event Structure Validation Failures
**Category:** failing-test-regression-P1-websocket-event-validation
**Status:** FAILING
**Severity:** P1 (High - major feature broken)
**Test File:** `tests/mission_critical/test_websocket_agent_events_suite.py::TestIndividualWebSocketEvents::test_agent_started_event_structure`

**Failure Details:**
- AssertionError: agent_started event structure validation failed
- WebSocket connection successful but event content structure invalid
- Related to business-critical WebSocket events for $500K+ ARR chat functionality

**Error Output:**
```
E   AssertionError: agent_started event structure validation failed
E   assert False
E    +  where False = validate_event_content_structure({'correlation_id': None, 'data': {'connection_id': 'main_828bdc00', 'features': {'agent_orchestration': True, 'cloud_run_optimized': True, 'emergency_fallback': True, 'full_business_logic': True, ...}, 'golden_path_events': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'], 'mode': 'main', ...}, 'server_id': None, 'timestamp': 1757855976.1867754, ...}, 'agent_started')
```

**Related WebSocket Tests:**
- `test_tool_executing_event_structure` - FAILED
- `test_tool_completed_event_structure` - FAILED
- `test_agent_completed_event_structure` - FAILED

### Issue 2: Docker Daemon Connection Failures
**Category:** failing-test-active-dev-P2-docker-connection
**Status:** FAILING
**Severity:** P2 (Medium - infrastructure issue affecting test execution)

**Failure Details:**
- Error: "The system cannot find the file specified" when connecting to Docker daemon
- Affects test infrastructure and container orchestration tests
- Fallback mode activating but may mask other issues

**Error Output:**
```
WARNING  test_framework.resource_monitor:resource_monitor.py:325 Failed to initialize Docker client (Docker daemon may not be running): Error while fetching server API version: (2, 'CreateFile', 'The system cannot find the file specified.')
```

### Issue 3: Test Collection Failures
**Category:** uncollectable-test-regression-P2-collection-issue
**Status:** UNCOLLECTABLE
**Severity:** P2 (Medium - tests not running)

**Affected Tests:**
- `tests/mission_critical/test_no_ssot_violations.py` - collected 0 items
- `tests/mission_critical/test_docker_stability_suite.py` - collected 0 items

**Impact:** Critical tests not being executed, masking potential issues

### Issue 4: Multiple Deprecation Warnings
**Category:** failing-test-new-P3-deprecation-warnings
**Status:** WARNING
**Severity:** P3 (Low - future compatibility issues)

**Warnings Identified:**
1. **Logging Import Deprecation:**
   ```
   shared.logging.unified_logger_factory is deprecated. Use 'from shared.logging.unified_logging_ssot import get_logger' instead.
   ```

2. **WebSocket Import Deprecation:**
   ```
   Importing WebSocketManager from 'netra_backend.app.websocket_core' is deprecated. Use canonical path 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' instead.
   ```

3. **Pydantic Configuration Deprecation:**
   ```
   Support for class-based `config` is deprecated, use ConfigDict instead.
   ```

## Business Impact Assessment
- **P1 Issues:** WebSocket event validation failures directly impact $500K+ ARR chat functionality
- **P2 Issues:** Test infrastructure problems may hide critical regressions
- **P3 Issues:** Future technical debt and potential breaking changes

## Next Steps
1. Create/update GitHub issues for each category
2. Link to related existing issues
3. Prioritize fixes based on business impact
4. Track remediation progress

## Test Environment Details
- Platform: win32
- Python: 3.13.7
- pytest: 8.4.2
- Peak Memory Usage: 217.8 MB
- WebSocket Endpoint: `wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/api/v1/websocket`