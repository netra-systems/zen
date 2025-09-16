# Redis SSOT Legacy Removal Test Strategy

**Business Value Justification:**
- **Segment:** Platform/Internal
- **Business Goal:** Chat Functionality Reliability (90% of platform value)
- **Value Impact:** Prevents WebSocket 1011 errors that break real-time chat
- **Strategic Impact:** Protects $500K+ ARR by ensuring reliable Redis operations

## Executive Summary

This comprehensive test strategy validates Redis SSOT (Single Source of Truth) compliance and ensures legacy removal doesn't break the golden path: **users login → get AI responses**.

### Current State Assessment
- **SSOT Redis Manager:** `/netra_backend/app/redis_manager.py` (well-implemented with circuit breaker, auto-reconnection, health monitoring)
- **Compatibility Layer:** `/netra_backend/app/core/redis_manager.py` (marked as DEPRECATED, redirects to SSOT)
- **Business Critical:** Prevents Issue #849 WebSocket 1011 errors caused by competing Redis managers

## Test Suite Architecture

### 1. Mission Critical Tests (`/tests/mission_critical/`)

#### `test_redis_ssot_compliance_suite.py`
**Purpose:** Validate SSOT compliance and architecture
**Key Validations:**
- SSOT Redis Manager is the only active implementation
- Legacy compatibility layer properly redirects to SSOT
- Circuit breaker and auto-reconnection functionality
- Auth service compatibility methods
- User cache manager operations

**Critical Test Cases:**
```python
# SSOT Compliance
test_ssot_redis_manager_initialization()
test_ssot_redis_operations_basic()
test_ssot_redis_circuit_breaker_functionality()

# Legacy Compatibility  
test_legacy_manager_redirects_to_ssot()
test_legacy_operations_redirect_to_ssot()
test_legacy_deprecation_warning_issued()

# Multi-User Isolation
test_user_specific_cache_isolation()
test_concurrent_user_operations_no_conflicts()
test_websocket_state_isolation()
```

