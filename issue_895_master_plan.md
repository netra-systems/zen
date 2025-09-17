# MASTER PLAN: WebSocket Service Availability Detection (Issue #895)

## SCOPE DEFINITION & DEFINITION OF DONE

### What Constitutes "Service Availability"
**Critical Services:**
- Backend Service (port 8000/8002) - REQUIRED for WebSocket functionality
- Auth Service (port 8081) - REQUIRED for authentication
- Database Services (PostgreSQL, Redis) - REQUIRED for persistence
- ClickHouse - OPTIONAL for analytics

**Optional Services:**
- External APIs (OpenAI, Anthropic) - DEGRADE GRACEFULLY
- Analytics Service - DEGRADE GRACEFULLY

### Expected Behavior When Services Are Unavailable
**Critical Service Unavailable:**
- Clear error message to user explaining service dependency
- WebSocket connection gracefully rejects with informative 1011 error code
- Log detailed service dependency failure for operations team
- No silent failures or hanging connections

**Optional Service Unavailable:**
- Continue WebSocket operation with reduced functionality
- Log warning about degraded capability
- User receives notification about limited features
- Full recovery when service becomes available

## RESOLUTION APPROACHES

### A) Infrastructure/Config Approach
**Health Check Infrastructure:**
- Implement `/health/dependencies` endpoint checking all service dependencies
- Add startup validation ensuring critical services are reachable
- Configure proper timeouts (database: 600s, services: 30s)
- VPC connector validation for GCP staging environment

**Configuration:**
```yaml
# Service dependency timeouts
DEPENDENCY_CHECK_TIMEOUT_CRITICAL: 30
DEPENDENCY_CHECK_TIMEOUT_OPTIONAL: 10
DEPENDENCY_CHECK_RETRY_COUNT: 3
GRACEFUL_DEGRADATION_ENABLED: true
```

### B) Code Implementation
**Service Availability Detection:**
- Extend existing `tests/e2e/service_availability.py` for runtime use
- Create `ServiceAvailabilityManager` in WebSocket core
- Add graceful degradation patterns in agent execution
- Implement circuit breaker pattern for external services

**WebSocket Integration:**
- Pre-connection service validation
- Informative 1011 error responses with service status
- Real-time service recovery detection
- Graceful degradation messaging to users

### C) Documentation Updates
**Architecture Documentation:**
- Update `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md` with service dependency handling
- Document graceful degradation patterns in `@websocket_agent_integration_critical.xml`
- Create service dependency matrix in architecture docs

### D) Test Strategy
**Unit Tests:**
- Service availability detection logic
- Circuit breaker functionality
- Graceful degradation message formatting
- Mock service failure scenarios

**Integration Tests (Non-Docker):**
- Service dependency validation during WebSocket handshake
- Recovery behavior when services come online
- Partial functionality validation with optional services down

**E2E Tests (GCP Staging):**
- Full service failure and recovery scenarios
- User experience validation during service outages
- 1011 error handling and recovery messaging
- Performance impact of service availability checks

## IMPLEMENTATION PLAN

### Phase 1: Service Dependency Identification (Week 1)
**Goal:** Map all WebSocket flow dependencies
- [ ] Audit WebSocket startup sequence for service calls
- [ ] Identify critical vs optional service dependencies
- [ ] Document current failure modes and error codes
- [ ] Create service dependency matrix

**Deliverables:**
- Service dependency map
- Current failure mode analysis
- Updated architecture documentation

### Phase 2: Health Check Mechanism (Week 2)
**Goal:** Implement comprehensive service availability detection
- [ ] Create `ServiceAvailabilityManager` class
- [ ] Implement health check endpoints for all services
- [ ] Add circuit breaker pattern for external services
- [ ] Create timeout and retry configuration

**Deliverables:**
- Service availability detection system
- Health check endpoints
- Circuit breaker implementation
- Configuration framework

### Phase 3: Graceful Degradation Logic (Week 3)
**Goal:** Add graceful degradation and informative error handling
- [ ] Implement WebSocket pre-connection validation
- [ ] Add informative 1011 error responses
- [ ] Create graceful degradation messaging
- [ ] Implement real-time service recovery detection

**Deliverables:**
- WebSocket service validation layer
- Graceful degradation patterns
- User-friendly error messaging
- Service recovery detection

### Phase 4: Test Partial Functionality Scenarios (Week 4)
**Goal:** Validate system behavior under various service availability scenarios
- [ ] Create comprehensive test suite for service failures
- [ ] Validate graceful degradation user experience
- [ ] Test service recovery scenarios
- [ ] Performance testing under partial service availability

**Deliverables:**
- Comprehensive test suite
- Performance validation results
- User experience validation
- Documentation of supported scenarios

### Phase 5: Monitoring and Documentation (Week 5)
**Goal:** Complete monitoring, alerting, and documentation
- [ ] Add service availability metrics and alerting
- [ ] Update all architecture documentation
- [ ] Create operational runbooks for service failures
- [ ] Validate staging deployment with service failure simulation

**Deliverables:**
- Monitoring and alerting setup
- Complete documentation updates
- Operational runbooks
- Staging validation results

## TEST STRATEGY (Per TEST_CREATION_GUIDE.md)

