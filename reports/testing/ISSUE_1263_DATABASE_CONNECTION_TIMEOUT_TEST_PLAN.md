# Test Plan: Issue #1263 - Database Connection Timeout

**Issue**: Database Connection Timeout causing DeterministicStartupError
**Root Cause**: VPC configuration change (commit 2acf46c8a) disrupting Cloud SQL connectivity
**Objective**: Design comprehensive test plan to reproduce and validate database connection timeout issue
**Created**: 2025-09-15
**Priority**: P0 Critical - Affects Golden Path startup ($500K+ ARR)

## Executive Summary

### Root Cause Analysis Summary
Based on Five Whys analysis:
- **Primary**: VPC egress configuration changed from `private-ranges-only` to `all-traffic`
- **Secondary**: Cloud SQL connection routing through VPC connector changed behavior
- **Impact**: 8.0-second timeout vs expected <2.0s connection time
- **Result**: `DeterministicStartupError` preventing system startup

### Test Strategy
1. **Unit Tests**: Configuration validation without Docker overhead
2. **Integration Tests**: Cloud SQL connectivity with real GCP services
3. **Staging GCP Tests**: Full end-to-end startup sequence reproduction
4. **Performance Tests**: Timeout behavior validation and measurement

## 1. Unit Tests (No Docker Required)

### 1.1 Database Connection Pool Configuration Tests
**Location**: `netra_backend/tests/unit/db/test_issue_1263_connection_pool_config_unit.py`

```python
"""
Unit tests for database connection pool configuration affecting Issue #1263.

These tests validate connection pool settings that may contribute to 8.0s timeout:
- Connection pool size and timeout settings
- SQLAlchemy engine configuration
- AsyncAdaptedQueuePool vs StaticPool behavior
- Connection string validation for Cloud SQL proxy
"""

class TestDatabaseConnectionPoolConfigurationUnit(SSotAsyncTestCase):
    """Test connection pool configuration that may cause 8.0s timeout."""

    async def test_connection_pool_timeout_configuration(self):
        """Test Issue #1263: Connection pool timeout settings."""
        # Test various pool timeout configurations
        # Expected to FAIL with current settings causing 8.0s timeout

    async def test_cloud_sql_connection_string_format(self):
        """Test Cloud SQL connection string format validation."""
        # Validate /cloudsql/ socket path format
        # Test Unix socket vs TCP connection behavior

    async def test_vpc_egress_routing_configuration(self):
        """Test VPC egress routing affects connection behavior."""
        # Mock different VPC egress settings
        # Validate connection path routing decisions
```

### 1.2 Environment Variable Parsing Tests
**Location**: `netra_backend/tests/unit/config/test_issue_1263_postgres_env_parsing_unit.py`

```python
"""
Unit tests for POSTGRES_* environment variable parsing in Issue #1263.

These tests validate environment variable parsing that leads to connection timeout:
- POSTGRES_HOST validation (Cloud SQL instance name vs socket path)
- Secret Manager placeholder resolution
- DatabaseURLBuilder integration with VPC configuration
"""

class TestPostgresEnvironmentParsingUnit(SSotAsyncTestCase):
    """Test POSTGRES_* environment parsing contributing to timeout."""

    async def test_postgres_host_cloud_sql_format_validation(self):
        """Test Issue #1263: POSTGRES_HOST Cloud SQL format validation."""
        # Test various Cloud SQL host formats
        # /cloudsql/project:region:instance vs TCP format

    async def test_secret_manager_placeholder_resolution(self):
        """Test Secret Manager placeholder vs actual value resolution."""
        # Mock Secret Manager placeholder resolution
        # Test timeout behavior with unresolved placeholders

    async def test_database_url_builder_vpc_integration(self):
        """Test DatabaseURLBuilder VPC connector integration."""
        # Test URL building with different VPC configurations
        # Expected to identify timeout-causing configuration
```

### 1.3 SSL Certificate Configuration Tests
**Location**: `netra_backend/tests/unit/db/test_issue_1263_ssl_config_unit.py`

