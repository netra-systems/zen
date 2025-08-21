# L2 Integration Test Plan - 100 Critical Missing Tests

> **Generated:** 2025-08-20  
> **Total Protected MRR:** $870K  
> **Current Coverage:** 13.5% (434 tests) vs 60% target (1,933 tests needed)  
> **Gap:** 1,499 integration tests needed, 100 most critical identified here

## Executive Summary

This document identifies the 100 most critical missing L2 (Real SUT with Real Internal Dependencies) integration tests for the Netra Apex AI Optimization Platform. Each test includes business value justification (BVJ) and implementation priority.

## Test Categories Overview

| Category | Count | MRR Protection | Priority |
|----------|-------|----------------|----------|
| Authentication & Authorization | 15 | $150K | P0 |
| WebSocket & Real-time | 15 | $120K | P0 |
| Agent Orchestration | 20 | $200K | P0 |
| Database Coordination | 15 | $90K | P1 |
| Cache & State Management | 10 | $60K | P1 |
| Performance & Scalability | 10 | $80K | P2 |
| Error Recovery & Resilience | 10 | $70K | P1 |
| Business Critical Flows | 5 | $100K | P0 |

## Implementation Status

| Test # | Test Name | Status | File Location |
|--------|-----------|--------|---------------|
| 1 | OAuth-to-JWT-to-WebSocket Flow | ✅ Implemented | `test_oauth_jwt_websocket_flow.py` |
| 2 | Multi-Service Token Propagation | ✅ Implemented | `test_multi_service_token_propagation.py` |
| 31 | Supervisor-SubAgent Communication | ✅ Implemented | `test_supervisor_subagent_communication.py` |
| 96 | Free-to-Paid Conversion Flow | ✅ Implemented | `test_free_to_paid_conversion_flow.py` |
| 3-100 | Remaining Tests | 📋 Planned | See detailed list below |

---

## Detailed Test Specifications

### Authentication & Authorization (Tests 1-15) - $150K MRR Protection

#### 1. ✅ OAuth-to-JWT-to-WebSocket Flow
- **BVJ:** Prevents auth breaches worth $15K MRR per incident
- **Components:** OAuth provider, JWT handler, WebSocket manager, Redis
- **Status:** Implemented

#### 2. ✅ Multi-Service Token Propagation
- **BVJ:** SOC2 compliance, prevents $20K MRR data leakage
- **Components:** Auth service, backend, database, agent services
- **Status:** Implemented

#### 3. Session Redis Sync
- **BVJ:** Session consistency prevents $8K MRR user frustration churn
- **Components:** Redis cluster, session manager, auth service
- **Scenarios:** Session creation, updates, invalidation, cross-instance sync

#### 4. Permission Cascade on Role Change
- **BVJ:** Real-time permission updates prevent $10K MRR security incidents
- **Components:** Permission service, WebSocket broadcaster, cache invalidator
- **Scenarios:** Role upgrade, downgrade, team changes, immediate effect validation

#### 5. Auth Service Failover
- **BVJ:** High availability prevents $12K MRR downtime losses
- **Components:** Auth service, fallback cache, circuit breaker
- **Scenarios:** Primary auth down, cache-based auth, recovery detection

#### 6. Concurrent Login Sessions
- **BVJ:** Multi-device support worth $5K MRR enterprise features
- **Components:** Session manager, device registry, WebSocket multiplexer
- **Scenarios:** Same user multiple devices, session limits, device management

#### 7. Token Refresh During Active Request
- **BVJ:** Seamless UX prevents $7K MRR frustration churn
- **Components:** Token refresher, request interceptor, retry logic
- **Scenarios:** Mid-flight refresh, queued requests, parallel refreshes

#### 8. Cross-Service User Context
- **BVJ:** Consistent identity worth $9K MRR data integrity
- **Components:** User context propagator, service mesh, trace headers
- **Scenarios:** Context forwarding, enrichment, validation

