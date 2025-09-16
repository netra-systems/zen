# 🚨 TEST PLAN: Issue #1278 VPC Connector Infrastructure Failure

**Date:** 2025-09-16
**Priority:** P0 EMERGENCY
**Business Impact:** $500K+ ARR - Complete Golden Path failure
**Issue Status:** Infrastructure connectivity failure preventing Cloud Run → Cloud SQL/Redis access

## Executive Summary

This test plan provides comprehensive test coverage to reproduce and validate fixes for Issue #1278 VPC connector capacity constraints that cause staging infrastructure outages. Tests are designed to **FAIL INITIALLY** to prove the issue exists, then **PASS AFTER FIXES** to validate resolution.

**Root Cause:** VPC Connector `staging-connector` capacity constraints preventing Cloud Run services from accessing Cloud SQL/Redis, causing 503 errors and golden path failure.

## Test Categories & Strategy

### 1. Unit Tests (No Docker Required)
**Purpose:** Test VPC connector monitoring and timeout logic
**Environment:** Local development
**Infrastructure:** None required
**Expected Duration:** 5-10 minutes

### 2. Integration Tests (Non-Docker)
**Purpose:** Test infrastructure connectivity patterns without Docker
**Environment:** Local with remote staging GCP resources
**Infrastructure:** Real GCP staging services
**Expected Duration:** 15-30 minutes

### 3. E2E Staging GCP Tests
**Purpose:** Test complete infrastructure connectivity in real staging environment
**Environment:** GCP staging deployment
**Infrastructure:** Full staging stack
**Expected Duration:** 30-60 minutes

## Test Plan Details

### Phase 1: Unit Tests - VPC Connector Monitoring Logic

#### 1.1 VPC Connector State Management Tests
**File:** `tests/unit/infrastructure/test_vpc_connector_state_management.py`

```python
class TestVPCConnectorStateManagement:
    """Test VPC connector state transitions and monitoring logic."""

    def test_normal_to_capacity_pressure_transition(self):
        """Test state transition when capacity pressure detected."""
        # Should FAIL initially if monitoring not implemented
        # Should PASS after monitoring logic added

    def test_capacity_pressure_timeout_adjustments(self):
        """Test automatic timeout adjustments during capacity pressure."""
        # Should FAIL initially if dynamic timeouts not implemented
        # Should PASS after dynamic timeout logic added

    def test_overloaded_state_emergency_bypass(self):
        """Test emergency bypass activation during VPC overload."""
        # Should FAIL initially if emergency bypass not working
        # Should PASS after emergency bypass fixes
```

#### 1.2 Database Timeout Configuration Tests
**File:** `tests/unit/infrastructure/test_database_timeout_config.py`

```python
class TestDatabaseTimeoutConfig:
    """Test database timeout configuration under VPC constraints."""

    def test_vpc_capacity_pressure_timeout_scaling(self):
        """Test timeout scaling based on VPC capacity metrics."""
        # Should FAIL initially if scaling not implemented
        # Should PASS after capacity-aware timeout scaling

    def test_600s_timeout_requirement_compliance(self):
        """Test compliance with Issue #1278 600s timeout requirement."""
        # Should PASS - validate current 600s timeout setting

    def test_connection_retry_backoff_under_vpc_pressure(self):
        """Test exponential backoff during VPC connector pressure."""
        # Should FAIL initially if backoff not VPC-aware
        # Should PASS after VPC-aware retry logic
```

### Phase 2: Integration Tests - Real Infrastructure Connectivity

#### 2.1 VPC Connector Capacity Stress Tests
**File:** `tests/integration/infrastructure/test_vpc_connector_capacity_stress.py`

```python
class TestVPCConnectorCapacityStress:
    """Integration tests reproducing VPC connector capacity issues."""

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_concurrent_cloud_sql_connections_via_vpc(self):
        """
        CRITICAL TEST - MUST FAIL INITIALLY

        Test concurrent Cloud SQL connections through VPC connector.
        Reproduces Issue #1278 capacity constraints.

        Expected: FAIL initially (capacity exceeded)
        Expected: PASS after VPC scaling
        """
        concurrent_connections = 15  # Above current VPC capacity
        # Test should timeout/fail initially
        # Should succeed after VPC connector scaling

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_redis_connectivity_under_vpc_load(self):
        """
        Test Redis connectivity through VPC connector under load.

        Expected: FAIL initially (VPC capacity bottleneck)
        Expected: PASS after infrastructure optimization
        """
        # Simulate multiple services connecting to Redis via VPC
        # Should show degraded performance initially

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_database_connection_timeout_scenarios(self):
        """
        Test database connection timeouts under VPC capacity pressure.

        Expected: FAIL initially (connections timeout <600s)
        Expected: PASS after timeout configuration fixes
        """
        # Test connections should complete within 600s timeout
        # Should fail initially due to VPC bottlenecks
```