#### `test_redis_websocket_1011_regression.py`
**Purpose:** Prevent WebSocket 1011 errors (Issue #849)
**Key Validations:**
- No competing Redis managers exist
- WebSocket handshake doesn't race with Redis operations
- Circuit breaker prevents cascading failures
- Multi-user sessions don't conflict

**Critical Test Cases:**
```python
# 1011 Error Prevention
test_no_competing_redis_managers_prevent_1011()
test_websocket_handshake_redis_race_condition_prevention()
test_redis_circuit_breaker_prevents_1011_errors()
test_concurrent_user_websocket_no_1011_conflicts()
```

### 2. Integration Tests (`/tests/integration/`)

#### `test_redis_websocket_integration_no_docker.py`
**Purpose:** Validate Redis + WebSocket integration without Docker
**Key Validations:**
- WebSocket events properly use Redis for state management
- Agent execution state persists correctly
- Real-time events delivered without conflicts
- Error recovery scenarios

**Critical Test Cases:**
```python
# WebSocket + Redis Integration
test_websocket_state_persistence_in_redis()
test_agent_execution_state_redis_integration()
test_websocket_event_sequence_redis_tracking()
test_concurrent_websocket_redis_operations()

# Error Recovery
test_websocket_state_recovery_after_redis_reconnect()
test_websocket_graceful_degradation_without_redis()
```

### 3. Performance Tests (`/tests/performance/`)

#### `test_redis_performance_validation.py`
**Purpose:** Validate Redis performance for chat functionality
**Key Validations:**
- Connection pool efficiency under load
- Auto-reconnection performance characteristics
- Multi-user concurrent operation performance
- Memory usage and leak prevention

**Performance Thresholds:**
- Connection status check: < 1ms
- get_client operation: < 10ms
- Basic SET operations: < 5ms average, < 15ms 95th percentile
- Basic GET operations: < 3ms average, < 10ms 95th percentile
- WebSocket events: < 3ms storage, < 2ms retrieval
- Concurrent users: > 100 ops/sec throughput

### 4. End-to-End Tests (`/tests/e2e/`)

#### `test_redis_gcp_staging_validation.py`
**Purpose:** Validate complete Redis integration in GCP staging
**Key Validations:**
- Redis connectivity through VPC connector
- Complete chat workflow with Redis backend
- Multi-user chat sessions in production-like environment
- Performance characteristics in staging

**Staging Environment:**
- Uses `*.netrasystems.ai` domains (Issue #1278 fix)
- Redis through VPC connector: `10.0.0.3:6379`
- Production-like performance validation
- Complete golden path validation

## Test Execution Strategy

### Local Development Testing
```bash
# Mission Critical Tests
python tests/mission_critical/test_redis_ssot_compliance_suite.py
python tests/mission_critical/test_redis_websocket_1011_regression.py

# Integration Tests (NO DOCKER)
python tests/integration/test_redis_websocket_integration_no_docker.py

# Performance Validation
python tests/performance/test_redis_performance_validation.py
```

### Staging Environment Testing
```bash
# GCP Staging Validation
ENVIRONMENT=staging python tests/e2e/test_redis_gcp_staging_validation.py
```

### Unified Test Runner Execution
```bash
# Complete Redis SSOT test suite
python tests/unified_test_runner.py --category mission_critical --pattern "redis"
python tests/unified_test_runner.py --category integration --pattern "redis" --real-services
python tests/unified_test_runner.py --category performance --pattern "redis" --real-services
python tests/unified_test_runner.py --category e2e --pattern "redis" --env staging
```

## Key Test Focus Areas

### 1. Business Critical (90% of Platform Value)
- **Chat Functionality:** Complete user workflow from login to AI response
- **WebSocket Events:** All 5 critical events delivered (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- **Real-time Performance:** Sub-10ms Redis operations for chat responsiveness

### 2. Technical Critical
- **SSOT Compliance:** No competing Redis managers causing conflicts
- **Legacy Removal:** Deprecated layer properly redirects to SSOT
- **WebSocket 1011 Prevention:** Race conditions eliminated

### 3. User Experience
- **Multi-User Isolation:** Users don't see each other's data
- **Performance Scalability:** System handles concurrent users
- **Error Recovery:** Graceful degradation when Redis unavailable

### 4. Production Ready
- **Staging Validation:** Complete workflow in GCP staging environment
- **VPC Connectivity:** Redis accessible through Cloud Run VPC connector
- **Performance Characteristics:** Production-like latency and throughput

## Test Environment Configuration

### Local Testing
```bash
TESTING=true
ENVIRONMENT=test
TEST_DISABLE_REDIS=false
REDIS_URL=redis://localhost:6381/0  # Test Redis port
```

### Staging Testing
```bash
ENVIRONMENT=staging
GCP_PROJECT=netra-staging
BACKEND_URL=https://staging.netrasystems.ai
REDIS_URL=redis://10.0.0.3:6379/0  # GCP internal Redis
VPC_CONNECTOR=staging-connector
```

## Success Criteria

### SSOT Compliance
- ✅ All Redis imports reference the same instance
- ✅ Legacy manager redirects to SSOT implementation
- ✅ No duplicate Redis managers in memory
- ✅ Deprecation warnings issued for legacy imports

### WebSocket 1011 Prevention
- ✅ No race conditions during WebSocket handshake
- ✅ Circuit breaker prevents cascading failures
- ✅ Multi-user sessions don't conflict
- ✅ Event delivery is reliable and fast

### Performance Validation
- ✅ Basic operations under performance thresholds
- ✅ Concurrent user scalability demonstrated
- ✅ Memory usage remains bounded
- ✅ Auto-reconnection works efficiently

### Production Readiness
- ✅ Complete chat workflow in staging
- ✅ VPC connectivity validated
- ✅ Production-like performance characteristics
- ✅ Error recovery scenarios tested

## Risk Mitigation

### High Risk Scenarios
1. **WebSocket 1011 Errors:** Comprehensive regression tests prevent recurrence
2. **Performance Degradation:** Performance thresholds ensure chat responsiveness
3. **Multi-User Conflicts:** Isolation tests prevent data leakage
4. **Production Failures:** Staging validation matches production environment

### Monitoring & Validation
- Redis manager status reporting for production monitoring
- Circuit breaker metrics for failure detection
- Performance metrics for SLA compliance
- Health check endpoints for operational visibility

## Conclusion

This comprehensive test strategy ensures Redis SSOT legacy removal maintains system stability and protects the critical chat functionality that delivers 90% of platform value. The test suite validates everything from basic SSOT compliance to production-ready performance characteristics in GCP staging environment.

**Golden Path Protection:** Users login → get AI responses remains reliable throughout Redis SSOT migration.