### Unit Tests
**Target:** `tests/unit/test_service_availability_detection.py`
```python
class TestServiceAvailabilityDetection:
    def test_critical_service_unavailable_blocks_websocket(self):
        # Test that WebSocket rejects connection when critical services down

    def test_optional_service_unavailable_allows_degraded_operation(self):
        # Test that WebSocket continues with reduced functionality

    def test_service_recovery_detection(self):
        # Test that system detects when failed services come back online
```

### Integration Tests (Non-Docker)
**Target:** `tests/integration/test_websocket_service_dependencies.py`
```python
class TestWebSocketServiceDependencies:
    async def test_websocket_handshake_with_auth_service_down(self):
        # Validate behavior when auth service is unavailable

    async def test_websocket_graceful_degradation_messaging(self):
        # Test user messaging during service degradation

    async def test_service_recovery_websocket_functionality(self):
        # Test full functionality restoration when services recover
```

### E2E Tests (GCP Staging)
**Target:** `tests/e2e/test_service_availability_golden_path.py`
```python
class TestServiceAvailabilityGoldenPath:
    async def test_complete_service_failure_recovery_cycle(self):
        # Test full cycle: service failure -> graceful degradation -> recovery

    async def test_user_experience_during_partial_service_outage(self):
        # Validate user experience and messaging during outages

    async def test_1011_error_handling_and_recovery(self):
        # Reproduce 1011 errors and validate recovery mechanisms
```

## RISK ASSESSMENT

### Technical Risks
**HIGH RISK:**
- **Race Conditions:** Service availability checks during high concurrency
  - *Mitigation:* Circuit breaker pattern with proper synchronization

- **Performance Impact:** Health checks adding latency to WebSocket connections
  - *Mitigation:* Cached health status with TTL, async health checks

**MEDIUM RISK:**
- **False Positives:** Services appearing unavailable due to network blips
  - *Mitigation:* Retry logic with exponential backoff

- **Cascading Failures:** Health check failures causing additional service load
  - *Mitigation:* Throttled health checks, independent monitoring

### Business Risks
**HIGH RISK:**
- **User Experience Impact:** Poor error messaging during service outages
  - *Mitigation:* User-friendly error messages, proactive communication

**MEDIUM RISK:**
- **Revenue Impact:** Users unable to access chat functionality during outages
  - *Mitigation:* Graceful degradation, rapid recovery procedures

### Operational Risks
**MEDIUM RISK:**
- **Monitoring Overhead:** Additional complexity in service monitoring
  - *Mitigation:* Automated monitoring, clear operational procedures

- **Backward Compatibility:** Changes affecting existing WebSocket clients
  - *Mitigation:* Feature flags, phased rollout, comprehensive testing

## SUCCESS METRICS

### Technical Metrics
- [ ] 99.9% reduction in silent WebSocket failures
- [ ] <500ms additional latency for service availability checks
- [ ] 100% test coverage for service failure scenarios
- [ ] Zero 1011 errors without informative error messages

### Business Metrics
- [ ] Improved user satisfaction during service outages
- [ ] Reduced support tickets related to WebSocket connection issues
- [ ] Faster mean time to recovery (MTTR) for service outages
- [ ] Maintained chat functionality availability >99.5%

### Operational Metrics
- [ ] Clear service dependency visibility in monitoring
- [ ] Automated alerting for service dependency failures
- [ ] Documented procedures for service outage scenarios
- [ ] <5 minute detection time for critical service failures

## IMPLEMENTATION CHECKLIST

### Pre-Implementation
- [ ] Review existing service availability code in `tests/e2e/service_availability.py`
- [ ] Analyze current WebSocket failure modes and error codes
- [ ] Validate test strategy with TEST_CREATION_GUIDE.md requirements
- [ ] Ensure SSOT compliance with architecture patterns

### During Implementation
- [ ] Follow Definition of Done checklist for WebSocket module
- [ ] Maintain real services requirement (no mocks in integration/E2E tests)
- [ ] Update MASTER_WIP_STATUS.md with progress
- [ ] Validate against GOLDEN_PATH_USER_FLOW_COMPLETE.md requirements

### Post-Implementation
- [ ] Run comprehensive test suite: `python tests/unified_test_runner.py --real-services`
- [ ] Validate WebSocket events: `python tests/mission_critical/test_websocket_agent_events_suite.py`
- [ ] Update architecture compliance: `python scripts/check_architecture_compliance.py`
- [ ] Document learnings in `SPEC/learnings/` directory

---

**Next Steps:**
1. Begin Phase 1 service dependency mapping
2. Create detailed technical design document
3. Set up development environment for service failure simulation
4. Begin unit test implementation following TDD approach

**Business Value Justification:**
- **Segment:** Enterprise/Platform
- **Goal:** Stability and user experience improvement
- **Value Impact:** Eliminates silent failures, improves chat reliability (90% of platform value)
- **Revenue Impact:** Protects $500K+ ARR by ensuring reliable WebSocket functionality

*This plan addresses the critical WebSocket 1011 errors identified in issues #878 and #891, ensuring robust service availability detection with graceful degradation for Netra Apex's core chat functionality.*