# CRITICAL: ClickHouse Connection and Query Execution Fix
## Multi-Agent Team Mission

**SEVERITY: CRITICAL**
**IMPACT: Complete analytics system failure, circuit breaker activation**
**TIMELINE: Immediate fix required**

## Team Composition

### 1. Database Schema Agent
**Mission:** Ensure ClickHouse tables exist with correct schema
**Context:** Table `netra_analytics.performance_metrics` is missing
**Deliverables:**
- Verify/create ClickHouse database and tables
- Implement schema migration if needed
- Add health check for table existence

### 2. Query Debugging Agent
**Mission:** Fix the `user_id` undefined error in cache fallback
**Context:** Line 817 in `/app/netra_backend/app/db/clickhouse.py` has NameError
**Deliverables:**
- Fix variable scoping in cache access
- Ensure proper parameter passing
- Add defensive error handling

### 3. Connection Pool Agent
**Mission:** Stabilize ClickHouse connection management
**Context:** Frequent connection failures triggering circuit breaker
**Deliverables:**
- Implement connection retry logic
- Add connection pool monitoring
- Configure appropriate timeouts

### 4. Circuit Breaker Agent
**Mission:** Tune circuit breaker for appropriate failure tolerance
**Context:** Circuit breaker opening after 5 failures in 60 seconds
**Deliverables:**
- Review and adjust circuit breaker thresholds
- Implement gradual recovery strategy
- Add manual reset capability

## Critical Files to Investigate

```
netra_backend/app/db/clickhouse.py - Lines 800-850 (cache fallback logic)
netra_backend/app/db/clickhouse_schema.py - Schema definitions
netra_backend/app/core/telemetry.py - Circuit breaker configuration
netra_backend/migrations/ - Check for ClickHouse migrations
```

## Test Requirements

1. **Unit Tests:**
   - Test cache fallback with missing user_id
   - Test connection recovery after failure
   - Test circuit breaker state transitions

2. **Integration Tests:**
   - End-to-end metrics recording
   - Verify table creation on startup
   - Test failover to Redis cache

3. **Performance Tests:**
   - Load test with 100+ concurrent queries
   - Measure circuit breaker impact
   - Verify no memory leaks in connection pool

## Success Criteria

- [ ] No ClickHouse errors in startup logs
- [ ] Circuit breaker remains closed during normal operation
- [ ] All analytics queries execute successfully
- [ ] Cache fallback works without errors
- [ ] 100% test coverage for error paths

## Coordination Protocol

1. Schema Agent creates tables FIRST
2. Query Agent fixes code SECOND
3. Connection Agent optimizes pool THIRD
4. Circuit Breaker Agent tunes thresholds LAST
5. All agents run integration tests TOGETHER

## Emergency Rollback Plan

If fixes cause regression:
1. Disable ClickHouse integration temporarily
2. Use Redis-only fallback mode
3. Queue analytics events for later processing
4. Alert team of degraded analytics mode