#### 9. Team Permission Inheritance
- **BVJ:** Enterprise team features worth $15K MRR
- **Components:** Team service, permission calculator, inheritance resolver
- **Scenarios:** Nested teams, override rules, effective permissions

#### 10. API Key to User Mapping
- **BVJ:** Service account auth worth $8K MRR automation features
- **Components:** API key validator, user resolver, audit logger
- **Scenarios:** Key validation, user context, rate limiting

#### 11. Rate Limiting Per User Tier
- **BVJ:** Fair usage worth $10K MRR tier differentiation
- **Components:** Rate limiter, tier resolver, quota manager
- **Scenarios:** Tier limits, quota exhaustion, limit updates

#### 12. Auth Cache Invalidation
- **BVJ:** Security updates worth $12K MRR breach prevention
- **Components:** Cache invalidator, pub/sub, WebSocket notifier
- **Scenarios:** Logout propagation, permission changes, cache coherency

#### 13. SAML SSO Integration
- **BVJ:** Enterprise SSO worth $25K MRR enterprise contracts
- **Components:** SAML handler, IdP connector, user provisioner
- **Scenarios:** SAML assertion, user mapping, JIT provisioning

#### 14. 2FA Code Verification
- **BVJ:** Enhanced security worth $8K MRR compliance
- **Components:** 2FA generator, verifier, backup codes
- **Scenarios:** TOTP validation, SMS fallback, recovery codes

#### 15. Password Reset Token Flow
- **BVJ:** Account recovery worth $5K MRR support reduction
- **Components:** Token generator, email service, expiration handler
- **Scenarios:** Token generation, validation, expiration, one-time use

### WebSocket & Real-time (Tests 16-30) - $120K MRR Protection

#### 16. WebSocket-Database Session Coordination
- **BVJ:** Proper async context prevents $10K MRR data corruption
- **Components:** WebSocket handler, async DB session, context manager
- **Scenarios:** Session lifecycle, transaction boundaries, error handling

#### 17. Message Queue to WebSocket Broadcast
- **BVJ:** Real-time updates worth $8K MRR user engagement
- **Components:** Redis pub/sub, WebSocket broadcaster, message router
- **Scenarios:** Broadcast patterns, targeted messages, delivery guarantees

#### 18. WebSocket Reconnection State Recovery
- **BVJ:** Seamless reconnection worth $7K MRR UX quality
- **Components:** State manager, reconnection handler, message buffer
- **Scenarios:** Connection loss, state restoration, message replay

#### 19. Multi-Tab WebSocket Synchronization
- **BVJ:** Multi-tab support worth $6K MRR power user features
- **Components:** Tab coordinator, shared worker, message deduplication
- **Scenarios:** Tab detection, state sync, leader election

#### 20. WebSocket Rate Limiting
- **BVJ:** DoS prevention worth $9K MRR stability
- **Components:** Rate limiter, throttle handler, backpressure manager
- **Scenarios:** Message throttling, client notification, quota management

#### 21. Binary Message Handling
- **BVJ:** File upload worth $5K MRR feature completeness
- **Components:** Binary parser, chunk handler, progress tracker
- **Scenarios:** Large files, chunking, progress updates, resume

#### 22. WebSocket Health Check Integration
- **BVJ:** Monitoring worth $6K MRR operational excellence
- **Components:** Health checker, heartbeat manager, metric collector
- **Scenarios:** Heartbeat mechanism, timeout detection, metric reporting

#### 23. Message Ordering Guarantees
- **BVJ:** Data consistency worth $8K MRR reliability
- **Components:** Sequence manager, order enforcer, buffer manager
- **Scenarios:** Out-of-order detection, reordering, gap handling

#### 24. WebSocket Circuit Breaker
- **BVJ:** Failure isolation worth $10K MRR cascade prevention
- **Components:** Circuit breaker, fallback handler, recovery detector
- **Scenarios:** Failure detection, circuit states, automatic recovery

#### 25. Connection Pool Management
- **BVJ:** Resource efficiency worth $7K MRR cost optimization
- **Components:** Pool manager, connection reaper, metric tracker
- **Scenarios:** Pool sizing, idle cleanup, burst handling

