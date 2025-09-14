# Issue #1032 WebSocket Message Timeout - Comprehensive Test Plan

**Issue**: WebSocket Message Timeout in staging (3+ second delays)
**Root Cause**: Infrastructure dependency degradation (Redis/PostgreSQL)
**Current Test**: `tests/e2e/staging/test_2_message_flow_staging.py::test_real_websocket_message_flow`
**Success Rate**: 80% (4/5 tests passing)
**SLA Requirement**: <2 seconds response time
**Failure Threshold**: >3 seconds (currently failing)

## Executive Summary

This test plan addresses WebSocket message timeout issues in the staging environment where response times exceed 3 seconds, violating the 2-second SLA. The root cause is infrastructure dependency degradation affecting Redis and PostgreSQL performance. We need comprehensive tests to reproduce, validate, and monitor timeout behavior across the entire message processing pipeline.

## Test Categories Overview

### 1. Infrastructure Dependency Tests
**Purpose**: Validate Redis/PostgreSQL connectivity and performance under load
**Target**: Identify when infrastructure dependencies cause >2s delays

### 2. WebSocket Performance Tests
**Purpose**: Measure actual response times vs expected SLA (<2 seconds)
**Target**: Reproduce and validate the >3 second timeout scenarios

### 3. Message Flow Integration Tests
**Purpose**: Test complete agent message pipeline end-to-end
**Target**: Validate entire business workflow under stress conditions

### 4. Timeout Behavior Tests
**Purpose**: Reproduce and validate specific timeout scenarios
**Target**: Create failing tests that expose timeout conditions

### 5. Staging Environment Validation Tests
**Purpose**: Verify GCP staging service health and performance
**Target**: Validate production-like environment behavior

## Detailed Test Implementation Plan

### Phase 1: Infrastructure Dependency Tests

#### 1.1 Redis Performance Tests
**File**: `tests/integration/infrastructure/test_redis_timeout_validation.py`

**Test Scenarios**:
- `test_redis_connection_latency_sla_validation()` - EXPECTED TO FAIL
  - Measure Redis connection establishment time
  - Assert connection time < 100ms (will fail if infrastructure degraded)
  - Track latency trends over multiple attempts

- `test_redis_cache_read_performance_under_load()` - EXPECTED TO FAIL
  - Simulate high cache read volume
  - Measure response times under concurrent access
  - Assert 95th percentile < 50ms

- `test_redis_cache_write_performance_degradation()` - EXPECTED TO FAIL
  - Test cache writes under memory pressure
  - Monitor for performance degradation patterns
  - Track memory usage and connection pooling

#### 1.2 PostgreSQL Performance Tests
**File**: `tests/integration/infrastructure/test_postgresql_timeout_validation.py`

**Test Scenarios**:
- `test_postgresql_query_response_time_sla()` - EXPECTED TO FAIL
  - Execute typical queries used in message flow
  - Measure query execution times
  - Assert query time < 200ms (currently failing at >5 seconds)

- `test_postgresql_connection_pool_exhaustion()` - EXPECTED TO FAIL
  - Simulate high connection demand
  - Monitor for connection pool exhaustion
  - Validate graceful degradation vs timeout failures

- `test_postgresql_transaction_isolation_performance()` - EXPECTED TO FAIL
  - Test concurrent transaction performance
  - Measure transaction commit times under load
  - Identify lock contention causing delays

### Phase 2: WebSocket Performance Tests

#### 2.1 WebSocket Response Time Tests
**File**: `tests/e2e/performance/test_websocket_response_time_sla.py`

**Test Scenarios**:
- `test_websocket_message_response_time_under_2_seconds()` - EXPECTED TO FAIL
  - Send messages via WebSocket
  - Measure end-to-end response time
  - Assert response time < 2000ms (currently failing at >3000ms)
  - Use existing `record_latency()` utility from performance helpers

- `test_websocket_concurrent_message_performance_degradation()` - EXPECTED TO FAIL
  - Send multiple concurrent messages
  - Monitor response time degradation
  - Track resource usage during high load

- `test_websocket_agent_event_delivery_timing()` - EXPECTED TO FAIL
  - Test all 5 required WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
  - Measure time between events
  - Assert event delivery within performance thresholds

#### 2.2 WebSocket Connection Stability Tests
**File**: `tests/integration/websocket/test_websocket_connection_timeout_behavior.py`