```python
"""
Unit tests for SSL certificate configuration in Issue #1263.

SSL certificate validation may contribute to connection timeout:
- SSL mode configuration for Cloud SQL
- Certificate validation timeout behavior
- SSL handshake timeout settings
"""

class TestSSLCertificateConfigurationUnit(SSotAsyncTestCase):
    """Test SSL configuration contributing to 8.0s timeout."""

    async def test_cloud_sql_ssl_mode_configuration(self):
        """Test Issue #1263: Cloud SQL SSL mode timeout behavior."""
        # Test different SSL modes: require, prefer, disable
        # Identify SSL handshake timeout contribution

    async def test_ssl_certificate_validation_timeout(self):
        """Test SSL certificate validation timeout behavior."""
        # Mock SSL certificate validation delays
        # Test timeout accumulation during validation
```

## 2. Integration Tests (Non-Docker, Local/GCP)

### 2.1 Cloud SQL Connectivity Tests
**Location**: `tests/integration/database/test_issue_1263_cloud_sql_connectivity_integration.py`

```python
"""
Integration tests for Cloud SQL connectivity in Issue #1263.

These tests use REAL GCP services to reproduce the 8.0s timeout:
- Direct Cloud SQL connection testing
- VPC connector routing validation
- Connection timeout measurement and comparison
"""

class TestCloudSQLConnectivityIntegration(SSotAsyncTestCase):
    """Integration tests for Cloud SQL connection timeout reproduction."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cloud_sql_connection_timeout_measurement(self):
        """Test Issue #1263: Measure actual Cloud SQL connection timeout."""
        # Connect to real staging Cloud SQL instance
        # Measure connection time with different configurations
        # EXPECTED TO FAIL: 8.0s timeout vs <2.0s expected

    @pytest.mark.integration
    async def test_vpc_connector_routing_validation(self):
        """Test VPC connector routing affecting connection time."""
        # Test connection routing through VPC connector
        # Compare private-ranges-only vs all-traffic egress
        # Measure routing impact on connection latency

    @pytest.mark.integration
    async def test_secret_manager_resolution_performance(self):
        """Test Secret Manager placeholder resolution performance."""
        # Measure Secret Manager API call latency
        # Test impact on overall connection timeout
```

### 2.2 VPC Routing Validation Tests
**Location**: `tests/integration/gcp/test_issue_1263_vpc_routing_validation_integration.py`

```python
"""
Integration tests for VPC routing configuration in Issue #1263.

These tests validate VPC connector behavior changes:
- VPC egress routing path validation
- Network latency measurement through VPC
- Cloud SQL proxy connection path testing
"""

class TestVPCRoutingValidationIntegration(SSotAsyncTestCase):
    """Test VPC routing configuration impact on Cloud SQL connectivity."""

    @pytest.mark.integration
    @pytest.mark.gcp
    async def test_vpc_egress_routing_path_validation(self):
        """Test Issue #1263: VPC egress routing path changes."""
        # Test network path from Cloud Run to Cloud SQL
        # Compare routing with different VPC egress settings
        # EXPECTED TO IDENTIFY: Routing change causing timeout

    @pytest.mark.integration
    async def test_cloud_sql_proxy_connection_path(self):
        """Test Cloud SQL proxy connection path through VPC."""
        # Test Unix socket vs TCP connection paths
        # Measure latency differences through VPC connector
```

### 2.3 Database Initialization Sequence Tests
**Location**: `tests/integration/startup/test_issue_1263_db_initialization_integration.py`

```python
"""
Integration tests for database initialization sequence in Issue #1263.

These tests reproduce the startup sequence leading to timeout:
- Database session factory initialization
- Connection pool creation timing
- Startup validation timeout reproduction
"""

class TestDatabaseInitializationIntegration(SSotAsyncTestCase):
    """Test database initialization sequence causing DeterministicStartupError."""

    @pytest.mark.integration
    async def test_database_session_factory_initialization_timeout(self):
        """Test Issue #1263: Database session factory initialization timeout."""
        # Reproduce startup sequence with timing measurement
        # EXPECTED TO FAIL: DeterministicStartupError after 8.0s

    @pytest.mark.integration
    async def test_connection_pool_creation_timing(self):
        """Test connection pool creation timing contribution to timeout."""
        # Measure connection pool initialization time
        # Test impact of pool size and timeout settings
```