#### 26. WebSocket Authentication Handshake
- **BVJ:** Secure connections worth $9K MRR security
- **Components:** Handshake validator, token verifier, upgrade handler
- **Scenarios:** Auth validation, token refresh, rejection handling

#### 27. Message Compression
- **BVJ:** Bandwidth savings worth $5K MRR cost reduction
- **Components:** Compressor, decompressor, algorithm selector
- **Scenarios:** Compression negotiation, fallback, performance

#### 28. Heartbeat Mechanism
- **BVJ:** Connection liveness worth $6K MRR reliability
- **Components:** Heartbeat sender, timeout detector, reconnect trigger
- **Scenarios:** Heartbeat intervals, timeout handling, adaptive timing

#### 29. WebSocket Load Balancing
- **BVJ:** Scalability worth $12K MRR growth support
- **Components:** Load balancer, sticky sessions, health checker
- **Scenarios:** Connection distribution, failover, session affinity

#### 30. Graceful WebSocket Shutdown
- **BVJ:** Clean shutdown worth $5K MRR data integrity
- **Components:** Shutdown coordinator, drain handler, cleanup manager
- **Scenarios:** Graceful close, message drain, state persistence

### Agent Orchestration (Tests 31-50) - $200K MRR Protection

#### 31. ✅ Supervisor-SubAgent Communication
- **BVJ:** Core AI functionality worth $30K MRR
- **Components:** Supervisor, sub-agents, tool dispatcher, state manager
- **Status:** Implemented

#### 32. Agent Tool Loading and Validation
- **BVJ:** Tool reliability worth $8K MRR feature availability
- **Components:** Tool loader, validator, registry, dependency resolver
- **Scenarios:** Dynamic loading, validation, dependency check, versioning

#### 33. Multi-Agent Workflow Coordination
- **BVJ:** Complex workflows worth $15K MRR advanced features
- **Components:** Workflow engine, agent coordinator, state machine
- **Scenarios:** Sequential flow, parallel execution, conditional routing

#### 34. Agent State Persistence
- **BVJ:** State recovery worth $10K MRR reliability
- **Components:** State serializer, storage manager, recovery handler
- **Scenarios:** State save, restore, migration, versioning

#### 35. Agent Error Propagation
- **BVJ:** Error visibility worth $7K MRR debugging efficiency
- **Components:** Error collector, propagator, aggregator, reporter
- **Scenarios:** Error capture, enrichment, routing, aggregation

#### 36. Agent Resource Allocation
- **BVJ:** Resource efficiency worth $9K MRR cost optimization
- **Components:** Resource manager, allocator, monitor, scaler
- **Scenarios:** Allocation strategy, limits, monitoring, scaling

#### 37. Agent Timeout and Cancellation
- **BVJ:** Responsiveness worth $6K MRR UX quality
- **Components:** Timeout manager, cancellation handler, cleanup coordinator
- **Scenarios:** Timeout detection, graceful cancellation, resource cleanup

#### 38. Agent Result Aggregation
- **BVJ:** Result quality worth $8K MRR output value
- **Components:** Result aggregator, merger, conflict resolver, formatter
- **Scenarios:** Multiple results, conflict resolution, formatting

#### 39. Agent Priority Queue
- **BVJ:** Fair scheduling worth $7K MRR performance
- **Components:** Priority queue, scheduler, executor, monitor
- **Scenarios:** Priority assignment, scheduling, starvation prevention

#### 40. Agent Fallback Strategies
- **BVJ:** Resilience worth $10K MRR availability
- **Components:** Fallback manager, strategy selector, recovery handler
- **Scenarios:** Primary failure, fallback selection, recovery

#### 41. Agent Metrics Collection
- **BVJ:** Observability worth $6K MRR operational excellence
- **Components:** Metric collector, aggregator, exporter, dashboard
- **Scenarios:** Metric collection, aggregation, export, alerting

