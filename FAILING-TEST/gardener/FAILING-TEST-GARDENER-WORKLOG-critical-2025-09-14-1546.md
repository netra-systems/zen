# FAILING-TEST-GARDENER-WORKLOG: Critical Tests

**Date:** 2025-09-14-1546  
**Test Focus:** critical  
**Command:** `python3 -m pytest tests/mission_critical/ -v --tb=short --disable-warnings --timeout=60 --maxfail=10 --continue-on-collection-errors`  
**Status:** 10 collection errors discovered out of 799 total items collected  

## Summary

Found 10 critical test collection errors preventing proper execution of mission critical tests. These are import/module-related failures that indicate SSOT violations or missing implementations.

## Issues Discovered

### 1. CircuitBreaker Import Failures (P1 - High Priority)
**Files Affected:**
- `tests/mission_critical/test_agent_resilience_patterns.py`
- `tests/mission_critical/test_circuit_breaker_comprehensive.py`

**Error:**
```
ImportError: cannot import name 'CircuitBreakerState' from 'netra_backend.app.services.circuit_breaker'
ImportError: cannot import name 'CircuitOpenException' from 'netra_backend.app.services.circuit_breaker'
```

**Impact:** Business resilience patterns not testable, affecting system stability validation.

### 2. Docker Circuit Breaker Module Missing (P2 - Medium Priority)
**File Affected:** `tests/mission_critical/test_docker_rate_limiter_integration.py`

**Error:**
```
ModuleNotFoundError: No module named 'test_framework.docker_circuit_breaker'
```

**Impact:** Docker rate limiting cannot be tested.

### 3. User Execution Context Import Failures (P0 - Critical Priority)
**Files Affected:**
- `tests/mission_critical/test_execution_engine_factory_isolation_1123.py`
- `tests/mission_critical/test_execution_engine_golden_path_integration_1123.py`

**Error:**
```
ImportError: cannot import name 'create_user_execution_context' from 'netra_backend.app.services.user_execution_context'
```

**Impact:** CRITICAL - User isolation testing broken, affects $500K+ ARR security compliance.

### 4. WebSocket Test Base Missing Function (P1 - High Priority)
**File Affected:** `tests/mission_critical/test_first_message_experience.py`

**Error:**
```
ImportError: cannot import name 'is_docker_available' from 'tests.mission_critical.websocket_real_test_base'
```

**Impact:** First message experience testing broken, affects user onboarding validation.

### 5. Infrastructure Remediation Module Missing (P2 - Medium Priority)
**File Affected:** `tests/mission_critical/test_infrastructure_remediation_comprehensive.py`

**Error:**
```
ModuleNotFoundError: No module named 'infrastructure.vpc_connectivity_fix'
```

**Impact:** Infrastructure validation testing broken.

### 6. Mission Critical Base Test Missing (P1 - High Priority)
**File Affected:** `tests/mission_critical/test_issue_1100_websocket_ssot_mission_critical.py`

**Error:**
```
ModuleNotFoundError: No module named 'tests.mission_critical.base'
```

**Impact:** SSOT WebSocket testing broken, affects core business functionality.

### 7. WebSocket Manager Factory Missing (P0 - Critical Priority)
**File Affected:** `tests/mission_critical/test_multi_user_id_isolation_failures.py`

**Error:**
```
ModuleNotFoundError: No module named 'netra_backend.app.websocket_core.websocket_manager_factory'
```

**Impact:** CRITICAL - Multi-user isolation testing broken, security vulnerability.

### 8. WebSocket Heartbeat Manager Import Failure (P1 - High Priority)
**File Affected:** `tests/mission_critical/test_presence_detection_critical.py`

**Error:**
```
ImportError: cannot import name 'WebSocketHeartbeatManager' from 'netra_backend.app.websocket_core.manager'
```

**Impact:** Connection health monitoring testing broken.

## Next Steps

1. Process each issue with individual subagent tasks
2. Search for existing GitHub issues 
3. Create new issues or update existing ones with priority tags
4. Link related issues, PRs, and documentation
5. Update this worklog and commit safely

## Test Execution Details

- **Total Items Collected:** 799
- **Collection Errors:** 10
- **Execution Time:** 2.37s
- **Python Version:** 3.13.7
- **Pytest Version:** 8.4.2
- **Platform:** Darwin (macOS 15.6.1)

## Priority Summary
- **P0 (Critical):** 2 issues - User isolation and multi-user security
- **P1 (High):** 4 issues - WebSocket functionality and business features  
- **P2 (Medium):** 2 issues - Infrastructure and rate limiting