# Critical Auth & WebSocket Tests Implementation Plan

## Executive Summary
Based on analysis of XML specs and current test coverage, we've identified **10 CRITICAL MISSING TESTS** that put $150K+ MRR at risk. These tests focus on BASIC functionality that's currently untested while exotic edge cases have extensive coverage.

## Top 10 Critical Missing Tests (Priority Order)

### 1. **Auth Service Independence Test** [P0 - BLOCKS ENTERPRISE]
- **File**: `tests/unified/e2e/test_auth_service_independence.py`
- **Issue**: Auth service imports from main app violate microservice independence
- **Impact**: Cannot scale auth separately, blocks SOC2 compliance
- **Test**: Verify auth service has ZERO imports from main app
- **Spec**: `independent_services.xml`

### 2. **WebSocket Database Session Handling Test** [P0 - CRITICAL BUG]
- **File**: `tests/unified/e2e/test_websocket_db_session_handling.py`
- **Issue**: FastAPI Depends() doesn't work in WebSocket endpoints
- **Impact**: Database connection failures in production WebSockets
- **Test**: Verify WebSocket endpoints create sessions correctly via context manager
- **Spec**: `websockets.xml` lines 49-67

### 3. **Service-to-Service Authentication Test** [P0 - SECURITY]
- **File**: `tests/unified/e2e/test_service_to_service_auth.py`
- **Issue**: No validation of internal service authentication tokens
- **Impact**: Services can't authenticate with each other securely
- **Test**: Backend calls auth service with service token, not user token
- **Spec**: `auth_microservice_migration_plan.xml`

### 4. **WebSocket Event Flow Completeness Test** [P0 - UX BROKEN]
- **File**: `tests/unified/e2e/test_websocket_event_completeness.py`
- **Issue**: Missing events: agent_thinking, partial_result, tool_executing, final_report
- **Impact**: Frontend UI layers don't update, users see blank screens
- **Test**: Verify ALL required events are sent with correct payloads
- **Spec**: `websocket_communication.xml`

### 5. **Auth Service Circuit Breaker Test** [P0 - AVAILABILITY]
- **File**: `tests/unified/e2e/test_auth_circuit_breaker.py`
- **Issue**: When auth service down, entire system fails
- **Impact**: 100% downtime when auth has issues
- **Test**: System degrades gracefully when auth service fails
- **Spec**: `auth_microservice_migration_plan.xml` lines 295-319

### 6. **WebSocket Token Expiry Reconnection Test** [P1 - USER EXPERIENCE]
- **File**: `tests/unified/e2e/test_websocket_token_expiry_reconnect.py`
- **Issue**: WebSocket disconnects permanently when token expires
- **Impact**: Users lose chat mid-conversation
- **Test**: WebSocket reconnects with refreshed token automatically
- **Spec**: `websockets.xml`

### 7. **Cross-Service Session Consistency Test** [P1 - DATA INTEGRITY]
- **File**: `tests/unified/e2e/test_cross_service_session_sync.py`
- **Issue**: Sessions inconsistent between auth service, backend, and WebSocket
- **Impact**: User logged in one place, logged out another
- **Test**: Session state synchronized across all services via Redis
- **Spec**: `auth_environment_isolation.xml`

### 8. **OAuth Proxy PR Environment Test** [P1 - STAGING BROKEN]
- **File**: `tests/unified/e2e/test_oauth_proxy_staging.py`
- **Issue**: PR environments can't use OAuth (Google requires exact URLs)
- **Impact**: Can't test auth in staging PRs
- **Test**: OAuth proxy correctly routes PR environment auth
- **Spec**: `auth_environment_isolation.xml` lines 115-149

### 9. **WebSocket Message Structure Consistency Test** [P1 - COMPATIBILITY]
- **File**: `tests/unified/e2e/test_websocket_message_structure.py`
- **Issue**: Inconsistent message formats {type, payload} vs {event, data}
- **Impact**: Frontend randomly fails to parse messages
- **Test**: ALL WebSocket messages use consistent structure
- **Spec**: `websocket_communication.xml` lines 210-219

### 10. **Auth Token Validation Cache Test** [P1 - PERFORMANCE]
- **File**: `tests/unified/e2e/test_auth_token_cache.py`
- **Issue**: Every request validates token with auth service (no caching)
- **Impact**: 100ms+ latency on every API call
- **Test**: Token validation cached for 5 minutes, cache invalidation works
- **Spec**: `auth_microservice_migration_plan.xml` lines 277-293

## Implementation Strategy

### Phase 1: Critical Foundation (Tests 1-5)
**Timeline**: Immediate
**Agents**: 5 parallel agents
**Goal**: Fix blocking issues preventing basic operation

### Phase 2: User Experience (Tests 6-10)  
**Timeline**: After Phase 1
**Agents**: 5 parallel agents
**Goal**: Fix issues affecting user experience

## Test Requirements

### ALL Tests MUST:
1. Use REAL services (NO MOCKS for internal services)
2. Complete in <10 seconds
3. Test both happy path AND 3+ error scenarios
4. Include performance validation
5. Follow `SPEC/testing.xml` patterns

### Test Structure Template:
```python
"""
Test Name - Priority Level
BVJ: Segment | Goal | Value Impact | Revenue Impact
SPEC: Reference to XML spec
ISSUE: What's broken
IMPACT: Business consequence
"""
```

## Success Criteria
- ALL 10 tests passing
- Zero imports from main app in auth service
- WebSocket events match frontend expectations
- Auth failover working
- Session consistency verified
- <10 second execution per test

## Agents Assignment
Each agent will implement one test following this plan. Tests are independent and can be implemented in parallel.

## Verification Process
1. Run each test individually
2. Run all tests together
3. Fix any failures in real system
4. Repeat until 100% pass rate

---
**CRITICAL**: These are not exotic edge cases - these are BASIC requirements that should have been tested from day one. The system cannot work reliably without these tests passing.