**Test Scenarios**:
- `test_websocket_connection_timeout_under_infrastructure_stress()` - EXPECTED TO FAIL
  - Establish WebSocket connections during infrastructure degradation
  - Monitor connection establishment times
  - Validate timeout behavior vs hanging connections

- `test_websocket_heartbeat_failure_during_slow_responses()` - EXPECTED TO FAIL
  - Test heartbeat mechanism when message processing is slow
  - Ensure connections don't drop during legitimate processing delays
  - Validate connection recovery mechanisms

### Phase 3: Message Flow Integration Tests

#### 3.1 Agent Pipeline Performance Tests
**File**: `tests/integration/agents/test_agent_pipeline_timeout_validation.py`

**Test Scenarios**:
- `test_agent_execution_pipeline_timeout_reproduction()` - EXPECTED TO FAIL
  - Execute complete agent workflow (Supervisor → Triage → Data → Optimizer)
  - Measure pipeline execution time
  - Assert total execution time < 10 seconds (may fail due to infrastructure)

- `test_agent_websocket_event_timing_degradation()` - EXPECTED TO FAIL
  - Track timing between WebSocket events during agent execution
  - Monitor for event delivery delays
  - Validate event ordering and timing consistency

#### 3.2 Three-Tier Persistence Performance Tests
**File**: `tests/integration/persistence/test_three_tier_timeout_behavior.py`

**Test Scenarios**:
- `test_redis_postgresql_clickhouse_cascade_timeout()` - EXPECTED TO FAIL
  - Test 3-tier persistence under infrastructure stress
  - Monitor for cascade timeout effects (Redis slow → PostgreSQL overload → ClickHouse delays)
  - Measure tier-specific performance degradation

### Phase 4: Timeout Behavior Reproduction Tests

#### 4.1 Specific Timeout Scenario Tests
**File**: `tests/critical/test_websocket_timeout_scenario_reproduction.py`

**Test Scenarios**:
- `test_reproduce_3_second_plus_websocket_timeout()` - EXPECTED TO FAIL
  - Specifically reproduce the >3 second timeout scenario from Issue #1032
  - Use staging environment configuration
  - Create controlled conditions that trigger the timeout

- `test_timeout_behavior_under_database_slow_queries()` - EXPECTED TO FAIL
  - Simulate slow database queries (>5 seconds as reported)
  - Monitor WebSocket response behavior during database delays
  - Validate timeout vs hanging behavior

#### 4.2 Graceful Degradation Tests
**File**: `tests/integration/resilience/test_timeout_graceful_degradation.py`

**Test Scenarios**:
- `test_websocket_graceful_timeout_vs_hanging()` - EXPECTED TO FAIL
  - Validate that timeouts fail gracefully rather than hanging indefinitely
  - Test timeout error messages and user feedback
  - Ensure resource cleanup during timeout scenarios

### Phase 5: Staging Environment Validation Tests

#### 5.1 GCP Staging Service Health Tests
**File**: `tests/e2e/staging/test_gcp_staging_service_health_validation.py`

**Test Scenarios**:
- `test_staging_service_health_endpoints_response_time()` - EXPECTED TO FAIL
  - Test all health endpoints in staging environment
  - Measure response times for health checks
  - Assert health check time < 1 second

- `test_staging_infrastructure_resource_monitoring()` - EXPECTED TO FAIL
  - Monitor CPU, memory, network usage in staging
  - Correlate resource usage with timeout behavior
  - Identify resource constraints causing performance degradation

#### 5.2 End-to-End Staging Validation
**File**: `tests/e2e/staging/test_staging_websocket_timeout_e2e.py`

**Test Scenarios**:
- `test_staging_complete_user_workflow_performance()` - EXPECTED TO FAIL
  - Execute complete user workflow in staging (login → send message → receive response)
  - Measure end-to-end timing
  - Assert complete workflow < 15 seconds total

## Test Infrastructure Requirements

### Dependencies
- **Authentication**: Use `test_framework.ssot.e2e_auth_helper` for all E2E tests
- **Performance Monitoring**: Leverage existing `test_message_flow_performance_helpers.py` utilities
- **Environment**: Use `shared.isolated_environment` for environment management
- **WebSocket Client**: Use existing `tests.clients.websocket_client` for connections