#### 42. Agent Version Compatibility
- **BVJ:** Backward compatibility worth $8K MRR smooth upgrades
- **Components:** Version manager, compatibility checker, adapter
- **Scenarios:** Version detection, compatibility check, adaptation

#### 43. Agent Configuration Hot Reload
- **BVJ:** Dynamic config worth $5K MRR operational agility
- **Components:** Config watcher, reloader, validator, notifier
- **Scenarios:** Config change detection, validation, reload, notification

#### 44. Agent Dependency Resolution
- **BVJ:** Dependency management worth $7K MRR reliability
- **Components:** Dependency resolver, loader, validator, cache
- **Scenarios:** Resolution strategy, circular detection, caching

#### 45. Agent Audit Trail
- **BVJ:** Compliance worth $9K MRR audit requirements
- **Components:** Audit logger, storage, query engine, reporter
- **Scenarios:** Action logging, storage, query, reporting

#### 46. LLM Provider Failover
- **BVJ:** Provider redundancy worth $12K MRR availability
- **Components:** Provider selector, failover handler, health checker
- **Scenarios:** Primary failure, provider selection, recovery

#### 47. Agent Context Window Management
- **BVJ:** Token optimization worth $8K MRR cost efficiency
- **Components:** Context manager, trimmer, prioritizer, tracker
- **Scenarios:** Context sizing, trimming, priority, tracking

#### 48. Agent Cost Tracking
- **BVJ:** Cost visibility worth $10K MRR optimization
- **Components:** Cost tracker, calculator, aggregator, reporter
- **Scenarios:** Usage tracking, cost calculation, reporting, alerting

#### 49. Agent Quality Gate Integration
- **BVJ:** Output quality worth $11K MRR value delivery
- **Components:** Quality validator, gate enforcer, feedback handler
- **Scenarios:** Validation rules, enforcement, feedback, improvement

#### 50. Agent Caching Strategy
- **BVJ:** Performance worth $7K MRR efficiency
- **Components:** Cache manager, strategy selector, invalidator
- **Scenarios:** Cache strategy, hit/miss, invalidation, warming

### Database Coordination (Tests 51-65) - $90K MRR Protection

#### 51. PostgreSQL-ClickHouse Transaction Sync
- **BVJ:** Data consistency worth $10K MRR integrity
- **Components:** Transaction coordinator, sync manager, validator
- **Scenarios:** Dual write, consistency check, rollback coordination

#### 52. Database Connection Pool Exhaustion
- **BVJ:** Availability worth $7K MRR uptime
- **Components:** Pool monitor, circuit breaker, recovery handler
- **Scenarios:** Pool exhaustion, queuing, timeout, recovery

#### 53. Distributed Transaction Rollback
- **BVJ:** Atomicity worth $8K MRR data integrity
- **Components:** Transaction manager, rollback coordinator, state tracker
- **Scenarios:** Partial failure, rollback cascade, state recovery

#### 54. Database Migration Sequencing
- **BVJ:** Schema evolution worth $6K MRR deployment safety
- **Components:** Migration runner, sequencer, validator, rollback handler
- **Scenarios:** Sequential execution, dependency, validation, rollback

#### 55. Read Replica Lag Handling
- **BVJ:** Consistency worth $5K MRR data accuracy
- **Components:** Lag monitor, router, fallback handler
- **Scenarios:** Lag detection, routing decision, fallback to primary

#### 56. Database Failover
- **BVJ:** High availability worth $9K MRR uptime
- **Components:** Failover detector, switch coordinator, validator
- **Scenarios:** Failure detection, switchover, validation, notification

#### 57. Batch Insert Performance
- **BVJ:** Throughput worth $4K MRR efficiency
- **Components:** Batch builder, executor, monitor, optimizer
- **Scenarios:** Batch sizing, execution, monitoring, optimization

#### 58. Database Lock Contention
- **BVJ:** Performance worth $6K MRR responsiveness
- **Components:** Lock monitor, deadlock detector, resolver
- **Scenarios:** Lock detection, deadlock resolution, timeout handling

