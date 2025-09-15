# Failing Tests Gardener Worklog - Critical Tests 
**Generated:** 2025-09-14 12:29
**Focus:** Critical mission critical tests
**Command:** `/failingtestsgardener critical`

## Executive Summary
Identified multiple critical test failures across WebSocket infrastructure, configuration management, and SSOT compliance patterns. Issues range from missing constants and deprecated imports to fundamental threading and event delivery problems.

## Test Execution Results

### 1. WebSocket Agent Events Suite (`test_websocket_agent_events_suite.py`)
**Status:** PARTIALLY FAILING (15/18 passed, 1 failed, 2 errors)
**Business Impact:** $500K+ ARR - Core chat functionality affected

**Issues Found:**

#### Issue 1A: RealWebSocketTestConfig Missing Attribute 
- **Error:** `AttributeError: 'RealWebSocketTestConfig' object has no attribute 'concurrent_connections'`
- **Location:** `tests/mission_critical/websocket_real_test_base.py:1322`
- **Test:** `test_real_websocket_performance_metrics`
- **Severity:** P2 - Performance testing blocked
- **Root Cause:** Configuration class missing required attribute

#### Issue 1B: RealWebSocketTestConfig Constructor Issue
- **Error:** `TypeError: RealWebSocketTestConfig.__init__() got an unexpected keyword argument 'concurrent_connections'`
- **Location:** `tests/mission_critical/test_websocket_agent_events_suite.py:1302`
- **Tests:** `TestRealE2EWebSocketAgentFlow` test setup 
- **Severity:** P1 - E2E testing completely blocked
- **Root Cause:** Constructor signature mismatch

### 2. WebSocket Bridge Critical Flows (`test_websocket_bridge_critical_flows.py`)
**Status:** FAILING (3/13 passed, 10 failed)
**Business Impact:** Critical WebSocket infrastructure failures

**Issues Found:**

#### Issue 2A: Missing RUN_ID_PREFIX Constant
- **Error:** `NameError: name 'RUN_ID_PREFIX' is not defined`
- **Location:** `tests/mission_critical/test_websocket_bridge_critical_flows.py:313`
- **Test:** `test_run_id_always_includes_thread`
- **Severity:** P1 - Critical constant missing
- **Root Cause:** Missing import or constant definition

#### Issue 2B: Thread Resolution Priority Chain Failure
- **Error:** `AssertionError: Orchestrator fallback failed: expected 'thread_from_orchestrator', got 'thread_priority_test_run_123'`
- **Location:** `tests/mission_critical/test_websocket_bridge_critical_flows.py:349`
- **Test:** `test_thread_resolution_priority_chain`
- **Severity:** P0 - Thread management critical failure
- **Root Cause:** Thread resolution logic broken

#### Issue 2C: Registry Backup Mechanism Failure
- **Error:** `AssertionError: Should attempt orchestrator resolution`
- **Location:** `tests/mission_critical/test_websocket_bridge_critical_flows.py:385`
- **Test:** `test_registry_backup_when_orchestrator_fails`
- **Severity:** P1 - Fallback mechanisms not working
- **Root Cause:** Orchestrator resolution not being attempted

#### Issue 2D: WebSocket Event Delivery Failures
- **Error:** Multiple event delivery test failures
- **Tests:** `test_websocket_events_reach_users`, `test_event_delivery_failure_recovery`, `test_high_frequency_event_delivery`
- **Severity:** P0 - Core WebSocket functionality broken
- **Root Cause:** Event delivery mechanism failures

#### Issue 2E: Performance Issues
- **Error:** `assert 0.0003650188446044922 > 1.8` - Performance expectations not met
- **Test:** High frequency event delivery
- **Severity:** P2 - Performance regression
- **Root Cause:** Event delivery too fast (potentially indicates bypassing/mocking)

### 3. Deprecated Import Warnings
**Status:** WARNING (System-wide issue)
**Business Impact:** Technical debt accumulation

**Issues Found:**

#### Issue 3A: WebSocket Manager Import Deprecation
- **Warning:** `Importing WebSocketManager from 'netra_backend.app.websocket_core' is deprecated`
- **Location:** `netra_backend/app/agents/mixins/websocket_bridge_adapter.py:14`
- **Severity:** P3 - Technical debt
- **Root Cause:** Legacy import patterns

#### Issue 3B: Pydantic Configuration Deprecation
- **Warning:** `Support for class-based config is deprecated, use ConfigDict instead`
- **Severity:** P3 - Framework compatibility
- **Root Cause:** Outdated Pydantic patterns

### 4. Resource Management Issues
**Status:** WARNING (Memory leaks potential)

#### Issue 4A: Uncompleted Coroutines
- **Warning:** `coroutine 'get_websocket_manager' was never awaited`
- **Warning:** `coroutine 'ThreadRunRegistry._cleanup_loop' was never awaited`
- **Severity:** P1 - Memory leak potential
- **Root Cause:** Async cleanup not properly handled

## Tests That Ran Silently (Potential Issues)
The following critical tests ran without output, which may indicate:
- Silent failures
- Bypassed execution
- Missing test implementation

- `test_no_ssot_violations.py`
- `test_orchestration_integration.py` 
- `test_docker_stability_suite.py`

## Recommended Actions

### Immediate (P0 - System Down)
1. Fix thread resolution priority chain failures
2. Restore WebSocket event delivery functionality

### High Priority (P1 - Major Feature Broken)
3. Fix RealWebSocketTestConfig constructor issues
4. Resolve missing RUN_ID_PREFIX constant
5. Fix registry backup mechanisms
6. Address resource management/cleanup issues

### Medium Priority (P2 - Minor Issues)
7. Fix performance testing configuration
8. Address performance regression in event delivery

### Low Priority (P3 - Technical Debt)
9. Update deprecated import patterns
10. Migrate to modern Pydantic configuration

## Next Steps
1. Create GitHub issues for each identified problem
2. Link related issues together
3. Assign priority labels (P0-P3)
4. Update this worklog with issue links
5. Track remediation progress

---
**Generated by:** Failing Tests Gardener (Critical Focus)
**Runtime:** ~2 minutes
**Test Files Analyzed:** 2 major test suites
**Issues Identified:** 10+ distinct problems