## 3. Staging GCP Tests (E2E)

### 3.1 Full Startup Sequence Tests
**Location**: `tests/e2e/staging/test_issue_1263_startup_timeout_e2e.py`

```python
"""
E2E tests for full startup sequence timeout in Issue #1263.

These tests reproduce the complete startup failure in staging environment:
- DeterministicStartupError reproduction
- Full service startup timing measurement
- Golden Path dependency validation
"""

class TestStartupSequenceTimeoutE2E(SSotAsyncTestCase):
    """E2E tests for startup sequence timeout causing DeterministicStartupError."""

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_deterministic_startup_error_reproduction(self):
        """Test Issue #1263: Reproduce DeterministicStartupError in staging."""
        # Full startup sequence in staging environment
        # EXPECTED TO FAIL: DeterministicStartupError after timeout

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_startup_phase_timing_measurement(self):
        """Test startup phase timing to identify timeout bottleneck."""
        # Measure each startup phase timing
        # Identify which phase contributes to 8.0s timeout
```

### 3.2 Golden Path Database Dependency Tests
**Location**: `tests/e2e/staging/test_issue_1263_golden_path_db_dependency_e2e.py`

```python
"""
E2E tests for Golden Path database dependency in Issue #1263.

These tests validate database dependency impact on Golden Path:
- Complete user flow database connectivity
- WebSocket agent execution database requirements
- $500K+ ARR functionality validation
"""

class TestGoldenPathDatabaseDependencyE2E(SSotAsyncTestCase):
    """E2E tests for Golden Path database connectivity requirements."""

    @pytest.mark.e2e
    @pytest.mark.golden_path
    async def test_golden_path_database_connectivity_requirement(self):
        """Test Issue #1263: Golden Path requires database connectivity."""
        # Test complete user journey with database dependency
        # EXPECTED TO FAIL: Golden Path broken by database timeout
```

## 4. Performance and Timeout Behavior Tests

### 4.1 Timeout Behavior Validation Tests
**Location**: `tests/performance/test_issue_1263_timeout_behavior_validation.py`

```python
"""
Performance tests for timeout behavior validation in Issue #1263.

These tests validate timeout configuration and behavior:
- 8.0s timeout vs expected <2.0s measurement
- Connection retry behavior validation
- Timeout escalation pattern testing
"""

class TestTimeoutBehaviorValidation(SSotAsyncTestCase):
    """Performance tests for connection timeout behavior."""

    @pytest.mark.performance
    async def test_connection_timeout_measurement_accuracy(self):
        """Test Issue #1263: Accurate measurement of 8.0s timeout."""
        # Measure actual connection timeout behavior
        # Compare against expected timeout values

    @pytest.mark.performance
    async def test_connection_retry_behavior_validation(self):
        """Test connection retry behavior contributing to timeout."""
        # Test connection retry logic and timing
        # Validate retry backoff and total timeout calculation
```

## 5. Test Infrastructure Requirements

### 5.1 Test Dependencies
- **SSOT Base Classes**: All tests inherit from `SSotAsyncTestCase`
- **Real Services**: Integration and E2E tests use real GCP services
- **No Mocks Policy**: Integration tests avoid mocks for database connections
- **Staging Environment**: E2E tests require staging GCP deployment

### 5.2 Test Data and Fixtures
```python
# Shared test fixtures for Issue #1263
@pytest.fixture
async def staging_cloud_sql_config():
    """Staging Cloud SQL configuration for timeout reproduction."""
    return {
        "host": "/cloudsql/netra-staging:us-central1:netra-postgres-staging",
        "port": 5432,
        "database": "netra_staging",
        "timeout_config": "8.0s"  # Reproduce timeout behavior
    }

@pytest.fixture
async def vpc_connector_config():
    """VPC connector configuration for routing validation."""
    return {
        "vpc_access_connector": "netra-vpc-connector",
        "egress": "all-traffic",  # Current configuration causing issues
        "vpc_access_egress": "all-traffic"
    }
```

## 6. Success Criteria and Validation Patterns