#### 59. Query Timeout Handling
- **BVJ:** Stability worth $5K MRR reliability
- **Components:** Timeout manager, query killer, cleanup handler
- **Scenarios:** Timeout detection, query termination, resource cleanup

#### 60. Database Cache Coherency
- **BVJ:** Consistency worth $7K MRR accuracy
- **Components:** Cache coordinator, invalidator, synchronizer
- **Scenarios:** Update detection, invalidation, synchronization

#### 61. Materialized View Refresh
- **BVJ:** Performance worth $4K MRR query speed
- **Components:** Refresh scheduler, executor, validator
- **Scenarios:** Scheduled refresh, incremental update, validation

#### 62. Database Backup Integration
- **BVJ:** Disaster recovery worth $8K MRR data protection
- **Components:** Backup scheduler, executor, validator, restorer
- **Scenarios:** Backup execution, validation, restore testing

#### 63. Cross-Database Foreign Keys
- **BVJ:** Referential integrity worth $5K MRR consistency
- **Components:** FK validator, consistency checker, repair handler
- **Scenarios:** FK validation, inconsistency detection, repair

#### 64. Database Connection Retry
- **BVJ:** Resilience worth $4K MRR availability
- **Components:** Retry manager, backoff calculator, circuit breaker
- **Scenarios:** Connection failure, retry strategy, circuit breaking

#### 65. Database Monitoring Integration
- **BVJ:** Observability worth $5K MRR operational excellence
- **Components:** Metric collector, alert manager, dashboard
- **Scenarios:** Metric collection, alerting, visualization

### Cache & State Management (Tests 66-75) - $60K MRR Protection

#### 66. Redis Cache Invalidation Cascade
- **BVJ:** Cache consistency worth $8K MRR data accuracy
- **Components:** Invalidation manager, cascade handler, notifier
- **Scenarios:** Single key, pattern-based, cascade logic, notification

#### 67. Cache Warming Strategy
- **BVJ:** Performance worth $5K MRR initial response time
- **Components:** Warmer, scheduler, priority manager, monitor
- **Scenarios:** Scheduled warming, priority-based, monitoring

#### 68. Cache Expiration Handling
- **BVJ:** Freshness worth $4K MRR data accuracy
- **Components:** TTL manager, expiration handler, refresh trigger
- **Scenarios:** TTL setting, expiration detection, refresh

#### 69. Distributed Cache Sync
- **BVJ:** Consistency worth $7K MRR multi-instance accuracy
- **Components:** Sync coordinator, conflict resolver, validator
- **Scenarios:** Multi-instance update, conflict resolution, validation

#### 70. Cache Memory Pressure
- **BVJ:** Stability worth $6K MRR availability
- **Components:** Memory monitor, eviction manager, alert handler
- **Scenarios:** Memory detection, eviction policy, alerting

#### 71. Cache Hit Rate Optimization
- **BVJ:** Efficiency worth $5K MRR cost optimization
- **Components:** Hit rate monitor, key analyzer, optimizer
- **Scenarios:** Hit rate tracking, analysis, optimization

#### 72. Session State Migration
- **BVJ:** Scalability worth $7K MRR seamless scaling
- **Components:** Migration coordinator, state mover, validator
- **Scenarios:** Node addition, state migration, validation

#### 73. Cache Corruption Recovery
- **BVJ:** Data integrity worth $6K MRR reliability
- **Components:** Corruption detector, recovery handler, rebuilder
- **Scenarios:** Detection, quarantine, rebuild, validation

#### 74. Cache Cluster Failover
- **BVJ:** High availability worth $8K MRR uptime
- **Components:** Cluster monitor, failover coordinator, validator
- **Scenarios:** Node failure, failover, recovery, validation

#### 75. Cache Performance Under Load
- **BVJ:** Scalability worth $5K MRR peak performance
- **Components:** Load generator, performance monitor, analyzer
- **Scenarios:** Load patterns, monitoring, analysis, optimization

### Performance & Scalability (Tests 76-85) - $80K MRR Protection