### Performance Measurement Utilities

```python
# From existing performance helpers
class PerformanceTracker:
    def record_latency(self, operation: str, latency_ms: float) -> None:
        # Check SLA violation (>2000ms for standard operations)
        if latency_ms > 2000:
            self.sla_violations.append({
                "operation": operation,
                "latency_ms": latency_ms,
                "violation_type": "latency",
                "timestamp": datetime.now(timezone.utc),
            })

    def record_throughput(self, operations_per_second: float) -> None:
        # Check SLA violation (<10 ops/sec minimum)
        if operations_per_second < 10:
            # Record throughput SLA violation
```

### Test Data and Configuration

**Environment Configuration**:
- **Staging URL**: Use staging WebSocket endpoint from `get_staging_config()`
- **Authentication**: Create test tokens via `TestAuthHelper(environment="staging")`
- **Test Users**: Use dedicated test users for performance validation

**Performance Thresholds**:
- WebSocket Response Time SLA: <2000ms (2 seconds)
- Current Failure Threshold: >3000ms (3 seconds)
- Database Query SLA: <200ms
- Redis Operation SLA: <50ms
- Health Check SLA: <1000ms
- Complete User Workflow SLA: <15 seconds

## Test Execution Strategy

### Execution Phases

1. **Phase 1 - Infrastructure Tests**: Run infrastructure dependency tests first
2. **Phase 2 - WebSocket Performance**: Test WebSocket-specific performance
3. **Phase 3 - Integration**: Test complete message flow pipeline
4. **Phase 4 - Reproduction**: Create specific timeout reproduction scenarios
5. **Phase 5 - Staging Validation**: Validate in production-like environment

### Test Commands

```bash
# Run all timeout validation tests
python -m pytest tests/integration/infrastructure/ tests/e2e/performance/ tests/critical/test_websocket_timeout_scenario_reproduction.py -v --tb=short

# Run specific infrastructure tests
python -m pytest tests/integration/infrastructure/test_redis_timeout_validation.py -v
python -m pytest tests/integration/infrastructure/test_postgresql_timeout_validation.py -v

# Run WebSocket performance tests
python -m pytest tests/e2e/performance/test_websocket_response_time_sla.py -v

# Run staging environment validation
python -m pytest tests/e2e/staging/test_staging_websocket_timeout_e2e.py -v
```

### Expected Results

**Initial Test Run Expected Results**:
- **FAIL**: 70-80% of tests expected to fail initially (reproducing timeout conditions)
- **Infrastructure Tests**: Should identify Redis/PostgreSQL performance bottlenecks
- **WebSocket Tests**: Should reproduce >3 second timeout scenarios
- **Integration Tests**: Should show pipeline bottlenecks during infrastructure stress

**Success Criteria After Fixes**:
- **PASS**: >95% of tests passing after infrastructure improvements
- **Performance**: All response times < 2 second SLA
- **Reliability**: No timeout scenarios in normal operation
- **Monitoring**: Clear visibility into performance degradation causes

## Test Deliverables

### 1. Test Files Created
- 8-10 new test files across infrastructure, performance, and staging validation
- ~50-60 individual test methods targeting specific timeout scenarios
- Integration with existing performance monitoring utilities

### 2. Performance Baselines
- Document current performance baselines before fixes
- Establish performance regression detection
- Create performance trend monitoring

### 3. Issue #1032 Resolution Validation
- Tests that specifically reproduce the 3+ second timeout issue
- Validation tests to confirm resolution after infrastructure fixes
- Regression tests to prevent future timeout issues

## Business Impact and Success Metrics

### Revenue Protection
- **$500K+ ARR Protection**: Ensure chat functionality meets performance SLA
- **User Retention**: Prevent user abandonment due to slow response times
- **Customer Satisfaction**: Meet response time expectations for enterprise clients

### Technical Success Metrics
- **SLA Compliance**: >95% of messages respond within 2 seconds
- **Infrastructure Health**: Database queries consistently <200ms
- **System Reliability**: Zero hanging connections or indefinite timeouts
- **Monitoring Coverage**: 100% visibility into performance bottlenecks

---

*This test plan follows CLAUDE.md best practices for NON-DOCKER testing, real service integration, and SSOT authentication patterns. All tests are designed to use real staging services and reproduce actual production conditions.*