#### 2.2 Service Startup Sequence Tests
**File:** `tests/integration/infrastructure/test_startup_sequence_vpc_dependency.py`

```python
class TestStartupSequenceVPCDependency:
    """Test service startup phases under VPC connectivity constraints."""

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_deterministic_startup_phase_3_database_connectivity(self):
        """
        Test Phase 3 database connectivity during deterministic startup.

        Expected: FAIL initially (Phase 3 hangs due to VPC issues)
        Expected: PASS after VPC capacity fixes
        """
        # Reproduce startup hanging at Phase 3 due to database connectivity

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_startup_phases_5_6_skipping_issue(self):
        """
        Test Phases 5-6 being skipped due to VPC connectivity failures.

        Expected: FAIL initially (phases skipped, 503 errors)
        Expected: PASS after startup sequence resilience fixes
        """
        # Validate that emergency bypass doesn't skip critical phases
```

#### 2.3 SSL Certificate and Domain Configuration Tests
**File:** `tests/integration/infrastructure/test_ssl_domain_config_vpc_pressure.py`

```python
class TestSSLDomainConfigVPCPressure:
    """Test SSL certificate validation under VPC connector pressure."""

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_netrasystems_ai_ssl_validation_under_load(self):
        """
        Test *.netrasystems.ai SSL certificate validation under VPC load.

        Expected: FAIL initially (SSL validation degrades under VPC pressure)
        Expected: PASS after VPC capacity optimization
        """
        domains_to_test = [
            'staging.netrasystems.ai',      # Should work
            'api-staging.netrasystems.ai',  # Should work
        ]
        # Test SSL validation performance under VPC capacity pressure

    @pytest.mark.integration
    @pytest.mark.staging_gcp
    async def test_deprecated_staging_subdomain_ssl_failures(self):
        """
        Test deprecated *.staging.netrasystems.ai SSL certificate failures.

        Expected: FAIL (as expected - these should fail)
        Purpose: Validate deprecated domains consistently fail
        """
        deprecated_domains = [
            'backend.staging.netrasystems.ai',  # Should fail
            'ws.staging.netrasystems.ai',       # Should fail
        ]
        # These should fail consistently (expected behavior)
```

### Phase 3: E2E Staging GCP Tests - Complete Infrastructure Validation

#### 3.1 Golden Path E2E Tests with VPC Infrastructure
**File:** `tests/e2e/staging/test_golden_path_vpc_infrastructure.py`

```python
class TestGoldenPathVPCInfrastructure:
    """E2E tests validating complete Golden Path under VPC constraints."""

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    @pytest.mark.mission_critical
    async def test_complete_user_journey_vpc_resilience(self):
        """
        MISSION CRITICAL - Complete user journey test with VPC infrastructure.

        Expected: FAIL initially (503 errors, connection failures)
        Expected: PASS after comprehensive VPC infrastructure fixes

        Tests: Login → WebSocket → Agent Execution → Database Persistence
        """
        # Test complete user flow from frontend through all infrastructure
        # Should fail at WebSocket/database connectivity initially

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_concurrent_user_sessions_vpc_load(self):
        """
        Test multiple concurrent user sessions under VPC load.

        Expected: FAIL initially (system degradation under load)
        Expected: PASS after VPC capacity scaling
        """
        concurrent_users = 10
        # Simulate real user load through complete stack

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_service_health_endpoints_vpc_dependency(self):
        """
        Test service health endpoints under VPC connectivity constraints.

        Expected: FAIL initially (health checks return 503)
        Expected: PASS after infrastructure health improvements
        """
        health_endpoints = [
            'https://staging.netrasystems.ai/health',
            'https://staging.netrasystems.ai/auth/health',
        ]
        # Should return 200 OK after infrastructure fixes
```

#### 3.2 Infrastructure Resilience and Recovery Tests
**File:** `tests/e2e/staging/test_infrastructure_resilience_recovery.py`

```python
class TestInfrastructureResilienceRecovery:
    """Test infrastructure resilience patterns and recovery mechanisms."""

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_vpc_connector_auto_scaling_behavior(self):
        """
        Test VPC connector automatic scaling under load.

        Expected: FAIL initially (no auto-scaling implemented)
        Expected: PASS after auto-scaling infrastructure added
        """
        # Test infrastructure responds to capacity pressure

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_graceful_degradation_during_vpc_outage(self):
        """
        Test graceful degradation when VPC connector unavailable.

        Expected: FAIL initially (complete service failure)
        Expected: PASS after graceful degradation implementation
        """
        # Test services continue with degraded functionality

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_infrastructure_monitoring_and_alerting(self):
        """
        Test infrastructure monitoring detects VPC capacity issues.

        Expected: FAIL initially (no VPC capacity monitoring)
        Expected: PASS after comprehensive monitoring implementation
        """
        # Test monitoring systems detect and alert on VPC capacity issues
```