#### 76. Concurrent User Load
- **BVJ:** Scale support worth $12K MRR growth capacity
- **Components:** Load balancer, connection manager, resource monitor
- **Scenarios:** 1000+ users, resource usage, bottleneck detection

#### 77. Message Throughput
- **BVJ:** High volume worth $10K MRR enterprise capability
- **Components:** Message processor, queue manager, throughput monitor
- **Scenarios:** 10K msg/sec, queue management, backpressure

#### 78. Database Query Optimization
- **BVJ:** Query performance worth $7K MRR responsiveness
- **Components:** Query analyzer, optimizer, plan validator
- **Scenarios:** Slow query detection, optimization, validation

#### 79. Memory Leak Detection
- **BVJ:** Stability worth $8K MRR long-term reliability
- **Components:** Memory profiler, leak detector, alert manager
- **Scenarios:** Memory growth, leak detection, alerting

#### 80. CPU Utilization Patterns
- **BVJ:** Efficiency worth $6K MRR resource optimization
- **Components:** CPU monitor, pattern analyzer, optimizer
- **Scenarios:** Usage patterns, hotspot detection, optimization

#### 81. Network Latency Compensation
- **BVJ:** Global reach worth $9K MRR international users
- **Components:** Latency monitor, compensator, optimizer
- **Scenarios:** High latency detection, compensation, optimization

#### 82. Batch Processing Performance
- **BVJ:** Throughput worth $7K MRR bulk operations
- **Components:** Batch processor, performance monitor, optimizer
- **Scenarios:** Batch sizing, parallel processing, optimization

#### 83. Startup Time Optimization
- **BVJ:** Availability worth $8K MRR quick recovery
- **Components:** Startup profiler, optimizer, validator
- **Scenarios:** Cold start, warm start, optimization validation

#### 84. Resource Pool Sizing
- **BVJ:** Efficiency worth $6K MRR resource optimization
- **Components:** Pool monitor, size calculator, adjuster
- **Scenarios:** Pool sizing, adjustment, validation

#### 85. Garbage Collection Impact
- **BVJ:** Performance worth $7K MRR consistent latency
- **Components:** GC monitor, tuner, impact analyzer
- **Scenarios:** GC patterns, tuning, impact analysis

### Error Recovery & Resilience (Tests 86-95) - $70K MRR Protection

#### 86. Circuit Breaker Cascade
- **BVJ:** Failure isolation worth $10K MRR cascade prevention
- **Components:** Circuit manager, cascade detector, recovery handler
- **Scenarios:** Failure propagation, circuit coordination, recovery

#### 87. Retry Logic Validation
- **BVJ:** Resilience worth $6K MRR transient failure handling
- **Components:** Retry manager, backoff calculator, validator
- **Scenarios:** Retry strategy, backoff validation, success detection

#### 88. Error Aggregation
- **BVJ:** Visibility worth $5K MRR debugging efficiency
- **Components:** Error collector, aggregator, reporter, analyzer
- **Scenarios:** Collection, aggregation, reporting, analysis

#### 89. Graceful Degradation
- **BVJ:** Partial availability worth $8K MRR user retention
- **Components:** Feature toggle, degradation manager, notifier
- **Scenarios:** Feature detection, degradation, user notification

#### 90. Health Check Propagation
- **BVJ:** Monitoring worth $6K MRR operational awareness
- **Components:** Health aggregator, propagator, dashboard
- **Scenarios:** Check aggregation, propagation, visualization

#### 91. Timeout Cascade Prevention
- **BVJ:** Stability worth $7K MRR system resilience
- **Components:** Timeout coordinator, isolation handler, recovery
- **Scenarios:** Timeout detection, isolation, recovery

#### 92. Error Rate Limiting
- **BVJ:** Stability worth $5K MRR error storm prevention
- **Components:** Rate limiter, circuit breaker, alert manager
- **Scenarios:** Error rate detection, limiting, alerting