### 6.1 Test Failure Patterns (Expected)
```python
# Expected failure patterns to validate root cause
class ExpectedFailurePatterns:
    """Expected test failure patterns for Issue #1263."""

    DETERMINISTIC_STARTUP_ERROR = "DeterministicStartupError: Database initialization failed"
    CONNECTION_TIMEOUT = "Connection timeout after 8.0 seconds"
    VPC_ROUTING_DELAY = "VPC connector routing delay detected"
    SECRET_MANAGER_DELAY = "Secret Manager resolution timeout"
```

### 6.2 Success Criteria for Remediation
```python
# Success criteria when Issue #1263 is fixed
class RemediationSuccessCriteria:
    """Success criteria for Issue #1263 remediation validation."""

    CONNECTION_TIME_TARGET = 2.0  # seconds
    STARTUP_SUCCESS_RATE = 100.0  # percent
    GOLDEN_PATH_FUNCTIONAL = True
    NO_DETERMINISTIC_ERRORS = True
```

### 6.3 Test Execution Commands

```bash
# Unit tests (fast feedback, no infrastructure)
python tests/unified_test_runner.py --category unit --pattern "*issue_1263*" --fast-fail

# Integration tests (real GCP services)
python tests/unified_test_runner.py --category integration --pattern "*issue_1263*" --real-services

# E2E staging tests (full reproduction)
python tests/unified_test_runner.py --category e2e --pattern "*issue_1263*" --env staging

# Performance validation
python tests/unified_test_runner.py --category performance --pattern "*issue_1263*" --timeout 30
```

## 7. Integration with Existing Test Infrastructure

### 7.1 SSOT Compliance
- All tests use `SSotAsyncTestCase` base class
- Configuration through `IsolatedEnvironment`
- Database connections through `DatabaseManager` SSOT
- No direct `os.environ` access

### 7.2 Test Categorization
- **Unit**: `@pytest.mark.unit` - No external dependencies
- **Integration**: `@pytest.mark.integration` - Real GCP services
- **E2E**: `@pytest.mark.e2e` - Full system testing
- **Performance**: `@pytest.mark.performance` - Timing validation

### 7.3 Continuous Integration
```yaml
# CI pipeline integration for Issue #1263 tests
- name: Database Connection Timeout Tests
  run: |
    python tests/unified_test_runner.py \
      --category unit integration \
      --pattern "*issue_1263*" \
      --real-services \
      --timeout 60
```

## 8. Expected Outcomes and Next Steps

### 8.1 Immediate Outcomes
1. **Reproduce 8.0s timeout**: Unit and integration tests reproduce the exact timeout behavior
2. **Identify bottleneck**: Performance tests pinpoint the exact cause within VPC routing
3. **Validate root cause**: VPC egress configuration change confirmed as primary cause
4. **Business impact confirmation**: Golden Path functionality broken by timeout

### 8.2 Remediation Validation
1. **VPC configuration fix**: Tests validate VPC egress setting corrections
2. **Connection optimization**: Performance improvements measurable in tests
3. **Golden Path restoration**: E2E tests confirm $500K+ ARR functionality restored
4. **Startup reliability**: DeterministicStartupError eliminated

### 8.3 Long-term Monitoring
1. **Regression prevention**: Tests become part of CI/CD pipeline
2. **Performance baselines**: Connection timeout thresholds established
3. **VPC configuration validation**: Infrastructure changes tested before deployment
4. **Golden Path protection**: Critical business functionality continuously validated

## 9. Business Value Justification

### 9.1 Revenue Impact
- **Direct**: $500K+ ARR Golden Path functionality restored
- **Indirect**: System reliability and customer confidence maintained
- **Risk Mitigation**: Prevents future VPC configuration regressions

### 9.2 Development Efficiency
- **Faster debugging**: Precise test reproduction of timeout issues
- **Confidence in changes**: VPC modifications validated before deployment
- **Reduced downtime**: Quick identification of connectivity regressions

### 9.3 Platform Reliability
- **Infrastructure confidence**: Network configuration changes tested
- **Database connectivity assurance**: Cloud SQL connection reliability validated
- **Golden Path protection**: Critical user journeys continuously monitored

---

**Document Status**: Draft
**Next Review**: After test implementation
**Owner**: Platform Infrastructure Team
**Stakeholders**: Backend, DevOps, QA Teams