## Test Execution Strategy

### Test Execution Order

1. **Unit Tests First** (5-10 minutes)
   ```bash
   python -m pytest tests/unit/infrastructure/ -v --tb=short
   ```

2. **Integration Tests** (15-30 minutes)
   ```bash
   python -m pytest tests/integration/infrastructure/ -v -m "staging_gcp" --tb=short
   ```

3. **E2E Staging Tests** (30-60 minutes)
   ```bash
   python -m pytest tests/e2e/staging/ -v -m "staging_gcp" --tb=short
   ```

### Expected Failure Patterns (Before Fixes)

#### Initial Test Results - Proving Issue Exists
- **VPC Connector Capacity:** Tests timeout after 15+ concurrent connections
- **Database Connectivity:** Connections fail or timeout before 600s limit
- **Service Startup:** Phases 5-6 skipped, services return 503
- **SSL Validation:** Certificate validation degrades under VPC pressure
- **Golden Path:** Complete user journey fails with infrastructure errors

#### Success Criteria (After Fixes Applied)
- **VPC Connector Scaling:** Handles 20+ concurrent connections reliably
- **Database Timeout Compliance:** All connections complete within 600s
- **Startup Sequence:** All 7 phases complete successfully
- **SSL Certificate Performance:** Validation remains fast under load
- **Golden Path Success:** Complete user journey works end-to-end

### Test Environment Configuration

#### Staging GCP Test Configuration
```yaml
environment: staging
gcp_project: netra-staging
vpc_connector: staging-connector
domains:
  frontend: staging.netrasystems.ai
  backend: staging.netrasystems.ai
  websocket: api-staging.netrasystems.ai
database_timeout: 600s
redis_timeout: 30s
ssl_validation_timeout: 10s
```

#### Test Infrastructure Requirements
- **GCP Access:** Service account with staging environment access
- **Network Access:** Ability to reach staging.netrasystems.ai domains
- **Monitoring Access:** GCP logging and monitoring for validation
- **SSL Testing:** Certificate validation capabilities

## Validation Metrics

### Infrastructure Performance Benchmarks
- **VPC Connector Throughput:** >300 Mbps sustained
- **Database Connection Time:** <10s average, <600s maximum
- **Redis Connection Time:** <5s average, <30s maximum
- **SSL Validation Time:** <3s average, <10s maximum
- **Service Startup Time:** <60s total for all 7 phases

### Business Impact Metrics
- **Service Availability:** >99.5% uptime in staging
- **Golden Path Success Rate:** >95% end-to-end completion
- **User Experience:** <2s WebSocket connection time
- **Error Rate:** <1% infrastructure-related failures

## Test Reporting and Monitoring

### Test Result Analysis
1. **Failure Reproduction Validation:** Confirm tests fail initially as expected
2. **Fix Validation:** Tests pass after infrastructure improvements
3. **Performance Regression:** Monitor for performance degradation over time
4. **Business Impact Tracking:** Measure impact on user experience metrics

### Continuous Monitoring Integration
- **Test Suite Integration:** Add to CI/CD pipeline as infrastructure validation
- **Staging Environment Health:** Regular execution to detect capacity issues
- **Performance Benchmarking:** Track performance trends over time
- **Alert Integration:** Automated alerting when tests detect infrastructure issues

## Success Criteria Summary

### Immediate Success (Test Failures Reproduced)
- [ ] VPC connector capacity constraints reproduced in tests
- [ ] Database connectivity timeouts demonstrated under load
- [ ] Service startup failures validated with infrastructure pressure
- [ ] SSL certificate validation degradation measured

### Long-term Success (Infrastructure Fixes Validated)
- [ ] VPC connector capacity scaled to handle required load
- [ ] Database connectivity stable within 600s timeout requirements
- [ ] Service startup sequence completes all 7 phases reliably
- [ ] Golden Path user journey works end-to-end in staging
- [ ] Infrastructure monitoring detects and alerts on capacity issues

---

**Test Plan Status:** Ready for implementation
**Expected Initial Results:** FAIL (proving Issue #1278 exists)
**Expected Post-Fix Results:** PASS (validating infrastructure resolution)
**Business Impact:** $500K+ ARR protection through infrastructure reliability