#### 93. Recovery Time Objective
- **BVJ:** Availability worth $9K MRR SLA compliance
- **Components:** RTO monitor, recovery coordinator, validator
- **Scenarios:** Failure detection, recovery execution, validation

#### 94. Failure Injection Testing
- **BVJ:** Resilience validation worth $8K MRR confidence
- **Components:** Chaos injector, impact monitor, validator
- **Scenarios:** Failure injection, impact assessment, recovery

#### 95. Emergency Shutdown
- **BVJ:** Damage control worth $7K MRR incident management
- **Components:** Kill switch, shutdown coordinator, state saver
- **Scenarios:** Trigger detection, coordinated shutdown, state preservation

### Business Critical Flows (Tests 96-100) - $100K MRR Protection

#### 96. ✅ Free-to-Paid Conversion Flow
- **BVJ:** Revenue generation worth $30K MRR growth
- **Components:** Subscription manager, payment processor, feature unlocker
- **Status:** Implemented

#### 97. Usage Metering Pipeline
- **BVJ:** Billing accuracy worth $25K MRR revenue integrity
- **Components:** Usage collector, aggregator, calculator, reporter
- **Scenarios:** Collection, aggregation, calculation, billing integration

#### 98. Payment Webhook Processing
- **BVJ:** Transaction handling worth $20K MRR payment reliability
- **Components:** Webhook receiver, validator, processor, notifier
- **Scenarios:** Receipt, validation, processing, notification

#### 99. Subscription Lifecycle
- **BVJ:** Retention worth $15K MRR customer lifecycle
- **Components:** Lifecycle manager, state machine, notifier
- **Scenarios:** Creation, upgrade, downgrade, cancellation, renewal

#### 100. Revenue Recognition
- **BVJ:** Financial accuracy worth $10K MRR compliance
- **Components:** Revenue calculator, recognition engine, reporter
- **Scenarios:** Calculation, recognition timing, reporting, audit

---

## Implementation Roadmap

### Phase 1: Critical Security & Revenue (Week 1)
- **Priority:** P0 tests protecting authentication, core AI, and revenue
- **Tests:** 1-15 (Auth), 31-35 (Core Agents), 96-100 (Revenue)
- **MRR Protected:** $280K

### Phase 2: System Stability (Week 2)
- **Priority:** P0/P1 tests for real-time and database reliability
- **Tests:** 16-30 (WebSocket), 51-65 (Database), 86-95 (Recovery)
- **MRR Protected:** $280K

### Phase 3: Performance & Scale (Week 3)
- **Priority:** P1/P2 tests for optimization and growth
- **Tests:** 36-50 (Advanced Agents), 66-75 (Cache), 76-85 (Performance)
- **MRR Protected:** $310K

## Testing Standards

### L2 Integration Test Requirements
1. **Real Internal Components:** Use actual services, no mocking internal dependencies
2. **Mock External Only:** Mock external APIs (payment gateways, LLM providers)
3. **In-Process Testing:** Components run in same process for L2
4. **Database:** Use TestContainers or in-memory databases
5. **Architecture Compliance:** 450-line files, 25-line functions

### Business Value Justification Format
Each test must include:
- **Segment:** Which customer tier benefits
- **Business Goal:** Strategic objective
- **Value Impact:** Quantified MRR or cost impact
- **Strategic Impact:** Long-term business benefit

## Execution Commands

```bash
# Run all L2 integration tests
python -m pytest app/tests/integration/critical_paths/ -v

# Run specific category
python -m pytest app/tests/integration/critical_paths/ -k "auth" -v

# Run with coverage
python -m pytest app/tests/integration/critical_paths/ --cov=app --cov-report=html

# Run in parallel
python -m pytest app/tests/integration/critical_paths/ -n auto
```

## Success Metrics

- **Coverage Target:** Achieve 60% integration test coverage (up from 13.5%)
- **Test Execution Time:** L2 tests complete in <10 minutes
- **Reliability:** <1% test flakiness rate
- **Business Impact:** $870K MRR protected through comprehensive testing

---

*This document serves as the authoritative source for L2 integration test planning and implementation tracking.*