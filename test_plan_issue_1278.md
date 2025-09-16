# Test Plan for Issue #1278: Database Connectivity Infrastructure Failure

## Executive Summary

This test plan provides comprehensive validation for Issue #1278 without requiring infrastructure fixes first. The tests are designed to validate application-level configuration and simulate infrastructure failure patterns.

## Current Issue Status
- **Root Cause**: VPC connector capacity constraints, Cloud SQL networking issues
- **Infrastructure Health**: 23.1% (DEGRADED) 
- **Primary Symptoms**: Database timeouts (85s), WebSocket unreachable, SSL issues
- **Environment**: Staging GCP deployment

## Test Categories

### Phase 1: Application Configuration Tests (Run Immediately)
**Purpose**: Validate app code is correctly configured
**Location**: Local/CI
**Expected**: PASS (proves code readiness)

#### Test Files to Create/Run:
1. `tests/unit/infrastructure/test_issue_1278_application_config_validation.py`
   - Database connection string validation
   - VPC connector configuration validation  
   - SSL certificate configuration validation
   - Timeout configuration validation

2. `tests/integration/test_issue_1278_configuration_compliance.py`
   - Environment variable validation
   - Service configuration SSOT compliance
   - Domain configuration validation

### Phase 2: Infrastructure Failure Simulation Tests (Run Immediately)
**Purpose**: Reproduce failure patterns for validation
**Location**: Local/CI with mocks
**Expected**: FAIL now, PASS after fix

#### Test Files to Create:
3. `tests/simulation/test_issue_1278_vpc_connector_capacity_simulation.py`
   - Simulate VPC connector capacity exhaustion
   - Test connection timeout patterns (85s timeout)
   - Test connection retry logic

4. `tests/simulation/test_issue_1278_cloud_sql_timeout_simulation.py`
   - Simulate Cloud SQL connection timeouts
   - Test database pool behavior under stress
   - Test transaction timeout handling

5. `tests/simulation/test_issue_1278_dns_resolution_simulation.py`
   - Simulate DNS resolution failures for api-staging.netrasystems.ai
   - Test WebSocket connection failure patterns
   - Test fallback behavior

### Phase 3: GCP Staging Connectivity Tests (Run Against Staging)
**Purpose**: Validate actual infrastructure state
**Location**: GCP staging environment
**Expected**: FAIL now, PASS after fix

#### Test Files to Run:
6. `tests/e2e/staging/test_issue_1278_staging_reproduction.py` (exists)
   - End-to-end reproduction of Issue #1278
   - Database connectivity validation
   - WebSocket endpoint connectivity

7. `tests/infrastructure/test_issue_1278_infrastructure_health_validation.py` (exists)
   - VPC connector health checks
   - Cloud SQL accessibility tests
   - Performance threshold validation

### Phase 4: Post-Fix Validation Suite (Run After Infrastructure Fix)
**Purpose**: Comprehensive validation that issues are resolved
**Location**: GCP staging environment
**Expected**: PASS only after fix

#### Test Files to Run:
8. `tests/validation/test_issue_1278_post_fix_validation.py` (exists)
   - Golden Path end-to-end validation
   - Performance SLA compliance
   - Load resilience testing

## Test Execution Commands

### Immediate Execution (Phases 1-2):
```bash
# Application configuration validation
python tests/unified_test_runner.py --category unit --pattern "*issue_1278*config*" 

# Infrastructure failure simulation  
python tests/unified_test_runner.py --category simulation --pattern "*issue_1278*"

# Generate infrastructure health report
python scripts/infrastructure_health_check_issue_1278.py --report-only
```

### Staging Environment Testing (Phase 3):
```bash
# Staging connectivity validation (expected to fail)
python tests/unified_test_runner.py --env staging --category e2e --pattern "*issue_1278*staging*"

# Infrastructure health validation
python tests/unified_test_runner.py --env staging --test-file tests/infrastructure/test_issue_1278_infrastructure_health_validation.py
```

### Post-Fix Validation (Phase 4):
```bash
# Comprehensive post-fix validation
python tests/unified_test_runner.py --env staging --test-file tests/validation/test_issue_1278_post_fix_validation.py

# Golden Path validation
python tests/unified_test_runner.py --env staging --category e2e --pattern "*golden_path*"
```

## Success Criteria

### Before Infrastructure Fix:
- ✅ **Phase 1 Tests**: Should PASS (confirms application configuration)
- ❌ **Phase 2 Tests**: Should FAIL (reproduces infrastructure issues)  
- ❌ **Phase 3 Tests**: Should FAIL (confirms staging environment issues)
- ❌ **Phase 4 Tests**: Should FAIL (infrastructure not ready)

### After Infrastructure Fix:
- ✅ **Phase 1 Tests**: Should PASS (configuration still valid)
- ✅ **Phase 2 Tests**: Should PASS (infrastructure issues resolved)
- ✅ **Phase 3 Tests**: Should PASS (staging environment healthy)
- ✅ **Phase 4 Tests**: Should PASS (full validation complete)

## Key Test Focus Areas

### Database Connectivity (Priority 1)
- Connection timeout validation (should be <10s after fix)
- Connection pool behavior under load
- Transaction isolation and retry logic
- VPC connector routing validation

### WebSocket Infrastructure (Priority 2)  
- DNS resolution for api-staging.netrasystems.ai
- SSL certificate validation for *.netrasystems.ai
- WebSocket upgrade success rates
- Event delivery reliability

### Performance Validation (Priority 3)
- Database operation latency (<5s)
- Agent response times (<30s)
- Service startup times (<45s)
- Load balancer health check timing

## Monitoring Integration

### Health Endpoints
- `/health/infrastructure` - Infrastructure component status
- `/health/backend` - Backend service capabilities
- `/health/ready` - Startup probe readiness

### Metrics Collection
- Connection timeout rates
- VPC connector throughput utilization
- Database connection pool metrics
- WebSocket event delivery rates

## Risk Mitigation

### Test Environment Isolation
- Use test-specific configuration
- Avoid impacting production systems
- Clean state between test runs

### Failure Handling
- Graceful degradation validation
- Error message clarity
- Monitoring alert verification

## Implementation Priority

1. **IMMEDIATE** (Phase 1): Application configuration validation
2. **IMMEDIATE** (Phase 2): Infrastructure failure simulation  
3. **AFTER TRIAGE** (Phase 3): Staging environment validation
4. **POST-FIX** (Phase 4): Comprehensive validation suite

This test plan provides comprehensive coverage for validating Issue #1278 resolution while ensuring our application code is properly configured to work with the infrastructure once it's fixed.